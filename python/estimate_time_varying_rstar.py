"""Estimate a transparent time-varying statistical proxy for Chilean r-star.

Expected inflation is generated recursively with an AR model, so the ex-ante
real policy rate does not use future inflation. A local-level state-space model
then separates a slow-moving latent component from high-frequency noise, with
the lagged output gap as a cyclical control.

This is deliberately labelled a proxy. It is not a full Laubach-Williams model:
potential growth, the IS relation and inflation expectations are not jointly
estimated in a structural system.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.statespace.structural import UnobservedComponents

from common import DATA_CLEAN, FIGURES, TABLES, ensure_directories


def recursive_inflation_expectation(pi: np.ndarray, max_lags: int = 4) -> np.ndarray:
    expected = np.full(len(pi), np.nan)
    for t in range(len(pi)):
        if t < 8:
            expected[t] = float(np.mean(pi[: t + 1]))
            continue
        lags = min(max_lags, t - 2)
        y = pi[lags:t]
        x = np.column_stack(
            [pi[lags - lag - 1:t - lag - 1] for lag in range(lags)]
        )
        model = sm.OLS(y, sm.add_constant(x)).fit()
        predictors = np.r_[1.0, [pi[t - lag - 1] for lag in range(lags)]]
        expected[t] = float(model.predict(predictors)[0])
    return expected


def annualized_real_rate(nominal_q: np.ndarray, expected_inflation_q: np.ndarray) -> np.ndarray:
    return (((1.0 + nominal_q) / (1.0 + expected_inflation_q)) ** 4 - 1.0) * 100.0


def main() -> None:
    ensure_directories()
    macro = pd.read_csv(DATA_CLEAN / "chile_macro_quarterly.csv")
    pi_q = macro["infl_q"].to_numpy(dtype=float)
    expected_pi_q = recursive_inflation_expectation(pi_q)
    real_ex_ante = annualized_real_rate(
        macro["i_q"].to_numpy(dtype=float), expected_pi_q
    )
    gap_lag = (100.0 * macro["output_gap"]).shift(1).fillna(0.0)

    model = UnobservedComponents(
        real_ex_ante,
        level="local level",
        exog=pd.DataFrame({"output_gap_lag_pp": gap_lag}),
    )
    result = model.fit(disp=False, maxiter=2000)
    smoothed = np.asarray(result.level.smoothed)
    filtered = np.asarray(result.level.filtered)
    variance = np.maximum(np.asarray(result.level.smoothed_cov), 0.0)
    se = np.sqrt(variance)

    output = pd.DataFrame(
        {
            "date": macro["date"],
            "policy_rate_annual_pct": macro["tpm_annual_pct"],
            "expected_inflation_annual_pct": ((1.0 + expected_pi_q) ** 4 - 1.0) * 100.0,
            "real_rate_ex_ante_annual_pct": real_ex_ante,
            "rstar_filtered_pct": filtered,
            "rstar_smoothed_pct": smoothed,
            "rstar_lower_95_pct": smoothed - 1.96 * se,
            "rstar_upper_95_pct": smoothed + 1.96 * se,
            "output_gap_pct": 100.0 * macro["output_gap"],
        }
    )
    output.to_csv(TABLES / "rstar_time_varying.csv", index=False)

    summary = pd.DataFrame(
        [
            {
                "method": "local_level_state_space_proxy",
                "sample_start": macro["date"].iloc[0],
                "sample_end": macro["date"].iloc[-1],
                "observations": len(macro),
                "converged": bool(result.mle_retvals.get("converged", False)),
                "latest_rstar_smoothed_pct": float(smoothed[-1]),
                "latest_rstar_filtered_pct": float(filtered[-1]),
                "sample_mean_rstar_pct": float(np.mean(smoothed)),
                "sample_min_rstar_pct": float(np.min(smoothed)),
                "sample_max_rstar_pct": float(np.max(smoothed)),
                "variance_irregular": float(result.params["sigma2.irregular"]),
                "variance_level": float(result.params["sigma2.level"]),
                "gap_coefficient": float(result.params["beta.output_gap_lag_pp"]),
                "fixed_grid_low_pct": 2.0,
                "fixed_grid_baseline_pct": 3.0,
                "fixed_grid_high_pct": 4.0,
                "interpretation": "statistical proxy; not structural Laubach-Williams r-star",
            }
        ]
    )
    summary.to_csv(TABLES / "rstar_time_varying_summary.csv", index=False)

    x = np.arange(len(macro))
    ticks = np.arange(0, len(macro), 8)
    labels = macro.loc[ticks, "date"]
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    axes[0].plot(x, real_ex_ante, color="#9CA3AF", linewidth=1,
                 label="Juro real ex ante (proxy)")
    axes[0].fill_between(
        x,
        output["rstar_lower_95_pct"],
        output["rstar_upper_95_pct"],
        color="#93C5FD",
        alpha=0.35,
        label="IC 95% do nivel latente",
    )
    axes[0].plot(x, smoothed, color="#1E4E79", linewidth=2.2,
                 label="r* suavizado (proxy)")
    axes[0].plot(x, filtered, color="#16A34A", linewidth=1.4, linestyle="--",
                 label="r* filtrado")
    axes[0].axhspan(2.0, 4.0, color="#F59E0B", alpha=0.10, label="Grade fixa 2%-4%")
    axes[0].axhline(3.0, color="#B45309", linestyle=":", linewidth=1.3)
    axes[0].set_ylabel("% a.a.")
    axes[0].set_title("Taxa real ex ante e componente neutro variavel")
    axes[0].legend(ncol=3, fontsize=8)
    axes[0].grid(alpha=0.25)

    axes[1].plot(x, macro["infl_annual_pct"], color="#B45309", linewidth=1.5,
                 label="Inflacao realizada anualizada")
    axes[1].plot(x, output["expected_inflation_annual_pct"], color="#1E4E79",
                 linewidth=1.5, label="Inflacao esperada AR recursiva")
    axes[1].axhline(3.0, color="black", linestyle=":", linewidth=1,
                    label="Meta de 3%")
    axes[1].set_ylabel("% a.a.")
    axes[1].set_title("Proxy de expectativas usada no juro real ex ante")
    axes[1].legend(ncol=3, fontsize=8)
    axes[1].grid(alpha=0.25)
    axes[1].set_xticks(ticks)
    axes[1].set_xticklabels(labels, rotation=70, fontsize=8)
    fig.suptitle("Chile: proxy estatistica de r* variavel no tempo")
    fig.text(
        0.01,
        0.01,
        "Modelo local-level com hiato defasado. Nao e uma estimativa estrutural "
        "Laubach-Williams; expectativas sao previsoes AR recursivas.",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    fig.savefig(FIGURES / "rstar_time_varying.png", dpi=180)
    plt.close(fig)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
