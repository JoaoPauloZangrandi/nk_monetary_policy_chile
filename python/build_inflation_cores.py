"""Decompose Chilean CPI (IPC) inflation by core/sub-index, from public FRED data.

FRED OECD series (no credentials). The component indices are only published to
~2023 (energy/services/core) so the analysis covers the build-up and the 2021-23
surge but not the most recent disinflation -- stated honestly on the figure.

Produces:
  * data/clean/chile_inflation_cores.csv -- YoY % inflation by component;
  * ipc_cores_panel.png   -- one panel per core vs the 3% target and 2-4% band;
  * ipc_cores_drivers.png -- what drove the surge: components through 2018-2023 +
    the peak-by-component ranking (what was most impactful).
"""

from __future__ import annotations

import io
import urllib.request

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import DATA_CLEAN, FIGURES, ensure_directories

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
SERIES = {
    "Cheia (todos os itens)": "CHLCPIALLMINMEI",
    "Núcleo (s/ alim. e energia)": "CHLCPICORMINMEI",
    "Energia": "CHLCPIENGMINMEI",
    "Serviços": "CHLCPGRSE01IXOBM",
}
COLORS = {
    "Cheia (todos os itens)": "#111827",
    "Núcleo (s/ alim. e energia)": "#1E4E79",
    "Energia": "#B45309",
    "Serviços": "#16A34A",
}
TARGET, BAND = 3.0, (2.0, 4.0)


def download_fred(series_id: str) -> pd.Series:
    url = FRED_CSV.format(series_id=series_id)
    with urllib.request.urlopen(url, timeout=60) as response:
        raw = response.read().decode("utf-8", "replace")
    frame = pd.read_csv(io.StringIO(raw))
    frame.columns = ["date", "value"]
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.dropna()
    return pd.Series(frame["value"].to_numpy(), index=pd.DatetimeIndex(frame["date"]))


def main() -> None:
    ensure_directories()
    yoy = {}
    for name, sid in SERIES.items():
        index = download_fred(sid).sort_index()
        # 12-month change of the monthly index = annualised (YoY) inflation rate.
        yoy[name] = (index / index.shift(12) - 1.0) * 100.0
    data = pd.DataFrame(yoy).dropna(how="all")
    data.index.name = "date"
    data.to_csv(DATA_CLEAN / "chile_inflation_cores.csv")
    last_full = data["Cheia (todos os itens)"].dropna().index.max()

    # ------------------------------------------------------------------ #
    # Figure 1: one panel per core vs the target band.                    #
    # ------------------------------------------------------------------ #
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 7.2), sharex=True)
    for ax, name in zip(axes.ravel(), SERIES):
        series = data[name].dropna().loc["2000-01-01":]  # inflation-targeting era only
        ax.axhspan(BAND[0], BAND[1], color="#FDE68A", alpha=0.35, label="Banda 2--4%")
        ax.axhline(TARGET, color="#B45309", linestyle="--", linewidth=1, label="Meta 3%")
        ax.plot(series.index, series.values, color=COLORS[name], linewidth=1.8)
        latest = series.iloc[-1]
        inside = BAND[0] <= latest <= BAND[1]
        ax.set_title(f"{name}  —  último {latest:.1f}% "
                     f"({'dentro' if inside else 'fora'} da banda)", fontsize=10)
        ax.set_ylabel("% a.a. (YoY)")
        ax.grid(alpha=0.25)
    axes[0, 0].legend(fontsize=8, loc="upper left")
    fig.suptitle("Inflação do IPC chileno por núcleo (variação anual) vs meta de 3%")
    fig.text(0.01, 0.01, f"Fonte: OECD via FRED. Componentes até {last_full:%Y-%m} "
             "(OECD descontinuou; perde a desinflação recente). Variação interanual = anualizada.",
             fontsize=7.5)
    fig.tight_layout(rect=(0, 0.03, 1, 0.96))
    fig.savefig(FIGURES / "ipc_cores_panel.png", dpi=170)
    plt.close(fig)

    # ------------------------------------------------------------------ #
    # Figure 2: what drove the surge (2018-2023) + peak ranking.          #
    # ------------------------------------------------------------------ #
    window = data.loc["2018-01-01":]
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.5, 5.0),
                                   gridspec_kw={"width_ratios": [2.0, 1.0]})
    for name in SERIES:
        s = window[name].dropna()
        axL.plot(s.index, s.values, color=COLORS[name], linewidth=2.0, label=name)
    axL.axhspan(BAND[0], BAND[1], color="#FDE68A", alpha=0.3)
    axL.axhline(TARGET, color="#B45309", linestyle="--", linewidth=1)
    axL.set_title("O surto de 2021--2023 por núcleo")
    axL.set_ylabel("Inflação anual (%)")
    axL.grid(alpha=0.25)
    axL.legend(fontsize=8)

    # Peak YoY during 2021-2023 by component = "what was most impactful".
    surge = data.loc["2021-01-01":"2023-12-31"]
    peaks = {name: float(surge[name].max()) for name in SERIES}
    order = sorted(peaks, key=peaks.get)
    axR.barh(range(len(order)), [peaks[n] for n in order],
             color=[COLORS[n] for n in order])
    axR.set_yticks(range(len(order)))
    axR.set_yticklabels([n.split(" (")[0] for n in order], fontsize=8)
    axR.axvline(TARGET, color="#B45309", linestyle="--", linewidth=1)
    axR.set_title("Pico de inflação 2021--23")
    axR.set_xlabel("% a.a.")
    axR.grid(alpha=0.25, axis="x")
    for i, n in enumerate(order):
        axR.text(peaks[n], i, f" {peaks[n]:.0f}%", va="center", fontsize=8)

    fig.suptitle("Quem mais empurrou a inflação chilena: energia lidera o pico, núcleo/serviços são persistentes")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIGURES / "ipc_cores_drivers.png", dpi=170)
    plt.close(fig)

    print("Peak YoY 2021-23 by component:")
    for n in reversed(order):
        print(f"  {n}: {peaks[n]:.1f}%")
    print(f"Wrote chile_inflation_cores.csv, ipc_cores_panel.png, ipc_cores_drivers.png "
          f"(through {last_full:%Y-%m})")


if __name__ == "__main__":
    main()
