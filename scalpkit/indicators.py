"""Texnik indikatorlar.

Barcha funksiyalar *sabab-oqibatli* (causal): t-bar qiymati faqat t va undan
oldingi barlardan hisoblanadi. Kelajakka qarash (lookahead) yo'q.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, length: int) -> pd.Series:
    """Eksponensial siljuvchi o'rtacha."""
    return series.ewm(span=length, adjust=False, min_periods=length).mean()


def sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(length, min_periods=length).mean()


def rma(series: pd.Series, length: int) -> pd.Series:
    """Wilder tekislash (RSI/ATR/ADX ichida ishlatiladi)."""
    return series.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    ranges = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    )
    return ranges.max(axis=1)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    return rma(true_range(high, low, close), length)


def rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = rma(gain, length)
    avg_loss = rma(loss, length)
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    # avg_loss == 0 bo'lsa RSI = 100 (faqat o'sish bo'lgan holat)
    return out.where(avg_loss != 0.0, 100.0).where(avg_gain.notna(), np.nan)


def adx(
    high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Wilder ADX. (adx, plus_di, minus_di) qaytaradi."""
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=high.index
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=high.index
    )

    tr_rma = rma(true_range(high, low, close), length)
    plus_di = 100.0 * rma(plus_dm, length) / tr_rma.replace(0.0, np.nan)
    minus_di = 100.0 * rma(minus_dm, length) / tr_rma.replace(0.0, np.nan)

    di_sum = (plus_di + minus_di).replace(0.0, np.nan)
    dx = 100.0 * (plus_di - minus_di).abs() / di_sum
    return rma(dx, length), plus_di, minus_di


def bollinger(
    close: pd.Series, length: int = 20, mult: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = sma(close, length)
    # ddof=0 — TradingView bilan mos kelishi uchun (populyatsiya st. og'ishi)
    sd = close.rolling(length, min_periods=length).std(ddof=0)
    return mid, mid + mult * sd, mid - mult * sd


def keltner(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    length: int = 20,
    atr_length: int = 14,
    mult: float = 1.5,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = ema(close, length)
    band = mult * atr(high, low, close, atr_length)
    return mid, mid + band, mid - band


def donchian(high: pd.Series, low: pd.Series, length: int = 20) -> tuple[pd.Series, pd.Series]:
    """Donchian kanali — joriy bar ham hisobga olinadi."""
    return high.rolling(length, min_periods=length).max(), low.rolling(
        length, min_periods=length
    ).min()


def session_vwap(
    high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series
) -> tuple[pd.Series, pd.Series]:
    """UTC kuniga bog'langan VWAP va uning standart og'ishi.

    Kumulyativ hisob — har bir UTC kun boshida nolga tushadi. Faqat o'tgan
    barlardan foydalanadi.
    """
    typical = (high + low + close) / 3.0
    day = close.index.tz_convert("UTC").normalize() if close.index.tz is not None else close.index.normalize()
    grouper = pd.Series(day, index=close.index)

    pv = (typical * volume).groupby(grouper).cumsum()
    vv = volume.groupby(grouper).cumsum()
    vwap = pv / vv.replace(0.0, np.nan)

    # Kumulyativ og'ish: sqrt(E[p^2] - E[p]^2), hajm bilan tortilgan
    pv2 = (typical.pow(2) * volume).groupby(grouper).cumsum()
    var = (pv2 / vv.replace(0.0, np.nan)) - vwap.pow(2)
    sd = np.sqrt(var.clip(lower=0.0))
    return vwap, sd


def rolling_zscore(series: pd.Series, length: int) -> pd.Series:
    mean = series.rolling(length, min_periods=length).mean()
    sd = series.rolling(length, min_periods=length).std(ddof=0)
    return (series - mean) / sd.replace(0.0, np.nan)


def swing_low(low: pd.Series, length: int) -> pd.Series:
    """Oxirgi `length` bardagi eng past nuqta (joriy bar bilan birga)."""
    return low.rolling(length, min_periods=1).min()


def swing_high(high: pd.Series, length: int) -> pd.Series:
    return high.rolling(length, min_periods=1).max()


def slope(series: pd.Series, length: int) -> pd.Series:
    """Oddiy qiyalik: (x[t] - x[t-length]) / length, narxga nisbatan normallashtirilgan."""
    return (series - series.shift(length)) / length
