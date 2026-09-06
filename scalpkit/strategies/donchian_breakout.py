"""SWING STRATEGIYA — "Donchian Breakout" (trendni kuzatish).

G'oya
-----
Klassik trend-following: narx N barlik kanalning yuqorisini buzsa — sotib
olamiz, pastini buzsa — sotamiz. Chiqish teskari tomondagi qisqaroq kanal
buzilishi yoki ATR trailing orqali.

Nima uchun bu skalpingdan boshqacha ishlaydi
-------------------------------------------
1. **Xarajat to'sig'i qulaydi.** D1 da stop narxning ~6 % i, spread esa
   0.03 % — xarajat 0.005R. M5 da xuddi shu spread 0.09-0.14R turadi.
   Ya'ni yuqori timeframe'da ustunlik ancha kichik bo'lsa ham yetarli.

2. **MAQSAD QO'YILMAYDI.** Bu eng muhim farq. Trend-following foydasi
   kam sonli juda katta yutuqlardan keladi (o'ng dumdan). Savdolarning
   ~60-70 % i zarar, ~5 % i esa butun natijani yaratadi. 3R da maqsad
   qo'yish aynan o'sha 5 % ni kesib tashlaydi va tizimni yo'q qiladi.
   Shuning uchun `tp2_r = 0` (maqsad yo'q) va chiqish faqat trailing
   yoki kanal signali orqali.

3. **Filtrlar kamroq.** Buzilishning o'zi trendning tasdig'i — ustiga
   ADX, RSI, hajm filtrlarini qo'yish savdolar sonini shovqin darajasiga
   tushiradi va overfitting xavfini oshiradi.

Qoidalar (long uchun; short — to'liq oyna aksi)
----------------------------------------------
REJIM
  R1  narx > EMA(trend_len)          — uzoq muddatli yo'nalish
  R2  ATR% belgilangan oynada        — juda sust yoki xaotik bozor emas
  R3  (ixtiyoriy) H1/H4 yo'nalishi mos

TRIGGER
  T1  close > oxirgi `entry_len` barning eng yuqori nuqtasi
      (joriy bar hisobga olinmaydi)
  T2  oxirgi `cooldown_len` barda buzilish bo'lmagan — takroriy
      "arra" harakatlarga tushmaslik uchun

CHIQISH
  X1  stop:     kirish - sl_atr_mult x ATR
  X2  trailing: eng yuqori nuqta - trail_atr_mult x ATR
  X3  kanal:    close < oxirgi `exit_len` barning eng past nuqtasi
  X4  maqsad:   YO'Q
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .base import Strategy, session_mask, week_guard_mask


class DonchianBreakout(Strategy):
    name = "donchian_breakout"

    defaults: dict[str, Any] = {
        # --- rejim ---
        "trend_len": 200,             # uzoq muddatli EMA
        "require_trend_filter": True,
        "min_atr_pct": 0.0020,        # profil timeframe'ga qarab masshtablaydi
        "max_atr_pct": 0.0120,
        "require_htf": False,         # buzilishning o'zi tasdiq — qo'shimcha shart shart emas
        "use_session_filter": False,  # swing uchun seans filtri ma'nosiz
        "session_start_hour": 0,
        "session_end_hour": 24,
        "weekend_flat": False,
        "week_close_hour_utc": 19,
        "week_close_dow": 4,
        "week_open_skip_bars": 0,
        # --- kanal ---
        "entry_len": 20,              # kirish kanali (Turtle: 20 yoki 55)
        "exit_len": 10,               # chiqish kanali (odatda entry_len / 2)
        "cooldown_len": 3,            # takroriy buzilishlar orasidagi eng kam masofa
        # --- kirish ---
        "entry_mode": "market",       # buzilishni quvish kerak — limit kutib qolmaydi
        "entry_offset_atr": 0.0,
        "entry_limit_bars": 1,
        # --- stop va chiqish ---
        "sl_atr_mult": 2.0,           # swing uchun kengroq
        "min_sl_atr": 1.5,
        "max_sl_atr": 3.5,
        "tp1_r": 0.0,                 # qisman olish yo'q
        "tp1_fraction": 0.0,
        "tp2_r": 0.0,                 # MAQSAD YO'Q — dumni kesmaslik uchun
        "tp1_stop_to_r": 0.0,
        "be_trigger_r": 1e9,          # zararsizlikka o'tish yo'q: trend nafas oladi
        "be_offset_r": 0.0,
        "trail_after_r": 0.5,
        "trail_atr_mult": 3.0,        # keng trailing — trenddan erta chiqmaslik
        "trail_min_step_atr": 0.25,
        "time_stop_bars": 1_000_000,  # vaqt stopi yo'q
        "time_stop_min_r": 0.0,
        "exit_on_ema_cross": False,
        # --- yo'nalish ---
        "allow_long": True,
        "allow_short": True,
    }

    def generate(self, f: pd.DataFrame) -> pd.DataFrame:
        p = self.params

        # ---------- REJIM ----------
        regime = f["atr_pct"].between(float(p["min_atr_pct"]), float(p["max_atr_pct"]))
        if p["use_session_filter"]:
            regime &= session_mask(f, int(p["session_start_hour"]),
                                   int(p["session_end_hour"]))
        if p.get("weekend_flat", False):
            regime &= week_guard_mask(
                f.index, int(p["week_close_dow"]), int(p["week_close_hour_utc"]),
                int(p["week_open_skip_bars"]),
            )

        trend = f["close"].ewm(span=int(p["trend_len"]), adjust=False,
                               min_periods=int(p["trend_len"])).mean()
        if p["require_trend_filter"]:
            trend_up, trend_dn = f["close"] > trend, f["close"] < trend
        else:
            trend_up = trend_dn = pd.Series(True, index=f.index)

        if p["require_htf"]:
            trend_up &= f["htf_bull"].fillna(False)
            trend_dn &= f["htf_bear"].fillna(False)

        # ---------- KANALLAR ----------
        # `.shift(1)` — joriy bar kanalni o'zgartirmasligi kerak, aks holda
        # narx har doim "o'z cho'qqisini" buzgan bo'lib chiqadi.
        entry_len, exit_len = int(p["entry_len"]), int(p["exit_len"])
        up_channel = f["high"].rolling(entry_len, min_periods=entry_len).max().shift(1)
        dn_channel = f["low"].rolling(entry_len, min_periods=entry_len).min().shift(1)
        exit_up = f["high"].rolling(exit_len, min_periods=exit_len).max().shift(1)
        exit_dn = f["low"].rolling(exit_len, min_periods=exit_len).min().shift(1)

        broke_up = f["close"] > up_channel
        broke_dn = f["close"] < dn_channel

        # ---------- TAKRORIY BUZILISHGA TO'SIQ ----------
        # Yon harakatda narx kanalni ketma-ket buzib turadi va har safar
        # zarar keltiradi. Buzilishlar orasida kamida `cooldown_len` bar
        # bo'lishini talab qilamiz.
        cooldown = int(p["cooldown_len"])
        if cooldown > 0:
            recent_up = broke_up.fillna(False).shift(1).rolling(
                cooldown, min_periods=1).max().fillna(0) > 0
            recent_dn = broke_dn.fillna(False).shift(1).rolling(
                cooldown, min_periods=1).max().fillna(0) > 0
            broke_up &= ~recent_up
            broke_dn &= ~recent_dn

        long_sig = regime & trend_up & broke_up
        short_sig = regime & trend_dn & broke_dn
        if not p["allow_long"]:
            long_sig &= False
        if not p["allow_short"]:
            short_sig &= False

        signal = pd.Series(0, index=f.index, dtype=np.int8)
        signal[long_sig.fillna(False)] = 1
        signal[short_sig.fillna(False)] = -1
        signal[(long_sig & short_sig).fillna(False)] = 0

        # ---------- STOP ----------
        dist = float(p["sl_atr_mult"]) * f["atr"]
        stop_price = pd.Series(np.nan, index=f.index, dtype=float)
        stop_price = stop_price.where(signal != 1, f["close"] - dist)
        stop_price = stop_price.where(signal != -1, f["close"] + dist)

        return pd.DataFrame(
            {
                "signal": signal,
                "stop_price": stop_price,
                "atr": f["atr"],
                "entry_ref": f["close"].where(signal != 0),
                # Chiqish kanali — dvigatel buni TP dan mustaqil bajaradi
                "exit_long": (f["close"] < exit_dn).fillna(False),
                "exit_short": (f["close"] > exit_up).fillna(False),
            },
            index=f.index,
        )

    @classmethod
    def param_space(cls, base: dict[str, Any] | None = None) -> dict[str, list[Any]]:
        p = {**cls.defaults, **(base or {})}
        atr0 = float(p["min_atr_pct"])
        return {
            "min_atr_pct": [round(atr0 * k, 8) for k in (0.6, 0.8, 1.0, 1.3)],
            "entry_len": [20, 30, 40, 55],
            "exit_len": [8, 10, 15, 20],
            "trend_len": [100, 150, 200],
            "sl_atr_mult": [1.5, 2.0, 2.5, 3.0],
            "trail_atr_mult": [2.5, 3.0, 4.0, 5.0],
            "cooldown_len": [0, 3, 6],
            "require_trend_filter": [True, False],
        }
