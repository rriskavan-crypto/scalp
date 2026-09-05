"""Xarajat modeli: komissiya, sirpanish (slippage) va funding."""

from __future__ import annotations

import pandas as pd

from ..config import CostConfig

BPS = 1e-4
FUNDING_HOURS = (0, 8, 16)  # Binance perpetual funding vaqtlari (UTC)


def fill_price(price: float, side: int, is_exit: bool, cost: CostConfig, is_stop: bool = False) -> float:
    """Sirpanishni hisobga olgan haqiqiy ijro narxi.

    Sirpanish har doim savdogarga qarshi ishlaydi: long kirishda yuqoriroq,
    long chiqishda pastroq.
    """
    slip = (cost.stop_slippage_bps if is_stop else cost.slippage_bps) * BPS
    direction = -side if is_exit else side  # chiqishda pozitsiya teskari yopiladi
    return price * (1.0 + direction * slip)


def fee_for(notional: float, cost: CostConfig, is_exit: bool, forced_taker: bool = False) -> float:
    """Bitta tomon uchun komissiya (mutlaq qiymat, USD)."""
    maker = (cost.exit_is_maker if is_exit else cost.entry_is_maker) and not forced_taker
    bps = cost.maker_fee_bps if maker else cost.taker_fee_bps
    return abs(notional) * bps * BPS


def funding_events(start: pd.Timestamp, end: pd.Timestamp) -> int:
    """Pozitsiya ochiq turgan davrda nechta funding to'lovi bo'lganini sanaydi."""
    if end <= start:
        return 0
    count = 0
    cursor = start.ceil("h")
    while cursor <= end:
        if cursor.hour in FUNDING_HOURS and cursor > start:
            count += 1
        cursor += pd.Timedelta(hours=1)
    return count


def funding_cost(notional: float, side: int, bars: int, start: pd.Timestamp,
                 end: pd.Timestamp, cost: CostConfig) -> float:
    """Funding to'lovi. Soddalashtirilgan: long doim to'laydi (musbat rate)."""
    if not cost.apply_funding:
        return 0.0
    n = funding_events(start, end)
    return n * abs(notional) * cost.funding_rate_8h * (1.0 if side > 0 else -1.0)
