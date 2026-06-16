"""Build the real Chilean quarterly dataset from the Banco Central de Chile (BCCh).

Source: BCCh "Base de Datos Estadisticos" REST web service (SieteRestWS).
Series actually downloaded (confirmed available):
  - TPM  (monetary policy rate, daily, % p.a.):      F022.TPM.TIN.D001.NO.Z.D
  - IPC  (CPI monthly variation, %):                 F074.IPC.VAR.Z.Z.C.M
  - PIB  (real GDP, chained vol., seasonally adj.,
          spliced, reference 2018, quarterly):       F032.PIB.FLU.R.CLP.EP18.Z.Z.1.T

Credentials are read from the environment variables BCCH_USER / BCCH_PASS, or from a
local, git-ignored file data/raw/bcch_credentials.json with {"user": ..., "pass": ...}.
Credentials are never written to data/clean or printed.

If credentials are missing or the download fails, the script falls back to a clearly
labelled SYNTHETIC AR(1) series (for pipeline testing only) and flags is_synthetic=True.

Outputs (all in data/clean):
  - chile_policy_rate.csv      quarterly policy rate (% p.a.) for the AR(1) of rho_i
  - chile_macro_quarterly.csv  full quarterly panel (rate, inflation, gdp, gap, real rate)
  - chile_observables.csv      model-unit deviations (pi, i, x) for Dynare estimation
  - dataset_metadata.json      provenance (institution, series ids, units, dates, transforms)
"""

from __future__ import annotations

import json
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

from common import DATA_CLEAN, DATA_RAW, ensure_directories, kalman_gap

BCCH_BASE = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"
SERIES = {
    "tpm": "F022.TPM.TIN.D001.NO.Z.D",
    "ipc_var": "F074.IPC.VAR.Z.Z.C.M",
    "pib": "F032.PIB.FLU.R.CLP.EP18.Z.Z.1.T",
}
START_DATE = "2001-01-01"
INFLATION_TARGET_ANNUAL = 0.03  # Meta de inflacion del BCCh: 3% anual.
HP_LAMBDA = 1600  # Convencion trimestral.


# --------------------------------------------------------------------------- #
# Credentials and HTTP access
# --------------------------------------------------------------------------- #
def get_credentials() -> tuple[str, str] | None:
    import os

    user = os.environ.get("BCCH_USER")
    password = os.environ.get("BCCH_PASS")
    if user and password:
        return user, password
    creds_file = DATA_RAW / "bcch_credentials.json"
    if creds_file.exists():
        try:
            payload = json.loads(creds_file.read_text(encoding="utf-8"))
            user = payload.get("user")
            password = payload.get("pass") or payload.get("password")
            if user and password:
                return str(user), str(password)
        except Exception as exc:  # noqa: BLE001
            print(f"Warning: could not read bcch_credentials.json: {exc}")
    return None


def fetch_series(series_id: str, user: str, password: str,
                 first: str = START_DATE, last: str | None = None) -> pd.Series:
    """Download one BCCh series and return a float Series indexed by date."""
    import urllib.parse
    import urllib.request

    if last is None:
        last = dt.date.today().isoformat()
    query = urllib.parse.urlencode(
        {
            "user": user,
            "pass": password,
            "function": "GetSeries",
            "timeseries": series_id,
            "firstdate": first,
            "lastdate": last,
        }
    )
    url = f"{BCCH_BASE}?{query}"
    with urllib.request.urlopen(url, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8", "replace"))
    if payload.get("Codigo") != 0:
        raise RuntimeError(
            f"BCCh error for {series_id}: {payload.get('Descripcion')}"
        )
    series_block = payload.get("Series") or {}
    observations = series_block.get("Obs") or []
    dates, values = [], []
    for obs in observations:
        if str(obs.get("statusCode", "")).upper() not in ("OK", ""):
            continue
        raw_value = str(obs.get("value", "")).replace(",", ".").strip()
        if raw_value in ("", "NaN", "ND"):
            continue
        try:
            value = float(raw_value)
        except ValueError:
            continue
        dates.append(pd.to_datetime(obs["indexDateString"], format="%d-%m-%Y"))
        values.append(value)
    if not dates:
        raise RuntimeError(f"BCCh returned no usable observations for {series_id}.")
    return pd.Series(values, index=pd.DatetimeIndex(dates), name=series_id).sort_index()


# --------------------------------------------------------------------------- #
# Real dataset assembly
# --------------------------------------------------------------------------- #
def build_real_panel(user: str, password: str) -> tuple[pd.DataFrame, dict]:
    tpm_daily = fetch_series(SERIES["tpm"], user, password)
    ipc_var_m = fetch_series(SERIES["ipc_var"], user, password)
    pib_q = fetch_series(SERIES["pib"], user, password)

    # Policy rate: quarterly mean of the daily TPM (annual %).
    tpm_q = tpm_daily.groupby(tpm_daily.index.to_period("Q")).mean()

    # Inflation: compound three monthly CPI variations into a quarterly fraction.
    ipc_frac = ipc_var_m / 100.0
    grouped = ipc_frac.groupby(ipc_frac.index.to_period("Q"))
    infl_q = grouped.apply(lambda s: float(np.prod(1.0 + s.to_numpy()) - 1.0))
    months_per_quarter = grouped.size()
    infl_q = infl_q[months_per_quarter == 3]  # keep only complete quarters

    # GDP: real, seasonally adjusted, quarterly -> log -> HP cycle (output gap).
    pib_q.index = pib_q.index.to_period("Q")
    pib_q = pib_q[~pib_q.index.duplicated(keep="last")].sort_index()

    panel = pd.DataFrame(
        {
            "tpm_annual_pct": tpm_q,
            "infl_q": infl_q,
            "pib_sa": pib_q,
        }
    ).dropna()
    if len(panel) < 20:
        raise RuntimeError(
            f"Only {len(panel)} overlapping quarters; expected a long sample."
        )

    panel["log_pib"] = np.log(panel["pib_sa"])
    cycle, trend = kalman_gap(panel["log_pib"].to_numpy())  # Kalman UC, not HP
    panel["pib_trend_kalman"] = trend
    panel["output_gap"] = cycle

    # Quarterly nominal rate as a fraction (model unit), Fisher-consistent.
    panel["i_q"] = (1.0 + panel["tpm_annual_pct"] / 100.0) ** 0.25 - 1.0
    panel["infl_annual_pct"] = ((1.0 + panel["infl_q"]) ** 4 - 1.0) * 100.0
    panel["real_rate_q"] = panel["i_q"] - panel["infl_q"]

    panel.index = panel.index.astype(str)
    panel.index.name = "date"

    metadata = {
        "institution": "Banco Central de Chile (BCCh)",
        "service": "Base de Datos Estadisticos - SieteRestWS REST API",
        "url_pattern": f"{BCCH_BASE}?function=GetSeries&timeseries=<ID>&firstdate=...&lastdate=...",
        "official_bde_url": "https://si3.bcentral.cl/Siete",
        "policy_framework_url": "https://www.bcentral.cl/web/banco-central/areas/politica-monetaria",
        "terms_of_use_url": "https://www.bcentral.cl/web/banco-central/condiciones-de-uso",
        "series_ids": SERIES,
        "frequency": "quarterly (built from daily TPM, monthly CPI, quarterly GDP)",
        "period": f"{panel.index[0]} to {panel.index[-1]}",
        "observations": int(len(panel)),
        "access_date": dt.date.today().isoformat(),
        "units": {
            "tpm_annual_pct": "TPM, percent per year (quarterly average of daily series)",
            "i_q": "nominal policy rate, quarterly fraction = (1+TPM/100)^(1/4)-1",
            "infl_q": "quarterly CPI inflation, fraction (compounded monthly variations)",
            "infl_annual_pct": "annualised quarterly inflation, percent",
            "pib_sa": "real GDP, chained volume, seasonally adjusted, ref 2018 (CLP bn)",
            "output_gap": "HP-filter cycle of log real GDP (lambda=1600), fraction",
            "real_rate_q": "ex-post real quarterly rate = i_q - infl_q",
        },
        "transformations": (
            "TPM: daily->quarterly mean. CPI: monthly % -> quarterly compounded fraction. "
            f"GDP: log + HP filter (lambda={HP_LAMBDA}) for the output gap."
        ),
        "inflation_target_annual": INFLATION_TARGET_ANNUAL,
        "is_synthetic": False,
        "note": "Real official data from BCCh; credentials are not stored in this file.",
    }
    return panel, metadata


def synthetic_panel() -> tuple[pd.DataFrame, dict]:
    """Clearly-labelled synthetic fallback for pipeline testing only."""
    rng = np.random.default_rng(20260614)
    periods = pd.period_range("2001Q3", "2026Q1", freq="Q")
    long_run = 4.5
    rho = 0.92
    tpm = np.empty(len(periods))
    tpm[0] = long_run
    for i in range(1, len(periods)):
        tpm[i] = max(0.25, long_run + rho * (tpm[i - 1] - long_run) + rng.normal(0, 0.5))
    infl_q = 0.0074 + 0.5 * (tpm / 100.0 / 4 - 0.0074) + rng.normal(0, 0.004, len(periods))
    gap = np.zeros(len(periods))
    for i in range(1, len(periods)):
        gap[i] = 0.7 * gap[i - 1] + rng.normal(0, 0.01)
    panel = pd.DataFrame(
        {
            "tpm_annual_pct": tpm,
            "infl_q": infl_q,
            "pib_sa": 100.0 * np.exp(np.cumsum(0.005 + gap * 0.0)),
            "output_gap": gap,
        },
        index=periods.astype(str),
    )
    panel.index.name = "date"
    panel["log_pib"] = np.log(panel["pib_sa"])
    panel["pib_trend_hp"] = panel["log_pib"]
    panel["i_q"] = (1.0 + panel["tpm_annual_pct"] / 100.0) ** 0.25 - 1.0
    panel["infl_annual_pct"] = ((1.0 + panel["infl_q"]) ** 4 - 1.0) * 100.0
    panel["real_rate_q"] = panel["i_q"] - panel["infl_q"]
    metadata = {
        "institution": "SYNTHETIC (no real data)",
        "is_synthetic": True,
        "source": "synthetic_ar1_pipeline_test_not_chilean_data",
        "access_date": dt.date.today().isoformat(),
        "note": "No BCCh credentials available; generated a labelled synthetic panel.",
    }
    return panel, metadata


# --------------------------------------------------------------------------- #
def main() -> None:
    ensure_directories()
    credentials = get_credentials()
    if credentials is not None:
        try:
            panel, metadata = build_real_panel(*credentials)
            print(f"Downloaded real BCCh data: {metadata['period']} "
                  f"({metadata['observations']} quarters).")
        except Exception as exc:  # noqa: BLE001
            print(f"WARNING: BCCh download failed ({exc}). Using synthetic fallback.")
            panel, metadata = synthetic_panel()
    else:
        print("WARNING: no BCCh credentials (set BCCH_USER/BCCH_PASS or "
              "data/raw/bcch_credentials.json). Using synthetic fallback.")
        panel, metadata = synthetic_panel()

    is_synth = bool(metadata.get("is_synthetic", False))
    source_label = (
        "synthetic_ar1_pipeline_test_not_chilean_data"
        if is_synth
        else f"BCCh:{SERIES['tpm']}"
    )

    # 1) Policy-rate file consumed by the AR(1) estimation.
    policy = pd.DataFrame(
        {
            "date": panel.index,
            "policy_rate": panel["tpm_annual_pct"].to_numpy(),
            "is_synthetic": is_synth,
            "data_source": source_label,
        }
    )
    policy.to_csv(DATA_CLEAN / "chile_policy_rate.csv", index=False)

    # 2) Full quarterly macro panel.
    macro_cols = [
        "tpm_annual_pct", "i_q", "infl_q", "infl_annual_pct",
        "pib_sa", "log_pib", "pib_trend_hp", "output_gap", "real_rate_q",
    ]
    panel.reset_index()[["date"] + macro_cols].to_csv(
        DATA_CLEAN / "chile_macro_quarterly.csv", index=False
    )

    # 3) Model-unit observables (deviations from steady state) for estimation.
    observables = pd.DataFrame(
        {
            "date": panel.index,
            "pi": (panel["infl_q"] - ((1.0 + INFLATION_TARGET_ANNUAL) ** 0.25 - 1.0)).to_numpy(),
            "i": (panel["i_q"] - panel["i_q"].mean()).to_numpy(),
            "x": (panel["output_gap"] - panel["output_gap"].mean()).to_numpy(),
        }
    )
    observables.to_csv(DATA_CLEAN / "chile_observables.csv", index=False)

    metadata["files"] = {
        "policy_rate": "chile_policy_rate.csv",
        "macro_panel": "chile_macro_quarterly.csv",
        "observables": "chile_observables.csv (deviations: pi, i, x)",
    }
    (DATA_CLEAN / "dataset_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Wrote chile_policy_rate.csv, chile_macro_quarterly.csv, "
          f"chile_observables.csv ({len(panel)} quarters). synthetic={is_synth}")


if __name__ == "__main__":
    main()
