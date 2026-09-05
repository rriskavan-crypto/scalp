# Strategiyani tekshirish tartibi

> Bitta chiroyli backtest egri chizig'i hech narsani isbotlamaydi.
> Yetarlicha parametr sinab ko'rilsa, **sof shovqinda ham** ajoyib
> natija topiladi. Quyidagi tartib shu tuzoqdan qutqaradi.

---

## Bosqich 1 — Real ma'lumot yuklash

```bash
python -m scalpkit fetch --symbol BTCUSDT --interval 5m \
    --start 2021-01-01 --market futures --out data/BTCUSDT_5m.csv
```

Kamida **2 yil** kerak. Bu davr ichida turli rejimlar bo'lishi shart:
ko'tarilish (2021, 2023–24), tushish (2022), yon harakat (2019).
Faqat bull bozorda tekshirilgan strategiya ayiq bozorda qulaydi.

---

## Bosqich 2 — Xarajatlarni to'g'ri kiritish

```bash
python -m scalpkit costs
```

`config/default.yaml` da **o'z haqiqiy tarifingizni** yozing. Noto'g'ri
komissiya butun backtestni yolg'onga aylantiradi — bu eng keng tarqalgan
va eng qimmat xato.

Shubha bo'lsa, xarajatni **oshirib** qo'ying. Yomon syurpriz real
savdoda emas, backtestda bo'lgani yaxshi.

---

## Bosqich 3 — Boshlang'ich backtest

```bash
python -m scalpkit backtest --config config/default.yaml \
    --data data/BTCUSDT_5m.csv --out out/baseline
```

Hisobotda avval shularga qarang:

| Ko'rsatkich | Nima demoqchi |
|---|---|
| `Ekspektatsiya` | musbat bo'lmasa — qolgani ahamiyatsiz |
| `Yalpi (xarajatsiz)` | xarajat qancha yeyayotganini ko'rsatadi |
| `t-statistika` | \|t\| < 2 bo'lsa natija shovqin |
| `Zararsizlik nuqtasi` | g'alaba foizi shundan yuqorimi? |
| `Savdolar soni` | 200 dan kam bo'lsa xulosa chiqarmang |

---

## Bosqich 4 — Walk-forward (ASOSIY TEKSHIRUV)

```bash
python -m scalpkit walkforward --config config/default.yaml \
    --data data/BTCUSDT_5m.csv \
    --folds 8 --train-days 180 --test-days 45 --out out/wf
```

Parametrlar **har safar faqat o'tmishdan** tanlanadi, natija esa faqat
ko'rilmagan kelajakdan yig'iladi.

**Qanday o'qish kerak:**

| Belgi | Xulosa |
|---|---|
| OOS ekspektatsiya musbat, `WF samaradorligi > 0.5` | sog'lom |
| OOS musbat, lekin samaradorlik < 0.3 | qisman overfitting |
| OOS manfiy, IS musbat | **klassik overfitting — ishlatmang** |
| Ishonch oralig'i nolni o'z ichiga oladi | ustunlik isbotlanmagan |
| Bosqichlar orasida natija juda o'zgaruvchan | barqaror emas |

---

## Bosqich 5 — Barqarorlik

```bash
python -m scalpkit optimize --data data/BTCUSDT_5m.csv \
    --max-combos 400 --out out/opt.csv
```

Chiqishdagi **barqarorlik jadvaliga** qarang. Yaxshi parametr
**plato** hosil qiladi:

```
YAXSHI (plato)              YOMON (cho'qqi)
adx_min  ort_expectancy     adx_min  ort_expectancy
16       0.08               16       -0.05
20       0.11               20        0.31   <- faqat shu yerda
24       0.09               24       -0.03
28       0.07               28       -0.08
```

Ikkinchi holat — shovqinga moslashish. Bunday parametr real savdoda ishlamaydi.

---

## Bosqich 6 — Monte Carlo

```bash
python -m scalpkit montecarlo --trades out/wf/wf_oos_trades.csv --sims 10000
```

Diqqat qiling:

- **p-qiymat** — 0.05 dan katta bo'lsa, ustunlik isbotlanmagan
- **95 % ishonch oralig'i** — nolni o'z ichiga olsa, ustunlik isbotlanmagan
- **p5 drawdown** — mana shunga tayyor bo'lishingiz kerak, median emas
- **Risk of ruin** — 1 % dan yuqori bo'lsa, riskni kamaytiring

---

## Bosqich 7 — Rejimlar bo'yicha ajratish

```bash
python -m scalpkit backtest --data data/BTCUSDT_5m.csv --start 2022-01-01 --end 2022-12-31   # ayiq
python -m scalpkit backtest --data data/BTCUSDT_5m.csv --start 2023-01-01 --end 2023-12-31   # tiklanish
python -m scalpkit backtest --data data/BTCUSDT_5m.csv --start 2024-01-01 --end 2024-12-31   # buqa
```

Strategiya **hamma yilda ham foyda keltirishi shart emas**, lekin biror
yilda halokatli bo'lmasligi kerak. Faqat bitta yil hisobiga ishlaydigan
natija — bu ustunlik emas, omad.

---

## Bosqich 8 — Sezgirlik

Xarajatni oshirib ko'ring:

```bash
python -m scalpkit backtest --data data/BTCUSDT_5m.csv --taker-bps 8
```

Komissiya 0.05 % dan 0.08 % ga oshganda natija qulasa — ustunligingiz
juda ingichka va real savdoda omon qolmaydi.

Kirish usulini ham solishtiring:

```bash
python -m scalpkit backtest --data data/BTCUSDT_5m.csv --entry-mode market
python -m scalpkit backtest --data data/BTCUSDT_5m.csv --entry-mode limit
```

---

## Yakuniy nazorat ro'yxati

Real pul bilan savdo qilishdan oldin **hammasi** bajarilgan bo'lsin:

- [ ] Kamida 2 yillik real ma'lumot
- [ ] Haqiqiy komissiya tarifi kiritilgan
- [ ] Walk-forward OOS ekspektatsiyasi musbat
- [ ] OOS savdolar soni ≥ 200
- [ ] Monte Carlo p-qiymati < 0.05
- [ ] 95 % ishonch oralig'i to'liq noldan yuqorida
- [ ] Parametrlar plato hosil qiladi
- [ ] Kamida 3 xil bozor rejimida sinalgan
- [ ] Xarajat 1.5x ga oshirilganda ham musbat
- [ ] p5 drawdown siz uchun qabul qilarli
- [ ] 1 oy qog'ozda savdo qilingan

**Bittasi bajarilmagan bo'lsa — real pul bilan boshlamang.**
