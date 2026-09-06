"""Broker interfeysi.

Ikkita amalga oshirish bor:
  * `PaperBroker` — simulyator. Har qanday muhitda ishlaydi va testlar bilan
    qoplangan, shuning uchun savdo mantig'i MT5'siz ham tekshiriladi.
  * `MT5Broker`   — haqiqiy MetaTrader 5 (faqat Windows, terminal ochiq bo'lishi kerak).

Ikkalasi bir xil interfeysni beradi, shuning uchun `LiveTrader` qaysi biri
bilan ishlayotganini bilmaydi — bu dry-run va real savdoni bir xil kod
yo'li bilan sinashga imkon beradi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

# --- natija kodlari ---
OK = "ok"
REJECTED = "rejected"
NOT_FOUND = "not_found"


@dataclass
class SymbolSpec:
    """Instrument texnik xususiyatlari — hajmni to'g'ri hisoblash uchun zarur."""

    name: str
    digits: int
    point: float
    contract_size: float        # 1 lot nechta birlik (BTCUSD uchun odatda 1.0)
    volume_min: float
    volume_max: float
    volume_step: float
    stops_level_points: float   # SL/TP narxdan shuncha punkt uzoq bo'lishi shart
    tick_size: float = 0.0
    tick_value: float = 0.0
    # Swap — swing savdosining ikkinchi katta xarajati. Broker qiymatlari:
    # manfiy = sizdan undiriladi, musbat = sizga to'lanadi.
    swap_long: float = 0.0
    swap_short: float = 0.0
    swap_mode: int = 0              # ENUM_SYMBOL_SWAP_MODE
    swap_rollover3days: int = 3     # 0=yakshanba ... 3=chorshanba (MT5 tartibi)

    def swap_pct_per_day(self, side: int, price: float) -> float | None:
        """Kechalik swapni narx ulushiga aylantiradi (musbat = xarajat).

        `None` — swap rejimi modellashtirilmagan (REOPEN_*). MQL5 tomonida
        `SwapPerUnitPerNight()` aynan shu hisobni bajaradi.
        """
        SWAP_DISABLED, SWAP_POINTS = 0, 1
        SWAP_CURRENCY = (2, 3, 4)          # SYMBOL, MARGIN, DEPOSIT
        SWAP_INTEREST = (5, 6)             # CURRENT, OPEN

        if self.swap_mode == SWAP_DISABLED or price <= 0:
            return 0.0
        raw = self.swap_long if side > 0 else self.swap_short
        cost = -raw                        # brokerda manfiy = undiriladi
        if self.swap_mode == SWAP_POINTS:
            return cost * self.point / price
        if self.swap_mode in SWAP_INTEREST:
            return cost / 100.0 / 360.0
        if self.swap_mode in SWAP_CURRENCY:
            contract = self.contract_size or 1.0
            return cost / contract / price
        return None

    def normalize_volume(self, volume: float) -> float:
        """Hajmni broker qadamiga moslaydi (pastga qarab yaxlitlaydi)."""
        if volume <= 0 or self.volume_step <= 0:
            return 0.0
        steps = int(volume / self.volume_step + 1e-9)
        vol = steps * self.volume_step
        vol = min(vol, self.volume_max)
        # Kichik xato to'planishini oldini olish uchun qadamga qarab yaxlitlash
        decimals = max(0, len(f"{self.volume_step:.8f}".rstrip("0").split(".")[-1]))
        vol = round(vol, decimals)
        return vol if vol >= self.volume_min - 1e-12 else 0.0

    def normalize_price(self, price: float) -> float:
        return round(price, self.digits)

    def min_stop_distance(self) -> float:
        """SL/TP uchun brokerning minimal masofasi (narx birligida)."""
        return self.stops_level_points * self.point


@dataclass
class AccountState:
    login: int
    balance: float
    equity: float
    margin_free: float
    currency: str
    leverage: int
    trade_allowed: bool


@dataclass
class Quote:
    time: pd.Timestamp
    bid: float
    ask: float

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0

    @property
    def spread(self) -> float:
        return self.ask - self.bid


@dataclass
class BrokerPosition:
    ticket: int
    symbol: str
    side: int            # +1 long, -1 short
    volume: float        # lot
    entry_price: float
    sl: float
    tp: float
    open_time: pd.Timestamp
    profit: float = 0.0
    comment: str = ""


@dataclass
class PendingOrder:
    ticket: int
    symbol: str
    side: int
    volume: float
    price: float
    sl: float
    tp: float
    expiry: pd.Timestamp | None = None


@dataclass
class OrderResult:
    status: str
    ticket: int | None = None
    price: float | None = None
    message: str = ""
    raw: Any = None

    @property
    def ok(self) -> bool:
        return self.status == OK


class Broker:
    """Umumiy interfeys. Barcha narxlar instrument narx birligida."""

    name = "base"

    # --- ma'lumot ---
    def connect(self) -> None: raise NotImplementedError
    def disconnect(self) -> None: raise NotImplementedError
    def account(self) -> AccountState: raise NotImplementedError
    def symbol_spec(self, symbol: str) -> SymbolSpec: raise NotImplementedError
    def quote(self, symbol: str) -> Quote: raise NotImplementedError
    def bars(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        raise NotImplementedError

    # --- pozitsiyalar ---
    def positions(self, symbol: str | None = None) -> list[BrokerPosition]:
        raise NotImplementedError
    def pending_orders(self, symbol: str | None = None) -> list[PendingOrder]:
        raise NotImplementedError

    # --- buyruqlar ---
    def market_order(self, symbol: str, side: int, volume: float,
                     sl: float, tp: float, comment: str = "") -> OrderResult:
        raise NotImplementedError
    def limit_order(self, symbol: str, side: int, volume: float, price: float,
                    sl: float, tp: float, expiry: pd.Timestamp | None = None,
                    comment: str = "") -> OrderResult:
        raise NotImplementedError
    def modify_position(self, ticket: int, sl: float | None = None,
                        tp: float | None = None) -> OrderResult:
        raise NotImplementedError
    def close_position(self, ticket: int, volume: float | None = None,
                       comment: str = "") -> OrderResult:
        raise NotImplementedError
    def cancel_order(self, ticket: int) -> OrderResult:
        raise NotImplementedError
