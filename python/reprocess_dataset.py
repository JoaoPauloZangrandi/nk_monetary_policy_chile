"""Re-derive the output gap (Kalman, not HP) and the model observables from the
cached BCCh panel, WITHOUT re-hitting the BCCh API.

Two methodological changes requested:
  * the output gap is an Unobserved-Components (Kalman) cycle, replacing the HP filter;
  * the inflation observable is centred on the 3% TARGET (not the sample mean), so the
    model's steady state is the target and forecasts converge to 3% by construction.

The rate stays demeaned by its sample mean (= realised neutral; Fisher-implied r*).
build_chile_dataset.py carries the same logic for a fresh pull, but it needs BCCh
credentials; this script works from the committed cache (data/clean/*.csv).
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from common import DATA_CLEAN, ensure_directories, kalman_gap

INFLATION_TARGET_ANNUAL = 0.03


def main() -> None:
    ensure_directories()
    panel = pd.read_csv(DATA_CLEAN / "chile_macro_quarterly.csv")

    # --- Output gap by Kalman (Unobserved Components) instead of HP ---
    cycle, trend = kalman_gap(panel["log_pib"].to_numpy())
    panel["output_gap_hp"] = panel["output_gap"]  # keep HP for reference
    panel["output_gap"] = cycle
    panel["pib_trend_kalman"] = trend
    panel.to_csv(DATA_CLEAN / "chile_macro_quarterly.csv", index=False)

    # --- Observables: inflation centred on the 3% target ---
    target_q = (1.0 + INFLATION_TARGET_ANNUAL) ** 0.25 - 1.0
    observables = pd.DataFrame(
        {
            "date": panel["date"],
            "pi": (panel["infl_q"] - target_q).to_numpy(),
            "i": (panel["i_q"] - panel["i_q"].mean()).to_numpy(),
            "x": (panel["output_gap"] - panel["output_gap"].mean()).to_numpy(),
        }
    )
    observables.to_csv(DATA_CLEAN / "chile_observables.csv", index=False)

    # --- Provenance ---
    meta_path = DATA_CLEAN / "dataset_metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["output_gap_method"] = (
        "Unobserved-Components Kalman smoother (smooth I(2) trend + AR(2) cycle), "
        "replacing the HP filter; COVID stays in the cycle"
    )
    meta["inflation_centering"] = (
        "observable pi = quarterly inflation minus the 3% annual target "
        "(steady state = target; model forecasts converge to 3% by construction)"
    )
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    mean_infl_annual = ((1.0 + panel["infl_q"].mean()) ** 4 - 1.0) * 100.0
    covid = float(cycle[panel["date"].to_numpy() == "2020Q2"][0]) * 100.0
    print(f"Kalman output gap: std {cycle.std()*100:.2f}% | COVID 2020Q2 "
          f"{covid:.1f}% | last {cycle[-1]*100:.2f}%")
    print(f"Inflation centred on 3% target (sample mean was {mean_infl_annual:.2f}%); "
          f"pi observable mean now {observables['pi'].mean()*400:.2f} annual p.p. above target")
    print("Wrote chile_macro_quarterly.csv, chile_observables.csv, dataset_metadata.json")


if __name__ == "__main__":
    main()
