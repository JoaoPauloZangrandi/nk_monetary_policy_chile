"""Collect Dynare CSV exports and create explicit synthetic fallbacks."""

from __future__ import annotations

import math
import pandas as pd

from common import (
    DYNARE_OUTPUTS,
    TABLES,
    calibration_rho,
    complete_parameters,
    ensure_directories,
    fallback_irfs,
    fallback_moments,
)

VARIABLES = ("x", "pi", "i")
SHOCKS = ("e_x", "e_pi", "e_i")


def read_dynare_fevd(scenario: str) -> pd.DataFrame | None:
    path = DYNARE_OUTPUTS / scenario / "fevd.csv"
    if not path.exists():
        return None
    wide = pd.read_csv(path)
    records = []
    for _, row in wide.iterrows():
        values = [float(row[shock]) for shock in SHOCKS]
        scale = 100.0 if sum(values) > 1.5 else 1.0
        for shock, value in zip(SHOCKS, values):
            records.append(
                {
                    "scenario": scenario,
                    "variable": row["variable"],
                    "shock": shock,
                    "variance_share": value / scale,
                    "source": "dynare",
                }
            )
    return pd.DataFrame(records)


def dynare_irfs(scenario: str, path) -> pd.DataFrame:
    wide = pd.read_csv(path)
    records = []
    for variable in VARIABLES:
        for shock in SHOCKS:
            column = f"{variable}_{shock}"
            if column not in wide:
                continue
            for horizon, response in zip(wide["horizon"], wide[column]):
                records.append(
                    {
                        "scenario": scenario,
                        "source": "dynare",
                        "variable": variable,
                        "shock": shock,
                        "horizon": int(horizon),
                        "response": float(response),
                    }
                )
    return pd.DataFrame(records)


def manifest_with_baseline() -> pd.DataFrame:
    path = TABLES / "scenario_manifest.csv"
    manifest = pd.read_csv(path) if path.exists() else pd.DataFrame()
    baseline = {"scenario": "baseline", "scenario_type": "baseline"}
    baseline.update(complete_parameters({"rho_i": calibration_rho()}))
    return pd.concat([pd.DataFrame([baseline]), manifest], ignore_index=True)


def row_parameters(row: pd.Series) -> dict:
    keys = (
        "rstar_annual",
        "sigma",
        "kappa",
        "rho_i",
        "phi_pi",
        "phi_x",
        "rstar",
        "beta",
    )
    return {key: float(row[key]) for key in keys if key in row and pd.notna(row[key])}


def collect_irfs(manifest: pd.DataFrame) -> pd.DataFrame:
    pieces = []
    for _, row in manifest.iterrows():
        scenario = str(row["scenario"])
        irf_path = DYNARE_OUTPUTS / scenario / "irfs.csv"
        if irf_path.exists():
            try:
                frame = dynare_irfs(scenario, irf_path)
                if not frame.empty:
                    pieces.append(frame)
                    continue
            except Exception as exc:
                print(f"Warning: could not parse {irf_path}: {exc}")
        params = complete_parameters(row_parameters(row))
        pieces.append(fallback_irfs(params, scenario))
    result = pd.concat(pieces, ignore_index=True)
    result.to_csv(TABLES / "irfs_long.csv", index=False)
    return result


def collect_moments(manifest: pd.DataFrame) -> None:
    frames = []
    for _, row in manifest.iterrows():
        scenario = str(row["scenario"])
        path = DYNARE_OUTPUTS / scenario / "moments.csv"
        if path.exists():
            moment = pd.read_csv(path)
            moment.insert(0, "scenario", scenario)
            moment["source"] = "dynare"
            frames.append(moment)
        else:
            params = complete_parameters(row_parameters(row))
            moment = fallback_moments(params)
            moment.insert(0, "scenario", scenario)
            frames.append(moment)
    if not frames:
        baseline = manifest.loc[manifest["scenario"] == "baseline"].iloc[0]
        moment = fallback_moments(complete_parameters(row_parameters(baseline)))
        moment.insert(0, "scenario", "baseline")
        frames.append(moment)
    moments_all = pd.concat(frames, ignore_index=True)
    moments_all.to_csv(TABLES / "moments_all_scenarios.csv", index=False)
    moments_all[moments_all["scenario"] == "baseline"].to_csv(
        TABLES / "moments.csv", index=False
    )


def collect_fevd(irfs: pd.DataFrame, manifest: pd.DataFrame) -> None:
    frames = []
    for scenario in manifest["scenario"].astype(str):
        frame = read_dynare_fevd(scenario)
        if frame is not None:
            frames.append(frame)
            continue
        selected = irfs[irfs["scenario"] == scenario].copy()
        selected["squared_response"] = selected["response"] ** 2
        totals = (
            selected.groupby(["variable", "shock"], as_index=False)["squared_response"]
            .sum()
            .rename(columns={"squared_response": "shock_contribution"})
        )
        totals["variance_share"] = totals["shock_contribution"] / totals.groupby(
            "variable"
        )["shock_contribution"].transform("sum")
        totals["scenario"] = scenario
        totals["source"] = "synthetic_irf_share_fallback"
        frames.append(
            totals[["scenario", "variable", "shock", "variance_share", "source"]]
        )
    fevd_all = pd.concat(frames, ignore_index=True)
    fevd_all.to_csv(TABLES / "fevd_all_scenarios.csv", index=False)
    fevd_all[fevd_all["scenario"] == "baseline"].to_csv(
        TABLES / "fevd_summary.csv", index=False
    )

def collect_determinacy(manifest: pd.DataFrame) -> None:
    rows = []
    for _, scenario_row in manifest.iterrows():
        scenario = str(scenario_row["scenario"])
        stability_path = DYNARE_OUTPUTS / scenario / "stability.csv"
        if stability_path.exists():
            row = pd.read_csv(stability_path).iloc[0].to_dict()
            row["source"] = "dynare_check"
        else:
            row = {
                "scenario": scenario,
                "status": "not_run_or_failed",
                "n_forward": None,
                "n_unstable": None,
                "n_eigenvalues": None,
                "source": "no_dynare_diagnostic",
            }
        eigen_path = DYNARE_OUTPUTS / scenario / "eigenvalues.csv"
        if eigen_path.exists():
            eigenvalues = pd.read_csv(eigen_path)
            stable = eigenvalues[eigenvalues["modulus"] < 1.0]["modulus"]
            unstable = eigenvalues[eigenvalues["modulus"] > 1.0]["modulus"]
            dominant = float(stable.max()) if not stable.empty else math.nan
            row["dominant_stable_modulus"] = dominant
            row["convergence_half_life_quarters"] = (
                math.log(0.5) / math.log(dominant)
                if 0.0 < dominant < 1.0
                else math.nan
            )
            row["smallest_unstable_modulus"] = (
                float(unstable.min()) if not unstable.empty else math.nan
            )
        else:
            row["dominant_stable_modulus"] = math.nan
            row["convergence_half_life_quarters"] = math.nan
            row["smallest_unstable_modulus"] = math.nan
        row["scenario_type"] = scenario_row.get("scenario_type", "")
        row["phi_pi"] = scenario_row.get("phi_pi", None)
        rows.append(row)
    pd.DataFrame(rows).to_csv(TABLES / "scenario_determinacy.csv", index=False)


def main() -> None:
    ensure_directories()
    manifest = manifest_with_baseline()
    irfs = collect_irfs(manifest)
    collect_moments(manifest)
    collect_fevd(irfs, manifest)
    collect_determinacy(manifest)
    print(f"Collected outputs in {TABLES}")
    print(irfs.groupby("source")["scenario"].nunique().to_string())


if __name__ == "__main__":
    main()
