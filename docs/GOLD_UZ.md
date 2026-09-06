# XAUUSD (oltin) M5 — nima uchun alohida sozlama kerak

Strategiya mantig'i BTC bilan **bir xil** (impuls → orqaga qaytish →
davom etish). Farq faqat kalibrlashda — lekin bu farq hal qiluvchi.

---

## 1. Asosiy raqam

| | BTCUSD | XAUUSD |
|---|---|---|
| Narx | ~65 000 | ~2 650 |
| M5 ATR(14) | ~145 (**0.22 %**) | ~1.80 (**0.068 %**) |
| Tipik spread | ~20 (0.031 %) | ~0.30 (0.011 %) |
| Lot hajmi | 1 BTC | **100 unsiya** |
| Savdo vaqti | 24/7 | **Du–Ju**, kunlik rollover tanaffusi bilan |

Oltin volatilligi BTC dan **~3.5 barobar past**. Shuning uchun BTC
sozlamalarini oltinga qo'yish robotni butunlay jim qoldiradi:

```
BTC filtri:  min_atr_pct = 0.20 %
Oltin ATR%:  mediani      0.068 %
Natija    :  oltin barlarining ~1 % i o'tadi -> deyarli hech qachon savdo yo'q
```

Bu xato jim kechadi — kod xato bermaydi, EA jurnalga hech nima yozmaydi,
siz esa sababini bilmaysiz. Shuning uchun profillar tizimi kiritilgan.

Farqni o'zingiz ko'ring:

```bash
python -m scalpkit profiles
```

---

## 2. Oltin uchun kalibrlangan qiymatlar

| Parametr | BTC | Oltin | Nima uchun |
|---|---|---|---|
| `min_atr_pct` | 0.0020 | **0.00045** | ATR% taqsimotining bir xil kvantili (~60 % barlar o'tadi) |
| `max_atr_pct` | 0.0120 | **0.0035** | yangilik portlashlarini kesish |
| `min_stop_pct` | 0.0015 | **0.0004** | aks holda majburiy chegara tabiiy stopni 1.4x kengaytiradi |
| `max_stop_pct` | 0.0200 | **0.0060** | |
| Seans (UTC) | 06–22 | **07–20** | Osiyo seansi sust; 21:00 — rollover |
| `max_leverage` | 5 | **10** | oltinda notional kichikroq |
| Kun / yil | 365 | **252** | CAGR va Sharpe to'g'ri hisoblanishi uchun |
| Komissiya | 5 bps (Binance) | **0.57 bps** | oltinda xarajat spread, komissiya emas |
| Sirpanish (stop) | 3.0 bps | **0.8 bps** | oltin tiki $0.01 — BTC bahosi 30x ortiqcha edi |

`adx_min` va butun setup/chiqish bloki **BTC bilan bir xil qoldirilgan** —
ularni oltin uchun o'zgartirishga o'lchangan asos topilmadi, asossiz farq
esa faqat overfitting xavfini oshiradi.

### Volatilitet chegarasi qanday tanlangan

Taxmin bilan emas, **xarajatdan** kelib chiqib:

```
cost_R = spread / (min_sl_atr x 1.4 x ATR) <= 0.25
0.30 / (1.0 x 1.4 x ATR) <= 0.25   =>   ATR >= 0.86 = 0.032 % (narx $2650 da)
```

Tanlangan **0.045 %** bundan 1.4 barobar yuqori — xavfsiz zaxira
qoldiradi va ayni paytda barlarning ~60 % ini o'tkazadi.

---

## 3. Hafta chegarasi — oltinning o'ziga xos qoidasi

Kripto 24/7 savdo qiladi, oltin esa yo'q. Bu ikki xavf tug'diradi:

1. **Hafta oxiri gapi.** Juma kechqurun ochilgan pozitsiya dushanba
   narx sakragan holda ochiladi. Stop-loss **ishlamaydi** — u gapdan
   o'tib ketadi va zarar rejalashtirilgandan bir necha barobar katta
   bo'lishi mumkin.
2. **Ochilish spreadi.** Hafta boshida spread bir necha barobar keng.

Shuning uchun oltin profilida:

```
juma 19:00 UTC dan keyin  -> yangi savdo YO'Q
                          -> kutayotgan limit orderlar BEKOR qilinadi
                          -> ochiq pozitsiya YOPILADI
hafta ochilishidan keyin  -> birinchi 6 bar (30 daqiqa) o'tkazib yuboriladi
```

> **Nozik nuqta:** chegara *kirish* nuqtasida tekshiriladi, signal
> nuqtasida emas. Signal juma 18:55 da ruxsat etilgan bo'lishi mumkin,
> lekin limit order 19:00 dan keyin to'ldirilsa, pozitsiya hafta oxiriga
> qolib ketadi. Backtest dvigateli ham, MQL5 EA ham buni to'g'ri
> bajaradi (`tests/test_profiles.py` tekshiradi).

---

## 4. Ishlatish

### Python

```bash
# Ma'lumot MT5 dan (Windows) yoki o'z manbangizdan
python -m scalpkit mt5-bars --symbol XAUUSD --count 200000 --out data/XAUUSD_5m.csv

# Backtest — profil simvoldan avtomatik aniqlanadi
python -m scalpkit backtest --profile xauusd --data data/XAUUSD_5m.csv

# To'liq tekshiruv va qat'iy xulosa
python -m scalpkit validate --profile xauusd --data data/XAUUSD_5m.csv --spread 0.30

# MT5 dan hammasini bitta buyruqda (spread avtomatik o'lchanadi)
python -m scalpkit mt5-validate --symbol XAUUSD --count 200000
```

Internetsiz sinash uchun:

```bash
python -m scalpkit synth --asset gold --bars 100000 --out data/SYNTH_GOLD_5m.csv
python -m scalpkit backtest --profile xauusd --data data/SYNTH_GOLD_5m.csv
```

### MetaTrader 5

`ScalpKit_XAU_Scalp.mq5` ni XAUUSD M5 grafigiga tashlang (preset: `ScalpKit_XAU_Scalp_5M.set`). To'liq qo'llanma:
[MQL5_UZ.md](MQL5_UZ.md).

BTC va oltin EA'larini bir vaqtda ishlatish mumkin — turli magic
raqamlaridan foydalanadi (20260905 / 20260906).

---

## 5. Kutilishi mumkin bo'lgan xulq

| Ko'rsatkich | Diapazon |
|---|---|
| Savdolar | 0.3–0.8 / kun |
| Stop masofasi | 0.08–0.25 % (≈ $2–7) |
| Pozitsiya davomiyligi | 40–120 daqiqa |
| Xarajat | 0.10–0.20 R (spread $0.30 da) |

**Muhim: oltin BTC dan kamroq savdo beradi.** Sabab ikkita — savdo
oynasi qisqaroq (13 soat × 5 kun = 65 soat/hafta, BTC da 112 soat) va
seans filtri qattiqroq.

Bu validatsiya uchun amaliy oqibat tug'diradi: ishonchli xulosa uchun
**100+ OOS savdo** kerak, ya'ni kuniga 0.4 savdo bilan **~250 savdo
kuni** = 1 yildan ortiq OOS ma'lumot. O'rgatish davri bilan birga
**kamida 2 yillik M5 tarix** kerak bo'ladi.

MT5 da tarix yetarli bo'lishi uchun: Tools → Options → Charts →
"Max bars in chart" = `9999999999`, so'ng XAUUSD M5 grafikda **Home**
tugmasi bilan orqaga aylantiring.

---

## 6. Halol ogohlantirish

Bu profil oltinning **volatilitet va kalendar** xususiyatlariga
moslashtirilgan. Bu strategiyaning oltinda foyda keltirishini
**isbotlamaydi** — uni faqat siz `validate` yoki MT5 Strategy Tester
(Forward 1/4) bilan aniqlay olasiz.

Repodagi sintetik oltin generatori tizimni sinash uchun; unda M5 trend
ustunligi ataylab yo'q, shuning uchun undan olingan raqamlar foyda
dalili emas.
