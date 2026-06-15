"""Build the open-economy extension dataset for Chile.

Public monthly series are downloaded as CSV from FRED:
  - CCUSMA02CLM618N: CLP per USD, source OECD Main Economic Indicators.
  - PCOPPUSDM: global copper price, source IMF Primary Commodity Prices.

The raw/clean CSV is kept local by .gitignore. Public outputs contain only
derived summary statistics, calibration targets, metadata and a figure.
"""

from __future__ import annotations

import datetime as dt
import json
import urllib.request
from io import BytesIO

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.filters.hp_filter import hpfilter

from common import DATA_CLEAN, FIGURES, TABLES, ensure_directories


SERIES = {
    "exchange_rate_clp_per_usd": "CCUSMA02CLM618N",
    "copper_usd_per_metric_ton": "PCOPPUSDM",
}
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"


def download_fred(series_id: str) -> pd.Series:
    request = urllib.request.Request(
        FRED_CSV.format(series_id=series_id),
        headers={"User-Agent": "nk-monetary-policy-chile/1.0"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = response.read()
    frame = pd.read_csv(BytesIO(payload))
    frame.columns = ["date", "value"]
    frame["date"] = pd.to_datetime(frame["date"])
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    return frame.dropna().set_index("date")["value"].sort_index()


def ar1(series: pd.Series) -> tuple[float, float]:
    y = series.iloc[1:].to_numpy()
    x = sm.add_constant(series.iloc[:-1].to_numpy())
    result = sm.OLS(y, x).fit()
    residual_std = float(np.std(result.resid, ddof=2))
    return float(result.params[1]), residual_std


def main() -> None:
    ensure_directories()
    fx_monthly = download_fred(SERIES["exchange_rate_clp_per_usd"])
    copper_monthly = download_fred(SERIES["copper_usd_per_metric_ton"])

    fx_q = fx_monthly.groupby(fx_monthly.index.to_period("Q")).mean()
    copper_q = copper_monthly.groupby(copper_monthly.index.to_period("Q")).mean()
    open_panel = pd.DataFrame({"fx_clp_usd": fx_q, "copper_usd_ton": copper_q})
    macro = pd.read_csv(DATA_CLEAN / "chile_macro_quarterly.csv")
    macro.index = pd.PeriodIndex(macro["date"], freq="Q")
    open_panel = open_panel.join(
        macro[["output_gap", "infl_q", "i_q", "tpm_annual_pct"]],
        how="inner",
    ).dropna()

    open_panel["log_fx"] = np.log(open_panel["fx_clp_usd"])
    open_panel["log_copper"] = np.log(open_panel["copper_usd_ton"])
    fx_cycle, fx_trend = hpfilter(open_panel["log_fx"], lamb=1600)
    copper_cycle, copper_trend = hpfilter(open_panel["log_copper"], lamb=1600)
    open_panel["fx_gap"] = fx_cycle
    open_panel["fx_trend"] = fx_trend
    open_panel["copper_gap"] = copper_cycle
    open_panel["copper_trend"] = copper_trend
    open_panel["fx_depreciation_q"] = open_panel["log_fx"].diff()

    rho_copper, std_copper = ar1(open_panel["copper_gap"])
    rho_fx, std_fx_gap = ar1(open_panel["fx_gap"])
    std_fx_depreciation = float(open_panel["fx_depreciation_q"].dropna().std(ddof=1))

    calibration = pd.DataFrame(
        [
            {
                "rho_copper": float(np.clip(rho_copper, 0.20, 0.95)),
                "rho_fx_gap_descriptive": rho_fx,
                "std_e_copper": float(np.clip(std_copper, 0.01, 0.12)),
                "std_e_fx": float(np.clip(std_fx_gap, 0.01, 0.10)),
                "std_fx_depreciation_q": std_fx_depreciation,
                "alpha_q_is": 0.05,
                "alpha_copper_is": 0.03,
                "gamma_q_phillips": 0.03,
                "eta_i_uip": 1.0,
                "phi_q_taylor": 0.05,
                "calibration_scope": "illustrative open-economy extension",
            }
        ]
    )
    calibration.to_csv(TABLES / "open_economy_calibration.csv", index=False)

    summary_rows = []
    for column in [
        "fx_clp_usd",
        "copper_usd_ton",
        "fx_gap",
        "copper_gap",
        "fx_depreciation_q",
    ]:
        values = open_panel[column].dropna()
        summary_rows.append(
            {
                "series": column,
                "observations": len(values),
                "mean": float(values.mean()),
                "std_dev": float(values.std(ddof=1)),
                "minimum": float(values.min()),
                "maximum": float(values.max()),
                "sample_start": str(values.index[0]),
                "sample_end": str(values.index[-1]),
            }
        )
    pd.DataFrame(summary_rows).to_csv(
        TABLES / "open_economy_data_summary.csv", index=False
    )

    clean = open_panel.reset_index(names="date")
    clean["date"] = clean["date"].astype(str)
    clean.to_csv(DATA_CLEAN / "chile_open_economy.csv", index=False)
    metadata = {
        "access_date": dt.date.today().isoformat(),
        "is_synthetic": False,
        "frequency": "quarterly averages built from monthly series",
        "series": {
            "exchange_rate": {
                "id": SERIES["exchange_rate_clp_per_usd"],
                "title": "CLP per USD, average daily rate",
                "source": "OECD Main Economic Indicators via FRED",
                "url": "https://fred.stlouisfed.org/series/CCUSMA02CLM618N",
            },
            "copper": {
                "id": SERIES["copper_usd_per_metric_ton"],
                "title": "Global price of copper, USD per metric ton",
                "source": "IMF Primary Commodity Prices via FRED",
                "url": "https://fred.stlouisfed.org/series/PCOPPUSDM",
            },
        },
        "transformations": (
            "Monthly levels to quarterly averages; natural logs; HP-filter cycles "
            "with lambda=1600. Calibration uses AR(1) persistence and innovation std."
        ),
        "warning": (
            "Open-economy parameters are illustrative and are not jointly estimated "
            "structural coefficients."
        ),
    }
    (DATA_CLEAN / "open_economy_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    x = np.arange(len(open_panel))
    ticks = np.arange(0, len(open_panel), 8)
    labels = [str(open_panel.index[index]) for index in ticks]
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), sharex=True)
    axes[0, 0].plot(x, open_panel["fx_clp_usd"], color="#1E4E79")
    axes[0, 0].set_title("Cambio nominal: pesos chilenos por US$ 1")
    axes[0, 0].set_ylabel("CLP/USD")
    axes[0, 1].plot(x, open_panel["copper_usd_ton"], color="#B45309")
    axes[0, 1].set_title("Preco global do cobre")
    axes[0, 1].set_ylabel("US$/tonelada")
    axes[1, 0].plot(x, 100 * open_panel["fx_gap"], color="#1E4E79")
    axes[1, 0].axhline(0, color="black", linewidth=0.7)
    axes[1, 0].set_title("Gap cambial HP (alta = peso depreciado)")
    axes[1, 0].set_ylabel("% log")
    axes[1, 1].plot(x, 100 * open_panel["copper_gap"], color="#B45309")
    axes[1, 1].axhline(0, color="black", linewidth=0.7)
    axes[1, 1].set_title("Gap do preco do cobre HP")
    axes[1, 1].set_ylabel("% log")
    for ax in axes.ravel():
        ax.grid(alpha=0.25)
        ax.set_xticks(ticks)
        ax.set_xticklabels(labels, rotation=70, fontsize=8)
    fig.suptitle("Chile como economia pequena e aberta: cambio e cobre")
    fig.text(
        0.01,
        0.01,
        "Fontes: OECD (cambio) e FMI (cobre), distribuidas pelo FRED. "
        "Gaps HP sao proxies ciclicas, nao valores de equilibrio observados.",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    fig.savefig(FIGURES / "open_economy_data.png", dpi=180)
    plt.close(fig)
    print(calibration.to_string(index=False))
    print(f"Wrote open-economy data for {len(open_panel)} quarters.")


if __name__ == "__main__":
    main()
