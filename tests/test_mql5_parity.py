"""MQL5 EA fayllari va Python profillarining mosligi.

Uchta mustaqil artefakt bor:
  * `scalpkit/profiles.py`            — kalibrlangan parametrlar
  * `mql5/Include/ScalpKit/Core.mqh`  — umumiy savdo mantig'i
  * `mql5/Experts/ScalpKit_*.mq5`     — instrumentga xos standart qiymatlar

Ular ajralib ketsa, backtest natijasi real savdoni tasvirlamay qo'yadi —
ya'ni butun tekshiruv ishi qiymatini yo'qotadi. EA fayllari
`tools/gen_mql5_experts.py` bilan generatsiya qilinadi; bu testlar
generatsiya natijasi joriy profillarga mos ekanini qulflaydi.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

from scalpkit.config import Config
from scalpkit.features import DEFAULT_FEATURE_PARAMS
from scalpkit.profiles import BTCUSD, XAUUSD, for_timeframe
from scalpkit.strategies import get_strategy

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "mql5" / "Include" / "ScalpKit" / "Core.mqh"
EXPERTS = ROOT / "mql5" / "Experts"

# nom -> (bazaviy profil, timeframe, strategiya, EA fayli)
EA_FOR_PROFILE = {
    "btc_scalp": (BTCUSD, "5m", "momentum_pullback", EXPERTS / "ScalpKit_BTC_Scalp.mq5"),
    "xau_scalp": (XAUUSD, "5m", "momentum_pullback", EXPERTS / "ScalpKit_XAU_Scalp.mq5"),
    "btc_trend": (BTCUSD, "4h", "donchian_breakout", EXPERTS / "ScalpKit_BTC_Trend.mq5"),
    "xau_trend": (XAUUSD, "4h", "donchian_breakout", EXPERTS / "ScalpKit_XAU_Trend.mq5"),
    "btc_range": (BTCUSD, "4h", "range_reversion", EXPERTS / "ScalpKit_BTC_Range.mq5"),
    "xau_range": (XAUUSD, "4h", "range_reversion", EXPERTS / "ScalpKit_XAU_Range.mq5"),
}

STRATEGY_KIND = {"momentum_pullback": 0, "donchian_breakout": 1, "range_reversion": 2}

# Har bir strategiya faqat o'ziga tegishli parametrlar bo'yicha tekshiriladi
PULLBACK_ONLY = {
    "InpImpulseLookback", "InpImpulseBodyAtr", "InpImpulseVolZ",
    "InpPullbackLookback", "InpTouchAtr", "InpRsiPullbackLong",
    "InpRsiPullbackShort", "InpTriggerVolZ", "InpTriggerClosePos",
    "InpMaxExtensionAtr", "InpAdxMin", "InpRequireHTF", "InpSlBufferAtr",
}
DONCHIAN_ONLY = {
    "InpTrendLen", "InpRequireTrendFilter", "InpEntryLen", "InpExitLen",
    "InpCooldownLen",
}
REVERSION_ONLY = {
    "InpAdxMax", "InpBandLen", "InpEntryZ", "InpRevRsiLen", "InpRsiOversold",
    "InpRsiOverbought", "InpRequireReversalBar", "InpSetupLookback",
    "InpRangeDevAtr", "InpMinTargetR",
}
# Har bir strategiya uchun TEKSHIRILMAYDIGAN (boshqasiga tegishli) parametrlar
SKIP_FOR = {
    "momentum_pullback": DONCHIAN_ONLY | REVERSION_ONLY | {"InpSlAtrMult"},
    "donchian_breakout": PULLBACK_ONLY | REVERSION_ONLY,
    "range_reversion": PULLBACK_ONLY | DONCHIAN_ONLY | {"InpTrendLen"},
}

STRATEGY_MAP = {
    "InpMinAtrPct": "min_atr_pct", "InpMaxAtrPct": "max_atr_pct",
    "InpAdxMin": "adx_min", "InpRequireHTF": "require_htf",
    "InpUseSession": "use_session_filter",
    "InpSessionStartUTC": "session_start_hour", "InpSessionEndUTC": "session_end_hour",
    "InpImpulseLookback": "impulse_lookback", "InpImpulseBodyAtr": "impulse_body_atr",
    "InpImpulseVolZ": "impulse_vol_z", "InpPullbackLookback": "pullback_lookback",
    "InpTouchAtr": "touch_atr", "InpRsiPullbackLong": "rsi_pullback_long",
    "InpRsiPullbackShort": "rsi_pullback_short", "InpTriggerVolZ": "trigger_vol_z",
    "InpTriggerClosePos": "trigger_close_pos", "InpMaxExtensionAtr": "max_extension_atr",
    "InpEntryOffsetAtr": "entry_offset_atr", "InpEntryLimitBars": "entry_limit_bars",
    "InpSlBufferAtr": "sl_buffer_atr", "InpMinSlAtr": "min_sl_atr",
    "InpMaxSlAtr": "max_sl_atr", "InpTp1R": "tp1_r", "InpTp1Fraction": "tp1_fraction",
    "InpTp2R": "tp2_r", "InpTp1StopToR": "tp1_stop_to_r", "InpBeTriggerR": "be_trigger_r",
    "InpBeOffsetR": "be_offset_r", "InpTrailAfterR": "trail_after_r",
    "InpTrailAtrMult": "trail_atr_mult", "InpTrailMinStepAtr": "trail_min_step_atr",
    "InpTimeStopBars": "time_stop_bars", "InpTimeStopMinR": "time_stop_min_r",
    "InpExitOnEmaCross": "exit_on_ema_cross", "InpWeekendFlat": "weekend_flat",
    "InpSlAtrMult": "sl_atr_mult",
    "InpAdxMax": "adx_max", "InpBandLen": "band_len", "InpEntryZ": "entry_z",
    "InpRevRsiLen": "rsi_len", "InpRsiOversold": "rsi_oversold",
    "InpRsiOverbought": "rsi_overbought",
    "InpRequireReversalBar": "require_reversal_bar",
    "InpSetupLookback": "setup_lookback", "InpRangeDevAtr": "range_dev_atr",
    "InpMinTargetR": "min_target_r",
    "InpWeekCloseHourUTC": "week_close_hour_utc", "InpWeekCloseDow": "week_close_dow",
    "InpWeekOpenSkipBars": "week_open_skip_bars",
}

FEATURE_MAP = {
    "InpEmaFast": "ema_fast", "InpEmaMid": "ema_mid", "InpEmaSlow": "ema_slow",
    "InpAtrLen": "atr_len", "InpRsiLen": "rsi_len", "InpAdxLen": "adx_len",
    "InpDonchianLen": "donchian_len", "InpVolZLen": "vol_z_len",
    "InpSwingLen": "swing_len", "InpHtfEma": "htf_ema",
}

RISK_MAP = {
    "InpRiskPerTrade": "risk_per_trade", "InpMaxLeverage": "max_leverage",
    "InpMaxTradesPerDay": "max_trades_per_day", "InpDailyLossLimit": "daily_loss_limit",
    "InpMaxConsecLosses": "max_consecutive_losses",
    "InpCooldownBars": "cooldown_bars_after_loss",
    "InpStreakCooldown": "cooldown_bars_after_streak",
    "InpHalveRiskDD": "halve_risk_drawdown",
    "InpMinStopPct": "min_stop_pct", "InpMaxStopPct": "max_stop_pct",
}


def read_inputs(path: Path) -> dict[str, object]:
    assert path.exists(), f"EA fayli topilmadi: {path}"
    out: dict[str, object] = {}
    for m in re.finditer(r"^input\s+\S+\s+(\w+)\s*=\s*([^;]+);", path.read_text("utf-8"), re.M):
        raw = m.group(2).strip()
        if raw in ("true", "false"):
            out[m.group(1)] = (raw == "true")
            continue
        try:
            out[m.group(1)] = float(raw)
        except ValueError:
            out[m.group(1)] = raw          # ENUM_TIMEFRAMES kabi belgili qiymatlar
    return out


def expected(profile_name: str):
    base, tf, strategy_name, path = EA_FOR_PROFILE[profile_name]
    profile = for_timeframe(base, tf)
    cfg = profile.apply(Config(), strategy_name)
    params = get_strategy(strategy_name, cfg.strategy.params).params
    return profile, strategy_name, params, cfg, read_inputs(path)


def same(ea_value, py_value, name: str) -> None:
    if isinstance(py_value, bool) or isinstance(ea_value, bool):
        assert bool(ea_value) == bool(py_value), f"{name}: EA={ea_value} Python={py_value}"
    else:
        assert float(ea_value) == pytest.approx(float(py_value)), \
            f"{name}: EA={ea_value} Python={py_value}"


@pytest.mark.parametrize("profile_name", sorted(EA_FOR_PROFILE))
def test_strategy_parameters_match(profile_name):
    _, strategy_name, params, _, inputs = expected(profile_name)
    skip = SKIP_FOR[strategy_name]
    for ea_name, py_key in STRATEGY_MAP.items():
        if ea_name in skip:
            continue
        assert ea_name in inputs, f"{ea_name} EA da yo'q"
        same(inputs[ea_name], params[py_key], f"{profile_name}/{ea_name}")


@pytest.mark.parametrize("profile_name", sorted(EA_FOR_PROFILE))
def test_risk_parameters_match(profile_name):
    _, _, _, cfg, inputs = expected(profile_name)
    for ea_name, py_key in RISK_MAP.items():
        same(inputs[ea_name], getattr(cfg.risk, py_key), f"{profile_name}/{ea_name}")


@pytest.mark.parametrize("profile_name", sorted(EA_FOR_PROFILE))
def test_indicator_lengths_match(profile_name):
    inputs = expected(profile_name)[4]
    for ea_name, py_key in FEATURE_MAP.items():
        same(inputs[ea_name], DEFAULT_FEATURE_PARAMS[py_key], f"{profile_name}/{ea_name}")


@pytest.mark.parametrize("profile_name", sorted(EA_FOR_PROFILE))
def test_limit_entry_matches_entry_mode(profile_name):
    _, _, params, _, inputs = expected(profile_name)
    assert inputs["InpUseLimitEntry"] is (params["entry_mode"] == "limit")


@pytest.mark.parametrize("profile_name", sorted(EA_FOR_PROFILE))
def test_strategy_kind_matches_the_expert(profile_name):
    _, strategy_name, _, _, inputs = expected(profile_name)
    assert inputs["InpStrategyKind"] == STRATEGY_KIND[strategy_name]


def test_trend_experts_have_no_profit_target():
    """Trend-following foydasi dumdan keladi — maqsad uni kesib tashlaydi.

    Bu eng oson buziladigan dizayn qarori: profilning `tp2_r = 3.0`
    qiymati Donchian'ga sizib o'tsa, strategiya jim ravishda buziladi.
    """
    for name in ("btc_trend", "xau_trend"):
        inputs = expected(name)[4]
        assert inputs["InpTp2R"] == 0.0, f"{name}: maqsad qo'yilgan!"
        assert inputs["InpTp1Fraction"] == 0.0, f"{name}: qisman olish qo'yilgan!"
    for name in ("btc_scalp", "xau_scalp"):
        assert expected(name)[4]["InpTp2R"] > 0.0


def test_reversion_experts_require_an_adequate_reward():
    """Mukofot/risk filtri mean-reversion uchun majburiy.

    Kirish qaytish barida bo'lgani uchun narx allaqachon o'rtachaga
    yaqinlashgan. Filtrsiz savdolarning 61 % ida mukofot riskdan
    kichik chiqardi — bunday tuzilma yutqazishga mahkum.
    """
    for name in ("btc_range", "xau_range"):
        inputs = expected(name)[4]
        assert inputs["InpMinTargetR"] >= 1.0, f"{name}: mukofot/risk filtri yo'q"
        # Trailing mean-reversion'da qaytishni qaytarib beradi — o'chirilgan
        assert inputs["InpTrailAfterR"] > 100


def test_reversion_and_trend_use_opposite_regimes():
    """Ikkalasi bir-birini to'ldirishi kerak: biri trendda, biri yon harakatda."""
    trend = expected("btc_trend")[4]
    reversion = expected("btc_range")[4]
    assert reversion["InpAdxMax"] <= 30.0        # yon harakat
    assert reversion["InpTp2R"] > 0 or reversion["InpMinTargetR"] > 0
    assert trend["InpTp2R"] == 0.0               # trend — maqsadsiz


def test_experts_declare_their_timeframe():
    """Parametrlar TF'ga bog'liq kalibrlangan — noto'g'ri grafikda ishlamasin."""
    for name, (_, tf, _, _) in EA_FOR_PROFILE.items():
        want = {"5m": "PERIOD_M5", "15m": "PERIOD_M15", "1h": "PERIOD_H1",
                "4h": "PERIOD_H4", "1d": "PERIOD_D1"}[tf]
        assert expected(name)[4]["InpExpectedTimeframe"] == want


@pytest.mark.parametrize("profile_name", sorted(EA_FOR_PROFILE))
def test_cost_guard_matches_python(profile_name):
    """EA va Python bir xil xarajat chegarasida savdoni rad etishi kerak."""
    import inspect

    from scalpkit import trader

    source = inspect.getsource(trader.LiveTrader._open_trade)
    m = re.search(r"cost_r\s*>\s*([0-9.]+)", source)
    assert m, "trader.py da xarajat chegarasi topilmadi"
    same(expected(profile_name)[4]["InpMaxCostR"], float(m.group(1)), "InpMaxCostR")


def test_every_expert_uses_a_distinct_magic_number():
    """Bir terminalda bir nechtasi ishlasa, savdolar aralashib ketmasligi kerak."""
    magics = [expected(n)[4]["InpMagic"] for n in EA_FOR_PROFILE]
    assert len(set(magics)) == len(magics), f"magic raqamlar takrorlanmoqda: {magics}"


def test_gold_experts_enable_the_weekend_rule_on_low_timeframes():
    """Oltin M5 da hafta oxiriga pozitsiyasiz kiradi; D1 da bu imkonsiz."""
    assert expected("xau_scalp")[4]["InpWeekendFlat"] is True
    assert expected("btc_scalp")[4]["InpWeekendFlat"] is False
    # H4 swing'da hafta chegarasi o'chiriladi — bir bar bir necha kunni qamraydi
    assert expected("xau_trend")[4]["InpWeekendFlat"] is False


def test_gold_volatility_filter_is_far_below_the_crypto_one():
    """Regressiya: BTC filtri oltinda barcha barlarni bloklaydi."""
    for gold, crypto in (("xau_scalp", "btc_scalp"), ("xau_trend", "btc_trend")):
        g, c = expected(gold)[4], expected(crypto)[4]
        assert g["InpMinAtrPct"] < c["InpMinAtrPct"] / 3.0
        assert g["InpMinStopPct"] < c["InpMinStopPct"] / 3.0


def test_higher_timeframe_experts_use_wider_thresholds():
    """Volatilitet TF bilan o'sadi — chegaralar ham o'sishi shart."""
    for scalp, trend in (("btc_scalp", "btc_trend"), ("xau_scalp", "xau_trend")):
        assert expected(trend)[4]["InpMinAtrPct"] > expected(scalp)[4]["InpMinAtrPct"] * 3


# ------------------------------------------------------------ tuzilma
def test_generated_experts_are_up_to_date():
    """EA fayllari joriy profillardan generatsiya qilinganmi."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "gen_mql5_experts.py"), "--check"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_core_config_struct_covers_every_field_used():
    """`g_cfg.X` ishlatilsa, u strukturada e'lon qilingan bo'lishi shart."""
    core = CORE.read_text("utf-8")
    block = re.search(r"struct ScalpKitConfig\s*\{(.*?)\n\};", core, re.S)
    assert block, "ScalpKitConfig strukturasi topilmadi"
    declared = set(re.findall(r"^\s*(?:double|int|bool|long|string)\s+(\w+);",
                              block.group(1), re.M))
    used = set(re.findall(r"\bg_cfg\.(\w+)\b", core))
    assert not (used - declared), f"e'lon qilinmagan maydonlar: {sorted(used - declared)}"
    assert not (declared - used), f"ishlatilmagan maydonlar: {sorted(declared - used)}"


@pytest.mark.parametrize("profile_name", sorted(EA_FOR_PROFILE))
def test_every_config_field_is_passed_by_the_expert(profile_name):
    core = CORE.read_text("utf-8")
    block = re.search(r"struct ScalpKitConfig\s*\{(.*?)\n\};", core, re.S)
    declared = set(re.findall(r"^\s*(?:double|int|bool|long|string)\s+(\w+);",
                              block.group(1), re.M))
    src = EA_FOR_PROFILE[profile_name][3].read_text("utf-8")
    assigned = set(re.findall(r"g_cfg\.(\w+)\s*=", src))
    assert declared == assigned, (
        f"uzatilmagan: {sorted(declared - assigned)}; "
        f"ortiqcha: {sorted(assigned - declared)}"
    )


@pytest.mark.parametrize("path", [CORE, *[t[3] for t in EA_FOR_PROFILE.values()]],
                         ids=lambda p: p.name)
def test_mql_files_have_balanced_delimiters(path):
    """Kompilyatorsiz eng oddiy, lekin foydali tekshiruv."""
    clean, state = _strip(path.read_text("utf-8"))
    assert state == "code", "yopilmagan satr yoki kommentariy bor"
    for opener, closer in (("{", "}"), ("(", ")"), ("[", "]")):
        assert clean.count(opener) == clean.count(closer), \
            f"'{opener}{closer}' qavslar muvozanatda emas"


def _strip(src: str) -> tuple[str, str]:
    out: list[str] = []
    i, n, state = 0, len(src), "code"
    while i < n:
        c, nxt = src[i], (src[i + 1] if i + 1 < n else "")
        if state == "code":
            if c == "/" and nxt == "/":
                state = "line"; i += 2; continue
            if c == "/" and nxt == "*":
                state = "block"; i += 2; continue
            if c in "\"'":
                state = "dq" if c == '"' else "sq"; i += 1; continue
            out.append(c); i += 1; continue
        if state == "line":
            if c == "\n":
                state = "code"; out.append("\n")
            i += 1; continue
        if state == "block":
            if c == "*" and nxt == "/":
                state = "code"; i += 2; continue
            i += 1; continue
        quote = '"' if state == "dq" else "'"
        if c == "\\":
            i += 2; continue
        if c == quote:
            state = "code"
        i += 1
    return "".join(out), state
