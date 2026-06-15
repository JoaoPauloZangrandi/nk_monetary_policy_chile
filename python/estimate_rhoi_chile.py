"""Estimate the AR(1) persistence of the quarterly policy rate and pick rho_i.

Implements exactly the assignment's step: regress the quarterly policy rate on its
own lag, i_t = alpha + rho_i * i_{t-1} + u_t, by OLS with Newey-West (HAC) standard
errors. With real BCCh data the estimate is used directly in the calibration; with a
synthetic series (or an implausible estimate) it falls back to the baseline 0.80.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from common import BASELINE, DATA_CLEAN, TABLES, ensure_directories


def main() -> None:
    ensure_directories()
    input_path = DATA_CLEAN / "chile_policy_rate.csv"
    if not input_path.exists():
        raise FileNotFoundError(
            "Missing data/clean/chile_policy_rate.csv. "
            "Run python/build_chile_dataset.py first."
        )

    frame = pd.read_csv(input_path)
    required = {"policy_rate", "is_synthetic"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Clean dataset is missing columns: {sorted(missing)}")

    rate = pd.to_numeric(frame["policy_rate"], errors="coerce")
    valid = rate.dropna()
    if len(valid) < 11:
        raise ValueError("At least 11 valid policy-rate observations are required.")

    dates = frame["date"].astype(str) if "date" in frame.columns else None
    sample_start = dates.iloc[1] if dates is not None else ""
    sample_end = dates.iloc[-1] if dates is not None else ""

    current = valid.to_numpy()[1:]
    lagged = valid.to_numpy()[:-1]
    n_obs = len(current)

    se_hac = math.nan
    method = "statsmodels_ols_hac"
    try:
        import statsmodels.api as sm

        design = sm.add_constant(lagged)
        ols = sm.OLS(current, design).fit()
        hac = sm.OLS(current, design).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
        alpha = float(ols.params[0])
        rho_estimate = float(ols.params[1])
        se_ols = float(ols.bse[1])
        se_hac = float(hac.bse[1])
        r_squared = float(ols.rsquared)
    except ImportError:
        method = "numpy_lstsq_fallback"
        design = np.column_stack([np.ones(n_obs), lagged])
        coefficients, _, _, _ = np.linalg.lstsq(design, current, rcond=None)
        alpha, rho_estimate = map(float, coefficients)
        residual = current - design @ coefficients
        sigma2 = float(residual @ residual / (n_obs - 2))
        covariance = sigma2 * np.linalg.inv(design.T @ design)
        se_ols = float(np.sqrt(covariance[1, 1]))
        r_squared = 1.0 - float(residual @ residual) / float(
            ((current - current.mean()) ** 2).sum()
        )

    se_for_ci = se_hac if math.isfinite(se_hac) else se_ols
    ci_low = rho_estimate - 1.96 * se_for_ci
    ci_high = rho_estimate + 1.96 * se_for_ci
    half_life = (
        math.log(0.5) / math.log(rho_estimate)
        if 0.0 < rho_estimate < 1.0
        else math.nan
    )
    long_run_mean = alpha / (1.0 - rho_estimate) if rho_estimate != 1.0 else math.nan

    is_synthetic = bool(
        frame["is_synthetic"].astype(str).str.lower().isin(["true", "1"]).all()
    )
    data_source = (
        str(frame["data_source"].iloc[0])
        if "data_source" in frame.columns
        else "unknown"
    )
    if is_synthetic or not 0.0 <= rho_estimate < 0.999:
        rho_used = BASELINE["rho_i"]
        basis = "fallback_0.80_synthetic_or_implausible_estimate"
    else:
        rho_used = min(max(rho_estimate, 0.0), 0.98)
        basis = "estimated_ar1_real_bcch_tpm"

    output = pd.DataFrame(
        [
            {
                "alpha": alpha,
                "rho_i_estimate": rho_estimate,
                "rho_i_se_ols": se_ols,
                "rho_i_se_hac": se_hac,
                "rho_i_ci95_low": ci_low,
                "rho_i_ci95_high": ci_high,
                "half_life_quarters": half_life,
                "long_run_mean_pct": long_run_mean,
                "rho_i_used": rho_used,
                "r_squared": r_squared,
                "observations": n_obs,
                "sample_start": sample_start,
                "sample_end": sample_end,
                "is_synthetic": is_synthetic,
                "data_source": data_source,
                "calibration_basis": basis,
                "estimation_method": method,
            }
        ]
    )
    destination = TABLES / "rhoi_estimate.csv"
    output.to_csv(destination, index=False)
    print(output.T.to_string())
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
