"""Walk-forward tekshiruvi — strategiya haqiqatan ishlaydimi yoki yo'qmi shu hal qiladi.

Bir marta optimizatsiya qilingan natija hech narsani isbotlamaydi: yetarlicha
parametr sinab ko'rilsa, har qanday shovqinda "chiroyli" egri chiziq topiladi.
Walk-forward buni oldini oladi:

    [--- o'rgatish (IS) ---][- test (OOS) -]
              [--- o'rgatish (IS) ---][- test (OOS) -]
                        [--- o'rgatish (IS) ---][- test (OOS) -]

Parametrlar HAR SAFAR faqat o'tmishdan tanlanadi, natija esa faqat
ko'rilmagan kelajakdan yig'iladi. Yakuniy OOS egri chizig'i — real savdoga
eng yaqin baho.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .config import Config
from .metrics import compute_metrics
from .optimize import Evaluator, OBJECTIVES, grid_search
from .strategies import get_strategy


@dataclass
class WalkForwardResult:
    folds: pd.DataFrame          # har bir bosqich bo'yicha xulosa
    oos_trades: pd.DataFrame     # barcha OOS savdolar birlashtirilgan
    oos_equity: pd.Series        # zanjirlangan OOS ekviti
    oos_metrics: dict[str, float]
    is_metrics: dict[str, float]

    @property
    def efficiency(self) -> float:
        """OOS / IS ekspektatsiya nisbati.

        > 0.5  — sog'lom
        0-0.5  — qisman overfitting
        < 0    — strategiya ko'rilmagan ma'lumotda ishlamaydi
        """
        is_e = self.is_metrics.get("expectancy_r", 0.0)
        oos_e = self.oos_metrics.get("expectancy_r", 0.0)
        return oos_e / is_e if is_e not in (0.0, None) else np.nan


def walk_forward(
    df: pd.DataFrame,
    cfg: Config,
    strategy_name: str = "momentum_pullback",
    space: dict[str, list[Any]] | None = None,
    n_folds: int = 6,
    train_days: int = 120,
    test_days: int = 30,
    objective: str = "expectancy",
    max_combos: int = 150,
    anchored: bool = False,
    verbose: bool = True,
) -> WalkForwardResult:
    """Bosqichma-bosqich optimizatsiya va ko'rilmagan ma'lumotda test."""
    base_strategy = get_strategy(strategy_name, cfg.strategy.params)
    space = space or base_strategy.param_space(base_strategy.params)
    space_keys = list(space)
    obj_fn = OBJECTIVES[objective]

    start, end = df.index[0], df.index[-1]
    total_days = (end - start).days
    need = train_days + n_folds * test_days
    if total_days < need:
        n_folds = max(1, (total_days - train_days) // test_days)
        if verbose:
            print(f"  Ma'lumot {total_days} kun — bosqichlar soni {n_folds} ga kamaytirildi.")
    if n_folds < 1:
        raise ValueError(
            f"Walk-forward uchun kamida {train_days + test_days} kunlik ma'lumot kerak "
            f"(mavjud: {total_days} kun)."
        )

    fold_rows: list[dict[str, Any]] = []
    oos_trade_frames: list[pd.DataFrame] = []
    oos_equity_parts: list[pd.Series] = []
    is_trade_frames: list[pd.DataFrame] = []
    equity = cfg.risk.initial_equity

    for k in range(n_folds):
        test_end = end - pd.Timedelta(days=test_days * (n_folds - k - 1))
        test_start = test_end - pd.Timedelta(days=test_days)
        train_start = start if anchored else test_start - pd.Timedelta(days=train_days)
        train_start = max(train_start, start)

        train_df = df.loc[train_start:test_start]
        test_df = df.loc[train_start:test_end]  # warmup uchun IS ni ham qo'shamiz

        if len(train_df) < 500 or len(test_df) < 500:
            continue

        if verbose:
            print(f"\n[{k + 1}/{n_folds}] o'rgatish {train_start:%Y-%m-%d}→{test_start:%Y-%m-%d}"
                  f"  |  test {test_start:%Y-%m-%d}→{test_end:%Y-%m-%d}")

        # --- 1) IS optimizatsiya ---
        res = grid_search(train_df, cfg, strategy_name, space, objective,
                          max_combos=max_combos, seed=k, verbose=False)
        if res.empty:
            continue
        params = {k2: res.iloc[0][k2] for k2 in space_keys if k2 in res.columns}
        params = _coerce(params, space)

        # --- 2) OOS test ---
        ev = Evaluator(test_df, cfg, strategy_name)
        _, full = ev.evaluate(params, initial_equity=equity)

        oos_mask = full.trades["entry_time"] >= test_start
        oos_trades = full.trades[oos_mask].copy()
        oos_eq = full.equity.loc[test_start:test_end]

        is_trades = full.trades[~oos_mask]
        if not is_trades.empty:
            is_trade_frames.append(is_trades)

        # OOS ekvitini oldingi bosqich oxiridan davom ettiramiz
        if not oos_eq.empty:
            offset = equity - float(oos_eq.iloc[0])
            oos_equity_parts.append(oos_eq + offset)
            equity = float(oos_eq.iloc[-1]) + offset

        if not oos_trades.empty:
            oos_trade_frames.append(oos_trades)

        m_oos = compute_metrics(oos_trades, oos_eq, cfg.risk.initial_equity,
                                max((test_end - test_start).days, 1),
                                days_per_year=cfg.days_per_year)
        fold_rows.append({
            "fold": k + 1,
            "train_start": train_start, "test_start": test_start, "test_end": test_end,
            "is_score": float(res.iloc[0]["score"]),
            "is_expectancy_r": float(res.iloc[0]["expectancy_r"]),
            "oos_trades": m_oos["trades"],
            "oos_expectancy_r": m_oos["expectancy_r"],
            "oos_win_rate": m_oos["win_rate"],
            "oos_profit_factor": m_oos["profit_factor"],
            "equity_after": equity,
            **{f"p_{k2}": v for k2, v in params.items()},
        })
        if verbose:
            print(f"     IS ekspektatsiya {res.iloc[0]['expectancy_r']:+.3f}R  →  "
                  f"OOS {m_oos['expectancy_r']:+.3f}R  ({m_oos['trades']:.0f} savdo)")

    if not fold_rows:
        raise RuntimeError("Hech bir walk-forward bosqichi bajarilmadi — ma'lumot yetarli emas.")

    oos_trades_all = (
        pd.concat(oos_trade_frames, ignore_index=True) if oos_trade_frames else pd.DataFrame()
    )
    is_trades_all = (
        pd.concat(is_trade_frames, ignore_index=True) if is_trade_frames else pd.DataFrame()
    )
    oos_equity = (
        pd.concat(oos_equity_parts) if oos_equity_parts
        else pd.Series([cfg.risk.initial_equity], index=[end])
    )
    oos_equity = oos_equity[~oos_equity.index.duplicated(keep="last")].sort_index()

    oos_days = max(sum(r["oos_trades"] > -1 for r in fold_rows) * test_days, 1)
    return WalkForwardResult(
        folds=pd.DataFrame(fold_rows),
        oos_trades=oos_trades_all,
        oos_equity=oos_equity,
        oos_metrics=compute_metrics(oos_trades_all, oos_equity,
                                    cfg.risk.initial_equity, oos_days,
                                    days_per_year=cfg.days_per_year),
        is_metrics=compute_metrics(is_trades_all, oos_equity,
                                   cfg.risk.initial_equity, max(train_days, 1),
                                   days_per_year=cfg.days_per_year),
    )


def _coerce(params: dict[str, Any], space: dict[str, list[Any]]) -> dict[str, Any]:
    """Qidiruv natijasidagi qiymatlarni asl turiga qaytaradi (pandas float qiladi)."""
    out: dict[str, Any] = {}
    for k, v in params.items():
        sample = space[k][0]
        if isinstance(sample, bool):
            out[k] = bool(v)
        elif isinstance(sample, int):
            out[k] = int(round(float(v)))
        elif isinstance(sample, str):
            out[k] = str(v)
        else:
            out[k] = float(v)
    return out


def walk_forward_report(wf: WalkForwardResult) -> str:
    L = ["=" * 66, "WALK-FORWARD TEKSHIRUVI".center(66), "=" * 66, ""]
    cols = ["fold", "test_start", "test_end", "is_expectancy_r",
            "oos_trades", "oos_expectancy_r", "oos_win_rate"]
    view = wf.folds[[c for c in cols if c in wf.folds.columns]].copy()
    view["test_start"] = view["test_start"].dt.strftime("%Y-%m-%d")
    view["test_end"] = view["test_end"].dt.strftime("%Y-%m-%d")
    L.append(view.round(3).to_string(index=False))

    o, i = wf.oos_metrics, wf.is_metrics
    L += ["", "-" * 66,
          f"  OOS savdolar          {o['trades']:.0f}",
          f"  OOS ekspektatsiya     {o['expectancy_r']:+.3f} R / savdo",
          f"  OOS g'alaba foizi     {o['win_rate'] * 100:.1f} %"
          f"  (zararsizlik: {o['breakeven_win_rate'] * 100:.1f} %)",
          f"  OOS profit factor     {o['profit_factor']:.2f}",
          f"  OOS max drawdown      {o['max_drawdown_pct'] * 100:.2f} %",
          f"  OOS t-statistika      {o['r_tstat']:.2f}",
          f"  IS  ekspektatsiya     {i['expectancy_r']:+.3f} R / savdo",
          f"  WF samaradorligi      {wf.efficiency:.2f}   "
          f"({'sog`lom' if wf.efficiency > 0.5 else 'overfitting xavfi'})",
          "=" * 66]
    return "\n".join(L)
