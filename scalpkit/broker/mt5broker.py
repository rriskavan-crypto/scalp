"""MetaTrader 5 brokeri (Exness va boshqa MT5 brokerlari uchun).

TALABLAR
--------
* **Windows** — `MetaTrader5` paketi faqat Windows uchun mavjud.
* MT5 terminali **ochiq** va hisobga kirgan bo'lishi kerak.
* Terminalda: Tools → Options → Expert Advisors →
  "Allow algorithmic trading" yoqilgan bo'lishi shart.
* `pip install MetaTrader5`

Bu modul Linux/macOS da import qilinsa tushunarli xato beradi — chunki
MT5 Python API tarmoq orqali emas, **shu kompyuterdagi** terminalga
IPC orqali ulanadi.

XAVFSIZLIK
----------
Parol hech qachon faylga yozilmaydi. U `MT5_PASSWORD` muhit
o'zgaruvchisidan yoki `.env` (git'ga kirmaydigan) fayldan o'qiladi.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .base import (
    OK, REJECTED, NOT_FOUND, AccountState, Broker, BrokerPosition, OrderResult,
    PendingOrder, Quote, SymbolSpec,
)

MAGIC = 20260905          # bizning savdolarni ajratish uchun
DEFAULT_DEVIATION = 30    # maksimal sirpanish, punktda

_TIMEFRAMES = {
    "1m": "TIMEFRAME_M1", "3m": "TIMEFRAME_M3", "5m": "TIMEFRAME_M5",
    "15m": "TIMEFRAME_M15", "30m": "TIMEFRAME_M30", "1h": "TIMEFRAME_H1",
    "4h": "TIMEFRAME_H4", "1d": "TIMEFRAME_D1",
}

# Eng ko'p uchraydigan xato kodlari — tushunarli tushuntirish bilan
_RETCODE_HELP = {
    10004: "Rekvot — narx o'zgardi, qayta urinib ko'ring",
    10006: "Broker so'rovni rad etdi",
    10013: "Noto'g'ri so'rov (parametrlarni tekshiring)",
    10014: "Noto'g'ri hajm (lot qadami / min / max)",
    10015: "Noto'g'ri narx",
    10016: "Noto'g'ri SL yoki TP — narxga juda yaqin (stops level)",
    10017: "Savdo o'chirilgan",
    10018: "Bozor yopiq",
    10019: "Mablag' yetarli emas",
    10027: "Algoritmik savdo terminalda O'CHIRILGAN — "
           "Tools > Options > Expert Advisors > Allow algorithmic trading",
    10030: "To'ldirish rejimi (filling mode) qo'llab-quvvatlanmaydi",
    10031: "Terminal serverga ulanmagan",
}


def _load_env_file(path: str = ".env") -> None:
    """`.env` faylini o'qiydi (agar mavjud bo'lsa).

    Allaqachon o'rnatilgan muhit o'zgaruvchilarini BOSMAYDI — buyruq
    qatoridan berilgan qiymat har doim ustun.
    """
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass
class MT5Credentials:
    login: int
    server: str
    password: str = ""
    terminal_path: str | None = None

    @classmethod
    def from_env(cls, login: int | None = None, server: str | None = None,
                 path: str | None = None, env_file: str = ".env") -> "MT5Credentials":
        """Parolni faqat muhitdan yoki `.env` faylidan oladi — koddan emas."""
        _load_env_file(env_file)
        login = int(login or os.environ.get("MT5_LOGIN", 0))
        server = server or os.environ.get("MT5_SERVER", "")
        password = os.environ.get("MT5_PASSWORD", "")
        if not login or not server:
            raise ValueError(
                "MT5 hisob ma'lumotlari yo'q. Quyidagilarni o'rnating:\n"
                "  set MT5_LOGIN=<hisob raqamingiz>\n"
                "  set MT5_SERVER=<server nomi, masalan Exness-MT5Trial00>\n"
                "  set MT5_PASSWORD=***"
            )
        return cls(login=login, server=server, password=password,
                   terminal_path=path or os.environ.get("MT5_PATH"))


class MT5Broker(Broker):
    name = "mt5"

    def __init__(self, credentials: MT5Credentials | None = None,
                 deviation: int = DEFAULT_DEVIATION, magic: int = MAGIC,
                 dry_run: bool = True):
        self.credentials = credentials
        self.deviation = deviation
        self.magic = magic
        self.dry_run = dry_run
        self._mt5 = None
        self._server_utc_offset_hours: float = 0.0
        self._spec_cache: dict[str, SymbolSpec] = {}

    # ------------------------------------------------------------ ulanish
    def connect(self) -> None:
        try:
            import MetaTrader5 as mt5  # noqa: N813
        except ImportError as exc:
            raise RuntimeError(
                "`MetaTrader5` paketi topilmadi.\n"
                "  Bu paket FAQAT Windows uchun mavjud.\n"
                "  O'rnatish: pip install MetaTrader5\n"
                "  Linux/macOS da MT5 Python API ishlamaydi — MT5 terminali\n"
                "  bilan aloqa shu kompyuterda IPC orqali amalga oshadi."
            ) from exc
        self._mt5 = mt5

        kwargs = {}
        if self.credentials and self.credentials.terminal_path:
            kwargs["path"] = self.credentials.terminal_path
        if not mt5.initialize(**kwargs):
            raise RuntimeError(
                f"MT5 terminaliga ulanib bo'lmadi: {mt5.last_error()}\n"
                "  Terminal ochiqmi? Hisobga kirilganmi?"
            )

        if self.credentials and self.credentials.password:
            ok = mt5.login(self.credentials.login,
                           password=self.credentials.password,
                           server=self.credentials.server)
            if not ok:
                mt5.shutdown()
                raise RuntimeError(
                    f"Hisobga kirib bo'lmadi ({self.credentials.login} @ "
                    f"{self.credentials.server}): {mt5.last_error()}"
                )
        self._detect_server_time_offset()

    def disconnect(self) -> None:
        if self._mt5 is not None:
            self._mt5.shutdown()
            self._mt5 = None

    def __enter__(self) -> "MT5Broker":
        self.connect()
        return self

    def __exit__(self, *exc) -> None:
        self.disconnect()

    def _detect_server_time_offset(self) -> None:
        """Broker server vaqtining UTC dan farqini aniqlaydi.

        Bu MUHIM: seans filtri (UTC 06:00-22:00) va H1 moslash to'g'ri
        ishlashi uchun bar vaqtlari haqiqiy UTC ga keltirilishi kerak.
        Exness serverlari odatda UTC+0 yoki UTC+3 da ishlaydi.
        """
        mt5 = self._require()
        for symbol in ("BTCUSD", "EURUSD", "XAUUSD"):
            tick = mt5.symbol_info_tick(symbol)
            if tick and tick.time:
                self._server_utc_offset_hours = round((tick.time - time.time()) / 3600.0)
                return
        self._server_utc_offset_hours = 0.0

    @property
    def server_utc_offset_hours(self) -> float:
        return self._server_utc_offset_hours

    def _require(self):
        if self._mt5 is None:
            raise RuntimeError("Avval connect() chaqiring.")
        return self._mt5

    # ------------------------------------------------------------ ma'lumot
    def account(self) -> AccountState:
        mt5 = self._require()
        info = mt5.account_info()
        if info is None:
            raise RuntimeError(f"account_info() bo'sh: {mt5.last_error()}")
        return AccountState(
            login=info.login, balance=info.balance, equity=info.equity,
            margin_free=info.margin_free, currency=info.currency,
            leverage=info.leverage, trade_allowed=bool(info.trade_allowed),
        )

    def resolve_symbol(self, symbol: str) -> str:
        """Instrument nomini topadi.

        Exness'da bir xil instrument turli nomlarda bo'ladi: `BTCUSD`,
        `BTCUSDm`, `BTCUSD.raw`. Aniq nom topilmasa, o'xshashini qidiradi.
        """
        mt5 = self._require()
        if mt5.symbol_info(symbol) is not None:
            return symbol
        base = symbol.upper().replace("/", "")
        for candidate in mt5.symbols_get() or []:
            if candidate.name.upper().startswith(base):
                return candidate.name
        raise RuntimeError(
            f"'{symbol}' instrumenti topilmadi. MarketWatch'da mavjud nomni "
            f"tekshiring (masalan BTCUSD, BTCUSDm)."
        )

    def symbol_spec(self, symbol: str) -> SymbolSpec:
        if symbol in self._spec_cache:
            return self._spec_cache[symbol]
        mt5 = self._require()
        info = mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"'{symbol}' haqida ma'lumot yo'q: {mt5.last_error()}")
        if not info.visible and not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"'{symbol}' ni MarketWatch'ga qo'shib bo'lmadi.")
        info = mt5.symbol_info(symbol)

        spec = SymbolSpec(
            name=info.name, digits=info.digits, point=info.point,
            contract_size=info.trade_contract_size,
            volume_min=info.volume_min, volume_max=info.volume_max,
            volume_step=info.volume_step,
            stops_level_points=float(info.trade_stops_level),
            tick_size=getattr(info, "trade_tick_size", 0.0) or info.point,
            tick_value=getattr(info, "trade_tick_value", 0.0),
        )
        self._spec_cache[symbol] = spec
        return spec

    def quote(self, symbol: str) -> Quote:
        mt5 = self._require()
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"'{symbol}' kotirovkasi yo'q: {mt5.last_error()}")
        return Quote(
            time=self._to_utc(tick.time), bid=tick.bid, ask=tick.ask
        )

    def bars(self, symbol: str, timeframe: str = "5m", count: int = 1500) -> pd.DataFrame:
        """Yopilgan barlarni UTC vaqt bilan qaytaradi.

        Oxirgi bar hali yopilmagan bo'lgani uchun tashlab yuboriladi.
        """
        mt5 = self._require()
        tf = getattr(mt5, _TIMEFRAMES[timeframe])
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count + 1)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"'{symbol}' uchun barlar yo'q: {mt5.last_error()}")

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True) - pd.Timedelta(
            hours=self._server_utc_offset_hours
        )
        df = df.set_index("time")
        volume_col = "real_volume" if df.get("real_volume", pd.Series([0])).sum() > 0 else "tick_volume"
        out = df[["open", "high", "low", "close", volume_col]].copy()
        out.columns = ["open", "high", "low", "close", "volume"]
        return out.iloc[:-1].astype(float)   # oxirgi bar hali yopilmagan

    def _to_utc(self, server_epoch: float) -> pd.Timestamp:
        return pd.Timestamp(server_epoch, unit="s", tz="UTC") - pd.Timedelta(
            hours=self._server_utc_offset_hours
        )

    # ------------------------------------------------------------ pozitsiyalar
    def positions(self, symbol: str | None = None) -> list[BrokerPosition]:
        mt5 = self._require()
        raw = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
        out = []
        for p in raw or []:
            if p.magic and p.magic != self.magic:
                continue   # boshqa dastur/qo'l bilan ochilgan pozitsiyalarga tegmaymiz
            out.append(BrokerPosition(
                ticket=p.ticket, symbol=p.symbol,
                side=1 if p.type == mt5.POSITION_TYPE_BUY else -1,
                volume=p.volume, entry_price=p.price_open, sl=p.sl, tp=p.tp,
                open_time=self._to_utc(p.time), profit=p.profit, comment=p.comment,
            ))
        return out

    def pending_orders(self, symbol: str | None = None) -> list[PendingOrder]:
        mt5 = self._require()
        raw = mt5.orders_get(symbol=symbol) if symbol else mt5.orders_get()
        out = []
        for o in raw or []:
            if o.magic and o.magic != self.magic:
                continue
            is_buy = o.type in (mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_BUY_STOP)
            out.append(PendingOrder(
                ticket=o.ticket, symbol=o.symbol, side=1 if is_buy else -1,
                volume=o.volume_current, price=o.price_open, sl=o.sl, tp=o.tp,
                expiry=self._to_utc(o.time_expiration) if o.time_expiration else None,
            ))
        return out

    # ------------------------------------------------------------ buyruqlar
    def _filling_mode(self, symbol: str):
        """Broker qo'llab-quvvatlaydigan to'ldirish rejimini tanlaydi."""
        mt5 = self._require()
        info = mt5.symbol_info(symbol)
        mask = getattr(info, "filling_mode", 0)
        if mask & 1:      # SYMBOL_FILLING_FOK
            return mt5.ORDER_FILLING_FOK
        if mask & 2:      # SYMBOL_FILLING_IOC
            return mt5.ORDER_FILLING_IOC
        return mt5.ORDER_FILLING_RETURN

    def _send(self, request: dict, what: str) -> OrderResult:
        # Dry-run terminalga ulanishni talab qilmaydi — u faqat nima
        # yuborilishini ko'rsatadi.
        if self.dry_run:
            return OrderResult(OK, ticket=0, price=request.get("price"),
                               message=f"[DRY-RUN] {what} yuborilmadi", raw=request)
        mt5 = self._require()

        check = mt5.order_check(request)
        if check is not None and check.retcode not in (0, mt5.TRADE_RETCODE_DONE):
            return OrderResult(REJECTED, message=self._explain(check.retcode, check.comment),
                               raw=check)

        result = mt5.order_send(request)
        if result is None:
            return OrderResult(REJECTED, message=f"order_send bo'sh: {mt5.last_error()}")
        if result.retcode not in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED):
            return OrderResult(REJECTED, message=self._explain(result.retcode, result.comment),
                               raw=result)
        return OrderResult(OK, ticket=result.order or result.deal,
                           price=result.price or request.get("price"), raw=result)

    @staticmethod
    def _explain(retcode: int, comment: str = "") -> str:
        help_text = _RETCODE_HELP.get(retcode, "")
        parts = [f"retcode={retcode}"]
        if help_text:
            parts.append(help_text)
        if comment:
            parts.append(f"({comment})")
        return " — ".join(parts)

    def market_order(self, symbol, side, volume, sl, tp, comment="scalpkit") -> OrderResult:
        mt5 = self._require()
        spec = self.symbol_spec(symbol)
        volume = spec.normalize_volume(volume)
        if volume <= 0:
            return OrderResult(REJECTED, message="hajm minimal lotdan kichik")

        tick = mt5.symbol_info_tick(symbol)
        price = tick.ask if side > 0 else tick.bid
        sl, tp = self._clamp_stops(spec, side, price, sl, tp)

        return self._send({
            "action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": volume,
            "type": mt5.ORDER_TYPE_BUY if side > 0 else mt5.ORDER_TYPE_SELL,
            "price": price, "sl": sl, "tp": tp,
            "deviation": self.deviation, "magic": self.magic, "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC, "type_filling": self._filling_mode(symbol),
        }, f"{'BUY' if side > 0 else 'SELL'} {volume} {symbol} @ market")

    def limit_order(self, symbol, side, volume, price, sl, tp,
                    expiry=None, comment="scalpkit") -> OrderResult:
        mt5 = self._require()
        spec = self.symbol_spec(symbol)
        volume = spec.normalize_volume(volume)
        if volume <= 0:
            return OrderResult(REJECTED, message="hajm minimal lotdan kichik")

        price = spec.normalize_price(price)
        sl, tp = self._clamp_stops(spec, side, price, sl, tp)
        request = {
            "action": mt5.TRADE_ACTION_PENDING, "symbol": symbol, "volume": volume,
            "type": mt5.ORDER_TYPE_BUY_LIMIT if side > 0 else mt5.ORDER_TYPE_SELL_LIMIT,
            "price": price, "sl": sl, "tp": tp,
            "magic": self.magic, "comment": comment,
            "type_filling": self._filling_mode(symbol),
        }
        if expiry is not None:
            request["type_time"] = mt5.ORDER_TIME_SPECIFIED
            request["expiration"] = int(
                (expiry + pd.Timedelta(hours=self._server_utc_offset_hours)).timestamp()
            )
        else:
            request["type_time"] = mt5.ORDER_TIME_GTC
        return self._send(request, f"{'BUY' if side > 0 else 'SELL'} LIMIT {volume} @ {price}")

    def modify_position(self, ticket, sl=None, tp=None) -> OrderResult:
        mt5 = self._require()
        positions = [p for p in self.positions() if p.ticket == ticket]
        if not positions:
            return OrderResult(NOT_FOUND, message=f"pozitsiya {ticket} topilmadi")
        pos = positions[0]
        spec = self.symbol_spec(pos.symbol)
        tick = mt5.symbol_info_tick(pos.symbol)
        price = tick.bid if pos.side > 0 else tick.ask
        new_sl, new_tp = self._clamp_stops(
            spec, pos.side, price, pos.sl if sl is None else sl,
            pos.tp if tp is None else tp,
        )
        return self._send({
            "action": mt5.TRADE_ACTION_SLTP, "symbol": pos.symbol,
            "position": ticket, "sl": new_sl, "tp": new_tp, "magic": self.magic,
        }, f"SL/TP -> {new_sl}/{new_tp}")

    def close_position(self, ticket, volume=None, comment="scalpkit-close") -> OrderResult:
        mt5 = self._require()
        positions = [p for p in self.positions() if p.ticket == ticket]
        if not positions:
            return OrderResult(NOT_FOUND, message=f"pozitsiya {ticket} topilmadi")
        pos = positions[0]
        spec = self.symbol_spec(pos.symbol)
        vol = pos.volume if volume is None else spec.normalize_volume(volume)
        if vol <= 0:
            return OrderResult(REJECTED, message="yopish hajmi minimal lotdan kichik")
        vol = min(vol, pos.volume)

        tick = mt5.symbol_info_tick(pos.symbol)
        return self._send({
            "action": mt5.TRADE_ACTION_DEAL, "symbol": pos.symbol, "volume": vol,
            "type": mt5.ORDER_TYPE_SELL if pos.side > 0 else mt5.ORDER_TYPE_BUY,
            "position": ticket,
            "price": tick.bid if pos.side > 0 else tick.ask,
            "deviation": self.deviation, "magic": self.magic, "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC, "type_filling": self._filling_mode(pos.symbol),
        }, f"CLOSE {vol} of #{ticket}")

    def cancel_order(self, ticket) -> OrderResult:
        mt5 = self._require()
        return self._send(
            {"action": mt5.TRADE_ACTION_REMOVE, "order": ticket}, f"CANCEL #{ticket}"
        )

    # ------------------------------------------------------------ yordamchi
    @staticmethod
    def _clamp_stops(spec: SymbolSpec, side: int, price: float,
                     sl: float, tp: float) -> tuple[float, float]:
        """SL/TP ni brokerning minimal masofasiga moslaydi.

        Aks holda broker 10016 ("Invalid stops") xatosi bilan rad etadi —
        MT5 da eng ko'p uchraydigan muammo. Chegarada turib qolmaslik uchun
        bir punkt zaxira qo'shiladi.
        """
        min_dist = max(spec.min_stop_distance(), spec.point) + spec.point
        if sl:
            limit = price - side * min_dist
            sl = min(sl, limit) if side > 0 else max(sl, limit)
            sl = spec.normalize_price(sl)
        if tp:
            limit = price + side * min_dist
            tp = max(tp, limit) if side > 0 else min(tp, limit)
            tp = spec.normalize_price(tp)
        return sl or 0.0, tp or 0.0
