"""Visualise and cross-check the native Dynare forecast (slides 48-55).

The forecast itself is produced by Dynare (python/run_forecast.py runs
dynare/nk_chile_forecast.mod):

* the UNCONDITIONAL projection comes from estimation(..., forecast=8); Dynare
  returns oo_.forecast.Mean and the HPDinf/HPDsup credibility bands, launched
  from the smoothed end-of-sample state. We read those CSVs and draw the fan
  chart spliced onto the observed history.
* the CONDITIONAL projections come from Dynare's conditional_forecast command
  (hold the rate, tighten, force inflation to target). Dynare's
  conditional_forecast launches from the steady state, so here we ALSO recompute
  the same three experiments anchored to the current state with the exact
  first-order reduced form (identical to Dynare's solution: the unconditional
  mean matches oo_.forecast to the last digit). This anchored version connects
  continuously to history and recovers the monetary-policy innovation e_i needed
  to enforce each path.

All series are mapped back to interpretable annualised levels using the sample
means that build_chile_dataset.py removed when it created the observables
(pi = infl_q - mean(infl_q); i = i_q - mean(i_q); x = output_gap - mean).
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
    DYNARE_OUTPUTS,
    FIGURES,
    TABLES,
    calibration_rho,
    complete_parameters,
    ensure_directories,
    _state_coefficients,
)

HORIZON = 8
INFLATION_TARGET_ANNUAL = 0.03
FORECAST_DIR = DYNARE_OUTPUTS / "forecast"

# Palette (kept consistent with the rest of the figure set).
COLORS = {
    "unconditional": "#111827",
    "hold": "#FF6B35",
    "hike": "#16A34A",
    "pi_target": "#7C3AED",
}


def annual_pct(quarterly_fraction):
    return ((1.0 + quarterly_fraction) ** 4 - 1.0) * 100.0


def solution_matrices(params: dict) -> tuple[np.ndarray, np.ndarray]:
    """Return the reduced form  y_t = transition * i_{t-1} + impact * eps_t."""
    a_x, a_pi, a_i = _state_coefficients(params)
    sigma, beta, kappa = params["sigma"], params["beta"], params["kappa"]
    rho_i, phi_pi, phi_x = params["rho_i"], params["phi_pi"], params["phi_x"]
    c_i = a_x - (1.0 - a_pi) / sigma
    structural = np.array(
        [
            [1.0, 0.0, -c_i],
            [-kappa, 1.0, -beta * a_pi],
            [-(1.0 - rho_i) * phi_x, -(1.0 - rho_i) * phi_pi, 1.0],
        ]
    )
    transition = np.array([a_x, a_pi, a_i])
    impact = np.linalg.inv(structural)
    return transition, impact


def conditional_path(transition, impact, initial_i_gap, controlled_variable, targets):
    """Hit a constrained endogenous path using e_i, anchored at the current state."""
    index = {"x": 0, "pi": 1, "i": 2}[controlled_variable]
    policy_shock_index = 2
    values = np.zeros((HORIZON, 3))
    implied_policy_shocks = np.zeros(HORIZON)
    previous_i = initial_i_gap
    for horizon in range(HORIZON):
        mean = transition * previous_i
        innovations = np.zeros(3)
        if horizon in targets:
            denominator = impact[index, policy_shock_index]
            innovations[policy_shock_index] = (targets[horizon] - mean[index]) / denominator
        current = mean + impact @ innovations
        values[horizon] = current
        implied_policy_shocks[horizon] = innovations[policy_shock_index]
        previous_i = current[2]
    return values, implied_policy_shocks


def load_unconditional() -> pd.DataFrame:
    return pd.read_csv(FORECAST_DIR / "forecast_unconditional.csv")


def main() -> None:
    ensure_directories()
    params = complete_parameters({"rho_i": calibration_rho()})
    transition, impact = solution_matrices(params)

    macro = pd.read_csv(DATA_CLEAN / "chile_macro_quarterly.csv")
    observables = pd.read_csv(DATA_CLEAN / "chile_observables.csv")
    metadata = json.loads((DATA_CLEAN / "dataset_metadata.json").read_text(encoding="utf-8"))
    data_source = str(metadata.get("institution", metadata.get("source", "unknown")))

    # Level mapping: add back the sample means removed when building observables.
    mean_infl_q = float(macro["infl_q"].mean())
    mean_i_q = float(macro["i_q"].mean())
    mean_tpm_annual = annual_pct(mean_i_q)
    mean_infl_annual = annual_pct(mean_infl_q)
    target_q = (1.0 + INFLATION_TARGET_ANNUAL) ** 0.25 - 1.0
    pi_target_dev = target_q - mean_infl_q  # 3% target as a demeaned inflation gap

    def to_level(variable: str, deviation):
        if variable == "x":
            return 100.0 * np.asarray(deviation)
        if variable == "pi":
            return annual_pct(mean_infl_q + np.asarray(deviation))
        return annual_pct(mean_i_q + np.asarray(deviation))

    last_i_gap = float(observables.iloc[-1]["i"])
    last_period = pd.Period(str(observables.iloc[-1]["date"]), freq="Q")
    future = [str(last_period + h) for h in range(1, HORIZON + 1)]

    # ------------------------------------------------------------------ #
    # 1) Unconditional forecast: read Dynare's mean and HPD bands.        #
    # ------------------------------------------------------------------ #
    uncond = load_unconditional()
    uncond = uncond.assign(
        mean_level=lambda d: [to_level(v, m) for v, m in zip(d["variable"], d["mean"])],
        inf_level=lambda d: [to_level(v, m) for v, m in zip(d["variable"], d["hpd_inf"])],
        sup_level=lambda d: [to_level(v, m) for v, m in zip(d["variable"], d["hpd_sup"])],
        date=lambda d: [future[h - 1] for h in d["horizon"]],
    )

    # ------------------------------------------------------------------ #
    # 2) Conditional experiments anchored at the current state.          #
    # ------------------------------------------------------------------ #
    scenarios = {
        "hold": {
            "label": "Hold rate at current level (2q)",
            "controlled": "i",
            "targets": {0: last_i_gap, 1: last_i_gap},
        },
        "hike": {
            "label": "Tighten ~+1pp for 4q",
            "controlled": "i",
            "targets": {h: 0.0025 for h in range(4)},
        },
        "pi_target": {
            "label": "Inflation to 3% target for 4q",
            "controlled": "pi",
            "targets": {h: pi_target_dev for h in range(4)},
        },
    }
    # Unconditional reduced-form mean (matches Dynare oo_.forecast to last digit).
    uncond_dev = np.zeros((HORIZON, 3))
    prev = last_i_gap
    for h in range(HORIZON):
        uncond_dev[h] = transition * prev
        prev = uncond_dev[h, 2]

    results = {"unconditional": (uncond_dev, np.zeros(HORIZON))}
    for key, spec in scenarios.items():
        values, shocks = conditional_path(
            transition, impact, last_i_gap, spec["controlled"], spec["targets"]
        )
        results[key] = (values, shocks)

    # ------------------------------------------------------------------ #
    # 3) Tidy forecast table (deviations + levels), combining both views. #
    # ------------------------------------------------------------------ #
    var_index = {"x": 0, "pi": 1, "i": 2}
    records: list[dict] = []
    for scenario, (values, shocks) in results.items():
        for h in range(HORIZON):
            for variable, idx in var_index.items():
                row = {
                    "horizon": h + 1,
                    "date": future[h],
                    "scenario": scenario,
                    "variable": variable,
                    "value_dev": values[h, idx],
                    "value_level": float(to_level(variable, values[h, idx])),
                    "implied_e_i_q": shocks[h] if variable == "i" else np.nan,
                }
                if scenario == "unconditional":
                    band = uncond[(uncond["horizon"] == h + 1) & (uncond["variable"] == variable)]
                    row["p05_level"] = float(band["inf_level"].iloc[0]) if len(band) else np.nan
                    row["p95_level"] = float(band["sup_level"].iloc[0]) if len(band) else np.nan
                records.append(row)
    table = pd.DataFrame(records)
    table["data_source"] = data_source
    table["mean_tpm_annual_pct"] = mean_tpm_annual
    table["mean_infl_annual_pct"] = mean_infl_annual
    table.to_csv(TABLES / "forecast.csv", index=False)
    table[table["horizon"].isin([1, 4, 8])].to_csv(TABLES / "forecast_summary.csv", index=False)

    # ------------------------------------------------------------------ #
    # Figure 1: history + unconditional Dynare fan chart (annual levels). #
    # ------------------------------------------------------------------ #
    history = macro.tail(16).copy()
    fig, axes = plt.subplots(3, 1, figsize=(11, 9))
    panels = (
        ("i", history["tpm_annual_pct"], "Policy rate TPM (% per year)"),
        ("pi", history["infl_annual_pct"], "Inflation (% per year)"),
        ("x", 100.0 * history["output_gap"], "Output gap (%)"),
    )
    for ax, (variable, hist_series, title) in zip(axes, panels):
        ax.plot(history["date"], hist_series, color="black", marker="o",
                markersize=3, label="Observed history")
        sub = uncond[uncond["variable"] == variable]
        ax.plot(sub["date"], sub["mean_level"], color="#1E4E79", linewidth=2.4,
                label="Dynare forecast mean")
        ax.fill_between(sub["date"], sub["inf_level"], sub["sup_level"],
                        color="#1E4E79", alpha=0.16, label="Dynare HPD band")
        if variable == "pi":
            ax.axhline(3.0, color="#B45309", linestyle="--", linewidth=1, label="3% target")
            ax.axhline(mean_infl_annual, color="#6B7280", linestyle=":", linewidth=1,
                       label=f"Sample mean ({mean_infl_annual:.1f}%)")
        elif variable == "i":
            ax.axhline(mean_tpm_annual, color="#6B7280", linestyle=":", linewidth=1,
                       label=f"Sample mean ({mean_tpm_annual:.1f}%)")
        else:
            ax.axhline(0.0, color="#6B7280", linewidth=0.7)
        ax.set_title(title)
        ax.grid(alpha=0.25)
        ax.tick_params(axis="x", rotation=75, labelsize=7)
        ax.legend(fontsize=7, ncol=2)
    fig.suptitle("Chile: unconditional forecast (Dynare estimation, forecast=8)")
    fig.text(0.01, 0.005,
             f"Source: {data_source}. Native Dynare forecast launched from the smoothed "
             "end-of-sample state. Mechanical model projection, not an official BCCh forecast.",
             fontsize=7)
    fig.tight_layout(rect=(0, 0.03, 1, 0.96))
    fig.savefig(FIGURES / "forecast_fanchart.png", dpi=180)
    plt.close(fig)

    # ------------------------------------------------------------------ #
    # Figure 2: conditional scenarios anchored to the current state.     #
    # ------------------------------------------------------------------ #
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8))
    keymap = (("i", "Policy rate TPM (% per year)"),
              ("pi", "Inflation (% per year)"),
              ("x", "Output gap (%)"))
    for ax, (variable, title) in zip(axes, keymap):
        idx = var_index[variable]
        htail = macro.tail(4)
        hist_series = {"i": htail["tpm_annual_pct"], "pi": htail["infl_annual_pct"],
                       "x": 100.0 * htail["output_gap"]}[variable]
        ax.plot(range(-3, 1), hist_series, color="black", marker="o", markersize=3,
                linewidth=1.2, label="History")
        for scenario, (values, _) in results.items():
            color = COLORS["unconditional" if scenario == "unconditional" else scenario]
            label = "Unconditional" if scenario == "unconditional" else scenarios[scenario]["label"]
            level = to_level(variable, values[:, idx])
            # splice: connect the last observed point to the forecast path
            xs = list(range(0, HORIZON + 1))
            ys = [float(hist_series.iloc[-1])] + list(level)
            ax.plot(xs, ys, color=color, linewidth=2, label=label,
                    linestyle="-" if scenario == "unconditional" else "-")
        if variable == "pi":
            ax.axhline(3.0, color="#B45309", linestyle="--", linewidth=1)
        elif variable == "i":
            ax.axhline(mean_tpm_annual, color="#6B7280", linestyle=":", linewidth=1)
        else:
            ax.axhline(0.0, color="#6B7280", linewidth=0.8)
        ax.axvline(0, color="#9CA3AF", linewidth=0.8)
        ax.set_title(title)
        ax.set_xlabel("Quarter (0 = last data)")
        ax.grid(alpha=0.25)
    axes[0].legend(fontsize=7)
    fig.suptitle("Conditional scenarios (anchored at the current state; e_i solves each path)")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIGURES / "conditional_scenarios.png", dpi=180)
    plt.close(fig)

    # ------------------------------------------------------------------ #
    # Figure 3: monetary-policy innovations e_i required by each path.   #
    # ------------------------------------------------------------------ #
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    for scenario in ("hold", "hike", "pi_target"):
        _, shocks = results[scenario]
        ax.plot(np.arange(1, HORIZON + 1), 100.0 * shocks, marker="o", linewidth=2,
                color=COLORS[scenario], label=scenarios[scenario]["label"])
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set(title="Monetary-policy innovations e_i required by each conditional path",
           xlabel="Forecast quarter", ylabel="e_i (quarterly percentage points)")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURES / "conditional_policy_shocks.png", dpi=180)
    plt.close(fig)

    print(f"Sample-mean TPM {mean_tpm_annual:.2f}% | mean inflation {mean_infl_annual:.2f}% "
          f"| 3% target as gap {pi_target_dev:+.5f}")
    print(f"Initial state: last policy-rate gap {100*last_i_gap:+.3f} quarterly pp")
    print(table[table["horizon"].isin([1, 4, 8])
                & table["variable"].isin(["pi", "i", "x"])].to_string(index=False))
    print("Wrote forecast tables and three figures (fan chart, scenarios, policy shocks).")


if __name__ == "__main__":
    main()
