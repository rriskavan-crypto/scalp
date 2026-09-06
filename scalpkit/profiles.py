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
    timeframe: str = "5m"
    # Bozorga oid parametrlar — barcha strategiyalar uchun umumiy
    # (volatilitet oynasi, seans, kalendar).
    strategy: dict[str, Any] = field(default_factory=dict)
    # Strategiyaga XOS qoplamalar. Bu ajratish zarur: `tp2_r = 3.0`
    # momentum_pullback uchun to'g'ri, lekin donchian_breakout uchun
    # halokatli — u maqsadsiz ishlashi kerak, aks holda trend-following
    # foydasi keladigan dumni kesib tashlaydi.
    strategy_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)
    risk: dict[str, Any] = field(default_factory=dict)
    cost: dict[str, Any] = field(default_factory=dict)
    default_strategy: str = "momentum_pullback"

    def apply(self, cfg: Config, strategy_name: str | None = None) -> Config:
        """Profilni konfiguratsiyaga qo'llaydi (nusxa qaytaradi)."""
        out = Config.from_dict(cfg.to_dict())
        out.symbol = self.symbols[0]
        out.days_per_year = self.calendar.days_per_year
        # `strategy_name` berilmasa — profilning tavsiya etilgan strategiyasi.
        # `cfg.strategy.name` ga tayanib bo'lmaydi: uning standart qiymati
        # ("momentum_pullback") har doim to'lgan bo'ladi va profil
        # tavsiyasini jim ravishda bosib turadi.
        out.strategy.name = strategy_name or self.default_strategy
        out.strategy.params = {
            **cfg.strategy.params,
            **self.strategy,
            **self.strategy_overrides.get(out.strategy.name, {}),
        }
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
        # SWING UCHUN MUHIM: MT5 da BTC CFD kechalik SWAP oladi, Binance
        # perpetual esa funding. Ikkalasi bir xil narsa emas va bir xil
        # raqam ham emas. Bu yerda swap 0 — chunki uni TAXMIN QILIB
        # bo'lmaydi, u har brokerda boshqacha. O'lchab qo'ying:
        #     python -m scalpkit mt5-test --symbol BTCUSD
        # [3b] bloki brokeringizning haqiqiy qiymatini R ga aylantirib
        # beradi; uni quyidagi maydonlarga yozing va `apply_swap` ni
        # yoqing (o'shanda `apply_funding` ni o'chiring).
        # MQL5 EA bu maydonlarga BOG'LIQ EMAS — u swapni terminaldan
        # to'g'ridan-to'g'ri o'qiydi (`SwapPerUnitPerNight`).
        "apply_swap": False,
        "swap_pct_per_day_long": 0.0,
        "swap_pct_per_day_short": 0.0,
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
    },
    strategy_overrides={
        # Chiqish parametrlari strategiyaga xos — ular umumiy blokda
        # bo'lsa, boshqa strategiyaga noto'g'ri qo'llanadi.
        "momentum_pullback": {
            "tp2_r": 3.0,             # oltin trendlari BTC nikidan qisqaroq
            "trail_atr_mult": 2.2,
            "time_stop_bars": 18,     # 90 daqiqa
        },
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
        # SWAP — swing uchun hal qiluvchi. Long pozitsiya USD foiz stavkasini
        # to'laydi (~4.5 %/yil), short esa oz miqdorda oladi. 30 kunlik long
        # pozitsiya ~0.28R turadi; skalpingda sezilmaydi, D1 da esa yo'q.
        # BROKERINGIZNING HAQIQIY SWAP QIYMATINI TEKSHIRING — u keskin farq qiladi.
        "apply_swap": True,
        "swap_pct_per_day_long": 0.00012,    # -0.012 %/kun
        "swap_pct_per_day_short": -0.00004,  # +0.004 %/kun (daromad)
    },
)


# ---------------------------------------------------------------------------
#  TIMEFRAME BO'YICHA KENGAYTIRISH
# ---------------------------------------------------------------------------
# Volatilitet timeframe bilan taxminan sqrt(T) qonuni bo'yicha o'sadi, spread
# esa o'zgarmaydi. Natijada yuqori timeframe'da xarajat R birligida keskin
# arzonlashadi — swing'ning skalpingdan asosiy tuzilmaviy afzalligi:
#
#   BTCUSD, stop = 1.5 ATR, spread $20 @ $65 000
#     M5  ATR% 0.220 %  -> xarajat 0.093 R
#     H1  ATR% 0.776 %  -> xarajat 0.026 R   (3.5x arzon)
#     D1  ATR% 4.173 %  -> xarajat 0.005 R  (18.9x arzon)
#
# Ko'paytiruvchilar sintetik ma'lumotda o'lchangan; nazariy sqrt(T) ga
# yaqin, lekin yuqori TF'da biroz undan katta (narx harakati sof tasodifiy
# emas — kunlik gorizontda davomiylik bor).
TF_M5_BARS: dict[str, int] = {"5m": 1, "15m": 3, "1h": 12, "4h": 48, "1d": 288}
TF_ATR_SCALE: dict[str, float] = {"5m": 1.0, "15m": 1.73, "1h": 3.5, "4h": 7.2, "1d": 18.9}

# Yuqori timeframe'da ba'zi qoidalar ma'nosini yo'qotadi:
#   * seans filtri — H4 bari bir necha seansni qamrab oladi;
#   * hafta chegarasi — D1 da pozitsiyasiz qolish imkonsiz, swing savdosi
#     hafta oxiri gapini qabul qiladi (uning o'rniga stop kengroq).
TF_SESSION_FILTER: dict[str, bool] = {"5m": True, "15m": True, "1h": True,
                                      "4h": False, "1d": False}
TF_WEEKEND_FLAT: dict[str, bool] = {"5m": True, "15m": True, "1h": True,
                                    "4h": False, "1d": False}
# Tanaffuslar bar hisobida — yuqori TF'da bir bar ancha uzoq vaqt
TF_COOLDOWN: dict[str, tuple[int, int]] = {
    "5m": (6, 24), "15m": (4, 16), "1h": (3, 8), "4h": (2, 4), "1d": (1, 2),
}


# Kutilgan ushlash muddati — SWAP xarajatini baholash uchun.
#
# Nima uchun kerak: swing pozitsiyasi kechalab ochiq turadi va broker har
# kecha swap oladi. D1 da o'rtacha ushlash ~18 kun; oltin long uchun bu
# 0.012 %/kun x 24 birlik = 0.29 % notional, ya'ni D1 stopining (1.28 %)
# deyarli chorak qismi. Spreadga qaraganda bu ancha katta — shuning uchun
# xarajat filtri swapsiz noto'g'ri javob beradi.
#
# Ko'paytiruvchilar 8 seedli sintetik o'lchovdan olingan (o'lchangan
# ushlash / nazariy chegara). Donchian kanaldan chiqadi, shuning uchun
# `exit_len` dan uzoqroq turadi; maqsadli strategiyalar vaqt stopiga
# yetmasdan maqsadga uriladi, shuning uchun undan qisqaroq.
#
#   donchian: o'lchangan/exit_len = 1.80, 1.63, 1.66, 1.77  -> 1.75
#   reversion: o'lchangan/time_stop = 0.58, 0.54            -> 0.55
#
# Bu ANIQ qiymat emas, kattalik tartibi — u faqat FILTR uchun ishlatiladi.
HOLD_FROM_EXIT_LEN = 1.75      # donchian_breakout
HOLD_FROM_TIME_STOP = 0.55     # maqsad yoki vaqt stopi bo'lgan strategiyalar
TF_HOURS: dict[str, float] = {"5m": 1 / 12, "15m": 0.25, "1h": 1.0,
                              "4h": 4.0, "1d": 24.0}


def expected_hold_days(timeframe: str, strategy_name: str, params: dict) -> float:
    """Pozitsiya o'rtacha necha kun ochiq turishining bahosi."""
    hours = TF_HOURS[timeframe]
    if strategy_name == "donchian_breakout":
        bars = float(params.get("exit_len", 10)) * HOLD_FROM_EXIT_LEN
    else:
        # Vaqt stopi "cheksiz" bo'lsa (trend-following), exit_len ga qaytamiz
        raw = float(params.get("time_stop_bars", 24))
        if raw > 10_000:
            raw = float(params.get("exit_len", 10))
        bars = raw * HOLD_FROM_TIME_STOP
    return round(bars * hours / 24.0, 4)


def for_timeframe(base: Profile, timeframe: str) -> Profile:
    """Profilni boshqa timeframe'ga moslaydi.

    Volatilitetga bog'liq barcha chegaralar o'lchangan ko'paytiruvchi
    bilan masshtablanadi. Qattiq kodlangan qiymatlarni ko'chirish
    xato bo'lardi: M5 uchun `min_atr_pct = 0.20 %` D1 da barcha
    barlarni o'tkazib yuboradi (D1 ATR% mediani 4.17 %), ya'ni filtr
    umuman ishlamay qoladi.
    """
    if timeframe not in TF_ATR_SCALE:
        raise KeyError(f"Noma'lum timeframe '{timeframe}'. Mavjud: {sorted(TF_ATR_SCALE)}")
    scale = TF_ATR_SCALE[timeframe] / TF_ATR_SCALE[base.timeframe]

    strategy = dict(base.strategy)
    for key in ("min_atr_pct", "max_atr_pct"):
        if key in strategy:
            strategy[key] = round(float(strategy[key]) * scale, 8)
    strategy["use_session_filter"] = (
        strategy.get("use_session_filter", True) and TF_SESSION_FILTER[timeframe]
    )
    strategy["weekend_flat"] = (
        strategy.get("weekend_flat", False) and TF_WEEKEND_FLAT[timeframe]
    )

    risk = dict(base.risk)
    for key in ("min_stop_pct", "max_stop_pct"):
        if key in risk:
            risk[key] = round(float(risk[key]) * scale, 8)
    cooldown, streak = TF_COOLDOWN[timeframe]
    risk["cooldown_bars_after_loss"] = cooldown
    risk["cooldown_bars_after_streak"] = streak

    bars_per_day = 288 / TF_M5_BARS[timeframe]
    risk["max_trades_per_day"] = max(1, int(round(base.risk.get(
        "max_trades_per_day", 8) * bars_per_day / 288)))

    # Yuqori timeframe'da vaqt stopi bar hisobida qayta o'lchanadi:
    # M5 da 18 bar = 90 daqiqa, D1 da 18 bar = 18 kun (swing uchun to'g'ri).
    overrides = {k: dict(v) for k, v in base.strategy_overrides.items()}

    # Swing timeframe'larida standart strategiya — trendni kuzatish.
    # M5/M15 da esa tanlab-skalping.
    default_strategy = ("donchian_breakout" if timeframe in ("1h", "4h", "1d")
                        else base.default_strategy)

    return Profile(
        name=f"{base.name}_{timeframe}", symbols=base.symbols,
        description=f"{base.description} ({timeframe})",
        timeframe=timeframe, typical_spread=base.typical_spread,
        typical_price=base.typical_price, contract_size=base.contract_size,
        calendar=base.calendar, strategy=strategy, strategy_overrides=overrides,
        risk=risk, cost=dict(base.cost), default_strategy=default_strategy,
    )


_BASES = (BTCUSD, XAUUSD)
TIMEFRAMES: tuple[str, ...] = ("5m", "15m", "1h", "4h", "1d")

PROFILES: dict[str, Profile] = {p.name: p for p in _BASES}
for _base in _BASES:
    for _tf in TIMEFRAMES:
        _p = for_timeframe(_base, _tf)
        PROFILES[_p.name] = _p


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
