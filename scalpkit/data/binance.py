"""Binance'dan tarixiy klines yuklash (ochiq API, kalit talab qilinmaydi).

Spot uchun  : https://api.binance.com/api/v3/klines
Futures uchun: https://fapi.binance.com/fapi/v1/klines

Har bir so'rovda maksimal 1500 bar keladi, shuning uchun sahifalab yuklaymiz.
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

SPOT_URL = "https://api.binance.com/api/v3/klines"
FUTURES_URL = "https://fapi.binance.com/fapi/v1/klines"

_INTERVAL_MS = {
    "1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000,
    "30m": 1_800_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000,
}


def _to_ms(ts: str | pd.Timestamp) -> int:
    t = pd.Timestamp(ts)
    if t.tz is None:
        t = t.tz_localize("UTC")
    return int(t.value // 1_000_000)


def fetch_klines(
    symbol: str = "BTCUSDT",
    interval: str = "5m",
    start: str = "2023-01-01",
    end: str | None = None,
    market: str = "futures",
    limit: int = 1500,
    max_retries: int = 5,
    session: requests.Session | None = None,
    verbose: bool = True,
) -> pd.DataFrame:
    """Berilgan davr uchun to'liq OHLCV tarixini yuklaydi."""
    if interval not in _INTERVAL_MS:
        raise ValueError(f"Qo'llab-quvvatlanmaydigan interval: {interval}")

    url = FUTURES_URL if market == "futures" else SPOT_URL
    step = _INTERVAL_MS[interval]
    start_ms = _to_ms(start)
    end_ms = _to_ms(end) if end else int(time.time() * 1000)

    sess = session or requests.Session()
    rows: list[list] = []
    cursor = start_ms

    while cursor < end_ms:
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "startTime": cursor,
            "endTime": end_ms,
            "limit": limit,
        }
        batch = _get_with_retry(sess, url, params, max_retries)
        if not batch:
            break

        rows.extend(batch)
        last_open = batch[-1][0]
        cursor = last_open + step

        if verbose:
            got = pd.to_datetime(last_open, unit="ms", utc=True)
            print(f"  {len(rows):>8,} bar yuklandi — {got:%Y-%m-%d %H:%M} UTC", end="\r")

        if len(batch) < limit:
            break
        time.sleep(0.12)  # rate-limit hurmati

    if verbose:
        print()
    if not rows:
        raise RuntimeError("Binance hech qanday ma'lumot qaytarmadi.")

    df = pd.DataFrame(
        rows,
        columns=[
            "open_time", "open", "high", "low", "close", "volume", "close_time",
            "quote_volume", "trades", "taker_base", "taker_quote", "ignore",
        ],
    )
    df["time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.set_index("time")[["open", "high", "low", "close", "volume"]].astype(float)
    df = df[~df.index.duplicated(keep="last")].sort_index()

    # Oxirgi bar hali yopilmagan bo'lishi mumkin — uni tashlaymiz
    now_ms = int(time.time() * 1000)
    if not df.empty and _to_ms(df.index[-1]) + step > now_ms:
        df = df.iloc[:-1]
    return df


def _get_with_retry(session: requests.Session, url: str, params: dict, max_retries: int):
    delay = 1.0
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = session.get(url, params=params, timeout=30)
            if resp.status_code == 429 or resp.status_code == 418:
                wait = float(resp.headers.get("Retry-After", delay * 4))
                print(f"\n  Rate limit — {wait:.0f}s kutilmoqda...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001 — tarmoq xatolarini qayta urinamiz
            last_error = exc
            if attempt == max_retries - 1:
                break
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(
        f"Binance so'rovi {max_retries} urinishdan keyin ham bajarilmadi: {last_error}"
    )


def download_to_csv(
    path: str | Path,
    symbol: str = "BTCUSDT",
    interval: str = "5m",
    start: str = "2023-01-01",
    end: str | None = None,
    market: str = "futures",
) -> pd.DataFrame:
    df = fetch_klines(symbol, interval, start, end, market)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index_label="time")
    print(f"  Saqlandi: {path}  ({len(df):,} bar, {df.index[0]:%Y-%m-%d} → {df.index[-1]:%Y-%m-%d})")
    return df
