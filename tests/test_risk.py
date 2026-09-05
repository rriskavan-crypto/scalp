"""Risk boshqaruvi qoidalari."""

import pandas as pd
import pytest

from scalpkit.config import RiskConfig
from scalpkit.risk import RiskManager, position_size


def ts(hour=10, day=4):
    return pd.Timestamp(f"2024-03-{day:02d} {hour:02d}:00", tz="UTC")


def test_position_size_formula():
    # 10 000 * 1 % = 100 risk; stop 50 -> 2 birlik
    assert position_size(10_000, 0.01, 50, 1000, 100) == pytest.approx(2.0)


def test_position_size_respects_leverage_cap():
    # riskka ko'ra 100 birlik chiqadi, lekin 3x leverage 30 birlikni beradi
    qty = position_size(10_000, 0.50, 50, 1000, 3.0)
    assert qty == pytest.approx(30.0)


def test_position_size_zero_when_stop_invalid():
    assert position_size(10_000, 0.01, 0, 1000, 5) == 0.0
    assert position_size(10_000, 0.01, -5, 1000, 5) == 0.0


def test_daily_loss_limit_locks_the_day():
    rm = RiskManager(RiskConfig(daily_loss_limit=0.03, cooldown_bars_after_loss=0))
    rm.on_new_bar(ts(9), 10_000)
    assert rm.can_trade(ts(9), 1, 10_000)

    # -3.5 % zarar -> kun yopiladi
    assert not rm.can_trade(ts(10), 2, 9_650)
    # kapital tiklansa ham shu kun ochilmaydi
    assert not rm.can_trade(ts(11), 3, 9_990)
    # ertasi kuni yana ochiladi
    rm.on_new_bar(ts(9, day=5), 9_650)
    assert rm.can_trade(ts(9, day=5), 4, 9_650)


def test_max_trades_per_day():
    rm = RiskManager(RiskConfig(max_trades_per_day=2, cooldown_bars_after_loss=0))
    rm.on_new_bar(ts(9), 10_000)
    for _ in range(2):
        assert rm.can_trade(ts(9), 1, 10_000)
        rm.on_trade_opened(ts(9))
    assert not rm.can_trade(ts(9), 1, 10_000)


def test_cooldown_after_a_loss():
    rm = RiskManager(RiskConfig(cooldown_bars_after_loss=6, max_consecutive_losses=99))
    rm.on_new_bar(ts(9), 10_000)
    rm.on_trade_closed(-50.0, ts(9), bar_i=10)
    assert not rm.can_trade(ts(9), 12, 9_950)   # 16-bargacha bloklangan
    assert rm.can_trade(ts(9), 16, 9_950)


def test_longer_cooldown_after_a_losing_streak():
    cfg = RiskConfig(cooldown_bars_after_loss=6, cooldown_bars_after_streak=24,
                     max_consecutive_losses=3)
    rm = RiskManager(cfg)
    rm.on_new_bar(ts(9), 10_000)
    for i in range(2):
        rm.on_trade_closed(-50.0, ts(9), bar_i=i)
    assert rm.block_until_bar == 1 + 6
    rm.on_trade_closed(-50.0, ts(9), bar_i=2)   # uchinchi ketma-ket zarar
    assert rm.block_until_bar == 2 + 24
    assert rm.consecutive_losses == 0           # hisoblagich tozalanadi


def test_win_resets_loss_streak():
    rm = RiskManager(RiskConfig())
    rm.on_trade_closed(-50.0, ts(9), 1)
    rm.on_trade_closed(-50.0, ts(9), 2)
    assert rm.consecutive_losses == 2
    rm.on_trade_closed(+80.0, ts(9), 3)
    assert rm.consecutive_losses == 0


def test_risk_is_halved_in_deep_drawdown():
    cfg = RiskConfig(risk_per_trade=0.01, halve_risk_drawdown=0.08)
    rm = RiskManager(cfg)
    rm.on_new_bar(ts(9), 12_000)                             # yangi cho'qqi
    assert rm.effective_risk(12_000) == pytest.approx(0.01)   # drawdown yo'q
    assert rm.effective_risk(11_100) == pytest.approx(0.01)   # -7.5 %, chegaradan past
    assert rm.effective_risk(11_000) == pytest.approx(0.005)  # -8.3 %, chegaradan o'tdi -> yarmi
    assert rm.effective_risk(10_000) == pytest.approx(0.005)  # -16.7 % -> yarmi


def test_new_day_resets_counters():
    rm = RiskManager(RiskConfig(max_trades_per_day=1))
    rm.on_new_bar(ts(9), 10_000)
    rm.on_trade_opened(ts(9))
    assert not rm.can_trade(ts(9), 1, 10_000)
    rm.on_new_bar(ts(9, day=5), 10_000)
    assert rm.trades_today == 0
    assert rm.can_trade(ts(9, day=5), 2, 10_000)
