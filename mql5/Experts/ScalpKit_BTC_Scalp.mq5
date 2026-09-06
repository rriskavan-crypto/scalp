//+------------------------------------------------------------------+
//|   ScalpKit BTC/USD — tanlab-skalping (M5/M15)
//|
//|   Bitcoin — 24/7, yuqori volatilitet, kuchli trend portlashlari (5m)
//|   Savdo vaqti : 24/7 (dam olish kunlarisiz)
//|   tipik spread 20 @ narx 65,000 -> xarajat ~0.103 R
//|
//|   MarketWatch'dagi nom BTCUSDm bo'lishi mumkin.
//|
//|   BU FAYL AVTOMATIK GENERATSIYA QILINGAN.
//|   Qo'lda tahrirlamang — `python tools/gen_mql5_experts.py` ishlating.
//|   Standart qiymatlar `scalpkit/profiles.py` dan olinadi, shuning
//|   uchun Python va MQL5 versiyalari hech qachon ajralib ketmaydi.
//+------------------------------------------------------------------+
#property copyright "scalpkit"
#property link      "https://github.com/rriskavan-crypto/scalp"
#property version   "1.10"
#property description "ScalpKit BTC/USD — tanlab-skalping (M5/M15)"

#include <ScalpKit/Core.mqh>

input group "=== Strategiya ==="
input int     InpStrategyKind         = 0;    // 0 = pullback, 1 = donchian
input ENUM_TIMEFRAMES InpExpectedTimeframe    = PERIOD_M5; // Preset qaysi TF uchun

input group "=== Rejim filtrlari ==="
input double  InpMinAtrPct            = 0.002; // ATR% minimal
input double  InpMaxAtrPct            = 0.012; // ATR% maksimal
input double  InpAdxMin               = 20.0; // ADX minimal
input bool    InpRequireHTF           = true; // H1 yo'nalishi mos bo'lsin
input bool    InpUseSession           = true; // Seans filtri
input int     InpSessionStartUTC      = 6;    // Seans boshi (UTC soat)
input int     InpSessionEndUTC        = 22;   // Seans oxiri (UTC soat)

input group "=== Yo'nalish ==="
input bool    InpAllowLong            = true; // Long savdolarga ruxsat
input bool    InpAllowShort           = true; // Short savdolarga ruxsat

input group "=== Donchian (trendni kuzatish) ==="
input int     InpTrendLen             = 200;  // Uzoq muddatli EMA
input bool    InpRequireTrendFilter   = true; // Narx EMA ning to'g'ri tomonida
input int     InpEntryLen             = 20;   // Kirish kanali (bar)
input int     InpExitLen              = 10;   // Chiqish kanali (bar)
input int     InpCooldownLen          = 3;    // Buzilishlar orasidagi masofa
input double  InpSlAtrMult            = 2.0;  // Stop masofasi (ATR)

input group "=== Setup (pullback) ==="
input int     InpImpulseLookback      = 12;   // Impuls oynasi (bar)
input double  InpImpulseBodyAtr       = 0.8;  // Impuls tanasi (ATR)
input double  InpImpulseVolZ          = 1.0;  // Impuls hajmi (z-score)
input int     InpPullbackLookback     = 4;    // Qaytish oynasi (bar)
input double  InpTouchAtr             = 0.25; // EMA21 zonasi (ATR)
input double  InpRsiPullbackLong      = 45.0; // RSI long uchun
input double  InpRsiPullbackShort     = 55.0; // RSI short uchun

input group "=== Trigger ==="
input double  InpTriggerVolZ          = -0.2; // Trigger hajmi (z-score)
input double  InpTriggerClosePos      = 0.5;  // Bar ichida yopilish o'rni
input double  InpMaxExtensionAtr      = 1.0;  // EMA21 dan maks. uzoqlik (ATR)

input group "=== Kirish ==="
input bool    InpUseLimitEntry        = true; // Limit order (false = market)
input double  InpEntryOffsetAtr       = 0.15; // Limit siljishi (ATR)
input int     InpEntryLimitBars       = 3;    // Limit muddati (bar)

input group "=== Stop ==="
input int     InpSwingLen             = 5;    // Swing oynasi (bar)
input double  InpSlBufferAtr          = 0.25; // Swing dan zaxira (ATR)
input double  InpMinSlAtr             = 1.0;  // Stop minimal (ATR)
input double  InpMaxSlAtr             = 2.2;  // Stop maksimal (ATR)
input double  InpMinStopPct           = 0.0015; // Stop minimal (narx %)
input double  InpMaxStopPct           = 0.02; // Stop maksimal (narx %)

input group "=== Chiqish (yutuqlar cheklanmaydi) ==="
input double  InpTp1R                 = 1.5;  // TP1 (R)
input double  InpTp1Fraction          = 0.35; // TP1 da yopiladigan ulush
input double  InpTp2R                 = 3.5;  // TP2 (R)
input double  InpTp1StopToR           = -0.35; // TP1 dan keyin stop (R)
input double  InpBeTriggerR           = 2.0;  // Zararsizlikka o'tish (R)
input double  InpBeOffsetR            = 0.05; // Zararsizlik zaxirasi (R)
input double  InpTrailAfterR          = 1.5;  // Trailing boshlanishi (R)
input double  InpTrailAtrMult         = 2.5;  // Trailing masofasi (ATR)
input double  InpTrailMinStepAtr      = 0.15; // Trailing minimal qadami (ATR)
input int     InpTimeStopBars         = 24;   // Vaqt stopi (bar)
input double  InpTimeStopMinR         = 0.5;  // Vaqt stopi shu R gacha
input bool    InpExitOnEmaCross       = true; // TP1 dan keyin EMA21 chiqishi

input group "=== Risk ==="
input double  InpRiskPerTrade         = 0.005; // Savdo boshiga risk
input double  InpMaxLeverage          = 5.0;  // Maksimal leverage
input int     InpMaxTradesPerDay      = 8;    // Kunlik savdolar chegarasi
input double  InpDailyLossLimit       = 0.03; // Kunlik zarar chegarasi
input int     InpMaxConsecLosses      = 3;    // Ketma-ket zararlar
input int     InpCooldownBars         = 6;    // Zarardan keyin tanaffus
input int     InpStreakCooldown       = 24;   // Seriyadan keyin tanaffus
input double  InpHalveRiskDD          = 0.08; // Shu drawdownda risk yarmiga

input group "=== Hafta chegarasi ==="
input bool    InpWeekendFlat          = false; // Hafta oxiriga pozitsiyasiz kirish
input int     InpWeekCloseHourUTC     = 19;   // Juma shu soatdan keyin savdo yo'q
input int     InpWeekCloseDow         = 4;    // 0=dushanba ... 4=juma
input int     InpWeekOpenSkipBars     = 6;    // Hafta ochilishida kutiladigan barlar

input group "=== Xarajat himoyasi ==="
input double  InpMaxCostR             = 0.40; // Xarajat shundan oshsa savdo yo'q

input group "=== Texnik ==="
input int     InpEmaFast              = 21;
input int     InpEmaMid               = 55;
input int     InpEmaSlow              = 200;
input int     InpAtrLen               = 14;
input int     InpRsiLen               = 7;
input int     InpAdxLen               = 14;
input int     InpDonchianLen          = 20;
input int     InpVolZLen              = 50;
input int     InpHtfEma               = 50;
input long    InpMagic                = 20260905; // Magic raqam
input int     InpDeviation            = 30;   // Maks. sirpanish (punkt)
input int     InpServerUtcOffset      = -99;  // Server-UTC farqi, -99 = avto
input bool    InpVerbose              = true; // Batafsil log

//+------------------------------------------------------------------+
//| Parametrlarni yadroga uzatish                                    |
//+------------------------------------------------------------------+
void LoadConfig()
{
   g_cfg.StrategyKind         = InpStrategyKind;
   g_cfg.ExpectedTimeframe    = InpExpectedTimeframe;
   g_cfg.MinAtrPct            = InpMinAtrPct;
   g_cfg.MaxAtrPct            = InpMaxAtrPct;
   g_cfg.AdxMin               = InpAdxMin;
   g_cfg.RequireHTF           = InpRequireHTF;
   g_cfg.UseSession           = InpUseSession;
   g_cfg.SessionStartUTC      = InpSessionStartUTC;
   g_cfg.SessionEndUTC        = InpSessionEndUTC;
   g_cfg.AllowLong            = InpAllowLong;
   g_cfg.AllowShort           = InpAllowShort;
   g_cfg.TrendLen             = InpTrendLen;
   g_cfg.RequireTrendFilter   = InpRequireTrendFilter;
   g_cfg.EntryLen             = InpEntryLen;
   g_cfg.ExitLen              = InpExitLen;
   g_cfg.CooldownLen          = InpCooldownLen;
   g_cfg.SlAtrMult            = InpSlAtrMult;
   g_cfg.ImpulseLookback      = InpImpulseLookback;
   g_cfg.ImpulseBodyAtr       = InpImpulseBodyAtr;
   g_cfg.ImpulseVolZ          = InpImpulseVolZ;
   g_cfg.PullbackLookback     = InpPullbackLookback;
   g_cfg.TouchAtr             = InpTouchAtr;
   g_cfg.RsiPullbackLong      = InpRsiPullbackLong;
   g_cfg.RsiPullbackShort     = InpRsiPullbackShort;
   g_cfg.TriggerVolZ          = InpTriggerVolZ;
   g_cfg.TriggerClosePos      = InpTriggerClosePos;
   g_cfg.MaxExtensionAtr      = InpMaxExtensionAtr;
   g_cfg.UseLimitEntry        = InpUseLimitEntry;
   g_cfg.EntryOffsetAtr       = InpEntryOffsetAtr;
   g_cfg.EntryLimitBars       = InpEntryLimitBars;
   g_cfg.SwingLen             = InpSwingLen;
   g_cfg.SlBufferAtr          = InpSlBufferAtr;
   g_cfg.MinSlAtr             = InpMinSlAtr;
   g_cfg.MaxSlAtr             = InpMaxSlAtr;
   g_cfg.MinStopPct           = InpMinStopPct;
   g_cfg.MaxStopPct           = InpMaxStopPct;
   g_cfg.Tp1R                 = InpTp1R;
   g_cfg.Tp1Fraction          = InpTp1Fraction;
   g_cfg.Tp2R                 = InpTp2R;
   g_cfg.Tp1StopToR           = InpTp1StopToR;
   g_cfg.BeTriggerR           = InpBeTriggerR;
   g_cfg.BeOffsetR            = InpBeOffsetR;
   g_cfg.TrailAfterR          = InpTrailAfterR;
   g_cfg.TrailAtrMult         = InpTrailAtrMult;
   g_cfg.TrailMinStepAtr      = InpTrailMinStepAtr;
   g_cfg.TimeStopBars         = InpTimeStopBars;
   g_cfg.TimeStopMinR         = InpTimeStopMinR;
   g_cfg.ExitOnEmaCross       = InpExitOnEmaCross;
   g_cfg.RiskPerTrade         = InpRiskPerTrade;
   g_cfg.MaxLeverage          = InpMaxLeverage;
   g_cfg.MaxTradesPerDay      = InpMaxTradesPerDay;
   g_cfg.DailyLossLimit       = InpDailyLossLimit;
   g_cfg.MaxConsecLosses      = InpMaxConsecLosses;
   g_cfg.CooldownBars         = InpCooldownBars;
   g_cfg.StreakCooldown       = InpStreakCooldown;
   g_cfg.HalveRiskDD          = InpHalveRiskDD;
   g_cfg.WeekendFlat          = InpWeekendFlat;
   g_cfg.WeekCloseHourUTC     = InpWeekCloseHourUTC;
   g_cfg.WeekCloseDow         = InpWeekCloseDow;
   g_cfg.WeekOpenSkipBars     = InpWeekOpenSkipBars;
   g_cfg.MaxCostR             = InpMaxCostR;
   g_cfg.EmaFast              = InpEmaFast;
   g_cfg.EmaMid               = InpEmaMid;
   g_cfg.EmaSlow              = InpEmaSlow;
   g_cfg.AtrLen               = InpAtrLen;
   g_cfg.RsiLen               = InpRsiLen;
   g_cfg.AdxLen               = InpAdxLen;
   g_cfg.DonchianLen          = InpDonchianLen;
   g_cfg.VolZLen              = InpVolZLen;
   g_cfg.HtfEma               = InpHtfEma;
   g_cfg.Magic                = InpMagic;
   g_cfg.Deviation            = InpDeviation;
   g_cfg.ServerUtcOffset      = InpServerUtcOffset;
   g_cfg.Verbose              = InpVerbose;
}

int  OnInit()                    { LoadConfig(); return ScalpKit_OnInit(); }
void OnDeinit(const int reason)  { ScalpKit_OnDeinit(reason); }
void OnTick()                    { ScalpKit_OnTick(); }
double OnTester()                { return ScalpKit_OnTester(); }
void OnTesterDeinit()            { ScalpKit_OnTesterDeinit(); }
//+------------------------------------------------------------------+
