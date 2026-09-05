# Risk boshqaruvi

> Ustunlik sizni boy qiladi. Risk boshqaruvi sizni **o'yinda saqlaydi**.
> Ikkinchisi birinchisidan muhimroq: ustunligi bor, lekin hajmi noto'g'ri
> savdogar baribir hisobini yo'qotadi.

---

## 1. Beshta himoya qatlami

Bu qatlamlar `scalpkit/risk.py` da kod sifatida amalga oshirilgan —
ular tavsiya emas, backtestda ham majburiy bajariladi.

| # | Qoida | Standart qiymat | Nima uchun |
|---|---|---|---|
| 1 | Savdo boshiga risk | **0.5 %** | 10 ta ketma-ket zarar = −5 %, tiklanadigan |
| 2 | Kunlik zarar chegarasi | **−3 %** | yomon kun yomon haftaga aylanmasin |
| 3 | Ketma-ket zararlar | 3 ta → **2 soat** tanaffus | "tilt" ga qarshi |
| 4 | Drawdownda risk | −8 % da **yarmiga** | chuqurlikda avtomatik sekinlashuv |
| 5 | Kunlik savdolar | maksimal **8** | ortiqcha savdoga to'siq |

Har bir zarardan keyin ham **30 daqiqa** majburiy tanaffus bor.

---

## 2. Nima uchun aynan 0.5 %

Ketma-ket zararlar tasodifiy emas — ular **muqarrar**. 42 % g'alaba
foizli tizimda 100 ta savdo ichida 8 ta ketma-ket zarar ehtimoli ~50 %.

| Savdo boshiga risk | 10 ketma-ket zarar | 15 ketma-ket zarar |
|---|---|---|
| 0.5 % | −4.9 % | −7.2 % |
| 1.0 % | −9.6 % | −14.0 % |
| 2.0 % | −18.3 % | −26.1 % |
| 5.0 % | −40.1 % | −53.7 % |

−40 % dan chiqish uchun **+67 %** kerak. −50 % dan chiqish uchun **+100 %**.
Katta risk sizni matematik tuzoqqa soladi.

**Yangi boshlovchilar uchun: birinchi 3 oy 0.25 % dan oshmang.**

---

## 3. Leverage — asosiy chalkashlik

Leverage risk **emas**. Riskni stop masofasi belgilaydi.

```
kapital 10 000 $, BTC 60 000 $

stop 0.3 % ->  hajm = 50/180  = 0.278 BTC -> notional 16 667 $ -> 1.67x
stop 0.8 % ->  hajm = 50/480  = 0.104 BTC -> notional  6 250 $ -> 0.63x
```

Ikkala holatda ham risk **bir xil — 50 $**. Tor stop ko'proq leverage
talab qiladi, shuning uchun `max_leverage: 5` cheklovi bor: likvidatsiya
narxi stopdan uzoqroq turishi kerak.

> **Hech qachon** likvidatsiya narxi stopga yaqin bo'lgan hajmda savdo
> qilmang. 5x da likvidatsiya ~20 % uzoqlikda; bizning eng keng stopimiz
> 2 % — xavfsiz zaxira yetarli.

---

## 4. Kunlik tartib

**Savdodan oldin**
1. `python -m scalpkit costs` — o'z tarifingizni kiritganingizga ishonch hosil qiling
2. Bugungi kapitalni yozib qo'ying → kunlik chegara = kapital × 0.97
3. Yuqori ta'sirli yangiliklar (FOMC, CPI) vaqtini tekshiring — 30 daqiqa oldin
   va keyin savdo qilmang

**Savdo davomida**
4. Har savdodan oldin: stop va hajmni **oldindan** hisoblang
5. Order qo'yilishi bilan **stop ham qo'yiladi** — "keyin qo'yaman" degan narsa yo'q
6. Stopni **hech qachon** zarar tomonga surmang

**Kun oxirida**
7. Barcha savdolarni jurnalga yozing: sabab, R natijasi, qoida buzildimi
8. Kunlik chegaraga yetgan bo'lsangiz — kompyuterni yoping. Bahs yo'q.

---

## 5. Statistik haqiqat

Ustunlik **uzoq muddatda** namoyon bo'ladi:

| Savdolar soni | Natijaning ishonchliligi |
|---|---|
| 10 | butunlay tasodif |
| 50 | hali ham asosan shovqin |
| 100 | dastlabki tasavvur |
| **200+** | statistik ma'noli |

Kuniga 2 savdoda 200 ta savdo uchun **100 kun** kerak. Shu vaqtgacha
strategiyani o'zgartirmang — bu eng keng tarqalgan xato.

Natijangizni tekshiring:
```bash
python -m scalpkit montecarlo --trades out/bt/trades.csv
```
Agar 95 % ishonch oralig'i nolni o'z ichiga olsa — ustunligingiz
isbotlanmagan, hajmni oshirmang.

---

## 6. Psixologik qoidalar

| Holat | To'g'ri harakat |
|---|---|
| Ketma-ket 3 zarar | Kod majburan to'xtatadi. **Chetlab o'tmang.** |
| "Yo'qotganni qaytaraman" | Bu tilt. Kunni yoping. |
| Signal yo'q, lekin zerikdim | Kutish ham pozitsiya. |
| Savdo yaxshi ketyapti, hajmni oshiray | Rejadagi hajm o'zgarmaydi. |
| Strategiya 2 hafta ishlamadi | 200 ta savdodan oldin xulosa yo'q. |

---

## 7. Real savdoga o'tish bosqichlari

```
1-bosqich  Backtest         -> walkforward OOS musbatmi?
2-bosqich  Qog'ozda savdo   -> 1 oy, kamida 40 savdo
3-bosqich  Minimal hajm     -> 0.1 % risk, 1 oy
4-bosqich  Yarim hajm       -> 0.25 % risk, 1 oy
5-bosqich  To'liq hajm      -> 0.5 % risk
```

Har bosqichda natija kutilgandan yomon bo'lsa — **bir bosqich orqaga
qayting**. Shoshilish bu yerda eng qimmat xato.
