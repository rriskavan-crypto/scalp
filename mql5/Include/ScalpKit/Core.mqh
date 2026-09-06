//+------------------------------------------------------------------+
//|                                    ScalpKit/Core.mqh             |
//|   "M5 Momentum Pullback" strategiyasining umumiy yadrosi         |
//|                                                                  |
//|   Bu fayl mantiqni saqlaydi; parametrlar EA fayllarida           |
//|   e'lon qilinadi va `ScalpKitConfig` orqali uzatiladi.           |
//|   Shu tufayli BTCUSD va XAUUSD versiyalari bitta kod bazasidan   |
//|   ishlaydi — tuzatish bittasida qilinsa, ikkalasiga ham tegadi.  |
//+------------------------------------------------------------------+
#property copyright "scalpkit"
#property link      "https://github.com/rriskavan-crypto/scalp"

#include <Trade\Trade.mqh>

//==================================================================
//  SOZLAMALAR STRUKTURASI
//==================================================================
struct ScalpKitConfig
{
   //--- === Rejim filtrlari ===
   double   MinAtrPct;             // ATR% minimal (0.0020 = 0.20 %)
   double   MaxAtrPct;             // ATR% maksimal
   double   AdxMin;                // ADX minimal
   bool     RequireHTF;            // H1 yo'nalishi mos bo'lsin
   bool     UseSession;            // Seans filtri
   int      SessionStartUTC;       // Seans boshi (UTC soat)
   int      SessionEndUTC;         // Seans oxiri (UTC soat)
   //--- === Setup ===
   int      ImpulseLookback;       // Impuls oynasi (bar)
   double   ImpulseBodyAtr;        // Impuls tanasi (ATR)
   double   ImpulseVolZ;           // Impuls hajmi (z-score)
   int      PullbackLookback;      // Qaytish oynasi (bar)
   double   TouchAtr;              // EMA21 ga tegish zonasi (ATR)
   double   RsiPullbackLong;       // RSI long uchun
   double   RsiPullbackShort;      // RSI short uchun
   //--- === Trigger ===
   double   TriggerVolZ;           // Trigger hajmi (z-score)
   double   TriggerClosePos;       // Bar ichida yopilish o'rni
   double   MaxExtensionAtr;       // EMA21 dan maks. uzoqlik (ATR)
   //--- === Kirish ===
   bool     UseLimitEntry;         // Limit order (false = market)
   double   EntryOffsetAtr;        // Limit siljishi (ATR)
   int      EntryLimitBars;        // Limit amal qilish muddati (bar)
   //--- === Stop ===
   int      SwingLen;              // Swing oynasi (bar)
   double   SlBufferAtr;           // Swing dan zaxira (ATR)
   double   MinSlAtr;              // Stop minimal (ATR)
   double   MaxSlAtr;              // Stop maksimal (ATR)
   double   MinStopPct;            // Stop minimal (narx %)
   double   MaxStopPct;            // Stop maksimal (narx %)
   //--- === Chiqish (yutuqlar cheklanmaydi) ===
   double   Tp1R;                  // TP1 (R)
   double   Tp1Fraction;           // TP1 da yopiladigan ulush
   double   Tp2R;                  // TP2 (R)
   double   Tp1StopToR;            // TP1 dan keyin stop (R)
   double   BeTriggerR;            // Zararsizlikka o'tish (R)
   double   BeOffsetR;             // Zararsizlik zaxirasi (R)
   double   TrailAfterR;           // Trailing boshlanishi (R)
   double   TrailAtrMult;          // Trailing masofasi (ATR)
   double   TrailMinStepAtr;       // Trailing minimal qadami (ATR)
   int      TimeStopBars;          // Vaqt stopi (bar)
   double   TimeStopMinR;          // Vaqt stopi shu R gacha
   bool     ExitOnEmaCross;        // TP1 dan keyin EMA21 chiqishi
   //--- === Risk ===
   double   RiskPerTrade;          // Savdo boshiga risk (0.005 = 0.5 %)
   double   MaxLeverage;           // Maksimal leverage
   int      MaxTradesPerDay;       // Kunlik savdolar chegarasi
   double   DailyLossLimit;        // Kunlik zarar chegarasi
   int      MaxConsecLosses;       // Ketma-ket zararlar
   int      CooldownBars;          // Zarardan keyin tanaffus (bar)
   int      StreakCooldown;        // Seriyadan keyin tanaffus (bar)
   double   HalveRiskDD;           // Shu drawdownda risk yarmiga
   //--- === Xarajat himoyasi ===
   double   MaxCostR;              // Xarajat shundan oshsa savdo yo'q
   bool     ApplySwapCost;         // Xarajatga swapni (kechalik) qo'shish
   double   ExpectedHoldDays;      // Kutilgan ushlash muddati (kun)
   //--- === Yo'nalish ===
   bool     AllowLong;             // Long savdolarga ruxsat
   bool     AllowShort;            // Short savdolarga ruxsat
   //--- === Strategiya ===
   int      StrategyKind;          // 0 = momentum_pullback, 1 = donchian_breakout
   int      ExpectedTimeframe;     // preset qaysi TF uchun (PERIOD_CURRENT = tekshirmaslik)
   //--- === Donchian (trendni kuzatish) ===
   int      TrendLen;              // uzoq muddatli EMA
   bool     RequireTrendFilter;    // narx EMA ning to'g'ri tomonidami
   int      EntryLen;              // kirish kanali (bar)
   int      ExitLen;               // chiqish kanali (bar)
   int      CooldownLen;           // buzilishlar orasidagi eng kam masofa
   double   SlAtrMult;             // stop masofasi (ATR)
   //--- === Range Reversion (o'rtachaga qaytish) ===
   double   AdxMax;                // bundan yuqorisi trend — savdo yo'q
   int      BandLen;               // o'rtacha va sigma oynasi
   double   EntryZ;                // necha sigma chekkada kirish
   int      RevRsiLen;             // qisqa RSI uzunligi
   double   RsiOversold;
   double   RsiOverbought;
   bool     RequireReversalBar;    // qaytish bari tasdig'i
   int      SetupLookback;         // setup shuncha bar ichida
   double   RangeDevAtr;           // EMA dan maks. uzoqlik (ATR)
   double   MinTargetR;            // mukofot/risk minimal nisbati
   //--- === Hafta chegarasi (oltin/forex uchun) ===
   bool     WeekendFlat;           // Hafta oxiriga pozitsiyasiz kirish
   int      WeekCloseHourUTC;      // Juma shu soatdan keyin yangi savdo yo'q
   int      WeekCloseDow;          // 0=dushanba ... 4=juma
   int      WeekOpenSkipBars;      // Hafta ochilishidan keyin kutiladigan barlar
   //--- === Texnik ===
   int      EmaFast;
   int      EmaMid;
   int      EmaSlow;
   int      AtrLen;
   int      RsiLen;
   int      AdxLen;
   int      DonchianLen;
   int      VolZLen;
   int      HtfEma;
   long     Magic;                 // Magic raqam
   int      Deviation;             // Maks. sirpanish (punkt)
   int      ServerUtcOffset;       // Server-UTC farqi (soat), -99 = avto
   bool     Verbose;               // Batafsil log
};

ScalpKitConfig g_cfg;

//==================================================================
//  GLOBAL HOLAT
//==================================================================
CTrade   Trade;

int      hEmaFast = INVALID_HANDLE, hEmaMid = INVALID_HANDLE, hEmaSlow = INVALID_HANDLE;
int      hAtr = INVALID_HANDLE, hRsi = INVALID_HANDLE, hAdx = INVALID_HANDLE;
int      hHtfEma = INVALID_HANDLE, hTrendEma = INVALID_HANDLE;
int      hRevRsi = INVALID_HANDLE, hStdDev = INVALID_HANDLE, hBandMa = INVALID_HANDLE;

ENUM_TIMEFRAMES g_tf = PERIOD_M5;   // grafik timeframe'i, OnInit da o'rnatiladi
bool     g_exitLong = false;        // strategiyaning chiqish signali (bar bo'yicha)
bool     g_exitShort = false;
datetime g_lastBarTime = 0;
int      g_barsSinceGap = 9999;   // hafta/bayram uzilishidan keyingi barlar
int      g_serverUtcOffset = 0;
int      g_barCounter = 0;          // tanaffuslarni sanash uchun
bool     g_swapModeWarned = false;  // noma'lum swap rejimi haqida bir marta
int      g_blockUntilBar = -1;
int      g_consecLosses = 0;
int      g_tradesToday = 0;
datetime g_currentDay = 0;
double   g_dayStartEquity = 0.0;
double   g_peakEquity = 0.0;

// --- OnTester uchun statistika ---
double   g_sumR = 0.0;
int      g_closedTrades = 0;
int      g_wins = 0;

// --- Savdo holati (pozitsiya/order ticket bo'yicha) ---
struct TradeState
{
   ulong    ticket;
   ulong    positionId;      // tarixdan natijani olish uchun (POSITION_IDENTIFIER)
   int      side;            // +1 long, -1 short
   double   entryPrice;
   double   riskPerUnit;     // R, narx birligida
   double   riskMoney;       // R, pul birligida
   double   atrAtEntry;
   double   bestPrice;
   datetime entryTime;
   int      entryBar;
   bool     tp1Done;
   bool     beMoved;
   bool     isPending;
};

TradeState g_states[];

//==================================================================
//  YORDAMCHI: holat massivi
//==================================================================
int StateIndex(const ulong ticket)
{
   for(int i = 0; i < ArraySize(g_states); i++)
      if(g_states[i].ticket == ticket)
         return i;
   return -1;
}

int StateAdd(const TradeState &st)
{
   int n = ArraySize(g_states);
   ArrayResize(g_states, n + 1);
   g_states[n] = st;
   return n;
}

string GVName(const ulong ticket, const string field)
{
   return StringFormat("SK_%I64u_%s", ticket, field);
}

void StateRemove(const ulong ticket)
{
   int idx = StateIndex(ticket);
   if(idx < 0)
      return;
   int n = ArraySize(g_states);
   for(int i = idx; i < n - 1; i++)
      g_states[i] = g_states[i + 1];
   ArrayResize(g_states, n - 1);
   GlobalVariableDel(GVName(ticket, "R"));
   GlobalVariableDel(GVName(ticket, "RM"));
   GlobalVariableDel(GVName(ticket, "ATR"));
   GlobalVariableDel(GVName(ticket, "TP1"));
   GlobalVariableDel(GVName(ticket, "BE"));
   GlobalVariableDel(GVName(ticket, "BEST"));
}

// Holatni terminal global o'zgaruvchilariga yozadi — terminal qayta
// ishga tushsa ham savdo to'g'ri boshqariladi.
void StatePersist(const int idx)
{
   if(idx < 0 || idx >= ArraySize(g_states))
      return;
   ulong t = g_states[idx].ticket;
   GlobalVariableSet(GVName(t, "R"),    g_states[idx].riskPerUnit);
   GlobalVariableSet(GVName(t, "RM"),   g_states[idx].riskMoney);
   GlobalVariableSet(GVName(t, "ATR"),  g_states[idx].atrAtEntry);
   GlobalVariableSet(GVName(t, "TP1"),  g_states[idx].tp1Done ? 1.0 : 0.0);
   GlobalVariableSet(GVName(t, "BE"),   g_states[idx].beMoved ? 1.0 : 0.0);
   GlobalVariableSet(GVName(t, "BEST"), g_states[idx].bestPrice);
}

void Log(const string message)
{
   if(g_cfg.Verbose)
      Print(message);
}

//==================================================================
//  ISHGA TUSHIRISH
//==================================================================
int ScalpKit_OnInit()
{
   // Timeframe grafikdan olinadi. Parametrlar timeframe'ga bog'liq
   // kalibrlangani uchun mos preset yuklanganini tekshiramiz.
   if(g_cfg.ExpectedTimeframe != PERIOD_CURRENT && Period() != g_cfg.ExpectedTimeframe)
   {
      PrintFormat("XATO: bu preset %s uchun, grafik esa %s. "
                  "Volatilitet chegaralari timeframe'ga bog'liq — mos presetni yuklang "
                  "yoki InpExpectedTimeframe ni PERIOD_CURRENT qiling.",
                  EnumToString((ENUM_TIMEFRAMES)g_cfg.ExpectedTimeframe),
                  EnumToString(Period()));
      return INIT_PARAMETERS_INCORRECT;
   }
   g_tf = Period();

   hEmaFast = iMA(_Symbol, g_tf, g_cfg.EmaFast, 0, MODE_EMA, PRICE_CLOSE);
   hEmaMid  = iMA(_Symbol, g_tf, g_cfg.EmaMid,  0, MODE_EMA, PRICE_CLOSE);
   hEmaSlow = iMA(_Symbol, g_tf, g_cfg.EmaSlow, 0, MODE_EMA, PRICE_CLOSE);
   hAtr     = iATR(_Symbol, g_tf, g_cfg.AtrLen);
   hRsi     = iRSI(_Symbol, g_tf, g_cfg.RsiLen, PRICE_CLOSE);
   hAdx     = iADX(_Symbol, g_tf, g_cfg.AdxLen);
   hHtfEma  = iMA(_Symbol, PERIOD_H1, g_cfg.HtfEma, 0, MODE_EMA, PRICE_CLOSE);
   hTrendEma = iMA(_Symbol, g_tf, g_cfg.TrendLen, 0, MODE_EMA, PRICE_CLOSE);
   hRevRsi   = iRSI(_Symbol, g_tf, g_cfg.RevRsiLen, PRICE_CLOSE);
   hBandMa   = iMA(_Symbol, g_tf, g_cfg.BandLen, 0, MODE_SMA, PRICE_CLOSE);
   hStdDev   = iStdDev(_Symbol, g_tf, g_cfg.BandLen, 0, MODE_SMA, PRICE_CLOSE);

   if(hEmaFast == INVALID_HANDLE || hEmaMid == INVALID_HANDLE ||
      hEmaSlow == INVALID_HANDLE || hAtr == INVALID_HANDLE ||
      hRsi == INVALID_HANDLE || hAdx == INVALID_HANDLE ||
      hHtfEma == INVALID_HANDLE || hTrendEma == INVALID_HANDLE ||
      hRevRsi == INVALID_HANDLE || hBandMa == INVALID_HANDLE ||
      hStdDev == INVALID_HANDLE)
   {
      Print("XATO: indikator handle yaratilmadi. Kod: ", GetLastError());
      return INIT_FAILED;
   }

   Trade.SetExpertMagicNumber(g_cfg.Magic);
   Trade.SetDeviationInPoints(g_cfg.Deviation);
   Trade.SetTypeFillingBySymbol(_Symbol);
   Trade.LogLevel(LOG_LEVEL_ERRORS);

   g_serverUtcOffset = (g_cfg.ServerUtcOffset == -99) ? DetectServerUtcOffset()
                                                   : g_cfg.ServerUtcOffset;
   g_peakEquity      = AccountInfoDouble(ACCOUNT_EQUITY);
   g_dayStartEquity  = g_peakEquity;
   g_currentDay      = 0;
   g_lastBarTime     = 0;

   RecoverExistingPositions();

   PrintFormat("ScalpKit M5 ishga tushdi | %s | magic %I64d | server-UTC farqi %+d soat",
               _Symbol, g_cfg.Magic, g_serverUtcOffset);
   PrintFormat("  Risk %.2f%% | kunlik chegara %.1f%% | maks. xarajat %.2fR",
               g_cfg.RiskPerTrade * 100.0, g_cfg.DailyLossLimit * 100.0, g_cfg.MaxCostR);
   return INIT_SUCCEEDED;
}

void ScalpKit_OnDeinit(const int reason)
{
   IndicatorRelease(hEmaFast);
   IndicatorRelease(hEmaMid);
   IndicatorRelease(hEmaSlow);
   IndicatorRelease(hAtr);
   IndicatorRelease(hRsi);
   IndicatorRelease(hAdx);
   IndicatorRelease(hHtfEma);
   IndicatorRelease(hTrendEma);
   IndicatorRelease(hRevRsi);
   IndicatorRelease(hBandMa);
   IndicatorRelease(hStdDev);
}

//------------------------------------------------------------------
//  Server vaqti va UTC farqi.
//  Seans filtri UTC bo'yicha ishlashi uchun bu farq zarur —
//  Exness serverlari odatda UTC+0 yoki UTC+3 da ishlaydi.
//------------------------------------------------------------------
int DetectServerUtcOffset()
{
   datetime server = TimeCurrent();
   datetime utc    = TimeGMT();
   if(server <= 0 || utc <= 0)
      return 0;
   return (int)MathRound((double)((long)server - (long)utc) / 3600.0);
}

int UtcHourOf(const datetime serverTime)
{
   datetime utc = serverTime - (datetime)(g_serverUtcOffset * 3600);
   MqlDateTime dt;
   TimeToStruct(utc, dt);
   return dt.hour;
}

datetime UtcDayOf(const datetime serverTime)
{
   datetime utc = serverTime - (datetime)(g_serverUtcOffset * 3600);
   MqlDateTime dt;
   TimeToStruct(utc, dt);
   dt.hour = 0; dt.min = 0; dt.sec = 0;
   return StructToTime(dt);
}

//------------------------------------------------------------------
//  HAFTA CHEGARASI
//
//  Ikki xavfni qoplaydi:
//    1. Hafta oxiri gapi — juma kechqurun ochilgan pozitsiya dushanba
//       narx sakragan holda ochiladi va stop ishlamaydi;
//    2. Ochilish spreadi — hafta boshida spread bir necha barobar keng.
//------------------------------------------------------------------
bool IsPastWeekCutoff(const datetime serverTime)
{
   if(!g_cfg.WeekendFlat)
      return false;
   datetime utc = serverTime - (datetime)(g_serverUtcOffset * 3600);
   MqlDateTime dt;
   TimeToStruct(utc, dt);
   int dow = (dt.day_of_week == 0) ? 6 : dt.day_of_week - 1;   // 0 = dushanba
   return (dow == g_cfg.WeekCloseDow && dt.hour >= g_cfg.WeekCloseHourUTC);
}

// Hafta/bayram uzilishidan keyin yetarli bar o'tdimi
bool IsWeekOpenSettled()
{
   if(!g_cfg.WeekendFlat || g_cfg.WeekOpenSkipBars <= 0)
      return true;
   return (g_barsSinceGap >= g_cfg.WeekOpenSkipBars);
}

// Bar vaqtidagi katta uzilishni aniqlaydi (hafta oxiri yoki bayram)
void UpdateWeekGapCounter(const datetime barTime, const datetime prevBarTime)
{
   if(prevBarTime > 0 && (barTime - prevBarTime) > 4 * 3600)
      g_barsSinceGap = 0;
   else if(g_barsSinceGap < 100000)
      g_barsSinceGap++;
}

//------------------------------------------------------------------
//  Terminal qayta ishga tushganda ochiq pozitsiyalarni tiklaydi
//------------------------------------------------------------------
void RecoverExistingPositions()
{
   ArrayResize(g_states, 0);
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != g_cfg.Magic)
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;

      TradeState st;
      st.ticket     = ticket;
      st.positionId = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
      st.side       = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
      st.entryPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      st.entryTime  = (datetime)PositionGetInteger(POSITION_TIME);
      st.entryBar   = 0;
      st.isPending  = false;

      // Avval saqlangan holatdan, bo'lmasa stop masofasidan tiklaymiz
      if(GlobalVariableCheck(GVName(ticket, "R")))
      {
         st.riskPerUnit = GlobalVariableGet(GVName(ticket, "R"));
         st.riskMoney   = GlobalVariableGet(GVName(ticket, "RM"));
         st.atrAtEntry  = GlobalVariableGet(GVName(ticket, "ATR"));
         st.tp1Done     = (GlobalVariableGet(GVName(ticket, "TP1")) > 0.5);
         st.beMoved     = (GlobalVariableGet(GVName(ticket, "BE")) > 0.5);
         st.bestPrice   = GlobalVariableGet(GVName(ticket, "BEST"));
         Log(StringFormat("Holat tiklandi: #%I64u (R=%.2f)", ticket, st.riskPerUnit));
      }
      else
      {
         double sl = PositionGetDouble(POSITION_SL);
         st.riskPerUnit = (sl > 0.0) ? MathAbs(st.entryPrice - sl) : CurrentAtr();
         st.riskMoney   = 0.0;
         st.atrAtEntry  = CurrentAtr();
         st.tp1Done     = false;
         st.beMoved     = false;
         st.bestPrice   = st.entryPrice;
         Log(StringFormat("Holat stopdan tiklandi: #%I64u (R=%.2f)", ticket, st.riskPerUnit));
      }
      if(st.riskPerUnit <= 0.0)
         st.riskPerUnit = CurrentAtr();
      StatePersist(StateAdd(st));
   }
}

//==================================================================
//  INDIKATOR O'QISH
//==================================================================
bool CopyOne(const int handle, const int buffer, const int shift, double &value)
{
   double tmp[];
   if(CopyBuffer(handle, buffer, shift, 1, tmp) < 1)
      return false;
   value = tmp[0];
   return (value != EMPTY_VALUE && MathIsValidNumber(value));
}

bool CopyMany(const int handle, const int buffer, const int shift,
              const int count, double &dest[])
{
   ArrayResize(dest, count);
   ArraySetAsSeries(dest, true);
   return (CopyBuffer(handle, buffer, shift, count, dest) == count);
}

double CurrentAtr()
{
   double v = 0.0;
   return CopyOne(hAtr, 0, 1, v) ? v : 0.0;
}

//==================================================================
//  SIGNAL MANTIQI
//
//  Indekslash: chart indeksi 1 = oxirgi YOPILGAN bar (Python dagi
//  `t` bari). Indeks 0 — hali shakllanayotgan bar, ishlatilmaydi.
//==================================================================
struct SignalResult
{
   int    side;          // +1 long, -1 short, 0 signal yo'q
   double stopPrice;     // strukturaviy stop
   double entryRef;      // limit kirish darajasi
   double atr;
   bool   exitLong;      // strategiyaning o'z chiqish signali (Donchian kanali)
   bool   exitShort;
   double targetPrice;   // dinamik maqsad (mean-reversion uchun; 0 = yo'q)
   string reject;        // qaysi shart bajarilmadi (log uchun)
};

// Hajm z-score: (v[i] - mean) / std, oyna i..i+len-1 (populyatsiya std)
double VolZAt(const long &tv[], const int i, const int len)
{
   if(i + len > ArraySize(tv))
      return 0.0;
   double sum = 0.0;
   for(int k = i; k < i + len; k++)
      sum += (double)tv[k];
   double mean = sum / len;

   double var = 0.0;
   for(int k = i; k < i + len; k++)
   {
      double d = (double)tv[k] - mean;
      var += d * d;
   }
   var /= len;
   double sd = MathSqrt(var);
   if(sd <= 0.0)
      return 0.0;
   return ((double)tv[i] - mean) / sd;
}

//------------------------------------------------------------------
//  DONCHIAN BREAKOUT — swing / trendni kuzatish
//
//  Python dagi `donchian_breakout` bilan bir xil. Asosiy farqi
//  momentum_pullback dan: MAQSAD QO'YILMAYDI. Trend-following foydasi
//  kam sonli juda katta yutuqlardan keladi; 3R da maqsad qo'yish
//  aynan o'sha savdolarni kesib tashlaydi.
//------------------------------------------------------------------
SignalResult BuildSignalDonchian()
{
   SignalResult out;
   out.side = 0; out.stopPrice = 0.0; out.entryRef = 0.0; out.atr = 0.0;
   out.exitLong = false; out.exitShort = false; out.targetPrice = 0.0; out.reject = "";

   const int needBars = g_cfg.EntryLen + g_cfg.CooldownLen + g_cfg.TrendLen + 10;

   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(_Symbol, g_tf, 0, needBars, rates) < needBars)
   {
      out.reject = "barlar yetarli emas";
      return out;
   }

   double atr[], trend[];
   if(!CopyMany(hAtr, 0, 0, needBars, atr) || !CopyMany(hTrendEma, 0, 0, needBars, trend))
   {
      out.reject = "indikator ma'lumoti yo'q";
      return out;
   }

   const int S = 1;                      // oxirgi yopilgan bar
   const double a = atr[S], cl = rates[S].close;
   if(a <= 0.0 || cl <= 0.0)
   {
      out.reject = "ATR yoki narx noto'g'ri";
      return out;
   }
   out.atr = a;

   //---- kanallar: joriy bar kanalni O'ZGARTIRMASLIGI kerak ----
   double upCh = -DBL_MAX, dnCh = DBL_MAX, exUp = -DBL_MAX, exDn = DBL_MAX;
   for(int i = S + 1; i <= S + g_cfg.EntryLen; i++)
   {
      upCh = MathMax(upCh, rates[i].high);
      dnCh = MathMin(dnCh, rates[i].low);
   }
   for(int i = S + 1; i <= S + g_cfg.ExitLen; i++)
   {
      exUp = MathMax(exUp, rates[i].high);
      exDn = MathMin(exDn, rates[i].low);
   }

   //---- chiqish signali (pozitsiya ochiq bo'lsa dvigatel ishlatadi) ----
   out.exitLong  = (cl < exDn);
   out.exitShort = (cl > exUp);

   //---- rejim ----
   double atrPct = a / cl;
   if(atrPct < g_cfg.MinAtrPct || atrPct > g_cfg.MaxAtrPct)
   {
      out.reject = StringFormat("ATR%% oynadan tashqarida (%.4f%%)", atrPct * 100.0);
      return out;
   }
   if(IsPastWeekCutoff(rates[S].time))
   {
      out.reject = "hafta chegarasi";
      return out;
   }
   if(g_cfg.UseSession)
   {
      int h = UtcHourOf(rates[S].time);
      bool inSession = (g_cfg.SessionStartUTC <= g_cfg.SessionEndUTC)
                     ? (h >= g_cfg.SessionStartUTC && h < g_cfg.SessionEndUTC)
                     : (h >= g_cfg.SessionStartUTC || h < g_cfg.SessionEndUTC);
      if(!inSession)
      {
         out.reject = "seansdan tashqarida";
         return out;
      }
   }

   bool trendUp = true, trendDn = true;
   if(g_cfg.RequireTrendFilter)
   {
      trendUp = (cl > trend[S]);
      trendDn = (cl < trend[S]);
   }

   //---- buzilish ----
   bool brokeUp = (cl > upCh);
   bool brokeDn = (cl < dnCh);

   //---- takroriy buzilishga to'siq ----
   // Yon harakatda narx kanalni ketma-ket buzib, har safar zarar keltiradi.
   if(g_cfg.CooldownLen > 0 && (brokeUp || brokeDn))
   {
      for(int i = S + 1; i <= S + g_cfg.CooldownLen; i++)
      {
         double hi = -DBL_MAX, lo = DBL_MAX;
         for(int k = i + 1; k <= i + g_cfg.EntryLen; k++)
         {
            hi = MathMax(hi, rates[k].high);
            lo = MathMin(lo, rates[k].low);
         }
         if(rates[i].close > hi) brokeUp = false;
         if(rates[i].close < lo) brokeDn = false;
      }
   }

   bool longSig  = trendUp && brokeUp  && g_cfg.AllowLong;
   bool shortSig = trendDn && brokeDn && g_cfg.AllowShort;
   if(longSig == shortSig)
   {
      if(!longSig)
         out.reject = "buzilish yo'q";
      return out;
   }

   int side = longSig ? 1 : -1;
   out.side      = side;
   out.stopPrice = cl - side * g_cfg.SlAtrMult * a;
   out.entryRef  = cl;
   return out;
}


SignalResult BuildSignalPullback()
{
   SignalResult out;
   out.side = 0; out.stopPrice = 0.0; out.entryRef = 0.0; out.atr = 0.0;
   out.exitLong = false; out.exitShort = false; out.targetPrice = 0.0; out.reject = "";

   const int needBars = MathMax(g_cfg.DonchianLen + g_cfg.ImpulseLookback + 5,
                       MathMax(g_cfg.VolZLen + g_cfg.ImpulseLookback + 5, 70));

   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(_Symbol, g_tf, 0, needBars, rates) < needBars)
   {
      out.reject = "barlar yetarli emas";
      return out;
   }

   double emaF[], emaM[], emaS[], atr[], rsi[], adx[];
   if(!CopyMany(hEmaFast, 0, 0, needBars, emaF) ||
      !CopyMany(hEmaMid,  0, 0, needBars, emaM) ||
      !CopyMany(hEmaSlow, 0, 0, needBars, emaS) ||
      !CopyMany(hAtr,     0, 0, needBars, atr)  ||
      !CopyMany(hRsi,     0, 0, needBars, rsi)  ||
      !CopyMany(hAdx,     0, 0, needBars, adx))
   {
      out.reject = "indikator ma'lumoti yo'q";
      return out;
   }

   long tv[];
   ArraySetAsSeries(tv, true);
   if(CopyTickVolume(_Symbol, g_tf, 0, needBars, tv) < needBars)
   {
      out.reject = "hajm ma'lumoti yo'q";
      return out;
   }

   const int S = 1;                     // signal bari
   const double a  = atr[S];
   const double cl = rates[S].close;
   if(a <= 0.0 || cl <= 0.0)
   {
      out.reject = "ATR yoki narx noto'g'ri";
      return out;
   }
   out.atr = a;

   //---------------- REJIM ----------------
   double atrPct = a / cl;
   if(atrPct < g_cfg.MinAtrPct || atrPct > g_cfg.MaxAtrPct)
   {
      out.reject = StringFormat("ATR%% oynadan tashqarida (%.4f%%)", atrPct * 100.0);
      return out;
   }
   if(adx[S] < g_cfg.AdxMin)
   {
      out.reject = StringFormat("ADX past (%.1f)", adx[S]);
      return out;
   }
   if(IsPastWeekCutoff(rates[S].time))
   {
      out.reject = "hafta chegarasi — yangi savdo yo'q";
      return out;
   }
   if(!IsWeekOpenSettled())
   {
      out.reject = StringFormat("hafta ochilishi (%d/%d bar)",
                                g_barsSinceGap, g_cfg.WeekOpenSkipBars);
      return out;
   }
   if(g_cfg.UseSession)
   {
      int h = UtcHourOf(rates[S].time);
      bool inSession = (g_cfg.SessionStartUTC <= g_cfg.SessionEndUTC)
                     ? (h >= g_cfg.SessionStartUTC && h < g_cfg.SessionEndUTC)
                     : (h >= g_cfg.SessionStartUTC || h < g_cfg.SessionEndUTC);
      if(!inSession)
      {
         out.reject = StringFormat("seansdan tashqarida (UTC %02d:00)", h);
         return out;
      }
   }

   //---------------- TREND ----------------
   bool trendUp = (emaF[S] > emaM[S] && emaM[S] > emaS[S] && cl > emaS[S]);
   bool trendDn = (emaF[S] < emaM[S] && emaM[S] < emaS[S] && cl < emaS[S]);

   if(g_cfg.RequireHTF)
   {
      double htf[];
      if(!CopyMany(hHtfEma, 0, 0, 3, htf))
      {
         out.reject = "H1 ma'lumoti yo'q";
         return out;
      }
      // Indeks 1 — oxirgi YOPILGAN H1 bar (kelajakka qarash yo'q)
      double htfClose = iClose(_Symbol, PERIOD_H1, 1);
      double slope    = htf[1] - htf[2];
      bool htfBull = (htfClose > htf[1] && slope > 0.0);
      bool htfBear = (htfClose < htf[1] && slope < 0.0);
      trendUp = trendUp && htfBull;
      trendDn = trendDn && htfBear;
   }

   if(!trendUp && !trendDn)
   {
      out.reject = "trend strukturasi mos emas";
      return out;
   }

   //---------------- SETUP: impuls ----------------
   // Python: had_impulse = any(impulse[t-12 .. t-1])  ->  chart 2 .. 13
   // Har bir impuls bari O'Z oldingi Donchian kanaliga nisbatan tekshiriladi
   // (Python dagi dc_high_prev = dc_high.shift(1) bilan bir xil).
   bool hadImpulseUp = false, hadImpulseDn = false;
   for(int i = S + 1; i <= S + g_cfg.ImpulseLookback; i++)
   {
      if(atr[i] <= 0.0)
         continue;
      double bodyAtr = (rates[i].close - rates[i].open) / atr[i];
      double vz      = VolZAt(tv, i, g_cfg.VolZLen);
      bool strongBody = (MathAbs(bodyAtr) >= g_cfg.ImpulseBodyAtr && vz >= g_cfg.ImpulseVolZ);

      // Donchian buzilishi shu bar uchun O'Z oldingi kanaliga nisbatan
      double hiPrev = -DBL_MAX, loPrev = DBL_MAX;
      for(int k = i + 1; k <= i + g_cfg.DonchianLen; k++)
      {
         hiPrev = MathMax(hiPrev, rates[k].high);
         loPrev = MathMin(loPrev, rates[k].low);
      }
      if((strongBody && bodyAtr > 0.0) || rates[i].close > hiPrev)
         hadImpulseUp = true;
      if((strongBody && bodyAtr < 0.0) || rates[i].close < loPrev)
         hadImpulseDn = true;
   }

   //---------------- SETUP: orqaga qaytish ----------------
   bool touchedUp = false, touchedDn = false, rsiDip = false, rsiPop = false;
   for(int i = S; i < S + g_cfg.PullbackLookback; i++)
   {
      if(rates[i].low  <= emaF[i] + g_cfg.TouchAtr * atr[i]) touchedUp = true;
      if(rates[i].high >= emaF[i] - g_cfg.TouchAtr * atr[i]) touchedDn = true;
      if(rsi[i] <= g_cfg.RsiPullbackLong)  rsiDip = true;
      if(rsi[i] >= g_cfg.RsiPullbackShort) rsiPop = true;
   }

   //---------------- TRIGGER ----------------
   double rng = rates[S].high - rates[S].low;
   double closePos = (rng > 0.0) ? (rates[S].close - rates[S].low) / rng : 0.5;
   double volZ = VolZAt(tv, S, g_cfg.VolZLen);

   bool trigUp = (rates[S].close > rates[S + 1].high)
              && (rates[S].close > emaF[S])
              && (rates[S].close > rates[S].open)
              && (closePos >= g_cfg.TriggerClosePos)
              && (volZ >= g_cfg.TriggerVolZ)
              && (rates[S].close <= emaF[S] + g_cfg.MaxExtensionAtr * a);

   bool trigDn = (rates[S].close < rates[S + 1].low)
              && (rates[S].close < emaF[S])
              && (rates[S].close < rates[S].open)
              && (closePos <= 1.0 - g_cfg.TriggerClosePos)
              && (volZ >= g_cfg.TriggerVolZ)
              && (rates[S].close >= emaF[S] - g_cfg.MaxExtensionAtr * a);

   bool longSig  = trendUp && hadImpulseUp && touchedUp && rsiDip && trigUp && g_cfg.AllowLong;
   bool shortSig = trendDn && hadImpulseDn && touchedDn && rsiPop && trigDn && g_cfg.AllowShort;

   if(longSig == shortSig)     // ikkalasi ham yoki hech biri
   {
      if(!longSig)
         out.reject = StringFormat("setup/trigger to'liq emas (imp %d/%d, touch %d/%d, rsi %d/%d, trig %d/%d)",
                                   (int)hadImpulseUp, (int)hadImpulseDn,
                                   (int)touchedUp, (int)touchedDn,
                                   (int)rsiDip, (int)rsiPop,
                                   (int)trigUp, (int)trigDn);
      else
         out.reject = "long va short bir vaqtda — signal berilmaydi";
      return out;
   }

   //---------------- STOP VA KIRISH DARAJASI ----------------
   int side = longSig ? 1 : -1;
   double swing = longSig ? DBL_MAX : -DBL_MAX;
   for(int i = S; i < S + g_cfg.SwingLen; i++)
      swing = longSig ? MathMin(swing, rates[i].low) : MathMax(swing, rates[i].high);

   out.side      = side;
   out.stopPrice = swing - side * g_cfg.SlBufferAtr * a;
   out.entryRef  = rates[S].close - side * g_cfg.EntryOffsetAtr * a;
   return out;
}

//------------------------------------------------------------------
//  RANGE REVERSION — o'rtachaga qaytish (trend strategiyasining aksi)
//
//  Python dagi `range_reversion` bilan bir xil. Ikkita majburiy blok:
//    * SETUP va TRIGGER ajratilgan (bitta barda talab qilish mantiqsiz);
//    * MUKOFOT/RISK filtri — o'rtachagacha masofa stopdan kichik bo'lsa
//      savdo olinmaydi (filtrsiz savdolarning 61 % i shunday chiqardi).
//------------------------------------------------------------------
SignalResult BuildSignalReversion()
{
   SignalResult out;
   out.side = 0; out.stopPrice = 0.0; out.entryRef = 0.0; out.atr = 0.0;
   out.exitLong = false; out.exitShort = false; out.targetPrice = 0.0; out.reject = "";

   const int needBars = MathMax(g_cfg.BandLen + g_cfg.SetupLookback + 5,
                                g_cfg.TrendLen + 10);

   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(_Symbol, g_tf, 0, needBars, rates) < needBars)
   {
      out.reject = "barlar yetarli emas";
      return out;
   }

   double atr[], adx[], trend[], mid[], sd[], rsi[];
   const int span = g_cfg.SetupLookback + 2;
   if(!CopyMany(hAtr, 0, 0, needBars, atr) ||
      !CopyMany(hAdx, 0, 0, span + 1, adx) ||
      !CopyMany(hTrendEma, 0, 0, span + 1, trend) ||
      !CopyMany(hBandMa, 0, 0, span + 1, mid) ||
      !CopyMany(hStdDev, 0, 0, span + 1, sd) ||
      !CopyMany(hRevRsi, 0, 0, span + 1, rsi))
   {
      out.reject = "indikator ma'lumoti yo'q";
      return out;
   }

   const int S = 1;
   const double a = atr[S], cl = rates[S].close;
   if(a <= 0.0 || cl <= 0.0 || sd[S] <= 0.0)
   {
      out.reject = "ATR yoki sigma noto'g'ri";
      return out;
   }
   out.atr = a;

   //---- rejim: yon harakat ----
   double atrPct = a / cl;
   if(atrPct < g_cfg.MinAtrPct || atrPct > g_cfg.MaxAtrPct)
   {
      out.reject = "ATR% oynadan tashqarida";
      return out;
   }
   if(adx[S] >= g_cfg.AdxMax)
   {
      out.reject = StringFormat("ADX yuqori (%.1f) — trend rejimi", adx[S]);
      return out;
   }
   if(MathAbs(cl - trend[S]) >= g_cfg.RangeDevAtr * a)
   {
      out.reject = "uzoq muddatli o'rtachadan juda uzoq";
      return out;
   }
   if(IsPastWeekCutoff(rates[S].time))
   {
      out.reject = "hafta chegarasi";
      return out;
   }
   if(g_cfg.UseSession)
   {
      int h = UtcHourOf(rates[S].time);
      bool inSession = (g_cfg.SessionStartUTC <= g_cfg.SessionEndUTC)
                     ? (h >= g_cfg.SessionStartUTC && h < g_cfg.SessionEndUTC)
                     : (h >= g_cfg.SessionStartUTC || h < g_cfg.SessionEndUTC);
      if(!inSession)
      {
         out.reject = "seansdan tashqarida";
         return out;
      }
   }

   //---- SETUP: oxirgi barlarda chekkaga chiqilganmi ----
   bool setupLow = false, setupHigh = false;
   int from = g_cfg.RequireReversalBar ? S + 1 : S;
   int to   = g_cfg.RequireReversalBar ? S + g_cfg.SetupLookback : S;
   for(int i = from; i <= to; i++)
   {
      if(sd[i] <= 0.0)
         continue;
      double z = (rates[i].close - mid[i]) / sd[i];
      if(z <= -g_cfg.EntryZ && rsi[i] <= g_cfg.RsiOversold)   setupLow = true;
      if(z >=  g_cfg.EntryZ && rsi[i] >= g_cfg.RsiOverbought) setupHigh = true;
   }

   //---- TRIGGER: qaytish bari ----
   bool longSig  = setupLow  && g_cfg.AllowLong;
   bool shortSig = setupHigh && g_cfg.AllowShort;
   if(g_cfg.RequireReversalBar)
   {
      longSig  = longSig  && (rates[S].close > rates[S].open);
      shortSig = shortSig && (rates[S].close < rates[S].open);
   }
   if(longSig == shortSig)
   {
      if(!longSig)
         out.reject = "chekka yoki qaytish bari yo'q";
      return out;
   }

   int side = longSig ? 1 : -1;
   double stop   = cl - side * g_cfg.SlAtrMult * a;
   double target = mid[S];

   //---- MUKOFOT/RISK filtri ----
   // Mukofot ISHORALI o'lchanadi: qaytish bari o'rtachadan o'tib ketsa,
   // maqsad savdo yo'nalishining orqasida qoladi. Modul bilan o'lchaganda
   // bunday savdo filtrdan o'tib ketardi.
   double reward = side * (target - cl);
   double risk   = MathAbs(cl - stop);
   if(reward <= 0.0)
   {
      out.reject = "maqsad noto'g'ri tomonda";
      return out;
   }
   if(risk <= 0.0 || reward < g_cfg.MinTargetR * risk)
   {
      out.reject = StringFormat("mukofot/risk past (%.2f < %.2f)",
                                risk > 0 ? reward / risk : 0.0, g_cfg.MinTargetR);
      return out;
   }

   out.side        = side;
   out.stopPrice   = stop;
   out.entryRef    = cl;
   out.targetPrice = target;
   return out;
}

//------------------------------------------------------------------
//  Strategiya tanlovchisi
//------------------------------------------------------------------
SignalResult BuildSignal()
{
   if(g_cfg.StrategyKind == 1)
      return BuildSignalDonchian();
   if(g_cfg.StrategyKind == 2)
      return BuildSignalReversion();
   return BuildSignalPullback();
}

//==================================================================
//  HAJM VA STOP NORMALLASHTIRISH
//==================================================================
double NormalizeVolume(const double lots)
{
   double vmin  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double vstep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(vstep <= 0.0)
      return 0.0;

   double v = MathFloor(lots / vstep + 1e-9) * vstep;
   v = MathMin(v, vmax);
   // Qadamga qarab yaxlitlash (suzuvchi nuqta xatosini oldini oladi)
   int digits = (int)MathMax(0, MathCeil(-MathLog10(vstep) - 1e-9));
   v = NormalizeDouble(v, digits);
   return (v >= vmin - 1e-9) ? v : 0.0;
}

double MinStopDistance()
{
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   long   level = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   // Chegarada turib qolmaslik uchun bir punkt zaxira
   return ((double)level + 1.0) * point;
}

// SL/TP ni brokerning minimal masofasiga moslaydi (10016 xatosining oldini oladi)
void ClampStops(const int side, const double price, double &sl, double &tp)
{
   int    dg   = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double dist = MinStopDistance();

   if(sl > 0.0)
   {
      double limit = price - side * dist;
      sl = (side > 0) ? MathMin(sl, limit) : MathMax(sl, limit);
      sl = NormalizeDouble(sl, dg);
   }
   if(tp > 0.0)
   {
      double limit = price + side * dist;
      tp = (side > 0) ? MathMax(tp, limit) : MathMin(tp, limit);
      tp = NormalizeDouble(tp, dg);
   }
}

//==================================================================
//  RISK BOSHQARUVI
//==================================================================
void RollDay(const datetime barTime)
{
   datetime day = UtcDayOf(barTime);
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_currentDay != day)
   {
      g_currentDay     = day;
      g_tradesToday    = 0;
      g_dayStartEquity = equity;
   }
   g_peakEquity = MathMax(g_peakEquity, equity);
}

double EffectiveRisk()
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_peakEquity <= 0.0)
      return g_cfg.RiskPerTrade;
   double dd = 1.0 - equity / g_peakEquity;
   return (dd >= g_cfg.HalveRiskDD) ? g_cfg.RiskPerTrade * 0.5 : g_cfg.RiskPerTrade;
}

// Bo'sh satr = savdoga ruxsat bor
string RiskBlockReason()
{
   if(g_barCounter < g_blockUntilBar)
      return StringFormat("tanaffus (yana %d bar)", g_blockUntilBar - g_barCounter);
   if(g_tradesToday >= g_cfg.MaxTradesPerDay)
      return StringFormat("kunlik savdolar chegarasi (%d)", g_cfg.MaxTradesPerDay);

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_dayStartEquity > 0.0)
   {
      double dayPnl = (equity - g_dayStartEquity) / g_dayStartEquity;
      if(dayPnl <= -g_cfg.DailyLossLimit)
         return StringFormat("kunlik zarar chegarasi (%.2f%%)", dayPnl * 100.0);
   }
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))
      return "terminalda savdo o'chirilgan";
   if(!AccountInfoInteger(ACCOUNT_TRADE_ALLOWED))
      return "hisobda savdo o'chirilgan";
   return "";
}

void OnLossRegistered()
{
   g_consecLosses++;
   int cooldown = g_cfg.CooldownBars;
   if(g_consecLosses >= g_cfg.MaxConsecLosses)
   {
      cooldown = g_cfg.StreakCooldown;
      g_consecLosses = 0;
      Log(StringFormat("Ketma-ket zararlar — %d bar tanaffus.", cooldown));
   }
   g_blockUntilBar = g_barCounter + cooldown;
}

//==================================================================
//  YOPILGAN SAVDOLARNI QAYD ETISH
//==================================================================
bool IsOpenPosition(const ulong ticket)
{
   return PositionSelectByTicket(ticket);
}

bool IsPendingOrder(const ulong ticket)
{
   for(int i = OrdersTotal() - 1; i >= 0; i--)
      if(OrderGetTicket(i) == ticket)
         return true;
   return false;
}

// Pozitsiya yopilgach, uning to'liq natijasini tarixdan hisoblaydi
double RealizedProfitOf(const ulong positionId)
{
   if(!HistorySelectByPosition(positionId))
      return 0.0;
   double total = 0.0;
   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
   {
      ulong deal = HistoryDealGetTicket(i);
      if(deal == 0)
         continue;
      total += HistoryDealGetDouble(deal, DEAL_PROFIT)
             + HistoryDealGetDouble(deal, DEAL_SWAP)
             + HistoryDealGetDouble(deal, DEAL_COMMISSION);
   }
   return total;
}

void SyncClosedTrades()
{
   for(int i = ArraySize(g_states) - 1; i >= 0; i--)
   {
      ulong ticket = g_states[i].ticket;
      if(IsOpenPosition(ticket) || IsPendingOrder(ticket))
         continue;

      // Holat bor, lekin na pozitsiya na order — demak yopilgan yoki bekor qilingan
      ulong  posId  = (g_states[i].positionId != 0) ? g_states[i].positionId : ticket;
      double profit = RealizedProfitOf(posId);
      double riskMoney = g_states[i].riskMoney;

      if(riskMoney > 0.0 && MathAbs(profit) > 1e-9)
      {
         double r = profit / riskMoney;
         g_sumR += r;
         g_closedTrades++;
         if(profit > 0.0)
         {
            g_wins++;
            g_consecLosses = 0;
         }
         else
            OnLossRegistered();
         Log(StringFormat("Savdo yopildi #%I64u: %.2f (%.2f R) | jami %d savdo, %.2f R",
                          ticket, profit, r, g_closedTrades, g_sumR));
      }
      StateRemove(ticket);
   }
}

// Holatsiz ochiq pozitsiyani topsa, uni stop masofasidan tiklaydi.
// Limit order pozitsiyaga aylanganda ham shu yo'l ishlaydi.
void AdoptOrphanPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != g_cfg.Magic)
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if(StateIndex(ticket) >= 0)
         continue;

      TradeState st;
      st.ticket     = ticket;
      st.positionId = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
      st.side       = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
      st.entryPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      st.entryTime  = (datetime)PositionGetInteger(POSITION_TIME);
      st.entryBar   = g_barCounter;
      st.isPending  = false;
      st.tp1Done    = false;
      st.beMoved    = false;
      st.bestPrice  = st.entryPrice;
      st.atrAtEntry = CurrentAtr();

      double sl = PositionGetDouble(POSITION_SL);
      // Stop kirishda aynan R masofada qo'yilgani uchun tiklash aniq bo'ladi
      st.riskPerUnit = (sl > 0.0) ? MathAbs(st.entryPrice - sl) : st.atrAtEntry;
      st.riskMoney   = st.riskPerUnit * PositionGetDouble(POSITION_VOLUME)
                     * SymbolInfoDouble(_Symbol, SYMBOL_TRADE_CONTRACT_SIZE);

      StatePersist(StateAdd(st));
      Log(StringFormat("Yangi pozitsiya qabul qilindi #%I64u (R=%.2f, risk=%.2f)",
                       ticket, st.riskPerUnit, st.riskMoney));
   }
}

//==================================================================
//  YANGI SAVDO OCHISH
//==================================================================
void ExpirePendingOrders()
{
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0 || !OrderSelect(ticket))
         continue;
      if(OrderGetInteger(ORDER_MAGIC) != g_cfg.Magic)
         continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;

      datetime placed = (datetime)OrderGetInteger(ORDER_TIME_SETUP);
      int barsOld = (int)((TimeCurrent() - placed) / (PeriodSeconds(g_tf)));
      if(barsOld >= g_cfg.EntryLimitBars)
      {
         if(Trade.OrderDelete(ticket))
         {
            Log(StringFormat("Limit order #%I64u muddati tugadi — bekor qilindi.", ticket));
            StateRemove(ticket);
         }
      }
   }
}

void CancelAllPending()
{
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0 || !OrderSelect(ticket))
         continue;
      if(OrderGetInteger(ORDER_MAGIC) != g_cfg.Magic)
         continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;
      if(Trade.OrderDelete(ticket))
         StateRemove(ticket);
   }
}

void CloseAllPositions(const string reason)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != g_cfg.Magic)
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if(Trade.PositionClose(ticket))
         Log(StringFormat("#%I64u yopildi (%s)", ticket, reason));
   }
}

//==================================================================
//  USHLAB TURISH XARAJATI (SWAP) — SWING UCHUN HAL QILUVCHI
//==================================================================
//  Skalpingda pozitsiya bir necha bar turadi va swap nolga teng.
//  Swing'da esa boshqacha: D1 da o'rtacha ushlash ~18 kun, oltin long
//  uchun swap 0.012 %/kun. Broker hafta oxiri qiymat sanasini bitta
//  kechada undiradi (odatda chorshanba x3), shuning uchun 18 kun ~24
//  kechalik swap to'laydi: 0.29 % notional. D1 stopi 1.28 % bo'lsa, bu
//  0.23 R — spreaddan o'nlab marta katta. Faqat spreadga qaraydigan
//  filtr bu yerda noto'g'ri javob beradi.
//
//  Natija BIRLIK uchun narx birligida qaytariladi (stop masofasi bilan
//  bir xil o'lchov), shuning uchun to'g'ridan-to'g'ri R ga bo'linadi.
//  MUSBAT = xarajat. Daromad (manfiy swap) hisobga OLINMAYDI: filtr
//  ehtiyotkor bo'lishi kerak, daromadni oldindan yozib qo'yish emas.
//------------------------------------------------------------------
double SwapPerUnitPerNight(const int side)
{
   long mode = SymbolInfoInteger(_Symbol, SYMBOL_SWAP_MODE);
   if(mode == SYMBOL_SWAP_MODE_DISABLED)
      return 0.0;

   double raw = (side > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_SWAP_LONG)
                           : SymbolInfoDouble(_Symbol, SYMBOL_SWAP_SHORT);
   if(raw == 0.0)
      return 0.0;

   double cost = -raw;                 // brokerda manfiy = undiriladi
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double contract = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_CONTRACT_SIZE);
   if(contract <= 0.0)
      contract = 1.0;

   switch((int)mode)
   {
      case SYMBOL_SWAP_MODE_POINTS:
         return cost * point;

      // Yillik foiz -> bir kechalik narx ulushi
      case SYMBOL_SWAP_MODE_INTEREST_CURRENT:
      case SYMBOL_SWAP_MODE_INTEREST_OPEN:
         return cost / 100.0 * price / 360.0;

      // Lot uchun pul -> birlik uchun pul
      case SYMBOL_SWAP_MODE_CURRENCY_SYMBOL:
      case SYMBOL_SWAP_MODE_CURRENCY_MARGIN:
      case SYMBOL_SWAP_MODE_CURRENCY_DEPOSIT:
         return cost / contract;

   }

   // REOPEN_* rejimlari pozitsiyani qayta ochish orqali swap oladi — bu
   // yerda modellashtirilmaydi. Nol qaytaramiz va bir marta ogohlantiramiz.
   if(!g_swapModeWarned)
   {
      g_swapModeWarned = true;
      PrintFormat("OGOHLANTIRISH: swap rejimi %d modellashtirilmagan — "
                  "ushlab turish xarajati hisobga olinmaydi.", (int)mode);
   }
   return 0.0;
}

// Kutilgan ushlash davomida to'planadigan swap (birlik uchun, narx birligida).
double ExpectedSwapPerUnit(const int side)
{
   if(!g_cfg.ApplySwapCost || g_cfg.ExpectedHoldDays <= 0.0)
      return 0.0;

   double perNight = SwapPerUnitPerNight(side);
   if(perNight <= 0.0)
      return 0.0;                       // daromadni hisobga olmaymiz

   // Uch baravar rollover: haftada bir kecha x3, ya'ni 7 kunda 9 birlik.
   // Python tomonida `swap_units()` aynan shu hisobni aniq sanaydi.
   double units = g_cfg.ExpectedHoldDays * (9.0 / 7.0);
   return perNight * units;
}

void TryOpen(const SignalResult &sig)
{
   double a = sig.atr;
   if(a <= 0.0)
      return;

   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double spread = ask - bid;
   if(bid <= 0.0 || ask <= 0.0)
      return;

   double entry = g_cfg.UseLimitEntry ? sig.entryRef : ((sig.side > 0) ? ask : bid);

   //--- stop masofasi: struktura -> ATR chegarasi -> foiz chegarasi
   double dist = sig.side * (entry - sig.stopPrice);
   dist = MathMax(dist, g_cfg.MinSlAtr * a);
   dist = MathMin(dist, g_cfg.MaxSlAtr * a);
   dist = MathMax(dist, g_cfg.MinStopPct * entry);
   dist = MathMin(dist, g_cfg.MaxStopPct * entry);
   if(dist <= 0.0)
      return;

   //--- XARAJAT HIMOYASI
   // To'liq savdo BIR spread turadi: ask'da olib, bid'da sotasiz.
   // Swing'da bunga ushlab turish (swap) xarajati qo'shiladi.
   double swapCost = ExpectedSwapPerUnit(sig.side);
   double costR    = (spread + swapCost) / dist;
   if(costR > g_cfg.MaxCostR)
   {
      Log(StringFormat("Savdo o'tkazib yuborildi: xarajat %.3fR > %.2fR "
                       "(spread %.2f, swap %.2f / %.1f kun, stop %.2f)",
                       costR, g_cfg.MaxCostR, spread, swapCost,
                       g_cfg.ExpectedHoldDays, dist));
      return;
   }

   //--- hajm
   double equity   = AccountInfoDouble(ACCOUNT_EQUITY);
   double contract = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_CONTRACT_SIZE);
   if(contract <= 0.0)
      contract = 1.0;

   double riskMoney = equity * EffectiveRisk();
   double units     = riskMoney / dist;
   double lots      = NormalizeVolume(units / contract);
   if(lots <= 0.0)
   {
      Log(StringFormat("Savdo o'tkazib yuborildi: hajm minimal lotdan kichik (%.4f)",
                       units / contract));
      return;
   }

   double actualRisk = lots * contract * dist;
   if(actualRisk > riskMoney * 1.5)
   {
      Log(StringFormat("Savdo o'tkazib yuborildi: minimal lot juda katta risk beradi "
                       "(%.2f > %.2f)", actualRisk, riskMoney));
      return;
   }

   double leverage = (lots * contract * entry) / MathMax(equity, 1e-9);
   if(leverage > g_cfg.MaxLeverage)
   {
      Log(StringFormat("Savdo o'tkazib yuborildi: leverage %.1fx > %.1fx",
                       leverage, g_cfg.MaxLeverage));
      return;
   }

   //--- SL / TP
   int dg = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   entry  = NormalizeDouble(entry, dg);
   double sl = entry - sig.side * dist;
   // Dinamik maqsad (mean-reversion) berilgan bo'lsa uni ishlatamiz,
   // aks holda qat'iy R ko'paytmasi. Tp2R = 0 => maqsad umuman yo'q
   // (trendni kuzatishda dumni kesmaslik uchun).
   double tp = 0.0;
   if(sig.targetPrice > 0.0)
      tp = sig.targetPrice;
   else if(g_cfg.Tp2R > 0.0)
      tp = entry + sig.side * g_cfg.Tp2R * dist;
   ClampStops(sig.side, entry, sl, tp);

   string dir = (sig.side > 0) ? "LONG" : "SHORT";
   PrintFormat("%s %s | kirish %.*f (%s) | stop %.*f | TP %.*f | %.2f lot | "
               "risk %.2f (%.2f%%) | xarajat %.3fR",
               dir, _Symbol, dg, entry, g_cfg.UseLimitEntry ? "limit" : "market",
               dg, sl, dg, tp, lots, actualRisk,
               actualRisk / MathMax(equity, 1e-9) * 100.0, costR);

   bool ok = false;
   ulong ticket = 0;
   if(g_cfg.UseLimitEntry)
   {
      datetime expiry = TimeCurrent() + g_cfg.EntryLimitBars * PeriodSeconds(g_tf);
      ok = (sig.side > 0)
         ? Trade.BuyLimit(lots, entry, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "scalpkit")
         : Trade.SellLimit(lots, entry, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "scalpkit");
      if(!ok)
      {
         // Ba'zi brokerlar ORDER_TIME_SPECIFIED ni qo'llab-quvvatlamaydi —
         // GTC bilan qo'yamiz, muddatni EA o'zi kuzatadi
         ok = (sig.side > 0)
            ? Trade.BuyLimit(lots, entry, _Symbol, sl, tp, ORDER_TIME_GTC, 0, "scalpkit")
            : Trade.SellLimit(lots, entry, _Symbol, sl, tp, ORDER_TIME_GTC, 0, "scalpkit");
      }
   }
   else
   {
      ok = (sig.side > 0)
         ? Trade.Buy(lots, _Symbol, 0.0, sl, tp, "scalpkit")
         : Trade.Sell(lots, _Symbol, 0.0, sl, tp, "scalpkit");
   }

   if(!ok)
   {
      PrintFormat("ORDER RAD ETILDI: retcode=%d (%s)",
                  Trade.ResultRetcode(), Trade.ResultRetcodeDescription());
      return;
   }

   ticket = Trade.ResultOrder();
   if(ticket == 0)
      ticket = Trade.ResultDeal();

   TradeState st;
   st.ticket      = ticket;
   st.positionId  = ticket;   // limit to'ldirilgach AdoptOrphanPositions aniqlashtiradi
   st.side        = sig.side;
   st.entryPrice  = entry;
   st.riskPerUnit = dist;
   st.riskMoney   = actualRisk;
   st.atrAtEntry  = a;
   st.bestPrice   = entry;
   st.entryTime   = TimeCurrent();
   st.entryBar    = g_barCounter;
   st.tp1Done     = false;
   st.beMoved     = false;
   st.isPending   = g_cfg.UseLimitEntry;
   StatePersist(StateAdd(st));

   g_tradesToday++;
}

//==================================================================
//  OCHIQ POZITSIYALARNI BOSHQARISH
//==================================================================
// Stopni suradi va HAQIQIY qo'yilgan darajani `applied` ga yozadi.
// Bu muhim: ClampStops broker chegarasiga qarab darajani o'zgartirishi
// mumkin, va keyingi taqqoslashlar eski qiymatga tayansa xato bo'ladi.
bool MoveStop(const ulong ticket, const int side, const double target,
              const double currentSl, const string why, double &applied)
{
   applied = currentSl;
   // Stop faqat foydali yo'nalishda suriladi
   bool better = (side > 0) ? (target > currentSl) : (target < currentSl);
   if(currentSl > 0.0 && !better)
      return false;

   if(!PositionSelectByTicket(ticket))
      return false;
   double price = (side > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                             : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double sl = target;
   double tp = PositionGetDouble(POSITION_TP);
   ClampStops(side, price, sl, tp);

   if(!Trade.PositionModify(ticket, sl, tp))
   {
      Log(StringFormat("#%I64u stopni surib bo'lmadi (%s): retcode=%d",
                       ticket, why, Trade.ResultRetcode()));
      return false;
   }
   // Brokerda haqiqatda qanday saqlanganini o'qib olamiz
   if(PositionSelectByTicket(ticket))
      applied = PositionGetDouble(POSITION_SL);
   else
      applied = sl;
   Log(StringFormat("#%I64u stop -> %.*f (%s)",
                    ticket, (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS), applied, why));
   return true;
}

void ManagePositions()
{
   for(int i = ArraySize(g_states) - 1; i >= 0; i--)
   {
      ulong ticket = g_states[i].ticket;
      if(!PositionSelectByTicket(ticket))
         continue;

      int    side   = g_states[i].side;
      double R      = g_states[i].riskPerUnit;
      double entry  = g_states[i].entryPrice;
      double atr0   = g_states[i].atrAtEntry;
      double volume = PositionGetDouble(POSITION_VOLUME);
      double sl     = PositionGetDouble(POSITION_SL);
      if(R <= 0.0)
         continue;

      double price = (side > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                                : SymbolInfoDouble(_Symbol, SYMBOL_ASK);

      g_states[i].bestPrice = (side > 0) ? MathMax(g_states[i].bestPrice, price)
                                         : MathMin(g_states[i].bestPrice, price);
      double moveR = side * (g_states[i].bestPrice - entry) / R;
      double nowR  = side * (price - entry) / R;

      //--- TP1: qisman yopish
      if(!g_states[i].tp1Done && nowR >= g_cfg.Tp1R)
      {
         double part = NormalizeVolume(volume * g_cfg.Tp1Fraction);
         double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
         if(part > 0.0 && (volume - part) >= vmin - 1e-9)
         {
            if(Trade.PositionClosePartial(ticket, part))
            {
               g_states[i].tp1Done = true;
               Log(StringFormat("#%I64u TP1 (+%.2fR): %.2f lot yopildi.", ticket, nowR, part));
            }
         }
         else
         {
            // Hajm bo'linmaydi — TP1 o'tkazib yuboriladi, trailing ishlaydi
            g_states[i].tp1Done = true;
            Log(StringFormat("#%I64u TP1 o'tkazib yuborildi (hajm bo'linmaydi).", ticket));
         }
         // TP1 dan keyin stop -0.35R ga (zararsizlikka EMAS)
         double appliedSl = sl;
         if(MoveStop(ticket, side, entry + side * g_cfg.Tp1StopToR * R, sl, "tp1_stop", appliedSl))
            sl = appliedSl;
         StatePersist(i);
      }

      //--- zararsizlikka o'tish (faqat +2R dan keyin)
      if(!g_states[i].beMoved && moveR >= g_cfg.BeTriggerR)
      {
         double spread = SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                       - SymbolInfoDouble(_Symbol, SYMBOL_BID);
         double target = entry + side * (g_cfg.BeOffsetR * R + spread);
         double appliedBe = sl;
         if(MoveStop(ticket, side, target, sl, "breakeven", appliedBe))
         {
            g_states[i].beMoved = true;
            sl = appliedBe;
            StatePersist(i);
         }
      }

      //--- trailing (mayda qadamlarda surilmaydi)
      if(moveR >= g_cfg.TrailAfterR && atr0 > 0.0)
      {
         double trail = g_states[i].bestPrice - side * g_cfg.TrailAtrMult * atr0;
         double minStep = g_cfg.TrailMinStepAtr * atr0;
         if(sl <= 0.0 || MathAbs(trail - sl) >= minStep)
         {
            double appliedTrail = sl;
            if(MoveStop(ticket, side, trail, sl, "trailing", appliedTrail))
            {
               sl = appliedTrail;
               StatePersist(i);
            }
         }
      }

      //--- vaqt stopi: faqat hech qayoqqa ketmagan savdolar
      datetime openTime = (datetime)PositionGetInteger(POSITION_TIME);
      int barsHeld = (int)((TimeCurrent() - openTime) / PeriodSeconds(g_tf));
      if(barsHeld >= g_cfg.TimeStopBars && moveR < g_cfg.TimeStopMinR)
      {
         if(Trade.PositionClose(ticket))
         {
            Log(StringFormat("#%I64u vaqt stopi (%d bar, %+.2fR) — yopildi.",
                             ticket, barsHeld, nowR));
            continue;
         }
      }

      //--- strategiyaning o'z chiqish signali (Donchian kanali)
      if((side > 0 && g_exitLong) || (side < 0 && g_exitShort))
      {
         if(Trade.PositionClose(ticket))
         {
            Log(StringFormat("#%I64u strategiya chiqish signali (%+.2fR) — yopildi.",
                             ticket, nowR));
            continue;
         }
      }

      //--- TP1 dan keyin EMA21 chiqishi
      if(g_cfg.ExitOnEmaCross && g_states[i].tp1Done)
      {
         double emaF = 0.0;
         if(CopyOne(hEmaFast, 0, 1, emaF))
         {
            double closeBar = iClose(_Symbol, g_tf, 1);
            if((side > 0 && closeBar < emaF) || (side < 0 && closeBar > emaF))
            {
               if(Trade.PositionClose(ticket))
               {
                  Log(StringFormat("#%I64u EMA21 chiqishi (%+.2fR) — yopildi.", ticket, nowR));
                  continue;
               }
            }
         }
      }
      StatePersist(i);
   }
}

//==================================================================
//  ASOSIY SIKL
//==================================================================
bool IsNewBar()
{
   datetime t = iTime(_Symbol, g_tf, 0);
   if(t == 0 || t == g_lastBarTime)
      return false;
   g_lastBarTime = t;
   return true;
}

bool HasOpenExposure()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket != 0 && PositionSelectByTicket(ticket)
         && PositionGetInteger(POSITION_MAGIC) == g_cfg.Magic
         && PositionGetString(POSITION_SYMBOL) == _Symbol)
         return true;
   }
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket != 0 && OrderSelect(ticket)
         && OrderGetInteger(ORDER_MAGIC) == g_cfg.Magic
         && OrderGetString(ORDER_SYMBOL) == _Symbol)
         return true;
   }
   return false;
}

void ScalpKit_OnTick()
{
   // Ochiq pozitsiyalar har tikda kuzatiladi — TP1, trailing va
   // zararsizlik bar yopilishini kutmaydi.
   AdoptOrphanPositions();
   ManagePositions();

   // Signal esa FAQAT yopilgan barda hisoblanadi.
   if(!IsNewBar())
      return;

   g_barCounter++;
   UpdateWeekGapCounter(iTime(_Symbol, g_tf, 0), iTime(_Symbol, g_tf, 1));
   SyncClosedTrades();
   ExpirePendingOrders();
   RollDay(iTime(_Symbol, g_tf, 1));

   // Hafta chegarasi: kutayotgan orderlarni bekor qilib, pozitsiyani yopamiz.
   // Bu KIRISH nuqtasida tekshiriladi — signal juma 18:55 da ruxsat etilgan
   // bo'lishi mumkin, lekin limit 19:00 dan keyin to'ldirilsa, pozitsiya
   // hafta oxiriga qolib ketadi.
   if(IsPastWeekCutoff(TimeCurrent()))
   {
      CancelAllPending();
      CloseAllPositions("weekend_flat");
      return;
   }

   // Signalni bir marta hisoblab, chiqish bayroqlarini yangilaymiz —
   // ular ochiq pozitsiyani boshqarishda ishlatiladi.
   SignalResult bar = BuildSignal();
   g_exitLong  = bar.exitLong;
   g_exitShort = bar.exitShort;

   if(HasOpenExposure())
   {
      ManagePositions();      // yangi chiqish bayrog'ini darhol qo'llaymiz
      return;
   }

   string blocked = RiskBlockReason();
   if(blocked != "")
   {
      if(bar.side != 0)
         Log("SIGNAL BOR, lekin bloklangan: " + blocked);
      return;
   }

   if(bar.side == 0)
      return;

   TryOpen(bar);
}

//==================================================================
//  STRATEGY TESTER MEZONI
//
//  Optimizatsiyada "Custom max" tanlansa shu qiymat maksimallashtiriladi.
//  Python dagi `expectancy` mezoni bilan bir xil:
//      ekspektatsiya (R) x sqrt(savdolar soni)
//  Kam savdoli tasodifiy natijalar jazolanadi.
//==================================================================
double ScalpKit_OnTester()
{
   if(g_closedTrades < 20)
      return -1000.0;
   double expectancy = g_sumR / g_closedTrades;
   return expectancy * MathSqrt((double)g_closedTrades);
}

//==================================================================
//  TEST YAKUNIDA XULOSA
//==================================================================
void ScalpKit_OnTesterDeinit()
{
   if(g_closedTrades <= 0)
   {
      Print("ScalpKit: savdo bo'lmadi.");
      return;
   }
   double expectancy = g_sumR / g_closedTrades;
   double winRate    = 100.0 * g_wins / g_closedTrades;
   PrintFormat("ScalpKit yakuni: %d savdo | ekspektatsiya %+.3f R | "
               "g'alaba %.1f%% | jami %+.1f R",
               g_closedTrades, expectancy, winRate, g_sumR);
}
//+------------------------------------------------------------------+
