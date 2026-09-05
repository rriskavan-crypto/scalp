"""Xarajat matematikasi va statistika ko'rsatkichlari."""

import numpy as np
import pandas as pd
import pytest

from scalpkit.config import CostConfig
from scalpkit.costs import breakeven_win_rate, cost_in_r, min_stop_pct, round_trip_pct
from scalpkit.metrics import compute_metrics
from scalpkit.montecarlo import bootstrap_equity, edge_significance_test


# ------------------------------------------------------------------ xarajatlar
def test_round_trip_cost_matches_manual_sum():
    c = CostConfig(taker_fee_bps=5.0, slippage_bps=1.5, stop_slippage_bps=3.0)
    assert c.round_trip_bps() == pytest.approx(5.0 + 5.0 + 1.5 + 3.0)
    assert round_trip_pct(c) == pytest.approx(0.00145)


def test_maker_entry_is_cheaper_than_taker():
    taker = CostConfig(entry_is_maker=False)
    maker = CostConfig(entry_is_maker=True)
    assert maker.round_trip_bps() < taker.round_trip_bps()


def test_cost_in_r_is_inversely_proportional_to_stop_distance():
    """Skalpingdagi asosiy tenglama: tor stop = qimmat savdo."""
    c = CostConfig()
    assert cost_in_r(c, 0.0020) == pytest.approx(0.725)   # 0.20 % stop -> 0.725 R
    assert cost_in_r(c, 0.0050) == pytest.approx(0.29)    # 0.50 % stop -> 0.29 R
    assert cost_in_r(c, 0.0010) == 2 * cost_in_r(c, 0.0020)


def test_breakeven_win_rate_without_costs():
    assert breakeven_win_rate(1.0, 0.0) == pytest.approx(0.50)
    assert breakeven_win_rate(2.0, 0.0) == pytest.approx(1 / 3)
    assert breakeven_win_rate(3.0, 0.0) == pytest.approx(0.25)


def test_costs_raise_the_required_win_rate():
    no_cost = breakeven_win_rate(2.0, 0.0)
    with_cost = breakeven_win_rate(2.0, 0.30)
    assert with_cost > no_cost
    # 2R payoff, 0.30R xarajat -> (1.30)/(1.70+1.30)
    assert with_cost == pytest.approx(1.30 / 3.00)


def test_min_stop_pct_inverts_cost_in_r():
    c = CostConfig()
    sp = min_stop_pct(c, 0.25)
    assert cost_in_r(c, sp) == pytest.approx(0.25)


# ------------------------------------------------------------------ statistika
def make_trades(r_values):
    n = len(r_values)
    idx = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    risk = 100.0
    return pd.DataFrame({
        "entry_time": idx, "exit_time": idx, "side": 1,
        "entry_price": 1000.0, "exit_price": 1000.0, "qty": 1.0,
        "stop_init": 990.0, "tp1": 1015.0, "tp2": 1035.0,
        "risk_per_unit": 10.0, "risk_amount": risk, "notional": 1000.0,
        "gross_pnl": np.array(r_values) * risk, "fees": 0.0, "funding": 0.0,
        "net_pnl": np.array(r_values) * risk, "r_multiple": r_values,
        "bars_held": 10, "exit_reason": "tp2", "mae_r": -0.5, "mfe_r": 1.5,
        "equity_after": 10_000.0,
    })


def test_expectancy_and_breakeven_are_consistent():
    # 40 % g'alaba, +2R / -1R -> ekspektatsiya +0.2R
    r = [2.0] * 4 + [-1.0] * 6
    t = make_trades(r)
    eq = pd.Series(np.linspace(10_000, 10_200, 10),
                   index=pd.date_range("2024-01-01", periods=10, freq="1h", tz="UTC"))
    m = compute_metrics(t, eq, 10_000, 10)

    assert m["win_rate"] == pytest.approx(0.4)
    assert m["expectancy_r"] == pytest.approx(0.2)
    assert m["payoff_ratio"] == pytest.approx(2.0)
    assert m["breakeven_win_rate"] == pytest.approx(1 / 3)
    assert m["win_rate_edge"] > 0          # g'alaba foizi zararsizlikdan yuqori
    assert m["profit_factor"] == pytest.approx(8.0 / 6.0)


def test_metrics_on_empty_trades_do_not_crash():
    empty = make_trades([]).iloc[0:0]
    eq = pd.Series([10_000.0], index=pd.DatetimeIndex(["2024-01-01"], tz="UTC"))
    m = compute_metrics(empty, eq, 10_000, 30)
    assert m["trades"] == 0
    assert m["expectancy_r"] == 0.0


def test_max_drawdown_is_measured_from_the_peak():
    idx = pd.date_range("2024-01-01", periods=5, freq="1D", tz="UTC")
    eq = pd.Series([10_000, 12_000, 9_000, 11_000, 13_000.0], index=idx)
    m = compute_metrics(make_trades([1.0]), eq, 10_000, 5)
    assert m["max_drawdown_pct"] == pytest.approx(9_000 / 12_000 - 1.0)


# ------------------------------------------------------------------ Monte Carlo
def test_significance_test_detects_a_real_edge():
    rng = np.random.default_rng(3)
    r = np.where(rng.random(500) < 0.45, 2.0, -1.0)   # ekspektatsiya ~ +0.35R
    out = edge_significance_test(r, n_sims=3000)
    assert out["observed_mean_r"] > 0
    assert out["p_value"] < 0.01
    assert out["ci_low"] > 0


def test_significance_test_does_not_flag_a_zero_mean_sample():
    # Aynan nol ekspektatsiyali namuna: 100 x (+2R) va 200 x (-1R)
    r = np.array([2.0] * 100 + [-1.0] * 200)
    assert r.mean() == pytest.approx(0.0)
    out = edge_significance_test(r, n_sims=3000)
    assert out["p_value"] > 0.05
    assert out["ci_low"] < 0 < out["ci_high"]


def test_significance_test_false_positive_rate_is_calibrated():
    """Ustunlik yo'q bo'lganda test 5 % dan sezilarli ko'p signal bermasligi kerak.

    Bitta seedga tayanib bo'lmaydi — yolg'on-musbat vaqti-vaqti bilan
    tabiiy ravishda uchraydi. Shuning uchun 60 ta mustaqil namuna ustida
    yolg'on-musbat ULUSHI o'lchanadi.
    """
    flagged = 0
    trials = 60
    for seed in range(trials):
        rng = np.random.default_rng(seed)
        r = np.where(rng.random(400) < 1 / 3, 2.0, -1.0)   # ekspektatsiya = 0
        if edge_significance_test(r, n_sims=800, seed=seed)["significant_5pct"]:
            flagged += 1
    # Nominal daraja 5 %; kichik namunada 15 % gacha chetlanish qabul qilinadi
    assert flagged / trials <= 0.15, f"yolg'on-musbat ulushi juda yuqori: {flagged}/{trials}"


def test_bootstrap_drawdowns_are_negative_and_ordered():
    rng = np.random.default_rng(5)
    r = np.where(rng.random(300) < 0.45, 2.0, -1.0)
    mc = bootstrap_equity(r, n_sims=1500, risk_per_trade=0.01)
    assert (mc.max_drawdowns <= 0).all()
    # p5 eng yomon, p95 eng yengil drawdown
    dd = mc.summary["maks. drawdown %"]
    assert dd.loc["p5"] < dd.loc["p95"]
    assert mc.prob_profit > 0.9
