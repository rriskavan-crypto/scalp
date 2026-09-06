"""Swing EA'lari: o'zini grafik timeframe'idan sozlaydigan variant.

Bu EA'lar `input` orqali emas, kod ichidagi `Apply_<TF>_<KIND>()` bloklari
orqali sozlanadi. Shuning uchun eng katta xavf boshqacha: oddiy EA'da
unutilgan parametr kompilyatsiya xatosi beradi, bu yerda esa blok ichida
QOLDIRILGAN maydon jimgina initsializatsiyasiz qoladi va EA noto'g'ri
parametr bilan savdo qiladi. Shuning uchun har bir blok to'liq
tekshiriladi.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scalpkit.config import Config                     # noqa: E402
from scalpkit.features import DEFAULT_FEATURE_PARAMS   # noqa: E402
from scalpkit.profiles import (BTCUSD, XAUUSD,         # noqa: E402
                               expected_hold_days, for_timeframe)
from scalpkit.strategies import get_strategy           # noqa: E402

from test_mql5_parity import (FEATURE_MAP, RISK_MAP,   # noqa: E402
                              SKIP_FOR, STRATEGY_MAP, same)

CORE = ROOT / "mql5" / "Include" / "ScalpKit" / "Core.mqh"
EXPERTS = ROOT / "mql5" / "Experts"

SWING = {
    "btc": (BTCUSD, EXPERTS / "ScalpKit_BTC_Swing.mq5", 20261100),
    "xau": (XAUUSD, EXPERTS / "ScalpKit_XAU_Swing.mq5", 20261200),
}
KIND_NAME = {1: "donchian_breakout", 2: "range_reversion"}
TF_OF = {"15M": "15m", "1H": "1h", "4H": "4h", "1D": "1d"}
# MQL5 enum nomlari boshqacha tartibda: PERIOD_M15, PERIOD_H1, ...
TF_OF_PERIOD = {"M15": "15m", "H1": "1h", "H4": "4h", "D1": "1d"}
TF_INDEX = {"15m": 1, "1h": 2, "4h": 3, "1d": 4}

# Foydalanuvchi inputlari kalibrlangan blokdan keyin qo'llanadi
USER_OVERRIDES = {
    "RiskPerTrade": "risk_per_trade", "DailyLossLimit": "daily_loss_limit",
    "MaxLeverage": "max_leverage",
}


def blocks(path: Path) -> dict[tuple[str, int], dict[str, str]]:
    """`Apply_4H_1()` kabi funksiyalardan `g_cfg.X = V;` juftliklarini oladi."""
    src = path.read_text("utf-8")
    out: dict[tuple[str, int], dict[str, str]] = {}
    for m in re.finditer(r"void Apply_(\w+?)_(\d)\(\)\s*\{(.*?)\n\}", src, re.S):
        tf, kind = TF_OF[m.group(1)], int(m.group(2))
        fields = dict(re.findall(r"g_cfg\.(\w+)\s*=\s*([^;]+);", m.group(3)))
        out[(tf, kind)] = {k: v.strip() for k, v in fields.items()}
    return out


def as_value(raw: str):
    if raw in ("true", "false"):
        return raw == "true"
    try:
        return float(raw)
    except ValueError:
        return raw


ALL_BLOCKS = [(sym, tf, kind)
              for sym, (_, path, _) in SWING.items()
              for (tf, kind) in sorted(blocks(path))]
BLOCK_IDS = [f"{s}-{tf}-{KIND_NAME[k]}" for s, tf, k in ALL_BLOCKS]


def expected_for(sym: str, tf: str, kind: int):
    base = SWING[sym][0]
    strategy_name = KIND_NAME[kind]
    profile = for_timeframe(base, tf)
    cfg = profile.apply(Config(), strategy_name)
    params = get_strategy(strategy_name, cfg.strategy.params).params
    return profile, strategy_name, params, cfg, blocks(SWING[sym][1])[(tf, kind)]


# ------------------------------------------------------------------ #
#  Har bir blok Python profiliga mos kelishi kerak
# ------------------------------------------------------------------ #
@pytest.mark.parametrize("sym,tf,kind", ALL_BLOCKS, ids=BLOCK_IDS)
def test_block_strategy_parameters_match(sym, tf, kind):
    _, strategy_name, params, _, got = expected_for(sym, tf, kind)
    skip = {n[3:] for n in SKIP_FOR[strategy_name]}
    checked = 0
    for inp, key in STRATEGY_MAP.items():
        field = inp[3:]
        if field in skip or field not in got or key not in params:
            continue
        same(as_value(got[field]), params[key], f"{sym}/{tf}/{strategy_name}.{field}")
        checked += 1
    assert checked >= 10, f"juda kam parametr tekshirildi: {checked}"


@pytest.mark.parametrize("sym,tf,kind", ALL_BLOCKS, ids=BLOCK_IDS)
def test_block_risk_and_indicator_parameters_match(sym, tf, kind):
    _, _, _, cfg, got = expected_for(sym, tf, kind)
    for inp, key in RISK_MAP.items():
        field = inp[3:]
        if field in got:
            same(as_value(got[field]), getattr(cfg.risk, key), f"{sym}/{tf}.{field}")
    for inp, key in FEATURE_MAP.items():
        field = inp[3:]
        if field in got:
            same(as_value(got[field]), DEFAULT_FEATURE_PARAMS[key], f"{sym}/{tf}.{field}")


@pytest.mark.parametrize("sym,tf,kind", ALL_BLOCKS, ids=BLOCK_IDS)
def test_block_expected_hold_days_match(sym, tf, kind):
    """Swap xarajati shu bahoga tayanadi — u profil bilan bir xil bo'lsin."""
    _, strategy_name, params, _, got = expected_for(sym, tf, kind)
    assert "ExpectedHoldDays" in got
    same(as_value(got["ExpectedHoldDays"]),
         expected_hold_days(tf, strategy_name, params), f"{sym}/{tf}.hold")


# ------------------------------------------------------------------ #
#  Eng muhimi: hech qanday maydon initsializatsiyasiz qolmasin
# ------------------------------------------------------------------ #
def declared_fields() -> set[str]:
    block = re.search(r"struct ScalpKitConfig\s*\{(.*?)\n\};",
                      CORE.read_text("utf-8"), re.S)
    assert block, "ScalpKitConfig topilmadi"
    return set(re.findall(r"^\s*(?:double|int|bool|long|string)\s+(\w+);",
                          block.group(1), re.M))


@pytest.mark.parametrize("sym,tf,kind", ALL_BLOCKS, ids=BLOCK_IDS)
def test_every_config_field_is_set_for_every_timeframe(sym, tf, kind):
    """Blok + LoadConfig birgalikda strukturaning HAMMA maydonini yozadi.

    Bir maydon unutilsa MQL5 xato bermaydi — u avvalgi qiymatida qoladi.
    Timeframe'lar orasida almashganda bu jimgina noto'g'ri kalibrlash.
    """
    src = SWING[sym][1].read_text("utf-8")
    tail = src.split("bool LoadConfig()")[1]
    in_load = set(re.findall(r"g_cfg\.(\w+)\s*=", tail))
    got = set(blocks(SWING[sym][1])[(tf, kind)])
    missing = declared_fields() - (got | in_load)
    assert not missing, f"{sym}/{tf}/{KIND_NAME[kind]} da yozilmagan: {sorted(missing)}"


@pytest.mark.parametrize("sym", sorted(SWING))
def test_no_field_is_written_outside_the_struct(sym):
    src = SWING[sym][1].read_text("utf-8")
    written = set(re.findall(r"g_cfg\.(\w+)\s*=", src))
    assert not (written - declared_fields()), \
        f"strukturada yo'q maydon: {sorted(written - declared_fields())}"


# ------------------------------------------------------------------ #
#  Foydalanuvchi inputlari xavfsizmi
# ------------------------------------------------------------------ #
@pytest.mark.parametrize("field,key", sorted(USER_OVERRIDES.items()))
def test_user_overrides_are_timeframe_invariant(field, key):
    """Input kalibrlangan qiymatni bossa, u TF'ga bog'liq BO'LMASLIGI shart.

    `weekend_flat` aynan shu sababdan input emas, uch holatli rejim:
    oltinda u M15/H1 da yoqilgan, H4/D1 da o'chirilgan.
    """
    for base in (BTCUSD, XAUUSD):
        seen = {getattr(for_timeframe(base, tf).apply(Config(), "donchian_breakout").risk,
                        key) for tf in TF_INDEX}
        assert len(seen) == 1, (
            f"{base.name}.{key} timeframe bo'yicha o'zgaradi ({seen}) — "
            f"uni oddiy input qilib bo'lmaydi, uch holatli rejim kerak")


def test_weekend_rule_is_tristate_and_defaults_to_the_profile():
    for sym, (base, path, _) in SWING.items():
        src = path.read_text("utf-8")
        assert re.search(r"input\s+int\s+InpWeekendFlatMode\s*=\s*-1;", src), \
            f"{sym}: hafta oxiri rejimi uch holatli emas"
        assert "if(InpWeekendFlatMode >= 0)" in src, \
            f"{sym}: -1 holatida profil qiymati saqlanmaydi"


def test_gold_swing_keeps_the_weekend_rule_on_low_timeframes():
    """Oltin M15/H1 da hafta oxiriga pozitsiyasiz kiradi, H4/D1 da yo'q."""
    got = blocks(SWING["xau"][1])
    assert got[("15m", 1)]["WeekendFlat"] == "true"
    assert got[("1h", 1)]["WeekendFlat"] == "true"
    assert got[("4h", 1)]["WeekendFlat"] == "false"
    assert got[("1d", 1)]["WeekendFlat"] == "false"


def test_crypto_swing_never_closes_for_the_weekend():
    for (tf, kind), fields in blocks(SWING["btc"][1]).items():
        assert fields["WeekendFlat"] == "false", f"btc/{tf}/{kind}: 24/7 bozor"


# ------------------------------------------------------------------ #
#  Qamrov: qaysi juftliklar taklif qilinadi
# ------------------------------------------------------------------ #
def test_trend_covers_every_swing_timeframe():
    for sym in SWING:
        got = {tf for tf, kind in blocks(SWING[sym][1]) if kind == 1}
        assert got == set(TF_INDEX), f"{sym}: trend qamrovi {sorted(got)}"


def test_reversion_is_not_offered_where_it_cannot_be_measured():
    """H4/D1 da o'rtachaga qaytish 3 yilda 100 savdoga yetmaydi (33 va 3).

    Statistik xulosa chiqarib bo'lmaydigan juftlikni taklif qilish —
    foydalanuvchini shovqinni natija deb o'qishga undash demakdir.
    """
    for sym in SWING:
        got = {tf for tf, kind in blocks(SWING[sym][1]) if kind == 2}
        assert got == {"15m", "1h"}, f"{sym}: qaytish qamrovi {sorted(got)}"


@pytest.mark.parametrize("sym", sorted(SWING))
def test_dispatcher_covers_exactly_the_generated_blocks(sym):
    """Yozilgan blok bor, lekin dispetcherda yo'q — o'lik kod, jimgina xato."""
    src = SWING[sym][1].read_text("utf-8")
    routed = {(TF_OF_PERIOD[tf], int(kind)) for kind, tf in
              re.findall(r"if\(kind == (\d) && tf == PERIOD_(\w+)\)", src)}
    assert routed == set(blocks(SWING[sym][1]))


# ------------------------------------------------------------------ #
#  Magic raqamlar
# ------------------------------------------------------------------ #
def test_magic_numbers_are_unique_across_symbol_strategy_and_timeframe():
    """Bir vaqtda bir nechta grafikda ishlasa, ular bir-birini yopmasin."""
    seen: dict[int, str] = {}
    for sym, (_, path, magic_base) in SWING.items():
        assert re.search(rf"InpMagicBase\s*=\s*{magic_base};", path.read_text("utf-8"))
        for tf, kind in blocks(path):
            magic = magic_base + kind * 10 + TF_INDEX[tf]
            label = f"{sym}/{tf}/{KIND_NAME[kind]}"
            assert magic not in seen, f"magic {magic}: {label} va {seen[magic]}"
            seen[magic] = label
    assert len(seen) == 12


def test_swing_magics_do_not_collide_with_the_preset_experts():
    others = set()
    for path in EXPERTS.glob("ScalpKit_*.mq5"):
        if path.name.endswith("_Swing.mq5"):
            continue
        m = re.search(r"InpMagic\s*=\s*(\d+);", path.read_text("utf-8"))
        assert m, f"{path.name}: magic topilmadi"
        others.add(int(m.group(1)))
    swing = {base + kind * 10 + TF_INDEX[tf]
             for _, (_, path, base) in SWING.items()
             for tf, kind in blocks(path)}
    assert not (others & swing), f"to'qnashuv: {sorted(others & swing)}"


# ------------------------------------------------------------------ #
#  Timeframe kalibrlash haqiqatan farq qiladimi
# ------------------------------------------------------------------ #
def test_higher_timeframes_use_wider_thresholds():
    """Bu EA'ning butun mavjud bo'lish sababi: TF'lar bir xil emas."""
    for sym in SWING:
        got = blocks(SWING[sym][1])
        atr = [float(got[(tf, 1)]["MinAtrPct"]) for tf in ("15m", "1h", "4h", "1d")]
        assert atr == sorted(atr) and atr[0] < atr[-1] / 5, \
            f"{sym}: ATR chegaralari TF bo'yicha o'smayapti: {atr}"
        stop = [float(got[(tf, 1)]["MinStopPct"]) for tf in ("15m", "1h", "4h", "1d")]
        assert stop == sorted(stop) and stop[0] < stop[-1] / 5, \
            f"{sym}: stop chegaralari TF bo'yicha o'smayapti: {stop}"


def test_hold_estimate_grows_with_timeframe():
    for sym in SWING:
        got = blocks(SWING[sym][1])
        hold = [float(got[(tf, 1)]["ExpectedHoldDays"]) for tf in ("15m", "1h", "4h", "1d")]
        assert hold == sorted(hold)
        assert hold[-1] > 10.0, f"{sym}: D1 ushlash bahosi juda kichik: {hold[-1]}"


def test_trend_blocks_never_set_a_profit_target():
    """Trend-following foydasi uzun dumdan keladi — maqsad uni kesadi."""
    for sym in SWING:
        for (tf, kind), fields in blocks(SWING[sym][1]).items():
            if kind != 1:
                continue
            assert float(fields["Tp2R"]) == 0.0, f"{sym}/{tf}: maqsad qo'yilgan"


def test_reversion_blocks_always_require_a_target():
    """O'rtachaga qaytish ustunligi bitta aniq harakatda — maqsad majburiy."""
    for sym in SWING:
        for (tf, kind), fields in blocks(SWING[sym][1]).items():
            if kind != 2:
                continue
            assert float(fields["MinTargetR"]) >= 1.0, f"{sym}/{tf}: mukofot/risk past"
            assert float(fields["AdxMax"]) > 0.0, f"{sym}/{tf}: rejim filtri yo'q"
