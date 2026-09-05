"""Instrument profillari.

Bitta strategiya mantig'i, lekin har bir bozor uchun **alohida kalibrlangan**
parametrlar. Bu shunchaki qulaylik emas — zaruriyat:

    BTCUSD  M5 ATR(14) ~ 0.22 % narxdan
    XAUUSD  M5 ATR(14) ~ 0.07 % narxdan

Ya'ni BTC uchun mo'ljallangan `min_atr_pct = 0.20 %` filtri oltinda
**barcha barlarni bloklaydi**. Xuddi shunday, `min_stop_pct = 0.15 %`
chegarasi oltinda tabiiy stopni 1.4 barobar kengaytirib yuboradi.

Har bir profil quyidagilarni belgilaydi:
  * volatilitet filtrlari — o'sha bozorning ATR taqsimotiga moslangan
  * stop chegaralari     — narx birligiga emas, bozor xarakteriga bog'liq
  * savdo kalendari      — kripto 24/7, oltin dam olish kunlari yopiq
  * seans oynasi         — likvidlik qayerda to'plangani
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .config import Config


@dataclass(frozen=True)
class Calendar:
    """Bozorning ish vaqti — natijani to'g'ri o'lchash uchun zarur."""

    days_per_year: float = 365.0     # yillik ko'rsatkichlarni hisoblash uchun
    trades_weekends: bool = True
    weekend_flat: bool = False       # hafta oxiriga pozitsiyasiz kirish
    week_close_hour_utc: int = 21    # juma shu soatdan keyin yangi savdo yo'q
    week_close_dow: int = 4          # 0 = dushanba, 4 = juma
    week_open_skip_bars: int = 6     # yakshanba ochilishidan keyin kutiladigan barlar

    def describe(self) -> str:
        if self.trades_weekends:
            return "24/7 (dam olish kunlarisiz)"
        return (
            f"Dushanba-Juma, juma {self.week_close_hour_utc:02d}:00 UTC dan keyin "
            f"yangi savdo yo'q"
        )


@dataclass(frozen=True)
class Profile:
    """Bitta instrument uchun to'liq sozlama to'plami."""

    name: str
    symbols: tuple[str, ...]
    description: str
    typical_spread: float            # narx birligida, hujjat va standart uchun
    typical_price: float             # misollar uchun taxminiy narx
    contract_size: float             # 1 lot nechta birlik
    calendar: Calendar
    strategy: dict[str, Any] = field(default_factory=dict)
    risk: dict[str, Any] = field(default_factory=dict)
    cost: dict[str, Any] = field(default_factory=dict)

    def apply(self, cfg: Config) -> Config:
        """Profilni konfiguratsiyaga qo'llaydi (nusxa qaytaradi)."""
        out = Config.from_dict(cfg.to_dict())
        out.symbol = self.symbols[0]
        out.days_per_year = self.calendar.days_per_year
        out.strategy.params = {**cfg.strategy.params, **self.strategy}
        for key, value in self.risk.items():
            setattr(out.risk, key, value)
        for key, value in self.cost.items():
            setattr(out.cost, key, value)
        return out

    def matches(self, symbol: str) -> bool:
        upper = symbol.upper()
        return any(upper.startswith(s.upper()) for s in self.symbols)


# ---------------------------------------------------------------------------
#  KRIPTO — BTC/USD
# ---------------------------------------------------------------------------
# ATR(14) M5 taqsimoti: median ~0.22 %, p75 ~0.28 %, p90 ~0.35 %
# Filtr medianadan biroz past qo'yilgan — trendli, lekin xaotik bo'lmagan
# rejimlarni tanlaydi.
BTCUSD = Profile(
    name="btcusd",
    symbols=("BTCUSD", "BTCUSDT", "BTCUSDm", "BTCUSD.raw"),
    description="Bitcoin — 24/7, yuqori volatilitet, kuchli trend portlashlari",
    typical_spread=20.0,
    typical_price=65_000.0,
    contract_size=1.0,
    calendar=Calendar(days_per_year=365.0, trades_weekends=True, weekend_flat=False),
    strategy={
        "min_atr_pct": 0.0020,
        "max_atr_pct": 0.0120,
        "adx_min": 20.0,
        "session_start_hour": 6,
        "session_end_hour": 22,
        "weekend_flat": False,
    },
    risk={
        "min_stop_pct": 0.0015,
        "max_stop_pct": 0.0200,
        "max_leverage": 5.0,
    },
    cost={
        # Standart — Binance USDⓈ-M futures (VIP0): taker 5 bps, maker 2 bps.
        # BTC ni MT5 brokerida savdo qilsangiz xarajat komissiya emas,
        # spread bo'ladi — `mt5-validate` uni o'lchab avtomatik almashtiradi.
        "taker_fee_bps": 5.0,
        "maker_fee_bps": 2.0,
        "slippage_bps": 1.5,
        "stop_slippage_bps": 3.0,
        "apply_funding": True,       # perpetual funding
    },
)


# ---------------------------------------------------------------------------
#  OLTIN — XAU/USD
# ---------------------------------------------------------------------------
# ATR(14) M5 taqsimoti: median ~0.07 %, p75 ~0.10 %, p90 ~0.14 %
# — BTC dan ~3 barobar past. Barcha volatilitet filtrlari shunga moslangan.
#
# Volatilitet chegarasi XARAJATdan kelib chiqib tekshirilgan:
#   cost_R = spread / (1.6 x ATR) <= 0.25  =>  ATR >= 2.5 x spread
#   spread $0.30 -> ATR >= $0.75 = 0.028 % (narx $2650 da)
# Tanlangan 0.045 % chegarasi bundan 1.6 barobar yuqori — xarajat uchun
# xavfsiz zaxira qoldiradi va ayni paytda barlarning ~60 % ini o'tkazadi
# (BTC profili bilan bir xil tanlovchanlik).
#
# Seans: oltin likvidligi London ochilishidan (07:00 UTC) NY tushigacha
# (20:00 UTC) to'plangan. Osiyo seansi sust — u yerda shovqin ko'p.
# 21:00-23:00 UTC — rollover, spread keskin kengayadi.
XAUUSD = Profile(
    name="xauusd",
    symbols=("XAUUSD", "XAUUSDm", "GOLD", "XAUUSD.raw"),
    description="Oltin — dam olish kunlari yopiq, London/NY seansida faol",
    typical_spread=0.30,
    typical_price=2_650.0,
    contract_size=100.0,
    calendar=Calendar(
        days_per_year=252.0,          # oltin yiliga ~252 kun savdo qiladi
        trades_weekends=False,
        weekend_flat=True,            # juma kechqurun pozitsiyasiz qolish
        week_close_hour_utc=19,       # juma 19:00 UTC dan keyin yangi savdo yo'q
        week_close_dow=4,
        week_open_skip_bars=6,        # yakshanba gapidan keyin 30 daqiqa kutiladi
    ),
    strategy={
        # --- volatilitet: BTC dagidan ~3.5 barobar past ---
        # Chegara BTC bilan bir xil TANLOVCHANLIKDA belgilangan (barlarning
        # ~60 % i o'tadi), narx foizida emas. Dastlab 0.06 % qo'yilgandi —
        # o'lchov ko'rsatdiki, u faqat 45 % ni o'tkazib, savdolar sonini
        # kuniga 0.10 gacha tushirib yuborardi.
        "min_atr_pct": 0.00045,       # 0.045 % — xarajat 0.16R (spread $0.30)
        "max_atr_pct": 0.0035,        # 0.35 % — yangilik portlashlarini kesadi
        "adx_min": 20.0,              # BTC bilan bir xil: ADX taqsimoti ham bir xil
        # --- seans: London ochilishi -> NY tushi ---
        # Bu filtr PRINSIPIAL: oltinning Osiyo seansi haqiqatan sust va
        # spread keng. 21:00-23:00 UTC — rollover, spread keskin kengayadi.
        "session_start_hour": 7,
        "session_end_hour": 20,
        # --- hafta chegarasi ---
        "weekend_flat": True,
        "week_close_hour_utc": 19,
        "week_close_dow": 4,
        "week_open_skip_bars": 6,
        # --- setup va chiqish: BTC bilan bir xil ---
        # Ularni oltin uchun o'zgartirishga o'lchangan asos yo'q, shuning
        # uchun asossiz farq kiritilmaydi.
        "tp2_r": 3.0,                 # oltin trendlari BTC nikidan qisqaroq
        "trail_atr_mult": 2.2,
        "time_stop_bars": 18,         # 90 daqiqa
    },
    risk={
        # Stop chegaralari ham 3+ barobar torroq — aks holda majburiy
        # chegara tabiiy ATR stopini kengaytirib yuboradi
        "min_stop_pct": 0.0004,       # 0.04 %  (~$1.06 narx $2650 da)
        "max_stop_pct": 0.0060,       # 0.60 %  (~$15.9)
        "max_leverage": 10.0,         # oltinda notional kichikroq bo'ladi
    },
    cost={
        # MUHIM: oltin MT5 brokerida savdo qilinadi, u yerda komissiya emas,
        # SPREAD to'lanadi. Bir tomonlama xarajat = spread / 2:
        #     (0.30 / 2) / 2650 x 10000 = 0.57 bps
        # Binance'ning 5 bps kripto tarifi oltinda $2.65 to'liq savdo
        # xarajatini beradi — bu ~$3.90 stopning 0.68R ini yeydi va
        # strategiyani butunlay yaroqsiz qiladi.
        "taker_fee_bps": 0.57,
        "maker_fee_bps": 0.57,        # MT5 da limit order ham spreadni to'laydi
        # Sirpanish mikrostrukturaga bog'liq, narx foiziga emas.
        # Oltin tiki $0.01; stopdagi sirpanish odatda 1-3 tik = $0.01-0.03.
        "slippage_bps": 0.3,          # ~$0.08
        "stop_slippage_bps": 0.8,     # ~$0.21
        "apply_funding": False,       # oltinda funding emas, swap bor
    },
)


PROFILES: dict[str, Profile] = {p.name: p for p in (BTCUSD, XAUUSD)}


def get_profile(name: str) -> Profile:
    key = name.lower().strip()
    if key in PROFILES:
        return PROFILES[key]
    for profile in PROFILES.values():
        if profile.matches(key):
            return profile
    raise KeyError(f"Noma'lum profil '{name}'. Mavjud: {sorted(PROFILES)}")


def profile_for_symbol(symbol: str, default: str = "btcusd") -> Profile:
    """Simvol nomiga qarab profilni topadi (Exness nomlarini ham tushunadi)."""
    for profile in PROFILES.values():
        if profile.matches(symbol):
            return profile
    return PROFILES[default]


def available() -> list[str]:
    return sorted(PROFILES)


def compare_table() -> str:
    """Profillar farqini ko'rsatuvchi jadval — hujjat va tekshiruv uchun."""
    rows = [
        ("Parametr", *[p.name.upper() for p in PROFILES.values()]),
        ("-" * 22, *["-" * 12 for _ in PROFILES]),
        ("min ATR %", *[f"{p.strategy['min_atr_pct'] * 100:.3f} %" for p in PROFILES.values()]),
        ("max ATR %", *[f"{p.strategy['max_atr_pct'] * 100:.3f} %" for p in PROFILES.values()]),
        ("ADX min", *[f"{p.strategy['adx_min']:.0f}" for p in PROFILES.values()]),
        ("seans (UTC)", *[f"{p.strategy['session_start_hour']:02d}-"
                          f"{p.strategy['session_end_hour']:02d}" for p in PROFILES.values()]),
        ("min stop %", *[f"{p.risk['min_stop_pct'] * 100:.3f} %" for p in PROFILES.values()]),
        ("max stop %", *[f"{p.risk['max_stop_pct'] * 100:.3f} %" for p in PROFILES.values()]),
        ("lot hajmi", *[f"{p.contract_size:g}" for p in PROFILES.values()]),
        ("tipik spread", *[f"{p.typical_spread:g}" for p in PROFILES.values()]),
        ("kun / yil", *[f"{p.calendar.days_per_year:.0f}" for p in PROFILES.values()]),
        ("dam olish kunlari", *["ha" if p.calendar.trades_weekends else "yo'q"
                                for p in PROFILES.values()]),
    ]
    widths = [max(len(str(r[i])) for r in rows) for i in range(len(rows[0]))]
    return "\n".join(
        "  ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row))
        for row in rows
    )
