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
from scalpkit.profiles import (BTCUSD, XAUUSD, Profile,  # noqa: E402
                              expected_hold_days, for_timeframe)
from scalpkit.strategies import get_strategy           # noqa: E402

CORE = ROOT / "mql5" / "Include" / "ScalpKit" / "Core.mqh"
EXPERTS = ROOT / "mql5" / "Experts"
PRESETS = ROOT / "mql5" / "Presets"

# EA input nomi -> (turi, qayerdan olinadi, izoh)
#   "s:" strategiya parametri, "r:" risk, "f:" feature, "c:" doimiy
SPEC: list[tuple[str, str, str, str]] = [
    ("=== Strategiya ===", "", "", ""),
    ("InpStrategyKind",     "int",    "k:kind",               "0 = pullback, 1 = donchian"),
    ("InpExpectedTimeframe", "ENUM_TIMEFRAMES", "k:tf",        "Preset qaysi TF uchun"),

    ("=== Rejim filtrlari ===", "", "", ""),
    ("InpMinAtrPct",        "double", "s:min_atr_pct",        "ATR% minimal"),
    ("InpMaxAtrPct",        "double", "s:max_atr_pct",        "ATR% maksimal"),
    ("InpAdxMin",           "double", "s:adx_min",            "ADX minimal"),
    ("InpRequireHTF",       "bool",   "s:require_htf",        "H1 yo'nalishi mos bo'lsin"),
    ("InpUseSession",       "bool",   "s:use_session_filter", "Seans filtri"),
    ("InpSessionStartUTC",  "int",    "s:session_start_hour", "Seans boshi (UTC soat)"),
    ("InpSessionEndUTC",    "int",    "s:session_end_hour",   "Seans oxiri (UTC soat)"),

    ("=== Yo'nalish ===", "", "", ""),
    ("InpAllowLong",        "bool",   "s:allow_long",         "Long savdolarga ruxsat"),
    ("InpAllowShort",       "bool",   "s:allow_short",        "Short savdolarga ruxsat"),

    ("=== Donchian (trendni kuzatish) ===", "", "", ""),
    ("InpTrendLen",         "int",    "s:trend_len",          "Uzoq muddatli EMA"),
    ("InpRequireTrendFilter", "bool", "s:require_trend_filter", "Narx EMA ning to'g'ri tomonida"),
    ("InpEntryLen",         "int",    "s:entry_len",          "Kirish kanali (bar)"),
    ("InpExitLen",          "int",    "s:exit_len",           "Chiqish kanali (bar)"),
    ("InpCooldownLen",      "int",    "s:cooldown_len",       "Buzilishlar orasidagi masofa"),
    ("InpSlAtrMult",        "double", "s:sl_atr_mult",        "Stop masofasi (ATR)"),

    ("=== Range Reversion (o'rtachaga qaytish) ===", "", "", ""),
    ("InpAdxMax",           "double", "s:adx_max",            "Bundan yuqorisi trend"),
    ("InpBandLen",          "int",    "s:band_len",           "O'rtacha va sigma oynasi"),
    ("InpEntryZ",           "double", "s:entry_z",            "Necha sigma chekkada"),
    ("InpRevRsiLen",        "int",    "s:rsi_len",            "Qisqa RSI uzunligi"),
    ("InpRsiOversold",      "double", "s:rsi_oversold",       "O'ta sotilgan chegara"),
    ("InpRsiOverbought",    "double", "s:rsi_overbought",     "O'ta sotib olingan chegara"),
    ("InpRequireReversalBar", "bool", "s:require_reversal_bar", "Qaytish bari tasdig'i"),
    ("InpSetupLookback",    "int",    "s:setup_lookback",     "Setup oynasi (bar)"),
    ("InpRangeDevAtr",      "double", "s:range_dev_atr",      "EMA dan maks. uzoqlik (ATR)"),
    ("InpMinTargetR",       "double", "s:min_target_r",       "Mukofot/risk minimal nisbati"),

    ("=== Setup (pullback) ===", "", "", ""),
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
    ("InpApplySwapCost",    "bool",   "k:applyswap",          "Xarajatga swapni qo'shish"),
    ("InpExpectedHoldDays", "double", "k:hold",               "Kutilgan ushlash (kun)"),

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

MAGIC = {
    ("btcusd", "momentum_pullback"): 20260905,
    ("xauusd", "momentum_pullback"): 20260906,
    ("btcusd", "donchian_breakout"): 20260907,
    ("xauusd", "donchian_breakout"): 20260908,
    ("btcusd", "range_reversion"):   20260909,
    ("xauusd", "range_reversion"):   20260910,
}

MQL_TIMEFRAME = {"5m": "PERIOD_M5", "15m": "PERIOD_M15", "1h": "PERIOD_H1",
                 "4h": "PERIOD_H4", "1d": "PERIOD_D1"}
STRATEGY_KIND = {"momentum_pullback": 0, "donchian_breakout": 1,
                 "range_reversion": 2}


def _fmt(value, kind: str) -> str:
    if kind == "bool":
        return "true" if value else "false"
    if kind == "int":
        return str(int(round(float(value))))
    if kind == "long":
        return str(int(value))
    # 6 xona yetarli emas: oltin M15 uchun min_atr_pct = 0.0007785 bo'lib,
    # u 0.000779 ga yaxlitlanardi va EA Python bilan ajralib ketardi.
    # `repr` eng qisqa aylanma-aniq shaklni beradi.
    v = float(value)
    text = repr(v)
    if "e" in text or "E" in text:          # MQL5 uchun o'nlik shaklda yozamiz
        text = f"{v:.15f}".rstrip("0")
        if text.endswith("."):
            text += "0"
    return text


def resolve(source: str, profile: Profile, params: dict, risk,
            strategy_name: str) -> object:
    kind, _, key = source.partition(":")
    if kind == "s":
        if key.endswith("==limit"):
            return params["entry_mode"] == "limit"
        return params[key]
    if kind == "r":
        return getattr(risk, key)
    if kind == "f":
        return DEFAULT_FEATURE_PARAMS[key]
    if kind == "k":
        if key == "kind":
            return STRATEGY_KIND[strategy_name]
        if key == "tf":
            return MQL_TIMEFRAME[profile.timeframe]
        if key == "hold":
            return expected_hold_days(profile.timeframe, strategy_name, params)
        if key == "applyswap":
            # Kripto perpetual emas, MT5 CFD — har ikkalasida ham swap bor.
            # M5/M15 da u nolga yaqin, lekin filtr baribir to'g'ri ishlaydi.
            return True
    if kind == "c":
        base = profile.name.split("_")[0]
        return MAGIC[(base, strategy_name)] if key == "MAGIC" else key
    raise ValueError(f"noma'lum manba: {source}")


def merged_params(profile: Profile, strategy_name: str) -> dict:
    """Har ikkala strategiyaning parametrlarini birlashtiradi.

    MQL5 strukturasi barcha maydonlarni talab qiladi, shuning uchun
    tanlanmagan strategiyaning maydonlari ham to'ldirilishi kerak —
    ular o'sha strategiyaning standart qiymatlaridan olinadi.
    """
    merged: dict = {}
    for other in ("momentum_pullback", "donchian_breakout", "range_reversion"):
        merged.update(get_strategy(other).params)
    cfg = profile.apply(Config(), strategy_name)
    merged.update(get_strategy(strategy_name, cfg.strategy.params).params)
    return merged


def render(profile: Profile, strategy_name: str, title: str, note: str) -> str:
    cfg = profile.apply(Config(), strategy_name)
    params = merged_params(profile, strategy_name)

    body, assigns = [], []
    for name, ctype, source, comment in SPEC:
        if not ctype:                                  # guruh sarlavhasi
            body.append(f'\ninput group "{name}"')
            continue
        raw = resolve(source, profile, params, cfg.risk, strategy_name)
        if ctype == "ENUM_TIMEFRAMES" or (
                source.startswith("c:") and not str(raw).lstrip("-").isdigit()):
            value = str(raw)
        else:
            value = _fmt(raw, ctype)
        pad = " " * max(1, 24 - len(name))
        line = f"input {ctype:<7} {name}{pad}= {value};"
        body.append(f"{line}{'':<{max(1, 46 - len(line))}}// {comment}" if comment else line)
        assigns.append(f"   g_cfg.{name[3:]:<20} = {name};")

    stop_est = 1.5 * float(params["min_atr_pct"]) * profile.typical_price
    spread_note = (
        f"tipik spread {profile.typical_spread:g} @ narx {profile.typical_price:,.0f} "
        f"-> xarajat ~{profile.typical_spread / stop_est:.3f} R"
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


# (bazaviy profil, timeframe, strategiya, fayl nomi, sarlavha, izoh)
def render_preset(profile: Profile, strategy_name: str) -> str:
    """MT5 `.set` fayli — Strategy Tester va grafikdan yuklash uchun."""
    cfg = profile.apply(Config(), strategy_name)
    params = merged_params(profile, strategy_name)
    lines = [f"; ScalpKit preset — {profile.name} / {strategy_name}",
             f"; timeframe: {profile.timeframe}"]
    for name, ctype, source, _ in SPEC:
        if not ctype:
            continue
        raw = resolve(source, profile, params, cfg.risk, strategy_name)
        if ctype == "ENUM_TIMEFRAMES" or (
                source.startswith("c:") and not str(raw).lstrip("-").isdigit()):
            continue          # enum va matn qiymatlari presetga kiritilmaydi
        lines.append(f"{name}={_fmt(raw, ctype)}")
    return "\n".join(lines) + "\n"


TARGETS = [
    (BTCUSD, "5m", "momentum_pullback", "ScalpKit_BTC_Scalp.mq5",
     "ScalpKit BTC/USD — tanlab-skalping (M5/M15)",
     "MarketWatch'dagi nom BTCUSDm bo'lishi mumkin."),
    (XAUUSD, "5m", "momentum_pullback", "ScalpKit_XAU_Scalp.mq5",
     "ScalpKit XAU/USD (oltin) — tanlab-skalping (M5/M15)",
     "Oltin dam olish kunlari yopiq: EA juma kechqurun pozitsiyani yopadi."),
    (BTCUSD, "4h", "donchian_breakout", "ScalpKit_BTC_Trend.mq5",
     "ScalpKit BTC/USD — swing / trendni kuzatish (M15-D1)",
     "MAQSAD QO'YILMAYDI: trend-following foydasi kam sonli katta yutuqlardan keladi."),
    (XAUUSD, "4h", "donchian_breakout", "ScalpKit_XAU_Trend.mq5",
     "ScalpKit XAU/USD (oltin) — swing / trendni kuzatish (M15-D1)",
     "MAQSAD QO'YILMAYDI: trend-following foydasi kam sonli katta yutuqlardan keladi."),
    (BTCUSD, "4h", "range_reversion", "ScalpKit_BTC_Range.mq5",
     "ScalpKit BTC/USD — o'rtachaga qaytish (H1-H4)",
     "Trend strategiyasining aksi: ADX PAST rejimda ishlaydi, maqsad MAJBURIY."),
    (XAUUSD, "4h", "range_reversion", "ScalpKit_XAU_Range.mq5",
     "ScalpKit XAU/USD (oltin) — o'rtachaga qaytish (H1-H4)",
     "Trend strategiyasining aksi: ADX PAST rejimda ishlaydi, maqsad MAJBURIY."),
]

# Har bir EA uchun tayyor timeframe presetlari
PRESET_TIMEFRAMES = {
    "momentum_pullback": ("5m", "15m"),
    "donchian_breakout": ("15m", "1h", "4h", "1d"),
    # M15 da xarajat qaytish ustunligidan katta chiqdi — preset berilmaydi
    "range_reversion": ("1h", "4h"),
}


# ==================================================================
#  SWING EA — grafik timeframe'idan o'zini sozlaydigan variant
# ==================================================================
#  Nima uchun alohida: oddiy EA + `.set` juftligida foydalanuvchi
#  noto'g'ri presetni noto'g'ri grafikka yuklashi mumkin, va bu jimgina
#  noto'g'ri kalibrlash beradi (M5 uchun `min_atr_pct = 0.20 %` D1 da
#  hamma barni o'tkazib yuboradi). Bu yerda EA `Period()` ni o'qiydi va
#  o'sha timeframe uchun kalibrlangan blokni O'ZI tanlaydi — noto'g'ri
#  juftlik tuzish IMKONSIZ bo'ladi. Preset yuklash umuman kerak emas.

SWING_TFS = ("15m", "1h", "4h", "1d")
SWING_TF_INDEX = {"15m": 1, "1h": 2, "4h": 3, "1d": 4}

# (strategiya, ruxsat etilgan timeframe'lar) — o'lchangan savdo chastotasi
# bo'yicha. Chegara: 3 yillik tarixda kamida ~100 savdo.
#   donchian  : 15m 1629 | 1h 485 | 4h 142 | 1d 11   (1d — chegaradan past,
#               lekin trend-following uchun asosiy timeframe, ogohlantirish
#               bilan qoldiriladi)
#   reversion : 15m 304 | 1h 105 | 4h 33 | 1d 3      (4h/1d — juda kam)
SWING_STRATEGIES = {
    1: ("donchian_breakout", SWING_TFS),
    2: ("range_reversion", ("15m", "1h")),
}

# Foydalanuvchi o'zgartirishi mumkin bo'lgan inputlar — kalibrlangan
# blokdan KEYIN qo'llanadi, shuning uchun ular ustun turadi.
SWING_USER_INPUTS = [
    ("InpRiskPerTrade",     "double", "Savdo boshiga risk (0.005 = 0.5 %)"),
    ("InpDailyLossLimit",   "double", "Kunlik zarar chegarasi"),
    ("InpMaxLeverage",      "double", "Maksimal leverage"),
    ("InpMaxCostR",         "double", "Xarajat shundan oshsa savdo yo'q"),
    ("InpApplySwapCost",    "bool",   "Xarajatga swapni (kechalik) qo'shish"),
    ("InpAllowLong",        "bool",   "Long savdolarga ruxsat"),
    ("InpAllowShort",       "bool",   "Short savdolarga ruxsat"),
]

# `weekend_flat` — YAGONA timeframe'ga bog'liq bo'lgan qiymat: oltinda
# M15/H1 da yoqilgan, H4/D1 da o'chirilgan (swing hafta oxiri gapini
# qabul qiladi, uning o'rniga stop kengroq). Oddiy bool input uni jimgina
# bosib ketardi — masalan oltin M15 da hafta oxiri himoyasini yo'q qilardi.
# Shuning uchun u UCH HOLATLI: -1 = profil qaror qiladi.
SWING_TRISTATE = ("InpWeekendFlat",)

SWING_SKIP = {name for name, _, _ in SWING_USER_INPUTS} | set(SWING_TRISTATE) | {
    "InpMagic", "InpDeviation", "InpServerUtcOffset", "InpVerbose",
    "InpExpectedTimeframe", "InpStrategyKind",
}


def swing_block(base: Profile, tf: str, kind: int) -> str:
    """Bitta (timeframe x strategiya) uchun kalibrlangan qiymatlar bloki."""
    strategy_name = SWING_STRATEGIES[kind][0]
    profile = for_timeframe(base, tf)
    cfg = profile.apply(Config(), strategy_name)
    params = merged_params(profile, strategy_name)

    lines = []
    for name, ctype, source, _ in SPEC:
        if not ctype or (name in SWING_SKIP and name not in SWING_TRISTATE):
            continue
        raw = resolve(source, profile, params, cfg.risk, strategy_name)
        value = str(raw) if source.startswith("c:") and not str(raw).lstrip("-").isdigit() \
            else _fmt(raw, ctype)
        lines.append(f"   g_cfg.{name[3:]:<20} = {value};")

    stop_pct = float(cfg.risk.min_stop_pct) * 100.0
    hold = expected_hold_days(tf, strategy_name, params)
    return (f"//--- {tf.upper()} / {strategy_name}: stop >= {stop_pct:.3f} %, "
            f"ushlash ~{hold:.2f} kun\n"
            f"void Apply_{tf.upper()}_{kind}()\n{{\n" + "\n".join(lines) + "\n}\n")


def render_swing(base: Profile, filename: str, title: str,
                 magic_base: int) -> str:
    blocks, dispatch = [], []
    for kind, (strategy_name, tfs) in sorted(SWING_STRATEGIES.items()):
        for tf in SWING_TFS:
            if tf not in tfs:
                continue
            blocks.append(swing_block(base, tf, kind))
            dispatch.append(
                f"   if(kind == {kind} && tf == {MQL_TIMEFRAME[tf]}) "
                f"{{ Apply_{tf.upper()}_{kind}(); return {SWING_TF_INDEX[tf]}; }}")

    user_inputs, user_assign = [], []
    for name, ctype, comment in SWING_USER_INPUTS:
        spec = next(s for s in SPEC if s[0] == name)
        # Standart qiymat H4/donchian profilidan (o'rta swing) olinadi
        prof = for_timeframe(base, "4h")
        cfg = prof.apply(Config(), "donchian_breakout")
        raw = resolve(spec[2], prof, merged_params(prof, "donchian_breakout"),
                      cfg.risk, "donchian_breakout")
        line = f"input {ctype:<7} {name}{' ' * max(1, 24 - len(name))}= {_fmt(raw, ctype)};"
        user_inputs.append(f"{line}{'':<{max(1, 46 - len(line))}}// {comment}")
        user_assign.append(f"   g_cfg.{name[3:]:<20} = {name};")

    tf_list = ", ".join(t.upper() for t in SWING_TFS)
    rev_list = ", ".join(t.upper() for t in SWING_STRATEGIES[2][1])
    return f'''//+------------------------------------------------------------------+
//|   {title}
//|
//|   {base.description}
//|   Savdo vaqti : {base.calendar.describe()}
//|
//|   PRESET KERAK EMAS. EA grafik timeframe'ini o'qiydi va o'sha
//|   timeframe uchun kalibrlangan parametrlarni O'ZI tanlaydi.
//|   Ruxsat etilgan: {tf_list}
//|   O'rtachaga qaytish faqat: {rev_list}
//|
//|   Nima uchun: parametrlar (ATR chegaralari, stop foizlari, tanaffuslar)
//|   timeframe'ga bog'liq. M5 uchun kalibrlangan qiymat D1 da hamma barni
//|   o'tkazib yuboradi. Preset yuklashni unutish shunday jimgina xatoga
//|   olib keladi — bu yerda u imkonsiz.
//|
//|   BU FAYL AVTOMATIK GENERATSIYA QILINGAN.
//|   Qo'lda tahrirlamang — `python tools/gen_mql5_experts.py` ishlating.
//+------------------------------------------------------------------+
#property copyright "scalpkit"
#property link      "https://github.com/rriskavan-crypto/scalp"
#property version   "1.10"
#property description "{title}"

#include <ScalpKit/Core.mqh>

input group "=== Strategiya ==="
input int     InpStrategy             = 1;    // 1 = trend (donchian), 2 = o'rtachaga qaytish

input group "=== Risk va xarajat ==="
{chr(10).join(user_inputs)}

input group "=== Hafta chegarasi ==="
input int     InpWeekendFlatMode      = -1;   // -1 = profil qaror qiladi, 0 = o'chirilgan, 1 = yoqilgan

input group "=== Texnik ==="
input long    InpMagicBase            = {magic_base}; // Magic asosi (+strategiya, +TF)
input int     InpDeviation            = 30;   // Maks. sirpanish (punkt)
input int     InpServerUtcOffset      = -99;  // Server-UTC farqi, -99 = avto
input bool    InpVerbose              = true; // Batafsil log

//+------------------------------------------------------------------+
//| Timeframe x strategiya bloklari (profillardan generatsiya qilingan)
//+------------------------------------------------------------------+
{chr(10).join(blocks)}
//+------------------------------------------------------------------+
//| Grafik timeframe'iga mos blokni tanlaydi.
//| Qaytaradi: TF indeksi (1..4), yoki 0 — qo'llab-quvvatlanmaydi.
//+------------------------------------------------------------------+
int ApplyProfileForChart(const int kind, const ENUM_TIMEFRAMES tf)
{{
{chr(10).join(dispatch)}
   return 0;
}}

//+------------------------------------------------------------------+
//| Parametrlarni yadroga uzatish                                    |
//+------------------------------------------------------------------+
bool LoadConfig()
{{
   int kind = InpStrategy;
   if(kind != 1 && kind != 2)
   {{
      PrintFormat("XATO: InpStrategy = %d. Ruxsat: 1 = trend, 2 = o'rtachaga qaytish.", kind);
      return false;
   }}

   int tfIdx = ApplyProfileForChart(kind, Period());
   if(tfIdx == 0)
   {{
      PrintFormat("XATO: %s grafigi bu strategiya uchun kalibrlanmagan. "
                  "Trend uchun: {tf_list}. O'rtachaga qaytish uchun: {rev_list}. "
                  "Sabab: bu juftlikda savdo soni statistik xulosa uchun juda kam.",
                  EnumToString(Period()));
      return false;
   }}

   //--- kalibrlangan blokdan KEYIN — foydalanuvchi qiymatlari ustun turadi
{chr(10).join(user_assign)}

   // -1 bo'lsa kalibrlangan blokdagi qiymat saqlanadi
   if(InpWeekendFlatMode >= 0)
      g_cfg.WeekendFlat     = (InpWeekendFlatMode == 1);

   g_cfg.StrategyKind       = kind;
   g_cfg.ExpectedTimeframe  = PERIOD_CURRENT;   // EA o'zini sozlaydi
   g_cfg.Magic              = InpMagicBase + kind * 10 + tfIdx;
   g_cfg.Deviation          = InpDeviation;
   g_cfg.ServerUtcOffset    = InpServerUtcOffset;
   g_cfg.Verbose            = InpVerbose;

   PrintFormat("Swing sozlandi: %s / %s | magic %I64d | ushlash ~%.2f kun | "
               "hafta oxiri %s",
               EnumToString(Period()),
               (kind == 1) ? "trend (donchian)" : "o'rtachaga qaytish",
               g_cfg.Magic, g_cfg.ExpectedHoldDays,
               g_cfg.WeekendFlat ? "pozitsiyasiz" : "ochiq qoladi");
   return true;
}}

int  OnInit()                    {{ if(!LoadConfig()) return INIT_PARAMETERS_INCORRECT;
                                   return ScalpKit_OnInit(); }}
void OnDeinit(const int reason)  {{ ScalpKit_OnDeinit(reason); }}
void OnTick()                    {{ ScalpKit_OnTick(); }}
double OnTester()                {{ return ScalpKit_OnTester(); }}
void OnTesterDeinit()            {{ ScalpKit_OnTesterDeinit(); }}
//+------------------------------------------------------------------+
'''


SWING_TARGETS = [
    (BTCUSD, "ScalpKit_BTC_Swing.mq5",
     "ScalpKit BTC/USD — SWING (M15-D1, o'zini sozlaydi)", 20261100),
    (XAUUSD, "ScalpKit_XAU_Swing.mq5",
     "ScalpKit XAU/USD (oltin) — SWING (M15-D1, o'zini sozlaydi)", 20261200),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="Fayllarni yozmasdan, mosligini tekshiradi")
    args = ap.parse_args()

    EXPERTS.mkdir(parents=True, exist_ok=True)
    PRESETS.mkdir(parents=True, exist_ok=True)
    stale = []
    for base, tf, strategy_name, filename, title, note in TARGETS:
        profile = for_timeframe(base, tf)
        text = render(profile, strategy_name, title, note)
        path = EXPERTS / filename
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(filename)
        else:
            path.write_text(text, encoding="utf-8")
            n_inputs = len(re.findall(r"^input\s+\w+\s+\w+", text, re.M))
            print(f"  {filename:<26} {len(text.splitlines()):>4} qator, {n_inputs} input")

        # Timeframe presetlari
        for preset_tf in PRESET_TIMEFRAMES[strategy_name]:
            pp = for_timeframe(base, preset_tf)
            body = render_preset(pp, strategy_name)
            name = f"{filename[:-4]}_{preset_tf.upper()}.set"
            target = PRESETS / name
            if args.check:
                if not target.exists() or target.read_text(encoding="utf-8") != body:
                    stale.append(name)
            else:
                target.write_text(body, encoding="utf-8")

    for base, filename, title, magic_base in SWING_TARGETS:
        text = render_swing(base, filename, title, magic_base)
        path = EXPERTS / filename
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(filename)
        else:
            path.write_text(text, encoding="utf-8")
            print(f"  {filename:<26} {len(text.splitlines()):>4} qator, "
                  f"preset kerak emas")

    if not args.check:
        print(f"  {len(list(PRESETS.glob('*.set')))} ta preset -> {PRESETS.relative_to(ROOT)}/")

    if args.check and stale:
        print("ESKIRGAN fayllar:", ", ".join(stale))
        print("Yechim: python tools/gen_mql5_experts.py")
        return 1
    if args.check:
        print("EA fayllari profillarga mos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
