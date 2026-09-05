"""OHLCV ma'lumotlarini yuklash, tekshirish va qayta namunalash."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OHLCV = ["open", "high", "low", "close", "volume"]


def load_csv(path: str | Path) -> pd.DataFrame:
    """CSV faylni o'qiydi. Birinchi ustun vaqt indeksi bo'lishi kerak."""
    df = pd.read_csv(path)
    time_col = df.columns[0]
    df[time_col] = pd.to_datetime(df[time_col], utc=True, format="mixed")
    df = df.set_index(time_col)
    df.index.name = "time"
    df.columns = [c.lower() for c in df.columns]
    missing = [c for c in OHLCV if c not in df.columns]
    if missing:
        raise ValueError(f"CSV da ustunlar yetishmayapti: {missing}")
    return validate_ohlcv(df[OHLCV])


def save_csv(df: pd.DataFrame, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index_label="time")


def validate_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Takrorlar, tartibsizlik va mantiqsiz barlarni tozalaydi."""
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df = df.astype(float)

    bad = (
        df[OHLCV].isna().any(axis=1)
        | (df["high"] < df["low"])
        | (df["high"] < df[["open", "close"]].max(axis=1) - 1e-9)
        | (df["low"] > df[["open", "close"]].min(axis=1) + 1e-9)
        | (df[["open", "high", "low", "close"]] <= 0).any(axis=1)
    )
    if bad.any():
        df = df[~bad]
    return df


def gap_report(df: pd.DataFrame, timeframe: str = "5min") -> pd.DataFrame:
    """Yetishmayotgan barlarni topadi (birja uzilishi / yuklash xatosi)."""
    step = pd.Timedelta(timeframe)
    deltas = df.index.to_series().diff()
    gaps = deltas[deltas > step]
    return pd.DataFrame({"gap": gaps, "missing_bars": (gaps / step - 1).astype("Int64")})


def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Yuqori timeframega o'tkazish (masalan '1h')."""
    out = df.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    return out.dropna(subset=["open", "high", "low", "close"])


def align_htf(ltf_index: pd.DatetimeIndex, htf: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Yuqori TF qiymatlarini quyi TF indeksiga *kelajakka qaramasdan* ulash.

    Muhim: H1 bar 10:00–11:00 faqat 11:00 da yopiladi. Shuning uchun uni bir
    barga suramiz — 11:00 dan keyingi M5 barlar undan foydalanadi. Aks holda
    backtest natijasi soxta bo'ladi.
    """
    shifted = htf.shift(1)
    shifted.index = shifted.index + pd.Timedelta(rule)
    return shifted.reindex(ltf_index, method="ffill")
