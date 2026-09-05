# M5 Momentum Pullback — to'liq strategiya spetsifikatsiyasi

BTC/USDT perpetual, 5 daqiqalik grafik.

---

## 0. Avval eng muhim haqiqat

Skalping haqidagi eng keng tarqalgan yolg'on — "tor stop qo'ying, kuniga
20 ta savdo qiling, har biridan 0.2 % oling". Buni raqamlar bilan tekshiramiz.

Binance USDⓈ-M futures, VIP0 tarifi:

| Element | Qiymat |
|---|---|
| Taker komissiya (kirish) | 0.05 % |
| Taker komissiya (chiqish) | 0.05 % |
| Sirpanish (kirish) | ~0.015 % |
| Sirpanish (stop chiqish) | ~0.030 % |
| **Bitta to'liq savdo** | **0.145 %** |

Foyda **R** bilan o'lchanadi (R = stop masofasi), xarajat esa **notional**dan
olinadi. Demak:

```
xarajat (R birligida) = 0.145 % / stop_masofasi_%
```

| Stop masofasi | Xarajat | Zararsizlik uchun kerakli g'alaba % (2R payoff) |
|---|---|---|
| 0.15 % | **0.97 R** | 65.6 % |
| 0.20 % | **0.73 R** | 57.5 % |
| 0.30 % | 0.48 R | 49.4 % |
| **0.50 %** | **0.29 R** | **43.0 %** |
| 0.80 % | 0.18 R | 39.4 % |
| 1.50 % | 0.10 R | 36.6 % |

**Xulosa:** 0.20 % stop bilan har bir savdo 0.73R turadi. Bunday ustunlik
M5 da mavjud emas — bu tizim matematik jihatdan yutqazadi. Shuning uchun
bu strategiya **kam, lekin sifatli** savdo qiladi: stop 0.40–0.90 %,
kuniga 1–4 savdo, pozitsiya 30–120 daqiqa ushlanadi.

Bu jadvalni o'zingiz ko'rish uchun:
```bash
python -m scalpkit costs
```

---

## 1. Strategiyaning mantiqi

BTC M5 da vaqtning ~70 % i shovqin. Barqaror ustunlik shovqinni bashorat
qilishdan **emas**, quyidagi ketma-ketlikdan kelib chiqadi:

1. **Impuls** — bozorda haqiqiy kuch paydo bo'ladi (katta tanali bar,
   yuqori hajm yoki kanal buzilishi);
2. **Orqaga qaytish** — narx qiymat zonasiga (EMA21) qaytadi, zaif
   qo'llar chiqib ketadi;
3. **Davom etish** — asosiy yo'nalish tiklanadi.

Biz 2-bosqichda kiramiz, 3-bosqichda foyda olamiz. Bu **musbat assimetriya**
beradi: kichik stop, katta maqsad.

### Nima uchun "kuchli barning yopilishida" sotib olinmaydi

Bu loyihani qurishda o'lchangan muhim natija: kuchli o'sish barining
yopilishida sotib olish **manfiy** kutilma beradi (keyingi 1–3 barda
o'rtacha −0.04 ATR). Siz lokal cho'qqida sotib olasiz. Shuning uchun
strategiya standart holatda **limit order** ishlatadi — trigger baridan
0.15 ATR pastroqqa qo'yiladi.

---

## 2. Indikatorlar

| Indikator | Parametr | Vazifasi |
|---|---|---|
| EMA | 21 / 55 / 200 | trend strukturasi va qiymat zonasi |
| ATR | 14 | volatilitet, stop va maqsad o'lchovi |
| RSI | 7 | orqaga qaytish chuqurligi |
| ADX | 14 | trend bormi yoki yon harakatmi |
| Donchian | 20 | kanal buzilishi (impuls) |
| Hajm z-score | 50 | hajm normadan yuqorimi |
| H1 EMA | 50 | yuqori timeframe yo'nalishi |

---

## 3. LONG uchun qoidalar

### 3.1 Rejim filtrlari — barchasi bajarilishi SHART

| # | Shart | Sabab |
|---|---|---|
| R1 | `0.20 % ≤ ATR14/narx ≤ 1.20 %` | past volatilitetda komissiya yutadi; juda yuqorisida xaos |
| R2 | `ADX(14) ≥ 20` | trend bo'lmasa davom etish ham bo'lmaydi |
| R3 | `EMA21 > EMA55 > EMA200` va `narx > EMA200` | M5 strukturasi ko'tarilishda |
| R4 | H1: `narx > EMA50` va EMA50 o'smoqda | yuqori TF ga qarshi bormaslik |
| R5 | UTC 06:00–22:00 | London + Nyu-York likvidligi |

### 3.2 Setup

| # | Shart |
|---|---|
| S1 | Oxirgi **12** barda impuls bo'lgan: `tana ≥ 0.8 × ATR` va `hajm z ≥ 1.0`, **yoki** Donchian(20) yuqorisi buzilgan |
| S2 | Oxirgi **4** barda narx qiymat zonasiga qaytgan: `low ≤ EMA21 + 0.25 × ATR` |
| S3 | Shu oynada `RSI(7) ≤ 45` ga tushgan |

### 3.3 Trigger (bar yopilishida)

| # | Shart |
|---|---|
| T1 | `close > oldingi bar high` |
| T2 | `close > EMA21` va `close > open` |
| T3 | `close_pos ≥ 0.5` (bar tepasida yopilgan) |
| T4 | `hajm z ≥ −0.2` |
| T5 | `close ≤ EMA21 + 1.0 × ATR` — kech qolib quvmaslik |

### 3.4 Kirish

- **Limit order** `trigger_close − 0.15 × ATR` da, **3 bar** amal qiladi.
- Agar narx to'ldirilishdan oldin stop darajasidan o'tsa — order bekor qilinadi.
- To'ldirilmasa — savdo o'tkazib yuboriladi (bu normal, ~11 % holatda).
- Muqobil: `entry_mode: market` — keyingi bar ochilishida, kafolatlangan ijro,
  lekin ~0.13R qimmatroq.

### 3.5 Stop-loss

```
xom_stop  = oxirgi 5 bar eng past nuqtasi − 0.25 × ATR
masofa    = clamp(kirish − xom_stop,  1.0 × ATR,  2.2 × ATR)
masofa    = clamp(masofa,  narxning 0.15 % i,  narxning 2.0 % i)
stop      = kirish − masofa
```

### 3.6 Chiqish — **yutuqlar cheklanmaydi**

Bu blok strategiyaning eng muhim qismi. Dastlabki versiyada TP1 da yarim
pozitsiya olinib, stop darhol zararsizlikka surilardi. Natija:

* o'rtacha yutuq **+0.72R**, o'rtacha zarar **−1.08R**
* zararsizlik uchun **59.9 %** g'alaba kerak → amalda imkonsiz

Tuzatilgan tuzilma:

| Bosqich | Qoida |
|---|---|
| TP1 | `+1.5R` da pozitsiyaning **35 %** i olinadi |
| TP1 dan keyin | stop **−0.35R** ga suriladi (zararsizlikka EMAS) |
| Zararsizlik | faqat `+2.0R` dan keyin |
| Trailing | `+1.5R` dan keyin: `eng_yuqori_nuqta − 2.5 × ATR` |
| TP2 | `+3.5R` — to'liq chiqish |
| EMA chiqish | TP1 dan keyin `close < EMA21` bo'lsa |
| Vaqt stopi | 24 bar (2 soat) **va** savdo `+0.5R` ga yetmagan bo'lsa |

Bir xil ma'lumotda o'lchangan natija:

| | Klassik (BE stop) | Bu strategiya |
|---|---|---|
| O'rtacha yutuq | +0.720 R | **+1.303 R** |
| O'rtacha zarar | −1.077 R | −1.272 R |
| Payoff | 0.669 | **1.025** |
| **Zararsizlik** | **59.9 %** | **49.4 %** |

Klassik tuzilma kodda saqlangan — `be_after_tp1: true` bilan yoqib,
taqqoslashni o'zingiz qayta ishlab chiqarishingiz mumkin.

> Bu **payoff tuzilmasi** taqqoslashi, foyda va'dasi emas. Ustunlik
> bo'lmagan ma'lumotda hech qanday chiqish tuzilmasi foyda yaratmaydi —
> u faqat qanday g'alaba foizi talab qilinishini o'zgartiradi.

> **Nima uchun zararsizlik stopi yomon:** u yutuqlarni nolga aylantiradi,
> zararlarni esa o'zgartirmaydi. Payoff nisbatini buzadi va tizimni
> yuqori g'alaba foiziga bog'lab qo'yadi — M5 da bunday foizga erishib
> bo'lmaydi.

---

## 4. SHORT uchun qoidalar

To'liq oyna aksi:

- `EMA21 < EMA55 < EMA200`, `narx < EMA200`
- H1: `narx < EMA50`, EMA50 pasaymoqda
- Impuls: pastga katta tana yoki Donchian pasti buzilishi
- Qaytish: `high ≥ EMA21 − 0.25 × ATR`, `RSI(7) ≥ 55`
- Trigger: `close < oldingi bar low`, `close < EMA21`, `close < open`
- Limit: `trigger_close + 0.15 × ATR`

> BTC uzoq muddatda ko'tarilish tendensiyasiga ega — shortlar odatda
> qisqaroq va tezroq bo'ladi. `allow_short: false` bilan ularni o'chirib,
> natijani solishtirib ko'ring.

---

## 5. Pozitsiya hajmi

```
xавf_summasi = kapital × 0.005          # 0.5 %
hajm         = xавf_summasi / stop_masofasi
hajm         = min(hajm, kapital × 5 / kirish_narxi)   # leverage cheklovi
```

**Misol:** kapital 10 000 $, BTC 60 000 $, stop masofasi 0.5 % (300 $):

```
xавf = 50 $
hajm = 50 / 300 = 0.1667 BTC
notional = 0.1667 × 60 000 = 10 000 $  (1.0x leverage)
```

E'tibor bering: 0.5 % risk ≠ 0.5 % leverage. Tor stop katta notional beradi.

---

## 6. Kutilishi mumkin bo'lgan xulq

| Ko'rsatkich | Kutilgan diapazon |
|---|---|
| Savdolar | 1–4 / kun |
| G'alaba foizi | 38–48 % |
| Payoff | 1.3–1.8 |
| Stop masofasi | 0.40–0.90 % |
| Pozitsiya davomiyligi | 30–120 daqiqa |
| Ketma-ket zararlar | 6–10 ta — **normal** |

**Agar g'alaba foizi 40 % bo'lsa, 10 ta savdodan 6 tasi zarar bo'ladi.
Bu tizimning buzilgani emas — bu uning normal ishlashi.**

---

## 7. Nimaga ishonmaslik kerak

Bu spetsifikatsiya **mukammal** emas — bunday narsa yo'q. Halol ro'yxat:

1. **Hech qanday strategiya foydani kafolatlamaydi.** Bozor rejimi
   o'zgarganda har qanday statik qoidalar to'plami ishlashdan to'xtaydi.
2. **Bu yerdagi parametrlar boshlang'ich nuqta**, yakuniy javob emas.
   Ularni `walkforward` bilan o'z ma'lumotingizda tekshiring.
3. **Sintetik ma'lumotdagi natijalar foyda dalili emas.** Repodagi
   generator tizimni sinash uchun; unda M5 trend ustunligi ataylab yo'q.
4. **Ustunlik isbotlanishi kerak.** `walkforward` OOS ishonch oralig'i
   nolni o'z ichiga olsa — ustunlik yo'q, hajmni oshirmang.
