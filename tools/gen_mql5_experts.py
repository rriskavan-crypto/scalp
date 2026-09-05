#!/usr/bin/env python3
"""MQL5 Expert Advisor fayllarini Python profillaridan generatsiya qiladi.

Nima uchun generatsiya, qo'lda yozish emas?

Ikkita mustaqil amalga oshirish (Python tadqiqot uchun, MQL5 savdo uchun)
vaqt o'tib ajralib ketadi — kimdir bitta joyda parametrni o'zgartiradi va
backtest natijasi real savdoni tasvirlamay qo'yadi. Bu skript EA'ning
standart qiymatlarini `scalpkit.profiles` dan **olib chiqadi**, shuning
uchun ular ta'rifi bo'yicha mos keladi.

Ishlatish:
    python tools/gen_mql5_experts.py          # fayllarni yozadi
    python tools/gen_mql5_experts.py --check  # faqat tekshiradi (CI uchun)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scalpkit.config import Config                     # noqa: E402
from scalpkit.features import DEFAULT_FEATURE_PARAMS   # noqa: E402
from scalpkit.profiles import BTCUSD, XAUUSD, Profile  # noqa: E402
from scalpkit.strategies import get_strategy           # noqa: E402

CORE = ROOT / "mql5" / "Include" / "ScalpKit" / "Core.mqh"
EXPERTS = ROOT / "mql5" / "Experts"

# EA input nomi -> (turi, qayerdan olinadi, izoh)
#   "s:" strategiya parametri, "r:" risk, "f:" feature, "c:" doimiy
SPEC: list[tuple[str, str, str, str]] = [
    ("=== Rejim filtrlari ===", "", "", ""),
    ("InpMinAtrPct",        "double", "s:min_atr_pct",        "ATR% minimal"),
    ("InpMaxAtrPct",        "double", "s:max_atr_pct",        "ATR% maksimal"),
    ("InpAdxMin",           "double", "s:adx_min",            "ADX minimal"),
    ("InpRequireHTF",       "bool",   "s:require_htf",        "H1 yo'nalishi mos bo'lsin"),
    ("InpUseSession",       "bool",   "s:use_session_filter", "Seans filtri"),
    ("InpSessionStartUTC",  "int",    "s:session_start_hour", "Seans boshi (UTC soat)"),
    ("InpSessionEndUTC",    "int",    "s:session_end_hour",   "Seans oxiri (UTC soat)"),

    ("=== Setup ===", "", "", ""),
    ("InpImpulseLookback",  "int",    "s:impulse_lookback",   "Impuls oynasi (bar)"),
    ("InpImpulseBodyAtr",   "double", "s:impulse_body_atr",   "Impuls tanasi (ATR)"),
    ("InpImpulseVolZ",      "double", "s:impulse_vol_z",      "Impuls hajmi (z-score)"),
    ("InpPullbackLookback", "int",    "s:pullback_lookback",  "Qaytish oynasi (bar)"),
    ("InpTouchAtr",         "double", "s:touch_atr",          "EMA21 zonasi (ATR)"),
    ("InpRsiPullbackLong",  "double", "s:rsi_pullback_long",  "RSI long uchun"),
    ("InpRsiPullbackShort", "double", "s:rsi_pullback_short", "RSI short uchun"),

    ("=== Trigger ===", "", "", ""),
    ("InpTriggerVolZ",      "double", "s:trigger_vol_z",      "Trigger hajmi (z-score)"),
    ("InpTriggerClosePos",  "double", "s:trigger_close_pos",  "Bar ichida yopilish o'rni"),
    ("InpMaxExtensionAtr",  "double", "s:max_extension_atr",  "EMA21 dan maks. uzoqlik (ATR)"),

    ("=== Kirish ===", "", "", ""),
    ("InpUseLimitEntry",    "bool",   "s:entry_mode==limit",  "Limit order (false = market)"),
    ("InpEntryOffsetAtr",   "double", "s:entry_offset_atr",   "Limit siljishi (ATR)"),
    ("InpEntryLimitBars",   "int",    "s:entry_limit_bars",   "Limit muddati (bar)"),

    ("=== Stop ===", "", "", ""),
    ("InpSwingLen",         "int",    "f:swing_len",          "Swing oynasi (bar)"),
    ("InpSlBufferAtr",      "double", "s:sl_buffer_atr",      "Swing dan zaxira (ATR)"),
    ("InpMinSlAtr",         "double", "s:min_sl_atr",         "Stop minimal (ATR)"),
    ("InpMaxSlAtr",         "double", "s:max_sl_atr",         "Stop maksimal (ATR)"),
    ("InpMinStopPct",       "double", "r:min_stop_pct",       "Stop minimal (narx %)"),
    ("InpMaxStopPct",       "double", "r:max_stop_pct",       "Stop maksimal (narx %)"),

    ("=== Chiqish (yutuqlar cheklanmaydi) ===", "", "", ""),
    ("InpTp1R",             "double", "s:tp1_r",              "TP1 (R)"),
    ("InpTp1Fraction",      "double", "s:tp1_fraction",       "TP1 da yopiladigan ulush"),
    ("InpTp2R",             "double", "s:tp2_r",              "TP2 (R)"),
    ("InpTp1StopToR",       "double", "s:tp1_stop_to_r",      "TP1 dan keyin stop (R)"),
    ("InpBeTriggerR",       "double", "s:be_trigger_r",       "Zararsizlikka o'tish (R)"),
    ("InpBeOffsetR",        "double", "s:be_offset_r",        "Zararsizlik zaxirasi (R)"),
    ("InpTrailAfterR",      "double", "s:trail_after_r",      "Trailing boshlanishi (R)"),
    ("InpTrailAtrMult",     "double", "s:trail_atr_mult",     "Trailing masofasi (ATR)"),
    ("InpTrailMinStepAtr",  "double", "s:trail_min_step_atr", "Trailing minimal qadami (ATR)"),
    ("InpTimeStopBars",     "int",    "s:time_stop_bars",     "Vaqt stopi (bar)"),
    ("InpTimeStopMinR",     "double", "s:time_stop_min_r",    "Vaqt stopi shu R gacha"),
    ("InpExitOnEmaCross",   "bool",   "s:exit_on_ema_cross",  "TP1 dan keyin EMA21 chiqishi"),

    ("=== Risk ===", "", "", ""),
    ("InpRiskPerTrade",     "double", "r:risk_per_trade",     "Savdo boshiga risk"),
    ("InpMaxLeverage",      "double", "r:max_leverage",       "Maksimal leverage"),
    ("InpMaxTradesPerDay",  "int",    "r:max_trades_per_day", "Kunlik savdolar chegarasi"),
    ("InpDailyLossLimit",   "double", "r:daily_loss_limit",   "Kunlik zarar chegarasi"),
    ("InpMaxConsecLosses",  "int",    "r:max_consecutive_losses", "Ketma-ket zararlar"),
    ("InpCooldownBars",     "int",    "r:cooldown_bars_after_loss", "Zarardan keyin tanaffus"),
    ("InpStreakCooldown",   "int",    "r:cooldown_bars_after_streak", "Seriyadan keyin tanaffus"),
    ("InpHalveRiskDD",      "double", "r:halve_risk_drawdown", "Shu drawdownda risk yarmiga"),

    ("=== Hafta chegarasi ===", "", "", ""),
    ("InpWeekendFlat",      "bool",   "s:weekend_flat",        "Hafta oxiriga pozitsiyasiz kirish"),
    ("InpWeekCloseHourUTC", "int",    "s:week_close_hour_utc", "Juma shu soatdan keyin savdo yo'q"),
    ("InpWeekCloseDow",     "int",    "s:week_close_dow",      "0=dushanba ... 4=juma"),
    ("InpWeekOpenSkipBars", "int",    "s:week_open_skip_bars", "Hafta ochilishida kutiladigan barlar"),

    ("=== Xarajat himoyasi ===", "", "", ""),
    ("InpMaxCostR",         "double", "c:0.40",               "Xarajat shundan oshsa savdo yo'q"),

    ("=== Texnik ===", "", "", ""),
    ("InpEmaFast",          "int",    "f:ema_fast",           ""),
    ("InpEmaMid",           "int",    "f:ema_mid",            ""),
    ("InpEmaSlow",          "int",    "f:ema_slow",           ""),
    ("InpAtrLen",           "int",    "f:atr_len",            ""),
    ("InpRsiLen",           "int",    "f:rsi_len",            ""),
    ("InpAdxLen",           "int",    "f:adx_len",            ""),
    ("InpDonchianLen",      "int",    "f:donchian_len",       ""),
    ("InpVolZLen",          "int",    "f:vol_z_len",          ""),
    ("InpHtfEma",           "int",    "f:htf_ema",            ""),
    ("InpMagic",            "long",   "c:MAGIC",              "Magic raqam"),
    ("InpDeviation",        "int",    "c:30",                 "Maks. sirpanish (punkt)"),
    ("InpServerUtcOffset",  "int",    "c:-99",                "Server-UTC farqi, -99 = avto"),
    ("InpVerbose",          "bool",   "c:true",               "Batafsil log"),
]

MAGIC = {"btcusd": 20260905, "xauusd": 20260906}


def _fmt(value, kind: str) -> str:
    if kind == "bool":
        return "true" if value else "false"
    if kind == "int":
        return str(int(round(float(value))))
    if kind == "long":
        return str(int(value))
    text = f"{float(value):.6f}".rstrip("0")
    return text + "0" if text.endswith(".") else text


def resolve(source: str, profile: Profile, params: dict, risk) -> object:
    kind, _, key = source.partition(":")
    if kind == "s":
        if key.endswith("==limit"):
            return params["entry_mode"] == "limit"
        return params[key]
    if kind == "r":
        return getattr(risk, key)
    if kind == "f":
        return DEFAULT_FEATURE_PARAMS[key]
    if kind == "c":
        return MAGIC[profile.name] if key == "MAGIC" else key
    raise ValueError(f"noma'lum manba: {source}")


def render(profile: Profile, title: str, note: str) -> str:
    cfg = profile.apply(Config())
    params = get_strategy(cfg.strategy.name, cfg.strategy.params).params

    body, assigns = [], []
    for name, ctype, source, comment in SPEC:
        if not ctype:                                  # guruh sarlavhasi
            body.append(f'\ninput group "{name}"')
            continue
        raw = resolve(source, profile, params, cfg.risk)
        value = raw if source.startswith("c:") and not str(raw).lstrip("-").isdigit() \
            else _fmt(raw, ctype)
        pad = " " * max(1, 24 - len(name))
        line = f"input {ctype:<7} {name}{pad}= {value};"
        body.append(f"{line}{'':<{max(1, 46 - len(line))}}// {comment}" if comment else line)
        assigns.append(f"   g_cfg.{name[3:]:<20} = {name};")

    spread_note = (
        f"tipik spread {profile.typical_spread:g} @ narx {profile.typical_price:,.0f} "
        f"-> xarajat ~{profile.typical_spread / (float(params['min_sl_atr']) * 1.4 * float(params['min_atr_pct']) * profile.typical_price):.2f} R"
    )
    return f'''//+------------------------------------------------------------------+
//|   {title}
//|
//|   {profile.description}
//|   Savdo vaqti : {profile.calendar.describe()}
//|   {spread_note}
//|
//|   {note}
//|
//|   BU FAYL AVTOMATIK GENERATSIYA QILINGAN.
//|   Qo'lda tahrirlamang — `python tools/gen_mql5_experts.py` ishlating.
//|   Standart qiymatlar `scalpkit/profiles.py` dan olinadi, shuning
//|   uchun Python va MQL5 versiyalari hech qachon ajralib ketmaydi.
//+------------------------------------------------------------------+
#property copyright "scalpkit"
#property link      "https://github.com/rriskavan-crypto/scalp"
#property version   "1.10"
#property description "{title}"

#include <ScalpKit/Core.mqh>
{chr(10).join(body)}

//+------------------------------------------------------------------+
//| Parametrlarni yadroga uzatish                                    |
//+------------------------------------------------------------------+
void LoadConfig()
{{
{chr(10).join(assigns)}
}}

int  OnInit()                    {{ LoadConfig(); return ScalpKit_OnInit(); }}
void OnDeinit(const int reason)  {{ ScalpKit_OnDeinit(reason); }}
void OnTick()                    {{ ScalpKit_OnTick(); }}
double OnTester()                {{ return ScalpKit_OnTester(); }}
void OnTesterDeinit()            {{ ScalpKit_OnTesterDeinit(); }}
//+------------------------------------------------------------------+
'''


TARGETS = [
    (BTCUSD, "ScalpKit_BTC_M5.mq5", "ScalpKit BTC/USD M5 — tanlab-skalping",
     "MarketWatch'dagi nom BTCUSDm bo'lishi mumkin — grafikni o'sha nomda oching."),
    (XAUUSD, "ScalpKit_XAU_M5.mq5", "ScalpKit XAU/USD (oltin) M5 — tanlab-skalping",
     "Oltin dam olish kunlari yopiq: EA juma kechqurun pozitsiyani yopadi."),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="Fayllarni yozmasdan, mosligini tekshiradi")
    args = ap.parse_args()

    EXPERTS.mkdir(parents=True, exist_ok=True)
    stale = []
    for profile, filename, title, note in TARGETS:
        text = render(profile, title, note)
        path = EXPERTS / filename
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(filename)
        else:
            path.write_text(text, encoding="utf-8")
            n_inputs = len(re.findall(r"^input\s+\w+\s+\w+", text, re.M))
            print(f"  {filename:<24} {len(text.splitlines()):>4} qator, {n_inputs} input")

    if args.check and stale:
        print("ESKIRGAN fayllar:", ", ".join(stale))
        print("Yechim: python tools/gen_mql5_experts.py")
        return 1
    if args.check:
        print("EA fayllari profillarga mos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
