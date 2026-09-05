"""Jonli savdo sikli — strategiya, broker va riskni bog'laydi.

Ishlash tartibi (har yangi YOPILGAN M5 bar uchun bir marta):

  1. Brokerdan barlarni oladi (faqat yopilganlarini)
  2. Ochiq pozitsiyani boshqaradi: TP1, stopni surish, trailing, vaqt stopi
  3. Muddati o'tgan kutayotgan orderlarni bekor qiladi
  4. Yangi signal bo'lsa va risk ruxsat bersa — order qo'yadi

Holat (`state.json`) diskda saqlanadi, shuning uchun dastur qayta
ishga tushsa ham ochiq savdoni to'g'ri davom ettiradi.

XAVFSIZLIK: standart holatda `dry_run=True` — hech qanday order
yuborilmaydi, faqat nima qilinishi kerakligi ko'rsatiladi.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .broker.base import Broker, SymbolSpec
from .config import Config
from .features import build_features
from .risk import RiskManager
from .strategies import Strategy, get_strategy

BAR_MINUTES = 5


@dataclass
class TradeState:
    """Bitta savdo haqidagi ma'lumot — MT5 pozitsiyasida saqlanmaydi."""

    ticket: int
    side: int
    entry_price: float
    risk_per_unit: float          # R, narx birligida
    initial_volume: float
    atr_at_entry: float
    entry_time: str               # ISO
    tp1_done: bool = False
    be_moved: bool = False
    best_price: float = 0.0
    pending: bool = False         # hali to'ldirilmagan limit order


@dataclass
class TraderState:
    trades: dict[str, TradeState] = field(default_factory=dict)
    day: str = ""
    trades_today: int = 0
    day_start_equity: float = 0.0
    consecutive_losses: int = 0
    blocked_until: str = ""
    last_bar: str = ""

    def to_json(self) -> str:
        raw = asdict(self)
        raw["trades"] = {k: asdict(v) if not isinstance(v, dict) else v
                         for k, v in self.trades.items()}
        return json.dumps(raw, indent=2)

    @classmethod
    def load(cls, path: Path) -> "TraderState":
        if not path.exists():
            return cls()
        raw = json.loads(path.read_text(encoding="utf-8"))
        trades = {k: TradeState(**v) for k, v in (raw.pop("trades", {}) or {}).items()}
        return cls(trades=trades, **raw)


class LiveTrader:
    def __init__(self, broker: Broker, cfg: Config, symbol: str,
                 strategy: Strategy | None = None,
                 state_path: str | Path = "state/live_state.json",
                 dry_run: bool = True, verbose: bool = True):
        self.broker = broker
        self.cfg = cfg
        self.symbol = symbol
        self.strategy = strategy or get_strategy(cfg.strategy.name, cfg.strategy.params)
        self.state_path = Path(state_path)
        self.dry_run = dry_run
        self.verbose = verbose
        self.state = TraderState.load(self.state_path)
        self.risk = RiskManager(cfg.risk)
        self.log: list[str] = []

    # ------------------------------------------------------------ log
    def _say(self, message: str) -> None:
        self.log.append(message)
        if self.verbose:
            print(message)

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(self.state.to_json(), encoding="utf-8")

    # ------------------------------------------------------------ asosiy sikl
    def run_once(self, bars: pd.DataFrame | None = None) -> dict:
        """Bitta iteratsiya. Nima qilinganini lug'at sifatida qaytaradi."""
        p = self.strategy.params
        bars = bars if bars is not None else self.broker.bars(
            self.symbol, self.cfg.timeframe, count=1200
        )
        if len(bars) < 300:
            self._say(f"Barlar yetarli emas ({len(bars)}) — kutilmoqda.")
            return {"action": "wait", "reason": "insufficient_bars"}

        bar_time = bars.index[-1]
        account = self.broker.account()
        spec = self.broker.symbol_spec(self.symbol)
        self._roll_day(bar_time, account.equity)

        features = build_features(bars)
        signals = self.strategy.generate(features)

        result = {"bar": str(bar_time), "equity": account.equity, "action": "none"}

        # --- 1) ochiq pozitsiyalarni boshqarish ---
        managed = self._manage_open(features, spec, bar_time)
        if managed:
            result["managed"] = managed

        # --- 2) muddati o'tgan limitlarni tozalash ---
        self._expire_pending(bar_time, int(p.get("entry_limit_bars", 3)))

        # --- 3) yangi signal ---
        if self.broker.positions(self.symbol) or self.broker.pending_orders(self.symbol):
            result["action"] = "holding"
            self._save()
            return result

        side = int(signals["signal"].iloc[-1])
        if side == 0:
            result["action"] = "no_signal"
            self._save()
            return result

        blocked = self._risk_block(bar_time, account.equity)
        if blocked:
            self._say(f"SIGNAL BOR ({'LONG' if side > 0 else 'SHORT'}), lekin bloklangan: {blocked}")
            result.update(action="blocked", reason=blocked)
            self._save()
            return result

        placed = self._open_trade(side, features, signals, spec, account.equity, bar_time)
        result.update(placed)
        self._save()
        return result

    # ------------------------------------------------------------ pozitsiya boshqaruvi
    def _manage_open(self, features: pd.DataFrame, spec: SymbolSpec,
                     bar_time: pd.Timestamp) -> list[dict]:
        p = self.strategy.params
        actions: list[dict] = []
        live_tickets = set()

        for pos in self.broker.positions(self.symbol):
            live_tickets.add(str(pos.ticket))
            st = self.state.trades.get(str(pos.ticket))
            if st is None:
                # Holat yo'qolgan (dastur qayta ishga tushgan) — SL dan tiklaymiz
                st = self._recover_state(pos, features)
                self.state.trades[str(pos.ticket)] = st
                self._say(f"#{pos.ticket} holati SL asosida tiklandi.")

            st.pending = False
            quote = self.broker.quote(self.symbol)
            price = quote.bid if pos.side > 0 else quote.ask
            st.best_price = (max(st.best_price or price, price) if pos.side > 0
                             else min(st.best_price or price, price))
            R = st.risk_per_unit
            move_r = pos.side * (st.best_price - st.entry_price) / R if R > 0 else 0.0
            now_r = pos.side * (price - st.entry_price) / R if R > 0 else 0.0

            # --- TP1: qisman yopish ---
            tp1_r = float(p.get("tp1_r", 1.5))
            if not st.tp1_done and now_r >= tp1_r:
                part = spec.normalize_volume(pos.volume * float(p.get("tp1_fraction", 0.35)))
                if part > 0 and pos.volume - part >= spec.volume_min:
                    res = self.broker.close_position(pos.ticket, part, "tp1")
                    if res.ok:
                        st.tp1_done = True
                        actions.append({"ticket": pos.ticket, "do": "tp1_partial", "volume": part})
                        self._say(f"#{pos.ticket} TP1 (+{now_r:.2f}R): {part} lot yopildi.")
                else:
                    # Hajm bo'linmaydi — TP1 ni o'tkazib yuboramiz, trailing ishlaydi
                    st.tp1_done = True
                    self._say(f"#{pos.ticket} TP1 o'tkazib yuborildi (hajm bo'linmaydi).")
                # TP1 dan keyin stop -0.35R ga
                self._move_stop(pos, st, st.entry_price + pos.side * float(
                    p.get("tp1_stop_to_r", -0.35)) * R, "tp1_stop", actions)

            # --- zararsizlikka o'tish ---
            if not st.be_moved and move_r >= float(p.get("be_trigger_r", 2.0)):
                # Zararsizlik = kirish + kichik zaxira (R ulushi) + spread,
                # backtestdagi bilan bir xil mantiq
                pad = float(p.get("be_offset_r", 0.05)) * R + quote.spread
                target = st.entry_price + pos.side * pad
                if self._move_stop(pos, st, target, "breakeven", actions):
                    st.be_moved = True

            # --- trailing ---
            if move_r >= float(p.get("trail_after_r", 1.5)) and st.atr_at_entry > 0:
                trail = st.best_price - pos.side * float(p.get("trail_atr_mult", 2.5)) * st.atr_at_entry
                # Har bir mayda harakatda stopni surmaymiz: brokerga ortiqcha
                # so'rov yubormaslik va "stop hunting" ga o'zimizni tutib
                # bermaslik uchun minimal qadam talab qilinadi
                min_step = float(p.get("trail_min_step_atr", 0.15)) * st.atr_at_entry
                if not pos.sl or abs(trail - pos.sl) >= min_step:
                    self._move_stop(pos, st, trail, "trailing", actions)

            # --- vaqt stopi ---
            held = (bar_time - pd.Timestamp(st.entry_time)).total_seconds() / (60 * BAR_MINUTES)
            if held >= int(p.get("time_stop_bars", 24)) and move_r < float(
                    p.get("time_stop_min_r", 0.5)):
                res = self.broker.close_position(pos.ticket, None, "time_stop")
                if res.ok:
                    actions.append({"ticket": pos.ticket, "do": "time_stop"})
                    self._say(f"#{pos.ticket} vaqt stopi ({held:.0f} bar, {now_r:+.2f}R) — yopildi.")
                    self.state.trades.pop(str(pos.ticket), None)
                    live_tickets.discard(str(pos.ticket))

        # Yopilgan savdolarni holatdan olib tashlaymiz
        pending_tickets = {str(o.ticket) for o in self.broker.pending_orders(self.symbol)}
        for ticket in list(self.state.trades):
            if ticket not in live_tickets and ticket not in pending_tickets:
                self.state.trades.pop(ticket, None)
        return actions

    def _move_stop(self, pos, st: TradeState, target: float, why: str,
                   actions: list[dict]) -> bool:
        """Stopni faqat foydali yo'nalishda suradi."""
        better = target > pos.sl if pos.side > 0 else target < pos.sl
        if pos.sl and not better:
            return False
        res = self.broker.modify_position(pos.ticket, sl=target)
        if res.ok:
            actions.append({"ticket": pos.ticket, "do": why, "sl": target})
            self._say(f"#{pos.ticket} stop -> {target:.2f} ({why})")
            return True
        self._say(f"#{pos.ticket} stopni surib bo'lmadi ({why}): {res.message}")
        return False

    def _recover_state(self, pos, features: pd.DataFrame) -> TradeState:
        """Holat fayli yo'qolganda pozitsiyadan qayta quradi."""
        atr = float(features["atr"].iloc[-1])
        R = abs(pos.entry_price - pos.sl) if pos.sl else max(atr, 1e-9)
        return TradeState(
            ticket=pos.ticket, side=pos.side, entry_price=pos.entry_price,
            risk_per_unit=R, initial_volume=pos.volume, atr_at_entry=atr,
            entry_time=pos.open_time.isoformat(), best_price=pos.entry_price,
        )

    def _expire_pending(self, bar_time: pd.Timestamp, limit_bars: int) -> None:
        for order in self.broker.pending_orders(self.symbol):
            st = self.state.trades.get(str(order.ticket))
            if st is None:
                continue
            age = (bar_time - pd.Timestamp(st.entry_time)).total_seconds() / (60 * BAR_MINUTES)
            if age >= limit_bars:
                res = self.broker.cancel_order(order.ticket)
                if res.ok:
                    self._say(f"Limit order #{order.ticket} muddati tugadi — bekor qilindi.")
                    self.state.trades.pop(str(order.ticket), None)

    # ------------------------------------------------------------ yangi savdo
    def _open_trade(self, side: int, features: pd.DataFrame, signals: pd.DataFrame,
                    spec: SymbolSpec, equity: float, bar_time: pd.Timestamp) -> dict:
        p = self.strategy.params
        atr = float(signals["atr"].iloc[-1])
        raw_stop = float(signals["stop_price"].iloc[-1])
        quote = self.broker.quote(self.symbol)

        use_limit = str(p.get("entry_mode", "limit")) == "limit"
        ref = float(signals["entry_ref"].iloc[-1]) if "entry_ref" in signals else np.nan
        if use_limit and np.isfinite(ref):
            entry = ref
        else:
            entry = quote.ask if side > 0 else quote.bid
            use_limit = False

        dist = side * (entry - raw_stop)
        dist = float(np.clip(dist, float(p["min_sl_atr"]) * atr, float(p["max_sl_atr"]) * atr))
        dist = float(np.clip(dist, self.cfg.risk.min_stop_pct * entry,
                             self.cfg.risk.max_stop_pct * entry))
        if dist <= 0:
            return {"action": "skip", "reason": "stop masofasi noto'g'ri"}

        sl = entry - side * dist
        tp = entry + side * float(p.get("tp2_r", 3.5)) * dist

        # --- hajm ---
        risk_money = equity * self.risk.effective_risk(equity)
        units = risk_money / dist
        lots = spec.normalize_volume(units / spec.contract_size)
        if lots <= 0:
            return {"action": "skip",
                    "reason": f"hisoblangan hajm minimal lotdan kichik "
                              f"({units / spec.contract_size:.4f} < {spec.volume_min})"}

        actual_risk = lots * spec.contract_size * dist
        if actual_risk > risk_money * 1.5:
            return {"action": "skip",
                    "reason": f"minimal lot juda katta risk beradi "
                              f"({actual_risk:.2f} > byudjet {risk_money:.2f})"}

        # --- spread tekshiruvi (MT5 da asosiy xarajat) ---
        cost_r = (2.0 * quote.spread) / dist if dist > 0 else np.inf
        if cost_r > 0.40:
            return {"action": "skip",
                    "reason": f"spread juda keng: xarajat {cost_r:.2f}R "
                              f"(spread {quote.spread:.2f}, stop {dist:.2f})"}

        max_lev = (lots * spec.contract_size * entry) / max(equity, 1e-9)
        if max_lev > self.cfg.risk.max_leverage:
            return {"action": "skip", "reason": f"leverage {max_lev:.1f}x chegaradan yuqori"}

        direction = "LONG" if side > 0 else "SHORT"
        self._say(
            f"\n{'[DRY-RUN] ' if self.dry_run else ''}{direction} {self.symbol}\n"
            f"  kirish {entry:.2f} ({'limit' if use_limit else 'market'})  "
            f"stop {sl:.2f}  TP {tp:.2f}\n"
            f"  hajm {lots} lot   risk {actual_risk:.2f} "
            f"({actual_risk / equity * 100:.2f}%)   xarajat {cost_r:.2f}R"
        )

        if use_limit:
            expiry = bar_time + pd.Timedelta(minutes=BAR_MINUTES * int(p.get("entry_limit_bars", 3)))
            res = self.broker.limit_order(self.symbol, side, lots, entry, sl, tp, expiry)
        else:
            res = self.broker.market_order(self.symbol, side, lots, sl, tp)

        if not res.ok:
            self._say(f"  ORDER RAD ETILDI: {res.message}")
            return {"action": "rejected", "reason": res.message}

        ticket = res.ticket or 0
        self.state.trades[str(ticket)] = TradeState(
            ticket=ticket, side=side, entry_price=entry, risk_per_unit=dist,
            initial_volume=lots, atr_at_entry=atr, entry_time=bar_time.isoformat(),
            best_price=entry, pending=use_limit,
        )
        self.state.trades_today += 1
        self.risk.on_trade_opened(bar_time)
        return {"action": "placed", "side": side, "ticket": ticket, "entry": entry,
                "sl": sl, "tp": tp, "lots": lots, "risk": actual_risk, "cost_r": cost_r}

    # ------------------------------------------------------------ risk
    def _roll_day(self, bar_time: pd.Timestamp, equity: float) -> None:
        day = bar_time.strftime("%Y-%m-%d")
        if self.state.day != day:
            self.state.day = day
            self.state.trades_today = 0
            self.state.day_start_equity = equity
        self.risk.on_new_bar(bar_time, equity)

    def _risk_block(self, bar_time: pd.Timestamp, equity: float) -> str:
        c = self.cfg.risk
        if self.state.trades_today >= c.max_trades_per_day:
            return f"kunlik savdolar chegarasi ({c.max_trades_per_day})"
        start = self.state.day_start_equity or equity
        day_pnl = (equity - start) / max(start, 1e-9)
        if day_pnl <= -c.daily_loss_limit:
            return f"kunlik zarar chegarasi ({day_pnl * 100:.2f}%)"
        if self.state.blocked_until:
            until = pd.Timestamp(self.state.blocked_until)
            if bar_time < until:
                return f"tanaffus {until:%H:%M} gacha"
        return ""

    # ------------------------------------------------------------ uzluksiz rejim
    def run_forever(self, poll_seconds: int = 20, max_iterations: int | None = None) -> None:
        """Har yangi YOPILGAN bar uchun bir marta `run_once` chaqiradi.

        Bar yopilishini kutadi — bar ichida qayta-qayta ishlamaydi. Bu
        muhim: signal faqat yopilgan barda haqiqiy.
        """
        import time as _time

        self._say(
            f"Jonli rejim boshlandi — {self.symbol} {self.cfg.timeframe}\n"
            f"  Rejim: {'DRY-RUN (order yuborilmaydi)' if self.dry_run else 'REAL SAVDO'}\n"
            f"  To'xtatish: Ctrl+C"
        )
        seen = self.state.last_bar
        iterations = 0
        while max_iterations is None or iterations < max_iterations:
            try:
                bars = self.broker.bars(self.symbol, self.cfg.timeframe, count=1200)
                latest = str(bars.index[-1])
                if latest != seen:
                    seen = latest
                    self.state.last_bar = latest
                    self._say(f"\n--- yangi bar: {latest} ---")
                    self.run_once(bars=bars)
                    iterations += 1
                else:
                    # Bar yopilmagan bo'lsa ham ochiq pozitsiyani kuzatamiz
                    if self.broker.positions(self.symbol):
                        spec = self.broker.symbol_spec(self.symbol)
                        self._manage_open(build_features(bars), spec, bars.index[-1])
                        self._save()
            except KeyboardInterrupt:
                self._say("\nTo'xtatildi (Ctrl+C).")
                break
            except Exception as exc:  # noqa: BLE001 — sikl uzilmasligi kerak
                self._say(f"XATO (sikl davom etadi): {exc}")
            _time.sleep(poll_seconds)
