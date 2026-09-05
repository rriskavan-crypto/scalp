"""Qog'ozdagi (simulyatsiya) broker.

MT5 o'rnini bosadi: bir xil interfeys, lekin barlar DataFrame'idan oziqlanadi.
Shu tufayli `LiveTrader` mantig'i MT5'siz, har qanday muhitda va testlarda
to'liq tekshiriladi.

Model soddalashtirilgan, lekin savdogar foydasiga emas:
  * bozor buyrug'i ask (sotib olish) / bid (sotish) narxida to'ldiriladi;
  * SL va TP bar ichida tekshiriladi, ikkalasi ham tegilsa **SL** ustun;
  * limit order bar narxi unga tegsagina to'ldiriladi.
"""

from __future__ import annotations

import itertools

import pandas as pd

from .base import (
    OK, REJECTED, NOT_FOUND, AccountState, Broker, BrokerPosition, OrderResult,
    PendingOrder, Quote, SymbolSpec,
)


class PaperBroker(Broker):
    name = "paper"

    def __init__(self, bars: pd.DataFrame, symbol: str = "BTCUSD",
                 balance: float = 10_000.0, spread: float = 8.0,
                 spec: SymbolSpec | None = None, warmup: int = 0):
        self._bars = bars
        self._symbol = symbol
        self._i = max(warmup, 1)
        self.balance = balance
        self._spread = spread
        self._spec = spec or SymbolSpec(
            name=symbol, digits=2, point=0.01, contract_size=1.0,
            volume_min=0.01, volume_max=100.0, volume_step=0.01,
            stops_level_points=0.0,
        )
        self._positions: dict[int, BrokerPosition] = {}
        self._pending: dict[int, PendingOrder] = {}
        self._tickets = itertools.count(1_000_001)
        self.closed_trades: list[dict] = []
        self.rejections: list[str] = []

    # ------------------------------------------------------------ vaqt
    @property
    def index(self) -> int:
        return self._i

    @property
    def finished(self) -> bool:
        return self._i >= len(self._bars) - 1

    def step(self) -> bool:
        """Keyingi barga o'tadi va shu bar ichida SL/TP/limitlarni qayta ishlaydi."""
        if self.finished:
            return False
        self._i += 1
        self._process_bar()
        return True

    # ------------------------------------------------------------ ma'lumot
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...

    def account(self) -> AccountState:
        return AccountState(
            login=0, balance=self.balance, equity=self._equity(),
            margin_free=self._equity(), currency="USD", leverage=100,
            trade_allowed=True,
        )

    def symbol_spec(self, symbol: str) -> SymbolSpec:
        return self._spec

    def quote(self, symbol: str) -> Quote:
        bar = self._bars.iloc[self._i]
        mid = float(bar["close"])
        half = self._spread / 2.0
        return Quote(time=self._bars.index[self._i], bid=mid - half, ask=mid + half)

    def bars(self, symbol: str, timeframe: str = "5m", count: int = 1000) -> pd.DataFrame:
        """Faqat YOPILGAN barlarni qaytaradi — kelajakka qarash bo'lmasligi uchun."""
        lo = max(0, self._i + 1 - count)
        return self._bars.iloc[lo:self._i + 1].copy()

    def positions(self, symbol: str | None = None) -> list[BrokerPosition]:
        return [p for p in self._positions.values() if symbol in (None, p.symbol)]

    def pending_orders(self, symbol: str | None = None) -> list[PendingOrder]:
        return [o for o in self._pending.values() if symbol in (None, o.symbol)]

    # ------------------------------------------------------------ buyruqlar
    def market_order(self, symbol, side, volume, sl, tp, comment="") -> OrderResult:
        volume = self._spec.normalize_volume(volume)
        if volume <= 0:
            return self._reject("hajm minimal lotdan kichik")
        q = self.quote(symbol)
        price = q.ask if side > 0 else q.bid
        err = self._validate_stops(side, price, sl, tp)
        if err:
            return self._reject(err)

        ticket = next(self._tickets)
        self._positions[ticket] = BrokerPosition(
            ticket=ticket, symbol=symbol, side=side, volume=volume,
            entry_price=price, sl=sl, tp=tp, open_time=q.time, comment=comment,
        )
        return OrderResult(OK, ticket=ticket, price=price)

    def limit_order(self, symbol, side, volume, price, sl, tp,
                    expiry=None, comment="") -> OrderResult:
        volume = self._spec.normalize_volume(volume)
        if volume <= 0:
            return self._reject("hajm minimal lotdan kichik")
        err = self._validate_stops(side, price, sl, tp)
        if err:
            return self._reject(err)

        ticket = next(self._tickets)
        self._pending[ticket] = PendingOrder(
            ticket=ticket, symbol=symbol, side=side, volume=volume,
            price=price, sl=sl, tp=tp, expiry=expiry,
        )
        return OrderResult(OK, ticket=ticket, price=price)

    def modify_position(self, ticket, sl=None, tp=None) -> OrderResult:
        pos = self._positions.get(ticket)
        if pos is None:
            return OrderResult(NOT_FOUND, message="pozitsiya topilmadi")
        new_sl = pos.sl if sl is None else sl
        new_tp = pos.tp if tp is None else tp
        q = self.quote(pos.symbol)
        price = q.bid if pos.side > 0 else q.ask
        err = self._validate_stops(pos.side, price, new_sl, new_tp)
        if err:
            return self._reject(err)
        pos.sl, pos.tp = new_sl, new_tp
        return OrderResult(OK, ticket=ticket)

    def close_position(self, ticket, volume=None, comment="") -> OrderResult:
        pos = self._positions.get(ticket)
        if pos is None:
            return OrderResult(NOT_FOUND, message="pozitsiya topilmadi")
        q = self.quote(pos.symbol)
        price = q.bid if pos.side > 0 else q.ask
        vol = pos.volume if volume is None else self._spec.normalize_volume(volume)
        if vol <= 0:
            return self._reject("yopish hajmi minimal lotdan kichik")
        vol = min(vol, pos.volume)
        self._settle(pos, price, vol, comment or "close")
        return OrderResult(OK, ticket=ticket, price=price)

    def cancel_order(self, ticket) -> OrderResult:
        if self._pending.pop(ticket, None) is None:
            return OrderResult(NOT_FOUND, message="order topilmadi")
        return OrderResult(OK, ticket=ticket)

    # ------------------------------------------------------------ ichki
    def _reject(self, message: str) -> OrderResult:
        self.rejections.append(message)
        return OrderResult(REJECTED, message=message)

    def _validate_stops(self, side: int, price: float, sl: float, tp: float) -> str:
        """SL/TP to'g'ri tomonda va brokerning minimal masofasidan uzoqmi."""
        min_dist = self._spec.min_stop_distance()
        if sl:
            if side > 0 and sl >= price - min_dist:
                return f"long SL narxdan yuqori yoki juda yaqin ({sl} >= {price - min_dist})"
            if side < 0 and sl <= price + min_dist:
                return f"short SL narxdan past yoki juda yaqin ({sl} <= {price + min_dist})"
        if tp:
            if side > 0 and tp <= price + min_dist:
                return "long TP narxdan past yoki juda yaqin"
            if side < 0 and tp >= price - min_dist:
                return "short TP narxdan yuqori yoki juda yaqin"
        return ""

    def _equity(self) -> float:
        q_cache: dict[str, Quote] = {}
        total = self.balance
        for pos in self._positions.values():
            q = q_cache.setdefault(pos.symbol, self.quote(pos.symbol))
            price = q.bid if pos.side > 0 else q.ask
            total += pos.side * (price - pos.entry_price) * pos.volume * self._spec.contract_size
        return total

    def _settle(self, pos: BrokerPosition, price: float, volume: float, reason: str) -> None:
        pnl = pos.side * (price - pos.entry_price) * volume * self._spec.contract_size
        self.balance += pnl
        self.closed_trades.append({
            "ticket": pos.ticket, "side": pos.side, "volume": volume,
            "entry_price": pos.entry_price, "exit_price": price,
            "pnl": pnl, "reason": reason,
            "open_time": pos.open_time, "close_time": self._bars.index[self._i],
        })
        pos.volume = round(pos.volume - volume, 8)
        if pos.volume <= 1e-9:
            self._positions.pop(pos.ticket, None)

    def _process_bar(self) -> None:
        """Joriy bar ichida limitlarni to'ldiradi va SL/TP ni tekshiradi."""
        bar = self._bars.iloc[self._i]
        high, low = float(bar["high"]), float(bar["low"])
        now = self._bars.index[self._i]
        half = self._spread / 2.0

        # --- kutayotgan limitlar ---
        for ticket, order in list(self._pending.items()):
            if order.expiry is not None and now > order.expiry:
                self._pending.pop(ticket, None)
                continue
            # Long limit ask bilan to'ldiriladi -> bar pastki chegarasi ask'da
            touched = (low + half <= order.price) if order.side > 0 else (high - half >= order.price)
            if touched:
                self._pending.pop(ticket, None)
                self._positions[ticket] = BrokerPosition(
                    ticket=ticket, symbol=order.symbol, side=order.side,
                    volume=order.volume, entry_price=order.price,
                    sl=order.sl, tp=order.tp, open_time=now,
                )

        # --- ochiq pozitsiyalar: SL birinchi (pessimistik) ---
        for pos in list(self._positions.values()):
            exit_bid, exit_ask = low - half, high + half
            if pos.side > 0:
                if pos.sl and exit_bid <= pos.sl:
                    self._settle(pos, pos.sl, pos.volume, "sl"); continue
                if pos.tp and high - half >= pos.tp:
                    self._settle(pos, pos.tp, pos.volume, "tp"); continue
            else:
                if pos.sl and exit_ask >= pos.sl:
                    self._settle(pos, pos.sl, pos.volume, "sl"); continue
                if pos.tp and low + half <= pos.tp:
                    self._settle(pos, pos.tp, pos.volume, "tp"); continue
