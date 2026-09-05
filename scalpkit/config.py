"""Konfiguratsiya: xarajat modeli, risk qoidalari va strategiya parametrlari."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field, asdict, fields
from pathlib import Path
from typing import Any

import yaml


@dataclass
class CostConfig:
    """Savdo xarajatlari — natijani hal qiladigan eng muhim blok.

    Binance USDⓈ-M futures standart tariflari (2026, VIP0):
      taker 0.05 % (5.0 bps), maker 0.02 % (2.0 bps).
      BNB chegirmasi bilan taker ~0.04 % (4.0 bps).
    """

    taker_fee_bps: float = 5.0      # bir tomon uchun, bazis punktda (1 bps = 0.01 %)
    maker_fee_bps: float = 2.0
    entry_is_maker: bool = False    # limit order bilan kirsangiz True qiling
    exit_is_maker: bool = False     # stop/market chiqish odatda taker
    slippage_bps: float = 1.5       # market kirish/chiqishdagi o'rtacha sirpanish
    stop_slippage_bps: float = 3.0  # stop ishlaganda qo'shimcha sirpanish
    funding_rate_8h: float = 0.0001 # perpetual funding, 8 soatlik o'rtacha (0.01 %)
    apply_funding: bool = True

    def round_trip_bps(self) -> float:
        """Bir to'liq savdoning (kirish + chiqish) taxminiy narxi, bps."""
        entry = self.maker_fee_bps if self.entry_is_maker else self.taker_fee_bps
        exit_ = self.maker_fee_bps if self.exit_is_maker else self.taker_fee_bps
        return entry + exit_ + self.slippage_bps + self.stop_slippage_bps


@dataclass
class RiskConfig:
    initial_equity: float = 10_000.0
    risk_per_trade: float = 0.005      # 0.5 % — bitta savdodagi maksimal zarar
    max_leverage: float = 5.0
    max_trades_per_day: int = 8
    daily_loss_limit: float = 0.03     # kunlik -3 % da savdo to'xtaydi
    max_consecutive_losses: int = 3
    cooldown_bars_after_loss: int = 6  # 6 * 5daq = 30 daqiqa tanaffus
    cooldown_bars_after_streak: int = 24  # ketma-ket zararlardan keyin 2 soat
    halve_risk_drawdown: float = 0.08  # -8 % drawdownda risk yarmiga tushadi
    min_stop_pct: float = 0.0015       # stop masofasi narxning kamida 0.15 %
    max_stop_pct: float = 0.020        # va ko'pi bilan 2.0 %


@dataclass
class StrategyConfig:
    name: str = "momentum_pullback"
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Config:
    symbol: str = "BTCUSDT"
    timeframe: str = "5m"
    # Yillik ko'rsatkichlar (CAGR, Sharpe) uchun savdo kunlari soni.
    # Kripto 365, oltin/forex ~252. Profil buni avtomatik belgilaydi.
    days_per_year: float = 365.0
    cost: CostConfig = field(default_factory=CostConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)

    # ---- serializatsiya ----
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Config":
        raw = copy.deepcopy(raw or {})
        cost = CostConfig(**_filter(raw.pop("cost", {}) or {}, CostConfig))
        risk = RiskConfig(**_filter(raw.pop("risk", {}) or {}, RiskConfig))
        strat_raw = raw.pop("strategy", {}) or {}
        strategy = StrategyConfig(
            name=strat_raw.get("name", "momentum_pullback"),
            params=strat_raw.get("params", {}) or {},
        )
        return cls(cost=cost, risk=risk, strategy=strategy, **_filter(raw, cls))

    @classmethod
    def load(cls, path: str | Path | None) -> "Config":
        if path is None:
            return cls()
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls.from_dict(raw)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(
            yaml.safe_dump(self.to_dict(), sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    def copy_with_params(self, params: dict[str, Any]) -> "Config":
        """Strategiya parametrlarini almashtirib nusxa qaytaradi (optimizatsiya uchun)."""
        clone = Config.from_dict(self.to_dict())
        clone.strategy.params = {**self.strategy.params, **params}
        return clone


def _filter(raw: dict[str, Any], target) -> dict[str, Any]:
    """Nomaʼlum kalitlarni tashlab yuboradi — eski konfiglar buzilmasligi uchun."""
    allowed = {f.name for f in fields(target)}
    return {k: v for k, v in raw.items() if k in allowed}
