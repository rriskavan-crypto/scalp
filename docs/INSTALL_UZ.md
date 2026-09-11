# O'rnatish — Windows (MT5 ishlaydigan kompyuter)

Ikki qadam: fayllarni olish, so'ng bitta faylni ikki marta bosish.

---

## 1-QADAM — fayllarni yuklab olish

### Oson yo'l (git kerak emas)

Brauzerda oching:

```
https://github.com/rriskavan-crypto/scalp/archive/refs/heads/claude/m5-scalping-strategy-5z9m9e.zip
```

ZIP yuklanadi. Uni masalan `C:\scalp\` ga chiqaring (arxivni ochib,
ichidagi papkani ko'chiring).

> Papka yo'lida **bo'sh joy va kirill harflar bo'lmasin**. `C:\scalp`
> yaxshi, `C:\Users\Мой диск\yangi papka` muammo beradi.

### Yaxshiroq yo'l (keyin yangilash oson bo'ladi)

Agar git o'rnatilgan bo'lsa, `cmd` da:

```cmd
cd C:\
git clone -b claude/m5-scalping-strategy-5z9m9e https://github.com/rriskavan-crypto/scalp.git
```

Keyinchalik yangilash uchun shu papkada: `git pull`

---

## 2-QADAM — o'rnatuvchini ishga tushirish

Papkada **`install_windows.bat`** faylini toping va **ikki marta bosing**.

U o'zi quyidagilarni qiladi:

| Qadam | Nima bo'ladi |
|---|---|
| 1 | Python topadi va versiyasini tekshiradi (3.10+ kerak) |
| 2 | `.venv` virtual muhitini yaratadi |
| 3 | `pip` ni yangilaydi |
| 4 | numpy, pandas, PyYAML, requests, pytest, **MetaTrader5** ni o'rnatadi |
| 5 | 302 ta testni ishga tushiradi |
| 6 | `scalpkit.bat` yorlig'ini yaratadi |

Oxirida `HAMMA TEST O'TDI` yozuvi chiqishi kerak. Chiqmasa — oynadagi
matnni menga yuboring.

### Agar "Python topilmadi" desa

https://www.python.org/downloads/ dan Python 3.11 yoki 3.12 ni yuklang.
O'rnatishda birinchi oynadagi **"Add python.exe to PATH"** katakchasini
albatta belgilang. Keyin `install_windows.bat` ni qaytadan bosing.

> **64-bitli Python kerak.** MT5 terminali 64-bitli, shuning uchun
> `MetaTrader5` paketi 32-bitli Python'ga o'rnatilmaydi. python.org
> sahifasida "Windows installer (64-bit)" ni tanlang.

---

## 3-QADAM — ishlayotganini tekshirish

Papkada `cmd` oching (manzil qatoriga `cmd` yozib Enter bosing) va:

```cmd
scalpkit profiles
```

12 qatorli jadval chiqishi kerak. Chiqsa — o'rnatish tugadi.

---

## Buyruqlar

Hammasi `scalpkit` bilan boshlanadi (papka ichidan ishlatiladi):

```cmd
REM Profillar va xarajat arifmetikasi
scalpkit profiles
scalpkit costs --profile btcusd_5m
scalpkit costs --profile xauusd_5m

REM MT5 ga ulanish tekshiruvi (MT5 terminali ochiq bo'lsin)
set MT5_PASSWORD=parolingiz
scalpkit mt5-test --symbol BTCUSD

REM Tarixni CSV ga yuklash
scalpkit mt5-bars --symbol BTCUSD --interval 15m --count 200000 --out data\BTCUSD_15m.csv
scalpkit mt5-bars --symbol XAUUSD --interval 15m --count 200000 --out data\XAUUSD_15m.csv

REM To'liq tekshiruv (walk-forward + qat'iy xulosa)
scalpkit validate --profile btcusd_15m --data data\BTCUSD_15m.csv --strategy donchian_breakout
scalpkit validate --profile xauusd_15m --data data\XAUUSD_15m.csv --strategy donchian_breakout
```

### Parol haqida

`MT5_PASSWORD` ni **har safar yangi `cmd` oynasida** qayta yozish kerak.
Doimiy qilish uchun papkada `.env` fayl yarating:

```
MT5_PASSWORD=parolingiz
MT5_LOGIN=474000791
MT5_SERVER=Exness-MT5Trial15
```

`.env` fayli `.gitignore` da — u hech qachon GitHub'ga ketmaydi.

> Suhbatda yuborgan parolingizni **almashtiring**. Chatda ko'ringan
> har qanday parol ishonchsiz hisoblanadi.

---

## macOS / Linux

```bash
bash install.sh
./scalpkit.sh profiles
```

MT5 ga ulanish (`mt5-test`, `mt5-bars`, `trade`) bu tizimlarda
**ishlamaydi** — `MetaTrader5` paketi faqat Windows uchun mavjud.
Backtest, walk-forward va validate esa to'liq ishlaydi (CSV fayl bilan).

---

## Tez-tez uchraydigan muammolar

| Muammo | Sabab va yechim |
|---|---|
| Oyna ochilib darhol yopilib ketadi | `.bat` ni `cmd` dan ishga tushiring: `install_windows.bat` — xato matni ko'rinadi |
| `MetaTrader5 o'rnatilmadi` | 32-bitli Python. 64-bitlisini o'rnating |
| `scalpkit` buyrug'i topilmadi | `cmd` ni **loyiha papkasida** oching, `install_windows.bat` ni qaytadan bosing |
| `mt5-test`: `IPC initialize failed` | MT5 terminali ochiq bo'lishi kerak, va Tools > Options > Expert Advisors > "Allow algorithmic trading" yoqilgan bo'lsin |
| `mt5-bars`: 0 qator | Grafikda **Home** tugmasini bosib tarixni serverdan torting |
| Testlar yiqildi | Oynadagi matnni menga yuboring |

---

## Nima o'rnatiladi

```
C:\scalp\
├── .venv\                  virtual muhit (o'rnatuvchi yaratadi)
├── scalpkit.bat            qulay yorliq (o'rnatuvchi yaratadi)
├── scalpkit\               asosiy kutubxona
├── tests\                  302 ta test
├── mql5\                   MT5 uchun EA va presetlar
├── docs\                   o'zbekcha qo'llanmalar
└── data\                   CSV fayllar bu yerga tushadi
```

`.venv` papkasi tizimdagi Python'ga tegmaydi — hamma kutubxona shu
papka ichida qoladi. O'chirmoqchi bo'lsangiz butun `C:\scalp` ni
o'chirib tashlash kifoya.
