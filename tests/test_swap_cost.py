"""Ushlab turish (swap) xarajati — swing savdosining ikkinchi katta xarajati.

Skalpingda pozitsiya daqiqalar turadi va swap nolga teng. Swing'da esa
D1 pozitsiyasi o'rtacha ~18 kun ochiq qoladi va swap R ning chorak
qismini yeb qo'yishi mumkin. Bu modul uni ikkala tomonda ham qulflab
qo'yadi: Python hisob-kitobi va MQL5 filtri bir xil arifmetikaga tayanadi.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scalpkit.config import CostConfig                          # noqa: E402
from scalpkit.engine.broker import (funding_cost, swap_cost,    # noqa: E402
                                    swap_nights, swap_units)
from scalpkit.profiles import (XAUUSD, expected_hold_days,      # noqa: E402
                               for_timeframe)
from scalpkit.config import Config                              # noqa: E402
from scalpkit.strategies import get_strategy                    # noqa: E402

CORE = ROOT / "mql5" / "Include" / "ScalpKit" / "Core.mqh"
MON = pd.Timestamp("2026-09-07")          # dushanba


# ------------------------------------------------------------------ #
#  Uch baravar rollover
# ------------------------------------------------------------------ #
def test_a_single_night_is_charged_once():
    assert swap_units(MON, MON + pd.Timedelta(days=1)) == 1.0


def test_crossing_wednesday_charges_three_nights():
    """Dushanbadan payshanbagacha: 3 kecha, lekin chorshanba x3 => 5 birlik."""
    assert swap_nights(MON, MON + pd.Timedelta(days=3)) == 3
    assert swap_units(MON, MON + pd.Timedelta(days=3)) == 5.0


def test_a_week_costs_nine_units_not_seven():
    assert swap_units(MON, MON + pd.Timedelta(days=7)) == 9.0


@pytest.mark.parametrize("days", [7, 14, 21, 28, 70])
def test_long_holds_cost_nine_sevenths_of_the_naive_count(days):
    """MQL5 filtri aynan shu 9/7 ko'paytmasidan foydalanadi."""
    assert swap_units(MON, MON + pd.Timedelta(days=days)) == days * 9.0 / 7.0


def test_intraday_holds_pay_nothing():
    start = MON + pd.Timedelta(hours=9)
    assert swap_units(start, start + pd.Timedelta(hours=6)) == 0.0


def test_the_triple_day_is_configurable():
    """Ba'zi brokerlar juma yoki payshanbani tanlaydi."""
    got = swap_units(MON, MON + pd.Timedelta(days=7), rollover3_dow=4)
    assert got == 9.0
    flat = swap_units(MON, MON + pd.Timedelta(days=7), rollover3_mult=1.0)
    assert flat == 7.0


# ------------------------------------------------------------------ #
#  Xarajatga aylantirish
# ------------------------------------------------------------------ #
def gold_cost() -> CostConfig:
    c = CostConfig()
    for key, value in XAUUSD.cost.items():
        setattr(c, key, value)
    return c


def test_gold_long_pays_swap_and_short_receives_it():
    cost = gold_cost()
    end = MON + pd.Timedelta(days=7)
    assert swap_cost(10_000.0, +1, MON, end, cost) > 0.0
    assert swap_cost(10_000.0, -1, MON, end, cost) < 0.0


def test_swap_is_ignored_when_the_profile_disables_it():
    cost = gold_cost()
    cost.apply_swap = False
    cost.apply_funding = False
    assert funding_cost(10_000.0, +1, 100, MON, MON + pd.Timedelta(days=7), cost) == 0.0


def swap_cost_r(tf: str, strategy_name: str, tightest: bool = True) -> float:
    """Long pozitsiya uchun swapning R dagi bahosi.

    `tightest=True` — eng tor ruxsat etilgan stop (`min_stop_pct`), ya'ni
    ENG YOMON holat; EA filtri aynan shu chegarada qaror qabul qiladi.
    `tightest=False` — odatiy stop (1.5 x eng past ATR).
    """
    profile = for_timeframe(XAUUSD, tf)
    cfg = profile.apply(Config(), strategy_name)
    params = get_strategy(strategy_name, cfg.strategy.params).params
    units = expected_hold_days(tf, strategy_name, params) * 9.0 / 7.0
    swap_pct = units * profile.cost["swap_pct_per_day_long"]
    stop_pct = (cfg.risk.min_stop_pct if tightest
                else 1.5 * float(params["min_atr_pct"]))
    return swap_pct / stop_pct


def test_daily_swing_swap_eats_a_large_share_of_one_r():
    """Bu butun o'zgarishning sababi — raqam bilan qulflab qo'yamiz.

    Oltin D1: o'rtacha ushlash ~17.5 kun, swap 0.012 %/kun. Uch baravar
    rollover bilan 22.5 birlik = 0.27 % notional. Eng tor ruxsat etilgan
    stopda (0.756 %) bu 0.36 R, odatiy stopda (1.28 %) 0.21 R.

    MUHIM: bu LONG uchun eng yomon holat, o'rtacha savdo emas. Sintetik
    ma'lumotda o'lchangan haqiqiy o'rtacha ancha past — 0.058 R, chunki
    (a) savdolarning yarmi short va short swapni OLADI, (b) haqiqiy stop
    masofasi eng tor chegaradan kengroq chiqadi. Ya'ni bu raqam filtr
    qaror qabul qiladigan nuqtani tasvirlaydi, natijaga o'rtacha ta'sirni
    emas — o'sha ta'sir `swap_rollover3_mult` o'lchovida -0.010 R.
    """
    tight = swap_cost_r("1d", "donchian_breakout", tightest=True)
    usual = swap_cost_r("1d", "donchian_breakout", tightest=False)
    assert 0.30 < tight < 0.45, f"eng tor stopda {tight:.3f} R"
    assert 0.15 < usual < 0.30, f"odatiy stopda {usual:.3f} R"


def test_swap_burden_grows_monotonically_with_timeframe():
    """M5 dan D1 ga o'tganda swap ~27 barobar qimmatlashadi.

    Spread esa aksincha arzonlashadi. Swing'ning xarajat afzalligi
    shuning uchun cheksiz emas — u D1 da qaytadan yo'qola boshlaydi.
    """
    got = [swap_cost_r(tf, strat) for tf, strat in
           (("5m", "momentum_pullback"), ("15m", "momentum_pullback"),
            ("1h", "donchian_breakout"), ("4h", "donchian_breakout"),
            ("1d", "donchian_breakout"))]
    assert got == sorted(got), got
    assert got[-1] / got[0] > 20.0, f"D1/M5 nisbati {got[-1] / got[0]:.1f}"


def test_scalping_swap_stays_small():
    """M5 da swap 0.02 R dan past — u yerda spread hukmronlik qiladi."""
    assert swap_cost_r("5m", "momentum_pullback") < 0.02


def test_crypto_swap_is_configured_separately_from_gold():
    """BTC 24/7 va perpetual funding modeliga yaqin — bir xil raqam emas."""
    from scalpkit.profiles import BTCUSD
    assert BTCUSD.cost.get("swap_pct_per_day_long") != \
        XAUUSD.cost.get("swap_pct_per_day_long") or \
        BTCUSD.cost.get("apply_funding") != XAUUSD.cost.get("apply_funding")


# ------------------------------------------------------------------ #
#  MQL5 tomoni bilan parity
# ------------------------------------------------------------------ #
def test_mql5_uses_the_same_rollover_factor():
    src = CORE.read_text("utf-8")
    assert "9.0 / 7.0" in src, "MQL5 uch baravar rolloverni hisobga olmayapti"


def test_mql5_cost_gate_includes_swap():
    src = CORE.read_text("utf-8")
    gate = re.search(r"double swapCost = ExpectedSwapPerUnit\(sig\.side\);\s*"
                     r"double costR\s*=\s*\(spread \+ swapCost\) / dist;", src)
    assert gate, "xarajat filtri swapni qo'shmayapti"


def test_mql5_never_counts_swap_income_as_a_discount():
    """Filtr ehtiyotkor bo'lishi kerak: daromadni oldindan yozib qo'ymaydi."""
    src = CORE.read_text("utf-8")
    body = re.search(r"double ExpectedSwapPerUnit\(const int side\)\s*\{(.*?)\n\}",
                     src, re.S)
    assert body, "ExpectedSwapPerUnit topilmadi"
    assert "if(perNight <= 0.0)" in body.group(1)


def test_mql5_handles_every_common_swap_mode():
    src = CORE.read_text("utf-8")
    for mode in ("SYMBOL_SWAP_MODE_POINTS", "SYMBOL_SWAP_MODE_INTEREST_CURRENT",
                 "SYMBOL_SWAP_MODE_INTEREST_OPEN", "SYMBOL_SWAP_MODE_CURRENCY_SYMBOL",
                 "SYMBOL_SWAP_MODE_CURRENCY_MARGIN", "SYMBOL_SWAP_MODE_CURRENCY_DEPOSIT",
                 "SYMBOL_SWAP_MODE_DISABLED"):
        assert mode in src, f"{mode} ishlanmagan"


def test_swap_can_be_switched_off_from_the_expert():
    src = CORE.read_text("utf-8")
    assert "if(!g_cfg.ApplySwapCost || g_cfg.ExpectedHoldDays <= 0.0)" in src


# ------------------------------------------------------------------ #
#  Filtr hech bir konfiguratsiyani jimgina o'chirib qo'ymasin
# ------------------------------------------------------------------ #
SHIPPED = [(sym, tf, strat)
           for sym in ("btcusd", "xauusd")
           for tf, strat in (("5m", "momentum_pullback"),
                             ("15m", "momentum_pullback"),
                             ("15m", "donchian_breakout"),
                             ("1h", "donchian_breakout"),
                             ("4h", "donchian_breakout"),
                             ("1d", "donchian_breakout"),
                             ("15m", "range_reversion"),
                             ("1h", "range_reversion"))]


@pytest.mark.parametrize("sym,tf,strategy_name", SHIPPED,
                         ids=[f"{s}-{tf}-{k}" for s, tf, k in SHIPPED])
def test_the_new_gate_never_blocks_a_typical_trade(sym, tf, strategy_name):
    """Xarajat filtriga swap qo'shildi — u ish beradigan sozlamani o'ldirmasin.

    Yangi filtrning eng jiddiy xavfi shu: juda ehtiyotkor baho qo'yilsa,
    EA hech qachon savdo ochmaydi va foydalanuvchi buni "strategiya
    ishlamadi" deb o'qiydi. Shuning uchun odatiy stop masofasida
    (1.5 x eng past ATR) spread + swap `MaxCostR` dan past bo'lishi shart.
    """
    from scalpkit.profiles import PROFILES

    profile = for_timeframe(PROFILES[sym], tf)
    cfg = profile.apply(Config(), strategy_name)
    params = get_strategy(strategy_name, cfg.strategy.params).params

    stop_price = 1.5 * float(params["min_atr_pct"]) * profile.typical_price
    spread_r = profile.typical_spread / stop_price

    units = expected_hold_days(tf, strategy_name, params) * 9.0 / 7.0
    swap_r = (units * profile.cost.get("swap_pct_per_day_long", 0.0)
              * profile.typical_price / stop_price)

    total = spread_r + swap_r
    assert total < 0.40, (
        f"{sym}/{tf}/{strategy_name}: spread {spread_r:.3f}R + "
        f"swap {swap_r:.3f}R = {total:.3f}R >= MaxCostR 0.40 — "
        f"bu sozlama hech qachon savdo ochmaydi")
