"""Risk boshqaruvi — strategiyaning omon qolishini ta'minlaydigan qism.

Har qanday ustunlik (edge) noto'g'ri pozitsiya hajmi bilan yo'q qilinadi.
Bu modul quyidagi himoya qatlamlarini beradi:

  1. Sobit ulushli hajm  — har savdoda kapitalning belgilangan % i xavf ostida
  2. Kunlik zarar chegarasi — yomon kunni to'xtatadi
  3. Ketma-ket zararlar   — "tilt" ga qarshi majburiy tanaffus
  4. Drawdownda risk kamayishi — chuqurlikda avtomatik sekinlashuv
  5. Kunlik savdolar soni — haddan tashqari savdo qilishga to'siq
"""

from __future__ import annotations

import pandas as pd

from .config import RiskConfig


class RiskManager:
    def __init__(self, cfg: RiskConfig):
        self.cfg = cfg
        self.peak_equity = cfg.initial_equity
        self.day: pd.Timestamp | None = None
        self.day_start_equity = cfg.initial_equity
        self.trades_today = 0
        self.consecutive_losses = 0
        self.block_until_bar = -1
        self.blocked_count = 0
        self._day_locked = False

    # ---------- kun almashuvi ----------
    def on_new_bar(self, ts: pd.Timestamp, equity: float) -> None:
        day = ts.normalize()
        if self.day is None or day != self.day:
            self.day = day
            self.day_start_equity = equity
            self.trades_today = 0
            self._day_locked = False
        self.peak_equity = max(self.peak_equity, equity)

    # ---------- ruxsat ----------
    def can_trade(self, ts: pd.Timestamp, bar_i: int, equity: float) -> bool:
        c = self.cfg
        if bar_i < self.block_until_bar:
            self.blocked_count += 1
            return False
        if self.trades_today >= c.max_trades_per_day:
            self.blocked_count += 1
            return False
        if self._day_locked:
            self.blocked_count += 1
            return False

        day_pnl_pct = (equity - self.day_start_equity) / max(self.day_start_equity, 1e-9)
        if day_pnl_pct <= -c.daily_loss_limit:
            self._day_locked = True
            self.blocked_count += 1
            return False
        if equity <= 0:
            return False
        return True

    # ---------- hajm ----------
    def effective_risk(self, equity: float) -> float:
        """Drawdown chuqur bo'lsa riskni yarmiga tushiradi."""
        c = self.cfg
        drawdown = 1.0 - equity / max(self.peak_equity, 1e-9)
        if drawdown >= c.halve_risk_drawdown:
            return c.risk_per_trade * 0.5
        return c.risk_per_trade

    # ---------- hodisalar ----------
    def on_trade_opened(self, ts: pd.Timestamp) -> None:
        self.trades_today += 1

    def on_trade_closed(self, net_pnl: float, ts: pd.Timestamp, bar_i: int) -> None:
        c = self.cfg
        if net_pnl < 0:
            self.consecutive_losses += 1
            cooldown = c.cooldown_bars_after_loss
            if self.consecutive_losses >= c.max_consecutive_losses:
                cooldown = c.cooldown_bars_after_streak
                self.consecutive_losses = 0
            self.block_until_bar = bar_i + cooldown
        else:
            self.consecutive_losses = 0


def position_size(equity: float, risk_pct: float, stop_distance: float,
                  entry_price: float, max_leverage: float) -> float:
    """Pozitsiya hajmi (BTC birligida).

        qty = (kapital * risk %) / stop masofasi

    Leverage cheklovi bilan kesiladi.
    """
    if stop_distance <= 0 or entry_price <= 0:
        return 0.0
    qty = (equity * risk_pct) / stop_distance
    return min(qty, (equity * max_leverage) / entry_price)
