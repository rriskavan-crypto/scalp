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
    validate     TO'LIQ TEKSHIRUV: backtest + walk-forward + xulosa

MetaTrader 5 (Exness va boshqalar) — FAQAT Windows:
    mt5-test     Terminalga ulanish, hisob, spread va joriy signalni tekshirish
    mt5-bars     MT5 dan tarixiy barlarni CSV ga yuklash
    trade        Jonli savdo sikli (standart holatda DRY-RUN)
    mt5-validate MT5 dan ma'lumot olib to'liq tekshiruv (bitta buyruq)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
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


def cmd_validate(args) -> None:
    from .validate import format_report, full_validation

    df, cfg = _load(args), _config(args)
    rep = full_validation(
        df, cfg, symbol=cfg.symbol, spread=args.spread,
        commission_per_lot=args.commission, folds=args.folds,
        train_days=args.train_days, test_days=args.test_days,
        max_combos=args.max_combos,
    )
    print("\n" + format_report(rep))
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "validation.txt").write_text(format_report(rep), encoding="utf-8")
        if rep.wf is not None:
            rep.wf.folds.to_csv(out / "wf_folds.csv", index=False)
            rep.wf.oos_trades.to_csv(out / "wf_oos_trades.csv", index=False)
        print(f"\nSaqlandi: {out}/")


# ---------------------------------------------------------------- MT5 buyruqlari
def _mt5_broker(args, dry_run: bool):
    from .broker.mt5broker import MT5Broker, MT5Credentials
    creds = MT5Credentials.from_env(login=args.login, server=args.server, path=args.path)
    broker = MT5Broker(creds, dry_run=dry_run)
    broker.connect()
    return broker


def cmd_mt5_test(args) -> None:
    from .costs import mt5_cost_in_r, mt5_spread_report, verdict_for_cost_r
    from .live import evaluate_now, format_signal

    cfg = _config(args)
    w = 66
    print("=" * w)
    print("MT5 ULANISH VA SIGNAL TEKSHIRUVI".center(w))
    print("=" * w)

    broker = _mt5_broker(args, dry_run=True)
    try:
        # --- hisob ---
        acc = broker.account()
        print(f"\n[1] HISOB")
        print(f"    login        : {acc.login}")
        print(f"    balans       : {acc.balance:,.2f} {acc.currency}")
        print(f"    ekviti       : {acc.equity:,.2f} {acc.currency}")
        print(f"    bo'sh marja  : {acc.margin_free:,.2f}")
        print(f"    leverage     : 1:{acc.leverage}")
        print(f"    savdo ruxsati: {'HA' if acc.trade_allowed else 'YO`Q'}")
        if not acc.trade_allowed:
            print("    >>> Terminal: Tools > Options > Expert Advisors >")
            print("        'Allow algorithmic trading' ni yoqing.")
        print(f"    server vaqti : UTC{broker.server_utc_offset_hours:+.0f}")

        # --- instrument ---
        symbol = broker.resolve_symbol(args.symbol or cfg.symbol)
        spec = broker.symbol_spec(symbol)
        print(f"\n[2] INSTRUMENT: {symbol}")
        print(f"    lot hajmi    : {spec.contract_size}")
        print(f"    min / qadam  : {spec.volume_min} / {spec.volume_step}")
        print(f"    digits/point : {spec.digits} / {spec.point}")
        print(f"    stops level  : {spec.stops_level_points} punkt "
              f"({spec.min_stop_distance():.2f} narx birligi)")

        # --- spread ---
        q = broker.quote(symbol)
        bars = broker.bars(symbol, cfg.timeframe, count=1200)
        from .features import build_features
        f = build_features(bars)
        atr = float(f["atr"].iloc[-1])
        p = cfg.strategy.params
        stop_dist = float(p.get("min_sl_atr", 1.0)) * atr * 1.4
        cost_r = mt5_cost_in_r(q.spread, stop_dist,
                               commission_per_lot=args.commission,
                               contract_size=spec.contract_size)
        print(f"\n[3] SPREAD VA XARAJAT")
        print(f"    bid / ask    : {q.bid:.2f} / {q.ask:.2f}")
        print(f"    spread       : {q.spread:.2f}  ({q.spread / q.mid * 100:.4f} %)")
        print(f"    ATR(14) M5   : {atr:.2f}  ({atr / q.mid * 100:.3f} % narxdan)")
        print(f"    xarajat      : {cost_r:.3f} R")
        print(f"    >>> {verdict_for_cost_r(cost_r)}")
        print()
        print(mt5_spread_report(q.spread, q.mid, atr,
                                commission_per_lot=args.commission,
                                contract_size=spec.contract_size).round(3).to_string())

        # --- barlar ---
        print(f"\n[4] BARLAR")
        print(f"    yuklandi     : {len(bars):,} ta (yopilgan)")
        print(f"    oxirgi bar   : {bars.index[-1]:%Y-%m-%d %H:%M} UTC")
        print(f"    narx         : {bars['close'].iloc[-1]:,.2f}")

        # --- signal ---
        print(f"\n[5] JORIY SIGNAL")
        cfg.symbol = symbol
        ls = evaluate_now(bars, cfg, equity=acc.equity)
        print(format_signal(ls, cfg, acc.equity))

        # --- hajm ---
        if ls.has_signal:
            units = (acc.equity * cfg.risk.risk_per_trade) / (ls.stop_pct * ls.entry)
            lots = spec.normalize_volume(units / spec.contract_size)
            print(f"\n[6] HAJM HISOBI")
            print(f"    lot          : {lots}")
            print(f"    real risk    : {lots * spec.contract_size * ls.stop_pct * ls.entry:,.2f} "
                  f"{acc.currency}")
            if lots <= 0:
                print("    >>> Hisoblangan hajm minimal lotdan kichik — savdo qilinmaydi.")
        print("\n" + "=" * w)
        print("Tekshiruv tugadi. Hech qanday order YUBORILMADI.".center(w))
        print("=" * w)
    finally:
        broker.disconnect()


def cmd_mt5_bars(args) -> None:
    cfg = _config(args)
    broker = _mt5_broker(args, dry_run=True)
    try:
        symbol = broker.resolve_symbol(args.symbol or cfg.symbol)
        df = broker.bars(symbol, args.interval, count=args.count)
        save_csv(df, args.out)
        print(f"  {len(df):,} bar saqlandi -> {args.out}")
        print(f"  {df.index[0]:%Y-%m-%d %H:%M} - {df.index[-1]:%Y-%m-%d %H:%M} UTC")
        print(f"  Endi shu ma'lumotda backtest qiling:")
        print(f"    python -m scalpkit backtest --data {args.out}")
    finally:
        broker.disconnect()


def cmd_mt5_validate(args) -> None:
    """MT5 dan ma'lumot va spreadni olib, to'liq tekshiruvni bajaradi."""
    import time as _time

    from .validate import format_report, full_validation

    cfg = _config(args)
    broker = _mt5_broker(args, dry_run=True)
    try:
        symbol = broker.resolve_symbol(args.symbol or cfg.symbol)
        spec = broker.symbol_spec(symbol)
        cfg.symbol = symbol

        # --- spreadni bir necha marta o'lchab, medianasini olamiz ---
        print(f"  Spread o'lchanmoqda ({args.spread_samples} namuna)...")
        samples = []
        for _ in range(args.spread_samples):
            try:
                samples.append(broker.quote(symbol).spread)
            except Exception:  # noqa: BLE001
                pass
            _time.sleep(args.spread_interval)
        if not samples:
            raise RuntimeError("Spreadni o'lchab bo'lmadi — bozor yopiq bo'lishi mumkin.")
        spread = float(np.median(samples))
        print(f"  Spread: median {spread:.2f}  "
              f"(min {min(samples):.2f}, max {max(samples):.2f})")

        print(f"  Barlar yuklanmoqda ({args.count:,} so'ralmoqda)...")
        df = broker.bars(symbol, cfg.timeframe, count=args.count)
        print(f"  {len(df):,} bar olindi: {df.index[0]:%Y-%m-%d} - {df.index[-1]:%Y-%m-%d}")
        if args.save_data:
            save_csv(df, args.save_data)
            print(f"  Ma'lumot saqlandi: {args.save_data}")

        rep = full_validation(
            df, cfg, symbol=symbol, spread=spread,
            commission_per_lot=args.commission,
            contract_size=spec.contract_size, folds=args.folds,
            train_days=args.train_days, test_days=args.test_days,
            max_combos=args.max_combos,
        )
        print("\n" + format_report(rep))
        if args.out:
            out = Path(args.out)
            out.mkdir(parents=True, exist_ok=True)
            (out / "validation.txt").write_text(format_report(rep), encoding="utf-8")
            if rep.wf is not None:
                rep.wf.folds.to_csv(out / "wf_folds.csv", index=False)
                rep.wf.oos_trades.to_csv(out / "wf_oos_trades.csv", index=False)
            print(f"\nSaqlandi: {out}/")
    finally:
        broker.disconnect()


def cmd_trade(args) -> None:
    from .trader import LiveTrader

    cfg = _config(args)
    dry_run = not args.live
    if not dry_run:
        print("\n" + "!" * 66)
        print("  DIQQAT: REAL SAVDO REJIMI — haqiqiy orderlar yuboriladi.")
        print(f"  Hisob: {args.login or 'MT5_LOGIN'}   Instrument: {args.symbol or cfg.symbol}")
        print(f"  Risk: {cfg.risk.risk_per_trade * 100:.2f} % / savdo")
        print("!" * 66)
        if input("\n  Davom etish uchun 'HA' deb yozing: ").strip() != "HA":
            print("  Bekor qilindi.")
            return

    broker = _mt5_broker(args, dry_run=dry_run)
    try:
        symbol = broker.resolve_symbol(args.symbol or cfg.symbol)
        trader = LiveTrader(broker, cfg, symbol, dry_run=dry_run,
                            state_path=args.state)
        if args.once:
            trader.run_once()
        else:
            trader.run_forever(poll_seconds=args.poll)
    finally:
        broker.disconnect()


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

    s = sub.add_parser("validate", help="To'liq tekshiruv: backtest + walk-forward + xulosa")
    common(s)
    s.add_argument("--spread", type=float,
                   help="O'lchangan spread (narx birligida). Berilsa xarajat shunga moslanadi")
    s.add_argument("--commission", type=float, default=0.0, help="Bir lot uchun komissiya")
    s.add_argument("--folds", type=int, help="Walk-forward bosqichlari (avtomatik)")
    s.add_argument("--train-days", type=int, default=180)
    s.add_argument("--test-days", type=int, default=45)
    s.add_argument("--max-combos", type=int, default=120)
    s.add_argument("--out", help="Natijalarni saqlash papkasi")
    s.set_defaults(func=cmd_validate)

    # ------------------------------ MT5 (faqat Windows) ------------------------------
    def mt5_args(sp):
        sp.add_argument("--login", type=int, help="MT5 login (yoki MT5_LOGIN)")
        sp.add_argument("--server", help="MT5 server (yoki MT5_SERVER)")
        sp.add_argument("--path", help="terminal64.exe yo'li (yoki MT5_PATH)")
        sp.add_argument("--symbol", help="Instrument nomi (masalan BTCUSD)")

    s = sub.add_parser("mt5-test", help="MT5 ulanish, spread va signal tekshiruvi")
    common(s, data=False)
    mt5_args(s)
    s.add_argument("--commission", type=float, default=0.0,
                   help="Bir lot uchun komissiya (Raw/Zero hisoblarda)")
    s.set_defaults(func=cmd_mt5_test)

    s = sub.add_parser("mt5-bars", help="MT5 dan barlarni CSV ga yuklash")
    common(s, data=False)
    mt5_args(s)
    s.add_argument("--interval", default="5m")
    s.add_argument("--count", type=int, default=50_000)
    s.add_argument("--out", default="data/MT5_BTCUSD_5m.csv")
    s.set_defaults(func=cmd_mt5_bars)

    s = sub.add_parser("mt5-validate",
                       help="MT5 dan ma'lumot olib to'liq tekshiruv (bitta buyruq)")
    common(s, data=False)
    mt5_args(s)
    s.add_argument("--count", type=int, default=200_000, help="So'raladigan barlar soni")
    s.add_argument("--commission", type=float, default=0.0)
    s.add_argument("--spread-samples", type=int, default=10)
    s.add_argument("--spread-interval", type=float, default=1.0)
    s.add_argument("--folds", type=int)
    s.add_argument("--train-days", type=int, default=180)
    s.add_argument("--test-days", type=int, default=45)
    s.add_argument("--max-combos", type=int, default=120)
    s.add_argument("--save-data", default="data/EXNESS_5m.csv",
                   help="Yuklangan barlarni CSV ga saqlash")
    s.add_argument("--out", default="out/exness")
    s.set_defaults(func=cmd_mt5_validate)

    s = sub.add_parser("trade", help="Jonli savdo sikli (standart: DRY-RUN)")
    common(s, data=False)
    mt5_args(s)
    s.add_argument("--live", action="store_true",
                   help="HAQIQIY orderlar yuborish (tasdiqlash so'raladi)")
    s.add_argument("--once", action="store_true", help="Bir marta ishlab to'xtash")
    s.add_argument("--poll", type=int, default=20, help="Tekshirish oralig'i, soniya")
    s.add_argument("--state", default="state/live_state.json")
    s.set_defaults(func=cmd_trade)
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
