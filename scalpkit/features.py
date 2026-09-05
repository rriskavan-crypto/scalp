"""OHLCV dan strategiya uchun kerakli barcha ustunlarni quradi.

Kelajakka qarash yo'q: `t` qatoridagi har bir qiymat faqat `t` bari yopilgan
paytda mavjud bo'lgan ma'lumotdan hisoblanadi. Yuqori timeframe (H1) qiymatlari
esa bir bar surilgan — H1 bari yopilmaguncha ishlatilmaydi.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import indicators as ind
from .data.loader import align_htf, resample_ohlcv

DEFAULT_FEATURE_PARAMS: dict[str, int | float] = {
    "ema_fast": 21,
    "ema_mid": 55,
    "ema_slow": 200,
    "atr_len": 14,
    "rsi_len": 7,
    "adx_len": 14,
    "donchian_len": 20,
    "bb_len": 20,
    "bb_mult": 2.0,
    "vol_z_len": 50,
    "swing_len": 5,
    "htf_rule": "1h",
    "htf_ema": 50,
}


def build_features(df: pd.DataFrame, params: dict | None = None) -> pd.DataFrame:
    """OHLCV → indikatorlar bilan boyitilgan DataFrame."""
    p = {**DEFAULT_FEATURE_PARAMS, **(params or {})}
    out = df.copy()
    o, h, l, c, v = out["open"], out["high"], out["low"], out["close"], out["volume"]

    # --- trend ---
    out["ema_fast"] = ind.ema(c, int(p["ema_fast"]))
    out["ema_mid"] = ind.ema(c, int(p["ema_mid"]))
    out["ema_slow"] = ind.ema(c, int(p["ema_slow"]))
    out["ema_fast_slope"] = out["ema_fast"].diff() / c

    # --- volatilitet ---
    out["atr"] = ind.atr(h, l, c, int(p["atr_len"]))
    out["atr_pct"] = out["atr"] / c
    out["atr_pct_med"] = out["atr_pct"].rolling(288, min_periods=48).median()  # ~1 kun

    # --- impuls / kuch ---
    out["rsi"] = ind.rsi(c, int(p["rsi_len"]))
    out["adx"], out["di_plus"], out["di_minus"] = ind.adx(h, l, c, int(p["adx_len"]))

    # --- struktura ---
    out["dc_high"], out["dc_low"] = ind.donchian(h, l, int(p["donchian_len"]))
    # Breakout tekshiruvi uchun *oldingi* kanal kerak (joriy bar kanalni o'zgartiradi)
    out["dc_high_prev"] = out["dc_high"].shift(1)
    out["dc_low_prev"] = out["dc_low"].shift(1)
    out["swing_low"] = ind.swing_low(l, int(p["swing_len"]))
    out["swing_high"] = ind.swing_high(h, int(p["swing_len"]))

    # --- hajm ---
    out["vol_z"] = ind.rolling_zscore(v, int(p["vol_z_len"]))

    # --- VWAP va Bollinger (range strategiyasi uchun) ---
    out["vwap"], out["vwap_sd"] = ind.session_vwap(h, l, c, v)
    out["bb_mid"], out["bb_up"], out["bb_dn"] = ind.bollinger(
        c, int(p["bb_len"]), float(p["bb_mult"])
    )

    # --- bar tavsifi ---
    bar_range = (h - l).replace(0.0, np.nan)
    out["body_pct"] = (c - o).abs() / bar_range
    out["body_atr"] = (c - o) / out["atr"].replace(0.0, np.nan)
    out["close_pos"] = (c - l) / bar_range  # 1.0 = barning tepasida yopilgan

    # --- yuqori timeframe (H1) yo'nalishi, kelajaksiz ---
    htf = resample_ohlcv(df, str(p["htf_rule"]))
    htf_feat = pd.DataFrame(index=htf.index)
    htf_feat["htf_close"] = htf["close"]
    htf_feat["htf_ema"] = ind.ema(htf["close"], int(p["htf_ema"]))
    htf_feat["htf_ema_slope"] = htf_feat["htf_ema"].diff()
    aligned = align_htf(out.index, htf_feat, str(p["htf_rule"]))
    out[aligned.columns] = aligned

    out["htf_bull"] = (out["htf_close"] > out["htf_ema"]) & (out["htf_ema_slope"] > 0)
    out["htf_bear"] = (out["htf_close"] < out["htf_ema"]) & (out["htf_ema_slope"] < 0)

    # --- vaqt ---
    out["hour"] = out.index.hour
    out["dow"] = out.index.dayofweek
    return out


def warmup_bars(params: dict | None = None) -> int:
    """Indikatorlar to'yinishi uchun kerakli minimal barlar soni."""
    p = {**DEFAULT_FEATURE_PARAMS, **(params or {})}
    htf_bars_in_m5 = int(pd.Timedelta(str(p["htf_rule"])) / pd.Timedelta("5min"))
    return int(max(p["ema_slow"], p["vol_z_len"], 288, p["htf_ema"] * htf_bars_in_m5)) + 10
