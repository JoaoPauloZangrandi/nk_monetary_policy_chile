"""Estimate the New Keynesian Phillips curve slope kappa (Chile, real data).

Inflation pi_t and the output gap x_t are quarterly fractions from the BCCh panel.
Three estimators of the slope kappa are reported:

  * Backward / accelerationist OLS (HAC):  pi_t = c + gamma_b*pi_{t-1} + kappa*x_t.
  * Forward-looking IV (2SLS):              pi_t = c + gamma_f*pi_{t+1} + kappa*x_t,
        with E_t pi_{t+1} instrumented by lagged inflation, gap and rate.
  * Restricted (gamma_f = beta = 0.9926):   (pi_t - beta*pi_{t+1}) = c + kappa*x_t.

Output: outputs/tables/nkpc_estimates.csv. The estimates are compared with the
calibration grid kappa in {0.07, 0.10, 0.13}.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from common import DATA_CLEAN, TABLES, complete_parameters, ensure_directories

KAPPA_GRID = (0.07, 0.10, 0.13)


def _tsls_hac(y, X, Z, maxlags: int = 4):
    ZtZ_inv = np.linalg.inv(Z.T @ Z)
    Pz = Z @ ZtZ_inv @ Z.T
    XtPzX_inv = np.linalg.inv(X.T @ Pz @ X)
    beta = XtPzX_inv @ X.T @ Pz @ y
    resid = y - X @ beta
    fitted_x = Pz @ X
    scores = fitted_x * resid[:, None]
    meat = scores.T @ scores
    for lag in range(1, min(maxlags, len(scores) - 1) + 1):
        weight = 1.0 - lag / (maxlags + 1.0)
        gamma = scores[lag:].T @ scores[:-lag]
        meat += weight * (gamma + gamma.T)
    cov = XtPzX_inv @ meat @ XtPzX_inv
    r2 = 1.0 - float(resid @ resid) / float(((y - y.mean()) ** 2).sum())
    return beta, np.sqrt(np.diag(cov)), r2


def _first_stage_f(endogenous, instruments) -> float:
    import statsmodels.api as sm

    result = sm.OLS(endogenous, instruments).fit()
    restrictions = np.zeros((instruments.shape[1] - 1, instruments.shape[1]))
    restrictions[:, 1:] = np.eye(instruments.shape[1] - 1)
    return float(result.f_test(restrictions).fvalue)


def main() -> None:
    ensure_directories()
    panel = pd.read_csv(DATA_CLEAN / "chile_macro_quarterly.csv")
    metadata = json.loads(
        (DATA_CLEAN / "dataset_metadata.json").read_text(encoding="utf-8")
    )
    is_synthetic = bool(metadata.get("is_synthetic", True))
    data_source = str(metadata.get("institution", metadata.get("source", "unknown")))
    base = pd.DataFrame({"pi": panel["infl_q"], "x": panel["output_gap"]})
    base["pi_lead"] = base["pi"].shift(-1)
    base["pi_l1"] = base["pi"].shift(1)
    base["pi_l2"] = base["pi"].shift(2)
    base["x_l1"] = base["x"].shift(1)
    base["x_l2"] = base["x"].shift(2)

    beta_disc = complete_parameters()["beta"]
    rows = []

    import statsmodels.api as sm

    # Backward-looking OLS (HAC).
    bw = base.dropna(subset=["pi", "pi_l1", "x"]).reset_index(drop=True)
    Xb = sm.add_constant(np.column_stack([bw["pi_l1"], bw["x"]]))
    ols = sm.OLS(bw["pi"].to_numpy(), Xb).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
    rows.append(
        {
            "method": "backward_OLS_HAC",
            "gamma": float(ols.params[1]),
            "kappa": float(ols.params[2]),
            "se_kappa": float(ols.bse[2]),
            "r_squared": float(ols.rsquared),
            "observations": int(len(bw)),
            "first_stage_F_pi_lead": np.nan,
            "first_stage_F_x": np.nan,
            "is_synthetic": is_synthetic,
            "data_source": data_source,
        }
    )

    # Forward-looking IV (instrument pi_{t+1} with lags).
    fw = base.dropna().reset_index(drop=True)
    n = len(fw)
    y = fw["pi"].to_numpy()
    X = np.column_stack([np.ones(n), fw["pi_lead"], fw["x"]])
    Z = np.column_stack(
        [np.ones(n), fw["pi_l1"], fw["pi_l2"], fw["x_l1"], fw["x_l2"]]
    )
    beta_iv, se_iv, r2_iv = _tsls_hac(y, X, Z)
    rows.append(
        {
            "method": "forward_IV_2SLS_HAC",
            "gamma": float(beta_iv[1]),
            "kappa": float(beta_iv[2]),
            "se_kappa": float(se_iv[2]),
            "r_squared": r2_iv,
            "observations": n,
            "first_stage_F_pi_lead": _first_stage_f(fw["pi_lead"].to_numpy(), Z),
            "first_stage_F_x": _first_stage_f(fw["x"].to_numpy(), Z),
            "is_synthetic": is_synthetic,
            "data_source": data_source,
        }
    )

    # Restricted: impose gamma_f = beta.
    rs = base.dropna(subset=["pi", "pi_lead", "x"]).reset_index(drop=True)
    y_r = (rs["pi"] - beta_disc * rs["pi_lead"]).to_numpy()
    Xr = sm.add_constant(rs["x"].to_numpy())
    olsr = sm.OLS(y_r, Xr).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
    rows.append(
        {
            "method": f"restricted_gamma_eq_beta({beta_disc:.4f})",
            "gamma": beta_disc,
            "kappa": float(olsr.params[1]),
            "se_kappa": float(olsr.bse[1]),
            "r_squared": float(olsr.rsquared),
            "observations": int(len(rs)),
            "first_stage_F_pi_lead": np.nan,
            "first_stage_F_x": np.nan,
            "is_synthetic": is_synthetic,
            "data_source": data_source,
        }
    )

    table = pd.DataFrame(rows)
    table["kappa_grid_nearest"] = table["kappa"].apply(
        lambda k: min(KAPPA_GRID, key=lambda g: abs(g - k))
    )
    table.to_csv(TABLES / "nkpc_estimates.csv", index=False)
    print(table.round(4).to_string(index=False))
    print(f"Wrote {TABLES / 'nkpc_estimates.csv'}")


if __name__ == "__main__":
    main()
