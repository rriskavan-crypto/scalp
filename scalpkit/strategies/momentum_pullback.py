"""ASOSIY STRATEGIYA — "M5 Momentum Pullback" (trendni davom ettirish skalpi).

G'oya
-----
BTC M5 da vaqtning ~70 % i shovqin (chop). Barqaror ustunlik shovqinni bashorat
qilishdan emas, **allaqachon boshlangan impulsga sayoz orqaga qaytishdan keyin
qo'shilishdan** kelib chiqadi.

Komissiya haqiqati
------------------
Bir to'liq savdo ~0.145 % turadi (taker 0.05 % x2 + sirpanish). Agar stop
masofasi (R) narxning 0.20 % i bo'lsa, xarajat 0.72R ga teng — bunday tizim
matematik jihatdan yutqazishga mahkum. Shuning uchun strategiya faqat
volatilitet yetarli bo'lganda (ATR% >= 0.20 %) savdo qiladi va stopni
1.0-2.2 ATR oralig'ida qo'yadi. Natijada R odatda 0.35-0.90 % bo'lib,
xarajat 0.16-0.41R ga tushadi.

Qoidalar (long uchun; short — to'liq oyna aksi)
----------------------------------------------
REJIM FILTRLARI (barchasi bajarilishi shart)
  R1  ATR14/narx  ∈ [min_atr_pct, max_atr_pct]
  R2  ADX(14) >= adx_min                      → trend bor
  R3  EMA21 > EMA55 > EMA200 va narx > EMA200 → M5 struktura ko'tarilish
  R4  H1: narx > EMA50 va EMA50 o'sib boryapti → yuqori TF mos
  R5  Savdo seansi (UTC soat oynasi)

SETUP
  S1  Oxirgi `impulse_lookback` barda impuls bo'lgan:
      tana >= impulse_body_atr x ATR va hajm z >= impulse_vol_z,
      YOKI Donchian(20) yuqorisi buzilgan
  S2  Narx qiymat zonasiga qaytgan: oxirgi `pullback_lookback` barda
      low <= EMA21 + touch_atr x ATR
  S3  Shu oynada RSI(7) <= rsi_pullback ga tushgan (haqiqiy chuqurlashish)

TRIGGER (bar yopilishida)
  T1  close > oldingi bar high      → qaytarib olish
  T2  close > EMA21 va close > open
  T3  close_pos >= trigger_close_pos (bar tepasida yopilgan)
  T4  hajm z >= trigger_vol_z
  T5  close <= EMA21 + max_extension_atr x ATR → kech qolib quvmaslik

Kirish keyingi bar OCHILISHIDA amalga oshadi (kelajakka qarash yo'q).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .base import Strategy, rolling_any, session_mask


class MomentumPullback(Strategy):
    name = "momentum_pullback"

    defaults: dict[str, Any] = {
        # --- rejim filtrlari ---
        "min_atr_pct": 0.0020,
        "max_atr_pct": 0.0120,
        "adx_min": 20.0,
        "require_htf": True,
        "use_session_filter": True,
        "session_start_hour": 6,
        "session_end_hour": 22,
        # --- setup ---
        "impulse_lookback": 12,
        "impulse_body_atr": 0.8,
        "impulse_vol_z": 1.0,
        "pullback_lookback": 4,
        "touch_atr": 0.25,
        "rsi_pullback_long": 45.0,
        "rsi_pullback_short": 55.0,
        # --- trigger ---
        "trigger_vol_z": -0.2,
        "trigger_close_pos": 0.5,
        "max_extension_atr": 1.0,
        # --- stop / target ---
        "sl_buffer_atr": 0.25,
        "min_sl_atr": 1.0,
        "max_sl_atr": 2.2,
        "tp1_r": 1.5,
        "tp1_fraction": 0.35,
        "tp2_r": 3.5,
        "tp1_stop_to_r": -0.35,
        # True bo'lsa TP1 dan keyin stop DARHOL zararsizlikka suriladi —
        # keng tarqalgan, lekin payoff'ni buzadigan klassik usul.
        # Taqqoslash uchun qoldirilgan; standart holatda o'chirilgan.
        "be_after_tp1": False,
        "be_trigger_r": 2.0,
        "be_offset_r": 0.05,
        "trail_atr_mult": 2.5,
        "trail_after_r": 1.5,
        "trail_min_step_atr": 0.15,   # jonli savdoda stopni mayda-mayda surmaslik
        "time_stop_bars": 24,
        "time_stop_min_r": 0.5,
        "exit_on_ema_cross": True,
        # --- kirish usuli ---
        # "limit"  : trigger yopilishidan `entry_offset_atr` ATR pastroqqa limit
        #            qo'yiladi -> maker komissiyasi + yaxshiroq narx,
        #            lekin bir qism savdo o'tkazib yuboriladi
        # "market" : keyingi bar ochilishida bozor narxida (kafolatlangan ijro,
        #            taker komissiyasi + sirpanish)
        "entry_mode": "limit",
        "entry_offset_atr": 0.15,
        "entry_limit_bars": 3,
        # --- yo'nalish ---
        "allow_long": True,
        "allow_short": True,
    }

    def generate(self, f: pd.DataFrame) -> pd.DataFrame:
        p = self.params

        # ---------- REJIM ----------
        regime = (
            f["atr_pct"].between(float(p["min_atr_pct"]), float(p["max_atr_pct"]))
            & (f["adx"] >= float(p["adx_min"]))
        )
        if p["use_session_filter"]:
            regime &= session_mask(f, int(p["session_start_hour"]), int(p["session_end_hour"]))

        trend_up = (
            (f["ema_fast"] > f["ema_mid"])
            & (f["ema_mid"] > f["ema_slow"])
            & (f["close"] > f["ema_slow"])
        )
        trend_dn = (
            (f["ema_fast"] < f["ema_mid"])
            & (f["ema_mid"] < f["ema_slow"])
            & (f["close"] < f["ema_slow"])
        )
        if p["require_htf"]:
            trend_up &= f["htf_bull"].fillna(False)
            trend_dn &= f["htf_bear"].fillna(False)

        # ---------- SETUP: impuls ----------
        strong_body = (f["body_atr"].abs() >= float(p["impulse_body_atr"])) & (
            f["vol_z"] >= float(p["impulse_vol_z"])
        )
        impulse_up = (strong_body & (f["body_atr"] > 0)) | (f["close"] > f["dc_high_prev"])
        impulse_dn = (strong_body & (f["body_atr"] < 0)) | (f["close"] < f["dc_low_prev"])

        lb = int(p["impulse_lookback"])
        # `.shift(1)` — impuls joriy bardan OLDIN bo'lishi kerak
        had_impulse_up = rolling_any(impulse_up.fillna(False).shift(1).fillna(False), lb)
        had_impulse_dn = rolling_any(impulse_dn.fillna(False).shift(1).fillna(False), lb)

        # ---------- SETUP: orqaga qaytish ----------
        pb = int(p["pullback_lookback"])
        touch = float(p["touch_atr"])
        touched_up = rolling_any(f["low"] <= f["ema_fast"] + touch * f["atr"], pb)
        touched_dn = rolling_any(f["high"] >= f["ema_fast"] - touch * f["atr"], pb)
        rsi_dip = rolling_any(f["rsi"] <= float(p["rsi_pullback_long"]), pb)
        rsi_pop = rolling_any(f["rsi"] >= float(p["rsi_pullback_short"]), pb)

        # ---------- TRIGGER ----------
        vol_ok = f["vol_z"] >= float(p["trigger_vol_z"])
        pos_ok_up = f["close_pos"] >= float(p["trigger_close_pos"])
        pos_ok_dn = f["close_pos"] <= 1.0 - float(p["trigger_close_pos"])
        ext = float(p["max_extension_atr"])

        trig_up = (
            (f["close"] > f["high"].shift(1))
            & (f["close"] > f["ema_fast"])
            & (f["close"] > f["open"])
            & pos_ok_up
            & vol_ok
            & (f["close"] <= f["ema_fast"] + ext * f["atr"])
        )
        trig_dn = (
            (f["close"] < f["low"].shift(1))
            & (f["close"] < f["ema_fast"])
            & (f["close"] < f["open"])
            & pos_ok_dn
            & vol_ok
            & (f["close"] >= f["ema_fast"] - ext * f["atr"])
        )

        long_sig = regime & trend_up & had_impulse_up & touched_up & rsi_dip & trig_up
        short_sig = regime & trend_dn & had_impulse_dn & touched_dn & rsi_pop & trig_dn

        if not p["allow_long"]:
            long_sig &= False
        if not p["allow_short"]:
            short_sig &= False

        signal = pd.Series(0, index=f.index, dtype=np.int8)
        signal[long_sig.fillna(False)] = 1
        signal[short_sig.fillna(False)] = -1
        # Ikkalasi ham yonsa — signal berilmaydi (ziddiyat)
        signal[(long_sig & short_sig).fillna(False)] = 0

        # ---------- strukturaviy stop ----------
        buf = float(p["sl_buffer_atr"]) * f["atr"]
        stop_price = pd.Series(np.nan, index=f.index, dtype=float)
        stop_price = stop_price.where(signal != 1, f["swing_low"] - buf)
        stop_price = stop_price.where(signal != -1, f["swing_high"] + buf)

        # ---------- limit kirish darajasi ----------
        # Long uchun trigger yopilishidan pastroq, short uchun yuqoriroq.
        offset = float(p["entry_offset_atr"]) * f["atr"]
        entry_ref = f["close"] - signal.astype(float) * offset

        return pd.DataFrame(
            {
                "signal": signal,
                "stop_price": stop_price,
                "atr": f["atr"],
                "entry_ref": entry_ref.where(signal != 0),
            },
            index=f.index,
        )

    @classmethod
    def param_space(cls) -> dict[str, list[Any]]:
        return {
            "min_atr_pct": [0.0015, 0.0020, 0.0025, 0.0030],
            "adx_min": [16.0, 20.0, 24.0, 28.0],
            "impulse_lookback": [8, 12, 18],
            "pullback_lookback": [3, 4, 6],
            "rsi_pullback_long": [40.0, 45.0, 50.0],
            "max_extension_atr": [0.6, 1.0, 1.5],
            "min_sl_atr": [0.8, 1.0, 1.3],
            "max_sl_atr": [1.8, 2.2, 2.6],
            "tp1_r": [1.0, 1.2, 1.5],
            "tp2_r": [2.5, 3.0, 4.0],
            "trail_atr_mult": [1.8, 2.2, 3.0],
            "time_stop_bars": [16, 24, 36],
            "entry_mode": ["limit", "market"],
            "entry_offset_atr": [0.0, 0.15, 0.3],
        }
