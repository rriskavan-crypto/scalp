"""Buyruqlar qatori interfeysi.

    python -m scalpkit <buyruq> [parametrlar]

Buyruqlar:
    fetch        Binance'dan tarixiy M5 ma'lumot yuklash
    synth        Sintetik test ma'lumoti yaratish (internetsiz ishlash uchun)
    costs        Xarajat / zararsizlik jadvallari
    backtest     Strategiyani tarixda sinash
    optimize     Parametr qidiruvi (walk-forward'siz ISHONMANG)
    walkforward  Ko'rilmagan ma'lumotda tekshirish — asosiy validatsiya
    montecarlo   Natijaning statistik ishonchliligi va drawdown taqsimoti
    signal       Oxirgi bar bo'yicha jonli signal va darajalar
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from .config import Config
from .costs import cost_table, edge_needed_report, fee_tier_comparison
from .data import generate_synthetic, load_csv, save_csv
from .engine import run_backtest
from .features import build_features, warmup_bars
from .metrics import compute_metrics
from .montecarlo import bootstrap_equity, edge_significance_test, monte_carlo_report
from .optimize import grid_search, robustness_check
from .report import save_report, text_report
from .strategies import available, get_strategy
from .walkforward import walk_forward, walk_forward_report

DEFAULT_DATA = "data/BTCUSDT_5m.csv"


# ---------------------------------------------------------------- yordamchilar
def _load(args) -> pd.DataFrame:
    path = Path(args.data)
    if not path.exists():
        raise SystemExit(
            f"Ma'lumot fayli topilmadi: {path}\n"
            f"  Yuklash    : python -m scalpkit fetch --start 2023-01-01\n"
            f"  Yoki sinov : python -m scalpkit synth --bars 120000"
        )
    df = load_csv(path)
    if getattr(args, "start", None):
        df = df.loc[pd.Timestamp(args.start, tz="UTC"):]
    if getattr(args, "end", None):
        df = df.loc[: pd.Timestamp(args.end, tz="UTC")]
    print(f"  {len(df):,} bar yuklandi: {df.index[0]:%Y-%m-%d} → {df.index[-1]:%Y-%m-%d}")
    return df


def _config(args) -> Config:
    cfg = Config.load(getattr(args, "config", None))
    if getattr(args, "strategy", None):
        cfg.strategy.name = args.strategy
    if getattr(args, "equity", None):
        cfg.risk.initial_equity = args.equity
    if getattr(args, "risk", None):
        cfg.risk.risk_per_trade = args.risk
    if getattr(args, "entry_mode", None):
        cfg.strategy.params["entry_mode"] = args.entry_mode
    if getattr(args, "taker_bps", None) is not None:
        cfg.cost.taker_fee_bps = args.taker_bps
    return cfg


# ---------------------------------------------------------------- buyruqlar
def cmd_fetch(args) -> None:
    from .data.binance import download_to_csv
    download_to_csv(args.out, args.symbol, args.interval, args.start, args.end, args.market)


def cmd_synth(args) -> None:
    df = generate_synthetic(n_bars=args.bars, start=args.start, seed=args.seed)
    save_csv(df, args.out)
    print(f"  Sintetik ma'lumot: {len(df):,} bar → {args.out}")
    print("  DIQQAT: bu sun'iy ma'lumot. Undan olingan foyda ko'rsatkichlari")
    print("  real natija EMAS — faqat tizimni tekshirish uchun.")


def cmd_costs(args) -> None:
    cfg = _config(args)
    print("\n=== STOP MASOFASI vs XARAJAT ===")
    print("Har bir qatorda: shu stop masofasida bitta savdo necha R turadi va")
    print("turli payoff nisbatlarida zararsizlik uchun necha % g'alaba kerak.\n")
    print(cost_table(cfg.cost).round(2).to_string())
    print("\n=== KOMISSIYA TARIFLARI (0.50 % stop uchun) ===")
    print(fee_tier_comparison(cfg.cost).round(4).to_string())
    print(f"\n=== USTUNLIK → YILLIK NATIJA ({args.trades_per_day} savdo/kun) ===")
    print(edge_needed_report(cfg.cost, args.trades_per_day).round(2).to_string())
    print("\nXULOSA: 0.20 % dan tor stop bilan M5 skalping matematik jihatdan")
    print("yutqazadi. Ishlaydigan diapazon — 0.40-0.90 % stop masofasi.\n")


def cmd_backtest(args) -> None:
    df, cfg = _load(args), _config(args)
    strat = get_strategy(cfg.strategy.name, cfg.strategy.params)
    print(f"\n{strat.describe()}\n")
    f = build_features(df)
    res = run_backtest(f, strat.generate(f), cfg, strat.params,
                       warmup=warmup_bars(cfg.strategy.params))
    print(text_report(res))
    if args.out:
        paths = save_report(res, args.out)
        print("\nSaqlandi:")
        for k, v in paths.items():
            print(f"  {k:<8} {v}")


def cmd_optimize(args) -> None:
    df, cfg = _load(args), _config(args)
    print(f"\nParametr qidiruvi ({args.objective})...")
    res = grid_search(df, cfg, cfg.strategy.name, objective=args.objective,
                      max_combos=args.max_combos)
    if res.empty:
        raise SystemExit("Hech qanday natija topilmadi (savdolar juda kam).")
    cols = ["score", "trades", "trades_per_day", "expectancy_r", "win_rate",
            "profit_factor", "return_pct", "max_dd_pct", "r_tstat"]
    show = [c for c in res.columns if c not in cols] + cols
    print(f"\n=== ENG YAXSHI {args.top} KOMBINATSIYA ===")
    print(res[show].head(args.top).round(4).to_string(index=False))

    print("\n=== BARQARORLIK TEKSHIRUVI ===")
    print("Yaxshi parametr PLATO hosil qiladi (qo'shni qiymatlar ham ishlaydi).")
    print("Faqat bitta qiymatda yaxshi natija — overfitting belgisi.\n")
    for param in [c for c in res.columns if c not in cols][:4]:
        rb = robustness_check(res, param)
        if not rb.empty:
            print(f"--- {param} ---")
            print(rb.to_string(), "\n")

    print("OGOHLANTIRISH: bu natijalar IN-SAMPLE. Ularga ishonishdan oldin")
    print("  python -m scalpkit walkforward  buyrug'ini ishga tushiring.")
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        res.to_csv(args.out, index=False)
        print(f"\nSaqlandi: {args.out}")


def cmd_walkforward(args) -> None:
    df, cfg = _load(args), _config(args)
    wf = walk_forward(df, cfg, cfg.strategy.name, n_folds=args.folds,
                      train_days=args.train_days, test_days=args.test_days,
                      objective=args.objective, max_combos=args.max_combos,
                      anchored=args.anchored)
    print("\n" + walk_forward_report(wf))
    if not wf.oos_trades.empty:
        sig = edge_significance_test(wf.oos_trades["r_multiple"].to_numpy())
        print(f"\n  OOS ekspektatsiya 95 % oralig'i: "
              f"[{sig['ci_low']:+.3f} R, {sig['ci_high']:+.3f} R], p = {sig['p_value']:.4f}")
        if sig["ci_low"] <= 0 <= sig["ci_high"]:
            print("  Ishonch oralig'i nolni o'z ichiga oladi — ustunlik isbotlanmagan.")
    if args.out:
        Path(args.out).mkdir(parents=True, exist_ok=True)
        wf.folds.to_csv(Path(args.out) / "wf_folds.csv", index=False)
        wf.oos_trades.to_csv(Path(args.out) / "wf_oos_trades.csv", index=False)
        print(f"\nSaqlandi: {args.out}/")


def cmd_montecarlo(args) -> None:
    if args.trades:
        trades = pd.read_csv(args.trades)
    else:
        df, cfg = _load(args), _config(args)
        strat = get_strategy(cfg.strategy.name, cfg.strategy.params)
        f = build_features(df)
        trades = run_backtest(f, strat.generate(f), cfg, strat.params,
                              warmup=warmup_bars(cfg.strategy.params)).trades
    if trades.empty:
        raise SystemExit("Savdolar yo'q — Monte Carlo bajarib bo'lmaydi.")
    r = trades["r_multiple"].to_numpy()
    mc = bootstrap_equity(r, n_sims=args.sims, risk_per_trade=args.risk or 0.005,
                          n_trades=args.horizon)
    print("\n" + monte_carlo_report(mc, edge_significance_test(r)))


def cmd_signal(args) -> None:
    from .live import evaluate_now, format_signal
    cfg = _config(args)
    if args.live:
        from .data.binance import fetch_klines
        start = (pd.Timestamp.utcnow() - pd.Timedelta(days=args.days)).strftime("%Y-%m-%d")
        df = fetch_klines(cfg.symbol, cfg.timeframe, start=start, market=args.market)
    else:
        df = _load(args)
    ls = evaluate_now(df, cfg, equity=cfg.risk.initial_equity)
    print("\n" + format_signal(ls, cfg, cfg.risk.initial_equity))


# ---------------------------------------------------------------- parser
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="scalpkit",
        description="BTC/USDT M5 tanlab-skalping strategiyasi: tadqiqot va tekshiruv to'plami",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp, data=True):
        if data:
            sp.add_argument("--data", default=DEFAULT_DATA, help="OHLCV CSV fayl yo'li")
            sp.add_argument("--start", help="Boshlanish sanasi (YYYY-MM-DD)")
            sp.add_argument("--end", help="Tugash sanasi (YYYY-MM-DD)")
        sp.add_argument("--config", help="YAML konfiguratsiya fayli")
        sp.add_argument("--strategy", choices=available(), help="Strategiya nomi")
        sp.add_argument("--equity", type=float, help="Boshlang'ich kapital")
        sp.add_argument("--risk", type=float, help="Bitta savdodagi risk (0.005 = 0.5 %%)")
        sp.add_argument("--entry-mode", choices=["limit", "market"], dest="entry_mode")
        sp.add_argument("--taker-bps", type=float, dest="taker_bps",
                        help="Taker komissiyasi, bps (default 5.0 = 0.05 %%)")

    s = sub.add_parser("fetch", help="Binance'dan ma'lumot yuklash")
    s.add_argument("--symbol", default="BTCUSDT")
    s.add_argument("--interval", default="5m")
    s.add_argument("--start", default="2023-01-01")
    s.add_argument("--end")
    s.add_argument("--market", default="futures", choices=["futures", "spot"])
    s.add_argument("--out", default=DEFAULT_DATA)
    s.set_defaults(func=cmd_fetch)

    s = sub.add_parser("synth", help="Sintetik ma'lumot yaratish")
    s.add_argument("--bars", type=int, default=120_000)
    s.add_argument("--start", default="2024-01-01")
    s.add_argument("--seed", type=int, default=42)
    s.add_argument("--out", default="data/SYNTH_5m.csv")
    s.set_defaults(func=cmd_synth)

    s = sub.add_parser("costs", help="Xarajat va zararsizlik jadvallari")
    common(s, data=False)
    s.add_argument("--trades-per-day", type=float, default=3.0)
    s.set_defaults(func=cmd_costs)

    s = sub.add_parser("backtest", help="Tarixiy sinov")
    common(s)
    s.add_argument("--out", help="Natijalarni saqlash papkasi")
    s.set_defaults(func=cmd_backtest)

    s = sub.add_parser("optimize", help="Parametr qidiruvi")
    common(s)
    s.add_argument("--objective", default="expectancy",
                   choices=["expectancy", "profit_factor", "calmar", "tstat"])
    s.add_argument("--max-combos", type=int, default=300)
    s.add_argument("--top", type=int, default=15)
    s.add_argument("--out", help="Natijalarni CSV ga saqlash")
    s.set_defaults(func=cmd_optimize)

    s = sub.add_parser("walkforward", help="Ko'rilmagan ma'lumotda tekshirish")
    common(s)
    s.add_argument("--folds", type=int, default=6)
    s.add_argument("--train-days", type=int, default=120)
    s.add_argument("--test-days", type=int, default=30)
    s.add_argument("--objective", default="expectancy",
                   choices=["expectancy", "profit_factor", "calmar", "tstat"])
    s.add_argument("--max-combos", type=int, default=150)
    s.add_argument("--anchored", action="store_true",
                   help="O'rgatish oynasi boshidan o'sib boradi")
    s.add_argument("--out", help="Natijalarni saqlash papkasi")
    s.set_defaults(func=cmd_walkforward)

    s = sub.add_parser("montecarlo", help="Statistik ishonchlilik tahlili")
    common(s)
    s.add_argument("--trades", help="Tayyor trades.csv fayli")
    s.add_argument("--sims", type=int, default=5000)
    s.add_argument("--horizon", type=int, help="Simulyatsiyadagi savdolar soni")
    s.set_defaults(func=cmd_montecarlo)

    s = sub.add_parser("signal", help="Jonli signal")
    common(s)
    s.add_argument("--live", action="store_true", help="Binance'dan yangi ma'lumot olish")
    s.add_argument("--days", type=int, default=10, help="--live uchun necha kunlik tarix")
    s.add_argument("--market", default="futures", choices=["futures", "spot"])
    s.set_defaults(func=cmd_signal)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nTo'xtatildi.")
        return 130
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — foydalanuvchiga toza xabar
        print(f"\nXATO: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
