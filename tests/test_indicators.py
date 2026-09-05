"""Indikatorlarning to'g'riligi va sabab-oqibatliligi."""

import numpy as np
import pandas as pd
import pytest

from scalpkit import indicators as ind


@pytest.fixture
def ohlcv():
    idx = pd.date_range("2024-01-01", periods=500, freq="5min", tz="UTC")
    rng = np.random.default_rng(0)
    close = pd.Series(50_000 * np.exp(np.cumsum(rng.normal(0, 0.0015, 500))), index=idx)
    high = close * (1 + rng.uniform(0, 0.002, 500))
    low = close * (1 - rng.uniform(0, 0.002, 500))
    vol = pd.Series(rng.lognormal(3, 0.5, 500), index=idx)
    return high, low, close, vol


def test_ema_matches_manual_recursion():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    out = ind.ema(s, 3)
    alpha = 2 / (3 + 1)
    expected = s.iloc[0]
    for x in s.iloc[1:]:
        expected = alpha * x + (1 - alpha) * expected
    assert out.iloc[-1] == pytest.approx(expected)


def test_rsi_bounds_and_extremes():
    rising = pd.Series(np.arange(1, 60, dtype=float))
    assert ind.rsi(rising, 14).iloc[-1] == pytest.approx(100.0)
    falling = pd.Series(np.arange(60, 1, -1, dtype=float))
    assert ind.rsi(falling, 14).iloc[-1] == pytest.approx(0.0, abs=1e-9)


def test_rsi_stays_in_range(ohlcv):
    _, _, close, _ = ohlcv
    r = ind.rsi(close, 7).dropna()
    assert r.between(0, 100).all()


def test_atr_is_positive_and_bounded(ohlcv):
    high, low, close, _ = ohlcv
    a = ind.atr(high, low, close, 14).dropna()
    assert (a > 0).all()
    assert a.max() < (high - low).max() * 5


def test_adx_range(ohlcv):
    high, low, close, _ = ohlcv
    adx, plus, minus = ind.adx(high, low, close, 14)
    assert adx.dropna().between(0, 100).all()
    assert plus.dropna().between(0, 100).all()
    assert minus.dropna().between(0, 100).all()


def test_true_range_first_bar_is_high_low():
    h = pd.Series([10.0, 12.0]); l = pd.Series([8.0, 9.0]); c = pd.Series([9.0, 11.0])
    tr = ind.true_range(h, l, c)
    assert tr.iloc[0] == pytest.approx(2.0)
    assert tr.iloc[1] == pytest.approx(3.0)  # max(3, |12-9|, |9-9|)


def test_donchian_includes_current_bar():
    h = pd.Series([1.0, 5.0, 3.0]); l = pd.Series([0.0, 2.0, 1.0])
    up, dn = ind.donchian(h, l, 2)
    assert up.iloc[1] == 5.0 and dn.iloc[1] == 0.0


def test_session_vwap_resets_each_utc_day():
    # 23:50, 23:55 -> 1-kun;  00:00..00:15 -> 2-kun
    idx = pd.date_range("2024-01-01 23:50", periods=6, freq="5min", tz="UTC")
    price = pd.Series([100.0] * 2 + [200.0] * 4, index=idx)
    vol = pd.Series([1.0] * 6, index=idx)
    vwap, _ = ind.session_vwap(price, price, price, vol)

    assert vwap.iloc[1] == pytest.approx(100.0)   # 1-kun kumulyativi
    # 2-kun noldan boshlanadi: reset bo'lmaganda bu ~133 bo'lardi
    assert vwap.iloc[2] == pytest.approx(200.0)
    assert vwap.iloc[5] == pytest.approx(200.0)


@pytest.mark.parametrize("fn,args", [
    (ind.ema, (21,)), (ind.rsi, (7,)), (ind.sma, (20,)),
])
def test_indicators_are_causal(ohlcv, fn, args):
    """Kelajakdagi barlarni kesib tashlash o'tmish qiymatlarini o'zgartirmasligi kerak."""
    _, _, close, _ = ohlcv
    full = fn(close, *args)
    truncated = fn(close.iloc[:-50], *args)
    pd.testing.assert_series_equal(full.iloc[:-50].tail(100), truncated.tail(100))
