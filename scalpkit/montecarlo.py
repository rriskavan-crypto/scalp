"""Monte Carlo tahlili — "shu natija omadmi yoki ustunlikmi?" degan savolga javob.

Bitta backtest egri chizig'i — savdolar ketma-ketligining BITTA mumkin bo'lgan
tartibi. Xuddi shu savdolar boshqa tartibda kelganida drawdown ikki barobar
chuqurroq bo'lishi mumkin edi. Bu modul savdolarni minglab marta aralashtirib,
natijalar TAQSIMOTINI beradi — shu asosda:

  * eng yomon holatdagi drawdownni ko'rish;
  * "risk of ruin" — hisobni yo'qotish ehtimolini o'lchash;
  * ustunlik nol bo'lgan farazni statistik rad etish.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class MonteCarloResult:
    final_returns: np.ndarray     # har bir simulyatsiyaning yakuniy foydasi (ulush)
    max_drawdowns: np.ndarray     # har bir simulyatsiyaning maksimal drawdowni
    risk_of_ruin: float
    prob_profit: float
    summary: pd.DataFrame


def bootstrap_equity(
    r_multiples: np.ndarray,
    n_sims: int = 5000,
    n_trades: int | None = None,
    risk_per_trade: float = 0.005,
    ruin_threshold: float = 0.50,
    seed: int = 42,
) -> MonteCarloResult:
    """Savdolarni qaytarish bilan aralashtirib ekviti yo'llarini simulyatsiya qiladi.

    Sobit ulushli hajm ishlatiladi (kapitalning % i), shuning uchun ekviti
    ko'paytma tarzida o'sadi — real savdodagidek.
    """
    r = np.asarray(r_multiples, dtype=float)
    r = r[np.isfinite(r)]
    if r.size == 0:
        raise ValueError("Monte Carlo uchun savdolar yo'q.")

    n_trades = n_trades or r.size
    rng = np.random.default_rng(seed)
    draws = rng.choice(r, size=(n_sims, n_trades), replace=True)

    # Ko'paytma o'sish: har savdoda kapitalning risk_per_trade ulushi xavfda
    growth = 1.0 + draws * risk_per_trade
    growth = np.maximum(growth, 1e-6)          # to'liq yo'qotishdan himoya
    equity = np.cumprod(growth, axis=1)

    peak = np.maximum.accumulate(equity, axis=1)
    drawdowns = (equity / peak - 1.0).min(axis=1)
    finals = equity[:, -1] - 1.0

    ruin = float((equity.min(axis=1) <= (1.0 - ruin_threshold)).mean())
    prob_profit = float((finals > 0).mean())

    # p5 = eng yomon 5 % (drawdown uchun ham, foyda uchun ham pastki dum)
    qs = [0.05, 0.25, 0.50, 0.75, 0.95]
    summary = pd.DataFrame({
        "yakuniy foyda %": np.quantile(finals, qs) * 100.0,
        "maks. drawdown %": np.quantile(drawdowns, qs) * 100.0,
    }, index=[f"p{int(q * 100)}" for q in qs])

    return MonteCarloResult(finals, drawdowns, ruin, prob_profit, summary)


def edge_significance_test(r_multiples: np.ndarray, n_sims: int = 10_000,
                           seed: int = 42) -> dict[str, float]:
    """Ustunlik noldan farq qiladimi? — bootstrap gipoteza testi.

    H0: o'rtacha R = 0 (ustunlik yo'q).
    Namuna nolga markazlashtiriladi, so'ng qaytarish bilan qayta tanlanadi;
    p-qiymat = nol farazi ostida kuzatilgan natijadan yaxshiroq chiqish ulushi.

    Bu yerda oddiy t-testdan foydalanilmaydi, chunki R-taqsimoti kuchli
    assimetrik (stoplar -1R da to'planadi, yutuqlar dumda cho'ziladi).
    """
    r = np.asarray(r_multiples, dtype=float)
    r = r[np.isfinite(r)]
    n = r.size
    if n < 10:
        return {"observed_mean_r": float(r.mean()) if n else np.nan,
                "p_value": np.nan, "n": float(n), "ci_low": np.nan,
                "ci_high": np.nan, "significant_5pct": 0.0}

    observed = float(r.mean())
    rng = np.random.default_rng(seed)

    # H0 taqsimoti: namunani nolga suramiz
    centered = r - observed
    null_means = rng.choice(centered, size=(n_sims, n), replace=True).mean(axis=1)
    p_value = float(
        (null_means >= observed).mean() if observed >= 0 else (null_means <= observed).mean()
    )

    # 95 % ishonch oralig'i (percentile bootstrap)
    boot_means = rng.choice(r, size=(n_sims, n), replace=True).mean(axis=1)
    ci_low, ci_high = np.quantile(boot_means, [0.025, 0.975])

    return {
        "observed_mean_r": observed,
        "p_value": p_value,
        "n": float(n),
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "significant_5pct": float(p_value < 0.05),
    }


def monte_carlo_report(mc: MonteCarloResult, pt: dict[str, float] | None = None) -> str:
    L = ["=" * 66, "MONTE CARLO TAHLILI".center(66), "=" * 66, "",
         "  Savdolar tartibi aralashtirilgan holdagi natijalar taqsimoti:", ""]
    L.append(mc.summary.round(2).to_string())
    L += ["",
          f"  Foyda bilan tugash ehtimoli   {mc.prob_profit * 100:.1f} %",
          f"  Risk of ruin (-50 %)          {mc.risk_of_ruin * 100:.2f} %",
          f"  Median maks. drawdown         {np.median(mc.max_drawdowns) * 100:.2f} %",
          f"  Eng yomon 5 % drawdown        {np.quantile(mc.max_drawdowns, 0.05) * 100:.2f} %"]
    if pt:
        if not pt.get("significant_5pct"):
            verdict = "Natija shovqindan farq qilmaydi (p >= 0.05) — ustunlik isbotlanmagan."
        elif pt["observed_mean_r"] > 0:
            verdict = "Musbat ustunlik statistik jihatdan ishonchli."
        else:
            verdict = "Natija ishonchli tarzda MANFIY — bu strategiya shu ma'lumotda pul yo'qotadi."
        L += ["", "-" * 66,
              f"  Ekspektatsiya         {pt['observed_mean_r']:+.3f} R",
              f"  95 % ishonch oralig'i [{pt['ci_low']:+.3f} R, {pt['ci_high']:+.3f} R]",
              f"  p-qiymat (H0: 0)      {pt['p_value']:.4f}",
              f"  {verdict}"]
    L.append("=" * 66)
    return "\n".join(L)
