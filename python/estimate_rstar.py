"""Light empirical anchor for the neutral real rate r* (Chile, real data).

The minimal NK model treats r* as a calibrated constant; the assignment asks for the
{2,3,4}% annual scenarios. Here we provide a data-based reference point so the scenario
grid can be judged against the realised ex-post real rate:

  * ex-post real quarterly rate r_t = i_q - infl_q (full IT sample and last 5 years);
  * HP-filter trend of r_t (end-of-sample value as a slow-moving r* proxy).

These are descriptive anchors (not a Laubach-Williams estimate); the report makes that
explicit. Output: outputs/tables/rstar_estimates.csv.
"""

from __future__ import annotations

import json
import numpy as np
import pandas as pd

from common import DATA_CLEAN, TABLES, ensure_directories


def annualise(q: float) -> float:
    return ((1.0 + q) ** 4 - 1.0) * 100.0


def main() -> None:
    ensure_directories()
    panel = pd.read_csv(DATA_CLEAN / "chile_macro_quarterly.csv")
    metadata = json.loads(
        (DATA_CLEAN / "dataset_metadata.json").read_text(encoding="utf-8")
    )
    is_synthetic = bool(metadata.get("is_synthetic", True))
    data_source = str(metadata.get("institution", metadata.get("source", "unknown")))
    real_q = panel["real_rate_q"].dropna().to_numpy()

    from statsmodels.tsa.filters.hp_filter import hpfilter

    cycle, trend = hpfilter(panel["real_rate_q"].dropna(), lamb=1600)

    rows = []
    full_mean = float(np.mean(real_q))
    rows.append(
        {
            "method": "ex_post_real_rate_mean_full_sample",
            "rstar_quarterly": full_mean,
            "rstar_annual_pct": annualise(full_mean),
            "beta_implied": 1.0 / (1.0 + full_mean),
            "observations": int(len(real_q)),
        }
    )
    last20 = real_q[-20:]
    last_mean = float(np.mean(last20))
    rows.append(
        {
            "method": "ex_post_real_rate_mean_last_5y",
            "rstar_quarterly": last_mean,
            "rstar_annual_pct": annualise(last_mean),
            "beta_implied": 1.0 / (1.0 + last_mean),
            "observations": int(len(last20)),
        }
    )
    trend_end = float(trend.iloc[-1])
    rows.append(
        {
            "method": "hp_trend_real_rate_end_of_sample",
            "rstar_quarterly": trend_end,
            "rstar_annual_pct": annualise(trend_end),
            "beta_implied": 1.0 / (1.0 + trend_end),
            "observations": int(len(real_q)),
        }
    )

    table = pd.DataFrame(rows)
    table["is_synthetic"] = is_synthetic
    table["data_source"] = data_source
    table.to_csv(TABLES / "rstar_estimates.csv", index=False)
    print(table.round(4).to_string(index=False))
    print(f"Wrote {TABLES / 'rstar_estimates.csv'}")


if __name__ == "__main__":
    main()
