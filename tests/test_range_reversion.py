"""Range Reversion — o'rtachaga qaytish strategiyasi.

Bu strategiya trend-following'ning aksi, va uning ikkita bloki
**majburiy** — ular bo'lmasa tuzilma matematik jihatdan yutqazadi.
Testlar ikkalasini ham qulflaydi.
"""

import numpy as np
import pandas as pd
import pytest

from scalpkit.config import Config
from scalpkit.data import generate_synthetic
from scalpkit.data.loader import resample_ohlcv
from scalpkit.engine import run_backtest
from scalpkit.features import build_features
from scalpkit.profiles import BTCUSD, for_timeframe
from scalpkit.strategies import get_strategy
from scalpkit.strategies.range_reversion import RangeReversion


@pytest.fixture(scope="module")
def h4():
    df = resample_ohlcv(generate_synthetic(n_bars=150_000, asset="btc", seed=11), "4h")
    return df, build_features(df)


@pytest.fixture(scope="module")
def pooled_h1():
    """Bir nechta seed birlashtirilgan H1 namunasi.

    Xulq-atvor testlari uchun katta namuna kerak: H4 da bitta seed
    atigi ~23 savdo beradi va har qanday statistik da'vo shovqinga
    aylanadi. H1 da uchta seed ~400 savdo beradi.
    """
    cfg = for_timeframe(BTCUSD, "1h").apply(Config(), "range_reversion")
    strat = get_strategy("range_reversion", cfg.strategy.params)
    trades = []
    for seed in (11, 12, 13):
        df = resample_ohlcv(generate_synthetic(n_bars=150_000, asset="btc", seed=seed), "1h")
        f = build_features(df)
        res = run_backtest(f, strat.generate(f), cfg, strat.params, warmup=300)
        if not res.trades.empty:
            trades.append(res.trades)
    return pd.concat(trades, ignore_index=True) if trades else pd.DataFrame()


# --------------------------------------------------------------- dizayn
def test_target_is_mandatory_unlike_trend_following():
    """Mean-reversion ustunligi aniq bir harakatda — maqsad shart."""
    p = RangeReversion().params
    assert p["target_mode"] == "mid"
    assert p["trail_after_r"] > 100, "trailing qaytishni qaytarib beradi"
    assert p["time_stop_bars"] <= 20, "faraz muddati qisqa bo'lishi kerak"
    assert p["time_stop_min_r"] > 100, "vaqt tugasa so'zsiz yopilishi kerak"


def test_regime_is_the_opposite_of_the_trend_strategy():
    reversion = RangeReversion().params
    trend = get_strategy("donchian_breakout").params
    assert reversion["adx_max"] <= 30.0          # yon harakat
    assert trend["tp2_r"] == 0.0                 # trend — maqsadsiz
    assert reversion["target_mode"] == "mid"     # qaytish — maqsadli


def test_setup_and_trigger_are_on_different_bars(h4):
    """Ikkalasini bitta barda talab qilish ularni bir-birini inkor qildiradi.

    Regressiya testi: `RSI(2) <= 10` oxirgi barlar pastga ketganini
    bildiradi, `close > open` esa o'sha barning yuqoriga yopilishini.
    Bitta barda talab qilinganda 327 ta signal 2 taga tushib qolgandi.
    """
    _, f = h4
    common = {"min_atr_pct": 0.0, "max_atr_pct": 1.0, "adx_max": 100.0,
              "range_dev_atr": 1e9, "min_target_r": 0.0}
    separated = (RangeReversion({**common, "require_reversal_bar": True})
                 .generate(f)["signal"] != 0).sum()
    no_confirm = (RangeReversion({**common, "require_reversal_bar": False})
                  .generate(f)["signal"] != 0).sum()

    # Asosiy da'vo: tasdiq signallarni YO'Q QILMAYDI. Bir barda talab
    # qilinganda ular 99 % ga kamayardi.
    assert separated > 0.5 * no_confirm, (
        f"qaytish tasdig'i signallarni {separated}/{no_confirm} ga tushirdi — "
        "setup va trigger yana bitta barda talab qilinyapti"
    )


def test_confirmation_on_the_same_bar_would_destroy_the_signals(h4):
    """Xatoning o'zini ko'rsatuvchi test: setup va trigger bitta barda."""
    _, f = h4
    common = {"min_atr_pct": 0.0, "max_atr_pct": 1.0, "adx_max": 100.0,
              "range_dev_atr": 1e9, "min_target_r": 0.0}
    correct = (RangeReversion({**common, "require_reversal_bar": True})
               .generate(f)["signal"] != 0).sum()

    # Qo'lda "eski" (xato) mantiqni qayta quramiz
    close = f["close"]
    band = 20
    mid = close.rolling(band, min_periods=band).mean()
    sd = close.rolling(band, min_periods=band).std(ddof=0)
    z = (close - mid) / sd.replace(0.0, np.nan)
    from scalpkit.strategies.range_reversion import _rsi
    rsi = _rsi(close, 2)
    same_bar = ((z <= -2.0) & (rsi <= 10.0) & (close > f["open"])).fillna(False).sum()

    assert same_bar < 0.1 * correct, (
        f"bitta barda: {same_bar}, ajratilgan: {correct} — "
        "farq kutilganidan kichik"
    )


# --------------------------------------------------------------- mukofot/risk
def test_reward_risk_filter_removes_inadequate_trades(h4):
    """Filtrsiz savdolarning ko'pchiligida mukofot riskdan kichik bo'ladi."""
    _, f = h4
    common = {"min_atr_pct": 0.0, "max_atr_pct": 1.0}
    loose = RangeReversion({**common, "min_target_r": 0.0}).generate(f)
    strict = RangeReversion({**common, "min_target_r": 1.2}).generate(f)

    n_loose = (loose["signal"] != 0).sum()
    n_strict = (strict["signal"] != 0).sum()
    assert 0 < n_strict < n_loose

    # Qolgan savdolarning HAMMASIDA mukofot >= 1.2 x risk bo'lishi shart
    m = strict["signal"] != 0
    reward = (strict.loc[m, "target_price"] - f.loc[m, "close"]).abs()
    risk = (f.loc[m, "close"] - strict.loc[m, "stop_price"]).abs()
    assert (reward >= 1.2 * risk - 1e-9).all()


def test_reward_risk_filter_lifts_the_payoff(pooled_h1):
    """Filtr payoff'ni sezilarli ko'taradi.

    Ko'p-seed o'lchovi: filtrsiz payoff 0.57-0.82, filtr bilan 0.98-1.33.
    """
    cfg = for_timeframe(BTCUSD, "1h").apply(Config(), "range_reversion")

    def payoff(min_target_r):
        st = get_strategy("range_reversion",
                          {**cfg.strategy.params, "min_target_r": min_target_r})
        rs = []
        for seed in (11, 12, 13):
            df = resample_ohlcv(
                generate_synthetic(n_bars=150_000, asset="btc", seed=seed), "1h")
            f = build_features(df)
            res = run_backtest(f, st.generate(f), cfg, st.params, warmup=300)
            if not res.trades.empty:
                rs.append(res.trades["r_multiple"])
        if not rs:
            return None
        r = pd.concat(rs)
        wins, losses = r[r > 0], r[r <= 0]
        if len(wins) < 10 or len(losses) < 10:
            return None
        return abs(wins.mean() / losses.mean())

    loose, strict = payoff(0.0), payoff(1.2)
    if loose is None or strict is None:
        pytest.skip("savdolar kam")
    assert strict > loose, f"filtr payoff'ni oshirmadi: {loose:.2f} -> {strict:.2f}"
    assert strict > 0.90, f"payoff hali ham juda past: {strict:.2f}"


def test_target_price_column_is_emitted_and_on_the_right_side(h4):
    _, f = h4
    # Rejim filtrlari bo'shatilgan: bu test ustunlikni emas, MAQSAD
    # ustunining to'g'ri tomonda ekanini tekshiradi
    sig = RangeReversion({"min_atr_pct": 0.0, "max_atr_pct": 1.0,
                          "adx_max": 100.0, "range_dev_atr": 1e9}).generate(f)
    assert "target_price" in sig.columns
    m = sig["signal"] != 0
    if m.sum() == 0:
        pytest.skip("signal yo'q")
    side = sig.loc[m, "signal"]
    diff = (sig.loc[m, "target_price"] - f.loc[m, "close"]) * side
    assert (diff > 0).all(), "maqsad noto'g'ri tomonda"


def test_engine_uses_the_dynamic_target(h4):
    """Maqsad qat'iy R ko'paytmasi emas, o'rtachaning o'zi bo'lishi kerak."""
    _, f = h4
    cfg = for_timeframe(BTCUSD, "4h").apply(Config(), "range_reversion")
    st = get_strategy("range_reversion", cfg.strategy.params)
    sig = st.generate(f)
    res = run_backtest(f, sig, cfg, st.params, warmup=300)
    if res.trades.empty:
        pytest.skip("savdo yo'q")

    t = res.trades
    r_multiple_of_target = ((t["tp2"] - t["entry_price"]) * t["side"]
                            / t["risk_per_unit"])
    # Dinamik maqsad har savdoda boshqa R ga to'g'ri keladi
    assert r_multiple_of_target.std() > 0.05, "maqsad qat'iy R ko'paytmasiga o'xshaydi"
    assert (r_multiple_of_target > 0).all()


# --------------------------------------------------------------- xulq
def test_mean_reversion_signature_differs_from_trend_following(pooled_h1):
    """Imzo trend-following'ning aksi bo'lishi kerak.

    Ko'p-seed o'lchovi (8 seed, H1):
      donchian_breakout : g'alaba 34.5 %, payoff 1.66, eng katta yutuq katta
      range_reversion   : g'alaba 45.8 %, payoff 1.12, yutuqlar cheklangan
    """
    if len(pooled_h1) < 100:
        pytest.skip("savdolar kam")
    rev = pooled_h1["r_multiple"]

    cfg = for_timeframe(BTCUSD, "1h").apply(Config(), "donchian_breakout")
    st = get_strategy("donchian_breakout", cfg.strategy.params)
    trend_r = []
    for seed in (11, 12, 13):
        df = resample_ohlcv(
            generate_synthetic(n_bars=150_000, asset="btc", seed=seed), "1h")
        f = build_features(df)
        res = run_backtest(f, st.generate(f), cfg, st.params, warmup=300)
        if not res.trades.empty:
            trend_r.append(res.trades["r_multiple"])
    trend = pd.concat(trend_r)

    assert (rev > 0).mean() > (trend > 0).mean(), \
        "qaytish strategiyasining g'alaba foizi yuqoriroq bo'lishi kerak"
    assert rev.max() < trend.max(), \
        "trend strategiyasining eng katta yutug'i kattaroq bo'lishi kerak"


def test_signals_do_not_change_when_the_future_is_removed(h4):
    df, _ = h4
    cut = 100
    strat = RangeReversion()
    full = strat.generate(build_features(df))
    truncated = strat.generate(build_features(df.iloc[:-cut]))
    cols = ["signal", "stop_price", "target_price"]
    pd.testing.assert_frame_equal(
        full[cols].iloc[:-cut].tail(60), truncated[cols].tail(60), check_dtype=False
    )
