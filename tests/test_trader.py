"""Jonli savdo siklining testlari.

Bu kod real pul bilan ishlaydi, shuning uchun har bir qoida alohida
tekshiriladi. `PaperBroker` MT5 o'rnini bosadi — mantiq bir xil.

Strategiya o'rniga `StubStrategy` ishlatiladi: shunda test *savdo
boshqaruvini* tekshiradi, signal generatsiyasini emas.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scalpkit.broker.base import SymbolSpec
from scalpkit.broker.paper import PaperBroker
from scalpkit.config import Config
from scalpkit.data import generate_synthetic
from scalpkit.strategies.base import Strategy
from scalpkit.trader import LiveTrader

ATR = 200.0


class StubStrategy(Strategy):
    """Berilgan tomonda signal beradigan soxta strategiya."""

    name = "stub"
    defaults = {
        "min_sl_atr": 1.0, "max_sl_atr": 2.2, "tp1_r": 1.5, "tp1_fraction": 0.35,
        "tp2_r": 3.5, "tp1_stop_to_r": -0.35, "be_trigger_r": 2.0, "be_offset_r": 0.05,
        "trail_after_r": 1.5, "trail_atr_mult": 2.5, "trail_min_step_atr": 0.15,
        "time_stop_bars": 24, "time_stop_min_r": 0.5, "entry_mode": "market",
        "entry_limit_bars": 3,
    }

    def __init__(self, params=None, side=0, stop_offset=ATR * 1.5):
        super().__init__(params)
        self.side = side
        self.stop_offset = stop_offset

    def generate(self, f: pd.DataFrame) -> pd.DataFrame:
        n = len(f)
        signal = pd.Series(0, index=f.index, dtype=np.int8)
        stop = pd.Series(np.nan, index=f.index, dtype=float)
        ref = pd.Series(np.nan, index=f.index, dtype=float)
        if self.side != 0:
            last = f.index[-1]
            signal.iloc[-1] = self.side
            close = float(f["close"].iloc[-1])
            stop.iloc[-1] = close - self.side * self.stop_offset
            ref.iloc[-1] = close
        return pd.DataFrame(
            {"signal": signal, "stop_price": stop,
             "atr": pd.Series(ATR, index=f.index, dtype=float), "entry_ref": ref}
        )


def make_broker(bars=None, spread=10.0, balance=10_000.0, volume_min=0.01,
                volume_step=0.01, stops_level=0.0):
    bars = generate_synthetic(n_bars=420, seed=21) if bars is None else bars
    spec = SymbolSpec("BTCUSD", 2, 0.01, 1.0, volume_min, 100.0, volume_step,
                      stops_level_points=stops_level)
    return PaperBroker(bars, spread=spread, balance=balance, spec=spec,
                       warmup=len(bars) - 2)


def make_trader(broker, tmp_path, side=1, dry_run=False, cfg=None, **strat_kw):
    cfg = cfg or Config()
    return LiveTrader(
        broker, cfg, "BTCUSD", strategy=StubStrategy(side=side, **strat_kw),
        state_path=Path(tmp_path) / "state.json", dry_run=dry_run, verbose=False,
    )


# --------------------------------------------------------------- ochish
def test_places_order_with_correct_risk(tmp_path):
    broker = make_broker()
    cfg = Config()
    cfg.risk.risk_per_trade = 0.005
    trader = make_trader(broker, tmp_path, side=1, cfg=cfg)

    out = trader.run_once()
    assert out["action"] == "placed"
    assert out["side"] == 1

    equity = broker.account().equity
    # Haqiqiy risk byudjetdan oshmasligi kerak (lot yaxlitlash tufayli kamroq bo'lishi mumkin)
    assert out["risk"] <= equity * 0.005 * 1.01
    assert out["risk"] > equity * 0.005 * 0.9
    assert len(broker.positions()) == 1


def test_short_signal_opens_short(tmp_path):
    broker = make_broker()
    out = make_trader(broker, tmp_path, side=-1).run_once()
    assert out["action"] == "placed"
    assert broker.positions()[0].side == -1


def test_no_signal_does_nothing(tmp_path):
    broker = make_broker()
    assert make_trader(broker, tmp_path, side=0).run_once()["action"] == "no_signal"
    assert not broker.positions()


def test_dry_run_places_nothing_in_mt5_but_reports(tmp_path):
    """PaperBroker dry-run'ni bilmaydi — dry-run MT5Broker darajasida ishlaydi."""
    from scalpkit.broker.mt5broker import MT5Broker
    b = MT5Broker(dry_run=True)
    res = b._send({"price": 100.0}, "TEST")
    assert res.ok
    assert "DRY-RUN" in res.message


def test_stop_and_target_are_placed_on_the_order(tmp_path):
    broker = make_broker()
    out = make_trader(broker, tmp_path, side=1).run_once()
    pos = broker.positions()[0]
    R = out["entry"] - out["sl"]
    assert pos.sl == pytest.approx(out["sl"])
    # TP2 = 3.5R
    assert (pos.tp - out["entry"]) == pytest.approx(3.5 * R, rel=1e-6)


# --------------------------------------------------------------- hajm
def test_skips_when_min_lot_exceeds_risk_budget(tmp_path):
    """Kichik hisobda minimal lot juda katta risk bersa — savdo qilinmaydi."""
    broker = make_broker(balance=200.0, volume_min=1.0, volume_step=1.0)
    out = make_trader(broker, tmp_path, side=1).run_once()
    assert out["action"] == "skip"
    assert "risk" in out["reason"] or "lot" in out["reason"]
    assert not broker.positions()


def test_skips_when_spread_makes_trade_too_expensive(tmp_path):
    """Spread stopga nisbatan keng bo'lsa savdo qilinmaydi."""
    broker = make_broker(spread=400.0)      # stop ~300, spread 400 -> xarajat > 2R
    out = make_trader(broker, tmp_path, side=1).run_once()
    assert out["action"] == "skip"
    assert "spread" in out["reason"]


def test_leverage_cap_blocks_oversized_position(tmp_path):
    cfg = Config()
    cfg.risk.risk_per_trade = 0.50       # ataylab katta
    cfg.risk.max_leverage = 1.0
    broker = make_broker()
    out = make_trader(broker, tmp_path, side=1, cfg=cfg).run_once()
    assert out["action"] == "skip"
    assert "leverage" in out["reason"]


# --------------------------------------------------------------- boshqaruv
def _open_then_move(tmp_path, move_r, side=1, bars_after=1, params=None):
    """Pozitsiya ochib, narxni `move_r` R ga suradi va boshqaruvni ishga tushiradi."""
    base = generate_synthetic(n_bars=420, seed=21)
    broker = make_broker(base)
    trader = make_trader(broker, tmp_path, side=side)
    trader.strategy.params.update(params or {})
    out = trader.run_once()
    assert out["action"] == "placed"

    R = abs(out["entry"] - out["sl"])
    target = out["entry"] + side * move_r * R
    extra = pd.DataFrame(
        {"open": target, "high": max(target, out["entry"]) + 1,
         "low": min(target, out["entry"]) - 1, "close": target, "volume": 100.0},
        index=pd.date_range(base.index[-1] + pd.Timedelta("5min"),
                            periods=bars_after, freq="5min", tz="UTC"),
    )
    if side > 0:
        extra["high"] = target
        extra["low"] = out["entry"] - 0.05 * R
    else:
        extra["low"] = target
        extra["high"] = out["entry"] + 0.05 * R

    broker._bars = pd.concat([base, extra])
    trader.strategy.side = 0          # yangi signal bermaydi
    # Broker indeksi hali `base` ning oxirgi barida — qo'shilgan barlarga
    # yetish uchun bitta qo'shimcha qadam kerak
    for _ in range(bars_after + 1):
        broker.step()
    assert broker.index >= len(base), "qo'shilgan barga yetilmadi"
    return broker, trader, out, R


def test_tp1_closes_part_and_moves_stop_to_reduced_risk(tmp_path):
    """TP1 dan keyin stop -0.35R ga suriladi, ZARARSIZLIKKA emas.

    Trailing ataylab o'chirilgan: standart sozlamada u ham 1.5R da yonadi
    va stopni yuqoriroqqa suradi (bu to'g'ri, lekin bu yerda TP1 ning
    o'z ta'sirini ajratib ko'rish kerak).
    """
    broker, trader, out, R = _open_then_move(
        tmp_path, move_r=1.6, params={"trail_after_r": 999.0}
    )
    before = broker.positions()[0].volume if broker.positions() else 0
    trader.run_once()

    partials = [t for t in broker.closed_trades if t["reason"] == "tp1"]
    assert partials, "TP1 da qisman yopilish bo'lishi kerak"
    assert len(broker.positions()) == 1, "qolgan qism ochiq turishi kerak"
    pos = broker.positions()[0]
    assert pos.volume < before
    assert pos.sl == pytest.approx(out["entry"] - 0.35 * R, rel=1e-3)
    # Eng muhimi: stop zararsizlikda EMAS
    assert pos.sl < out["entry"] - 0.2 * R


def test_trailing_takes_over_when_it_is_better_than_the_tp1_stop(tmp_path):
    """Trailing TP1 stopidan yuqoriroq bo'lsa, u ustun kelishi kerak."""
    broker, trader, out, R = _open_then_move(tmp_path, move_r=1.6)
    trader.run_once()
    pos = broker.positions()[0]
    tp1_level = out["entry"] - 0.35 * R
    assert pos.sl > tp1_level, "trailing stopni yuqoriroqqa surishi kerak edi"


def test_trailing_ignores_moves_smaller_than_the_minimum_step(tmp_path):
    """Mayda harakatlarda stop surilmaydi — brokerga ortiqcha so'rov bo'lmasin."""
    broker, trader, out, R = _open_then_move(tmp_path, move_r=1.8)
    trader.run_once()
    sl_after_first = broker.positions()[0].sl

    # Narxni juda oz (0.02R) suramiz -> trailing qadamidan kichik
    last = broker._bars.index[-1]
    # Bar past nuqtasi trailing stopdan yuqorida qolishi kerak, aks holda
    # pozitsiya yopilib ketadi va test boshqa narsani o'lchaydi
    tiny = out["entry"] + 1.82 * R
    broker._bars = pd.concat([broker._bars, pd.DataFrame(
        {"open": tiny, "high": tiny, "low": tiny - 1.0, "close": tiny, "volume": 100.0},
        index=[last + pd.Timedelta("5min")])])
    broker.step()
    trader.run_once()
    assert broker.positions()[0].sl == pytest.approx(sl_after_first)


def test_stop_never_moves_backwards(tmp_path):
    broker, trader, out, R = _open_then_move(tmp_path, move_r=1.6)
    trader.run_once()
    good_sl = broker.positions()[0].sl

    # Narx qaytadi -> stop orqaga surilmasligi kerak
    last = broker._bars.index[-1]
    back = pd.DataFrame(
        {"open": out["entry"], "high": out["entry"], "low": out["entry"] - 0.2 * R,
         "close": out["entry"], "volume": 100.0},
        index=[last + pd.Timedelta("5min")],
    )
    broker._bars = pd.concat([broker._bars, back])
    broker.step()
    trader.run_once()
    if broker.positions():
        assert broker.positions()[0].sl >= good_sl - 1e-6


def test_time_stop_closes_only_stagnant_positions(tmp_path):
    cfg = Config()
    broker = make_broker()
    trader = make_trader(broker, tmp_path, side=1, cfg=cfg)
    trader.strategy.params["time_stop_bars"] = 2
    out = trader.run_once()
    assert out["action"] == "placed"

    # Narx joyida turadi -> vaqt stopi ishlashi kerak
    last = broker._bars.index[-1]
    flat = pd.DataFrame(
        {"open": out["entry"], "high": out["entry"] + 1, "low": out["entry"] - 1,
         "close": out["entry"], "volume": 100.0},
        index=pd.date_range(last + pd.Timedelta("5min"), periods=4, freq="5min", tz="UTC"),
    )
    broker._bars = pd.concat([broker._bars, flat])
    trader.strategy.side = 0
    for _ in range(4):
        broker.step()
        trader.run_once()
    assert any(t["reason"] == "time_stop" for t in broker.closed_trades)


# --------------------------------------------------------------- risk
def test_daily_trade_limit_blocks_new_entries(tmp_path):
    cfg = Config()
    cfg.risk.max_trades_per_day = 1
    broker = make_broker()
    trader = make_trader(broker, tmp_path, side=1, cfg=cfg)
    assert trader.run_once()["action"] == "placed"

    broker.close_position(broker.positions()[0].ticket)
    out = trader.run_once()
    assert out["action"] == "blocked"
    assert "kunlik savdolar" in out["reason"]


def test_daily_loss_limit_blocks_new_entries(tmp_path):
    cfg = Config()
    cfg.risk.daily_loss_limit = 0.01
    broker = make_broker()
    trader = make_trader(broker, tmp_path, side=1, cfg=cfg)
    trader.run_once()                              # kun boshlanadi
    broker.balance -= 500.0                        # -5 %
    broker.close_position(broker.positions()[0].ticket)

    out = trader.run_once()
    assert out["action"] == "blocked"
    assert "zarar" in out["reason"]


def test_does_not_open_a_second_position(tmp_path):
    broker = make_broker()
    trader = make_trader(broker, tmp_path, side=1)
    trader.run_once()
    out = trader.run_once()
    assert out["action"] == "holding"
    assert len(broker.positions()) == 1


# --------------------------------------------------------------- holat
def test_state_survives_a_restart(tmp_path):
    broker = make_broker()
    trader = make_trader(broker, tmp_path, side=1)
    out = trader.run_once()
    ticket = str(out["ticket"])

    saved = json.loads((Path(tmp_path) / "state.json").read_text())
    assert ticket in saved["trades"]
    assert saved["trades"][ticket]["risk_per_unit"] == pytest.approx(
        out["entry"] - out["sl"]
    )

    # Yangi trader — holatni fayldan o'qiydi
    reloaded = make_trader(broker, tmp_path, side=0)
    assert ticket in reloaded.state.trades
    assert reloaded.state.trades[ticket].entry_price == pytest.approx(out["entry"])


def test_state_is_recovered_when_file_is_lost(tmp_path):
    broker = make_broker()
    trader = make_trader(broker, tmp_path, side=1)
    out = trader.run_once()

    # Holat fayli yo'qoldi, lekin MT5 da pozitsiya bor
    fresh = make_trader(broker, tmp_path / "empty", side=0)
    fresh.run_once()
    ticket = str(broker.positions()[0].ticket)
    assert ticket in fresh.state.trades
    # R stop masofasidan tiklanadi
    assert fresh.state.trades[ticket].risk_per_unit == pytest.approx(
        out["entry"] - out["sl"], rel=0.02
    )
