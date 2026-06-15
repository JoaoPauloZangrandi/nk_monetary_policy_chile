"""Estimate a recursive VAR and compare its monetary IRF with the NK model.

Identification uses the quarterly Cholesky ordering [x, pi, i]. Output and
inflation may affect the policy rate within the quarter, while a monetary shock
affects them with a lag. This is a transparent reduced-form robustness check,
not an incontrovertible identification of Chilean monetary shocks.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.api import VAR

from common import DATA_CLEAN, DYNARE_OUTPUTS, FIGURES, TABLES, ensure_directories


VARIABLES = ["x", "pi", "i"]
LABELS = {"x": "Hiato do produto", "pi": "Inflacao", "i": "Taxa de politica"}
SCALES = {"x": 100.0, "pi": 400.0, "i": 400.0}
MONETARY_IMPACT_ANNUAL_PP = 0.25
# Dynare exports horizons 0..19 (20 observations).
HORIZON = 19


def main() -> None:
    ensure_directories()
    observables = pd.read_csv(DATA_CLEAN / "chile_observables.csv")
    data = observables[VARIABLES].astype(float)

    selection = VAR(data).select_order(maxlags=4, trend="c")
    selected_lag = max(1, int(selection.selected_orders.get("bic") or 1))
    lag_candidates = []
    for lag in range(1, 5):
        candidate = VAR(data).fit(lag, trend="c")
        try:
            whiteness = float(candidate.test_whiteness(nlags=8).pvalue)
        except Exception:  # noqa: BLE001
            whiteness = np.nan
        lag_candidates.append((lag, candidate, whiteness))
    acceptable = [item for item in lag_candidates if item[2] >= 0.05]
    if acceptable:
        estimated_lag, result, selected_whiteness = acceptable[0]
        lag_reason = "smallest lag with residual-whiteness p>=0.05"
    else:
        estimated_lag = selected_lag
        result = VAR(data).fit(estimated_lag, trend="c")
        selected_whiteness = float(
            result.test_whiteness(nlags=max(8, estimated_lag + 2)).pvalue
        )
        lag_reason = "BIC; no lag up to 4 passed residual-whiteness test"

    orth = result.orth_ma_rep(HORIZON)
    lower, upper = result.irf_errband_mc(
        orth=True, repl=2000, steps=HORIZON, signif=0.10, seed=20260615
    )
    policy_index = VARIABLES.index("i")
    impact_i = float(orth[0, policy_index, policy_index])
    normalization = MONETARY_IMPACT_ANNUAL_PP / (SCALES["i"] * impact_i)

    baseline = pd.read_csv(DYNARE_OUTPUTS / "baseline" / "irfs.csv")
    dsge_impact = float(baseline.loc[0, "i_e_i"])
    dsge_normalization = MONETARY_IMPACT_ANNUAL_PP / (
        SCALES["i"] * dsge_impact
    )

    records: list[dict] = []
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4), sharex=True)
    horizons = np.arange(HORIZON + 1)
    for response_index, variable in enumerate(VARIABLES):
        scale = SCALES[variable]
        point = orth[:, response_index, policy_index] * normalization * scale
        lo = lower[:, response_index, policy_index] * normalization * scale
        hi = upper[:, response_index, policy_index] * normalization * scale
        dsge = (
            baseline[f"{variable}_e_i"].to_numpy()[: HORIZON + 1]
            * dsge_normalization
            * scale
        )
        ax = axes[response_index]
        ax.fill_between(horizons, lo, hi, color="#9DB9D1", alpha=0.5,
                        label="SVAR: banda 90%")
        ax.plot(horizons, point, color="#1E4E79", linewidth=2.2,
                label=f"SVAR recursivo, VAR({estimated_lag})")
        ax.plot(horizons, dsge, color="#B45309", linestyle="--", linewidth=2.2,
                label="DSGE/NK")
        ax.axhline(0, color="black", linewidth=0.7)
        ax.set_title(LABELS[variable])
        ax.set_xlabel("Trimestres")
        ax.set_ylabel("p.p." if variable != "x" else "% do PIB")
        ax.grid(alpha=0.25)
        for h in horizons:
            records.append(
                {
                    "horizon": int(h),
                    "variable": variable,
                    "svar_response": float(point[h]),
                    "svar_lower_90": float(lo[h]),
                    "svar_upper_90": float(hi[h]),
                    "dsge_response": float(dsge[h]),
                    "normalization": "policy-rate impact = +0.25 annual p.p.",
                    "ordering": "x,pi,i",
                }
            )

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=3, loc="lower center", frameon=False)
    fig.suptitle(
        "Choque monetario contracionista: SVAR recursivo versus modelo NK"
    )
    fig.text(
        0.01,
        0.01,
        f"SVAR com ordenacao [x, pi, i], VAR({estimated_lag}); bandas Monte Carlo de 90%. "
        "Ambas as IRFs normalizadas para elevar a taxa em 0,25 p.p. anual no impacto.",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.10, 1, 0.94))
    fig.savefig(FIGURES / "svar_vs_dsge_irf.png", dpi=180)
    plt.close(fig)

    try:
        whiteness_p = float(result.test_whiteness(nlags=max(8, estimated_lag + 2)).pvalue)
    except Exception:  # noqa: BLE001
        whiteness_p = np.nan
    try:
        normality_p = float(result.test_normality().pvalue)
    except Exception:  # noqa: BLE001
        normality_p = np.nan

    diagnostics = pd.DataFrame(
        [
            {
                "observations": int(result.nobs),
                "selected_lags_bic": selected_lag,
                "estimated_lags": estimated_lag,
                "lag_choice_reason": lag_reason,
                "aic": float(result.aic),
                "bic": float(result.bic),
                "hqic": float(result.hqic),
                "stable": bool(result.is_stable()),
                "max_inverse_root": float(np.max(np.abs(result.roots) ** -1)),
                "whiteness_test_pvalue": whiteness_p,
                "normality_test_pvalue": normality_p,
                "cholesky_ordering": "x,pi,i",
                "monetary_shock": "third orthogonal innovation",
                "impact_normalization_annual_pp": MONETARY_IMPACT_ANNUAL_PP,
            }
        ]
    )
    pd.DataFrame(records).to_csv(TABLES / "svar_vs_dsge_irfs.csv", index=False)
    diagnostics.to_csv(TABLES / "svar_diagnostics.csv", index=False)

    print(diagnostics.to_string(index=False))
    for variable in VARIABLES:
        frame = pd.DataFrame(records)
        row = frame[(frame["variable"] == variable) & (frame["horizon"] == 4)].iloc[0]
        print(
            f"h=4 {variable}: SVAR={row['svar_response']:.4f}, "
            f"DSGE={row['dsge_response']:.4f}"
        )


if __name__ == "__main__":
    main()
