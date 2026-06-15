"""Illustrative model-consistent scenarios from the calibrated NK model.

Works in deviations from steady state (the observables file is already demeaned).
The only predetermined state is the lagged policy rate, so the unconditional forecast
is the autonomous decay of the current state with expected shocks set to zero; bands
come from a Monte-Carlo of the calibrated shocks. Conditional forecasts impose an
exogenous interest-rate path and solve the IS/NKPC block under perfect foresight
(backward recursion to a zero terminal state).

Outputs: outputs/tables/forecast.csv and outputs/figures/forecast_fanchart.png.
"""

from __future__ import annotations

import json
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import (
    DATA_CLEAN,
    FIGURES,
    TABLES,
    _state_coefficients,
    calibration_rho,
    complete_parameters,
    SHOCK_STD,
    ensure_directories,
)

HORIZON = 8


def annual_pct(quarterly_fraction: float) -> float:
    return ((1.0 + quarterly_fraction) ** 4 - 1.0) * 100.0


def main() -> None:
    ensure_directories()
    params = complete_parameters({"rho_i": calibration_rho()})
    a_x, a_pi, a_i = _state_coefficients(params)
    sigma, beta, kappa = params["sigma"], params["beta"], params["kappa"]
    rho_i, phi_pi, phi_x = params["rho_i"], params["phi_pi"], params["phi_x"]
    c_i = a_x - (1.0 - a_pi) / sigma
    impact = np.array(
        [
            [1.0, 0.0, -c_i],
            [-kappa, 1.0, -beta * a_pi],
            [-(1.0 - rho_i) * phi_x, -(1.0 - rho_i) * phi_pi, 1.0],
        ]
    )

    obs = pd.read_csv(DATA_CLEAN / "chile_observables.csv")
    macro = pd.read_csv(DATA_CLEAN / "chile_macro_quarterly.csv")
    metadata = json.loads(
        (DATA_CLEAN / "dataset_metadata.json").read_text(encoding="utf-8")
    )
    is_synthetic = bool(metadata.get("is_synthetic", True))
    data_source = str(metadata.get("institution", metadata.get("source", "unknown")))
    mean_i = float(macro["i_q"].mean())
    mean_pi = float(macro["infl_q"].mean())
    mean_x = float(macro["output_gap"].mean())
    i0 = float(obs["i"].iloc[-1])
    last_period = pd.Period(str(obs["date"].iloc[-1]), freq="Q")
    future = [str(last_period + h) for h in range(1, HORIZON + 1)]

    records = []

    # 1) Unconditional mean (autonomous decay) + Monte-Carlo bands.
    prev = i0
    mean_path = {"x": [], "pi": [], "i": []}
    for _ in range(HORIZON):
        mean_path["x"].append(a_x * prev)
        mean_path["pi"].append(a_pi * prev)
        nxt = a_i * prev
        mean_path["i"].append(nxt)
        prev = nxt

    rng = np.random.default_rng(20260615)
    n_sim = 5000
    std = np.array([SHOCK_STD["e_x"], SHOCK_STD["e_pi"], SHOCK_STD["e_i"]])
    sims = np.zeros((n_sim, HORIZON, 3))
    for s in range(n_sim):
        prev_i = i0
        for h in range(HORIZON):
            rhs = rng.normal(0.0, std)
            rhs[2] += rho_i * prev_i
            v = np.linalg.solve(impact, rhs)
            sims[s, h] = v
            prev_i = v[2]
    p05 = np.percentile(sims, 5, axis=0)
    p95 = np.percentile(sims, 95, axis=0)

    var_index = {"x": 0, "pi": 1, "i": 2}
    for h in range(HORIZON):
        for var, idx in var_index.items():
            dev = mean_path[var][h]
            mean_add = {"x": mean_x, "pi": mean_pi, "i": mean_i}[var]
            level = (
                (dev + mean_add) * 100.0
                if var == "x"
                else annual_pct(dev + mean_add)
            )
            records.append(
                {
                    "horizon": h + 1,
                    "date": future[h],
                    "scenario": "unconditional",
                    "variable": var,
                    "value_dev": dev,
                    "value_level": level,
                    "p05_level": (
                        (p05[h, idx] + mean_add) * 100.0
                        if var == "x"
                        else annual_pct(p05[h, idx] + mean_add)
                    ),
                    "p95_level": (
                        (p95[h, idx] + mean_add) * 100.0
                        if var == "x"
                        else annual_pct(p95[h, idx] + mean_add)
                    ),
                }
            )

    # 2) Conditional forecasts: impose an interest-rate path, solve IS/NKPC forward.
    def conditional(i_path: list[float]) -> tuple[list[float], list[float]]:
        x = [0.0] * (HORIZON + 2)
        pi = [0.0] * (HORIZON + 2)
        for h in range(HORIZON, 0, -1):
            x[h] = x[h + 1] - (1.0 / sigma) * (i_path[h - 1] - pi[h + 1])
            pi[h] = beta * pi[h + 1] + kappa * x[h]
        return x[1 : HORIZON + 1], pi[1 : HORIZON + 1]

    scenarios = {
        "cond_rate_hold": [i0] * HORIZON,
        "cond_tighten_100bp_4q": [i0 + 0.0025] * 4 + [i0] * (HORIZON - 4),
    }
    for name, i_path in scenarios.items():
        x_path, pi_path = conditional(i_path)
        for h in range(HORIZON):
            for var, dev in (("x", x_path[h]), ("pi", pi_path[h]), ("i", i_path[h])):
                mean_add = {"x": mean_x, "pi": mean_pi, "i": mean_i}[var]
                level = (
                    (dev + mean_add) * 100.0
                    if var == "x"
                    else annual_pct(dev + mean_add)
                )
                records.append(
                    {
                        "horizon": h + 1,
                        "date": future[h],
                        "scenario": name,
                        "variable": var,
                        "value_dev": dev,
                        "value_level": level,
                        "p05_level": np.nan,
                        "p95_level": np.nan,
                    }
                )

    table = pd.DataFrame(records)
    table["is_synthetic"] = is_synthetic
    table["data_source"] = data_source
    table.to_csv(TABLES / "forecast.csv", index=False)

    # Figure: history + projections for annualised inflation and the policy rate.
    hist = macro.tail(12)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    for ax, var, col, title in (
        (axes[0], "pi", "infl_annual_pct", "Inflation (annual %)"),
        (axes[1], "i", "tpm_annual_pct", "Policy rate (annual %)"),
    ):
        ax.plot(hist["date"], hist[col], color="black", marker="o", ms=3, label="History")
        unc = table[(table["scenario"] == "unconditional") & (table["variable"] == var)]
        ax.plot(unc["date"], unc["value_level"], color="#1E4E79", lw=2, label="Unconditional")
        ax.fill_between(unc["date"], unc["p05_level"], unc["p95_level"], color="#1E4E79",
                        alpha=0.15, label="5-95% band")
        for name, color, lab in (
            ("cond_rate_hold", "#FF6B35", "Rate held flat"),
            ("cond_tighten_100bp_4q", "#16a34a", "+100bp for 4q"),
        ):
            cond = table[(table["scenario"] == name) & (table["variable"] == var)]
            ax.plot(cond["date"], cond["value_level"], color=color, lw=1.8, ls="--", label=lab)
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=90, labelsize=7)
        ax.grid(alpha=0.25)
        ax.legend(fontsize=7)
    fig.suptitle(
        "Illustrative model scenarios (8 quarters) - calibrated NK, Chile",
        fontsize=12,
    )
    fig.text(
        0.01,
        0.005,
        f"Input source: {data_source}; synthetic={is_synthetic}. "
        "Bands come from calibrated shocks (Monte Carlo), not an official forecast.",
        fontsize=7,
    )
    fig.tight_layout(rect=(0, 0.03, 1, 0.96))
    fig.savefig(FIGURES / "forecast_fanchart.png", dpi=180)
    plt.close(fig)

    print(table.head(12).to_string(index=False))
    print(f"Wrote {TABLES / 'forecast.csv'} and {FIGURES / 'forecast_fanchart.png'}")


if __name__ == "__main__":
    main()
