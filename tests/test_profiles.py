"""Instrument profillari va savdo kalendari.

Bu testlar bitta asosiy xatoni oldini oladi: bir bozor uchun kalibrlangan
parametrlarni boshqasiga o'zgartirmasdan qo'llash. BTC uchun mo'ljallangan
`min_atr_pct = 0.20 %` oltinda barcha barlarni bloklaydi — kod ishlaydi,
lekin hech qachon savdo qilmaydi.
"""

import numpy as np
import pandas as pd
import pytest

from scalpkit.config import Config
from scalpkit.data import generate_synthetic
from scalpkit.engine import run_backtest
from scalpkit.features import build_features, warmup_bars
from scalpkit.indicators import atr
from scalpkit.profiles import (
    BTCUSD, PROFILES, XAUUSD, get_profile, profile_for_symbol,
)
from scalpkit.strategies import get_strategy
from scalpkit.strategies.base import week_guard_mask


# --------------------------------------------------------------- profil tanlash
@pytest.mark.parametrize("symbol,expected", [
    ("BTCUSD", "btcusd"), ("BTCUSDT", "btcusd"), ("BTCUSDm", "btcusd"),
    ("XAUUSD", "xauusd"), ("XAUUSDm", "xauusd"), ("GOLD", "xauusd"),
    ("XAUUSD.raw", "xauusd"),
])
def test_symbol_resolves_to_the_right_profile(symbol, expected):
    assert profile_for_symbol(symbol).name == expected


def test_unknown_symbol_falls_back_to_default():
    assert profile_for_symbol("EURUSD").name == "btcusd"


def test_get_profile_rejects_unknown_name():
    with pytest.raises(KeyError):
        get_profile("silver")


def test_applying_a_profile_does_not_mutate_the_original_config():
    cfg = Config()
    original_symbol = cfg.symbol
    original_stop = cfg.risk.min_stop_pct

    applied = XAUUSD.apply(cfg)

    assert cfg.symbol == original_symbol
    assert cfg.risk.min_stop_pct == original_stop
    assert applied.symbol == "XAUUSD"
    assert applied.risk.min_stop_pct == XAUUSD.risk["min_stop_pct"]


def test_profile_sets_strategy_risk_and_cost():
    cfg = XAUUSD.apply(Config())
    assert cfg.strategy.params["min_atr_pct"] == XAUUSD.strategy["min_atr_pct"]
    assert cfg.risk.max_leverage == XAUUSD.risk["max_leverage"]
    assert cfg.cost.slippage_bps == XAUUSD.cost["slippage_bps"]
    assert cfg.cost.apply_funding is False   # oltinda funding yo'q, swap bor


# --------------------------------------------------------------- kalibrlash
def test_gold_volatility_filter_is_far_below_the_crypto_one():
    """Oltin ATR% BTC dan ~3.5 barobar past — filtr ham shunga mos bo'lishi shart."""
    assert XAUUSD.strategy["min_atr_pct"] < BTCUSD.strategy["min_atr_pct"] / 3.0
    assert XAUUSD.risk["min_stop_pct"] < BTCUSD.risk["min_stop_pct"] / 3.0


def test_crypto_filter_would_block_every_gold_bar():
    """Nima uchun profillar kerakligini ko'rsatuvchi test."""
    gold = generate_synthetic(n_bars=8_000, asset="gold", seed=5)
    atr_pct = atr(gold.high, gold.low, gold.close, 14) / gold.close

    passes_crypto = (atr_pct >= BTCUSD.strategy["min_atr_pct"]).mean()
    passes_gold = (atr_pct >= XAUUSD.strategy["min_atr_pct"]).mean()

    assert passes_crypto < 0.05, (
        f"BTC filtri oltin barlarining {passes_crypto:.1%} ini o'tkazyapti — "
        "bu testning maqsadi u deyarli hech narsani o'tkazmasligini ko'rsatish"
    )
    assert passes_gold > 0.40, "oltin filtri juda qattiq — savdo bo'lmaydi"
    # Asosiy da'vo: farq tasodifiy emas, kattalik tartibida
    assert passes_gold > 10 * passes_crypto


def test_gold_volatility_floor_keeps_costs_affordable():
    """min_atr_pct xarajat byudjetidan kelib chiqishi kerak.

    cost_R = spread / (min_sl_atr x ATR); tipik spread bilan bu 0.25R dan
    oshmasligi shart, aks holda strategiya matematik jihatdan yutqazadi.
    """
    params = get_strategy("momentum_pullback", XAUUSD.strategy).params
    min_atr = XAUUSD.strategy["min_atr_pct"] * XAUUSD.typical_price
    stop = float(params["min_sl_atr"]) * 1.4 * min_atr
    cost_r = XAUUSD.typical_spread / stop
    assert cost_r < 0.25, f"eng past volatilitetda xarajat {cost_r:.3f}R — juda qimmat"


def test_every_profile_declares_a_coherent_calendar():
    for profile in PROFILES.values():
        cal = profile.calendar
        if cal.trades_weekends:
            assert cal.days_per_year == pytest.approx(365.0)
            assert not cal.weekend_flat
        else:
            assert cal.days_per_year < 300.0        # dam olish kunlari yo'q
            assert cal.weekend_flat
            assert 0 <= cal.week_close_dow <= 6
            assert 0 <= cal.week_close_hour_utc <= 23


# --------------------------------------------------------------- hafta chegarasi
@pytest.fixture(scope="module")
def week_index():
    return pd.date_range("2024-03-04", periods=7 * 24 * 12, freq="5min", tz="UTC")


def test_week_guard_blocks_friday_evening(week_index):
    mask = week_guard_mask(week_index, close_dow=4, close_hour=19, open_skip_bars=0)
    ok = pd.Series(mask.to_numpy(), index=week_index)
    assert ok["2024-03-08 18:55"]        # juma kunduzi — mumkin
    assert not ok["2024-03-08 19:00"]    # chegara
    assert not ok["2024-03-08 23:00"]    # juma kechqurun


def test_week_guard_skips_the_first_bars_of_the_week(week_index):
    mask = week_guard_mask(week_index, close_dow=4, close_hour=19, open_skip_bars=6)
    assert not mask.iloc[0]
    assert not mask.iloc[5]
    assert mask.iloc[6]


def test_week_guard_is_inert_when_skip_is_zero(week_index):
    mask = week_guard_mask(week_index, close_dow=4, close_hour=19, open_skip_bars=0)
    assert mask.iloc[0]


# --------------------------------------------------------------- kalendar ma'lumoti
def test_gold_synthetic_respects_market_hours():
    gold = generate_synthetic(n_bars=6_000, asset="gold", seed=2)
    assert (gold.index.dayofweek == 5).sum() == 0                       # shanba
    assert ((gold.index.dayofweek == 6) & (gold.index.hour < 22)).sum() == 0
    assert ((gold.index.dayofweek == 4) & (gold.index.hour >= 21)).sum() == 0
    assert (gold.index.hour == 21).sum() == 0                           # rollover


def test_crypto_synthetic_trades_continuously():
    btc = generate_synthetic(n_bars=3_000, asset="btc", seed=2)
    assert (btc.index.dayofweek == 5).sum() > 0
    deltas = btc.index.to_series().diff().dropna().unique()
    assert len(deltas) == 1                    # uzilishsiz


def test_gold_is_much_less_volatile_than_crypto():
    btc = generate_synthetic(n_bars=20_000, asset="btc", seed=4)
    gold = generate_synthetic(n_bars=20_000, asset="gold", seed=4)
    btc_atr = (atr(btc.high, btc.low, btc.close, 14) / btc.close).median()
    gold_atr = (atr(gold.high, gold.low, gold.close, 14) / gold.close).median()
    assert gold_atr < btc_atr / 2.5


# --------------------------------------------------------------- uchdan-uchgacha
@pytest.fixture(scope="module")
def gold_backtest():
    df = generate_synthetic(n_bars=60_000, asset="gold", seed=7)
    cfg = XAUUSD.apply(Config())
    strat = get_strategy(cfg.strategy.name, cfg.strategy.params)
    feats = build_features(df)
    return run_backtest(feats, strat.generate(feats), cfg, strat.params,
                        warmup=warmup_bars())


def test_gold_profile_actually_produces_trades(gold_backtest):
    assert len(gold_backtest.trades) > 20, \
        "oltin profili savdo bermayapti — filtrlar juda qattiq"


def test_no_entries_after_the_friday_cutoff(gold_backtest):
    """Limit order signal ruxsat etilgan barda berilsa ham, to'ldirilishi
    chegaradan keyinga tushmasligi kerak."""
    t = gold_backtest.trades
    if t.empty:
        pytest.skip("savdo yo'q")
    late = (t["entry_time"].dt.dayofweek == 4) & (t["entry_time"].dt.hour >= 19)
    assert late.sum() == 0, f"{late.sum()} ta savdo juma chegarasidan keyin ochilgan"


def test_no_entries_on_the_weekend(gold_backtest):
    t = gold_backtest.trades
    if t.empty:
        pytest.skip("savdo yo'q")
    assert (t["entry_time"].dt.dayofweek >= 5).sum() == 0


def test_positions_are_closed_before_the_weekend(gold_backtest):
    """Ochiq pozitsiya hafta oxiriga qolmasligi kerak — gap stopni chetlab o'tadi."""
    t = gold_backtest.trades
    if t.empty:
        pytest.skip("savdo yo'q")
    assert (t["exit_time"].dt.dayofweek >= 5).sum() == 0
    # Chegaradan keyin ochiq qolgan savdo bo'lmasligi kerak
    still_open = (t["exit_time"].dt.dayofweek == 4) & (t["exit_time"].dt.hour >= 21)
    assert still_open.sum() == 0


def test_crypto_profile_is_unaffected_by_the_weekend_rule():
    df = generate_synthetic(n_bars=30_000, asset="btc", seed=7)
    cfg = BTCUSD.apply(Config())
    strat = get_strategy(cfg.strategy.name, cfg.strategy.params)
    feats = build_features(df)
    res = run_backtest(feats, strat.generate(feats), cfg, strat.params,
                       warmup=warmup_bars())
    if res.trades.empty:
        pytest.skip("savdo yo'q")
    # Kripto dam olish kunlari ham savdo qiladi
    assert (res.trades["entry_time"].dt.dayofweek >= 5).sum() > 0
    assert "weekend_flat" not in set(res.trades["exit_reason"])


# --------------------------------------------------------------- xarajat izchilligi
def test_gold_fees_are_derived_from_its_typical_spread():
    """Oltin MT5 da savdo qilinadi: xarajat komissiya emas, spread.

    Regressiya testi: profil dastlab Binance'ning 5 bps kripto tarifini
    meros qilib olgandi. Oltinda bu $2.65 to'liq savdo xarajatini berib,
    ~$3.90 stopning 0.68R ini yeb yuborardi.
    """
    expected_bps = (XAUUSD.typical_spread / 2.0) / XAUUSD.typical_price * 1e4
    assert XAUUSD.cost["taker_fee_bps"] == pytest.approx(expected_bps, abs=0.05)
    # MT5 da limit order ham spreadni to'laydi — maker chegirmasi yo'q
    assert XAUUSD.cost["maker_fee_bps"] == XAUUSD.cost["taker_fee_bps"]


def test_gold_total_cost_stays_inside_the_budget():
    """Tipik sharoitda to'liq savdo xarajati 0.25R dan oshmasligi kerak."""
    cfg = XAUUSD.apply(Config())
    params = get_strategy(cfg.strategy.name, cfg.strategy.params).params
    price = XAUUSD.typical_price
    typical_atr = 0.0007 * price                  # oltin M5 ATR mediani ~0.07 %
    stop = float(params["min_sl_atr"]) * 1.4 * typical_atr
    cost_r = cfg.cost.round_trip_bps() * 1e-4 * price / stop
    assert cost_r < 0.25, f"xarajat {cost_r:.3f}R — byudjetdan oshdi"


def test_crypto_fees_are_left_at_exchange_rates():
    assert BTCUSD.cost["taker_fee_bps"] == pytest.approx(5.0)
    assert BTCUSD.cost["maker_fee_bps"] == pytest.approx(2.0)
    assert BTCUSD.cost["apply_funding"] is True


def test_search_space_scales_with_the_profile():
    """Optimizator qidiruv fazasi instrumentga moslashishi shart.

    Regressiya testi: faza `min_atr_pct: [0.0015...0.0030]` deb qattiq
    kodlangandi. Oltinda (ATR% mediani ~0.055 %) bu qiymatlarning
    hammasi barcha barlarni bloklab, walk-forward'da NOL savdo berardi —
    vosita esa buni "ustunlik yo'q" deb noto'g'ri talqin qilardi.
    """
    spaces = {}
    for name, profile in (("btcusd", BTCUSD), ("xauusd", XAUUSD)):
        cfg = profile.apply(Config())
        strat = get_strategy(cfg.strategy.name, cfg.strategy.params)
        spaces[name] = strat.param_space(strat.params)["min_atr_pct"]

    # Har bir faza o'z profilining chegarasi atrofida bo'lishi kerak
    for name, profile in (("btcusd", BTCUSD), ("xauusd", XAUUSD)):
        base = profile.strategy["min_atr_pct"]
        assert min(spaces[name]) < base <= max(spaces[name])

    # Va ular bir-biriga kirishmasligi kerak
    assert max(spaces["xauusd"]) < min(spaces["btcusd"])


def test_gold_search_space_stays_inside_the_cost_budget():
    """Qidiruvdagi eng past chegara ham xarajat byudjetini buzmasligi kerak."""
    cfg = XAUUSD.apply(Config())
    strat = get_strategy(cfg.strategy.name, cfg.strategy.params)
    lowest = min(strat.param_space(strat.params)["min_atr_pct"])
    stop = float(strat.params["min_sl_atr"]) * 1.4 * lowest * XAUUSD.typical_price
    cost_r = XAUUSD.typical_spread / stop
    assert cost_r < 0.40, f"eng past qidiruv chegarasida xarajat {cost_r:.3f}R"
