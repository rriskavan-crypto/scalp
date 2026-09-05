"""Jonli signal — oxirgi yopilgan bar bo'yicha holat va aniq buyruq darajalari.

Bu modul FAQAT o'qiydi va hisoblaydi. Hech qanday order yubormaydi, API
kaliti talab qilmaydi. Chiqishni ko'rib, qarorni siz qabul qilasiz.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import Config
from .features import build_features
from .strategies import Strategy, get_strategy
from .strategies.base import rolling_any, session_mask


@dataclass
class LiveSignal:
    time: pd.Timestamp
    price: float
    side: int
    entry: float
    stop: float
    tp1: float
    tp2: float
    qty: float
    notional: float
    risk_amount: float
    stop_pct: float
    cost_r: float
    checks: dict[str, bool]

    @property
    def has_signal(self) -> bool:
        return self.side != 0


def evaluate_now(df: pd.DataFrame, cfg: Config,
                 strategy: Strategy | None = None,
                 equity: float | None = None) -> LiveSignal:
    """Oxirgi YOPILGAN bar bo'yicha signal va darajalarni hisoblaydi."""
    strategy = strategy or get_strategy(cfg.strategy.name, cfg.strategy.params)
    equity = equity if equity is not None else cfg.risk.initial_equity

    f = build_features(df)
    sig = strategy.generate(f)
    last = f.iloc[-1]
    s = int(sig["signal"].iloc[-1])
    atr0 = float(sig["atr"].iloc[-1])
    price = float(last["close"])

    checks = _condition_checks(f, strategy)

    if s == 0 or not np.isfinite(atr0) or atr0 <= 0:
        return LiveSignal(f.index[-1], price, 0, np.nan, np.nan, np.nan, np.nan,
                          0.0, 0.0, 0.0, np.nan, np.nan, checks)

    p = strategy.params
    entry = float(sig["entry_ref"].iloc[-1]) if "entry_ref" in sig.columns else price
    if not np.isfinite(entry):
        entry = price

    raw_stop = float(sig["stop_price"].iloc[-1])
    dist = s * (entry - raw_stop)
    dist = float(np.clip(dist, float(p["min_sl_atr"]) * atr0, float(p["max_sl_atr"]) * atr0))
    dist = float(np.clip(dist, cfg.risk.min_stop_pct * entry, cfg.risk.max_stop_pct * entry))

    risk_amount = equity * cfg.risk.risk_per_trade
    qty = min(risk_amount / dist, (equity * cfg.risk.max_leverage) / entry)
    stop_pct = dist / entry

    return LiveSignal(
        time=f.index[-1], price=price, side=s, entry=entry,
        stop=entry - s * dist,
        tp1=entry + s * float(p["tp1_r"]) * dist,
        tp2=entry + s * float(p["tp2_r"]) * dist,
        qty=qty, notional=qty * entry, risk_amount=qty * dist,
        stop_pct=stop_pct,
        cost_r=(cfg.cost.round_trip_bps() * 1e-4) / stop_pct if stop_pct > 0 else np.inf,
        checks=checks,
    )


def _condition_checks(f: pd.DataFrame, strategy: Strategy) -> dict[str, bool]:
    """Har bir shartning joriy holati — qo'lda savdo qilish uchun ro'yxat."""
    p = strategy.params
    last = f.iloc[-1]
    pb = int(p.get("pullback_lookback", 4))
    lb = int(p.get("impulse_lookback", 12))

    strong = (f["body_atr"].abs() >= float(p.get("impulse_body_atr", 0.8))) & (
        f["vol_z"] >= float(p.get("impulse_vol_z", 1.0)))
    imp_up = ((strong & (f["body_atr"] > 0)) | (f["close"] > f["dc_high_prev"])).fillna(False)
    imp_dn = ((strong & (f["body_atr"] < 0)) | (f["close"] < f["dc_low_prev"])).fillna(False)

    def tail(series: pd.Series) -> bool:
        return bool(series.iloc[-1])

    return {
        "ATR% oynada": bool(
            float(p.get("min_atr_pct", 0.002)) <= last["atr_pct"] <= float(p.get("max_atr_pct", 0.012))
        ),
        f"ADX >= {p.get('adx_min', 20)}": bool(last["adx"] >= float(p.get("adx_min", 20))),
        "Savdo seansi": (
            tail(session_mask(f, int(p.get("session_start_hour", 6)), int(p.get("session_end_hour", 22))))
            if p.get("use_session_filter", True) else True
        ),
        "M5 trend (LONG)": bool(
            last["ema_fast"] > last["ema_mid"] > last["ema_slow"] and last["close"] > last["ema_slow"]
        ),
        "M5 trend (SHORT)": bool(
            last["ema_fast"] < last["ema_mid"] < last["ema_slow"] and last["close"] < last["ema_slow"]
        ),
        "H1 bull": bool(last.get("htf_bull", False)),
        "H1 bear": bool(last.get("htf_bear", False)),
        "Impuls (long)": tail(rolling_any(imp_up.shift(1).fillna(False), lb)),
        "Impuls (short)": tail(rolling_any(imp_dn.shift(1).fillna(False), lb)),
        "EMA21 ga qaytish (long)": tail(
            rolling_any(f["low"] <= f["ema_fast"] + float(p.get("touch_atr", 0.25)) * f["atr"], pb)),
        "EMA21 ga qaytish (short)": tail(
            rolling_any(f["high"] >= f["ema_fast"] - float(p.get("touch_atr", 0.25)) * f["atr"], pb)),
        "RSI cho'kdi (long)": tail(rolling_any(f["rsi"] <= float(p.get("rsi_pullback_long", 45)), pb)),
        "RSI ko'tarildi (short)": tail(rolling_any(f["rsi"] >= float(p.get("rsi_pullback_short", 55)), pb)),
    }


def format_signal(ls: LiveSignal, cfg: Config, equity: float) -> str:
    w = 60
    L = ["=" * w, "JONLI SIGNAL".center(w), "=" * w,
         f"  Oxirgi yopilgan bar : {ls.time:%Y-%m-%d %H:%M} UTC",
         f"  Narx                : {ls.price:,.2f}", ""]

    L += ["  SHARTLAR HOLATI:"]
    for name, ok in ls.checks.items():
        L.append(f"    [{'x' if ok else ' '}] {name}")
    L.append("")

    if not ls.has_signal:
        L += ["  >>> SIGNAL YO'Q — kutish. <<<",
              "      Skalpingda kutish ham pozitsiya. Shartlar to'liq",
              "      bajarilmaguncha savdo qilmang.", "=" * w]
        return "\n".join(L)

    direction = "LONG (sotib olish)" if ls.side > 0 else "SHORT (sotish)"
    L += [f"  >>> {direction} <<<", "",
          f"  Kirish (limit)      : {ls.entry:,.2f}",
          f"  Stop-loss           : {ls.stop:,.2f}   ({ls.stop_pct * 100:.2f} %)",
          f"  TP1 ({cfg.strategy.params.get('tp1_r', 1.5)}R)          : {ls.tp1:,.2f}"
          f"   -> pozitsiyaning {float(cfg.strategy.params.get('tp1_fraction', 0.35)) * 100:.0f} % i",
          f"  TP2 ({cfg.strategy.params.get('tp2_r', 3.5)}R)          : {ls.tp2:,.2f}", "",
          f"  Kapital             : {equity:,.2f}",
          f"  Hajm                : {ls.qty:.6f} BTC  (notional {ls.notional:,.2f})",
          f"  Xavf ostidagi summa : {ls.risk_amount:,.2f}"
          f"  ({ls.risk_amount / equity * 100:.2f} %)",
          f"  Xarajat             : {ls.cost_r:.2f} R"]
    if ls.cost_r > 0.35:
        L.append("      OGOHLANTIRISH: xarajat 0.35R dan yuqori — stop juda tor,")
        L.append("      bu savdodan voz kechish tavsiya etiladi.")
    L.append("=" * w)
    return "\n".join(L)
