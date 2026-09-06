# TEST REJASI — birma-bir sinash ro'yxati

Bu hujjat suhbat boshidan beri tayyorlangan **hamma narsani** sinash tartibida
ro'yxatlaydi. Yuqoridan pastga qarab yuring. Har bandning oxirida natija
shabloni bor — o'shani to'ldirib menga yuboring, shunda javoblaringizni
bir-biri bilan solishtira olaman.

**Muhim:** tartib tasodifiy emas. Yuqoridagi testlar ko'p savdo beradi,
demak ular **statistik javob** beradi. Pastdagilar kam savdo beradi, ular
qancha "chiroyli" ko'rinmasin, javob bermaydi. Vaqtingizni yuqoridan sarflang.

---

## 0-BOSQICH — Papkalar xaritasi (nima qayerda)

### A. Python loyihasi (bu repozitoriy)

| Papka | Nima uchun | Sinash kerakmi |
|---|---|---|
| `scalpkit/` | Asosiy kutubxona: strategiyalar, dvigatel, risk, tekshiruv | ha — 1.1–1.5 bandlar |
| `scalpkit/strategies/` | 3 ta strategiya: `momentum_pullback`, `donchian_breakout`, `range_reversion` | ha |
| `scalpkit/engine/` | Bar-bar backtest dvigateli | avtomatik (testlar) |
| `tests/` | 197 ta avtomatik test | ha — 1.1 band |
| `tools/` | `gen_mql5_experts.py` — EA generatori | avtomatik (testlar) |
| `config/` | YAML konfiguratsiyalar | kerak bo'lsa tahrirlaysiz |
| `data/` | CSV narx ma'lumotlari (git'ga kirmaydi) | siz to'ldirasiz |
| `out/` | Natijalar chiqadi (git'ga kirmaydi) | o'qiysiz |
| `docs/` | Hamma o'zbekcha qo'llanmalar | o'qiysiz |

### B. MT5 tomoni (`ScalpKit_MT5_v3.zip` ichida)

| Papka | MT5 dagi joyi |
|---|---|
| `mql5/Include/ScalpKit/Core.mqh` | `MQL5\Include\ScalpKit\Core.mqh` |
| `mql5/Experts/*.mq5` (8 ta) | `MQL5\Experts\ScalpKit\` |
| — shundan `*_Swing.mq5` (2 ta) | preset kerak emas, o'zini sozlaydi |
| `mql5/Presets/*.set` (16 ta) | `MQL5\Presets\` |

---

## 1-BOSQICH — Python tomoni (kompyuterda, ~20 daqiqa)

Bu bosqich MT5 dan oldin. Maqsad: kod ishlayotganiga ishonch hosil qilish.

### 1.1 — Testlarni ishga tushirish

```bash
cd scalp
pip install -r requirements.txt
pytest -q
```

**Kutilgan:** `197 passed`. Agar bitta ham yiqilsa — menga xato matnini
yuboring, davom etmang.

### 1.2 — Profillarni ko'rish

```bash
python -m scalpkit profiles
```

**Kutilgan:** 12 qatorli jadval (btcusd va xauusd × 5 timeframe).
Diqqat qiling: `xarajat R` ustuni M5 da 0.103 (BTC) / 0.168 (oltin),
D1 da 0.005 / 0.009 — **20 baravar arzon**. Swing'ning butun mantiqi shu.

### 1.3 — Xarajat jadvali

```bash
python -m scalpkit costs --profile btcusd_5m
python -m scalpkit costs --profile xauusd_5m
```

**Kutilgan:** zararsizlik (breakeven) foizi. Agar u 55 % dan yuqori chiqsa —
o'sha timeframe'da skalping matematik jihatdan og'ir.

### 1.4 — Haqiqiy ma'lumot yuklash (MT5 kompyuteringizda ochiq bo'lsin)

Avval parolni muhit o'zgaruvchisiga qo'ying (parol hech qachon faylga
yozilmaydi):

```bash
export MT5_PASSWORD='...'        # Windows PowerShell: $env:MT5_PASSWORD='...'
```

So'ng:

```bash
python -m scalpkit mt5-bars --symbol BTCUSD --interval 5m  --count 200000 --out data/BTCUSD_5m.csv
python -m scalpkit mt5-bars --symbol BTCUSD --interval 15m --count 200000 --out data/BTCUSD_15m.csv
python -m scalpkit mt5-bars --symbol BTCUSD --interval 1h  --count 100000 --out data/BTCUSD_1h.csv
python -m scalpkit mt5-bars --symbol XAUUSD --interval 5m  --count 200000 --out data/XAUUSD_5m.csv
python -m scalpkit mt5-bars --symbol XAUUSD --interval 15m --count 200000 --out data/XAUUSD_15m.csv
python -m scalpkit mt5-bars --symbol XAUUSD --interval 1h  --count 100000 --out data/XAUUSD_1h.csv
```

> `--interval` qiymatlari: `5m`, `15m`, `1h`, `4h`, `1d` (kichik harflarda).

> Simvol nomi brokeringizda `BTCUSD` emas, `BTCUSDm` yoki `XAUUSDm` bo'lishi
> mumkin — MT5 Market Watch'dagi aniq nomni yozing.

> Bu buyruq **Windows** da, MT5 terminali ochiq turganda ishlaydi
> (`MetaTrader5` paketi faqat Windows uchun).

**Menga yuboring:** har fayl uchun necha qator chiqdi va qaysi sanadan
boshlanadi. Bu keyingi bandlar uchun tarix yetarliligini aniqlaydi.

### 1.5 — To'liq tekshiruv (walk-forward + xulosa)

Har biri uchun alohida:

```bash
python -m scalpkit validate --profile btcusd_15m --data data/BTCUSD_15m.csv --strategy donchian_breakout
python -m scalpkit validate --profile btcusd_5m  --data data/BTCUSD_5m.csv
python -m scalpkit validate --profile btcusd_1h  --data data/BTCUSD_1h.csv  --strategy donchian_breakout
python -m scalpkit validate --profile xauusd_15m --data data/XAUUSD_15m.csv --strategy donchian_breakout
python -m scalpkit validate --profile xauusd_5m  --data data/XAUUSD_5m.csv
python -m scalpkit validate --profile xauusd_1h  --data data/XAUUSD_1h.csv  --strategy donchian_breakout
```

**Kutilgan xulosalardan biri:**

| Xulosa | Ma'nosi |
|---|---|
| `trade` | OOS'da musbat va statistik ishonchli |
| `not_proven` | musbat, lekin ishonch oralig'i nolni kesib o'tadi |
| `insufficient` | savdo soni 100 dan kam — javob yo'q, ko'proq tarix kerak |
| `no_edge` | OOS'da manfiy |

**Menga yuboring:** har buyruq oxiridagi xulosa bloki (OOS savdo soni,
kutilma R, ishonch oralig'i, verdikt).

---

## 2-BOSQICH — MT5 o'rnatish (bir marta)

1. MT5 → `File` → `Open Data Folder`
2. `MQL5\Include\` ichiga `ScalpKit` papkasini (Core.mqh bilan) ko'chiring
3. `MQL5\Experts\` ichiga `ScalpKit` papkasini (6 ta .mq5) ko'chiring
4. `MQL5\Presets\` ichiga 16 ta `.set` faylni ko'chiring
5. MT5 → `Navigator` → o'ng tugma → `Refresh`
6. Har bir EA'ni MetaEditor'da oching → **F7** (Compile) → `0 error(s)`
7. `Tools` → `Options` → `Expert Advisors` → `Allow Algo Trading` ✅

### Tarixni yuklash (juda muhim)

`Tools` → `Options` → `Charts` → **Max bars in chart = 99999999**

So'ng har bir simvol/timeframe grafigini oching va **Home** tugmasini
uzoq bosib turing — MT5 tarixni serverdan tortadi. Buni qilmasangiz
tester "no history" beradi yoki qisqa davrda sinaydi.

**Menga yuboring:** kompilyatsiya natijasi (`0 error, N warning`) va
BTCUSD hamda XAUUSD uchun tarix qaysi sanadan boshlanadi.

---

## 3-BOSQICH — Strategy Tester: 16 ta presetni sinash

### Har test uchun bir xil sozlamalar

| Maydon | Qiymat |
|---|---|
| Expert | quyidagi jadvaldan |
| Symbol | `BTCUSD` yoki `XAUUSD` (brokeringizdagi aniq nom) |
| Period | quyidagi jadvaldan — **preset bilan mos bo'lishi shart** |
| Date | quyidagi jadvaldan (`Custom period`) |
| Modelling | **Every tick based on real ticks** |
| Deposit | real hisobingizga yaqin summa (masalan 1000 USD) |
| Leverage | hisobingizdagidek |
| Optimization | `Fast genetic based algorithm` |
| Forward | **`1/4`** |
| Custom max | tanlang (EA `OnTester()` da o'z mezonini beradi) |

> `Inputs` yorlig'ida `Load` tugmasi orqali kerakli `.set` faylni yuklang.
> Yuklamasangiz EA sozlamalari standart qoladi va natija noto'g'ri bo'ladi.

> **EA o'zi tekshiradi:** agar preset TF si grafik TF siga mos kelmasa,
> EA `InpExpectedTimeframe` guard'i ishga tushib xato beradi. Bu himoya —
> uni o'chirmang, TF ni to'g'rilang.

---

### 0-DARAJA — eng qisqa yo'l: SWING EA (preset yuklash yo'q)

Agar faqat swing bilan ishlamoqchi bo'lsangiz, quyidagi 6 testni
`ScalpKit_BTC_Swing` / `ScalpKit_XAU_Swing` bilan qiling. `.set` yuklash
kerak emas — EA grafik TF ini o'zi o'qiydi. Xato qilish imkonsiz.

| № | EA | Simvol | TF | `InpStrategy` | Tarix | Savdo (2 yil) |
|---|---|---|---|---|---|---|
| 3.0a | `ScalpKit_BTC_Swing` | BTCUSD | **M15** | 1 (trend) | 2 yil | ~940 |
| 3.0b | `ScalpKit_XAU_Swing` | XAUUSD | **M15** | 1 (trend) | 2 yil | ~940 |
| 3.0c | `ScalpKit_BTC_Swing` | BTCUSD | **H1** | 1 (trend) | 2 yil | ~307 |
| 3.0d | `ScalpKit_XAU_Swing` | XAUUSD | **H1** | 1 (trend) | 2 yil | ~307 |
| 3.0e | `ScalpKit_BTC_Swing` | BTCUSD | **H1** | 2 (qaytish) | 2–3 yil | ~160 |
| 3.0f | `ScalpKit_XAU_Swing` | XAUUSD | **H1** | 2 (qaytish) | 2–3 yil | ~160 |

Jurnalda birinchi qatorda quyidagicha yozuv chiqishi kerak — bu EA o'zini
to'g'ri sozlaganini tasdiqlaydi:

```
Swing sozlandi: PERIOD_H1 / trend (donchian) | magic 20261112 | ushlash ~0.73 kun | hafta oxiri ochiq qoladi
```

Chiqmasa — TF va `InpStrategy` juftligi qo'llab-quvvatlanmaydi
(masalan qaytish + H4). EA sababini yozadi.

> **Oltin uchun muhim:** swap endi kirish filtriga qo'shildi. Oltin D1 da
> u xarajat byudjetining yarmini egallaydi. Agar D1 da savdolar kutilganidan
> kam chiqsa, jurnalda "xarajat ... > 0.40R" qatorini qidiring — bu xato
> emas, filtr ishlayapti.

### 1-DARAJA — eng ko'p ma'lumot beradigan testlar (presetli EA'lar bilan)

| № | EA | Preset | Simvol | TF | Kerakli tarix | Kutilgan savdo (2 yil) |
|---|---|---|---|---|---|---|
| 3.1 | `ScalpKit_BTC_Trend` | `ScalpKit_BTC_Trend_15M.set` | BTCUSD | **M15** | 2 yil | ~940 |
| 3.2 | `ScalpKit_XAU_Trend` | `ScalpKit_XAU_Trend_15M.set` | XAUUSD | **M15** | 2 yil | ~940 |
| 3.3 | `ScalpKit_BTC_Scalp` | `ScalpKit_BTC_Scalp_5M.set` | BTCUSD | **M5** | 2 yil | ~350 |
| 3.4 | `ScalpKit_XAU_Scalp` | `ScalpKit_XAU_Scalp_5M.set` | XAUUSD | **M5** | 2 yil | ~350 |
| 3.5 | `ScalpKit_BTC_Trend` | `ScalpKit_BTC_Trend_1H.set` | BTCUSD | **H1** | 2 yil | ~307 |
| 3.6 | `ScalpKit_XAU_Trend` | `ScalpKit_XAU_Trend_1H.set` | XAUUSD | **H1** | 2 yil | ~307 |

Bu 6 tasi **eng qimmatli**. Agar vaqtingiz cheklangan bo'lsa, faqat
shularni qiling va natijalarini yuboring — men shulardan xulosa chiqara olaman.

### 2-DARAJA — javob beradi, lekin chegarada

| № | EA | Preset | Simvol | TF | Kerakli tarix | Kutilgan savdo (2 yil) |
|---|---|---|---|---|---|---|
| 3.7 | `ScalpKit_BTC_Scalp` | `ScalpKit_BTC_Scalp_15M.set` | BTCUSD | **M15** | 2–3 yil | ~160 |
| 3.8 | `ScalpKit_XAU_Scalp` | `ScalpKit_XAU_Scalp_15M.set` | XAUUSD | **M15** | 2–3 yil | ~160 |
| 3.9 | `ScalpKit_BTC_Range` | `ScalpKit_BTC_Range_1H.set` | BTCUSD | **H1** | 2–3 yil | ~160 |
| 3.10 | `ScalpKit_XAU_Range` | `ScalpKit_XAU_Range_1H.set` | XAUUSD | **H1** | 2–3 yil | ~160 |

Forward qismida 40 tacha savdo qoladi — bu kam. Xulosa "ehtimol", "isbot" emas.

### 3-DARAJA — faqat 3 yil tarix bo'lsa

| № | EA | Preset | Simvol | TF | Kerakli tarix | Kutilgan savdo (3 yil) |
|---|---|---|---|---|---|---|
| 3.11 | `ScalpKit_BTC_Trend` | `ScalpKit_BTC_Trend_4H.set` | BTCUSD | **H4** | **3 yil** | ~137 |
| 3.12 | `ScalpKit_XAU_Trend` | `ScalpKit_XAU_Trend_4H.set` | XAUUSD | **H4** | **3 yil** | ~137 |

### 4-DARAJA — HOZIRCHA QILMANG (statistik jihatdan imkonsiz)

| № | EA | Preset | TF | 3 yilda savdo | Nega |
|---|---|---|---|---|---|
| ~~3.13~~ | `ScalpKit_BTC_Range` | `ScalpKit_BTC_Range_4H.set` | H4 | ~82 | 100 dan kam |
| ~~3.14~~ | `ScalpKit_XAU_Range` | `ScalpKit_XAU_Range_4H.set` | H4 | ~82 | 100 dan kam |
| ~~3.15~~ | `ScalpKit_BTC_Trend` | `ScalpKit_BTC_Trend_1D.set` | D1 | ~31 | 100 dan kam |
| ~~3.16~~ | `ScalpKit_XAU_Trend` | `ScalpKit_XAU_Trend_1D.set` | D1 | ~31 | 100 dan kam |

**Nega qilmaslik kerak:** D1 da yiliga ~10 savdo bo'ladi. 10 savdoda
"foyda" ham, "zarar" ham tasodifdan farq qilmaydi — o'lchov shovqindan
iborat. Bu presetlar **noto'g'ri** degani emas; ular **hozirgi tarix
bilan tekshirib bo'lmaydi** degani. D1 ni haqiqatan sinash uchun 10+ yillik
tarix kerak, Exness'da BTCUSD bunchalik uzoqqa bormaydi.

Ular repozitoriyda qoladi — kelajakda tarix to'planganda ishlatasiz.

---

## 4-BOSQICH — Demo forward test (Strategy Tester'dan keyin)

3-bosqichda Forward natijasi musbat chiqqan **faqat o'shalarni** demo
hisobga qo'ying:

1. Grafikni oching (to'g'ri simvol + to'g'ri TF)
2. EA'ni tashlang → `Inputs` → `Load` → mos `.set`
3. `Common` → `Allow Algo Trading` ✅
4. Kamida **1 oy** ishlatib turing, hech narsani o'zgartirmang
5. Har hafta hisobot yuboring

**Muhim:** bir vaqtda bir nechta EA ishlatsangiz, har birining `InpMagic`
raqami boshqacha ekaniga ishonch hosil qiling (allaqachon shunday:
20260905–20260910), aks holda ular bir-birining pozitsiyasini yopadi.

---

## NATIJA SHABLONI — har test uchun shuni to'ldiring

Har bir testdan keyin quyidagini nusxa oling, to'ldiring va menga yuboring:

```
=== TEST № 3.__ ===
EA:            ScalpKit_______________
Preset:        ScalpKit_______________.set
Simvol / TF:   ______________ / ______
Davr:          ____-__-__ dan ____-__-__ gacha
Modelling:     Every tick based on real ticks

--- OPTIMIZATION RESULTS (o'rgatish qismi) ---
Savdolar soni:      ______
Net foyda:          ______ USD
Profit factor:      ______
Max drawdown:       ______ %

--- FORWARD RESULTS (ko'rilmagan qism) ← ASOSIYSI ---
Savdolar soni:      ______
Net foyda:          ______ USD
G'alaba foizi:      ______ %
O'rtacha yutuq:     ______ USD
O'rtacha yutqazuq:  ______ USD
Profit factor:      ______
Max drawdown:       ______ %
Eng uzun zarar seriyasi: ______

Izoh (xato bo'lsa, jurnaldagi matn): ______________________
```

### Nimaga qarash kerak (men ham shunga qarayman)

| Belgi | Xulosa |
|---|---|
| Forward savdolari **< 100** | xulosa yo'q — davrni uzaytiring |
| Forward musbat, Optimization'ga yaqin | **sog'lom** |
| Forward musbat, lekin Optimization dan 2–3 barobar past | qisman overfitting |
| **Forward manfiy, Optimization musbat** | **klassik overfitting — ishlatmang** |
| Forward'da profit factor < 1.1 | xarajat yeb qo'ygan |

> Eslatma: `Optimization Results` bu **o'rgatish** natijasi — u har doim
> chiroyli chiqadi, chunki parametrlar o'sha davrga moslangan. Unga
> qaramang. Faqat `Forward Results` haqiqiy javob beradi.

---

## Qisqacha yo'l xaritasi

```
1.1 pytest                      →  kod ishlayaptimi
1.4 mt5-bars                    →  tarix qancha bor
1.5 validate                    →  Python xulosasi
2   MT5 o'rnatish + kompilyatsiya
3.1–3.6 (1-DARAJA)              →  ASOSIY JAVOB shu yerdan chiqadi
3.7–3.12                        →  qo'shimcha
3.13–3.16                       →  HOZIRCHA YO'Q
4   demo forward                →  faqat Forward musbat chiqqanlari
```

---

## Ochiq aytadigan gap

Men bu robotlarning foyda keltirishini kafolatlay olmayman va hech kim
kafolatlay olmaydi. Bu testlarning maqsadi — foydani **isbotlash** emas,
balki **foyda yo'qligini aniqlash**. Agar Forward natijalari manfiy chiqsa,
bu yomon xabar emas: bu sizni real puldan saqlagan qimmatli ma'lumot.

Natijalarni yuboring — men ularni o'qib, qaysi biri haqiqiy, qaysi biri
tasodif ekanini ayta olaman.
