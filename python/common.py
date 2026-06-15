"""Shared paths and lightweight model-based fallback calculations."""

from __future__ import annotations

import math
import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_CLEAN = ROOT / "data" / "clean"
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"
LOGS = ROOT / "outputs" / "logs"
DYNARE_OUTPUTS = ROOT / "outputs" / "dynare"

# Shock standard deviations for the Chile baseline. They are calibrated to an
# explicitly illustrative FEVD target at the estimated interest-rate persistence.
# The target is a modelling choice, not an empirical decomposition published by BCCh.
SHOCK_STD = {"e_x": 0.00500, "e_pi": 0.00277, "e_i": 0.00068}
INITIAL_SHOCK_STD = {"e_x": 0.0050, "e_pi": 0.0025, "e_i": 0.0015}
BASELINE = {
    "rstar_annual": 0.03,
    "sigma": 1.0,
    "kappa": 0.10,
    "rho_i": 0.80,
    "phi_pi": 1.75,
    "phi_x": 0.50,
}


def ensure_directories() -> None:
    for path in (DATA_RAW, DATA_CLEAN, TABLES, FIGURES, LOGS, DYNARE_OUTPUTS):
        path.mkdir(parents=True, exist_ok=True)


def quarterly_rstar(annual_rate: float) -> float:
    return (1.0 + annual_rate) ** 0.25 - 1.0


def complete_parameters(overrides: dict | None = None) -> dict:
    params = dict(BASELINE)
    if overrides:
        params.update(overrides)
    params["rstar"] = quarterly_rstar(float(params["rstar_annual"]))
    params["beta"] = 1.0 / (1.0 + params["rstar"])
    return params


def calibration_rho() -> float:
    estimate_file = TABLES / "rhoi_estimate.csv"
    if not estimate_file.exists():
        return BASELINE["rho_i"]
    table = pd.read_csv(estimate_file)
    if table.empty or "rho_i_used" not in table:
        return BASELINE["rho_i"]
    value = float(table.loc[0, "rho_i_used"])
    return value if math.isfinite(value) else BASELINE["rho_i"]


def find_octave() -> Path | None:
    configured = os.environ.get("OCTAVE_BIN")
    candidates = [
        configured,
        shutil.which("octave-cli"),
        shutil.which("octave"),
        r"C:\Program Files\GNU Octave\Octave-11.1.0\mingw64\bin\octave-cli.exe",
        r"C:\Program Files\GNU Octave\Octave-10.3.0\mingw64\bin\octave-cli.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    octave_root = Path(r"C:\Program Files\GNU Octave")
    if octave_root.exists():
        matches = sorted(octave_root.glob(r"Octave-*\mingw64\bin\octave-cli.exe"))
        if matches:
            return matches[-1]
    return None


def find_dynare_matlab() -> Path | None:
    configured = os.environ.get("DYNARE_MATLAB")
    candidates = [
        configured,
        r"C:\dynare\7.1\matlab",
        r"C:\dynare\7.0\matlab",
        r"C:\Program Files\Dynare\7.1\matlab",
    ]
    for candidate in candidates:
        if candidate and (Path(candidate) / "dynare.m").exists():
            return Path(candidate)
    dynare_root = Path(r"C:\dynare")
    if dynare_root.exists():
        matches = sorted(dynare_root.glob(r"*\matlab\dynare.m"))
        if matches:
            return matches[-1].parent
    return None


def _state_coefficients(params: dict) -> tuple[float, float, float]:
    """Exact minimum-state-variable solution of the linear NK model.

    The only predetermined state is the lagged policy rate, so in the absence of
    shocks the dynamics collapse to a single stable eigenvalue a_i:
        x_t = a_x*i_{t-1},  pi_t = a_pi*i_{t-1},  i_t = a_i*i_{t-1}.
    a_i is the stable root (|a_i| < 1) of the system's characteristic cubic, which is
    unique under Blanchard-Kahn determinacy (one predetermined variable, two jumpers).
    """

    beta = params["beta"]
    sigma = params["sigma"]
    kappa = params["kappa"]
    rho_i = params["rho_i"]
    phi_pi = params["phi_pi"]
    phi_x = params["phi_x"]

    # Characteristic cubic P(a)=0 from a_x = a_x*a_i + ..., a_pi, and the Taylor rule:
    #   P(a) = (a-rho)*(beta a^2 - (1+beta+kappa/sigma) a + 1)
    #          + ((1-rho)/sigma)*((phi_pi*kappa + phi_x) a - phi_x*beta a^2)
    q2, q1, q0 = beta, -(1.0 + beta + kappa / sigma), 1.0
    c3 = q2
    c2 = q1 - rho_i * q2
    c1 = q0 - rho_i * q1
    c0 = -rho_i * q0
    g = (1.0 - rho_i) / sigma
    c2 += -g * phi_x * beta
    c1 += g * (phi_pi * kappa + phi_x)
    roots = np.roots([c3, c2, c1, c0])

    stable = [r.real for r in roots if abs(r.imag) < 1e-8 and abs(r) < 1.0 - 1e-10]
    if not stable:
        stable = [min(roots, key=lambda z: abs(z)).real]
    a_i = float(min(stable, key=lambda v: abs(v - rho_i)))

    determinant = (1.0 - a_i) * (1.0 - beta * a_i) - a_i * kappa / sigma
    a_x = (-a_i / sigma) * (1.0 - beta * a_i) / determinant
    a_pi = (-a_i * kappa / sigma) / determinant
    return a_x, a_pi, a_i


def characteristic_roots(params: dict) -> np.ndarray:
    """Eigenvalues (roots of the characteristic cubic) of the linear NK system.

    With one predetermined variable (the lagged rate) and two jumpers, Blanchard-Kahn
    determinacy requires exactly one root inside the unit circle.
    """
    beta = params["beta"]
    sigma = params["sigma"]
    kappa = params["kappa"]
    rho_i = params["rho_i"]
    phi_pi = params["phi_pi"]
    phi_x = params["phi_x"]
    q2, q1, q0 = beta, -(1.0 + beta + kappa / sigma), 1.0
    c3 = q2
    c2 = q1 - rho_i * q2
    c1 = q0 - rho_i * q1
    c0 = -rho_i * q0
    g = (1.0 - rho_i) / sigma
    c2 += -g * phi_x * beta
    c1 += g * (phi_pi * kappa + phi_x)
    return np.roots([c3, c2, c1, c0])


def fallback_irfs(
    params: dict, scenario: str, horizon: int = 20
) -> pd.DataFrame:
    """Generate model-based synthetic IRFs when Dynare output is unavailable."""

    a_x, a_pi, a_i = _state_coefficients(params)
    sigma = params["sigma"]
    rho_i = params["rho_i"]
    phi_pi = params["phi_pi"]
    phi_x = params["phi_x"]
    beta = params["beta"]

    c_i = a_x - (1.0 - a_pi) / sigma
    impact_matrix = np.array(
        [
            [1.0, 0.0, -c_i],
            [-params["kappa"], 1.0, -beta * a_pi],
            [
                -(1.0 - rho_i) * phi_x,
                -(1.0 - rho_i) * phi_pi,
                1.0,
            ],
        ]
    )

    records = []
    variables = ("x", "pi", "i")
    shocks = ("e_x", "e_pi", "e_i")
    for shock_index, shock in enumerate(shocks):
        innovation = np.zeros(3)
        innovation[shock_index] = SHOCK_STD[shock]
        impact = np.linalg.solve(impact_matrix, innovation)
        responses = [impact]
        lagged_rate = impact[2]
        for _ in range(1, horizon):
            current = np.array([a_x, a_pi, a_i]) * lagged_rate
            responses.append(current)
            lagged_rate = current[2]
        for period, response in enumerate(responses):
            for variable, value in zip(variables, response):
                records.append(
                    {
                        "scenario": scenario,
                        "source": "synthetic_model_fallback",
                        "variable": variable,
                        "shock": shock,
                        "horizon": period,
                        "response": float(value),
                    }
                )
    return pd.DataFrame.from_records(records)


def fallback_moments(params: dict, observations: int = 50000) -> pd.DataFrame:
    """Simulate deviation moments from the fallback solution."""

    a_x, a_pi, _ = _state_coefficients(params)
    sigma = params["sigma"]
    rho_i = params["rho_i"]
    beta = params["beta"]
    c_i = a_x - (1.0 - a_pi) / sigma
    impact_matrix = np.array(
        [
            [1.0, 0.0, -c_i],
            [-params["kappa"], 1.0, -beta * a_pi],
            [
                -(1.0 - rho_i) * params["phi_x"],
                -(1.0 - rho_i) * params["phi_pi"],
                1.0,
            ],
        ]
    )

    rng = np.random.default_rng(20260614)
    values = np.zeros((observations, 3))
    lagged_rate = 0.0
    std = np.array([SHOCK_STD["e_x"], SHOCK_STD["e_pi"], SHOCK_STD["e_i"]])
    for t in range(observations):
        rhs = rng.normal(0.0, std)
        rhs[2] += rho_i * lagged_rate
        values[t] = np.linalg.solve(impact_matrix, rhs)
        lagged_rate = values[t, 2]

    rows = []
    for index, variable in enumerate(("x", "pi", "i")):
        series = values[:, index]
        mean_value = float(series.mean())
        if variable == "i":
            mean_value += params["rstar"]
        rows.append(
            {
                "variable": variable,
                "mean": mean_value,
                "std_dev": float(series.std(ddof=1)),
                "variance": float(series.var(ddof=1)),
                "autocorrelation_1": float(np.corrcoef(series[1:], series[:-1])[0, 1]),
                "source": "synthetic_model_fallback",
            }
        )
    return pd.DataFrame(rows)
