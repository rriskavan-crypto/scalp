# Savdo nazorat ro'yxati (chop etib, stol ustiga qo'ying)

---

## A. Kun boshlanishida

- [ ] Kapitalni yozdim: `____________`
- [ ] Kunlik zarar chegarasi (−3 %): `____________`
- [ ] Bugungi yangiliklar tekshirildi (FOMC / CPI / NFP)
- [ ] Grafikda H1 yo'nalishini aniqladim: ⬆️ / ⬇️ / ↔️
- [ ] `python -m scalpkit signal --live` ishga tushirildi

---

## B. Har bir savdodan OLDIN

**Rejim (5 ta ham "ha" bo'lishi shart)**

- [ ] ATR% oynada (0.20 %–1.20 %)
- [ ] ADX ≥ 20
- [ ] M5 EMA ketma-ketligi to'g'ri (21 / 55 / 200)
- [ ] H1 yo'nalishi mos
- [ ] Savdo seansi (UTC 06:00–22:00)

**Setup**

- [ ] Oxirgi 12 barda impuls bo'lgan
- [ ] Narx EMA21 zonasiga qaytgan
- [ ] RSI(7) mos darajaga yetgan (long ≤ 45 / short ≥ 55)

**Trigger**

- [ ] Bar oldingi barning high/low ini yopilishda buzdi
- [ ] Bar to'g'ri tomonga yopildi
- [ ] Narx EMA21 dan 1.0 ATR dan uzoq emas

**Ijro**

- [ ] Stop darajasi hisoblandi: `____________`
- [ ] Stop masofasi 0.15 %–2.0 % oralig'ida
- [ ] **Xarajat < 0.35R** (aks holda savdodan voz kechaman)
- [ ] Hajm hisoblandi: `____________`
- [ ] TP1 (`+1.5R`): `____________`
- [ ] TP2 (`+3.5R`): `____________`
- [ ] Limit order + **stop order birga** qo'yildi

---

## C. Savdo davomida

- [ ] Stopni zarar tomonga **surmadim**
- [ ] Rejadan tashqari hajm **qo'shmadim**
- [ ] TP1 da 35 % olindi, stop −0.35R ga surildi
- [ ] +2R dan keyin stop zararsizlikka surildi

---

## D. Savdodan KEYIN — jurnal

| Maydon | Qiymat |
|---|---|
| Sana / vaqt | |
| Yo'nalish | LONG / SHORT |
| Kirish / Stop / Chiqish | |
| Natija (R) | |
| Chiqish sababi | |
| **Barcha qoidalarga amal qildimmi?** | HA / YO'Q |
| Agar YO'Q — qaysi qoida buzildi? | |

> **Eng muhim ustun — oxirgisi.** Qoidaga amal qilib zarar ko'rish
> yaxshi savdo. Qoidani buzib foyda olish — yomon savdo, chunki u
> keyingi safar sizni yo'q qiladi.

---

## E. Kun oxirida

- [ ] Barcha savdolar jurnalga yozildi
- [ ] Kunlik R natijasi: `____________`
- [ ] Qoida buzilishlari soni: `____________`
- [ ] Kunlik chegaraga yetdimmi? Ha bo'lsa — **kompyuter yopiladi**

---

## F. Hafta oxirida

- [ ] Haftalik R: `____________`
- [ ] Savdolar soni: `____________`
- [ ] G'alaba foizi: `____________`
- [ ] Qoidaga rioya foizi: `____________` ← **90 % dan past bo'lsa, muammo strategiyada emas, intizomda**
- [ ] 200 ta savdo to'plandimi? Yo'q bo'lsa — **hech narsani o'zgartirmayman**

---

## TO'XTASH SIGNALLARI

Quyidagilardan biri sodir bo'lsa, savdoni to'xtatib, qayta baholang:

- Kunlik chegara ketma-ket 3 kun urildi
- Haftalik drawdown −8 % dan oshdi
- Qoidaga rioya 80 % dan pastga tushdi
- 50 ta savdodan keyin natija backtestdan **2 barobar** yomonroq
- "Yo'qotganni qaytarish" fikri paydo bo'ldi
