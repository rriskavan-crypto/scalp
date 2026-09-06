"""Donchian breakout — swing / trendni kuzatish strategiyasi.

Asosiy dizayn qarori: **maqsad qo'yilmaydi**. Trend-following foydasi kam
sonli juda katta yutuqlardan keladi, va 3R da maqsad qo'yish aynan
o'shalarni kesib tashlaydi. Bu testlar shu qarorni va uni buzadigan
sizib o'tishlarni qulflaydi.
"""

import numpy as np
import pandas as pd
import pytest

from scalpkit.config import Config
from scalpkit.data import generate_synthetic
from scalpkit.data.loader import resample_ohlcv
from scalpkit.engine import run_backtest
from scalpkit.features import build_features
from scalpkit.profiles import BTCUSD, XAUUSD, for_timeframe
from scalpkit.strategies import get_strategy
from scalpkit.strategies.donchian_breakout import DonchianBreakout


@pytest.fixture(scope="module")
def h4_features():
    df = resample_ohlcv(generate_synthetic(n_bars=120_000, asset="btc", seed=11), "4h")
    return df, build_features(df)


# --------------------------------------------------------------- dizayn
def test_no_profit_target_by_default():
    """`tp2_r = 0` => dvigatel maqsadni umuman qo'ymaydi."""
    p = DonchianBreakout().params
    assert p["tp2_r"] == 0.0
    assert p["tp1_fraction"] == 0.0
    assert p["be_trigger_r"] > 100, "zararsizlikka o'tish trendni bo'g'adi"


def test_engine_treats_zero_target_as_no_target():
    from scalpkit.broker.base import SymbolSpec  # noqa: F401  (import sog'ligi)

    idx = pd.date_range("2024-01-01", periods=6, freq="4h", tz="UTC")
    f = pd.DataFrame({"open": 100.0, "high": 100.0, "low": 100.0,
                      "close": 100.0, "volume": 1.0, "ema_fast": 0.0}, index=idx)
    f.loc[idx[2:], ["open", "high", "low", "close"]] = 100.0
    sig = pd.DataFrame({"signal": np.int8(0), "stop_price": np.nan,
                        "atr": 1.0, "entry_ref": np.nan}, index=idx)
    sig.loc[idx[0], ["signal", "stop_price"]] = [1, 98.0]
    sig["signal"] = sig["signal"].astype(np.int8)

    cfg = Config()
    cfg.cost.taker_fee_bps = cfg.cost.maker_fee_bps = 0.0
    cfg.cost.slippage_bps = cfg.cost.stop_slippage_bps = 0.0
    cfg.cost.apply_funding = False

    params = {**DonchianBreakout().params, "entry_mode": "market"}
    res = run_backtest(f, sig, cfg, params, warmup=1)
    if res.trades.empty:
        pytest.skip("savdo ochilmadi")
    # tp2 amalda cheksizlikka surilgani uchun narxdan juda uzoqda bo'lishi kerak
    assert res.trades.iloc[0]["tp2"] > 1000.0


def test_profile_target_does_not_leak_into_the_trend_strategy():
    """`tp2_r = 3.0` (oltin pullback profili) Donchian'ga o'tmasligi shart."""
    for base in (BTCUSD, XAUUSD):
        for tf in ("15m", "1h", "4h", "1d"):
            cfg = for_timeframe(base, tf).apply(Config(), "donchian_breakout")
            params = get_strategy("donchian_breakout", cfg.strategy.params).params
            assert params["tp2_r"] == 0.0, f"{base.name}_{tf}: maqsad sizib o'tdi"


# --------------------------------------------------------------- signal
def test_signal_only_fires_on_a_channel_break(h4_features):
    df, f = h4_features
    strat = DonchianBreakout({"require_trend_filter": False, "cooldown_len": 0,
                              "min_atr_pct": 0.0, "max_atr_pct": 1.0})
    sig = strat.generate(f)
    entry_len = strat.params["entry_len"]
    prior_high = f["high"].rolling(entry_len, min_periods=entry_len).max().shift(1)
    prior_low = f["low"].rolling(entry_len, min_periods=entry_len).min().shift(1)

    longs = sig["signal"] == 1
    shorts = sig["signal"] == -1
    assert longs.sum() > 0 and shorts.sum() > 0
    assert (f.loc[longs, "close"] > prior_low[longs]).all()
    assert (f.loc[longs, "close"] > prior_high[longs]).all()
    assert (f.loc[shorts, "close"] < prior_low[shorts]).all()


def test_channel_excludes_the_current_bar(h4_features):
    """Joriy bar kanalga kirsa, narx doim 'o'z cho'qqisini' buzgan bo'lardi."""
    _, f = h4_features
    sig = DonchianBreakout({"require_trend_filter": False, "cooldown_len": 0,
                            "min_atr_pct": 0.0, "max_atr_pct": 1.0}).generate(f)
    # Kanal joriy barni o'z ichiga olganda signal deyarli hech qachon
    # bo'lmaydi (close > o'zining maksimumi mumkin emas)
    assert (sig["signal"] != 0).sum() > 20


def test_cooldown_reduces_repeated_breakouts(h4_features):
    _, f = h4_features
    common = {"require_trend_filter": False, "min_atr_pct": 0.0, "max_atr_pct": 1.0}
    no_cd = (DonchianBreakout({**common, "cooldown_len": 0})
             .generate(f)["signal"] != 0).sum()
    with_cd = (DonchianBreakout({**common, "cooldown_len": 6})
               .generate(f)["signal"] != 0).sum()
    assert with_cd < no_cd


def test_trend_filter_reduces_counter_trend_entries(h4_features):
    _, f = h4_features
    common = {"cooldown_len": 0, "min_atr_pct": 0.0, "max_atr_pct": 1.0}
    off = (DonchianBreakout({**common, "require_trend_filter": False})
           .generate(f)["signal"] != 0).sum()
    on = (DonchianBreakout({**common, "require_trend_filter": True})
          .generate(f)["signal"] != 0).sum()
    assert on < off


def test_exit_channel_columns_are_emitted(h4_features):
    _, f = h4_features
    sig = DonchianBreakout().generate(f)
    assert {"exit_long", "exit_short"} <= set(sig.columns)
    assert sig["exit_long"].dtype == bool
    assert sig["exit_long"].sum() > 0 and sig["exit_short"].sum() > 0
    # Ikkalasi bir vaqtda yonmasligi kerak (chiqish kanali qarama-qarshi)
    assert (sig["exit_long"] & sig["exit_short"]).sum() == 0


def test_engine_honours_the_strategy_exit_signal(h4_features):
    df, f = h4_features
    cfg = for_timeframe(BTCUSD, "4h").apply(Config(), "donchian_breakout")
    strat = get_strategy("donchian_breakout", cfg.strategy.params)
    res = run_backtest(f, strat.generate(f), cfg, strat.params, warmup=250)
    if res.trades.empty:
        pytest.skip("savdo yo'q")
    assert "signal_exit" in set(res.trades["exit_reason"]), \
        "kanal chiqish signali hech qachon ishlamadi"


# --------------------------------------------------------------- lookahead
def test_signals_do_not_change_when_the_future_is_removed(h4_features):
    df, _ = h4_features
    cut = 120
    strat = DonchianBreakout()
    full = strat.generate(build_features(df))
    truncated = strat.generate(build_features(df.iloc[:-cut]))
    cols = ["signal", "stop_price", "exit_long", "exit_short"]
    pd.testing.assert_frame_equal(
        full[cols].iloc[:-cut].tail(80), truncated[cols].tail(80), check_dtype=False
    )


# --------------------------------------------------------------- xulq
def test_trend_following_shows_its_signature_payoff(h4_features):
    """Past g'alaba foizi, yuqori payoff — trend-following imzosi.

    Bu foyda kafolati emas: sintetik ma'lumot martingale. Tekshirilayotgan
    narsa — chiqish tuzilmasi dumni saqlab qolyaptimi.
    """
    _, f = h4_features
    cfg = for_timeframe(BTCUSD, "4h").apply(Config(), "donchian_breakout")
    strat = get_strategy("donchian_breakout", cfg.strategy.params)
    res = run_backtest(f, strat.generate(f), cfg, strat.params, warmup=250)
    if len(res.trades) < 30:
        pytest.skip("savdolar kam")

    r = res.trades["r_multiple"]
    assert (r > 0).mean() < 0.50, "trend-following g'alaba foizi past bo'lishi kerak"
    assert r.max() > 2.5, "katta yutuq yo'q — dum kesilgan bo'lishi mumkin"


def test_capping_profits_hurts_the_trend_strategy(h4_features):
    """Maqsad qo'yish eng katta yutuqni kesib tashlashi kerak."""
    _, f = h4_features
    cfg = for_timeframe(BTCUSD, "4h").apply(Config(), "donchian_breakout")
    strat = get_strategy("donchian_breakout", cfg.strategy.params)
    sig = strat.generate(f)

    free = run_backtest(f, sig, cfg, strat.params, warmup=250)
    capped = run_backtest(f, sig, cfg, {**strat.params, "tp2_r": 2.0}, warmup=250)
    if free.trades.empty or capped.trades.empty:
        pytest.skip("savdo yo'q")

    assert free.trades["r_multiple"].max() > capped.trades["r_multiple"].max()
    assert capped.trades["r_multiple"].max() <= 2.2
