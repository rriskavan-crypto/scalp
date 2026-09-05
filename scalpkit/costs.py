"""Xarajat matematikasi — M5 skalpingda hamma narsani hal qiladigan blok.

Asosiy tenglama
---------------
Komissiya va sirpanish **notional** dan olinadi, foyda esa **R** (stop masofasi)
bilan o'lchanadi. Demak bitta savdoning xarajati R birligida:

    cost_R = round_trip_cost_pct / stop_distance_pct

Misol: to'liq savdo 0.145 %, stop masofasi 0.20 % bo'lsa -> cost = 0.725 R.
Bunday tizim yutqazishga mahkum: har savdoda 0.725R yalpi ustunlik kerak,
bunday ustunlik M5 da mavjud emas.

Xuddi shu 0.145 % stop masofasi 0.60 % bo'lganda atigi 0.24 R ni yeydi.
**Xulosa: M5 da "tez, kichik" skalping emas, "tanlab, kengroq" skalping ishlaydi.**
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import CostConfig


def round_trip_pct(cost: CostConfig) -> float:
    """Bitta to'liq savdoning narxi, notionalga nisbatan ulush."""
    return cost.round_trip_bps() * 1e-4


def cost_in_r(cost: CostConfig, stop_pct: float) -> float:
    """Xarajat R birligida."""
    return round_trip_pct(cost) / stop_pct if stop_pct > 0 else np.inf


def breakeven_win_rate(payoff_ratio: float, cost_r: float = 0.0) -> float:
    """Zararsizlik uchun kerakli g'alaba foizi.

    p * W = (1 - p) * L, bu yerda W = payoff - cost_r, L = 1 + cost_r
    """
    win_r = payoff_ratio - cost_r
    loss_r = 1.0 + cost_r
    if win_r + loss_r <= 0:
        return np.nan
    return loss_r / (win_r + loss_r)


def required_gross_edge_r(cost: CostConfig, stop_pct: float,
                          target_net_r: float = 0.10) -> float:
    """Kerakli sof foyda uchun qancha yalpi ustunlik kerakligi."""
    return target_net_r + cost_in_r(cost, stop_pct)


def min_stop_pct(cost: CostConfig, cost_budget_r: float = 0.25) -> float:
    """Xarajat berilgan R byudjetidan oshmasligi uchun minimal stop masofasi."""
    return round_trip_pct(cost) / cost_budget_r


def cost_table(cost: CostConfig,
               stop_pcts: list[float] | None = None,
               payoffs: list[float] | None = None) -> pd.DataFrame:
    """Stop masofasi bo'yicha xarajat va kerakli g'alaba foizi jadvali."""
    stop_pcts = stop_pcts or [0.0015, 0.0020, 0.0030, 0.0040, 0.0050,
                              0.0060, 0.0080, 0.0100, 0.0150]
    payoffs = payoffs or [1.0, 1.5, 2.0, 2.5]

    rows = []
    for sp in stop_pcts:
        c_r = cost_in_r(cost, sp)
        row = {"stop_pct": sp * 100.0, "cost_R": c_r}
        for pf in payoffs:
            row[f"WR@{pf:g}R"] = breakeven_win_rate(pf, c_r) * 100.0
        rows.append(row)
    return pd.DataFrame(rows).set_index("stop_pct")


def fee_tier_comparison(base: CostConfig | None = None) -> pd.DataFrame:
    """Turli komissiya tariflarida bitta savdoning narxi (0.50 % stop uchun)."""
    base = base or CostConfig()
    tiers = {
        "VIP0 taker/taker": dict(taker_fee_bps=5.0, entry_is_maker=False, exit_is_maker=False),
        "VIP0 + BNB (-10%)": dict(taker_fee_bps=4.5, entry_is_maker=False, exit_is_maker=False),
        "VIP0 maker kirish": dict(taker_fee_bps=5.0, maker_fee_bps=2.0, entry_is_maker=True),
        "VIP1 taker/taker": dict(taker_fee_bps=4.0, entry_is_maker=False, exit_is_maker=False),
        "VIP3 maker kirish": dict(taker_fee_bps=3.0, maker_fee_bps=1.5, entry_is_maker=True),
    }
    rows = []
    for name, kw in tiers.items():
        c = CostConfig(**{**base.__dict__, **kw})
        rows.append({
            "tarif": name,
            "to`liq savdo %": round_trip_pct(c) * 100.0,
            "cost_R @0.50% stop": cost_in_r(c, 0.005),
            "min stop (0.25R)": min_stop_pct(c, 0.25) * 100.0,
        })
    return pd.DataFrame(rows).set_index("tarif")


def edge_needed_report(cost: CostConfig, trades_per_day: float = 3.0) -> pd.DataFrame:
    """Turli ustunlik darajalarida yillik natija (0.5 % risk, qayta investitsiyasiz)."""
    rows = []
    for edge_r in [0.0, 0.05, 0.10, 0.15, 0.20, 0.30]:
        per_year = edge_r * trades_per_day * 365.0
        rows.append({
            "ustunlik (R/savdo)": edge_r,
            "R / yil": per_year,
            "foyda @0.5% risk": per_year * 0.005 * 100.0,
            "foyda @1.0% risk": per_year * 0.010 * 100.0,
        })
    return pd.DataFrame(rows).set_index("ustunlik (R/savdo)")


# ---------------------------------------------------------------------------
# MT5 / Exness uchun xarajat modeli
# ---------------------------------------------------------------------------
# MUHIM FARQ: Binance futures'da xarajat asosan **komissiya**dan iborat.
# Exness kabi MT5 brokerlarida standart hisobda komissiya odatda yo'q —
# butun xarajat **spread**ga singdirilgan. Shuning uchun bu yerda boshqa
# formula ishlatiladi:
#
#     bir tomonlama xarajat = spread (siz ask'da olib, bid'da sotasiz)
#     to'liq savdo          = 2 x spread + komissiya (agar bor bo'lsa)
#
# BTCUSD spreadi Exness'da hisob turiga qarab keskin farq qiladi va
# volatillikda kengayadi. Shuning uchun uni **jonli o'lchash** kerak.

def mt5_round_trip_cost(spread: float, commission_per_lot: float = 0.0,
                        contract_size: float = 1.0, price: float = 1.0,
                        extra_slippage: float = 0.0) -> float:
    """MT5 da bitta to'liq savdoning narxi (narx birligida, 1 birlik uchun).

    spread              — joriy ask - bid
    commission_per_lot  — hisobga qarab (Raw/Zero hisoblarda bor)
    """
    commission_per_unit = (
        commission_per_lot / contract_size if contract_size > 0 else 0.0
    )
    return 2.0 * spread + 2.0 * commission_per_unit + extra_slippage


def mt5_cost_in_r(spread: float, stop_distance: float, **kwargs) -> float:
    """MT5 xarajati R birligida — savdo qilish arziydimi yoki yo'qmi shu hal qiladi."""
    if stop_distance <= 0:
        return float("inf")
    return mt5_round_trip_cost(spread, **kwargs) / stop_distance


def mt5_spread_report(spread: float, price: float, atr: float,
                      sl_atr_mult: float = 1.6,
                      commission_per_lot: float = 0.0,
                      contract_size: float = 1.0) -> pd.DataFrame:
    """Joriy spread bilan turli stop masofalarida xarajat jadvali."""
    rows = []
    for mult in (1.0, 1.3, 1.6, 2.0, 2.5):
        dist = mult * atr
        cost_r = mt5_cost_in_r(spread, dist, commission_per_lot=commission_per_lot,
                               contract_size=contract_size)
        rows.append({
            "stop (ATR)": mult,
            "stop (narx)": dist,
            "stop (% narxdan)": dist / price * 100.0 if price else float("nan"),
            "xarajat (R)": cost_r,
            "zararsizlik @2R": breakeven_win_rate(2.0, cost_r) * 100.0,
        })
    return pd.DataFrame(rows).set_index("stop (ATR)")


def verdict_for_cost_r(cost_r: float) -> str:
    """Xarajat darajasiga qarab qisqa xulosa."""
    if cost_r <= 0.20:
        return "YAXSHI — bu spread bilan savdo qilish mumkin"
    if cost_r <= 0.30:
        return "QABUL QILARLI — ustunlik ingichka bo'lsa yo'qoladi"
    if cost_r <= 0.40:
        return "CHEGARADA — faqat kuchli signallarda"
    return "JUDA QIMMAT — bu spread bilan savdo qilmang"
