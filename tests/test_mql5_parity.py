"""MQL5 EA va Python strategiyasining mosligi.

Ikkita mustaqil amalga oshirish bor: `scalpkit` (Python, tadqiqot uchun) va
`ScalpKit_M5.mq5` (MetaTrader 5, savdo uchun). Ular ajralib ketsa, backtest
natijasi real savdoni tasvirlamay qo'yadi — ya'ni butun tekshiruv ishi
qiymatini yo'qotadi.

Bu testlar EA fayldagi `input` qiymatlarini Python sozlamalari bilan
qatorma-qator solishtiradi.
"""

import re
from pathlib import Path

import pytest

from scalpkit.config import Config
from scalpkit.features import DEFAULT_FEATURE_PARAMS
from scalpkit.strategies import get_strategy

EA_PATH = Path(__file__).resolve().parents[1] / "mql5" / "Experts" / "ScalpKit_M5.mq5"

# EA input nomi -> (Python qiymati qayerdan olinadi, kalit)
STRATEGY_MAP = {
    "InpMinAtrPct": "min_atr_pct",
    "InpMaxAtrPct": "max_atr_pct",
    "InpAdxMin": "adx_min",
    "InpRequireHTF": "require_htf",
    "InpUseSession": "use_session_filter",
    "InpSessionStartUTC": "session_start_hour",
    "InpSessionEndUTC": "session_end_hour",
    "InpImpulseLookback": "impulse_lookback",
    "InpImpulseBodyAtr": "impulse_body_atr",
    "InpImpulseVolZ": "impulse_vol_z",
    "InpPullbackLookback": "pullback_lookback",
    "InpTouchAtr": "touch_atr",
    "InpRsiPullbackLong": "rsi_pullback_long",
    "InpRsiPullbackShort": "rsi_pullback_short",
    "InpTriggerVolZ": "trigger_vol_z",
    "InpTriggerClosePos": "trigger_close_pos",
    "InpMaxExtensionAtr": "max_extension_atr",
    "InpEntryOffsetAtr": "entry_offset_atr",
    "InpEntryLimitBars": "entry_limit_bars",
    "InpSlBufferAtr": "sl_buffer_atr",
    "InpMinSlAtr": "min_sl_atr",
    "InpMaxSlAtr": "max_sl_atr",
    "InpTp1R": "tp1_r",
    "InpTp1Fraction": "tp1_fraction",
    "InpTp2R": "tp2_r",
    "InpTp1StopToR": "tp1_stop_to_r",
    "InpBeTriggerR": "be_trigger_r",
    "InpBeOffsetR": "be_offset_r",
    "InpTrailAfterR": "trail_after_r",
    "InpTrailAtrMult": "trail_atr_mult",
    "InpTrailMinStepAtr": "trail_min_step_atr",
    "InpTimeStopBars": "time_stop_bars",
    "InpTimeStopMinR": "time_stop_min_r",
    "InpExitOnEmaCross": "exit_on_ema_cross",
}

FEATURE_MAP = {
    "InpEmaFast": "ema_fast", "InpEmaMid": "ema_mid", "InpEmaSlow": "ema_slow",
    "InpAtrLen": "atr_len", "InpRsiLen": "rsi_len", "InpAdxLen": "adx_len",
    "InpDonchianLen": "donchian_len", "InpVolZLen": "vol_z_len",
    "InpSwingLen": "swing_len", "InpHtfEma": "htf_ema",
}

RISK_MAP = {
    "InpRiskPerTrade": "risk_per_trade",
    "InpMaxLeverage": "max_leverage",
    "InpMaxTradesPerDay": "max_trades_per_day",
    "InpDailyLossLimit": "daily_loss_limit",
    "InpMaxConsecLosses": "max_consecutive_losses",
    "InpCooldownBars": "cooldown_bars_after_loss",
    "InpStreakCooldown": "cooldown_bars_after_streak",
    "InpHalveRiskDD": "halve_risk_drawdown",
    "InpMinStopPct": "min_stop_pct",
    "InpMaxStopPct": "max_stop_pct",
}


@pytest.fixture(scope="module")
def ea_inputs() -> dict[str, object]:
    assert EA_PATH.exists(), f"EA fayli topilmadi: {EA_PATH}"
    src = EA_PATH.read_text(encoding="utf-8")
    out: dict[str, object] = {}
    for m in re.finditer(r"^input\s+\w+\s+(\w+)\s*=\s*([^;]+);", src, re.M):
        name, raw = m.group(1), m.group(2).strip()
        if raw in ("true", "false"):
            out[name] = (raw == "true")
        else:
            out[name] = float(raw)
    return out


def _assert_same(ea_value, py_value, name: str) -> None:
    if isinstance(py_value, bool) or isinstance(ea_value, bool):
        assert bool(ea_value) == bool(py_value), f"{name}: EA={ea_value} Python={py_value}"
    else:
        assert float(ea_value) == pytest.approx(float(py_value)), \
            f"{name}: EA={ea_value} Python={py_value}"


@pytest.mark.parametrize("ea_name,py_key", sorted(STRATEGY_MAP.items()))
def test_strategy_parameters_match(ea_inputs, ea_name, py_key):
    params = get_strategy("momentum_pullback").params
    assert ea_name in ea_inputs, f"{ea_name} EA da topilmadi"
    _assert_same(ea_inputs[ea_name], params[py_key], ea_name)


@pytest.mark.parametrize("ea_name,py_key", sorted(FEATURE_MAP.items()))
def test_indicator_lengths_match(ea_inputs, ea_name, py_key):
    assert ea_name in ea_inputs, f"{ea_name} EA da topilmadi"
    _assert_same(ea_inputs[ea_name], DEFAULT_FEATURE_PARAMS[py_key], ea_name)


@pytest.mark.parametrize("ea_name,py_key", sorted(RISK_MAP.items()))
def test_risk_parameters_match(ea_inputs, ea_name, py_key):
    assert ea_name in ea_inputs, f"{ea_name} EA da topilmadi"
    _assert_same(ea_inputs[ea_name], getattr(Config().risk, py_key), ea_name)


def test_limit_entry_is_the_default_in_both(ea_inputs):
    params = get_strategy("momentum_pullback").params
    assert ea_inputs["InpUseLimitEntry"] is True
    assert params["entry_mode"] == "limit"


def test_cost_guard_threshold_matches_python(ea_inputs):
    """EA va Python bir xil xarajat chegarasida savdoni rad etishi kerak."""
    import inspect

    from scalpkit import trader

    source = inspect.getsource(trader.LiveTrader._open_trade)
    m = re.search(r"cost_r\s*>\s*([0-9.]+)", source)
    assert m, "trader.py da xarajat chegarasi topilmadi"
    _assert_same(ea_inputs["InpMaxCostR"], float(m.group(1)), "InpMaxCostR")


def test_ea_has_no_unbalanced_braces():
    """Kompilyatorsiz eng oddiy, lekin foydali tekshiruv."""
    src = EA_PATH.read_text(encoding="utf-8")
    clean, state = _strip_comments_and_strings(src)
    assert state == "code", "yopilmagan satr yoki kommentariy bor"
    for opener, closer in (("{", "}"), ("(", ")"), ("[", "]")):
        assert clean.count(opener) == clean.count(closer), \
            f"'{opener}{closer}' qavslar muvozanatda emas"


def _strip_comments_and_strings(src: str) -> tuple[str, str]:
    out: list[str] = []
    i, n, state = 0, len(src), "code"
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if state == "code":
            if c == "/" and nxt == "/":
                state = "line"; i += 2; continue
            if c == "/" and nxt == "*":
                state = "block"; i += 2; continue
            if c in "\"'":
                state = "dq" if c == '"' else "sq"; i += 1; continue
            out.append(c); i += 1; continue
        if state == "line":
            if c == "\n":
                state = "code"; out.append("\n")
            i += 1; continue
        if state == "block":
            if c == "*" and nxt == "/":
                state = "code"; i += 2; continue
            i += 1; continue
        quote = '"' if state == "dq" else "'"
        if c == "\\":
            i += 2; continue
        if c == quote:
            state = "code"
        i += 1
    return "".join(out), state
