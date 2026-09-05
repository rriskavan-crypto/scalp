# scalpkit — BTC/USDT M5 skalping strategiyasi va tekshiruv to'plami

**"M5 Momentum Pullback"** — Bitcoin uchun 5 daqiqalik grafikda ishlaydigan
tanlab-skalping strategiyasi, uni **halol tekshirish** vositalari bilan birga.

---

## Avval halol gap

Sizdan so'ralgan savol: *"M5 da foyda keltiradigan eng yaxshi skalping
strategiyasi qaysi?"*

Halol javob uch qismdan iborat:

1. **Kafolatlangan foyda beradigan strategiya mavjud emas.** Kim shunday
   va'da qilsa — sizga bir narsa sotmoqchi.
2. **Lekin M5 skalpingda ishlaydigan va ishlamaydigan tuzilmalarni
   matematika aniq ajratadi.** Ko'pchilik strategiyalar komissiya
   hisobi tufayli yutqazadi, bozorni bilmagani uchun emas.
3. **Shuning uchun bu repoda ikki narsa bor:** to'liq yozilgan strategiya
   *va* uni o'z ma'lumotingizda tekshirib, ustunlik bor-yo'qligini
   isbotlaydigan asboblar.

### Eng muhim raqam

Binance futures VIP0 tarifida bitta to'liq savdo **0.145 %** turadi
(taker 0.05 % × 2 + sirpanish). Foyda esa **R** — stop masofasi — bilan
o'lchanadi:

```
xarajat (R da) = 0.145 % / stop_masofasi_%
```

| Stop masofasi | Xarajat | Zararsizlik uchun kerakli g'alaba % (2R payoff) |
|---|---|---|
| 0.15 % | **0.97 R** | 65.6 % |
| 0.20 % | **0.73 R** | 57.5 % |
| **0.50 %** | **0.29 R** | **43.0 %** |
| 0.80 % | 0.18 R | 39.4 % |

**"Tor stop, kuniga 20 savdo, har biridan 0.2 %"** degan mashhur maslahat
matematik jihatdan yutqazishga mahkum: har savdo 0.73R turadi, bunday
ustunlik M5 da yo'q.

Shuning uchun bu strategiya boshqacha ishlaydi:
**kuniga 1–4 savdo, stop 0.40–0.90 %, pozitsiya 30–120 daqiqa.**

O'zingiz ko'ring:
```bash
python -m scalpkit costs
```

---

## O'rnatish

```bash
git clone <repo>
cd scalp
pip install -r requirements.txt      # numpy, pandas, PyYAML, requests
```

---

## Tez boshlash

```bash
# 1. Real ma'lumot yuklash (kamida 2 yil)
python -m scalpkit fetch --start 2021-01-01 --out data/BTCUSDT_5m.csv

# 2. Xarajat matematikasini ko'rish
python -m scalpkit costs

# 3. Backtest
python -m scalpkit backtest --config config/default.yaml \
    --data data/BTCUSDT_5m.csv --out out/baseline

# 4. ASOSIY TEKSHIRUV — walk-forward
python -m scalpkit walkforward --config config/default.yaml \
    --data data/BTCUSDT_5m.csv --folds 8 --train-days 180 --test-days 45

# 5. Statistik ishonchlilik
python -m scalpkit montecarlo --trades out/baseline/trades.csv

# 6. Jonli signal
python -m scalpkit signal --live
```

Internet yo'q bo'lsa yoki avval tizimni sinab ko'rmoqchi bo'lsangiz:
```bash
python -m scalpkit synth --bars 120000 --out data/SYNTH_5m.csv
python -m scalpkit backtest --data data/SYNTH_5m.csv
```

---

## Strategiya qisqacha

**G'oya:** BTC M5 da vaqtning ~70 % i shovqin. Ustunlik shovqinni bashorat
qilishdan emas, **impulsdan keyingi sayoz orqaga qaytishda** trendga
qo'shilishdan kelib chiqadi.

| Bosqich | Qoida (LONG uchun) |
|---|---|
| **Rejim** | ATR% ∈ [0.20 %, 1.20 %] · ADX ≥ 20 · EMA21>55>200 · H1 ko'tarilishda · UTC 06–22 |
| **Setup** | oxirgi 12 barda impuls · narx EMA21 zonasiga qaytdi · RSI(7) ≤ 45 |
| **Trigger** | `close >` oldingi bar high · `close >` EMA21 · bar tepasida yopildi |
| **Kirish** | limit `trigger_close − 0.15 ATR`, 3 bar amal qiladi |
| **Stop** | `swing_low − 0.25 ATR`, 1.0–2.2 ATR oralig'ida cheklangan |
| **Chiqish** | TP1 +1.5R da 35 % · stop −0.35R ga · +2R da zararsizlikka · trailing 2.5 ATR · TP2 +3.5R |
| **Hajm** | kapitalning 0.5 % i xavfda, maksimal 5x leverage |

SHORT — to'liq oyna aksi.

To'liq spetsifikatsiya: **[docs/STRATEGY_UZ.md](docs/STRATEGY_UZ.md)**

### Chiqish tuzilmasi nima uchun aynan shunday

Klassik "TP1 da yarmini ol, stopni darhol zararsizlikka sur" tuzilmasi
payoff nisbatini buzadi. Ikkala tuzilma bir xil ma'lumotda, bir xil
kirish usulida o'lchangan:

| | Klassik (BE stop) | Bu strategiya |
|---|---|---|
| O'rtacha yutuq | +0.720 R | **+1.303 R** |
| O'rtacha zarar | −1.077 R | −1.272 R |
| Payoff | 0.669 | **1.025** |
| **Zararsizlik uchun kerakli g'alaba** | **59.9 %** | **49.4 %** |

Zararsizlik stopi yutuqlarni nolga aylantiradi, zararlarni esa
o'zgartirmaydi — u tizimni erishib bo'lmaydigan g'alaba foiziga bog'laydi.
59.9 % g'alaba foizi M5 da amalda mavjud emas; 49.4 % esa erishsa bo'ladigan
chegara.

Bu taqqoslash `be_after_tp1` parametri orqali o'zingizda qayta ishlab
chiqariladi — klassik tuzilma kodda saqlab qolingan.

> **Aniqlik uchun:** bu payoff *tuzilmasi* taqqoslashi, foyda va'dasi emas.
> Ustunlik bo'lmagan ma'lumotda hech qanday chiqish tuzilmasi foyda
> yaratmaydi — u faqat qanday g'alaba foizi talab qilinishini o'zgartiradi.
> Tuzilma tuzatilishi **haqiqiy ustunlik mavjud bo'lganda** natija beradi.

---

## Nima uchun bu backtestga ishonish mumkin

Backtest dvigateli ataylab **pessimistik** qilingan:

| Qoida | Ta'siri |
|---|---|
| Signal bar yopilishida, ijro keyingi bar ochilishida | kelajakka qarash yo'q |
| Bir barda stop ham, TP ham tegilsa → **stop** hisoblanadi | natijani kamaytiradi |
| Bar stopdan narida ochilsa → ochilish narxida ijro | gap zarari real |
| Har ijroda komissiya + sirpanish | 0.30R (market) / 0.24R (limit) har savdoda |
| Perpetual funding hisoblanadi | uzoq pozitsiyalar uchun |
| Limit orderlar to'ldirilmasligi mumkin | ~11 % savdo o'tkazib yuboriladi |

Dvigatel matematikasi testlar bilan tasdiqlangan: nol xarajatda to'liq
stop **aynan −1.000R** beradi.

```bash
python -m pytest tests/ -q      # 54 test
```

---

## Loyiha tuzilishi

```
scalpkit/
  config.py          xarajat / risk / strategiya sozlamalari
  indicators.py      EMA, RSI, ATR, ADX, Donchian, VWAP (barchasi sabab-oqibatli)
  features.py        indikator matritsasi + H1 moslash (kelajaksiz)
  strategies/
    momentum_pullback.py   ASOSIY STRATEGIYA
  engine/
    backtest.py      bar-bar dvigatel, bracket orderlar, limit kirish
    broker.py        komissiya, sirpanish, funding
  risk.py            hajm, kunlik chegara, tanaffuslar
  metrics.py         ekspektatsiya, payoff, Sharpe, drawdown
  costs.py           zararsizlik matematikasi
  walkforward.py     ASOSIY VALIDATSIYA
  optimize.py        parametr qidiruvi + barqarorlik tekshiruvi
  montecarlo.py      bootstrap, risk of ruin, statistik ishonchlilik
  live.py            jonli signal (faqat o'qiydi, order yubormaydi)
  cli.py             buyruqlar qatori
docs/
  STRATEGY_UZ.md     to'liq qoidalar
  RISK_UZ.md         risk boshqaruvi
  VALIDATION_UZ.md   tekshirish tartibi
  CHECKLIST_UZ.md    kundalik nazorat ro'yxati
```

---

## Muhim ogohlantirishlar

1. **Bu moliyaviy maslahat emas.** Kripto savdosi kapitalning to'liq
   yo'qolishiga olib kelishi mumkin. Yo'qotishga tayyor bo'lmagan pul
   bilan savdo qilmang.

2. **Repodagi standart parametrlar — boshlang'ich nuqta, yakuniy javob emas.**
   Ular real BTC ma'lumotida optimallashtirilmagan; ularni o'zingiz
   `walkforward` bilan tekshirishingiz kerak.

3. **Sintetik generatordan olingan natijalar foyda dalili emas.**
   Generatorda M5 trend ustunligi ataylab yo'q — u faqat tizimning
   mexanikasini tekshirish uchun.

4. **Ustunlik isbotlanishi kerak.** `walkforward` OOS ishonch oralig'i
   nolni o'z ichiga olsa — ustunlik yo'q. Bunday holatda hajmni
   oshirmang; strategiyani qayta ko'rib chiqing.

5. **`live.py` hech qanday order yubormaydi.** U faqat ochiq ma'lumotni
   o'qiydi va signalni ko'rsatadi. API kaliti talab qilinmaydi.
