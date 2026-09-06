//+------------------------------------------------------------------+
//|   ScalpKit XAU/USD (oltin) — SWING (M15-D1, o'zini sozlaydi)
//|
//|   Oltin — dam olish kunlari yopiq, London/NY seansida faol
//|   Savdo vaqti : Dushanba-Juma, juma 19:00 UTC dan keyin yangi savdo yo'q
//|
//|   PRESET KERAK EMAS. EA grafik timeframe'ini o'qiydi va o'sha
//|   timeframe uchun kalibrlangan parametrlarni O'ZI tanlaydi.
//|   Ruxsat etilgan: 15M, 1H, 4H, 1D
//|   O'rtachaga qaytish faqat: 15M, 1H
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
#property description "ScalpKit XAU/USD (oltin) — SWING (M15-D1, o'zini sozlaydi)"

#include <ScalpKit/Core.mqh>

input group "=== Strategiya ==="
input int     InpStrategy             = 1;    // 1 = trend (donchian), 2 = o'rtachaga qaytish

input group "=== Risk va xarajat ==="
input double  InpRiskPerTrade         = 0.005; // Savdo boshiga risk (0.005 = 0.5 %)
input double  InpDailyLossLimit       = 0.03; // Kunlik zarar chegarasi
input double  InpMaxLeverage          = 10.0; // Maksimal leverage
input double  InpMaxCostR             = 0.4;  // Xarajat shundan oshsa savdo yo'q
input bool    InpApplySwapCost        = true; // Xarajatga swapni (kechalik) qo'shish
input bool    InpAllowLong            = true; // Long savdolarga ruxsat
input bool    InpAllowShort           = true; // Short savdolarga ruxsat

input group "=== Hafta chegarasi ==="
input int     InpWeekendFlatMode      = -1;   // -1 = profil qaror qiladi, 0 = o'chirilgan, 1 = yoqilgan

input group "=== Texnik ==="
input long    InpMagicBase            = 20261200; // Magic asosi (+strategiya, +TF)
input int     InpDeviation            = 30;   // Maks. sirpanish (punkt)
input int     InpServerUtcOffset      = -99;  // Server-UTC farqi, -99 = avto
input bool    InpVerbose              = true; // Batafsil log

//+------------------------------------------------------------------+
//| Timeframe x strategiya bloklari (profillardan generatsiya qilingan)
//+------------------------------------------------------------------+
//--- 15M / donchian_breakout: stop >= 0.069 %, ushlash ~0.18 kun
void Apply_15M_1()
{
   g_cfg.MinAtrPct            = 0.0007785;
   g_cfg.MaxAtrPct            = 0.006055;
   g_cfg.AdxMin               = 20.0;
   g_cfg.RequireHTF           = false;
   g_cfg.UseSession           = true;
   g_cfg.SessionStartUTC      = 7;
   g_cfg.SessionEndUTC        = 20;
   g_cfg.TrendLen             = 200;
   g_cfg.RequireTrendFilter   = true;
   g_cfg.EntryLen             = 20;
   g_cfg.ExitLen              = 10;
   g_cfg.CooldownLen          = 3;
   g_cfg.SlAtrMult            = 2.0;
   g_cfg.AdxMax               = 25.0;
   g_cfg.BandLen              = 20;
   g_cfg.EntryZ               = 2.0;
   g_cfg.RevRsiLen            = 2;
   g_cfg.RsiOversold          = 10.0;
   g_cfg.RsiOverbought        = 90.0;
   g_cfg.RequireReversalBar   = true;
   g_cfg.SetupLookback        = 3;
   g_cfg.RangeDevAtr          = 4.0;
   g_cfg.MinTargetR           = 1.2;
   g_cfg.ImpulseLookback      = 12;
   g_cfg.ImpulseBodyAtr       = 0.8;
   g_cfg.ImpulseVolZ          = 1.0;
   g_cfg.PullbackLookback     = 4;
   g_cfg.TouchAtr             = 0.25;
   g_cfg.RsiPullbackLong      = 45.0;
   g_cfg.RsiPullbackShort     = 55.0;
   g_cfg.TriggerVolZ          = -0.2;
   g_cfg.TriggerClosePos      = 0.5;
   g_cfg.MaxExtensionAtr      = 1.0;
   g_cfg.UseLimitEntry        = false;
   g_cfg.EntryOffsetAtr       = 0.0;
   g_cfg.EntryLimitBars       = 1;
   g_cfg.SwingLen             = 5;
   g_cfg.SlBufferAtr          = 0.25;
   g_cfg.MinSlAtr             = 1.5;
   g_cfg.MaxSlAtr             = 3.5;
   g_cfg.MinStopPct           = 0.000692;
   g_cfg.MaxStopPct           = 0.01038;
   g_cfg.Tp1R                 = 0.0;
   g_cfg.Tp1Fraction          = 0.0;
   g_cfg.Tp2R                 = 0.0;
   g_cfg.Tp1StopToR           = 0.0;
   g_cfg.BeTriggerR           = 1000000000.0;
   g_cfg.BeOffsetR            = 0.0;
   g_cfg.TrailAfterR          = 0.5;
   g_cfg.TrailAtrMult         = 3.0;
   g_cfg.TrailMinStepAtr      = 0.25;
   g_cfg.TimeStopBars         = 1000000;
   g_cfg.TimeStopMinR         = 0.0;
   g_cfg.ExitOnEmaCross       = false;
   g_cfg.MaxTradesPerDay      = 3;
   g_cfg.MaxConsecLosses      = 3;
   g_cfg.CooldownBars         = 4;
   g_cfg.StreakCooldown       = 16;
   g_cfg.HalveRiskDD          = 0.08;
   g_cfg.WeekendFlat          = true;
   g_cfg.WeekCloseHourUTC     = 19;
   g_cfg.WeekCloseDow         = 4;
   g_cfg.WeekOpenSkipBars     = 6;
   g_cfg.ExpectedHoldDays     = 0.1823;
   g_cfg.EmaFast              = 21;
   g_cfg.EmaMid               = 55;
   g_cfg.EmaSlow              = 200;
   g_cfg.AtrLen               = 14;
   g_cfg.RsiLen               = 7;
   g_cfg.AdxLen               = 14;
   g_cfg.DonchianLen          = 20;
   g_cfg.VolZLen              = 50;
   g_cfg.HtfEma               = 50;
}

//--- 1H / donchian_breakout: stop >= 0.140 %, ushlash ~0.73 kun
void Apply_1H_1()
{
   g_cfg.MinAtrPct            = 0.001575;
   g_cfg.MaxAtrPct            = 0.01225;
   g_cfg.AdxMin               = 20.0;
   g_cfg.RequireHTF           = false;
   g_cfg.UseSession           = true;
   g_cfg.SessionStartUTC      = 7;
   g_cfg.SessionEndUTC        = 20;
   g_cfg.TrendLen             = 200;
   g_cfg.RequireTrendFilter   = true;
   g_cfg.EntryLen             = 20;
   g_cfg.ExitLen              = 10;
   g_cfg.CooldownLen          = 3;
   g_cfg.SlAtrMult            = 2.0;
   g_cfg.AdxMax               = 25.0;
   g_cfg.BandLen              = 20;
   g_cfg.EntryZ               = 2.0;
   g_cfg.RevRsiLen            = 2;
   g_cfg.RsiOversold          = 10.0;
   g_cfg.RsiOverbought        = 90.0;
   g_cfg.RequireReversalBar   = true;
   g_cfg.SetupLookback        = 3;
   g_cfg.RangeDevAtr          = 4.0;
   g_cfg.MinTargetR           = 1.2;
   g_cfg.ImpulseLookback      = 12;
   g_cfg.ImpulseBodyAtr       = 0.8;
   g_cfg.ImpulseVolZ          = 1.0;
   g_cfg.PullbackLookback     = 4;
   g_cfg.TouchAtr             = 0.25;
   g_cfg.RsiPullbackLong      = 45.0;
   g_cfg.RsiPullbackShort     = 55.0;
   g_cfg.TriggerVolZ          = -0.2;
   g_cfg.TriggerClosePos      = 0.5;
   g_cfg.MaxExtensionAtr      = 1.0;
   g_cfg.UseLimitEntry        = false;
   g_cfg.EntryOffsetAtr       = 0.0;
   g_cfg.EntryLimitBars       = 1;
   g_cfg.SwingLen             = 5;
   g_cfg.SlBufferAtr          = 0.25;
   g_cfg.MinSlAtr             = 1.5;
   g_cfg.MaxSlAtr             = 3.5;
   g_cfg.MinStopPct           = 0.0014;
   g_cfg.MaxStopPct           = 0.021;
   g_cfg.Tp1R                 = 0.0;
   g_cfg.Tp1Fraction          = 0.0;
   g_cfg.Tp2R                 = 0.0;
   g_cfg.Tp1StopToR           = 0.0;
   g_cfg.BeTriggerR           = 1000000000.0;
   g_cfg.BeOffsetR            = 0.0;
   g_cfg.TrailAfterR          = 0.5;
   g_cfg.TrailAtrMult         = 3.0;
   g_cfg.TrailMinStepAtr      = 0.25;
   g_cfg.TimeStopBars         = 1000000;
   g_cfg.TimeStopMinR         = 0.0;
   g_cfg.ExitOnEmaCross       = false;
   g_cfg.MaxTradesPerDay      = 1;
   g_cfg.MaxConsecLosses      = 3;
   g_cfg.CooldownBars         = 3;
   g_cfg.StreakCooldown       = 8;
   g_cfg.HalveRiskDD          = 0.08;
   g_cfg.WeekendFlat          = true;
   g_cfg.WeekCloseHourUTC     = 19;
   g_cfg.WeekCloseDow         = 4;
   g_cfg.WeekOpenSkipBars     = 6;
   g_cfg.ExpectedHoldDays     = 0.7292;
   g_cfg.EmaFast              = 21;
   g_cfg.EmaMid               = 55;
   g_cfg.EmaSlow              = 200;
   g_cfg.AtrLen               = 14;
   g_cfg.RsiLen               = 7;
   g_cfg.AdxLen               = 14;
   g_cfg.DonchianLen          = 20;
   g_cfg.VolZLen              = 50;
   g_cfg.HtfEma               = 50;
}

//--- 4H / donchian_breakout: stop >= 0.288 %, ushlash ~2.92 kun
void Apply_4H_1()
{
   g_cfg.MinAtrPct            = 0.00324;
   g_cfg.MaxAtrPct            = 0.0252;
   g_cfg.AdxMin               = 20.0;
   g_cfg.RequireHTF           = false;
   g_cfg.UseSession           = false;
   g_cfg.SessionStartUTC      = 7;
   g_cfg.SessionEndUTC        = 20;
   g_cfg.TrendLen             = 200;
   g_cfg.RequireTrendFilter   = true;
   g_cfg.EntryLen             = 20;
   g_cfg.ExitLen              = 10;
   g_cfg.CooldownLen          = 3;
   g_cfg.SlAtrMult            = 2.0;
   g_cfg.AdxMax               = 25.0;
   g_cfg.BandLen              = 20;
   g_cfg.EntryZ               = 2.0;
   g_cfg.RevRsiLen            = 2;
   g_cfg.RsiOversold          = 10.0;
   g_cfg.RsiOverbought        = 90.0;
   g_cfg.RequireReversalBar   = true;
   g_cfg.SetupLookback        = 3;
   g_cfg.RangeDevAtr          = 4.0;
   g_cfg.MinTargetR           = 1.2;
   g_cfg.ImpulseLookback      = 12;
   g_cfg.ImpulseBodyAtr       = 0.8;
   g_cfg.ImpulseVolZ          = 1.0;
   g_cfg.PullbackLookback     = 4;
   g_cfg.TouchAtr             = 0.25;
   g_cfg.RsiPullbackLong      = 45.0;
   g_cfg.RsiPullbackShort     = 55.0;
   g_cfg.TriggerVolZ          = -0.2;
   g_cfg.TriggerClosePos      = 0.5;
   g_cfg.MaxExtensionAtr      = 1.0;
   g_cfg.UseLimitEntry        = false;
   g_cfg.EntryOffsetAtr       = 0.0;
   g_cfg.EntryLimitBars       = 1;
   g_cfg.SwingLen             = 5;
   g_cfg.SlBufferAtr          = 0.25;
   g_cfg.MinSlAtr             = 1.5;
   g_cfg.MaxSlAtr             = 3.5;
   g_cfg.MinStopPct           = 0.00288;
   g_cfg.MaxStopPct           = 0.0432;
   g_cfg.Tp1R                 = 0.0;
   g_cfg.Tp1Fraction          = 0.0;
   g_cfg.Tp2R                 = 0.0;
   g_cfg.Tp1StopToR           = 0.0;
   g_cfg.BeTriggerR           = 1000000000.0;
   g_cfg.BeOffsetR            = 0.0;
   g_cfg.TrailAfterR          = 0.5;
   g_cfg.TrailAtrMult         = 3.0;
   g_cfg.TrailMinStepAtr      = 0.25;
   g_cfg.TimeStopBars         = 1000000;
   g_cfg.TimeStopMinR         = 0.0;
   g_cfg.ExitOnEmaCross       = false;
   g_cfg.MaxTradesPerDay      = 1;
   g_cfg.MaxConsecLosses      = 3;
   g_cfg.CooldownBars         = 2;
   g_cfg.StreakCooldown       = 4;
   g_cfg.HalveRiskDD          = 0.08;
   g_cfg.WeekendFlat          = false;
   g_cfg.WeekCloseHourUTC     = 19;
   g_cfg.WeekCloseDow         = 4;
   g_cfg.WeekOpenSkipBars     = 6;
   g_cfg.ExpectedHoldDays     = 2.9167;
   g_cfg.EmaFast              = 21;
   g_cfg.EmaMid               = 55;
   g_cfg.EmaSlow              = 200;
   g_cfg.AtrLen               = 14;
   g_cfg.RsiLen               = 7;
   g_cfg.AdxLen               = 14;
   g_cfg.DonchianLen          = 20;
   g_cfg.VolZLen              = 50;
   g_cfg.HtfEma               = 50;
}

//--- 1D / donchian_breakout: stop >= 0.756 %, ushlash ~17.50 kun
void Apply_1D_1()
{
   g_cfg.MinAtrPct            = 0.008505;
   g_cfg.MaxAtrPct            = 0.06615;
   g_cfg.AdxMin               = 20.0;
   g_cfg.RequireHTF           = false;
   g_cfg.UseSession           = false;
   g_cfg.SessionStartUTC      = 7;
   g_cfg.SessionEndUTC        = 20;
   g_cfg.TrendLen             = 200;
   g_cfg.RequireTrendFilter   = true;
   g_cfg.EntryLen             = 20;
   g_cfg.ExitLen              = 10;
   g_cfg.CooldownLen          = 3;
   g_cfg.SlAtrMult            = 2.0;
   g_cfg.AdxMax               = 25.0;
   g_cfg.BandLen              = 20;
   g_cfg.EntryZ               = 2.0;
   g_cfg.RevRsiLen            = 2;
   g_cfg.RsiOversold          = 10.0;
   g_cfg.RsiOverbought        = 90.0;
   g_cfg.RequireReversalBar   = true;
   g_cfg.SetupLookback        = 3;
   g_cfg.RangeDevAtr          = 4.0;
   g_cfg.MinTargetR           = 1.2;
   g_cfg.ImpulseLookback      = 12;
   g_cfg.ImpulseBodyAtr       = 0.8;
   g_cfg.ImpulseVolZ          = 1.0;
   g_cfg.PullbackLookback     = 4;
   g_cfg.TouchAtr             = 0.25;
   g_cfg.RsiPullbackLong      = 45.0;
   g_cfg.RsiPullbackShort     = 55.0;
   g_cfg.TriggerVolZ          = -0.2;
   g_cfg.TriggerClosePos      = 0.5;
   g_cfg.MaxExtensionAtr      = 1.0;
   g_cfg.UseLimitEntry        = false;
   g_cfg.EntryOffsetAtr       = 0.0;
   g_cfg.EntryLimitBars       = 1;
   g_cfg.SwingLen             = 5;
   g_cfg.SlBufferAtr          = 0.25;
   g_cfg.MinSlAtr             = 1.5;
   g_cfg.MaxSlAtr             = 3.5;
   g_cfg.MinStopPct           = 0.00756;
   g_cfg.MaxStopPct           = 0.1134;
   g_cfg.Tp1R                 = 0.0;
   g_cfg.Tp1Fraction          = 0.0;
   g_cfg.Tp2R                 = 0.0;
   g_cfg.Tp1StopToR           = 0.0;
   g_cfg.BeTriggerR           = 1000000000.0;
   g_cfg.BeOffsetR            = 0.0;
   g_cfg.TrailAfterR          = 0.5;
   g_cfg.TrailAtrMult         = 3.0;
   g_cfg.TrailMinStepAtr      = 0.25;
   g_cfg.TimeStopBars         = 1000000;
   g_cfg.TimeStopMinR         = 0.0;
   g_cfg.ExitOnEmaCross       = false;
   g_cfg.MaxTradesPerDay      = 1;
   g_cfg.MaxConsecLosses      = 3;
   g_cfg.CooldownBars         = 1;
   g_cfg.StreakCooldown       = 2;
   g_cfg.HalveRiskDD          = 0.08;
   g_cfg.WeekendFlat          = false;
   g_cfg.WeekCloseHourUTC     = 19;
   g_cfg.WeekCloseDow         = 4;
   g_cfg.WeekOpenSkipBars     = 6;
   g_cfg.ExpectedHoldDays     = 17.5;
   g_cfg.EmaFast              = 21;
   g_cfg.EmaMid               = 55;
   g_cfg.EmaSlow              = 200;
   g_cfg.AtrLen               = 14;
   g_cfg.RsiLen               = 7;
   g_cfg.AdxLen               = 14;
   g_cfg.DonchianLen          = 20;
   g_cfg.VolZLen              = 50;
   g_cfg.HtfEma               = 50;
}

//--- 15M / range_reversion: stop >= 0.069 %, ushlash ~0.07 kun
void Apply_15M_2()
{
   g_cfg.MinAtrPct            = 0.0007785;
   g_cfg.MaxAtrPct            = 0.006055;
   g_cfg.AdxMin               = 20.0;
   g_cfg.RequireHTF           = false;
   g_cfg.UseSession           = true;
   g_cfg.SessionStartUTC      = 7;
   g_cfg.SessionEndUTC        = 20;
   g_cfg.TrendLen             = 200;
   g_cfg.RequireTrendFilter   = true;
   g_cfg.EntryLen             = 20;
   g_cfg.ExitLen              = 10;
   g_cfg.CooldownLen          = 3;
   g_cfg.SlAtrMult            = 1.5;
   g_cfg.AdxMax               = 25.0;
   g_cfg.BandLen              = 20;
   g_cfg.EntryZ               = 2.0;
   g_cfg.RevRsiLen            = 2;
   g_cfg.RsiOversold          = 10.0;
   g_cfg.RsiOverbought        = 90.0;
   g_cfg.RequireReversalBar   = true;
   g_cfg.SetupLookback        = 3;
   g_cfg.RangeDevAtr          = 4.0;
   g_cfg.MinTargetR           = 1.2;
   g_cfg.ImpulseLookback      = 12;
   g_cfg.ImpulseBodyAtr       = 0.8;
   g_cfg.ImpulseVolZ          = 1.0;
   g_cfg.PullbackLookback     = 4;
   g_cfg.TouchAtr             = 0.25;
   g_cfg.RsiPullbackLong      = 45.0;
   g_cfg.RsiPullbackShort     = 55.0;
   g_cfg.TriggerVolZ          = -0.2;
   g_cfg.TriggerClosePos      = 0.5;
   g_cfg.MaxExtensionAtr      = 1.0;
   g_cfg.UseLimitEntry        = false;
   g_cfg.EntryOffsetAtr       = 0.0;
   g_cfg.EntryLimitBars       = 1;
   g_cfg.SwingLen             = 5;
   g_cfg.SlBufferAtr          = 0.25;
   g_cfg.MinSlAtr             = 1.0;
   g_cfg.MaxSlAtr             = 3.0;
   g_cfg.MinStopPct           = 0.000692;
   g_cfg.MaxStopPct           = 0.01038;
   g_cfg.Tp1R                 = 0.0;
   g_cfg.Tp1Fraction          = 0.0;
   g_cfg.Tp2R                 = 1.5;
   g_cfg.Tp1StopToR           = 0.0;
   g_cfg.BeTriggerR           = 1000000000.0;
   g_cfg.BeOffsetR            = 0.0;
   g_cfg.TrailAfterR          = 1000000000.0;
   g_cfg.TrailAtrMult         = 3.0;
   g_cfg.TrailMinStepAtr      = 0.25;
   g_cfg.TimeStopBars         = 12;
   g_cfg.TimeStopMinR         = 1000000000.0;
   g_cfg.ExitOnEmaCross       = false;
   g_cfg.MaxTradesPerDay      = 3;
   g_cfg.MaxConsecLosses      = 3;
   g_cfg.CooldownBars         = 4;
   g_cfg.StreakCooldown       = 16;
   g_cfg.HalveRiskDD          = 0.08;
   g_cfg.WeekendFlat          = true;
   g_cfg.WeekCloseHourUTC     = 19;
   g_cfg.WeekCloseDow         = 4;
   g_cfg.WeekOpenSkipBars     = 6;
   g_cfg.ExpectedHoldDays     = 0.0688;
   g_cfg.EmaFast              = 21;
   g_cfg.EmaMid               = 55;
   g_cfg.EmaSlow              = 200;
   g_cfg.AtrLen               = 14;
   g_cfg.RsiLen               = 7;
   g_cfg.AdxLen               = 14;
   g_cfg.DonchianLen          = 20;
   g_cfg.VolZLen              = 50;
   g_cfg.HtfEma               = 50;
}

//--- 1H / range_reversion: stop >= 0.140 %, ushlash ~0.28 kun
void Apply_1H_2()
{
   g_cfg.MinAtrPct            = 0.001575;
   g_cfg.MaxAtrPct            = 0.01225;
   g_cfg.AdxMin               = 20.0;
   g_cfg.RequireHTF           = false;
   g_cfg.UseSession           = true;
   g_cfg.SessionStartUTC      = 7;
   g_cfg.SessionEndUTC        = 20;
   g_cfg.TrendLen             = 200;
   g_cfg.RequireTrendFilter   = true;
   g_cfg.EntryLen             = 20;
   g_cfg.ExitLen              = 10;
   g_cfg.CooldownLen          = 3;
   g_cfg.SlAtrMult            = 1.5;
   g_cfg.AdxMax               = 25.0;
   g_cfg.BandLen              = 20;
   g_cfg.EntryZ               = 2.0;
   g_cfg.RevRsiLen            = 2;
   g_cfg.RsiOversold          = 10.0;
   g_cfg.RsiOverbought        = 90.0;
   g_cfg.RequireReversalBar   = true;
   g_cfg.SetupLookback        = 3;
   g_cfg.RangeDevAtr          = 4.0;
   g_cfg.MinTargetR           = 1.2;
   g_cfg.ImpulseLookback      = 12;
   g_cfg.ImpulseBodyAtr       = 0.8;
   g_cfg.ImpulseVolZ          = 1.0;
   g_cfg.PullbackLookback     = 4;
   g_cfg.TouchAtr             = 0.25;
   g_cfg.RsiPullbackLong      = 45.0;
   g_cfg.RsiPullbackShort     = 55.0;
   g_cfg.TriggerVolZ          = -0.2;
   g_cfg.TriggerClosePos      = 0.5;
   g_cfg.MaxExtensionAtr      = 1.0;
   g_cfg.UseLimitEntry        = false;
   g_cfg.EntryOffsetAtr       = 0.0;
   g_cfg.EntryLimitBars       = 1;
   g_cfg.SwingLen             = 5;
   g_cfg.SlBufferAtr          = 0.25;
   g_cfg.MinSlAtr             = 1.0;
   g_cfg.MaxSlAtr             = 3.0;
   g_cfg.MinStopPct           = 0.0014;
   g_cfg.MaxStopPct           = 0.021;
   g_cfg.Tp1R                 = 0.0;
   g_cfg.Tp1Fraction          = 0.0;
   g_cfg.Tp2R                 = 1.5;
   g_cfg.Tp1StopToR           = 0.0;
   g_cfg.BeTriggerR           = 1000000000.0;
   g_cfg.BeOffsetR            = 0.0;
   g_cfg.TrailAfterR          = 1000000000.0;
   g_cfg.TrailAtrMult         = 3.0;
   g_cfg.TrailMinStepAtr      = 0.25;
   g_cfg.TimeStopBars         = 12;
   g_cfg.TimeStopMinR         = 1000000000.0;
   g_cfg.ExitOnEmaCross       = false;
   g_cfg.MaxTradesPerDay      = 1;
   g_cfg.MaxConsecLosses      = 3;
   g_cfg.CooldownBars         = 3;
   g_cfg.StreakCooldown       = 8;
   g_cfg.HalveRiskDD          = 0.08;
   g_cfg.WeekendFlat          = true;
   g_cfg.WeekCloseHourUTC     = 19;
   g_cfg.WeekCloseDow         = 4;
   g_cfg.WeekOpenSkipBars     = 6;
   g_cfg.ExpectedHoldDays     = 0.275;
   g_cfg.EmaFast              = 21;
   g_cfg.EmaMid               = 55;
   g_cfg.EmaSlow              = 200;
   g_cfg.AtrLen               = 14;
   g_cfg.RsiLen               = 7;
   g_cfg.AdxLen               = 14;
   g_cfg.DonchianLen          = 20;
   g_cfg.VolZLen              = 50;
   g_cfg.HtfEma               = 50;
}

//+------------------------------------------------------------------+
//| Grafik timeframe'iga mos blokni tanlaydi.
//| Qaytaradi: TF indeksi (1..4), yoki 0 — qo'llab-quvvatlanmaydi.
//+------------------------------------------------------------------+
int ApplyProfileForChart(const int kind, const ENUM_TIMEFRAMES tf)
{
   if(kind == 1 && tf == PERIOD_M15) { Apply_15M_1(); return 1; }
   if(kind == 1 && tf == PERIOD_H1) { Apply_1H_1(); return 2; }
   if(kind == 1 && tf == PERIOD_H4) { Apply_4H_1(); return 3; }
   if(kind == 1 && tf == PERIOD_D1) { Apply_1D_1(); return 4; }
   if(kind == 2 && tf == PERIOD_M15) { Apply_15M_2(); return 1; }
   if(kind == 2 && tf == PERIOD_H1) { Apply_1H_2(); return 2; }
   return 0;
}

//+------------------------------------------------------------------+
//| Parametrlarni yadroga uzatish                                    |
//+------------------------------------------------------------------+
bool LoadConfig()
{
   int kind = InpStrategy;
   if(kind != 1 && kind != 2)
   {
      PrintFormat("XATO: InpStrategy = %d. Ruxsat: 1 = trend, 2 = o'rtachaga qaytish.", kind);
      return false;
   }

   int tfIdx = ApplyProfileForChart(kind, Period());
   if(tfIdx == 0)
   {
      PrintFormat("XATO: %s grafigi bu strategiya uchun kalibrlanmagan. "
                  "Trend uchun: 15M, 1H, 4H, 1D. O'rtachaga qaytish uchun: 15M, 1H. "
                  "Sabab: bu juftlikda savdo soni statistik xulosa uchun juda kam.",
                  EnumToString(Period()));
      return false;
   }

   //--- kalibrlangan blokdan KEYIN — foydalanuvchi qiymatlari ustun turadi
   g_cfg.RiskPerTrade         = InpRiskPerTrade;
   g_cfg.DailyLossLimit       = InpDailyLossLimit;
   g_cfg.MaxLeverage          = InpMaxLeverage;
   g_cfg.MaxCostR             = InpMaxCostR;
   g_cfg.ApplySwapCost        = InpApplySwapCost;
   g_cfg.AllowLong            = InpAllowLong;
   g_cfg.AllowShort           = InpAllowShort;

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
}

int  OnInit()                    { if(!LoadConfig()) return INIT_PARAMETERS_INCORRECT;
                                   return ScalpKit_OnInit(); }
void OnDeinit(const int reason)  { ScalpKit_OnDeinit(reason); }
void OnTick()                    { ScalpKit_OnTick(); }
double OnTester()                { return ScalpKit_OnTester(); }
void OnTesterDeinit()            { ScalpKit_OnTesterDeinit(); }
//+------------------------------------------------------------------+
