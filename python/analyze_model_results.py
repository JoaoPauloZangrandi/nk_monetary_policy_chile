"""Build diagnostic tables that connect model outputs to the assignment.

The script compares theoretical and empirical moments, summarizes IRF impact and
convergence metrics, and checks the expected impact signs of the three structural
shocks. It also creates a model-versus-data moments figure.
"""

from __future__ import annotations

import json
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import (
    DATA_CLEAN,
    DYNARE_OUTPUTS,
    FIGURES,
    SHOCK_STD,
    TABLES,
    _state_coefficients,
    calibration_rho,
    complete_parameters,
    ensure_directories,
)

VARIABLES = ("x", "pi", "i")
LABELS = {"x": "Output gap", "pi": "Inflation", "i": "Policy rate"}


def acf1(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    return float(clean.autocorr(lag=1)) if len(clean) > 2 else math.nan


def empirical_moment_rows(panel: pd.DataFrame, sample: str) -> list[dict]:
    series = {
        "x": panel["output_gap"],
        "pi": panel["infl_q"],
        "i": panel["i_q"],
    }
    rows = []
    for variable, values in series.items():
        clean = pd.to_numeric(values, errors="coerce").dropna()
        rows.append(
            {
                "source": "BCCh data",
                "sample": sample,
                "variable": variable,
                "mean_pp_quarterly": 100.0 * float(clean.mean()),
                "std_dev_pp_quarterly": 100.0 * float(clean.std(ddof=1)),
                "variance": float(clean.var(ddof=1)),
                "autocorrelation_1": acf1(clean),
                "observations": int(len(clean)),
            }
        )
    return rows


def model_moment_rows(moments: pd.DataFrame, scenario: str, sample: str) -> list[dict]:
    selected = moments[moments["scenario"] == scenario]
    rows = []
    for _, row in selected.iterrows():
        variable = str(row["variable"])
        model_mean = float(row["mean"])
        if variable == "i":
            # Dynare reports the level r*; comparisons focus on cyclical deviations.
            model_mean = 0.0
        rows.append(
            {
                "source": "Dynare model",
                "sample": sample,
                "variable": variable,
                "mean_pp_quarterly": 100.0 * model_mean,
                "std_dev_pp_quarterly": 100.0 * float(row["std_dev"]),
                "variance": float(row["variance"]),
                "autocorrelation_1": float(row["autocorrelation_1"]),
                "observations": np.nan,
            }
        )
    return rows


def build_moment_comparison() -> pd.DataFrame:
    panel = pd.read_csv(DATA_CLEAN / "chile_macro_quarterly.csv")
    moments = pd.read_csv(TABLES / "moments_all_scenarios.csv")
    dates = panel["date"].astype(str)
    pandemic = dates.between("2020Q2", "2021Q4")

    rows = empirical_moment_rows(panel, "2001Q1-2026Q1")
    rows += empirical_moment_rows(
        panel.loc[~pandemic].reset_index(drop=True),
        "excluding 2020Q2-2021Q4",
    )
    rows += model_moment_rows(moments, "baseline", "rho_i estimated (0.934)")
    rows += model_moment_rows(
        moments,
        "rho_calibrated_0p80",
        "rho_i calibrated (0.80)",
    )
    table = pd.DataFrame(rows)
    table.to_csv(TABLES / "moments_model_vs_data.csv", index=False)
    return table


def plot_moments(table: pd.DataFrame) -> None:
    order = [
        "2001Q1-2026Q1",
        "excluding 2020Q2-2021Q4",
        "rho_i estimated (0.934)",
        "rho_i calibrated (0.80)",
    ]
    colors = ["#111827", "#6B7280", "#1E4E79", "#FF6B35"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    width = 0.19
    positions = np.arange(len(VARIABLES))
    for index, (sample, color) in enumerate(zip(order, colors)):
        selected = table[table["sample"] == sample].set_index("variable")
        offset = (index - 1.5) * width
        axes[0].bar(
            positions + offset,
            selected.loc[list(VARIABLES), "std_dev_pp_quarterly"],
            width=width,
            label=sample,
            color=color,
        )
        axes[1].bar(
            positions + offset,
            selected.loc[list(VARIABLES), "autocorrelation_1"],
            width=width,
            label=sample,
            color=color,
        )
    axes[0].set_title("Quarterly standard deviations")
    axes[0].set_ylabel("Percentage points")
    axes[1].set_title("First-order autocorrelation")
    axes[1].axhline(0, color="black", linewidth=0.7)
    for ax in axes:
        ax.set_xticks(positions, [LABELS[var] for var in VARIABLES])
        ax.grid(axis="y", alpha=0.25)
    axes[0].legend(fontsize=8)
    fig.suptitle("Chile: theoretical moments versus empirical moments")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(FIGURES / "moments_model_vs_data.png", dpi=180)
    plt.close(fig)


def first_sign_change(frame: pd.DataFrame) -> float:
    ordered = frame.sort_values("horizon")
    initial = float(ordered.iloc[0]["response"])
    if abs(initial) < 1e-14:
        return math.nan
    initial_sign = np.sign(initial)
    changed = ordered[
        (np.sign(ordered["response"]) != initial_sign)
        & (ordered["response"].abs() > 1e-12)
    ]
    return float(changed.iloc[0]["horizon"]) if not changed.empty else math.nan


def build_irf_metrics() -> pd.DataFrame:
    irfs = pd.read_csv(TABLES / "irfs_long.csv")
    manifest = pd.read_csv(TABLES / "scenario_manifest.csv")
    types = dict(zip(manifest["scenario"], manifest["scenario_type"]))
    types["baseline"] = "baseline"
    rows = []
    for (scenario, variable, shock), frame in irfs.groupby(
        ["scenario", "variable", "shock"]
    ):
        ordered = frame.sort_values("horizon")
        peak_row = ordered.loc[ordered["response"].abs().idxmax()]
        by_horizon = ordered.set_index("horizon")["response"]
        rows.append(
            {
                "scenario": scenario,
                "scenario_type": types.get(scenario, ""),
                "variable": variable,
                "shock": shock,
                "impact_pp": 100.0 * float(ordered.iloc[0]["response"]),
                "peak_response_pp": 100.0 * float(peak_row["response"]),
                "peak_abs_pp": 100.0 * abs(float(peak_row["response"])),
                "peak_horizon": int(peak_row["horizon"]),
                "cumulative_abs_pp": 100.0 * float(ordered["response"].abs().sum()),
                "first_sign_change_horizon": first_sign_change(ordered),
                "response_h4_pp": 100.0 * float(by_horizon.get(4, np.nan)),
                "response_h8_pp": 100.0 * float(by_horizon.get(8, np.nan)),
                "response_h19_pp": 100.0 * float(by_horizon.get(19, np.nan)),
                "source": str(ordered.iloc[0]["source"]),
            }
        )
    table = pd.DataFrame(rows)
    table.to_csv(TABLES / "irf_summary_metrics.csv", index=False)
    return table


def build_sign_checks(metrics: pd.DataFrame) -> pd.DataFrame:
    expected = {
        ("e_x", "x"): 1,
        ("e_x", "pi"): 1,
        ("e_x", "i"): 1,
        ("e_pi", "x"): -1,
        ("e_pi", "pi"): 1,
        ("e_pi", "i"): 1,
        ("e_i", "x"): -1,
        ("e_i", "pi"): -1,
        ("e_i", "i"): 1,
    }
    baseline = metrics[metrics["scenario"] == "baseline"].copy()
    baseline["expected_impact_sign"] = baseline.apply(
        lambda row: expected[(row["shock"], row["variable"])], axis=1
    )
    baseline["observed_impact_sign"] = np.sign(baseline["impact_pp"]).astype(int)
    baseline["impact_sign_matches"] = (
        baseline["expected_impact_sign"] == baseline["observed_impact_sign"]
    )
    output = baseline[
        [
            "shock",
            "variable",
            "expected_impact_sign",
            "observed_impact_sign",
            "impact_sign_matches",
            "impact_pp",
            "first_sign_change_horizon",
        ]
    ]
    output.to_csv(TABLES / "irf_sign_checks.csv", index=False)
    return output


def build_policy_functions() -> pd.DataFrame:
    params = complete_parameters({"rho_i": calibration_rho()})
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
    impact = np.linalg.inv(structural)
    transition = np.array([a_x, a_pi, a_i])
    drivers = [
        ("constant", np.array([0.0, 0.0, params["rstar"]])),
        ("i(-1)", transition),
        ("e_x", impact[:, 0]),
        ("e_pi", impact[:, 1]),
        ("e_i", impact[:, 2]),
    ]
    rows = []
    for driver, coefficients in drivers:
        for variable, coefficient in zip(VARIABLES, coefficients):
            rows.append(
                {
                    "driver": driver,
                    "variable": variable,
                    "coefficient_unit_shock": float(coefficient),
                    "coefficient_calibrated_shock": (
                        float(coefficient) * SHOCK_STD[driver]
                        if driver in SHOCK_STD
                        else float(coefficient)
                    ),
                }
            )
    table = pd.DataFrame(rows)
    table.to_csv(TABLES / "policy_transition_coefficients.csv", index=False)
    return table


def build_correlation_comparison() -> pd.DataFrame:
    panel = pd.read_csv(DATA_CLEAN / "chile_macro_quarterly.csv")
    empirical = pd.DataFrame(
        {
            "x": panel["output_gap"],
            "pi": panel["infl_q"],
            "i": panel["i_q"],
        }
    ).corr()
    rows = []
    for variable in VARIABLES:
        for other in VARIABLES:
            rows.append(
                {
                    "source": "BCCh data",
                    "variable": variable,
                    "other_variable": other,
                    "correlation": float(empirical.loc[variable, other]),
                }
            )
    model_path = DYNARE_OUTPUTS / "baseline" / "correlations.csv"
    if model_path.exists():
        model = pd.read_csv(model_path).set_index("variable")
        for variable in VARIABLES:
            for other in VARIABLES:
                rows.append(
                    {
                        "source": "Dynare baseline",
                        "variable": variable,
                        "other_variable": other,
                        "correlation": float(model.loc[variable, other]),
                    }
                )
    table = pd.DataFrame(rows)
    table.to_csv(TABLES / "correlations_model_vs_data.csv", index=False)
    return table


def main() -> None:
    ensure_directories()
    metadata = json.loads(
        (DATA_CLEAN / "dataset_metadata.json").read_text(encoding="utf-8")
    )
    if bool(metadata.get("is_synthetic", True)):
        print("WARNING: empirical moment rows use the labelled synthetic fallback.")
    moment_table = build_moment_comparison()
    plot_moments(moment_table)
    metrics = build_irf_metrics()
    signs = build_sign_checks(metrics)
    policy = build_policy_functions()
    correlations = build_correlation_comparison()
    print(f"Moment comparison rows: {len(moment_table)}")
    print(f"IRF metric rows: {len(metrics)}")
    print(f"Policy-function rows: {len(policy)}")
    print(f"Correlation rows: {len(correlations)}")
    print(
        "Baseline impact sign checks: "
        f"{int(signs['impact_sign_matches'].sum())}/{len(signs)}"
    )


if __name__ == "__main__":
    main()
