"""Estimate a reduced-form Taylor rule with interest-rate smoothing (Chile).

Specification (all variables in quarterly fractions, from the real BCCh panel):

    i_t = c + a * i_{t-1} + b * pi_t + d * x_t + eps_t,

with the structural mapping rho_i = a, phi_pi = b / (1 - a), phi_x = d / (1 - a).

Two estimators are reported:
  * OLS with Newey-West (HAC) standard errors.
  * 2SLS/IV instrumenting current inflation and the gap with their own lags (and the
    lagged rate), which addresses the simultaneity between the policy rate and the
    contemporaneous inflation/gap it reacts to.

Structural-parameter standard errors use the delta method. Output:
outputs/tables/taylor_rule_estimates.csv.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from common import DATA_CLEAN, TABLES, ensure_directories


def _delta_ratio(params: np.ndarray, cov: np.ndarray, i_a: int, i_num: int) -> tuple[float, float]:
    """phi = params[i_num] / (1 - params[i_a]); delta-method standard error."""
    a = params[i_a]
    num = params[i_num]
    phi = num / (1.0 - a)
    grad = np.zeros(len(params))
    grad[i_a] = num / (1.0 - a) ** 2
    grad[i_num] = 1.0 / (1.0 - a)
    var = float(grad @ cov @ grad)
    return phi, math.sqrt(var) if var > 0 else math.nan


def _tsls_hac(y: np.ndarray, X: np.ndarray, Z: np.ndarray, maxlags: int = 4):
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
    return beta, cov, r2


def _first_stage_f(endogenous: np.ndarray, instruments: np.ndarray) -> float:
    import statsmodels.api as sm

    result = sm.OLS(endogenous, instruments).fit()
    restrictions = np.zeros((instruments.shape[1] - 2, instruments.shape[1]))
    restrictions[:, 2:] = np.eye(instruments.shape[1] - 2)
    return float(result.f_test(restrictions).fvalue)


def main() -> None:
    ensure_directories()
    panel = pd.read_csv(DATA_CLEAN / "chile_macro_quarterly.csv")
    metadata = json.loads(
        (DATA_CLEAN / "dataset_metadata.json").read_text(encoding="utf-8")
    )
    is_synthetic = bool(metadata.get("is_synthetic", True))
    data_source = str(metadata.get("institution", metadata.get("source", "unknown")))
    base = pd.DataFrame(
        {
            "i": panel["i_q"],
            "pi": panel["infl_q"],
            "x": panel["output_gap"],
        }
    )
    for col in ("i", "pi", "x"):
        base[f"{col}_l1"] = base[col].shift(1)
        base[f"{col}_l2"] = base[col].shift(2)
    reg = base.dropna().reset_index(drop=True)
    n = len(reg)

    y = reg["i"].to_numpy()
    X = np.column_stack([np.ones(n), reg["i_l1"], reg["pi"], reg["x"]])  # c, a, b, d
    Z = np.column_stack(
        [np.ones(n), reg["i_l1"], reg["pi_l1"], reg["pi_l2"], reg["x_l1"], reg["x_l2"]]
    )

    rows = []

    import statsmodels.api as sm

    ols = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
    cov_ols = np.asarray(ols.cov_params())
    phi_pi, se_pp = _delta_ratio(ols.params, cov_ols, 1, 2)
    phi_x, se_px = _delta_ratio(ols.params, cov_ols, 1, 3)
    rows.append(
        {
            "method": "OLS_HAC",
            "c": float(ols.params[0]),
            "rho_i": float(ols.params[1]),
            "se_rho_i": float(ols.bse[1]),
            "phi_pi": phi_pi,
            "se_phi_pi": se_pp,
            "phi_x": phi_x,
            "se_phi_x": se_px,
            "r_squared": float(ols.rsquared),
            "observations": n,
            "first_stage_F_pi": np.nan,
            "first_stage_F_x": np.nan,
            "is_synthetic": is_synthetic,
            "data_source": data_source,
        }
    )

    beta_iv, cov_iv, r2_iv = _tsls_hac(y, X, Z)
    se_iv = np.sqrt(np.diag(cov_iv))
    phi_pi_iv, se_pp_iv = _delta_ratio(beta_iv, cov_iv, 1, 2)
    phi_x_iv, se_px_iv = _delta_ratio(beta_iv, cov_iv, 1, 3)
    rows.append(
        {
            "method": "IV_2SLS_HAC",
            "c": float(beta_iv[0]),
            "rho_i": float(beta_iv[1]),
            "se_rho_i": float(se_iv[1]),
            "phi_pi": phi_pi_iv,
            "se_phi_pi": se_pp_iv,
            "phi_x": phi_x_iv,
            "se_phi_x": se_px_iv,
            "r_squared": r2_iv,
            "observations": n,
            "first_stage_F_pi": _first_stage_f(reg["pi"].to_numpy(), Z),
            "first_stage_F_x": _first_stage_f(reg["x"].to_numpy(), Z),
            "is_synthetic": is_synthetic,
            "data_source": data_source,
        }
    )

    table = pd.DataFrame(rows)
    table.to_csv(TABLES / "taylor_rule_estimates.csv", index=False)
    print(table.round(4).to_string(index=False))
    print(f"Wrote {TABLES / 'taylor_rule_estimates.csv'}")


if __name__ == "__main__":
    main()
