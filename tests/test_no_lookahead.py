"""Kelajakka qarash (lookahead) yo'qligini tekshirish.

Bu backtestdagi eng xavfli xato turi: u har doim natijani chiroyli qiladi va
real savdoda darhol yo'qoladi. Asosiy tamoyil: kelajakdagi barlarni kesib
tashlash o'tmishdagi hech narsani o'zgartirmasligi kerak.
"""

import numpy as np
import pandas as pd
import pytest

from scalpkit.config import Config
from scalpkit.data import generate_synthetic
from scalpkit.data.loader import align_htf, resample_ohlcv
from scalpkit.engine import run_backtest
from scalpkit.features import build_features, warmup_bars
from scalpkit.strategies import get_strategy

CUT = 400  # oxiridan nechta bar kesiladi


@pytest.fixture(scope="module")
def data():
    return generate_synthetic(n_bars=12_000, seed=11)


def test_features_do_not_change_when_future_is_removed(data):
    full = build_features(data)
    truncated = build_features(data.iloc[:-CUT])
    numeric = [c for c in full.columns if full[c].dtype.kind in "fb"]
    pd.testing.assert_frame_equal(
        full[numeric].iloc[:-CUT].tail(300),
        truncated[numeric].tail(300),
        check_dtype=False,
    )


def test_signals_do_not_change_when_future_is_removed(data):
    strat = get_strategy("momentum_pullback")
    full = strat.generate(build_features(data))
    truncated = strat.generate(build_features(data.iloc[:-CUT]))
    pd.testing.assert_frame_equal(
        full.iloc[:-CUT].tail(300), truncated.tail(300), check_dtype=False
    )


def test_trades_do_not_change_when_future_is_removed(data):
    cfg = Config()
    strat = get_strategy("momentum_pullback")

    def trades_for(df):
        f = build_features(df)
        res = run_backtest(f, strat.generate(f), cfg, strat.params, warmup=warmup_bars())
        return res.trades

    full = trades_for(data)
    truncated = trades_for(data.iloc[:-CUT])
    if full.empty or truncated.empty:
        pytest.skip("Bu namunada savdo yo'q")

    cutoff = data.index[-CUT]
    # Kesilgan sanadan ancha oldin yopilgan savdolar bir xil bo'lishi shart
    margin = cutoff - pd.Timedelta("6h")
    a = full[full["exit_time"] < margin].reset_index(drop=True)
    b = truncated[truncated["exit_time"] < margin].reset_index(drop=True)
    assert len(a) == len(b)
    pd.testing.assert_series_equal(a["entry_time"], b["entry_time"])
    pd.testing.assert_series_equal(a["net_pnl"], b["net_pnl"])


def test_htf_alignment_never_uses_an_unclosed_bar(data):
    """H1 bar 11:00 da yopiladi — 10:30 dagi M5 bar undan foydalana olmaydi."""
    htf = resample_ohlcv(data, "1h")
    aligned = align_htf(data.index, htf[["close"]], "1h")

    for ts in data.index[100:400:37]:
        value = aligned.loc[ts, "close"]
        if pd.isna(value):
            continue
        # Ishlatilgan H1 barning yopilish vaqti joriy vaqtdan katta bo'lmasligi kerak
        source = htf[htf["close"] == value]
        assert not source.empty
        bar_close_time = source.index[-1] + pd.Timedelta("1h")
        assert bar_close_time <= ts, f"{ts} da hali yopilmagan H1 bar ishlatilgan"


def test_entry_always_follows_a_prior_signal_bar(data):
    """Kirish har doim signal baridan KEYIN va limit oynasi ichida bo'lishi kerak.

    `entry_mode: limit` da kutayotgan order bir necha bar keyin to'ldirilishi
    mumkin, shuning uchun invariant "aynan keyingi bar" emas, balki
    "signal baridan keyin, lekin entry_limit_bars oynasi ichida".
    """
    cfg = Config()
    strat = get_strategy("momentum_pullback")
    f = build_features(data)
    sig = strat.generate(f)
    res = run_backtest(f, sig, cfg, strat.params, warmup=warmup_bars())
    if res.trades.empty:
        pytest.skip("Bu namunada savdo yo'q")

    window = int(strat.params["entry_limit_bars"])
    signals = sig["signal"].to_numpy()

    for _, t in res.trades.iterrows():
        entry_i = f.index.get_loc(t["entry_time"])
        lo = max(entry_i - window, 0)
        prior = signals[lo:entry_i]                     # kirish barini O'Z ICHIGA OLMAYDI
        matching = np.flatnonzero(prior == t["side"])
        assert matching.size > 0, (
            f"{t['entry_time']} da kirish bor, lekin oldingi {window} barda "
            f"{t['side']} tomonli signal yo'q"
        )
        signal_time = f.index[lo + matching[-1]]
        assert t["entry_time"] > signal_time


def test_market_entry_uses_exactly_the_next_bar_open(data):
    """`market` rejimida kirish signal baridan keyingi barning ochilishida."""
    cfg = Config()
    strat = get_strategy("momentum_pullback", {"entry_mode": "market"})
    f = build_features(data)
    sig = strat.generate(f)
    res = run_backtest(f, sig, cfg, strat.params, warmup=warmup_bars())
    if res.trades.empty:
        pytest.skip("Bu namunada savdo yo'q")

    for _, t in res.trades.iterrows():
        entry_i = f.index.get_loc(t["entry_time"])
        assert sig["signal"].iloc[entry_i - 1] == t["side"]
        # Kirish narxi o'sha barning ochilishi (sirpanish qo'shilgan holda)
        assert t["entry_price"] == pytest.approx(
            f["open"].iloc[entry_i] * (1 + t["side"] * cfg.cost.slippage_bps * 1e-4)
        )
