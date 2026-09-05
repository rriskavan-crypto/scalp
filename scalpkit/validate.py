"""To'liq validatsiya quvuri — bitta chaqiruvda aniq xulosa.

Savol oddiy: **shu strategiya shu brokerda, shu ma'lumotda pul keltiradimi?**
Bu modul unga javob berish uchun kerakli barcha bosqichni ketma-ket bajaradi
va oxirida **qat'iy qaror** chiqaradi — "chiroyli grafik" emas.

Bosqichlar:
  1. Xarajatni o'lchangan spreadga moslash
  2. Butun tarixda backtest (dastlabki tasavvur)
  3. Walk-forward — ASOSIY tekshiruv (ko'rilmagan ma'lumot)
  4. OOS savdolarda statistik ishonchlilik testi
  5. XULOSA: savdo qilish mumkinmi yoki yo'q
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .config import Config
from .engine import run_backtest
from .features import build_features, warmup_bars
from .metrics import compute_metrics
from .montecarlo import bootstrap_equity, edge_significance_test
from .strategies import get_strategy
from .walkforward import WalkForwardResult, walk_forward

# Qaror mezonlari
MIN_OOS_TRADES = 100        # shundan kam savdoda statistika ma'nosiz
MAX_COST_R = 0.40           # xarajat shundan oshsa strategiya ishlamaydi


@dataclass
class Verdict:
    code: str                       # "trade" | "not_proven" | "no_edge" | "insufficient"
    headline: str
    reasons: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    symbol: str
    bars: int
    start: pd.Timestamp
    end: pd.Timestamp
    days: float
    spread: float
    price: float
    atr: float
    cost_r: float
    full_metrics: dict[str, float]
    wf: WalkForwardResult | None
    oos_metrics: dict[str, float]
    significance: dict[str, float]
    mc_summary: pd.DataFrame | None
    verdict: Verdict


def cost_config_from_spread(cfg: Config, spread: float, price: float,
                            commission_per_lot: float = 0.0,
                            contract_size: float = 1.0) -> Config:
    """Backtest xarajatini o'lchangan spreadga moslaydi.

    MT5 da har savdoda spread to'liq to'lanadi (ask'da olib, bid'da sotasiz),
    ya'ni bir tomonlama xarajat = spreadning yarmi. Buni bps ga o'giramiz,
    chunki dvigatel bps bilan ishlaydi.
    """
    if price <= 0:
        return cfg
    half_spread_bps = (spread / 2.0) / price * 1e4
    commission_bps = (
        (commission_per_lot / contract_size) / price * 1e4 if contract_size > 0 else 0.0
    )
    out = Config.from_dict(cfg.to_dict())
    out.cost.taker_fee_bps = half_spread_bps + commission_bps
    # MT5 da limit order ham spreadni to'laydi — maker chegirmasi yo'q
    out.cost.maker_fee_bps = half_spread_bps + commission_bps
    out.cost.entry_is_maker = False
    out.cost.exit_is_maker = False
    out.cost.apply_funding = False   # Exness'da funding emas, swap bor
    return out


def full_validation(
    df: pd.DataFrame,
    cfg: Config,
    symbol: str = "BTCUSD",
    spread: float | None = None,
    commission_per_lot: float = 0.0,
    contract_size: float = 1.0,
    folds: int | None = None,
    train_days: int = 180,
    test_days: int = 45,
    max_combos: int = 120,
    mc_sims: int = 5000,
    verbose: bool = True,
) -> ValidationReport:
    """To'liq tekshiruvni bajarib, xulosa qaytaradi."""
    price = float(df["close"].iloc[-1])
    feats = build_features(df)
    atr = float(feats["atr"].iloc[-1])

    # --- 1) xarajatni spreadga moslash ---
    if spread is not None:
        cfg = cost_config_from_spread(cfg, spread, price, commission_per_lot, contract_size)
        if verbose:
            print(f"  Xarajat spreadga moslandi: {cfg.cost.taker_fee_bps:.2f} bps / tomon")
    else:
        spread = cfg.cost.taker_fee_bps * 2.0 * 1e-4 * price

    p = cfg.strategy.params
    typical_stop = float(p.get("min_sl_atr", 1.0)) * atr * 1.4
    cost_r = (cfg.cost.round_trip_bps() * 1e-4 * price) / typical_stop if typical_stop else np.inf

    # --- 2) to'liq backtest ---
    if verbose:
        print("\n  [1/3] To'liq tarixda backtest...")
    strat = get_strategy(cfg.strategy.name, cfg.strategy.params)
    res = run_backtest(feats, strat.generate(feats), cfg, strat.params,
                       warmup=warmup_bars(cfg.strategy.params))
    full_metrics = compute_metrics(res.trades, res.equity, cfg.risk.initial_equity, res.days)

    # --- 3) walk-forward ---
    total_days = (df.index[-1] - df.index[0]).days
    if folds is None:
        folds = max(1, min(10, (total_days - train_days) // test_days))
    wf: WalkForwardResult | None = None
    oos_metrics: dict[str, float] = {}
    significance: dict[str, float] = {}
    mc_summary: pd.DataFrame | None = None

    if total_days >= train_days + test_days:
        if verbose:
            print(f"\n  [2/3] Walk-forward: {folds} bosqich "
                  f"({train_days} kun o'rgatish / {test_days} kun test)...")
        wf = walk_forward(df, cfg, cfg.strategy.name, n_folds=folds,
                          train_days=train_days, test_days=test_days,
                          max_combos=max_combos, verbose=verbose)
        oos_metrics = wf.oos_metrics
        if not wf.oos_trades.empty:
            r = wf.oos_trades["r_multiple"].to_numpy()
            significance = edge_significance_test(r, n_sims=mc_sims)
            if verbose:
                print("\n  [3/3] Monte Carlo...")
            mc_summary = bootstrap_equity(
                r, n_sims=mc_sims, risk_per_trade=cfg.risk.risk_per_trade
            ).summary
    elif verbose:
        print(f"\n  Walk-forward o'tkazib yuborildi: {total_days} kunlik ma'lumot "
              f"yetarli emas (kamida {train_days + test_days} kun kerak).")

    verdict = _decide(cost_r, total_days, train_days, test_days,
                      oos_metrics, significance, wf)

    return ValidationReport(
        symbol=symbol, bars=len(df), start=df.index[0], end=df.index[-1],
        days=float(total_days), spread=float(spread), price=price, atr=atr,
        cost_r=float(cost_r), full_metrics=full_metrics, wf=wf,
        oos_metrics=oos_metrics, significance=significance,
        mc_summary=mc_summary, verdict=verdict,
    )


def _decide(cost_r, total_days, train_days, test_days, oos_m, sig, wf) -> Verdict:
    """Qat'iy qaror qoidalari — 'balki' degan javob yo'q."""
    reasons: list[str] = []

    if cost_r > MAX_COST_R:
        return Verdict(
            "no_edge",
            "SAVDO QILMANG — spread juda keng",
            [f"Xarajat {cost_r:.2f} R (chegara {MAX_COST_R} R).",
             "Bunday spreadda hech qanday M5 strategiya foyda keltirmaydi."],
            ["Boshqa hisob turini ko'ring (Raw Spread / Zero).",
             "Yoki yuqoriroq timeframega o'ting (M15/H1) — stop kengroq bo'ladi."],
        )

    if total_days < train_days + test_days:
        return Verdict(
            "insufficient",
            "QAROR CHIQARIB BO'LMAYDI — ma'lumot yetarli emas",
            [f"Faqat {total_days} kunlik tarix bor, kamida "
             f"{train_days + test_days} kun kerak."],
            ["MT5 grafikda M5 ni orqaga aylantirib tarixni yuklang.",
             "Tools > Options > Charts > 'Max bars in chart' ni oshiring."],
        )

    n_oos = oos_m.get("trades", 0)
    if n_oos < MIN_OOS_TRADES:
        reasons.append(f"OOS savdolar atigi {n_oos:.0f} ta "
                       f"(ishonchli xulosa uchun {MIN_OOS_TRADES}+ kerak).")
        return Verdict(
            "insufficient",
            "QAROR CHIQARIB BO'LMAYDI — savdolar juda kam",
            reasons,
            ["Uzoqroq tarix yuklang.",
             "Yoki filtrlarni biroz yumshating (adx_min, min_atr_pct) va "
             "walk-forward'ni qayta ishga tushiring."],
        )

    e = oos_m.get("expectancy_r", 0.0)
    ci_low = sig.get("ci_low", np.nan)
    ci_high = sig.get("ci_high", np.nan)
    p_value = sig.get("p_value", np.nan)

    reasons.append(f"OOS ekspektatsiya {e:+.3f} R / savdo ({n_oos:.0f} savdo).")
    reasons.append(f"95 % ishonch oralig'i [{ci_low:+.3f}, {ci_high:+.3f}] R, "
                   f"p = {p_value:.4f}.")
    if wf is not None:
        reasons.append(f"Walk-forward samaradorligi {wf.efficiency:.2f}.")

    if e <= 0:
        return Verdict(
            "no_edge", "SAVDO QILMANG — ustunlik yo'q", reasons,
            ["Strategiyani real pulga qo'ymang.",
             "Filtrlarni qayta ko'rib chiqing yoki boshqa bozor rejimini sinang."],
        )

    if not np.isfinite(ci_low) or ci_low <= 0:
        return Verdict(
            "not_proven", "USTUNLIK ISBOTLANMAGAN — real pulga o'tmang", reasons,
            ["Ishonch oralig'i nolni o'z ichiga oladi — natija omad bo'lishi mumkin.",
             "Demo hisobda davom eting va savdolar sonini 200+ ga yetkazing."],
        )

    return Verdict(
        "trade", "USTUNLIK BOR — demo bosqichiga o'tish mumkin", reasons,
        ["Demoda 0.1 % risk bilan kamida 1 oy sinang.",
         "Natija backtestga mos kelsa, riskni bosqichma-bosqich oshiring.",
         "Kunlik chegara va tanaffus qoidalarini chetlab o'tmang."],
    )


def format_report(rep: ValidationReport) -> str:
    w = 68
    L = ["=" * w, f"VALIDATSIYA — {rep.symbol}".center(w), "=" * w, "",
         f"  Ma'lumot        : {rep.bars:,} bar   "
         f"{rep.start:%Y-%m-%d} — {rep.end:%Y-%m-%d}  ({rep.days:.0f} kun)",
         f"  Narx / ATR(M5)  : {rep.price:,.2f} / {rep.atr:,.2f} "
         f"({rep.atr / rep.price * 100:.3f} %)",
         f"  Spread          : {rep.spread:,.2f}  ({rep.spread / rep.price * 100:.4f} %)",
         f"  Xarajat         : {rep.cost_r:.3f} R / savdo", ""]

    m = rep.full_metrics
    L += ["-" * w, " TO'LIQ TARIXDA (dastlabki tasavvur)".center(w, "-"), "-" * w,
          f"  savdolar {m['trades']:.0f}  ({m['trades_per_day']:.2f}/kun)   "
          f"ekspektatsiya {m['expectancy_r']:+.3f} R",
          f"  g'alaba {m['win_rate'] * 100:.1f} %   "
          f"zararsizlik {m['breakeven_win_rate'] * 100:.1f} %   "
          f"PF {m['profit_factor']:.2f}",
          f"  natija {m['return_pct'] * 100:+.2f} %   "
          f"maks. DD {m['max_drawdown_pct'] * 100:.2f} %   "
          f"t-stat {m['r_tstat']:.2f}"]

    if rep.oos_metrics:
        o = rep.oos_metrics
        L += ["", "-" * w, " WALK-FORWARD — KO'RILMAGAN MA'LUMOT (asosiy)".center(w, "-"), "-" * w,
              f"  OOS savdolar    : {o['trades']:.0f}",
              f"  OOS ekspektatsiya: {o['expectancy_r']:+.3f} R / savdo",
              f"  OOS g'alaba     : {o['win_rate'] * 100:.1f} %  "
              f"(zararsizlik {o['breakeven_win_rate'] * 100:.1f} %)",
              f"  OOS profit factor: {o['profit_factor']:.2f}",
              f"  OOS maks. DD    : {o['max_drawdown_pct'] * 100:.2f} %"]
        if rep.wf is not None:
            L.append(f"  WF samaradorligi : {rep.wf.efficiency:.2f}")

    if rep.significance:
        s = rep.significance
        L += ["", "-" * w, " STATISTIK ISHONCHLILIK".center(w, "-"), "-" * w,
              f"  o'rtacha        : {s['observed_mean_r']:+.3f} R",
              f"  95 % oralig'i   : [{s['ci_low']:+.3f}, {s['ci_high']:+.3f}] R",
              f"  p-qiymat        : {s['p_value']:.4f}"]

    if rep.mc_summary is not None:
        L += ["", "  Monte Carlo (savdolar tartibi aralashtirilgan):", ""]
        L += ["  " + line for line in rep.mc_summary.round(2).to_string().splitlines()]

    v = rep.verdict
    L += ["", "=" * w, " XULOSA ".center(w, "="), "=" * w, "", f"  >>> {v.headline} <<<", ""]
    for r in v.reasons:
        L.append(f"    - {r}")
    if v.next_steps:
        L += ["", "  Keyingi qadamlar:"]
        for step in v.next_steps:
            L.append(f"    * {step}")
    L += ["", "=" * w]
    return "\n".join(L)
