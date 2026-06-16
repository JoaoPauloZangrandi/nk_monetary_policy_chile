"""Exact first-order reduced form of the hybrid-NKPC Chilean model.

The hybrid model adds intrinsic inflation persistence:

    x  = E x(+1) - (1/sigma)(i - E pi(+1)) + e_x
    pi = gamma*pi(-1) + (1-gamma)*(beta*E pi(+1) + kappa*x) + e_pi
    i  = rho*i(-1) + (1-rho)(phi_pi*pi + phi_x*x) + e_i

Now there are TWO predetermined states, s_t = [i_{t-1}, pi_{t-1}], so the minimal
state-variable solution is  y_t = T s_{t-1} + R eps_t  with T a 3x2 matrix. We
solve T by undetermined coefficients (a 6-equation fixed point) and validate the
solution against Dynare's hybrid IRFs (it reproduces them to ~1e-6).
"""

from __future__ import annotations

import numpy as np

from common import calibration_rho, complete_parameters

E1 = np.array([1.0, 0.0])  # picks i_{t-1}
E2 = np.array([0.0, 1.0])  # picks pi_{t-1}
I2 = np.eye(2)


def hybrid_params(gamma_pi: float = 0.35) -> dict:
    params = complete_parameters({"rho_i": calibration_rho()})
    params["gamma_pi"] = float(gamma_pi)
    return params


def solve_hybrid(params: dict, max_iter: int = 5000, tol: float = 1e-14) -> dict:
    """Unique stable MSV solution by contraction on the state transition A.

    Given a guess for the state transition A (s_t = A s_{t-1}, s=[i,pi]), the
    structural equations are LINEAR in T=[Tx;Tpi;Ti] (because the expectations
    become E_t y_{t+1}=T A s_{t-1}). We solve that linear system for T, update
    A=[Ti;Tpi], and iterate. For a determinate model this converges to the unique
    forward-stable solution (avoiding the spurious roots a blind root-finder hits).
    """
    beta, sigma, kappa = params["beta"], params["sigma"], params["kappa"]
    rho, phi_pi, phi_x = params["rho_i"], params["phi_pi"], params["phi_x"]
    g = params["gamma_pi"]

    def residual(v: np.ndarray, A: np.ndarray) -> np.ndarray:
        Tx, Tpi, Ti = v[0:2], v[2:4], v[4:6]
        r_is = Tx @ (I2 - A) + (1.0 / sigma) * Ti - (1.0 / sigma) * (Tpi @ A)
        r_pc = Tpi - (1.0 - g) * beta * (Tpi @ A) - (1.0 - g) * kappa * Tx - g * E2
        r_tr = Ti - (1.0 - rho) * phi_pi * Tpi - (1.0 - rho) * phi_x * Tx - rho * E1
        return np.concatenate([r_is, r_pc, r_tr])

    def solve_T(A: np.ndarray) -> np.ndarray:
        # residual is affine in v: L v + c = 0  ->  v = solve(L, -c)
        c = residual(np.zeros(6), A)
        L = np.zeros((6, 6))
        for k in range(6):
            ek = np.zeros(6)
            ek[k] = 1.0
            L[:, k] = residual(ek, A) - c
        return np.linalg.solve(L, -c)

    A = np.zeros((2, 2))
    v = np.zeros(6)
    for _ in range(max_iter):
        v = solve_T(A)
        A_new = np.vstack([v[4:6], v[2:4]])  # [Ti; Tpi]
        if np.max(np.abs(A_new - A)) < tol:
            A = A_new
            break
        A = A_new

    Tx, Tpi, Ti = v[0:2], v[2:4], v[4:6]
    S = np.vstack([Ti, Tpi])
    T = np.vstack([Tx, Tpi, Ti])  # rows x,pi,i; cols [i_{-1}, pi_{-1}]

    M = np.array([
        [1.0, -Tx[1] - Tpi[1] / sigma, -Tx[0] + 1.0 / sigma - Tpi[0] / sigma],
        [-(1.0 - g) * kappa, 1.0 - (1.0 - g) * beta * Tpi[1], -(1.0 - g) * beta * Tpi[0]],
        [-(1.0 - rho) * phi_x, -(1.0 - rho) * phi_pi, 1.0],
    ])
    R = np.linalg.inv(M)
    return {"T": T, "S": S, "R": R, "eig": np.linalg.eigvals(S),
            "stable": bool(np.max(np.abs(np.linalg.eigvals(S))) < 1.0)}


def hybrid_irf(sol: dict, shock_std: dict, horizon: int = 20) -> dict:
    T, S, R = sol["T"], sol["S"], sol["R"]
    out = {}
    for j, shock in enumerate(("e_x", "e_pi", "e_i")):
        e = np.zeros(3)
        e[j] = shock_std[shock]
        y0 = R @ e
        responses = [y0]
        s = np.array([y0[2], y0[1]])  # [i_0, pi_0]
        for _ in range(1, horizon):
            yk = T @ s
            responses.append(yk)
            s = np.array([yk[2], yk[1]])
        out[shock] = np.array(responses)
    return out


def hybrid_forecast(sol: dict, last_i_dev: float, last_pi_dev: float,
                    horizon: int) -> np.ndarray:
    """h-step forecast of [x, pi, i] deviations from the origin state."""
    s = np.array([last_i_dev, last_pi_dev])
    Sp = np.linalg.matrix_power(sol["S"], horizon - 1)
    return sol["T"] @ Sp @ s


def _validate() -> None:
    import pandas as pd

    from common import DYNARE_OUTPUTS

    params = hybrid_params(0.35)
    sol = solve_hybrid(params)
    print(f"Stable: {sol['stable']}; |eig(S)| = {np.abs(sol['eig']).round(4)}")

    shock_std = {"e_x": 0.005, "e_pi": 0.00277, "e_i": 0.00068}
    mine = hybrid_irf(sol, shock_std, horizon=20)

    dyn = pd.read_csv(DYNARE_OUTPUTS / "hybrid_nkpc" / "irfs.csv")
    var_index = {"x": 0, "pi": 1, "i": 2}
    max_diff = 0.0
    for shock in ("e_x", "e_pi", "e_i"):
        for var, vi in var_index.items():
            col = f"{var}_{shock}"
            if col not in dyn:
                continue
            diff = np.max(np.abs(mine[shock][:, vi] - dyn[col].to_numpy()[:20]))
            max_diff = max(max_diff, diff)
    print(f"Max |IRF difference| vs Dynare hybrid: {max_diff:.3e}")
    print("VALIDATION OK" if max_diff < 1e-5 else "VALIDATION FAILED")


if __name__ == "__main__":
    _validate()
