# ScalpKit MQL5 Expert Advisor — o'rnatish va test

`mql5/Experts/ScalpKit_M5.mq5` — Python strategiyasining MetaTrader 5
uchun to'liq amalga oshirilishi. Barcha parametrlar **aynan bir xil**
(buni `tests/test_mql5_parity.py` avtomatik tekshiradi).

> **Bu EA sizga men qila olmagan narsani beradi:** MT5 Strategy Tester
> Exness'ning o'z ma'lumotida, sizning kompyuteringizda ishlaydi.

---

## 1. O'rnatish

1. MT5 da: **File → Open Data Folder**
2. `MQL5\Experts\` papkasiga o'ting
3. `ScalpKit_M5.mq5` faylini shu yerga nusxalang
4. MT5 da **F4** bosing (MetaEditor ochiladi)
5. Chapdagi Navigator'da `ScalpKit_M5.mq5` ni toping va **F7** bosing (Compile)
6. `0 errors, 0 warnings` chiqishi kerak

> **Diqqat:** bu fayl Linux muhitida yozilgan, u yerda MQL5 kompilyatori
> yo'q (MetaEditor faqat Windows uchun). Kod sintaksis va parametr
> mosligi bo'yicha avtomatik tekshirilgan (`tests/test_mql5_parity.py`,
> 57 ta taqqoslash), lekin **haqiqiy kompilyatsiyadan o'tmagan**.
> Agar F7 xato bersa — xato matnini menga yuboring, darhol tuzataman.
7. MT5 ga qayting → Navigator → Expert Advisors → `ScalpKit_M5` paydo bo'ladi

**Terminal sozlamasi (majburiy):**
Tools → Options → Expert Advisors → ☑ **Allow algorithmic trading**

---

## 2. STRATEGY TESTER — asosiy qism

Bu yerda strategiyaning ishlash-ishlamasligi aniqlanadi.

### 2.1 Oddiy backtest

**View → Strategy Tester** (yoki Ctrl+R)

| Sozlama | Qiymat |
|---|---|
| Expert | `ScalpKit_M5` |
| Symbol | `BTCUSD` (yoki `BTCUSDm` — MarketWatch'dagi nomingiz) |
| Period | **M5** |
| Modelling | **Every tick based on real ticks** ← eng aniq |
| Dates | imkon qadar uzoq (kamida 1 yil) |
| Deposit | real hisobingizga yaqin summa |
| Leverage | hisobingizdagi kabi |

> **"Open prices only" ni ISHLATMANG.** Strategiya limit order va bar
> ichidagi SL/TP bilan ishlaydi — bu rejimda natija soxta chiqadi.
> Tez sinov uchun "1 minute OHLC" mumkin, lekin yakuniy qaror uchun
> "Every tick based on real ticks" kerak.

### 2.2 WALK-FORWARD — MT5 da o'rnatilgan

Bu Python'dagi `walkforward` ning aynan ekvivalenti va **eng muhim test**.

1. Strategy Tester → **Settings** yorlig'i
2. **Optimization**: `Fast genetic based algorithm`
3. **Forward**: `1/4` (yoki `1/3`)
4. **Custom max** ni tanlang — EA `OnTester()` da
   `ekspektatsiya × √savdolar` qiymatini qaytaradi (Python'dagi mezon bilan bir xil)
5. **Inputs** yorlig'ida optimallashtiriladigan parametrlarni belgilang

Tavsiya etilgan optimizatsiya oynasi (ko'p emas — overfitting xavfi):

| Parametr | Start | Step | Stop |
|---|---|---|---|
| `InpAdxMin` | 16 | 4 | 28 |
| `InpMinAtrPct` | 0.0015 | 0.0005 | 0.0030 |
| `InpTp1R` | 1.0 | 0.25 | 2.0 |
| `InpTrailAtrMult` | 2.0 | 0.5 | 3.5 |

6. **Start** bosing

Natijada ikkita yorliq bo'ladi:
- **Optimization Results** — o'rgatish davri (in-sample)
- **Forward Results** — **KO'RILMAGAN** davr (out-of-sample) ← faqat shunga qarang

### 2.3 Natijani qanday o'qish kerak

| Belgi | Xulosa |
|---|---|
| Forward natijasi musbat, IS ga yaqin | sog'lom |
| Forward musbat, lekin IS dan ancha past | qisman overfitting |
| **Forward manfiy, IS musbat** | **klassik overfitting — ishlatmang** |
| Forward savdolari < 100 | xulosa chiqarib bo'lmaydi |

Test tugagach EA jurnalga o'z xulosasini yozadi:

```
ScalpKit yakuni: 214 savdo | ekspektatsiya +0.061 R | g'alaba 43.9% | jami +13.1 R
```

**Ekspektatsiya musbat bo'lmasa — qolgan hech narsaning ahamiyati yo'q.**

---

## 3. Jonli ishlatish

1. BTCUSD M5 grafigini oching
2. `ScalpKit_M5` ni grafikka tashlang
3. Sozlamalarni tekshiring, **OK**
4. Yuqori o'ng burchakda ☺ tabassum belgisi chiqishi kerak
   (agar ☹ bo'lsa — algo savdo o'chirilgan)

EA jurnalga har bir qarorni yozadi: signal, hajm, xarajat, stop harakatlari.

> **Faqat BITTA grafikda ishlating.** EA bir vaqtda bitta pozitsiya
> ochadi va boshqa nusxasi bilan to'qnashadi.

> EA `magic = 20260905` bilan **faqat o'z savdolariga tegadi**.
> Qo'lda ochgan pozitsiyalaringizga aralashmaydi.

---

## 4. Nima qiladi

Har **yopilgan** M5 barda:

```
1. Rejim    : ATR% ∈ [0.20 %, 1.20 %] · ADX ≥ 20 · seans · EMA21>55>200 · H1 mos
2. Setup    : oxirgi 12 barda impuls · EMA21 zonasiga qaytish · RSI(7) ≤ 45
3. Trigger  : close > oldingi bar high · close > EMA21 · bar tepasida yopilgan
4. Xarajat  : spread / stop > 0.40R bo'lsa — SAVDO YO'Q
5. Hajm     : kapitalning 0.5 % i, lot qadamiga moslangan
6. Order    : limit (trigger_close − 0.15 ATR), 3 bar amal qiladi
```

Har **tikda** ochiq pozitsiya boshqariladi:

```
+1.5R  -> 35 % yopiladi, stop −0.35R ga (zararsizlikka EMAS)
+2.0R  -> stop zararsizlikka
+1.5R  -> 2.5 ATR trailing (0.15 ATR dan kichik qadamda surilmaydi)
24 bar -> savdo +0.5R ga yetmagan bo'lsa yopiladi
TP1 dan keyin close < EMA21 -> yopiladi
```

---

## 5. Muhim parametrlar

| Parametr | Standart | Izoh |
|---|---|---|
| `InpRiskPerTrade` | 0.005 | **Oshirmang.** Demo'da 0.001 dan boshlang |
| `InpMaxCostR` | 0.40 | Spread keng bo'lsa savdo qilmaydi |
| `InpUseLimitEntry` | true | `false` = market (kafolatlangan ijro, qimmatroq) |
| `InpServerUtcOffset` | -99 | −99 = avtomatik aniqlash |
| `InpMagic` | 20260905 | Bir nechta nusxa ishlatsangiz o'zgartiring |
| `InpVerbose` | true | Testda `false` qiling — tezroq ishlaydi |

---

## 6. Muammolar

| Belgi | Sabab / yechim |
|---|---|
| Kompilyatsiyada xato | MT5 build eski — Help → Check for Updates |
| ☹ belgisi | Tools → Options → Expert Advisors → Allow algorithmic trading |
| Savdo yo'q, jurnal jim | Normal: strategiya kuniga 1–4 savdo qiladi |
| `retcode=10016` | SL/TP juda yaqin — EA avtomatik tuzatadi; qayta chiqsa `stops_level` katta |
| `retcode=10014` | Lot qadami — `InpRiskPerTrade` ni yoki depozitni tekshiring |
| `retcode=10030` | Filling mode — `SetTypeFillingBySymbol` tanlaydi, chiqsa brokerga murojaat |
| "hajm minimal lotdan kichik" | Depozit kichik yoki stop keng. **Riskni oshirmang** |
| "xarajat > 0.40R" | Spread keng. EA sizni himoya qildi |
| Testda savdo juda kam | Uzoqroq davr oling yoki `InpAdxMin` ni pasaytiring |

---

## 7. Python versiyasi bilan farqlari

| Jihat | Python | MQL5 EA |
|---|---|---|
| Signal | yopilgan bar | yopilgan bar (bir xil) |
| Pozitsiya boshqaruvi | har bar | **har tik** (tezroq reaksiya) |
| Xarajat modeli | konfiguratsiyadan | **jonli spread** |
| Ma'lumot | CSV / Binance | brokeringizning o'zi |
| Tekshiruv | `walkforward` buyrug'i | Strategy Tester **Forward** |

Parametrlar bir xil ekanligi `pytest tests/test_mql5_parity.py` bilan
tekshiriladi — 57 ta taqqoslash.

---

## 8. Halol ogohlantirish

Bu EA strategiyani **to'g'ri bajaradi**, lekin uning **foydali ekanligini
kafolatlamaydi**. Strategiyaning ustunligi hali real ma'lumotda
isbotlanmagan — buni aniqlash uchun aynan siz Strategy Tester'da
walk-forward (Forward 1/4) o'tkazishingiz kerak.

Forward natijasi manfiy chiqsa — bu yomon xabar emas, bu **qimmatli
xabar**: siz pul yo'qotmasdan bilib oldingiz.
