"""Collect Dynare CSV exports and create explicit synthetic fallbacks."""

from __future__ import annotations

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
    for scenario in ("baseline",):
        path = DYNARE_OUTPUTS / scenario / "moments.csv"
        if path.exists():
            moment = pd.read_csv(path)
            moment.insert(0, "scenario", scenario)
            moment["source"] = "dynare"
            frames.append(moment)
    if frames:
        moments = pd.concat(frames, ignore_index=True)
    else:
        baseline = manifest.loc[manifest["scenario"] == "baseline"].iloc[0]
        moments = fallback_moments(complete_parameters(row_parameters(baseline)))
        moments.insert(0, "scenario", "baseline")
    moments.to_csv(TABLES / "moments.csv", index=False)


def collect_fevd(irfs: pd.DataFrame) -> None:
    frames = [
        frame
        for scenario in ("baseline",)
        if (frame := read_dynare_fevd(scenario)) is not None
    ]
    if frames:
        fevd = pd.concat(frames, ignore_index=True)
    else:
        baseline = irfs[irfs["scenario"] == "baseline"].copy()
        baseline["squared_response"] = baseline["response"] ** 2
        totals = (
            baseline.groupby(["variable", "shock"], as_index=False)["squared_response"]
            .sum()
            .rename(columns={"squared_response": "shock_contribution"})
        )
        totals["variance_share"] = totals["shock_contribution"] / totals.groupby(
            "variable"
        )["shock_contribution"].transform("sum")
        totals["scenario"] = "baseline"
        totals["source"] = "synthetic_irf_share_fallback"
        fevd = totals[["scenario", "variable", "shock", "variance_share", "source"]]
    fevd.to_csv(TABLES / "fevd_summary.csv", index=False)

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
        row["scenario_type"] = scenario_row.get("scenario_type", "")
        row["phi_pi"] = scenario_row.get("phi_pi", None)
        rows.append(row)
    pd.DataFrame(rows).to_csv(TABLES / "scenario_determinacy.csv", index=False)


def main() -> None:
    ensure_directories()
    manifest = manifest_with_baseline()
    irfs = collect_irfs(manifest)
    collect_moments(manifest)
    collect_fevd(irfs)
    collect_determinacy(manifest)
    print(f"Collected outputs in {TABLES}")
    print(irfs.groupby("source")["scenario"].nunique().to_string())


if __name__ == "__main__":
    main()
