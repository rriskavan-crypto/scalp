"""Realistik sintetik BTC M5 ma'lumot generatori.

Nima uchun kerak? Internetsiz muhitda yoki testlarda butun quvurni (indikator →
signal → backtest → hisobot) tekshirish uchun. Bu **real bozor emas** —
undan olingan foyda ko'rsatkichlarini haqiqiy natija sifatida qabul qilmang.

Model quyidagilarni takrorlaydi:
  * rejim almashinuvi (yon harakat ↔ trend) — Markov zanjiri;
  * volatilitet klasterlanishi — GARCH(1,1) ko'rinishidagi jarayon;
  * kun ichidagi mavsumiylik — London/Nyu-York seansida faollik yuqori;
  * bar ichidagi high/low — Brownian ko'prigi ekstremumlarining aniq taqsimoti;
  * hajmning |narx o'zgarishi| bilan bog'liqligi.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Kun ichidagi volatilitet koeffitsienti (UTC soatlari bo'yicha).
# Osiyo tunida past, London ochilishida (07:00) ko'tariladi,
# NY bilan kesishuvda (13:00–17:00) eng yuqori.
_HOURLY_VOL = np.array([
    0.72, 0.65, 0.62, 0.63, 0.68, 0.75, 0.88, 1.05,  # 00–07
    1.12, 1.10, 1.05, 1.02, 1.08, 1.35, 1.42, 1.30,  # 08–15
    1.22, 1.15, 1.05, 0.98, 0.92, 0.88, 0.82, 0.76,  # 16–23
])


def generate_synthetic(
    n_bars: int = 60_000,
    start: str = "2024-01-01",
    start_price: float = 42_000.0,
    annual_vol: float = 0.55,
    seed: int | None = 42,
    trend_prob: float = 0.06,      # yon harakatdan trendga o'tish ehtimoli
    chop_prob: float = 0.14,       # trenddan yon harakatga qaytish ehtimoli
    trend_drift_ann: float = 1.60, # trend rejimidagi yillik drift kuchi
    garch_alpha: float = 0.09,
    garch_beta: float = 0.88,
) -> pd.DataFrame:
    """5 daqiqalik OHLCV ma'lumot yaratadi."""
    rng = np.random.default_rng(seed)
    bars_per_year = 365 * 24 * 12
    base_sigma = annual_vol / np.sqrt(bars_per_year)
    drift_step = trend_drift_ann / bars_per_year

    index = pd.date_range(start=start, periods=n_bars, freq="5min", tz="UTC")
    hour_mult = _HOURLY_VOL[index.hour.to_numpy()]

    # --- rejim: 0 = yon harakat, 1 = trend (yo'nalish bilan) ---
    state = np.zeros(n_bars, dtype=np.int8)
    direction = np.zeros(n_bars, dtype=np.int8)
    cur_state, cur_dir = 0, 1
    switch = rng.random(n_bars)
    for i in range(n_bars):
        if cur_state == 0 and switch[i] < trend_prob:
            cur_state, cur_dir = 1, (1 if rng.random() < 0.5 else -1)
        elif cur_state == 1 and switch[i] < chop_prob:
            cur_state = 0
        state[i], direction[i] = cur_state, cur_dir

    # --- GARCH(1,1) volatilitet ---
    omega = base_sigma**2 * (1.0 - garch_alpha - garch_beta)
    var = np.empty(n_bars)
    var[0] = base_sigma**2
    # og'ir dumli innovatsiyalar (t-taqsimot, birlik dispersiyaga keltirilgan)
    t_df = 5.0
    shocks = rng.standard_t(df=t_df, size=n_bars) / np.sqrt(t_df / (t_df - 2.0))

    log_ret = np.empty(n_bars)
    prev_ret = 0.0
    for i in range(n_bars):
        if i > 0:
            var[i] = omega + garch_alpha * prev_ret**2 + garch_beta * var[i - 1]
        sigma = np.sqrt(var[i])
        # trendda drift bor; yon harakatda o'rtachaga qaytish (mean reversion)
        mu = drift_step * direction[i] if state[i] == 1 else -0.05 * prev_ret
        # GARCH qaytarishi mavsumiylikdan xoli innovatsiyaga tayanadi,
        # aks holda kun ichidagi koeffitsient ikki marta hisoblanib ketadi
        prev_ret = sigma * shocks[i]
        log_ret[i] = mu + prev_ret * hour_mult[i]

    close = start_price * np.exp(np.cumsum(log_ret))
    open_ = np.concatenate([[start_price], close[:-1]])

    # --- bar ichidagi high/low: Brownian ko'prigi ekstremumlari ---
    # P(max > m) = exp(-2m(m-r)/s^2)  =>  m = (r + sqrt(r^2 + 2 s^2 E)) / 2
    bar_sigma = np.sqrt(var) * hour_mult
    r = np.log(close / open_)
    e_hi = rng.exponential(1.0, n_bars)
    e_lo = rng.exponential(1.0, n_bars)
    hi_log = (r + np.sqrt(r**2 + 2.0 * bar_sigma**2 * e_hi)) / 2.0
    lo_log = (r - np.sqrt(r**2 + 2.0 * bar_sigma**2 * e_lo)) / 2.0

    high = open_ * np.exp(np.maximum(hi_log, np.maximum(r, 0.0)))
    low = open_ * np.exp(np.minimum(lo_log, np.minimum(r, 0.0)))

    # --- hajm ---
    abs_z = np.abs(log_ret) / bar_sigma
    volume = (
        260.0
        * hour_mult
        * np.exp(0.55 * np.clip(abs_z, 0, 6))
        * rng.lognormal(0.0, 0.35, n_bars)
    )

    df = pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=index,
    )
    df.index.name = "time"
    return df.round(
        {"open": 2, "high": 2, "low": 2, "close": 2, "volume": 3}
    )
