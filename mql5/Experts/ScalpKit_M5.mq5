//+------------------------------------------------------------------+
//|                                                 ScalpKit_M5.mq5  |
//|         BTC/USD M5 "Momentum Pullback" — tanlab-skalping EA      |
//|                                                                  |
//|  Python versiyasi (scalpkit) bilan bir xil mantiq:               |
//|    * rejim filtrlari -> setup -> trigger                         |
//|    * limit kirish, 3 bar amal qiladi                             |
//|    * TP1 +1.5R da 35 %, stop -0.35R ga (zararsizlikka EMAS)      |
//|    * +2R da zararsizlik, +1.5R dan keyin 2.5 ATR trailing        |
//|    * vaqt stopi faqat turg'un savdolarga                         |
//|    * 0.5 % risk, kunlik zarar chegarasi, tanaffuslar             |
//|    * spread keng bo'lsa savdo qilmaydi (xarajat > 0.40R)         |
//|                                                                  |
//|  MUHIM: signal faqat YOPILGAN barda hisoblanadi.                 |
//+------------------------------------------------------------------+
#property copyright "scalpkit"
#property link      "https://github.com/rriskavan-crypto/scalp"
#property version   "1.00"
#property description "M5 Momentum Pullback — tanlab-skalping (BTCUSD)"

#include <Trade\Trade.mqh>

//==================================================================
//  KIRISH PARAMETRLARI
//==================================================================
input group "=== Rejim filtrlari ==="
input double InpMinAtrPct        = 0.0020;  // ATR% minimal (0.0020 = 0.20 %)
input double InpMaxAtrPct        = 0.0120;  // ATR% maksimal
input double InpAdxMin           = 20.0;    // ADX minimal
input bool   InpRequireHTF       = true;    // H1 yo'nalishi mos bo'lsin
input bool   InpUseSession       = true;    // Seans filtri
input int    InpSessionStartUTC  = 6;       // Seans boshi (UTC soat)
input int    InpSessionEndUTC    = 22;      // Seans oxiri (UTC soat)

input group "=== Setup ==="
input int    InpImpulseLookback  = 12;      // Impuls oynasi (bar)
input double InpImpulseBodyAtr   = 0.8;     // Impuls tanasi (ATR)
input double InpImpulseVolZ      = 1.0;     // Impuls hajmi (z-score)
input int    InpPullbackLookback = 4;       // Qaytish oynasi (bar)
input double InpTouchAtr         = 0.25;    // EMA21 ga tegish zonasi (ATR)
input double InpRsiPullbackLong  = 45.0;    // RSI long uchun
input double InpRsiPullbackShort = 55.0;    // RSI short uchun

input group "=== Trigger ==="
input double InpTriggerVolZ      = -0.2;    // Trigger hajmi (z-score)
input double InpTriggerClosePos  = 0.5;     // Bar ichida yopilish o'rni
input double InpMaxExtensionAtr  = 1.0;     // EMA21 dan maks. uzoqlik (ATR)

input group "=== Kirish ==="
input bool   InpUseLimitEntry    = true;    // Limit order (false = market)
input double InpEntryOffsetAtr   = 0.15;    // Limit siljishi (ATR)
input int    InpEntryLimitBars   = 3;       // Limit amal qilish muddati (bar)

input group "=== Stop ==="
input int    InpSwingLen         = 5;       // Swing oynasi (bar)
input double InpSlBufferAtr      = 0.25;    // Swing dan zaxira (ATR)
input double InpMinSlAtr         = 1.0;     // Stop minimal (ATR)
input double InpMaxSlAtr         = 2.2;     // Stop maksimal (ATR)
input double InpMinStopPct       = 0.0015;  // Stop minimal (narx %)
input double InpMaxStopPct       = 0.0200;  // Stop maksimal (narx %)

input group "=== Chiqish (yutuqlar cheklanmaydi) ==="
input double InpTp1R             = 1.5;     // TP1 (R)
input double InpTp1Fraction      = 0.35;    // TP1 da yopiladigan ulush
input double InpTp2R             = 3.5;     // TP2 (R)
input double InpTp1StopToR       = -0.35;   // TP1 dan keyin stop (R)
input double InpBeTriggerR       = 2.0;     // Zararsizlikka o'tish (R)
input double InpBeOffsetR        = 0.05;    // Zararsizlik zaxirasi (R)
input double InpTrailAfterR      = 1.5;     // Trailing boshlanishi (R)
input double InpTrailAtrMult     = 2.5;     // Trailing masofasi (ATR)
input double InpTrailMinStepAtr  = 0.15;    // Trailing minimal qadami (ATR)
input int    InpTimeStopBars     = 24;      // Vaqt stopi (bar)
input double InpTimeStopMinR     = 0.5;     // Vaqt stopi shu R gacha
input bool   InpExitOnEmaCross   = true;    // TP1 dan keyin EMA21 chiqishi

input group "=== Risk ==="
input double InpRiskPerTrade     = 0.005;   // Savdo boshiga risk (0.005 = 0.5 %)
input double InpMaxLeverage      = 5.0;     // Maksimal leverage
input int    InpMaxTradesPerDay  = 8;       // Kunlik savdolar chegarasi
input double InpDailyLossLimit   = 0.03;    // Kunlik zarar chegarasi
input int    InpMaxConsecLosses  = 3;       // Ketma-ket zararlar
input int    InpCooldownBars     = 6;       // Zarardan keyin tanaffus (bar)
input int    InpStreakCooldown   = 24;      // Seriyadan keyin tanaffus (bar)
input double InpHalveRiskDD      = 0.08;    // Shu drawdownda risk yarmiga

input group "=== Xarajat himoyasi ==="
input double InpMaxCostR         = 0.40;    // Xarajat shundan oshsa savdo yo'q

input group "=== Texnik ==="
input int    InpEmaFast          = 21;
input int    InpEmaMid           = 55;
input int    InpEmaSlow          = 200;
input int    InpAtrLen           = 14;
input int    InpRsiLen           = 7;
input int    InpAdxLen           = 14;
input int    InpDonchianLen      = 20;
input int    InpVolZLen          = 50;
input int    InpHtfEma           = 50;
input long   InpMagic            = 20260905; // Magic raqam
input int    InpDeviation        = 30;       // Maks. sirpanish (punkt)
input int    InpServerUtcOffset  = -99;      // Server-UTC farqi (soat), -99 = avto
input bool   InpVerbose          = true;     // Batafsil log

//==================================================================
//  GLOBAL HOLAT
//==================================================================
CTrade   Trade;

int      hEmaFast = INVALID_HANDLE, hEmaMid = INVALID_HANDLE, hEmaSlow = INVALID_HANDLE;
int      hAtr = INVALID_HANDLE, hRsi = INVALID_HANDLE, hAdx = INVALID_HANDLE;
int      hHtfEma = INVALID_HANDLE;

datetime g_lastBarTime = 0;
int      g_serverUtcOffset = 0;
int      g_barCounter = 0;          // tanaffuslarni sanash uchun
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
   if(InpVerbose)
      Print(message);
}

//==================================================================
//  ISHGA TUSHIRISH
//==================================================================
int OnInit()
{
   if(Period() != PERIOD_M5)
      Print("OGOHLANTIRISH: EA M5 uchun mo'ljallangan, joriy TF = ", EnumToString(Period()));

   hEmaFast = iMA(_Symbol, PERIOD_M5, InpEmaFast, 0, MODE_EMA, PRICE_CLOSE);
   hEmaMid  = iMA(_Symbol, PERIOD_M5, InpEmaMid,  0, MODE_EMA, PRICE_CLOSE);
   hEmaSlow = iMA(_Symbol, PERIOD_M5, InpEmaSlow, 0, MODE_EMA, PRICE_CLOSE);
   hAtr     = iATR(_Symbol, PERIOD_M5, InpAtrLen);
   hRsi     = iRSI(_Symbol, PERIOD_M5, InpRsiLen, PRICE_CLOSE);
   hAdx     = iADX(_Symbol, PERIOD_M5, InpAdxLen);
   hHtfEma  = iMA(_Symbol, PERIOD_H1, InpHtfEma, 0, MODE_EMA, PRICE_CLOSE);

   if(hEmaFast == INVALID_HANDLE || hEmaMid == INVALID_HANDLE ||
      hEmaSlow == INVALID_HANDLE || hAtr == INVALID_HANDLE ||
      hRsi == INVALID_HANDLE || hAdx == INVALID_HANDLE || hHtfEma == INVALID_HANDLE)
   {
      Print("XATO: indikator handle yaratilmadi. Kod: ", GetLastError());
      return INIT_FAILED;
   }

   Trade.SetExpertMagicNumber(InpMagic);
   Trade.SetDeviationInPoints(InpDeviation);
   Trade.SetTypeFillingBySymbol(_Symbol);
   Trade.LogLevel(LOG_LEVEL_ERRORS);

   g_serverUtcOffset = (InpServerUtcOffset == -99) ? DetectServerUtcOffset()
                                                   : InpServerUtcOffset;
   g_peakEquity      = AccountInfoDouble(ACCOUNT_EQUITY);
   g_dayStartEquity  = g_peakEquity;
   g_currentDay      = 0;
   g_lastBarTime     = 0;

   RecoverExistingPositions();

   PrintFormat("ScalpKit M5 ishga tushdi | %s | magic %I64d | server-UTC farqi %+d soat",
               _Symbol, InpMagic, g_serverUtcOffset);
   PrintFormat("  Risk %.2f%% | kunlik chegara %.1f%% | maks. xarajat %.2fR",
               InpRiskPerTrade * 100.0, InpDailyLossLimit * 100.0, InpMaxCostR);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   IndicatorRelease(hEmaFast);
   IndicatorRelease(hEmaMid);
   IndicatorRelease(hEmaSlow);
   IndicatorRelease(hAtr);
   IndicatorRelease(hRsi);
   IndicatorRelease(hAdx);
   IndicatorRelease(hHtfEma);
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
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic)
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

SignalResult BuildSignal()
{
   SignalResult out;
   out.side = 0; out.stopPrice = 0.0; out.entryRef = 0.0; out.atr = 0.0; out.reject = "";

   const int needBars = MathMax(InpDonchianLen + InpImpulseLookback + 5,
                       MathMax(InpVolZLen + InpImpulseLookback + 5, 70));

   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(_Symbol, PERIOD_M5, 0, needBars, rates) < needBars)
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
   if(CopyTickVolume(_Symbol, PERIOD_M5, 0, needBars, tv) < needBars)
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
   if(atrPct < InpMinAtrPct || atrPct > InpMaxAtrPct)
   {
      out.reject = StringFormat("ATR%% oynadan tashqarida (%.4f%%)", atrPct * 100.0);
      return out;
   }
   if(adx[S] < InpAdxMin)
   {
      out.reject = StringFormat("ADX past (%.1f)", adx[S]);
      return out;
   }
   if(InpUseSession)
   {
      int h = UtcHourOf(rates[S].time);
      bool inSession = (InpSessionStartUTC <= InpSessionEndUTC)
                     ? (h >= InpSessionStartUTC && h < InpSessionEndUTC)
                     : (h >= InpSessionStartUTC || h < InpSessionEndUTC);
      if(!inSession)
      {
         out.reject = StringFormat("seansdan tashqarida (UTC %02d:00)", h);
         return out;
      }
   }

   //---------------- TREND ----------------
   bool trendUp = (emaF[S] > emaM[S] && emaM[S] > emaS[S] && cl > emaS[S]);
   bool trendDn = (emaF[S] < emaM[S] && emaM[S] < emaS[S] && cl < emaS[S]);

   if(InpRequireHTF)
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
   for(int i = S + 1; i <= S + InpImpulseLookback; i++)
   {
      if(atr[i] <= 0.0)
         continue;
      double bodyAtr = (rates[i].close - rates[i].open) / atr[i];
      double vz      = VolZAt(tv, i, InpVolZLen);
      bool strongBody = (MathAbs(bodyAtr) >= InpImpulseBodyAtr && vz >= InpImpulseVolZ);

      // Donchian buzilishi shu bar uchun O'Z oldingi kanaliga nisbatan
      double hiPrev = -DBL_MAX, loPrev = DBL_MAX;
      for(int k = i + 1; k <= i + InpDonchianLen; k++)
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
   for(int i = S; i < S + InpPullbackLookback; i++)
   {
      if(rates[i].low  <= emaF[i] + InpTouchAtr * atr[i]) touchedUp = true;
      if(rates[i].high >= emaF[i] - InpTouchAtr * atr[i]) touchedDn = true;
      if(rsi[i] <= InpRsiPullbackLong)  rsiDip = true;
      if(rsi[i] >= InpRsiPullbackShort) rsiPop = true;
   }

   //---------------- TRIGGER ----------------
   double rng = rates[S].high - rates[S].low;
   double closePos = (rng > 0.0) ? (rates[S].close - rates[S].low) / rng : 0.5;
   double volZ = VolZAt(tv, S, InpVolZLen);

   bool trigUp = (rates[S].close > rates[S + 1].high)
              && (rates[S].close > emaF[S])
              && (rates[S].close > rates[S].open)
              && (closePos >= InpTriggerClosePos)
              && (volZ >= InpTriggerVolZ)
              && (rates[S].close <= emaF[S] + InpMaxExtensionAtr * a);

   bool trigDn = (rates[S].close < rates[S + 1].low)
              && (rates[S].close < emaF[S])
              && (rates[S].close < rates[S].open)
              && (closePos <= 1.0 - InpTriggerClosePos)
              && (volZ >= InpTriggerVolZ)
              && (rates[S].close >= emaF[S] - InpMaxExtensionAtr * a);

   bool longSig  = trendUp && hadImpulseUp && touchedUp && rsiDip && trigUp;
   bool shortSig = trendDn && hadImpulseDn && touchedDn && rsiPop && trigDn;

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
   for(int i = S; i < S + InpSwingLen; i++)
      swing = longSig ? MathMin(swing, rates[i].low) : MathMax(swing, rates[i].high);

   out.side      = side;
   out.stopPrice = swing - side * InpSlBufferAtr * a;
   out.entryRef  = rates[S].close - side * InpEntryOffsetAtr * a;
   return out;
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
      return InpRiskPerTrade;
   double dd = 1.0 - equity / g_peakEquity;
   return (dd >= InpHalveRiskDD) ? InpRiskPerTrade * 0.5 : InpRiskPerTrade;
}

// Bo'sh satr = savdoga ruxsat bor
string RiskBlockReason()
{
   if(g_barCounter < g_blockUntilBar)
      return StringFormat("tanaffus (yana %d bar)", g_blockUntilBar - g_barCounter);
   if(g_tradesToday >= InpMaxTradesPerDay)
      return StringFormat("kunlik savdolar chegarasi (%d)", InpMaxTradesPerDay);

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_dayStartEquity > 0.0)
   {
      double dayPnl = (equity - g_dayStartEquity) / g_dayStartEquity;
      if(dayPnl <= -InpDailyLossLimit)
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
   int cooldown = InpCooldownBars;
   if(g_consecLosses >= InpMaxConsecLosses)
   {
      cooldown = InpStreakCooldown;
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
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic)
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
      if(OrderGetInteger(ORDER_MAGIC) != InpMagic)
         continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;

      datetime placed = (datetime)OrderGetInteger(ORDER_TIME_SETUP);
      int barsOld = (int)((TimeCurrent() - placed) / (PeriodSeconds(PERIOD_M5)));
      if(barsOld >= InpEntryLimitBars)
      {
         if(Trade.OrderDelete(ticket))
         {
            Log(StringFormat("Limit order #%I64u muddati tugadi — bekor qilindi.", ticket));
            StateRemove(ticket);
         }
      }
   }
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

   double entry = InpUseLimitEntry ? sig.entryRef : ((sig.side > 0) ? ask : bid);

   //--- stop masofasi: struktura -> ATR chegarasi -> foiz chegarasi
   double dist = sig.side * (entry - sig.stopPrice);
   dist = MathMax(dist, InpMinSlAtr * a);
   dist = MathMin(dist, InpMaxSlAtr * a);
   dist = MathMax(dist, InpMinStopPct * entry);
   dist = MathMin(dist, InpMaxStopPct * entry);
   if(dist <= 0.0)
      return;

   //--- XARAJAT HIMOYASI
   // To'liq savdo BIR spread turadi: ask'da olib, bid'da sotasiz.
   double costR = spread / dist;
   if(costR > InpMaxCostR)
   {
      Log(StringFormat("Savdo o'tkazib yuborildi: xarajat %.3fR > %.2fR "
                       "(spread %.2f, stop %.2f)", costR, InpMaxCostR, spread, dist));
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
   if(leverage > InpMaxLeverage)
   {
      Log(StringFormat("Savdo o'tkazib yuborildi: leverage %.1fx > %.1fx",
                       leverage, InpMaxLeverage));
      return;
   }

   //--- SL / TP
   int dg = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   entry  = NormalizeDouble(entry, dg);
   double sl = entry - sig.side * dist;
   double tp = entry + sig.side * InpTp2R * dist;
   ClampStops(sig.side, entry, sl, tp);

   string dir = (sig.side > 0) ? "LONG" : "SHORT";
   PrintFormat("%s %s | kirish %.*f (%s) | stop %.*f | TP %.*f | %.2f lot | "
               "risk %.2f (%.2f%%) | xarajat %.3fR",
               dir, _Symbol, dg, entry, InpUseLimitEntry ? "limit" : "market",
               dg, sl, dg, tp, lots, actualRisk,
               actualRisk / MathMax(equity, 1e-9) * 100.0, costR);

   bool ok = false;
   ulong ticket = 0;
   if(InpUseLimitEntry)
   {
      datetime expiry = TimeCurrent() + InpEntryLimitBars * PeriodSeconds(PERIOD_M5);
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
   st.isPending   = InpUseLimitEntry;
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
      if(!g_states[i].tp1Done && nowR >= InpTp1R)
      {
         double part = NormalizeVolume(volume * InpTp1Fraction);
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
         if(MoveStop(ticket, side, entry + side * InpTp1StopToR * R, sl, "tp1_stop", appliedSl))
            sl = appliedSl;
         StatePersist(i);
      }

      //--- zararsizlikka o'tish (faqat +2R dan keyin)
      if(!g_states[i].beMoved && moveR >= InpBeTriggerR)
      {
         double spread = SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                       - SymbolInfoDouble(_Symbol, SYMBOL_BID);
         double target = entry + side * (InpBeOffsetR * R + spread);
         double appliedBe = sl;
         if(MoveStop(ticket, side, target, sl, "breakeven", appliedBe))
         {
            g_states[i].beMoved = true;
            sl = appliedBe;
            StatePersist(i);
         }
      }

      //--- trailing (mayda qadamlarda surilmaydi)
      if(moveR >= InpTrailAfterR && atr0 > 0.0)
      {
         double trail = g_states[i].bestPrice - side * InpTrailAtrMult * atr0;
         double minStep = InpTrailMinStepAtr * atr0;
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
      int barsHeld = (int)((TimeCurrent() - openTime) / PeriodSeconds(PERIOD_M5));
      if(barsHeld >= InpTimeStopBars && moveR < InpTimeStopMinR)
      {
         if(Trade.PositionClose(ticket))
         {
            Log(StringFormat("#%I64u vaqt stopi (%d bar, %+.2fR) — yopildi.",
                             ticket, barsHeld, nowR));
            continue;
         }
      }

      //--- TP1 dan keyin EMA21 chiqishi
      if(InpExitOnEmaCross && g_states[i].tp1Done)
      {
         double emaF = 0.0;
         if(CopyOne(hEmaFast, 0, 1, emaF))
         {
            double closeBar = iClose(_Symbol, PERIOD_M5, 1);
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
   datetime t = iTime(_Symbol, PERIOD_M5, 0);
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
         && PositionGetInteger(POSITION_MAGIC) == InpMagic
         && PositionGetString(POSITION_SYMBOL) == _Symbol)
         return true;
   }
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket != 0 && OrderSelect(ticket)
         && OrderGetInteger(ORDER_MAGIC) == InpMagic
         && OrderGetString(ORDER_SYMBOL) == _Symbol)
         return true;
   }
   return false;
}

void OnTick()
{
   // Ochiq pozitsiyalar har tikda kuzatiladi — TP1, trailing va
   // zararsizlik bar yopilishini kutmaydi.
   AdoptOrphanPositions();
   ManagePositions();

   // Signal esa FAQAT yopilgan barda hisoblanadi.
   if(!IsNewBar())
      return;

   g_barCounter++;
   SyncClosedTrades();
   ExpirePendingOrders();
   RollDay(iTime(_Symbol, PERIOD_M5, 1));

   if(HasOpenExposure())
      return;

   string blocked = RiskBlockReason();
   if(blocked != "")
   {
      // Signal bo'lsagina xabar beramiz — log'ni to'ldirmaslik uchun
      SignalResult peek = BuildSignal();
      if(peek.side != 0)
         Log("SIGNAL BOR, lekin bloklangan: " + blocked);
      return;
   }

   SignalResult sig = BuildSignal();
   if(sig.side == 0)
      return;

   TryOpen(sig);
}

//==================================================================
//  STRATEGY TESTER MEZONI
//
//  Optimizatsiyada "Custom max" tanlansa shu qiymat maksimallashtiriladi.
//  Python dagi `expectancy` mezoni bilan bir xil:
//      ekspektatsiya (R) x sqrt(savdolar soni)
//  Kam savdoli tasodifiy natijalar jazolanadi.
//==================================================================
double OnTester()
{
   if(g_closedTrades < 20)
      return -1000.0;
   double expectancy = g_sumR / g_closedTrades;
   return expectancy * MathSqrt((double)g_closedTrades);
}

//==================================================================
//  TEST YAKUNIDA XULOSA
//==================================================================
void OnTesterDeinit()
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
