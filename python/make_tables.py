"""Create the parameter-target table and the neutral-rate conversion table.

The parameter-target table is the assignment's headline "parameter <-> target" deliverable.
It lists each calibrated value next to its empirical counterpart (when an estimate exists:
AR(1) for rho_i, IV/OLS Taylor rule for phi_pi/phi_x, NKPC for kappa, HP proxy for r*).
"""

from __future__ import annotations

import pandas as pd

from common import (
    BASELINE,
    SHOCK_STD,
    TABLES,
    calibration_rho,
    complete_parameters,
    ensure_directories,
    quarterly_rstar,
)


def _safe_read(name: str) -> pd.DataFrame | None:
    path = TABLES / name
    return pd.read_csv(path) if path.exists() else None


def empirical_estimates() -> dict[str, str]:
    emp: dict[str, str] = {}
    rhoi = _safe_read("rhoi_estimate.csv")
    if (
        rhoi is not None
        and not rhoi.empty
        and not bool(rhoi.iloc[0].get("is_synthetic", True))
    ):
        r = rhoi.iloc[0]
        emp["rho_i"] = f"{r['rho_i_estimate']:.3f} (AR1; HAC SE {r['rho_i_se_hac']:.3f})"
    taylor = _safe_read("taylor_rule_estimates.csv")
    if (
        taylor is not None
        and not taylor.empty
        and not bool(taylor.iloc[0].get("is_synthetic", True))
    ):
        iv = taylor[taylor["method"].str.startswith("IV_2SLS")]
        ols = taylor[taylor["method"] == "OLS_HAC"]
        if not iv.empty and not ols.empty:
            emp["phi_pi"] = (
                f"{iv.iloc[0]['phi_pi']:.2f} (IV-HAC); "
                f"{ols.iloc[0]['phi_pi']:.2f} (OLS-HAC)"
            )
            emp["phi_x"] = f"{iv.iloc[0]['phi_x']:.2f} (IV-HAC)"
    nkpc = _safe_read("nkpc_estimates.csv")
    if (
        nkpc is not None
        and not nkpc.empty
        and not bool(nkpc.iloc[0].get("is_synthetic", True))
    ):
        bw = nkpc[nkpc["method"] == "backward_OLS_HAC"]
        if not bw.empty:
            emp["kappa"] = f"{bw.iloc[0]['kappa']:.3f} (backward OLS, HAC)"
    rstar = _safe_read("rstar_estimates.csv")
    if (
        rstar is not None
        and not rstar.empty
        and not bool(rstar.iloc[0].get("is_synthetic", True))
    ):
        hp = rstar[rstar["method"] == "hp_trend_real_rate_end_of_sample"]
        if not hp.empty:
            emp["rstar_annual"] = f"{hp.iloc[0]['rstar_annual_pct']:.2f}% a.a. (HP proxy)"
    return emp


def main() -> None:
    ensure_directories()
    rho_i = calibration_rho()
    beta = complete_parameters()["beta"]
    emp = empirical_estimates()

    rows = [
        ("rstar_annual", BASELINE["rstar_annual"], emp.get("rstar_annual", ""),
         "Annual neutral real rate; scenarios 2/3/4%"),
        ("beta", round(beta, 6), "",
         "Discount factor = 1/(1+rstar_q), derived from r*"),
        ("sigma", BASELINE["sigma"], "",
         "Inverse intertemporal elasticity; log-utility benchmark"),
        ("kappa", BASELINE["kappa"], emp.get("kappa", ""),
         "Phillips-curve slope; sensitivity grid {0.07,0.10,0.13}"),
        ("rho_i", round(rho_i, 4), emp.get("rho_i", ""),
         "Interest-rate smoothing; AR(1) of the quarterly TPM"),
        ("phi_pi", BASELINE["phi_pi"], emp.get("phi_pi", ""),
         "Inflation response; grid [1.3,2.2]; determinacy checked numerically"),
        ("phi_x", BASELINE["phi_x"], emp.get("phi_x", ""),
         "Output-gap response (held fixed at 0.5)"),
        ("std_e_x", SHOCK_STD["e_x"], "",
         "Demand-shock std; illustrative model-based FEVD calibration"),
        ("std_e_pi", SHOCK_STD["e_pi"], "",
         "Cost-push-shock std; illustrative model-based FEVD calibration"),
        ("std_e_i", SHOCK_STD["e_i"], "",
         "Monetary-shock std; illustrative model-based FEVD calibration"),
    ]
    parameter_table = pd.DataFrame(
        rows,
        columns=["parameter", "calibrated_value", "empirical_estimate",
                 "target_or_rationale"],
    )
    parameter_table["country"] = "Chile"
    parameter_table.to_csv(TABLES / "parameter_targets.csv", index=False)

    rows_rstar = []
    for annual in (0.02, 0.03, 0.04):
        quarterly = quarterly_rstar(annual)
        rows_rstar.append(
            {
                "rstar_annual": annual,
                "rstar_annual_percent": annual * 100.0,
                "rstar_quarterly": quarterly,
                "rstar_quarterly_percent": quarterly * 100.0,
                "beta": 1.0 / (1.0 + quarterly),
            }
        )
    pd.DataFrame(rows_rstar).to_csv(TABLES / "rstar_beta_table.csv", index=False)
    print("Wrote parameter_targets.csv and rstar_beta_table.csv")
    print(parameter_table.to_string(index=False))


if __name__ == "__main__":
    main()
