"""Bar-bar backtest dvigateli.

Dizayn qoidalari (natijaning haqqoniyligi shularga bog'liq):

1. **Kelajakka qarash yo'q.** Signal `t` bar YOPILGANDA hisoblanadi,
   ijro `t+1` bar OCHILISHIDA bo'ladi.
2. **Bar ichidagi noaniqlik — savdogar zarariga.** Agar bitta bar ichida
   ham stop, ham take-profit darajasi tegilgan bo'lsa, dvigatel STOP
   birinchi ishlagan deb hisoblaydi. Bu natijani pessimistik qiladi.
3. **Gap (uzilish).** Agar bar stopdan narida ochilsa, ijro ochilish
   narxida bo'ladi — stop darajasida emas.
4. **Har bir ijro xarajat bilan.** Komissiya + sirpanish har kirish va
   chiqishda ushlanadi, perpetual funding esa pozitsiya ochiq turgan
   davrda hisoblanadi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from ..config import Config
from ..risk import RiskManager
from .broker import fee_for, fill_price, funding_cost


@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    side: int                 # +1 long, -1 short
    entry_price: float
    exit_price: float         # o'rtacha tortilgan chiqish narxi
    qty: float
    stop_init: float
    tp1: float
    tp2: float
    risk_per_unit: float      # R — narxdagi stop masofasi
    risk_amount: float        # USD dagi rejalashtirilgan zarar
    notional: float
    gross_pnl: float
    fees: float
    funding: float
    net_pnl: float
    r_multiple: float
    bars_held: int
    exit_reason: str
    mae_r: float              # eng yomon nuqta, R birligida
    mfe_r: float              # eng yaxshi nuqta, R birligida
    equity_after: float


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    equity: pd.Series
    config: Config
    bars: int
    start: pd.Timestamp
    end: pd.Timestamp
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def days(self) -> float:
        return max((self.end - self.start).total_seconds() / 86400.0, 1e-9)


class _Position:
    """Ochiq pozitsiya holati."""

    __slots__ = (
        "side", "entry_time", "entry_i", "entry_price", "qty", "qty_init",
        "stop", "tp1", "tp2", "risk_per_unit", "risk_amount", "atr0",
        "tp1_done", "realized_pnl", "fees", "best_price", "worst_price",
        "exit_reason", "exit_notional", "exit_qty",
    )

    def __init__(self, **kw):
        self.exit_reason = "unknown"
        self.exit_notional = 0.0
        self.exit_qty = 0.0
        for k, v in kw.items():
            setattr(self, k, v)


def run_backtest(
    features: pd.DataFrame,
    signals: pd.DataFrame,
    cfg: Config,
    strategy_params: dict[str, Any] | None = None,
    warmup: int = 0,
) -> BacktestResult:
    """Signallarni tarixiy narxlarda ijro etadi."""
    p = strategy_params or {}
    cost, risk_cfg = cfg.cost, cfg.risk
    rm = RiskManager(risk_cfg)

    # --- parametrlar ---
    min_sl_atr = float(p.get("min_sl_atr", 1.0))
    max_sl_atr = float(p.get("max_sl_atr", 2.2))
    tp1_r = float(p.get("tp1_r", 1.5))
    tp1_fraction = float(p.get("tp1_fraction", 0.35))
    tp2_r = float(p.get("tp2_r", 3.5))
    tp1_stop_to_r = float(p.get("tp1_stop_to_r", -0.35))
    be_after_tp1 = bool(p.get("be_after_tp1", False))
    be_trigger_r = float(p.get("be_trigger_r", 2.0))
    be_offset_r = float(p.get("be_offset_r", 0.05))
    trail_mult = float(p.get("trail_atr_mult", 2.5))
    trail_after_r = float(p.get("trail_after_r", 1.5))
    time_stop = int(p.get("time_stop_bars", 24))
    time_stop_min_r = float(p.get("time_stop_min_r", 0.5))
    exit_on_ema = bool(p.get("exit_on_ema_cross", True))
    entry_mode = str(p.get("entry_mode", "limit"))
    entry_limit_bars = int(p.get("entry_limit_bars", 3))

    # --- numpy massivlariga o'tkazamiz (tezlik uchun) ---
    idx = features.index
    op = features["open"].to_numpy(float)
    hi = features["high"].to_numpy(float)
    lo = features["low"].to_numpy(float)
    cl = features["close"].to_numpy(float)
    ema_fast = features["ema_fast"].to_numpy(float)
    sig_arr = signals["signal"].to_numpy(np.int8)
    stop_arr = signals["stop_price"].to_numpy(float)
    atr_arr = signals["atr"].to_numpy(float)
    entry_ref_arr = (
        signals["entry_ref"].to_numpy(float)
        if "entry_ref" in signals.columns
        else np.full(len(idx), np.nan)
    )

    n = len(idx)
    equity = float(risk_cfg.initial_equity)
    equity_curve = np.full(n, np.nan)
    trades: list[Trade] = []
    pos: _Position | None = None
    pending: _PendingOrder | None = None
    limit_expired = 0
    limit_filled = 0

    start_i = max(warmup, 1)

    for i in range(start_i, n):
        bar_time = idx[i]
        rm.on_new_bar(bar_time, equity)

        # ================= 1) OCHIQ POZITSIYANI BOSHQARISH =================
        closed_this_bar = False
        if pos is not None:
            closed_this_bar = _manage_position(
                pos, i, op, hi, lo, cl, ema_fast, cost,
                tp1_r, tp1_fraction, tp2_r, tp1_stop_to_r, be_after_tp1,
                be_trigger_r, be_offset_r, trail_mult, trail_after_r,
                time_stop, time_stop_min_r, exit_on_ema,
            )
            if closed_this_bar:
                trade = _finalize(pos, bar_time, i, cost, equity)
                equity += trade.net_pnl
                trade.equity_after = equity
                trades.append(trade)
                rm.on_trade_closed(trade.net_pnl, bar_time, i)
                pos = None

        # ================= 2) YANGI POZITSIYA OCHISH =================
        if pos is None and not closed_this_bar:
            # 2a) Kutayotgan limit orderni tekshiramiz
            if pending is not None:
                if i > pending.expiry_bar:
                    pending, limit_expired = None, limit_expired + 1
                elif pending.invalidated(lo[i], hi[i]):
                    pending, limit_expired = None, limit_expired + 1
                elif pending.touched(lo[i], hi[i]):
                    # Limit order — sirpanishsiz, o'z narxida to'ldiriladi
                    pos = _open_position(
                        pending.side, bar_time, i, pending.limit_price,
                        pending.raw_stop, pending.atr, equity, rm, cost, risk_cfg,
                        min_sl_atr, max_sl_atr, tp1_r, tp2_r, is_maker_entry=True,
                    )
                    pending = None
                    limit_filled += 1
                    if pos is not None:
                        rm.on_trade_opened(bar_time)

            # 2b) Yangi signal
            if pos is None:
                side = int(sig_arr[i - 1])
                atr0, raw_stop = atr_arr[i - 1], stop_arr[i - 1]
                valid = (
                    side != 0
                    and np.isfinite(atr0) and atr0 > 0
                    and np.isfinite(raw_stop)
                    and rm.can_trade(bar_time, i, equity)
                )
                if valid and entry_mode == "limit":
                    ref = entry_ref_arr[i - 1]
                    if not np.isfinite(ref):
                        ref = cl[i - 1]
                    # Limit narx allaqachon o'tib ketgan bo'lsa, shu barda to'ldiriladi
                    pending = _PendingOrder(
                        side=side, limit_price=float(ref), raw_stop=float(raw_stop),
                        atr=float(atr0), expiry_bar=i + entry_limit_bars - 1,
                    )
                    if pending.touched(lo[i], hi[i]) and not pending.invalidated(lo[i], hi[i]):
                        pos = _open_position(
                            side, bar_time, i, pending.limit_price, raw_stop, atr0,
                            equity, rm, cost, risk_cfg, min_sl_atr, max_sl_atr,
                            tp1_r, tp2_r, is_maker_entry=True,
                        )
                        pending = None
                        limit_filled += 1
                        if pos is not None:
                            rm.on_trade_opened(bar_time)
                elif valid:
                    entry_px = fill_price(op[i], side, is_exit=False, cost=cost)
                    pos = _open_position(
                        side, bar_time, i, entry_px, raw_stop, atr0, equity, rm,
                        cost, risk_cfg, min_sl_atr, max_sl_atr, tp1_r, tp2_r,
                        is_maker_entry=False,
                    )
                    if pos is not None:
                        rm.on_trade_opened(bar_time)

        # ================= 3) EKVITI EGRI CHIZIG'I =================
        if pos is not None:
            unreal = pos.side * (cl[i] - pos.entry_price) * pos.qty + pos.realized_pnl
            equity_curve[i] = equity + unreal - pos.fees
        else:
            equity_curve[i] = equity

    # --- ochiq qolgan pozitsiyani oxirgi narxda yopamiz ---
    if pos is not None:
        _close_all(pos, cl[n - 1], "end_of_data", cost, is_stop=False)
        trade = _finalize(pos, idx[n - 1], n - 1, cost, equity)
        equity += trade.net_pnl
        trade.equity_after = equity
        trades.append(trade)
        equity_curve[n - 1] = equity

    trades_df = _trades_to_frame(trades)
    equity_series = pd.Series(equity_curve, index=idx, name="equity").ffill()
    equity_series = equity_series.fillna(float(risk_cfg.initial_equity))

    return BacktestResult(
        trades=trades_df,
        equity=equity_series,
        config=cfg,
        bars=n - start_i,
        start=idx[start_i] if n > start_i else idx[0],
        end=idx[-1],
        meta={
            "strategy_params": dict(p),
            "blocked_by_risk": rm.blocked_count,
            "entry_mode": entry_mode,
            "limit_filled": limit_filled,
            "limit_expired": limit_expired,
            "limit_fill_rate": limit_filled / max(limit_filled + limit_expired, 1),
        },
    )


# --------------------------------------------------------------------------
# Ichki yordamchilar
# --------------------------------------------------------------------------

class _PendingOrder:
    """Kutayotgan limit order.

    Limit kirishning ikki tomoni bor:
      (+) maker komissiyasi (0.02 % o'rniga 0.05 %) va yaxshiroq narx —
          har savdoda ~0.065R tejaladi;
      (-) *salbiy tanlanish*: narx sizga qarshi ketgandagina to'ldirilasiz,
          va eng kuchli harakatlarni butunlay o'tkazib yuborasiz.
    Qaysi biri ustun kelishi REAL ma'lumotda tekshirilishi shart —
    shuning uchun `entry_mode` parametr sifatida qoldirilgan.
    """

    __slots__ = ("side", "limit_price", "raw_stop", "atr", "expiry_bar")

    def __init__(self, side: int, limit_price: float, raw_stop: float,
                 atr: float, expiry_bar: int):
        self.side = side
        self.limit_price = limit_price
        self.raw_stop = raw_stop
        self.atr = atr
        self.expiry_bar = expiry_bar

    def touched(self, low: float, high: float) -> bool:
        return low <= self.limit_price if self.side > 0 else high >= self.limit_price

    def invalidated(self, low: float, high: float) -> bool:
        """Narx to'ldirilishdan oldin stop darajasidan o'tib ketgan bo'lsa — bekor."""
        return low <= self.raw_stop if self.side > 0 else high >= self.raw_stop


def _open_position(side, bar_time, i, entry_px, raw_stop, atr0, equity, rm,
                   cost, risk_cfg, min_sl_atr, max_sl_atr, tp1_r, tp2_r,
                   is_maker_entry: bool) -> "_Position | None":
    """Pozitsiya ochadi va hajmni riskka qarab hisoblaydi."""
    dist = _stop_distance(entry_px, raw_stop, side, atr0, min_sl_atr, max_sl_atr,
                          risk_cfg.min_stop_pct, risk_cfg.max_stop_pct)
    if dist <= 0:
        return None
    risk_amount = equity * rm.effective_risk(equity)
    qty = min(risk_amount / dist, (equity * risk_cfg.max_leverage) / entry_px)
    if qty <= 0:
        return None

    entry_fee_bps = cost.maker_fee_bps if is_maker_entry else (
        cost.maker_fee_bps if cost.entry_is_maker else cost.taker_fee_bps
    )
    return _Position(
        side=side, entry_time=bar_time, entry_i=i, entry_price=entry_px,
        qty=qty, qty_init=qty, stop=entry_px - side * dist,
        tp1=entry_px + side * tp1_r * dist, tp2=entry_px + side * tp2_r * dist,
        risk_per_unit=dist, risk_amount=qty * dist, atr0=atr0, tp1_done=False,
        realized_pnl=0.0, fees=abs(qty * entry_px) * entry_fee_bps * 1e-4,
        best_price=entry_px, worst_price=entry_px,
    )


def _stop_distance(entry: float, raw_stop: float, side: int, atr0: float,
                   min_sl_atr: float, max_sl_atr: float,
                   min_pct: float, max_pct: float) -> float:
    """Strukturaviy stopni ATR va foiz chegaralari bilan cheklaydi."""
    dist = side * (entry - raw_stop)
    dist = float(np.clip(dist, min_sl_atr * atr0, max_sl_atr * atr0))
    return float(np.clip(dist, min_pct * entry, max_pct * entry))


def _record_exit(pos: _Position, price: float, qty: float, reason: str,
                 cost, is_stop: bool) -> None:
    px = fill_price(price, pos.side, is_exit=True, cost=cost, is_stop=is_stop)
    pos.realized_pnl += pos.side * (px - pos.entry_price) * qty
    pos.fees += fee_for(qty * px, cost, is_exit=True, forced_taker=is_stop)
    pos.qty -= qty
    pos.exit_reason = reason
    pos.exit_notional += px * qty
    pos.exit_qty += qty


def _close_all(pos: _Position, price: float, reason: str, cost, is_stop: bool) -> None:
    if pos.qty > 0:
        _record_exit(pos, price, pos.qty, reason, cost, is_stop)


def _manage_position(pos, i, op, hi, lo, cl, ema_fast, cost,
                     tp1_r, tp1_fraction, tp2_r, tp1_stop_to_r, be_after_tp1,
                     be_trigger_r, be_offset_r, trail_mult, trail_after_r,
                     time_stop, time_stop_min_r, exit_on_ema) -> bool:
    """Bitta bar davomida ochiq pozitsiyani boshqaradi. True = pozitsiya yopildi.

    Chiqish tuzilmasi qasddan shunday qurilgan: **yutuqlar cheklanmaydi**.
    Ilk versiyada TP1 da yarim pozitsiya olinib, stop darhol zararsizlikka
    surilardi — natijada o'rtacha yutuq 0.72R, o'rtacha zarar 1.08R bo'lib,
    zararsizlik uchun 60 % g'alaba kerak bo'lardi. Bu tuzilma buni tuzatadi:

      * TP1 kechroq (1.5R) va kichikroq ulush (35 %) — qolgani ishlashda davom etadi
      * TP1 dan keyin stop zararsizlikka emas, **-0.35R** ga suriladi
        (zararsizlik stopi yutuqlarni nolga aylantirib yuboradi)
      * Zararsizlikka o'tish faqat +2R dan keyin
      * Trailing kechroq (+1.5R) va kengroq (2.5 ATR) — shovqin bilan chiqarmaydi
      * Vaqt stopi faqat **hech qayoqqa ketmagan** savdolarni yopadi (< 0.5R)
    """
    s = pos.side
    o, h, l, c = op[i], hi[i], lo[i], cl[i]

    # MAE / MFE
    pos.best_price = max(pos.best_price, h) if s > 0 else min(pos.best_price, l)
    pos.worst_price = min(pos.worst_price, l) if s > 0 else max(pos.worst_price, h)

    # --- 1) Gap: bar stopdan narida ochildi ---
    if (s > 0 and o <= pos.stop) or (s < 0 and o >= pos.stop):
        _close_all(pos, o, "stop_gap", cost, is_stop=True)
        return True

    # --- 2) Stop (TP dan OLDIN tekshiriladi — pessimistik qoida) ---
    if (s > 0 and l <= pos.stop) or (s < 0 and h >= pos.stop):
        _close_all(pos, pos.stop, _stop_reason(pos), cost, is_stop=True)
        return True

    # --- 3) TP2 (to'liq chiqish) ---
    if (s > 0 and h >= pos.tp2) or (s < 0 and l <= pos.tp2):
        if not pos.tp1_done and tp1_fraction > 0:
            _record_exit(pos, pos.tp1, pos.qty * tp1_fraction, "tp1", cost, is_stop=False)
            pos.tp1_done = True
        _close_all(pos, pos.tp2, "tp2", cost, is_stop=False)
        return True

    # --- 4) TP1 (qisman chiqish) ---
    if not pos.tp1_done and tp1_fraction > 0:
        if (s > 0 and h >= pos.tp1) or (s < 0 and l <= pos.tp1):
            _record_exit(pos, pos.tp1, pos.qty * tp1_fraction, "tp1", cost, is_stop=False)
            pos.tp1_done = True
            if be_after_tp1:
                # Klassik (va zararli) usul: stop darhol zararsizlikka.
                # Taqqoslash uchun qoldirilgan — README dagi jadval shu bilan
                # qayta ishlab chiqariladi.
                fee_pad = pos.entry_price * (cost.taker_fee_bps + cost.slippage_bps) * 1e-4
                _raise_stop(pos, pos.entry_price + s * fee_pad)
            else:
                # Stop -0.35R ga: riskni kamaytiradi, lekin savdoni bo'g'maydi
                _raise_stop(pos, pos.entry_price + s * tp1_stop_to_r * pos.risk_per_unit)
            if (s > 0 and l <= pos.stop) or (s < 0 and h >= pos.stop):
                _close_all(pos, pos.stop, _stop_reason(pos), cost, is_stop=True)
                return True

    move_r = s * (pos.best_price - pos.entry_price) / pos.risk_per_unit

    # --- 5) Zararsizlikka o'tish: faqat savdo yetarli yurganda (+2R) ---
    if move_r >= be_trigger_r:
        fee_pad = pos.entry_price * (cost.taker_fee_bps + cost.slippage_bps) * 1e-4
        _raise_stop(pos, pos.entry_price + s * (be_offset_r * pos.risk_per_unit) + s * fee_pad)

    # --- 6) Trailing stop (keyingi barga ta'sir qiladi) ---
    if move_r >= trail_after_r:
        _raise_stop(pos, pos.best_price - s * trail_mult * pos.atr0)

    # --- 7) Vaqt stopi: faqat hech qayoqqa ketmagan savdolar ---
    if i - pos.entry_i >= time_stop and move_r < time_stop_min_r:
        _close_all(pos, c, "time_stop", cost, is_stop=False)
        return True

    # --- 8) EMA21 dan chiqish (faqat TP1 dan keyin, foydani himoya qilish) ---
    if exit_on_ema and pos.tp1_done and np.isfinite(ema_fast[i]):
        if (s > 0 and c < ema_fast[i]) or (s < 0 and c > ema_fast[i]):
            _close_all(pos, c, "ema_exit", cost, is_stop=False)
            return True

    return False


def _raise_stop(pos: _Position, level: float) -> None:
    """Stopni faqat foydali yo'nalishda suradi (hech qachon orqaga qaytarmaydi)."""
    pos.stop = max(pos.stop, level) if pos.side > 0 else min(pos.stop, level)


def _stop_reason(pos: _Position) -> str:
    """Stop qayerda ishlaganiga qarab sababni nomlaydi."""
    level_r = pos.side * (pos.stop - pos.entry_price) / pos.risk_per_unit
    if level_r >= 0.0:
        return "trail_profit" if pos.stop != pos.entry_price else "breakeven"
    if pos.tp1_done:
        return "stop_reduced"
    return "stop"


def _finalize(pos: _Position, exit_time, exit_i, cost, equity_before: float) -> Trade:
    avg_exit = pos.exit_notional / pos.exit_qty if pos.exit_qty > 0 else pos.entry_price

    notional = pos.qty_init * pos.entry_price
    funding = funding_cost(notional, pos.side, exit_i - pos.entry_i,
                           pos.entry_time, exit_time, cost)
    gross = pos.realized_pnl
    net = gross - pos.fees - funding
    r_unit = pos.risk_amount if pos.risk_amount > 0 else np.nan

    mfe = pos.side * (pos.best_price - pos.entry_price) * pos.qty_init
    mae = pos.side * (pos.worst_price - pos.entry_price) * pos.qty_init

    return Trade(
        entry_time=pos.entry_time, exit_time=exit_time, side=pos.side,
        entry_price=pos.entry_price, exit_price=avg_exit, qty=pos.qty_init,
        stop_init=pos.stop, tp1=pos.tp1, tp2=pos.tp2,
        risk_per_unit=pos.risk_per_unit, risk_amount=pos.risk_amount,
        notional=notional, gross_pnl=gross, fees=pos.fees, funding=funding,
        net_pnl=net, r_multiple=net / r_unit if r_unit else np.nan,
        bars_held=exit_i - pos.entry_i,
        exit_reason=pos.exit_reason,
        mae_r=mae / r_unit if r_unit else np.nan,
        mfe_r=mfe / r_unit if r_unit else np.nan,
        equity_after=equity_before,
    )


_TRADE_COLUMNS = [
    "entry_time", "exit_time", "side", "entry_price", "exit_price", "qty",
    "stop_init", "tp1", "tp2", "risk_per_unit", "risk_amount", "notional",
    "gross_pnl", "fees", "funding", "net_pnl", "r_multiple", "bars_held",
    "exit_reason", "mae_r", "mfe_r", "equity_after",
]


def _trades_to_frame(trades: list[Trade]) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame(columns=_TRADE_COLUMNS)
    df = pd.DataFrame([t.__dict__ for t in trades])
    return df[_TRADE_COLUMNS]
