"""Parametr qidiruvi.

OGOHLANTIRISH: bitta ma'lumot to'plamida optimizatsiya qilish — o'z-o'zini
aldashning eng keng tarqalgan yo'li. Bu yerdagi natijalar **faqat**
`walkforward` moduli bilan tekshirilgandan keyin ma'noga ega bo'ladi.
"""

from __future__ import annotations

import itertools
import random
from typing import Any, Callable

import numpy as np
import pandas as pd

from .config import Config
from .engine import run_backtest
from .features import DEFAULT_FEATURE_PARAMS, build_features, warmup_bars
from .metrics import compute_metrics
from .strategies import get_strategy

Objective = Callable[[dict[str, float]], float]


def objective_expectancy(m: dict[str, float]) -> float:
    """Ekspektatsiya x sqrt(savdolar soni) — kam savdoli tasodifiy natijalarni jazolaydi."""
    if m["trades"] < 20:
        return -np.inf
    return m["expectancy_r"] * np.sqrt(m["trades"])


def objective_profit_factor(m: dict[str, float]) -> float:
    if m["trades"] < 20:
        return -np.inf
    return float(np.clip(m["profit_factor"], 0, 10))


def objective_calmar(m: dict[str, float]) -> float:
    if m["trades"] < 20 or m["max_drawdown_pct"] >= 0:
        return -np.inf
    return m["cagr"] / abs(m["max_drawdown_pct"])


def objective_tstat(m: dict[str, float]) -> float:
    """Statistik ishonchlilik — ustunlikning shovqinga nisbati."""
    if m["trades"] < 20:
        return -np.inf
    return m["r_tstat"]


OBJECTIVES: dict[str, Objective] = {
    "expectancy": objective_expectancy,
    "profit_factor": objective_profit_factor,
    "calmar": objective_calmar,
    "tstat": objective_tstat,
}


class Evaluator:
    """Parametrlar to'plamini baholaydi; feature'larni keshlaydi."""

    def __init__(self, df: pd.DataFrame, cfg: Config, strategy_name: str):
        self.df = df
        self.cfg = cfg
        self.strategy_name = strategy_name
        self._cache: dict[tuple, pd.DataFrame] = {}

    def features_for(self, params: dict[str, Any]) -> pd.DataFrame:
        """Feature'lar faqat ularga ta'sir qiluvchi parametr o'zgarganda qayta quriladi."""
        feat_params = {k: v for k, v in params.items() if k in DEFAULT_FEATURE_PARAMS}
        key = tuple(sorted(feat_params.items()))
        if key not in self._cache:
            self._cache[key] = build_features(self.df, feat_params)
        return self._cache[key]

    def evaluate(self, params: dict[str, Any],
                 initial_equity: float | None = None) -> tuple[dict[str, float], Any]:
        f = self.features_for(params)
        strat = get_strategy(self.strategy_name, params)
        cfg = self.cfg.copy_with_params(params)
        if initial_equity is not None:
            cfg.risk.initial_equity = initial_equity
        res = run_backtest(f, strat.generate(f), cfg, strat.params,
                           warmup=warmup_bars(params))
        m = compute_metrics(res.trades, res.equity, cfg.risk.initial_equity, res.days,
                            days_per_year=cfg.days_per_year)
        return m, res


def grid_search(df: pd.DataFrame, cfg: Config, strategy_name: str,
                space: dict[str, list[Any]] | None = None,
                objective: str = "expectancy",
                max_combos: int | None = 400,
                seed: int = 0,
                verbose: bool = True) -> pd.DataFrame:
    """Parametr fazosini qidiradi va natijalarni reyting bo'yicha qaytaradi."""
    base_strategy = get_strategy(strategy_name, cfg.strategy.params)
    space = space or base_strategy.param_space(base_strategy.params)
    obj_fn = OBJECTIVES[objective]

    keys = list(space)
    all_combos = list(itertools.product(*(space[k] for k in keys)))
    if max_combos and len(all_combos) > max_combos:
        random.Random(seed).shuffle(all_combos)
        all_combos = all_combos[:max_combos]

    ev = Evaluator(df, cfg, strategy_name)
    rows = []
    for n, combo in enumerate(all_combos, 1):
        params = dict(zip(keys, combo))
        try:
            m, _ = ev.evaluate(params)
        except Exception:  # noqa: BLE001 — bitta yomon kombinatsiya qidiruvni to'xtatmasin
            continue
        score = obj_fn(m)
        rows.append({
            **params, "score": score, "trades": m["trades"],
            "expectancy_r": m["expectancy_r"], "win_rate": m["win_rate"],
            "profit_factor": m["profit_factor"], "return_pct": m["return_pct"],
            "max_dd_pct": m["max_drawdown_pct"], "r_tstat": m["r_tstat"],
            "trades_per_day": m["trades_per_day"],
        })
        if verbose and n % 25 == 0:
            print(f"  {n}/{len(all_combos)} kombinatsiya tekshirildi", end="\r")

    if verbose:
        print(f"  {len(rows)}/{len(all_combos)} kombinatsiya baholandi.        ")
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True)
    return out.replace([np.inf, -np.inf], np.nan)


def best_params(results: pd.DataFrame, space_keys: list[str]) -> dict[str, Any]:
    if results.empty:
        return {}
    row = results.iloc[0]
    return {k: row[k] for k in space_keys if k in results.columns}


def robustness_check(results: pd.DataFrame, param: str) -> pd.DataFrame:
    """Bitta parametr bo'yicha natija barqarormi?

    Agar faqat bitta qiymatda natija yaxshi bo'lsa — bu overfitting belgisi.
    Yaxshi parametr *plato* hosil qiladi, cho'qqi emas.
    """
    if results.empty or param not in results.columns:
        return pd.DataFrame()
    g = results.groupby(param)["expectancy_r"]
    return pd.DataFrame({
        "n": g.size(), "ort_expectancy_r": g.mean(),
        "median": g.median(), "eng_yaxshi": g.max(), "eng_yomon": g.min(),
    }).round(4)
