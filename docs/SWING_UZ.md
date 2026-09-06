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

Oltinda ham xuddi shunday (17x). Ma'nosi: **M5 da ishlashi uchun 0.10R
ustunlik kerak bo'lgan strategiya D1 da 0.01R bilan ham ishlaydi.**

Shuning uchun M5 da ishlamaydigan g'oya H4 da ishlashi mumkin — bozor
o'zgargani uchun emas, xarajat to'sig'i qulagani uchun.

O'zingiz ko'ring:

```bash
python -m scalpkit profiles
```

---

## 2. Ikkita strategiya

| | `momentum_pullback` | `donchian_breakout` |
|---|---|---|
| Turi | trend ichida qaytishni kutish | kanal buzilishi |
| Kirish | EMA21 ga qaytgach reclaim | N-bar cho'qqisi buzilganda |
| Maqsad | TP1 1.5R + TP2 3-3.5R | **YO'Q** |
| Chiqish | trailing + vaqt stopi | trailing + teskari kanal |
| Tabiati | ko'p savdo, o'rtacha payoff | kam savdo, katta dum |
| Tavsiya etilgan TF | **M5, M15** | **M15, H1, H4, D1** |

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
> standart qiymatlar (long −0.012 %/kun) taxminiy. MT5 da:
> Market Watch → instrument → o'ng tugma → Specification → Swap.

BTC perpetual'da swap emas, **funding** bor (0.01 %/8 soat) — u ham
modellashtirilgan.

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

### MetaTrader 5

Ikkita swing EA'si:

| Fayl | Instrument | Magic |
|---|---|---|
| `ScalpKit_BTC_Trend.mq5` | BTCUSD | 20260907 |
| `ScalpKit_XAU_Trend.mq5` | XAUUSD | 20260908 |

Timeframe **grafikdan** olinadi, parametrlar esa presetdan:

```
mql5/Presets/ScalpKit_BTC_Trend_H4.set
mql5/Presets/ScalpKit_XAU_Trend_D1.set   ... va h.k.
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

## 7. Halol ogohlantirish

Bu strategiyalarning foyda keltirishi **isbotlanmagan**. O'lchanган va
isbotlangan narsa:

* xarajatning timeframe bo'yicha 17-19 barobar kamayishi;
* maqsad qo'yish trend-following'ga zarar yetkazishi;
* har bir profil o'z bozorida to'g'ri kalibrlangani.

Ustunlikning **borligini** faqat siz aniqlay olasiz — real ma'lumotda
`validate` yoki MT5 Strategy Tester (Forward 1/4) bilan. Sintetik
generatordagi natijalar martingale ma'lumotda olingan va foyda dalili emas.
