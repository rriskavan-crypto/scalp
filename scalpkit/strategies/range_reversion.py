"""SWING STRATEGIYA — "Range Reversion" (o'rtachaga qaytish).

G'oya
-----
Bozor vaqtining katta qismini yon harakatda o'tkazadi. Bunday rejimda narx
o'rtachadan uzoqlashsa, unga qaytish ehtimoli o'sadi. Biz chekkadan
sotib olamiz va **o'rtachada** chiqamiz.

Trend strategiyasining TO'LIQ AKSI
----------------------------------
Bu ikkalasi bir-birini to'ldiradi, chunki ular qarama-qarshi rejimda
ishlaydi va chiqish tuzilmasi ham aks:

|                | donchian_breakout        | range_reversion            |
|----------------|--------------------------|----------------------------|
| Rejim          | ADX **yuqori** (trend)   | ADX **past** (yon harakat) |
| Kirish         | kanal buzilishida        | kanal chekkasida           |
| Maqsad         | **yo'q** — dum kesilmasin| **majburiy** — o'rtacha    |
| Trailing       | keng (3 ATR)             | yo'q                       |
| Vaqt stopi     | yo'q                     | **qisqa** — farazning muddati |

**Nima uchun bu yerda maqsad SHART.** Trend-following foydasi dumdan
keladi, shuning uchun maqsad zarar keltiradi. Mean-reversion'da esa
ustunlik aniq bir harakatda — o'rtachaga qaytishda. Undan keyin ushlab
turishning hech qanday asosi yo'q: narx o'rtachada bo'lsa, keyingi
harakat tasodifiy. Maqsadsiz mean-reversion — bu shunchaki
yo'nalishsiz pozitsiya.

**Nima uchun vaqt stopi SHART.** Faraz "narx tez orada qaytadi"
degani. 10-15 bar o'tib qaytmasa, faraz noto'g'ri chiqdi — bu
odatda yon harakat trendga aylanganini bildiradi va pozitsiya
trendga qarshi qolib ketadi. Mean-reversion strategiyalarini o'ldiradigan
asosiy sabab aynan shu.

Qoidalar (long uchun; short — to'liq oyna aksi)
----------------------------------------------
REJIM
  R1  ADX(14) < adx_max              — trend yo'q
  R2  ATR% belgilangan oynada
  R3  |narx - EMA(trend_len)| < range_dev_atr x ATR
      — uzoq muddatli o'rtachadan haddan tashqari uzoqlashmagan
        (aks holda bu qaytish emas, yangi trendning boshlanishi)

KIRISH — setup va trigger AJRATILGAN
  SETUP (oxirgi `setup_lookback` bar ichida)
    E1  z = (narx - SMA) / std  <=  -entry_z  — pastki chekkada
    E2  RSI(rsi_len) <= rsi_oversold          — qisqa muddatli o'ta sotilgan
  TRIGGER (joriy bar)
    E3  close > open                          — qaytish boshlangani tasdig'i
                                                ("tushayotgan pichoqni ushlamaslik")

  Bu ajratish MAJBURIY. Ikkalasini bitta barda talab qilish mantiqiy
  xato: `RSI(2) <= 10` oxirgi barlar pastga ketganini bildiradi,
  `close > open` esa o'sha barning yuqoriga yopilishini — ular
  deyarli bir-birini inkor qiladi. O'lchovda 327 ta signal 2 taga
  tushib qolgandi.

MUKOFOT/RISK FILTRI (majburiy)
  F1  (o'rtachagacha masofa) >= min_target_r x (stop masofasi)
      Kirish qaytish barida bo'lgani uchun narx allaqachon o'rtachaga
      yaqinlashgan bo'ladi. Filtrsiz savdolarning 61 % ida mukofot
      riskdan kichik chiqardi — bu tuzilma yutqazishga mahkum.

CHIQISH
  X1  maqsad: SMA (o'rtacha) — dinamik daraja
  X2  stop:   kirish - sl_atr_mult x ATR
  X3  vaqt:   time_stop_bars dan keyin so'zsiz
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .base import Strategy, rolling_any, session_mask, week_guard_mask


class RangeReversion(Strategy):
    name = "range_reversion"

    defaults: dict[str, Any] = {
        # --- rejim: trend strategiyasining aksi ---
        "adx_max": 25.0,              # bundan yuqorisi — trend, savdo yo'q
        "min_atr_pct": 0.0020,        # profil timeframe'ga qarab masshtablaydi
        "max_atr_pct": 0.0120,
        "trend_len": 200,
        "range_dev_atr": 4.0,         # uzoq muddatli o'rtachadan maks. uzoqlik
        "use_session_filter": False,
        "session_start_hour": 0,
        "session_end_hour": 24,
        "weekend_flat": False,
        "week_close_hour_utc": 19,
        "week_close_dow": 4,
        "week_open_skip_bars": 0,
        # --- kirish ---
        "band_len": 20,               # o'rtacha va standart og'ish oynasi
        "entry_z": 2.0,               # necha sigma chekkada kirish
        "rsi_len": 2,                 # qisqa RSI — Connors uslubi
        "rsi_oversold": 10.0,
        "rsi_overbought": 90.0,
        "require_reversal_bar": True, # tushayotgan pichoqni ushlamaslik
        "setup_lookback": 3,          # setup shuncha bar ichida bo'lsa yetadi
        # --- ijro ---
        "entry_mode": "market",
        "entry_offset_atr": 0.0,
        "entry_limit_bars": 1,
        # --- stop va maqsad ---
        "sl_atr_mult": 1.5,
        "min_sl_atr": 1.0,
        "max_sl_atr": 3.0,
        "target_mode": "mid",         # "mid" = o'rtacha; "r" = qat'iy R ko'paytmasi
        # Mukofot riskdan kamida shuncha barobar katta bo'lmasa — savdo yo'q.
        # 1.2 => zararsizlik uchun 45 % g'alaba yetadi.
        "min_target_r": 1.2,
        "tp2_r": 1.5,                 # target_mode = "r" bo'lganda ishlatiladi
        "tp1_r": 0.0,
        "tp1_fraction": 0.0,
        "tp1_stop_to_r": 0.0,
        "be_trigger_r": 1e9,          # zararsizlikka o'tish yo'q — maqsad yaqin
        "be_offset_r": 0.0,
        "trail_after_r": 1e9,         # TRAILING YO'Q: u qaytishni qaytarib beradi
        "trail_atr_mult": 3.0,
        "trail_min_step_atr": 0.25,
        "time_stop_bars": 12,         # faraz muddati
        "time_stop_min_r": 1e9,       # muddat tugasa SO'ZSIZ yopiladi
        "exit_on_ema_cross": False,
        # --- yo'nalish ---
        "allow_long": True,
        "allow_short": True,
    }

    def generate(self, f: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        close = f["close"]

        # ---------- REJIM: yon harakat ----------
        regime = (
            f["atr_pct"].between(float(p["min_atr_pct"]), float(p["max_atr_pct"]))
            & (f["adx"] < float(p["adx_max"]))
        )
        if p["use_session_filter"]:
            regime &= session_mask(f, int(p["session_start_hour"]),
                                   int(p["session_end_hour"]))
        if p.get("weekend_flat", False):
            regime &= week_guard_mask(
                f.index, int(p["week_close_dow"]), int(p["week_close_hour_utc"]),
                int(p["week_open_skip_bars"]),
            )

        # Uzoq muddatli o'rtachadan haddan tashqari uzoqlashgan bo'lsa, bu
        # "chekka" emas — yangi trendning boshlanishi bo'lishi mumkin.
        trend = close.ewm(span=int(p["trend_len"]), adjust=False,
                          min_periods=int(p["trend_len"])).mean()
        regime &= (close - trend).abs() < float(p["range_dev_atr"]) * f["atr"]

        # ---------- CHEKKALAR ----------
        band_len = int(p["band_len"])
        mid = close.rolling(band_len, min_periods=band_len).mean()
        sd = close.rolling(band_len, min_periods=band_len).std(ddof=0)
        z = (close - mid) / sd.replace(0.0, np.nan)

        rsi = _rsi(close, int(p["rsi_len"]))
        entry_z = float(p["entry_z"])

        oversold = (z <= -entry_z) & (rsi <= float(p["rsi_oversold"]))
        overbought = (z >= entry_z) & (rsi >= float(p["rsi_overbought"]))

        if p["require_reversal_bar"]:
            # SETUP oldingi barlarda, TRIGGER joriy barda.
            #
            # Bularni bitta barda talab qilish mantiqiy xato edi:
            # `RSI(2) <= 10` oxirgi barlar pastga ketganini bildiradi,
            # `close > open` esa o'sha barning yuqoriga yopilishini —
            # ular deyarli bir-birini inkor qiladi. O'lchov: 327 ta
            # signal 2 taga tushib qolgandi.
            lookback = int(p["setup_lookback"])
            setup_low = rolling_any(oversold.fillna(False), lookback).shift(1)
            setup_high = rolling_any(overbought.fillna(False), lookback).shift(1)
            stretched_low = setup_low.fillna(False) & (close > f["open"])
            stretched_high = setup_high.fillna(False) & (close < f["open"])
        else:
            stretched_low, stretched_high = oversold, overbought

        long_sig = regime & stretched_low
        short_sig = regime & stretched_high
        if not p["allow_long"]:
            long_sig &= False
        if not p["allow_short"]:
            short_sig &= False

        signal = pd.Series(0, index=f.index, dtype=np.int8)
        signal[long_sig.fillna(False)] = 1
        signal[short_sig.fillna(False)] = -1
        signal[(long_sig & short_sig).fillna(False)] = 0

        # ---------- STOP VA MAQSAD ----------
        dist = float(p["sl_atr_mult"]) * f["atr"]
        stop_price = pd.Series(np.nan, index=f.index, dtype=float)
        stop_price = stop_price.where(signal != 1, close - dist)
        stop_price = stop_price.where(signal != -1, close + dist)

        out = {
            "signal": signal,
            "stop_price": stop_price,
            "atr": f["atr"],
            "entry_ref": close.where(signal != 0),
        }
        if str(p["target_mode"]) == "mid":
            # Maqsad — o'rtachaning o'zi. Bu DINAMIK daraja: har savdoda
            # boshqa R ko'paytmasiga to'g'ri keladi, chunki chekkadan
            # o'rtachagacha masofa har xil.
            target = mid

            # MUKOFOT/RISK FILTRI — bu blok majburiy.
            #
            # Kirish qaytish barida bo'ladi, ya'ni narx allaqachon
            # o'rtachaga bir qadam yaqinlashgan. O'lchov: kirish paytida
            # o'rtachagacha masofa 1.25 ATR, stop esa 1.50 ATR — savdolarning
            # 61 % ida mukofot riskdan KICHIK bo'lib qolardi (30 % ida
            # yarmidan ham kichik, ya'ni 67 % g'alaba talab qilardi).
            # Bunday savdolarni umuman olmaslik kerak.
            # Mukofot ISHORALI o'lchanadi — modul bilan emas. Qaytish bari
            # o'rtachadan o'tib ketishi mumkin, o'shanda maqsad savdo
            # yo'nalishining ORQASIDA qoladi. Modul bilan o'lchaganda bunday
            # savdo filtrdan o'tib ketardi (136 signaldan 2 tasi).
            reward = (target - close) * signal
            risk = (close - stop_price).abs()
            adequate = (reward > 0) & (reward >= float(p["min_target_r"]) * risk)
            signal = signal.where(adequate.fillna(False), np.int8(0))
            out["signal"] = signal
            out["stop_price"] = stop_price.where(signal != 0)
            out["entry_ref"] = close.where(signal != 0)
            out["target_price"] = target.where(signal != 0)
        return pd.DataFrame(out, index=f.index)

    @classmethod
    def param_space(cls, base: dict[str, Any] | None = None) -> dict[str, list[Any]]:
        p = {**cls.defaults, **(base or {})}
        atr0 = float(p["min_atr_pct"])
        return {
            "min_atr_pct": [round(atr0 * k, 8) for k in (0.6, 0.8, 1.0, 1.3)],
            "adx_max": [20.0, 25.0, 30.0],
            "band_len": [15, 20, 30],
            "entry_z": [1.5, 2.0, 2.5],
            "rsi_len": [2, 3, 5],
            "rsi_oversold": [5.0, 10.0, 15.0],
            "sl_atr_mult": [1.0, 1.5, 2.0, 2.5],
            "time_stop_bars": [8, 12, 20],
            "range_dev_atr": [3.0, 4.0, 6.0],
            "require_reversal_bar": [True, False],
            "setup_lookback": [1, 3, 5],
            "min_target_r": [0.8, 1.0, 1.2, 1.5],
        }


def _rsi(close: pd.Series, length: int) -> pd.Series:
    """Qisqa oynali RSI (Wilder tekislash bilan bir xil)."""
    delta = close.diff()
    gain = delta.clip(lower=0.0).ewm(alpha=1.0 / length, adjust=False,
                                     min_periods=length).mean()
    loss = (-delta).clip(lower=0.0).ewm(alpha=1.0 / length, adjust=False,
                                        min_periods=length).mean()
    rs = gain / loss.replace(0.0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    return out.where(loss != 0.0, 100.0).where(gain.notna(), np.nan)
