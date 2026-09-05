# MetaTrader 5 (Exness) ga ulanish va jonli savdo

---

## 0. Talablar — buni o'qimasdan davom etmang

| Talab | Sabab |
|---|---|
| **Windows** | `MetaTrader5` Python paketi faqat Windows uchun mavjud |
| **MT5 terminali ochiq** | API tarmoq orqali emas, shu kompyuterdagi terminalga ulanadi |
| **Hisobga kirilgan** | terminal serverga ulangan bo'lishi kerak |
| **Algo savdo yoqilgan** | Tools → Options → Expert Advisors → ☑ Allow algorithmic trading |
| **Python 3.10+** | |

> **Linux/macOS da ishlamaydi.** Bu cheklov MetaQuotes tomonidan qo'yilgan —
> aylanib o'tishning to'g'ri yo'li yo'q. Mac'da Parallels/VM ichida Windows
> kerak bo'ladi.

---

## 1. O'rnatish

```bat
pip install -r requirements.txt
pip install MetaTrader5
```

---

## 2. Hisob ma'lumotlari — parolni HECH QACHON faylga yozmang

Parol faqat muhit o'zgaruvchisidan o'qiladi:

```bat
set MT5_LOGIN=00000000
set MT5_SERVER=Exness-MT5Trial00
set MT5_PASSWORD=sizning_parolingiz
```

PowerShell'da:

```powershell
$env:MT5_LOGIN="00000000"
$env:MT5_SERVER="Exness-MT5Trial00"
$env:MT5_PASSWORD="sizning_parolingiz"
```

Doimiy qilish uchun `.env` faylidan foydalaning (u `.gitignore` da):

```
MT5_LOGIN=00000000
MT5_SERVER=Exness-MT5Trial00
MT5_PASSWORD=sizning_parolingiz
```

> **Parolingiz chatda, skrinshotda yoki xabarda ko'ringan bo'lsa — darhol
> o'zgartiring.** Demo hisob bo'lsa ham, bu odat bo'lib qolishi kerak.

---

## 3. Birinchi qadam — ulanishni tekshirish

```bat
python -m scalpkit mt5-test --symbol BTCUSD
```

Bu buyruq **hech qanday order yubormaydi**. U quyidagilarni ko'rsatadi:

```
[1] HISOB          — balans, ekviti, leverage, savdo ruxsati, server vaqti
[2] INSTRUMENT     — lot hajmi, min lot, qadam, stops level
[3] SPREAD/XARAJAT — jonli spread va u necha R turishini
[4] BARLAR         — nechta M5 bar olingani
[5] JORIY SIGNAL   — barcha shartlar ro'yxati va signal bor-yo'qligi
[6] HAJM HISOBI    — signal bo'lsa, aniq lot va risk
```

### [3] bo'limi eng muhimi

Exness'da komissiya odatda yo'q — **butun xarajat spreadga singdirilgan**.
Bu Binance'dan tubdan farq qiladi va strategiyaning ishlashini hal qiladi:

| Spread (BTC ~60 000) | Xarajat (stop 1.6 ATR ≈ $240) | Xulosa |
|---|---|---|
| $5 | 0.02 R | yaxshi |
| $15 | 0.06 R | yaxshi |
| $30 | 0.13 R | yaxshi |
| $60 | 0.25 R | qabul qilarli |
| $100 | 0.42 R | **savdo qilmang** |

> To'liq savdo **bir** spread turadi (ask'da olib, bid'da sotasiz) —
> ikki emas. Komissiya esa har tomon uchun alohida hisoblanadi.

Kod xarajat **0.40R dan oshsa savdoni avtomatik rad etadi**.

> Exness Standard hisobida BTCUSD spreadi ko'pincha keng. Raw Spread yoki
> Zero hisobi arzonroq chiqishi mumkin — `--commission` bilan komissiyani
> ham hisobga oling:
> ```bat
> python -m scalpkit mt5-test --symbol BTCUSD --commission 3.5
> ```

---

## 4. Ikkinchi qadam — BITTA BUYRUQ bilan to'liq tekshiruv

Bu asosiy savolga javob beradi: **strategiya sizning brokeringizda pul
keltiradimi?**

```bat
python -m scalpkit mt5-validate --symbol BTCUSD --count 200000
```

Buyruq ketma-ket bajaradi:

1. **Spreadni o'lchaydi** — 10 marta namuna olib, medianasini hisoblaydi
2. **Xarajatni shunga moslaydi** — backtest sizning haqiqiy spreadingiz bilan ishlaydi
3. **Barlarni yuklaydi** va CSV ga saqlaydi
4. **To'liq tarixda backtest** qiladi
5. **Walk-forward** — parametrlar faqat o'tmishdan tanlanadi, natija faqat ko'rilmagan kelajakdan
6. **Monte Carlo** va statistik ishonchlilik testi
7. **QAT'IY XULOSA** chiqaradi

### Xulosa to'rt xil bo'lishi mumkin

| Xulosa | Ma'nosi | Nima qilish kerak |
|---|---|---|
| **SAVDO QILMANG — spread juda keng** | xarajat > 0.40R | boshqa hisob turi yoki yuqoriroq TF |
| **QAROR CHIQARIB BO'LMAYDI** | tarix yoki savdolar kam (< 100 OOS) | ko'proq tarix yuklang |
| **SAVDO QILMANG — ustunlik yo'q** | OOS ekspektatsiya ≤ 0 | real pulga qo'ymang |
| **USTUNLIK ISBOTLANMAGAN** | ishonch oralig'i nolni o'z ichiga oladi | demo'da davom eting |
| **USTUNLIK BOR** | OOS musbat va ishonchli | demo'da 0.1 % risk bilan boshlang |

> **Tarix yetarli bo'lishi uchun:** MT5 grafikda M5 ni ochib, **orqaga
> aylantiring** (Home tugmasi) — terminal tarixni shundan keyin yuklaydi.
> Tools → Options → Charts → "Max bars in chart" ni `9999999999` qiling.
> 180+45 kunlik walk-forward uchun kamida **65 000 M5 bar** kerak.

Ma'lumot allaqachon CSV da bo'lsa, MT5'siz ham ishlatish mumkin:

```bat
python -m scalpkit validate --data data/EXNESS_5m.csv --spread 20
```

---

## 5. Uchinchi qadam — Exness ma'lumotida qo'lda backtest

Brokeringizning **o'z narxlarida** tekshiring — bu Binance ma'lumotidan farq qiladi:

```bat
python -m scalpkit mt5-bars --symbol BTCUSD --count 100000 --out data/EXNESS_BTCUSD_5m.csv
python -m scalpkit backtest --data data/EXNESS_BTCUSD_5m.csv --config config/default.yaml
python -m scalpkit walkforward --data data/EXNESS_BTCUSD_5m.csv --folds 6
```

`config/default.yaml` da xarajatni **spreadga qarab** sozlang. Masalan
spread $20, BTC $60 000 bo'lsa, bir tomonlama xarajat ≈ 0.033 % = 3.3 bps:

```yaml
cost:
  taker_fee_bps: 3.3     # spread / 2, foizda
  maker_fee_bps: 3.3     # MT5 da limit order ham spread to'laydi
  slippage_bps: 1.0
  stop_slippage_bps: 2.0
  apply_funding: false   # Exness'da funding emas, swap bor
```

---

## 6. To'rtinchi qadam — DRY-RUN (order yuborilmaydi)

```bat
python -m scalpkit trade --symbol BTCUSD --once
```

Bir marta ishlaydi va nima qilishini ko'rsatadi. Keyin uzluksiz rejim:

```bat
python -m scalpkit trade --symbol BTCUSD
```

Dastur har yangi **yopilgan** M5 barni kutadi va shundan keyin qaror qabul
qiladi. Bar ichida savdo qilmaydi — signal faqat yopilgan barda haqiqiy.

**Kamida 1 hafta shu rejimda kuzating.** Log'ni saqlang va natijani
backtest bilan solishtiring.

---

## 7. Beshinchi qadam — REAL savdo (faqat demo hisobda boshlang)

```bat
python -m scalpkit trade --symbol BTCUSD --live --risk 0.001
```

`--live` bilan dastur **tasdiqlash so'raydi** — `HA` deb yozishingiz kerak.

Bosqichma-bosqich oshiring:

```
1-hafta   --risk 0.001   (0.1 %)   demo
2-4 hafta --risk 0.0025  (0.25 %)  demo
keyin     --risk 0.005   (0.5 %)   demo, kamida 50 savdo
faqat shundan keyin      real hisob, yana 0.1 % dan
```

---

## 8. Dastur nima qiladi

Har yangi yopilgan M5 barda:

1. **Ochiq pozitsiyani boshqaradi**
   - `+1.5R` da 35 % ini yopadi, stopni `−0.35R` ga suradi
   - `+2R` da stopni zararsizlikka suradi
   - `+1.5R` dan keyin `2.5 ATR` trailing (0.15 ATR dan kichik qadamda surmaydi)
   - 24 bar o'tib savdo `+0.5R` ga yetmagan bo'lsa — yopadi
2. **Muddati o'tgan limit orderlarni bekor qiladi** (3 bar)
3. **Yangi signal bo'lsa** — risk tekshiruvidan o'tkazib order qo'yadi

Holat `state/live_state.json` da saqlanadi — dastur qayta ishga tushsa
ochiq savdoni to'g'ri davom ettiradi. Fayl yo'qolsa ham holatni MT5
pozitsiyasidan (stop masofasidan) tiklaydi.

Dastur **faqat o'z orderlariga tegadi** — `magic = 20260905`. Qo'lda
ochgan pozitsiyalaringizga aralashmaydi.

---

## 9. Xatolar va yechimlari

| Xato | Sabab / yechim |
|---|---|
| `MetaTrader5 paketi topilmadi` | Windows emas, yoki `pip install MetaTrader5` qilinmagan |
| `MT5 terminaliga ulanib bo'lmadi` | Terminal yopiq. Oching va hisobga kiring |
| `retcode=10027` | Algo savdo o'chirilgan → Tools → Options → Expert Advisors |
| `retcode=10016` | SL/TP narxga juda yaqin. Kod avtomatik tuzatadi; qayta chiqsa `stops_level` juda katta |
| `retcode=10014` | Lot qadami noto'g'ri — hisobingiz uchun `volume_step` ni tekshiring |
| `retcode=10019` | Mablag' yetarli emas — riskni kamaytiring |
| `retcode=10018` | Bozor yopiq (dam olish kunlari / texnik tanaffus) |
| `retcode=10030` | To'ldirish rejimi mos emas — kod avtomatik tanlaydi, chiqsa broker bilan bog'laning |
| `'BTCUSD' topilmadi` | Exness'da nom boshqacha bo'lishi mumkin: `BTCUSDm`, `BTCUSD.raw`. MarketWatch'ni tekshiring |
| `hajm minimal lotdan kichik` | Hisob juda kichik yoki stop juda keng. Riskni oshirmang — hisobni to'ldiring |
| `spread juda keng` | Kod sizni himoya qildi. Tinch vaqtni kuting yoki hisob turini o'zgartiring |

---

## 10. Server vaqti

Exness serverlari odatda UTC+0 yoki UTC+3 da ishlaydi. Kod bu farqni
**avtomatik aniqlaydi** va barlarni haqiqiy UTC ga keltiradi — seans
filtri (UTC 06:00–22:00) to'g'ri ishlashi uchun. `mt5-test` chiqishida
`server vaqti: UTC+3` ko'rinishida ko'rsatiladi.

---

## 11. Xavfsizlik qoidalari

1. **Demo bilan boshlang.** Kamida 1 oy.
2. **Dastur ishlaganda kompyuter o'chmasin.** Uzilsa, ochiq pozitsiya
   boshqarilmay qoladi — SL va TP broker tomonida turadi, lekin TP1,
   trailing va vaqt stopi ishlamaydi.
3. **SL har doim order bilan birga qo'yiladi** — brokerda saqlanadi,
   dastur o'chsa ham amal qiladi.
4. **Riskni oshirmang.** Kod 0.5 % dan yuqorisiga ruxsat beradi, lekin
   bu sizga foyda keltirmaydi — faqat drawdownni chuqurlashtiradi.
5. **Kunlik chegara ishlaganda to'xtang.** Dastur to'xtatadi; siz uni
   qayta ishga tushirib chetlab o'tmang.
