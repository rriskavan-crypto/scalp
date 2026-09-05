"""Backtest dvigatelining to'g'riligi.

Bu testlar qo'lda qurilgan barlar ustida ishlaydi — natija aniq oldindan
ma'lum bo'lgani uchun dvigateldagi har qanday xato darhol ko'rinadi.
"""

import numpy as np
import pandas as pd
import pytest

from scalpkit.config import Config
from scalpkit.engine import run_backtest

PRICE = 1000.0
ATR = 10.0
DIST = 10.0  # stop masofasi = 1 % = 1 R


def make_frames(bars, signal_at=0, side=1, raw_stop=PRICE - DIST):
    """bars: (open, high, low, close) ro'yxati. Signal 0-barda beriladi."""
    idx = pd.date_range("2024-03-04 10:00", periods=len(bars), freq="5min", tz="UTC")
    f = pd.DataFrame(bars, columns=["open", "high", "low", "close"], index=idx)
    f["volume"] = 1.0
    f["ema_fast"] = 0.0 if side > 0 else 1e9  # ema_exit hech qachon ishlamasin

    sig = pd.DataFrame(
        {"signal": 0, "stop_price": np.nan, "atr": ATR, "entry_ref": np.nan}, index=idx
    )
    sig.loc[idx[signal_at], "signal"] = side
    sig.loc[idx[signal_at], "stop_price"] = raw_stop
    sig["signal"] = sig["signal"].astype(np.int8)
    return f, sig


def zero_cost_config():
    cfg = Config()
    cfg.cost.taker_fee_bps = 0.0
    cfg.cost.maker_fee_bps = 0.0
    cfg.cost.slippage_bps = 0.0
    cfg.cost.stop_slippage_bps = 0.0
    cfg.cost.apply_funding = False
    return cfg


PARAMS = dict(entry_mode="market", min_sl_atr=1.0, max_sl_atr=2.2, tp1_r=1.5,
              tp1_fraction=0.35, tp2_r=3.5, tp1_stop_to_r=-0.35, be_trigger_r=2.0,
              trail_after_r=1.5, trail_atr_mult=2.5, time_stop_bars=99,
              time_stop_min_r=0.5, exit_on_ema_cross=False)


def test_entry_happens_on_next_bar_open_not_signal_bar():
    """Kelajakka qarashning oldini oladigan eng muhim qoida."""
    f, sig = make_frames([
        (900, 910, 890, 900),          # 0: signal bari — bu narxda kirilmasligi kerak
        (PRICE, 1001, 999, 1000),      # 1: kirish shu barning OCHILISHIDA
        (1000, 1040, 999, 1035),       # 2: TP2
    ])
    res = run_backtest(f, sig, zero_cost_config(), PARAMS, warmup=1)
    assert len(res.trades) == 1
    assert res.trades.iloc[0]["entry_price"] == pytest.approx(PRICE)
    assert res.trades.iloc[0]["entry_time"] == f.index[1]


def test_full_stop_loses_exactly_one_r():
    f, sig = make_frames([
        (900, 910, 890, 900),
        (PRICE, 1005, 995, 1000),
        (1000, 1002, PRICE - DIST, 992),   # stopga tegdi
    ])
    res = run_backtest(f, sig, zero_cost_config(), PARAMS, warmup=1)
    t = res.trades.iloc[0]
    assert t["exit_reason"] == "stop"
    assert t["r_multiple"] == pytest.approx(-1.0, abs=1e-9)


def test_tp2_gives_full_target_r():
    f, sig = make_frames([
        (900, 910, 890, 900),
        (PRICE, 1005, 995, 1000),
        (1000, PRICE + 3.5 * DIST, 999, 1034),  # TP1 va TP2 bir barda
    ])
    res = run_backtest(f, sig, zero_cost_config(), PARAMS, warmup=1)
    t = res.trades.iloc[0]
    assert t["exit_reason"] == "tp2"
    # 35 % TP1 da (1.5R), 65 % TP2 da (3.5R)
    expected = 0.35 * 1.5 + 0.65 * 3.5
    assert t["r_multiple"] == pytest.approx(expected, abs=1e-9)


def test_stop_wins_over_target_in_same_bar():
    """Pessimistik qoida: bir barda ikkalasi tegilsa — stop hisoblanadi."""
    f, sig = make_frames([
        (900, 910, 890, 900),
        (PRICE, 1005, 995, 1000),
        (1000, PRICE + 3.5 * DIST, PRICE - DIST, 1000),  # ikkalasi ham
    ])
    res = run_backtest(f, sig, zero_cost_config(), PARAMS, warmup=1)
    t = res.trades.iloc[0]
    assert t["exit_reason"] == "stop"
    assert t["r_multiple"] == pytest.approx(-1.0, abs=1e-9)


def test_gap_through_stop_fills_at_open_not_stop():
    f, sig = make_frames([
        (900, 910, 890, 900),
        (PRICE, 1005, 995, 1000),
        (960, 965, 955, 958),   # stopdan (990) ancha pastda ochildi
    ])
    res = run_backtest(f, sig, zero_cost_config(), PARAMS, warmup=1)
    t = res.trades.iloc[0]
    assert t["exit_reason"] == "stop_gap"
    assert t["r_multiple"] == pytest.approx(-4.0, abs=1e-9)  # (960-1000)/10


def test_short_stop_is_symmetric():
    f, sig = make_frames([
        (1100, 1110, 1090, 1100),
        (PRICE, 1005, 995, 1000),
        (1000, PRICE + DIST, 998, 1009),
    ], side=-1, raw_stop=PRICE + DIST)
    res = run_backtest(f, sig, zero_cost_config(), PARAMS, warmup=1)
    t = res.trades.iloc[0]
    assert t["side"] == -1
    assert t["exit_reason"] == "stop"
    assert t["r_multiple"] == pytest.approx(-1.0, abs=1e-9)


def test_position_size_matches_risk_budget():
    cfg = zero_cost_config()
    cfg.risk.risk_per_trade = 0.01
    cfg.risk.initial_equity = 50_000.0
    f, sig = make_frames([
        (900, 910, 890, 900),
        (PRICE, 1005, 995, 1000),
        (1000, 1002, PRICE - DIST, 992),
    ])
    res = run_backtest(f, sig, cfg, PARAMS, warmup=1)
    t = res.trades.iloc[0]
    assert t["risk_amount"] == pytest.approx(500.0)      # 50 000 * 1 %
    assert t["qty"] == pytest.approx(500.0 / DIST)
    assert t["net_pnl"] == pytest.approx(-500.0)


def test_leverage_cap_limits_size():
    cfg = zero_cost_config()
    cfg.risk.risk_per_trade = 0.50      # ataylab aqlsiz darajada katta
    cfg.risk.max_leverage = 2.0
    f, sig = make_frames([
        (900, 910, 890, 900),
        (PRICE, 1005, 995, 1000),
        (1000, 1002, PRICE - DIST, 992),
    ])
    res = run_backtest(f, sig, cfg, PARAMS, warmup=1)
    t = res.trades.iloc[0]
    assert t["notional"] == pytest.approx(cfg.risk.initial_equity * 2.0)


def test_fees_reduce_pnl_and_are_recorded():
    cfg = zero_cost_config()
    cfg.cost.taker_fee_bps = 5.0
    f, sig = make_frames([
        (900, 910, 890, 900),
        (PRICE, 1005, 995, 1000),
        (1000, 1002, PRICE - DIST, 992),
    ])
    res = run_backtest(f, sig, cfg, PARAMS, warmup=1)
    t = res.trades.iloc[0]
    assert t["fees"] > 0
    assert t["net_pnl"] == pytest.approx(t["gross_pnl"] - t["fees"] - t["funding"])
    assert t["r_multiple"] < -1.0   # komissiya zararni 1R dan chuqurroq qiladi


def test_time_stop_only_closes_stagnant_trades():
    """0.5R dan ko'p yurgan savdo vaqt bo'yicha yopilmasligi kerak."""
    params = {**PARAMS, "time_stop_bars": 2, "time_stop_min_r": 0.5}
    bars = [(900, 910, 890, 900), (PRICE, 1005, 995, 1000)]
    bars += [(1000, PRICE + 1.2 * DIST, 999, 1011)] * 5   # +1.2R gacha yurdi
    f, sig = make_frames(bars)
    res = run_backtest(f, sig, zero_cost_config(), params, warmup=1)
    assert res.trades.iloc[0]["exit_reason"] != "time_stop"

    # Endi hech qayoqqa ketmagan savdo — yopilishi kerak
    flat = [(900, 910, 890, 900), (PRICE, 1005, 995, 1000)]
    flat += [(1000, 1002, 998, 1000)] * 5
    f2, sig2 = make_frames(flat)
    res2 = run_backtest(f2, sig2, zero_cost_config(), params, warmup=1)
    assert res2.trades.iloc[0]["exit_reason"] == "time_stop"


def test_limit_entry_fills_at_limit_price_or_expires():
    params = {**PARAMS, "entry_mode": "limit", "entry_limit_bars": 2}
    # entry_ref 995 — narx unga tegadi
    f, sig = make_frames([
        (900, 910, 890, 900),
        (PRICE, 1005, 994, 1000),
        (1000, 1040, 999, 1035),
    ])
    sig.loc[sig.index[0], "entry_ref"] = 995.0
    res = run_backtest(f, sig, zero_cost_config(), params, warmup=1)
    assert len(res.trades) == 1
    assert res.trades.iloc[0]["entry_price"] == pytest.approx(995.0)

    # entry_ref 900 — hech qachon tegmaydi, order muddati tugaydi
    f2, sig2 = make_frames([
        (900, 910, 890, 900),
        (PRICE, 1005, 999, 1000),
        (1000, 1010, 999, 1005),
        (1005, 1010, 1000, 1008),
    ])
    sig2.loc[sig2.index[0], "entry_ref"] = 900.0
    sig2.loc[sig2.index[0], "stop_price"] = 880.0
    res2 = run_backtest(f2, sig2, zero_cost_config(), params, warmup=1)
    assert len(res2.trades) == 0
    assert res2.meta["limit_expired"] == 1


def test_no_trade_without_signal():
    f, sig = make_frames([(1000, 1005, 995, 1000)] * 5)
    sig["signal"] = np.int8(0)
    res = run_backtest(f, sig, zero_cost_config(), PARAMS, warmup=1)
    assert res.trades.empty
    assert (res.equity == Config().risk.initial_equity).all()


def test_breakeven_stop_after_tp1_caps_the_winner():
    """`be_after_tp1` klassik tuzilmani tiklaydi — taqqoslash uchun.

    TP1 dan keyin stop zararsizlikka suriladi, shuning uchun narx qaytsa
    savdo katta yutuq o'rniga deyarli nol bilan yopiladi.
    """
    params = {**PARAMS, "be_after_tp1": True, "be_trigger_r": 999.0,
              "trail_after_r": 999.0}
    f, sig = make_frames([
        (900, 910, 890, 900),
        (PRICE, 1005, 995, 1000),
        (1000, PRICE + 1.5 * DIST, 999, 1014),   # TP1 tegdi -> stop = kirish
        (1010, 1012, 999, 1000),                 # kirishga qaytdi -> BE da chiqish
    ])
    res = run_backtest(f, sig, zero_cost_config(), params, warmup=1)
    t = res.trades.iloc[0]
    assert t["exit_reason"] == "breakeven"
    # 35 % TP1 da 1.5R, qolgan 65 % nolda -> 0.525R
    assert t["r_multiple"] == pytest.approx(0.35 * 1.5, abs=1e-9)


def test_reduced_risk_stop_is_the_default_not_breakeven():
    """Standart holatda TP1 dan keyin stop -0.35R da, zararsizlikda emas."""
    f, sig = make_frames([
        (900, 910, 890, 900),
        (PRICE, 1005, 995, 1000),
        (1000, PRICE + 1.5 * DIST, 999, 1014),
        (1010, 1012, PRICE - 0.35 * DIST, 996),   # -0.35R stopga tegdi
    ])
    res = run_backtest(f, sig, zero_cost_config(),
                       {**PARAMS, "trail_after_r": 999.0, "be_trigger_r": 999.0},
                       warmup=1)
    t = res.trades.iloc[0]
    assert t["exit_reason"] == "stop_reduced"
    # 35 % @ +1.5R, 65 % @ -0.35R
    assert t["r_multiple"] == pytest.approx(0.35 * 1.5 + 0.65 * -0.35, abs=1e-9)
