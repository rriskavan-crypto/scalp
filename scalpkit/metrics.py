"""Natija ko'rsatkichlari.

Eng muhim ko'rsatkich — `expectancy_r`: har bir savdodagi o'rtacha foyda,
risk birligida (R). U musbat bo'lmasa, boshqa hech narsaning ahamiyati yo'q.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Standart: kripto 24/7 savdo qiladi. Oltin/forex uchun ~252 kun —
# `compute_metrics(..., days_per_year=252)` bilan uzatiladi. Noto'g'ri
# qiymat CAGR va Sharpe ni sezilarli buzadi.
TRADING_DAYS_PER_YEAR = 365.0


def compute_metrics(trades: pd.DataFrame, equity: pd.Series,
                    initial_equity: float, days: float,
                    days_per_year: float = TRADING_DAYS_PER_YEAR) -> dict[str, float]:
    """Savdolar va ekviti egri chizig'idan to'liq statistika.

    `days_per_year` — yillik ko'rsatkichlarni hisoblash uchun savdo
    kunlari soni: kripto 365, oltin/forex ~252.
    """
    m: dict[str, float] = {}
    n = len(trades)
    m["trades"] = float(n)
    m["days"] = float(days)
    m["trades_per_day"] = n / days if days > 0 else 0.0

    if n == 0:
        return {**m, **{k: 0.0 for k in _EMPTY_KEYS}}

    r = trades["r_multiple"].to_numpy(float)
    pnl = trades["net_pnl"].to_numpy(float)
    wins, losses = r[pnl > 0], r[pnl <= 0]

    # ---- savdo statistikasi (R birligida) ----
    m["win_rate"] = len(wins) / n
    m["avg_win_r"] = float(np.mean(wins)) if len(wins) else 0.0
    m["avg_loss_r"] = float(np.mean(losses)) if len(losses) else 0.0
    m["payoff_ratio"] = abs(m["avg_win_r"] / m["avg_loss_r"]) if m["avg_loss_r"] else np.inf
    m["expectancy_r"] = float(np.mean(r))
    m["expectancy_r_median"] = float(np.median(r))
    m["r_std"] = float(np.std(r, ddof=1)) if n > 1 else 0.0
    # Har savdodagi "Sharpe" — ustunlikning shovqinga nisbati
    m["r_tstat"] = m["expectancy_r"] / (m["r_std"] / np.sqrt(n)) if m["r_std"] > 0 else 0.0
    m["breakeven_win_rate"] = (
        -m["avg_loss_r"] / (m["avg_win_r"] - m["avg_loss_r"])
        if (m["avg_win_r"] - m["avg_loss_r"]) != 0 else np.nan
    )
    m["win_rate_edge"] = m["win_rate"] - m["breakeven_win_rate"]

    gross_win = float(pnl[pnl > 0].sum())
    gross_loss = float(-pnl[pnl <= 0].sum())
    m["profit_factor"] = gross_win / gross_loss if gross_loss > 0 else np.inf

    # ---- pul ----
    m["net_profit"] = float(pnl.sum())
    m["return_pct"] = m["net_profit"] / initial_equity
    m["total_fees"] = float(trades["fees"].sum())
    m["total_funding"] = float(trades["funding"].sum())
    risk_amt = trades["risk_amount"].to_numpy(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        m["fee_drag_r"] = float(np.nanmean(trades["fees"].to_numpy(float) / risk_amt))
        m["gross_expectancy_r"] = float(np.nanmean(trades["gross_pnl"].to_numpy(float) / risk_amt))
    m["fee_share_of_gross_profit"] = (
        m["total_fees"] / gross_win if gross_win > 0 else np.inf
    )

    # ---- ekviti ----
    eq = equity.dropna()
    m["final_equity"] = float(eq.iloc[-1]) if len(eq) else initial_equity
    dd = _drawdown(eq)
    m["max_drawdown_pct"] = float(dd.min()) if len(dd) else 0.0
    m["max_drawdown_days"] = _max_drawdown_duration_days(eq)

    years = days / days_per_year
    if years > 0 and m["final_equity"] > 0:
        m["cagr"] = (m["final_equity"] / initial_equity) ** (1.0 / years) - 1.0
    else:
        m["cagr"] = 0.0
    m["calmar"] = m["cagr"] / abs(m["max_drawdown_pct"]) if m["max_drawdown_pct"] < 0 else np.inf

    daily = eq.resample("1D").last().dropna()
    dret = daily.pct_change().dropna()
    if len(dret) > 2 and dret.std(ddof=1) > 0:
        m["sharpe"] = float(dret.mean() / dret.std(ddof=1) * np.sqrt(days_per_year))
        downside = dret[dret < 0]
        ds = downside.std(ddof=1) if len(downside) > 1 else 0.0
        m["sortino"] = float(dret.mean() / ds * np.sqrt(days_per_year)) if ds > 0 else np.inf
    else:
        m["sharpe"] = 0.0
        m["sortino"] = 0.0

    # ---- ketma-ketliklar va davomiylik ----
    m["max_consecutive_wins"] = float(_max_streak(pnl > 0))
    m["max_consecutive_losses"] = float(_max_streak(pnl <= 0))
    m["avg_bars_held"] = float(trades["bars_held"].mean())
    m["avg_minutes_held"] = m["avg_bars_held"] * 5.0
    m["best_trade_r"] = float(r.max())
    m["worst_trade_r"] = float(r.min())
    m["avg_mae_r"] = float(trades["mae_r"].mean())
    m["avg_mfe_r"] = float(trades["mfe_r"].mean())
    m["long_share"] = float((trades["side"] > 0).mean())
    m["avg_stop_pct"] = float(
        (trades["risk_per_unit"] / trades["entry_price"]).mean()
    )
    return m


_EMPTY_KEYS = [
    "win_rate", "avg_win_r", "avg_loss_r", "payoff_ratio", "expectancy_r",
    "expectancy_r_median", "r_std", "r_tstat", "breakeven_win_rate",
    "win_rate_edge", "profit_factor", "net_profit", "return_pct", "total_fees",
    "total_funding", "fee_drag_r", "gross_expectancy_r",
    "fee_share_of_gross_profit", "final_equity", "max_drawdown_pct",
    "max_drawdown_days", "cagr", "calmar", "sharpe", "sortino",
    "max_consecutive_wins", "max_consecutive_losses", "avg_bars_held",
    "avg_minutes_held", "best_trade_r", "worst_trade_r", "avg_mae_r",
    "avg_mfe_r", "long_share", "avg_stop_pct",
]


def _drawdown(equity: pd.Series) -> pd.Series:
    peak = equity.cummax()
    return equity / peak - 1.0


def _max_drawdown_duration_days(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    peak = equity.cummax()
    under = equity < peak
    if not under.any():
        return 0.0
    longest = pd.Timedelta(0)
    start: pd.Timestamp | None = None
    for ts, is_under in under.items():
        if is_under and start is None:
            start = ts
        elif not is_under and start is not None:
            longest = max(longest, ts - start)
            start = None
    if start is not None:
        longest = max(longest, under.index[-1] - start)
    return longest.total_seconds() / 86400.0


def _max_streak(flags: np.ndarray) -> int:
    best = cur = 0
    for x in flags:
        cur = cur + 1 if x else 0
        best = max(best, cur)
    return best


def exit_breakdown(trades: pd.DataFrame) -> pd.DataFrame:
    """Chiqish sabablari bo'yicha tahlil — tuzilmadagi nosozlikni ko'rsatadi."""
    if trades.empty:
        return pd.DataFrame(columns=["count", "share", "avg_r", "total_r"])
    g = trades.groupby("exit_reason")["r_multiple"]
    out = pd.DataFrame({
        "count": g.size(), "share": g.size() / len(trades),
        "avg_r": g.mean(), "total_r": g.sum(),
    })
    return out.sort_values("total_r", ascending=False)


def monthly_returns(equity: pd.Series) -> pd.Series:
    monthly = equity.resample("1ME").last().dropna()
    return monthly.pct_change().dropna()
