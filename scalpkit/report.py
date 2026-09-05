"""Natijalarni odam o'qiy oladigan ko'rinishga keltirish."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .engine import BacktestResult
from .metrics import compute_metrics, exit_breakdown, monthly_returns


def _fmt(value: float, kind: str = "f") -> str:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "  n/a"
    return {"pct": f"{value * 100:.2f} %", "r": f"{value:+.3f} R",
            "money": f"{value:,.2f}", "f": f"{value:.2f}",
            "int": f"{value:,.0f}"}[kind]


def text_report(result: BacktestResult, title: str = "BACKTEST NATIJASI") -> str:
    m = compute_metrics(
        result.trades, result.equity, result.config.risk.initial_equity, result.days,
        days_per_year=result.config.days_per_year,
    )
    c = result.config
    w = 66
    L: list[str] = ["=" * w, title.center(w), "=" * w]

    L += [
        "",
        f"Simvol / TF        : {c.symbol} / {c.timeframe}",
        f"Strategiya         : {c.strategy.name}",
        f"Davr               : {result.start:%Y-%m-%d} — {result.end:%Y-%m-%d}"
        f"  ({result.days:.0f} kun)",
        f"Kirish usuli       : {result.meta.get('entry_mode', 'market')}",
    ]
    if result.meta.get("entry_mode") == "limit":
        L.append(f"Limit to'ldirilishi: {result.meta.get('limit_fill_rate', 0) * 100:.0f} %")

    L += ["", "-" * w, " USTUNLIK (eng muhim blok)".center(w, "-"), "-" * w,
        f"  Ekspektatsiya         {_fmt(m['expectancy_r'], 'r')} / savdo",
        f"  Yalpi (xarajatsiz)    {_fmt(m['gross_expectancy_r'], 'r')} / savdo",
        f"  Komissiya drenaji     {_fmt(-m['fee_drag_r'], 'r')} / savdo",
        f"  t-statistika          {m['r_tstat']:.2f}"
        f"   {'(statistik ishonchli)' if abs(m['r_tstat']) > 2 else '(SHOVQIN — ishonchsiz)'}",
        "",
        f"  G'alaba foizi         {_fmt(m['win_rate'], 'pct')}",
        f"  Zararsizlik nuqtasi   {_fmt(m['breakeven_win_rate'], 'pct')}"
        f"   (farq: {m['win_rate_edge'] * 100:+.2f} p.p.)",
        f"  O'rtacha g'alaba      {_fmt(m['avg_win_r'], 'r')}",
        f"  O'rtacha zarar        {_fmt(m['avg_loss_r'], 'r')}",
        f"  Payoff nisbati        {m['payoff_ratio']:.2f}",
        f"  Profit factor         {m['profit_factor']:.2f}",
    ]

    L += ["", "-" * w, " NATIJA".center(w, "-"), "-" * w,
        f"  Boshlang'ich kapital  {_fmt(c.risk.initial_equity, 'money')}",
        f"  Yakuniy kapital       {_fmt(m['final_equity'], 'money')}",
        f"  Sof foyda             {_fmt(m['net_profit'], 'money')}  ({_fmt(m['return_pct'], 'pct')})",
        f"  Yillik (CAGR)         {_fmt(m['cagr'], 'pct')}",
        f"  Maksimal drawdown     {_fmt(m['max_drawdown_pct'], 'pct')}"
        f"  ({m['max_drawdown_days']:.0f} kun)",
        f"  Sharpe / Sortino      {m['sharpe']:.2f} / {m['sortino']:.2f}",
        f"  Calmar                {m['calmar']:.2f}",
    ]

    L += ["", "-" * w, " SAVDO XULQI".center(w, "-"), "-" * w,
        f"  Savdolar soni         {m['trades']:,.0f}   ({m['trades_per_day']:.2f} / kun)",
        f"  O'rtacha davomiylik   {m['avg_minutes_held']:.0f} daqiqa",
        f"  O'rtacha stop masofa  {_fmt(m['avg_stop_pct'], 'pct')} (narxdan)",
        f"  Long ulushi           {_fmt(m['long_share'], 'pct')}",
        f"  Eng yaxshi / yomon    {m['best_trade_r']:+.2f} R / {m['worst_trade_r']:+.2f} R",
        f"  Ketma-ket g'alaba/zarar  {m['max_consecutive_wins']:.0f} / {m['max_consecutive_losses']:.0f}",
        f"  O'rtacha MFE / MAE    {m['avg_mfe_r']:+.2f} R / {m['avg_mae_r']:+.2f} R",
        f"  Jami komissiya        {_fmt(m['total_fees'], 'money')}"
        f"   (yalpi foydaning {m['fee_share_of_gross_profit'] * 100:.0f} %)",
    ]

    if not result.trades.empty:
        L += ["", "-" * w, " CHIQISH SABABLARI".center(w, "-"), "-" * w,
              f"  {'sabab':<16}{'soni':>6}{'ulush':>8}{'ort. R':>9}{'jami R':>10}"]
        for reason, row in exit_breakdown(result.trades).iterrows():
            L.append(f"  {reason:<16}{row['count']:>6.0f}{row['share'] * 100:>7.1f}%"
                     f"{row['avg_r']:>+9.3f}{row['total_r']:>+10.1f}")

    monthly = monthly_returns(result.equity)
    if len(monthly) > 1:
        L += ["", "-" * w, " OYLIK NATIJA".center(w, "-"), "-" * w]
        for ts, val in monthly.items():
            bar = "#" * min(int(abs(val) * 200), 28)
            L.append(f"  {ts:%Y-%m}  {val * 100:>+7.2f} %  {bar}")

    L += ["", "=" * w]
    return "\n".join(L)


def equity_svg(result: BacktestResult, width: int = 900, height: int = 340) -> str:
    """Ekviti egri chizig'i — tashqi kutubxonasiz, sof SVG."""
    eq = result.equity.dropna()
    if len(eq) < 2:
        return "<svg xmlns='http://www.w3.org/2000/svg'></svg>"

    eq = eq.iloc[:: max(len(eq) // 1500, 1)]
    y = eq.to_numpy(float)
    pad_l, pad_r, pad_t, pad_b = 62, 16, 24, 30
    pw, ph = width - pad_l - pad_r, height - pad_t - pad_b

    lo, hi = float(y.min()), float(y.max())
    span = max(hi - lo, 1e-9)
    lo, hi = lo - span * 0.06, hi + span * 0.06
    span = hi - lo

    xs = pad_l + np.linspace(0, pw, len(y))
    ys = pad_t + ph - (y - lo) / span * ph
    line = " ".join(f"{x:.1f},{v:.1f}" for x, v in zip(xs, ys))
    area = f"{xs[0]:.1f},{pad_t + ph:.1f} " + line + f" {xs[-1]:.1f},{pad_t + ph:.1f}"

    peak = np.maximum.accumulate(y)
    dd_ys = pad_t + ph - (peak - lo) / span * ph
    peak_line = " ".join(f"{x:.1f},{v:.1f}" for x, v in zip(xs, dd_ys))

    up = y[-1] >= y[0]
    color = "#16a34a" if up else "#dc2626"
    grid, labels = [], []
    for frac in (0, 0.25, 0.5, 0.75, 1.0):
        gy = pad_t + ph * frac
        val = hi - span * frac
        grid.append(f"<line x1='{pad_l}' y1='{gy:.1f}' x2='{width - pad_r}' y2='{gy:.1f}' "
                    f"stroke='#e5e7eb' stroke-width='1'/>")
        labels.append(f"<text x='{pad_l - 8}' y='{gy + 4:.1f}' text-anchor='end' "
                      f"font-size='11' fill='#6b7280'>{val:,.0f}</text>")

    x_labels = []
    for frac in (0, 0.5, 1.0):
        i = int(frac * (len(eq) - 1))
        x_labels.append(
            f"<text x='{xs[i]:.1f}' y='{height - 8}' text-anchor='middle' "
            f"font-size='11' fill='#6b7280'>{eq.index[i]:%Y-%m-%d}</text>"
        )

    return f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {width} {height}' width='{width}' height='{height}'>
<rect width='{width}' height='{height}' fill='#ffffff'/>
{''.join(grid)}
<polygon points='{area}' fill='{color}' opacity='0.10'/>
<polyline points='{peak_line}' fill='none' stroke='#9ca3af' stroke-width='1' stroke-dasharray='4 3'/>
<polyline points='{line}' fill='none' stroke='{color}' stroke-width='1.8'/>
{''.join(labels)}{''.join(x_labels)}
<text x='{pad_l}' y='16' font-size='12' fill='#374151' font-family='sans-serif'>
Ekviti — {result.config.symbol} {result.config.timeframe} · {result.config.strategy.name}</text>
</svg>"""


def save_report(result: BacktestResult, outdir: str | Path,
                title: str = "BACKTEST NATIJASI") -> dict[str, Path]:
    """Hisobot, savdolar jadvali va grafikni diskka yozadi."""
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "report": out / "report.txt",
        "trades": out / "trades.csv",
        "equity": out / "equity.csv",
        "chart": out / "equity.svg",
        "metrics": out / "metrics.csv",
    }
    paths["report"].write_text(text_report(result, title), encoding="utf-8")
    result.trades.to_csv(paths["trades"], index=False)
    result.equity.to_csv(paths["equity"], index_label="time")
    paths["chart"].write_text(equity_svg(result), encoding="utf-8")
    m = compute_metrics(result.trades, result.equity,
                        result.config.risk.initial_equity, result.days,
                        days_per_year=result.config.days_per_year)
    pd.Series(m).to_csv(paths["metrics"], header=["value"], index_label="metric")
    return paths
