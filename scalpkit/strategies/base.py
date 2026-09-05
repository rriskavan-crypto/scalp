"""Strategiya interfeysi."""

from __future__ import annotations

from typing import Any

import pandas as pd

SIGNAL_COLUMNS = ["signal", "stop_price", "atr"]


class Strategy:
    """Barcha strategiyalar uchun umumiy asos.

    `generate()` quyidagi ustunlarni qaytaradi:
      signal      : +1 (long), -1 (short), 0 (signal yo'q) — bar YOPILGANDA hisoblanadi
      stop_price  : strukturaviy stop darajasi (keyingi bar ochilishida aniqlanadi)
      atr         : signal paytidagi ATR — stop/target va trailing uchun
    """

    name: str = "base"
    defaults: dict[str, Any] = {}

    def __init__(self, params: dict[str, Any] | None = None):
        self.params: dict[str, Any] = {**self.defaults, **(params or {})}

    def __getitem__(self, key: str) -> Any:
        return self.params[key]

    def generate(self, f: pd.DataFrame) -> pd.DataFrame:  # pragma: no cover - abstrakt
        raise NotImplementedError

    @classmethod
    def param_space(cls) -> dict[str, list[Any]]:
        """Optimizatsiya uchun qidiruv fazosi."""
        return {}

    def describe(self) -> str:
        lines = [f"Strategiya: {self.name}"]
        for k, v in sorted(self.params.items()):
            lines.append(f"  {k:<24} = {v}")
        return "\n".join(lines)


def session_mask(f: pd.DataFrame, start_hour: int, end_hour: int) -> pd.Series:
    """UTC soatlari bo'yicha savdo oynasi. start > end bo'lsa tunni kesib o'tadi."""
    hour = f["hour"]
    if start_hour <= end_hour:
        return (hour >= start_hour) & (hour < end_hour)
    return (hour >= start_hour) | (hour < end_hour)


def rolling_any(cond: pd.Series, window: int) -> pd.Series:
    """Oxirgi `window` bar ichida shart kamida bir marta bajarilganmi."""
    return cond.astype(float).rolling(window, min_periods=1).max() > 0
