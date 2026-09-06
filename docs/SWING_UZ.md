# Swing savdosi — M15 / H1 / H4 / D1

Skalping va swing bir xil savdo emas. Farq faqat vaqtda emas — **xarajat
matematikasi tubdan o'zgaradi**, va shu sababli strategiya ham boshqacha
bo'lishi kerak.

---

## 1. Swing'ning asosiy afzalligi — o'lchangan

Volatilitet timeframe bilan taxminan √T qonuni bo'yicha o'sadi, spread esa
**o'zgarmaydi**. Natijada xarajat R birligida keskin arzonlashadi:

| TF | BTC ATR% | stop (1.5 ATR) | xarajat | M5 ga nisbatan |
|---|---|---|---|---|
| M5 | 0.220 % | 0.33 % | **0.093 R** | — |
| M15 | 0.382 % | 0.57 % | 0.054 R | 1.7x arzon |
| H1 | 0.776 % | 1.16 % | 0.026 R | 3.5x arzon |
| H4 | 1.594 % | 2.39 % | 0.013 R | 7.2x arzon |
| **D1** | 4.173 % | 6.26 % | **0.005 R** | **18.9x arzon** |

Yuqoridagi jadval faqat **spreadni** hisoblaydi. Bu to'liq rasm emas.

### Tuzatish: swap qo'shilganda rasm o'zgaradi

Spread TF bilan arzonlashadi, lekin **swap aksincha qimmatlashadi** —
chunki yuqori TF'da pozitsiya uzoqroq ochiq turadi. Oltin uchun ikkalasini
birga hisoblaganimizda:

| TF | spread R | swap R | **jami R** | eng arzonmi |
|---|---|---|---|---|
| M5 | 0.168 | 0.008 | 0.176 | |
| M15 | 0.097 | 0.024 | 0.121 | |
| **H1** | 0.048 | 0.048 | **0.096** | **← eng arzon** |
| H4 | 0.023 | 0.093 | 0.116 | |
| D1 | 0.009 | **0.212** | **0.221** | M15 dan ham qimmat |

**Oltin uchun D1 arzon EMAS.** Spread bo'yicha u 19x arzon, lekin ~17.5
kunlik ushlash swapni 0.21R ga olib chiqadi va umumiy xarajat M15
darajasidan ham yuqori bo'ladi. Eng arzon nuqta — **H1**, aynan spread
bilan swap teng bo'lgan joyda.

Bu suhbat boshida aytilgan "yuqori TF har doim arzonroq" xulosasining
tuzatilishi. U faqat spread uchun to'g'ri edi.

> BTC uchun bu jadval yo'q: repodagi BTC profili Binance perpetual
> (funding) modelida, MT5 CFD swapi esa o'lchanmagan — u brokerga qarab
> juda katta farq qiladi. O'z raqamingizni oling:
> `python -m scalpkit mt5-test --symbol BTCUSD` → `[3b]` bloki.

Shuning uchun M5 da ishlamaydigan g'oya H1/H4 da ishlashi mumkin — bozor
o'zgargani uchun emas, xarajat to'sig'i pasaygani uchun. Lekin D1 ga
o'tish oltinda xarajatni qaytadan oshiradi.

O'zingiz ko'ring:

```bash
python -m scalpkit profiles
```

---

## 2. Uchta strategiya

| | `momentum_pullback` | `donchian_breakout` | `range_reversion` |
|---|---|---|---|
| Turi | trend ichida qaytish | kanal buzilishi | o'rtachaga qaytish |
| Rejim | trend | **ADX yuqori** | **ADX past** |
| Kirish | EMA21 reclaim | N-bar cho'qqisi buzilganda | chekkada + qaytish bari |
| Maqsad | TP1 1.5R + TP2 3R | **YO'Q** | **MAJBURIY** (o'rtacha) |
| Trailing | bor | keng (3 ATR) | **yo'q** |
| Vaqt stopi | 24 bar | yo'q | **12 bar, so'zsiz** |
| Imzo | g'alaba ~37 %, payoff ~1.3 | g'alaba ~34 %, payoff ~1.7 | g'alaba ~46 %, payoff ~1.1 |
| Tavsiya etilgan TF | M5, M15 | M15, H1, H4, D1 | H1, H4 |

`donchian_breakout` va `range_reversion` — **bir-birining aksi**: biri
trendda, ikkinchisi yon harakatda ishlaydi. Chiqish tuzilmasi ham aks.

### Nima uchun maqsad birida zararli, ikkinchisida majburiy

Trend-following foydasi **dumdan** keladi — kam sonli juda katta yutuqdan.
Maqsad aynan o'shalarni kesadi.

Mean-reversion ustunligi esa **aniq bir harakatda** — o'rtachaga
qaytishda. Narx o'rtachaga yetgach, keyingi harakat tasodifiy va ushlab
turishning asosi yo'q. Maqsadsiz mean-reversion — bu shunchaki
yo'nalishsiz pozitsiya.

### Nima uchun `momentum_pullback` H4/D1 da ishlamaydi

O'lchangan (sintetik BTC, 250 000 M5 bar):

| Profil | momentum_pullback | donchian_breakout |
|---|---|---|
| btcusd_15m | 203 savdo | 1287 savdo |
| btcusd_1h | 37 savdo | 399 savdo |
| btcusd_4h | **8 savdo** | 109 savdo |
| btcusd_1d | **2 savdo** | 21 savdo |

Sababi: `momentum_pullback` oltita shartning **birgalikda** bajarilishini
talab qiladi (rejim + trend + impuls + qaytish + RSI + trigger). M5 da
kuniga 288 bar bor, D1 da esa 1 ta. Shart-konyunksiyasi shunchaki
bajarilmaydi.

Profillar buni avtomatik hal qiladi: H1/H4/D1 da standart strategiya —
`donchian_breakout`.

---

## 3. Trend-following'ning asosiy qoidasi: **maqsad qo'ymang**

Bu eng muhim va eng ko'p buziladigan qoida.

Trend-following foydasi kam sonli **juda katta** yutuqlardan keladi.
Savdolarning ~65-70 % i zarar, ~5 % i butun natijani yaratadi. 3R da
maqsad qo'yish aynan o'sha 5 % ni kesib tashlaydi.

O'lchangan (BTCUSD H4, bir xil signallar, faqat chiqish tuzilmasi farq qiladi):

| Chiqish tuzilmasi | savdo | g'alaba | payoff | eng yaxshi | ekspektatsiya |
|---|---|---|---|---|---|
| **maqsadsiz (dizayn)** | 112 | 26.8 % | **2.36** | **+5.8R** | **−0.079** |
| TP 5R da | 115 | 26.1 % | 2.30 | +4.9R | −0.110 |
| TP 3R da | 121 | 25.6 % | 2.04 | +3.0R | −0.176 |
| TP 2R da | 127 | 26.0 % | 1.98 | +2.0R | −0.179 |
| TP1 1.5R + zararsizlik | 121 | 24.8 % | 1.93 | +2.5R | **−0.218** |

Tartib monoton: maqsad qanchalik tor bo'lsa, natija shunchalik yomon.
Klassik "yarmini ol va stopni zararsizlikka sur" tuzilmasi esa eng yomoni.

> Bu foyda dalili emas — sintetik ma'lumot martingale, hamma variant
> manfiy. O'lchanayotgan narsa — chiqish tuzilmasining **nisbiy zarari**.

Shuning uchun Donchian profilida `tp2_r = 0`, `tp1_fraction = 0`,
`be_trigger_r` amalda cheksiz. Buni test qulflaydi
(`test_trend_experts_have_no_profit_target`).

---

## 4. Swing'ning o'ziga xos xarajati — SWAP

Skalpingda pozitsiya 30-90 daqiqa ochiq, swap sezilmaydi. Swing'da
haftalab ochiq turadi — va u jiddiy:

Oltin D1, risk $50, stop 1.28 %, notional $3 918:

| Ushlash | long | short |
|---|---|---|
| 3 kun | −0.028 R | +0.009 R |
| 10 kun | −0.094 R | +0.031 R |
| 20 kun | −0.188 R | +0.063 R |
| **30 kun** | **−0.282 R** | +0.094 R |

30 kunlik long pozitsiya 0.28R turadi — bu D1 spread xarajatidan (0.005R)
**56 barobar katta**. Backtest buni hisobga oladi (`apply_swap`).

> **BROKERINGIZNING HAQIQIY SWAP QIYMATINI TEKSHIRING.** Repodagi
> standart qiymat (oltin long −0.012 %/kun) bir kechalik carry hisobidan
> chiqarilgan (~4.5 % yillik / 360), lekin har brokerda ustama boshqacha.
> O'lchash: `python -m scalpkit mt5-test --symbol XAUUSD` → `[3b]` bloki
> brokeringizning qiymatini R ga aylantirib beradi.

BTC perpetual'da swap emas, **funding** bor (0.01 %/8 soat) — u ham
modellashtirilgan. Lekin **MT5 dagi BTC CFD funding emas, swap oladi**;
repoda uning qiymati 0 qo'yilgan (taxmin qilib bo'lmaydi). Shu sababli
BTC swing backtestlari optimistik bo'lishi mumkin — o'z raqamingizni
o'lchab qo'ying.

### Uch baravar rollover (chorshanba)

Broker hafta oxiri qiymat sanasini bitta kechada undiradi — odatda
chorshanba kechasi swap **uch baravar** olinadi. Ya'ni 7 kunlik pozitsiya
7 emas, **9 kechalik** to'lov qiladi (+28.6 %).

| Ushlash | sodda hisob | haqiqiy | farq |
|---|---|---|---|
| 3 kun | 3 kecha | 5 birlik | +67 % |
| 7 kun | 7 kecha | 9 birlik | +29 % |
| 18 kun | 18 kecha | 24 birlik | +33 % |

Buni hisobga olmaslik swing natijalarini yaxshi ko'rsatadi. Sintetik
ma'lumotda o'lchangan ta'sir: oltin D1 da savdo boshiga **−0.010 R**,
H4 da −0.005 R, H1 da −0.003 R. BTC ga ta'siri yo'q (unda swap 0).

### EA endi swapni kirish filtriga qo'shadi

MQL5 tomonida xarajat filtri avval faqat spreadga qarardi:

```
costR = spread / stop            // eski
costR = (spread + swap) / stop   // yangi
```

Swap terminaldan **to'g'ridan-to'g'ri o'qiladi** (`SYMBOL_SWAP_LONG/SHORT`,
barcha keng tarqalgan rejimlar bilan), shuning uchun u sizning
brokeringizning haqiqiy qiymati bo'ladi — repodagi taxmin emas.

Ikkita muhim tafsilot:

- **Daromad hisobga olinmaydi.** Short pozitsiyada swap musbat bo'lsa
  (oltin shortida shunday), filtr uni chegirma sifatida yozmaydi. Filtr
  ehtiyotkor bo'lishi kerak.
- **Filtr hech bir sozlamani o'chirib qo'ymaydi.** Bu test bilan
  qulflangan: har bir yetkazilgan konfiguratsiyada odatiy stop masofasida
  `spread + swap < MaxCostR` (0.40 R). Eng qattig'i oltin D1 — 0.22 R,
  ya'ni byudjetning yarmidan ko'pi ishlatiladi, lekin savdo to'silmaydi.

O'chirish kerak bo'lsa: `InpApplySwapCost = false`.

---

## 5. Ishlatish

### Python

```bash
# M5 ma'lumotdan istalgan TF ga avtomatik qayta namunalanadi
python -m scalpkit backtest  --profile btcusd_4h --data data/BTCUSDT_5m.csv
python -m scalpkit backtest  --profile xauusd_1d --data data/XAUUSD_5m.csv

# Boshqa strategiyani majburan tanlash
python -m scalpkit backtest  --profile btcusd_4h --strategy momentum_pullback --data ...

# To'liq tekshiruv va qat'iy xulosa
python -m scalpkit validate  --profile xauusd_4h --data data/XAUUSD_5m.csv --spread 0.30
```

Mavjud profillar: `btcusd_5m`, `btcusd_15m`, `btcusd_1h`, `btcusd_4h`,
`btcusd_1d` va oltin uchun `xauusd_*`.

### MetaTrader 5 — SWING uchun tavsiya etilgan yo'l

**Ikkita EA, preset kerak emas.** Ular grafik timeframe'ini o'qiydi va
o'sha TF uchun kalibrlangan parametrlarni **o'zlari** tanlaydi:

| Fayl | Instrument | Grafik TF | Magic asosi |
|---|---|---|---|
| `ScalpKit_BTC_Swing.mq5` | BTCUSD | M15 / H1 / H4 / D1 | 20261100 |
| `ScalpKit_XAU_Swing.mq5` | XAUUSD | M15 / H1 / H4 / D1 | 20261200 |

Ishlatish: EA ni kerakli grafikka tashlang — **tamom**. `.set` yuklash yo'q,
noto'g'ri preset yuklash xavfi yo'q.

Bitta sozlama muhim:

```
InpStrategy = 1   // trend (donchian)          — M15, H1, H4, D1
InpStrategy = 2   // o'rtachaga qaytish        — faqat M15, H1
```

`InpStrategy = 2` ni H4/D1 grafigida ishlatsangiz EA **ishga tushmaydi** va
sababini yozadi: 3 yillik tarixda H4 da ~25-33, D1 da ~3-4 ta savdo
chiqadi (8 seedli o'lchov), ya'ni statistik xulosa chiqarib bo'lmaydi.

Magic raqam avtomatik: `asos + strategiya x 10 + TF indeksi`. Ya'ni BTC
H1-trend = 20261112, BTC H4-trend = 20261113. Bir vaqtda 12 ta
kombinatsiyani ishlatsangiz ham ular bir-biriga tegmaydi.

Boshqa sozlamalar (risk, kunlik chegara, leverage, xarajat byudjeti)
kalibrlangan blokdan **keyin** qo'llanadi — ular sizniki.

> Hafta oxiri qoidasi uch holatli: `InpWeekendFlatMode = -1` (standart)
> profil qaror qilsin degani. Oltinda u M15/H1 da yoqiladi, H4/D1 da
> o'chiriladi. Buni oddiy `true/false` input qilib bo'lmasdi — u
> timeframe'ga bog'liq yagona qiymat.

### MetaTrader 5 — presetli yo'l (avvalgi EA'lar)

Oltita EA — 2 instrument x 3 strategiya. Bular **saqlanib qoldi**: ular
har bir parametrni input qilib ko'rsatadi, shuning uchun Strategy Tester'da
optimizatsiya qilish uchun qulay. Swing uchun kundalik ishlatishda esa
yuqoridagi ikkita EA xavfsizroq.

| Fayl | Instrument | Strategiya | Magic |
|---|---|---|---|
| `ScalpKit_BTC_Scalp.mq5` | BTCUSD | pullback (M5/M15) | 20260905 |
| `ScalpKit_XAU_Scalp.mq5` | XAUUSD | pullback (M5/M15) | 20260906 |
| `ScalpKit_BTC_Trend.mq5` | BTCUSD | trend (M15–D1) | 20260907 |
| `ScalpKit_XAU_Trend.mq5` | XAUUSD | trend (M15–D1) | 20260908 |
| `ScalpKit_BTC_Range.mq5` | BTCUSD | qaytish (H1/H4) | 20260909 |
| `ScalpKit_XAU_Range.mq5` | XAUUSD | qaytish (H1/H4) | 20260910 |

Magic raqamlar har xil — oltitasi bir vaqtda ishlay oladi.

Timeframe **grafikdan** olinadi, parametrlar esa presetdan:

```
mql5/Presets/ScalpKit_BTC_Trend_4H.set
mql5/Presets/ScalpKit_XAU_Trend_1D.set   ... va h.k.
```

1. EA ni kerakli TF grafigiga tashlang (masalan XAUUSD H4)
2. Sozlamalar oynasida **Load** → mos `.set` faylini tanlang
3. OK

> EA `InpExpectedTimeframe` orqali presetning grafik TF ga mosligini
> **tekshiradi**. Noto'g'ri preset yuklansa, ishga tushmaydi va xato
> yozadi — chunki volatilitet chegaralari TF ga bog'liq kalibrlangan.

---

## 6. Kutilishi mumkin bo'lgan xulq

| Ko'rsatkich | M15 | H1 | H4 | D1 |
|---|---|---|---|---|
| Savdolar | ~1.1–1.5/kun | ~0.4/kun | ~0.13/kun | ~0.03/kun |
| Stop masofasi | 0.5–0.6 % | 1.0–1.2 % | 2.2–2.4 % | 5.5–6.5 % |
| Ushlash | soatlar | 1–2 kun | 3–10 kun | haftalar |
| G'alaba foizi | 33–38 % | 34–38 % | 27–34 % | 33–38 % |
| Payoff | 1.4–1.6 | 1.4–1.5 | 1.5–2.4 | 1.5–1.6 |

**Past g'alaba foizidan qo'rqmang** — bu trend-following uchun normal.
10 savdodan 7 tasi zarar bo'lishi kutilgan natija; foyda qolgan 3 tadan,
ayniqsa eng katta 1 tasidan keladi.

### Validatsiya uchun amaliy oqibat

D1 da kuniga ~0.03 savdo. Ishonchli xulosa uchun 100+ OOS savdo kerak —
bu **~9 yillik** OOS ma'lumot degani. Amalda:

| TF | 100 OOS savdo uchun kerak |
|---|---|
| M15 | ~3 oy OOS |
| H1 | ~9 oy OOS |
| H4 | ~2 yil OOS |
| D1 | ~9 yil OOS |

**D1 ni yakka o'zi statistik tasdiqlab bo'lmaydi.** Yechim: bir nechta
instrument bo'yicha birlashtirish (portfel) yoki H4 ni asosiy swing TF
sifatida olish. H4 — statistik tasdiqlash va xarajat afzalligi o'rtasidagi
eng yaxshi murosa.

---

## 7. O'lchangan natijalar — ko'p-seed

Quyidagi jadval **8 ta mustaqil seed** birlashtirilgan holda olingan.
Ma'lumot sof martingale (`chop_reversion = 0`), ya'ni **ustunlik yo'q**.
Kutilgan natija — taxminan minus xarajat.

| Profil | Strategiya | Savdo | G'alaba | Payoff | Ekspektatsiya |
|---|---|---|---|---|---|
| btcusd_15m | trend | 6336 | 32.1 % | 1.49 | −0.170 |
| btcusd_1h | trend | 1916 | 34.5 % | 1.66 | −0.067 |
| btcusd_4h | trend | 553 | 36.5 % | 1.74 | **−0.001** |
| btcusd_1d | trend | 70 | 34.3 % | 1.53 | −0.107 |
| btcusd_1h | qaytish | 380 | 45.8 % | 1.12 | −0.028 |
| xauusd_4h | trend | 625 | 32.2 % | 1.92 | −0.049 |
| xauusd_1d | trend | 93 | 34.4 % | 1.90 | −0.001 |
| xauusd_1h | qaytish | 395 | 45.8 % | 1.18 | −0.001 |

**Nima ko'rinyapti:**

1. Barcha natijalar manfiy yoki noldan farq qilmaydi — ustunliksiz
   ma'lumotda bu **to'g'ri**. Vosita soxta ustunlik ixtiro qilmaydi.
2. Ekspektatsiya timeframe o'sishi bilan nolga yaqinlashadi
   (−0.170 → −0.001). Bu aynan xarajat afzalligining namoyon bo'lishi.
3. Payoff imzolari barqaror: trend 1.49–1.92, qaytish 1.12–1.18.

### Bitta seedga ishonib bo'lmaydi

Ish jarayonida bitta seedda `range_reversion` H4 da **+0.158R**
ko'rsatgandi. 8 seedda esa **−0.035R**. Farq butunlay shovqin edi.

Bu butun to'plamning mavjud bo'lish sababi: bitta chiroyli backtest
hech narsani isbotlamaydi.

### Nazorat tajribasi: vosita ustunlikni topa oladimi?

Generatorga ma'lum kuchdagi o'rtachaga qaytish qo'yib, uni topish-topmasligi
tekshirildi:

| Qo'yilgan qaytish (M5 avtokorrelyatsiya) | H4 da qoladi | Topildimi |
|---|---|---|
| 0.00 | 0.014 | — |
| 0.05 (−0.034) | 0.015 | yo'q |
| 0.15 (−0.100) | 0.014 | yo'q |

Sabab: qaytish M5 darajasida qo'yilgan va H4 ga o'tganda **bar ichida
o'rtachalanib yo'qoladi**. Ya'ni H4 da topadigan narsa yo'q edi —
strategiya to'g'ri hech nima topmadi.

M5 da esa (qaytish avtokorrelyatsiyasi −0.100) strategiya baribir uni
topa olmadi: ekspektatsiya −0.354R. Sabab — o'sha timeframe'da
**xarajat qo'yilgan ustunlikdan ancha katta**.

Bu M5 skalping haqidagi dastlabki xulosani mustaqil ravishda tasdiqlaydi.

---

## 8. Halol ogohlantirish

Bu strategiyalarning foyda keltirishi **isbotlanmagan**. O'lchanган va
isbotlangan narsa:

* xarajatning timeframe bo'yicha 17-19 barobar kamayishi;
* maqsad qo'yish trend-following'ga zarar yetkazishi;
* har bir profil o'z bozorida to'g'ri kalibrlangani.

Ustunlikning **borligini** faqat siz aniqlay olasiz — real ma'lumotda
`validate` yoki MT5 Strategy Tester (Forward 1/4) bilan. Sintetik
generatordagi natijalar martingale ma'lumotda olingan va foyda dalili emas.
