"""Chilean CPI cores from the BCCh (real, recent: base 2023=100, up to 2026).

Pulls the BCCh analytical CPI breakdown (general, sin volatiles, goods/services
sin volatiles, volatile, volatile food/energy) as monthly variations (MoM, %)
from the SieteRestWS, then builds the central-bank "inflation momentum" view per
core:

  * MoM  (monthly change, annualised)        -> bars
  * MM3M (3-month change, annualised)         -> line
  * MM6M (6-month change, annualised)         -> line
  * YoY  (12-month change)                    -> line

All four are expressed as annual % so they are directly comparable and sit
against the 2-4% tolerance band (in/out of target). This replaces the FRED cores
(frozen at 2023-12) with real data through the latest BCCh release.

Credentials: env BCCH_USER/BCCH_PASS or data/raw/bcch_credentials.json.
Outputs: data/clean/chile_inflation_cores_bcch.csv, ipc_cores_momentum.png.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import DATA_CLEAN, FIGURES, ensure_directories
from build_chile_dataset import fetch_series, get_credentials

# Monthly CPI variation (MoM, %) series ids -- filled from discover_ipc_series.py.
# label -> F074.IPC... id
MAPPING: dict[str, str] = {
    "Cheia (IPC geral)": "F074.IPC.VAR.Z.EP23.C.M",
    "Núcleo (SAE)": "F074.IPCSAE.VAR.Z.EP23.Z.M",
    "Serviços": "F074.IPCS.VAR.Z.EP23.Z.M",
    "Bens": "F074.IPCB.VAR.Z.EP23.Z.M",
    "Energia": "F074.IPCE.VAR.Z.EP23.Z.M",
    "Alimentos": "F074.IPCA.VAR.Z.EP23.Z.M",
}
COLORS = {
    "Cheia (IPC geral)": "#111827",
    "Núcleo (SAE)": "#1E4E79",
    "Serviços": "#16A34A",
    "Bens": "#7C3AED",
    "Energia": "#B45309",
    "Alimentos": "#0891B2",
}
TARGET, BAND = 3.0, (2.0, 4.0)
START_PLOT = "2021-01-01"


def momentum(mom_pct: pd.Series) -> pd.DataFrame:
    """Monthly variation (MoM, %), its 3/6-month moving averages (%/mo), YoY (%).

    MoM/MM3M/MM6M stay on the monthly scale (left axis); YoY is the accumulated
    12-month change on the annual scale (right axis). Annualising single monthly
    prints is avoided -- it explodes for volatile cores (energy tariff months).
    """
    s = mom_pct.sort_index()
    f = 1.0 + s / 100.0  # gross monthly factors
    out = pd.DataFrame(index=s.index)
    out["MoM"] = s                                  # monthly variation, %
    out["MM3M"] = s.rolling(3).mean()               # 3-month moving average, %/mo
    out["MM6M"] = s.rolling(6).mean()               # 6-month moving average, %/mo
    out["YoY"] = (f.rolling(12).apply(np.prod, raw=True) - 1.0) * 100.0  # 12-month, %
    return out


def main() -> None:
    ensure_directories()
    creds = get_credentials()
    if not creds:
        raise SystemExit("No BCCh credentials (set BCCH_USER/BCCH_PASS or "
                         "data/raw/bcch_credentials.json).")
    user, password = creds
    if len(MAPPING) < 2:
        raise SystemExit("Fill MAPPING with the core series ids first "
                         "(run discover_ipc_series.py).")

    cores = {label: momentum(fetch_series(sid, user, password, first="2018-01-01"))
             for label, sid in MAPPING.items()}

    # Tidy CSV: every core x metric.
    wide = pd.concat({label: df for label, df in cores.items()}, axis=1)
    wide.index.name = "date"
    wide.to_csv(DATA_CLEAN / "chile_inflation_cores_bcch.csv")
    last = max(df["YoY"].dropna().index.max() for df in cores.values())

    labels = list(cores)
    ncol = 3
    nrow = int(np.ceil(len(labels) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(5.6 * ncol, 3.4 * nrow),
                             sharex=True)
    axes = np.atleast_1d(axes).ravel()
    handles: list = []
    hlabels: list[str] = []
    for ax, label in zip(axes, labels):
        df = cores[label].loc[START_PLOT:]
        color = COLORS.get(label, "#1E4E79")
        # Left axis (monthly %): MoM bars + 3/6-month moving averages.
        ax.axhline(0, color="#9CA3AF", lw=0.6, zorder=1)
        b = ax.bar(df.index, df["MoM"], width=22, color=color, alpha=0.28,
                   label="MoM", zorder=2)
        l3, = ax.plot(df.index, df["MM3M"], color=color, lw=1.6, label="MM3M",
                      zorder=3)
        l6, = ax.plot(df.index, df["MM6M"], color=color, lw=1.2, ls=(0, (4, 2)),
                      label="MM6M", zorder=3)
        ax.tick_params(axis="y", labelsize=7, colors=color)
        ax.tick_params(axis="x", labelsize=8)
        # Right axis (annual %): YoY vs the 2-4% tolerance band.
        ax2 = ax.twinx()
        ax2.axhspan(BAND[0], BAND[1], color="#FDE68A", alpha=0.40, zorder=0)
        ax2.axhline(TARGET, color="#B45309", ls="--", lw=0.8, zorder=1)
        ly, = ax2.plot(df.index, df["YoY"], color="#111827", lw=1.9, label="YoY",
                       zorder=4)
        ax2.tick_params(axis="y", labelsize=7)
        yoy_last = df["YoY"].dropna().iloc[-1]
        inside = BAND[0] <= yoy_last <= BAND[1]
        ax.set_title(f"{label} — YoY {yoy_last:.1f}% "
                     f"({'dentro' if inside else 'fora'} da banda)", fontsize=9.5)
        ax.grid(alpha=0.18)
        if not handles:
            handles = [b, l3, l6, ly]
            hlabels = ["MoM (mensal, esq.)", "MM3M (esq.)", "MM6M (esq.)",
                       "YoY (anual, dir.)"]
    for ax in axes[len(labels):]:
        ax.set_visible(False)
    fig.legend(handles, hlabels, loc="lower center", fontsize=9, ncol=4,
               bbox_to_anchor=(0.5, 0.03), frameon=False)
    fig.suptitle("IPC chileno por núcleo — barras: MoM e linhas finas MM3M/MM6M "
                 "(eixo esq., %/mês)\n· linha preta: YoY (eixo dir., % a.a.) vs banda "
                 "de tolerância 2–4%", fontsize=11.5)
    fig.text(0.01, 0.004, "Fonte: Banco Central de Chile — IPC Analíticos empalmados "
             f"(cifras oficiais INE), base 2023=100, SieteRestWS. Última obs.: {last:%Y-%m}.",
             fontsize=7.5)
    fig.tight_layout(rect=(0, 0.06, 1, 0.93))
    fig.savefig(FIGURES / "ipc_cores_momentum.png", dpi=170)
    plt.close(fig)

    # ------------------------------------------------------------------ #
    # Figure 2: drivers -- YoY timeline + recent momentum (MM3M) ranking. #
    # ------------------------------------------------------------------ #
    timeline = [l for l in ("Cheia (IPC geral)", "Núcleo (SAE)", "Energia",
                            "Serviços") if l in cores]
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.5, 5.0),
                                   gridspec_kw={"width_ratios": [2.1, 1.0]})
    for label in timeline:
        s = cores[label]["YoY"].loc[START_PLOT:].dropna()
        axL.plot(s.index, s.values, color=COLORS.get(label, "#1E4E79"), lw=2.0,
                 label=label)
    axL.axhspan(BAND[0], BAND[1], color="#FDE68A", alpha=0.30)
    axL.axhline(TARGET, color="#B45309", ls="--", lw=1.0)
    axL.set_title("Inflação anual (YoY) por núcleo")
    axL.set_ylabel("% a.a.")
    axL.grid(alpha=0.25)
    axL.legend(fontsize=8)
    latest_mm3 = {l: float(cores[l]["MM3M"].dropna().iloc[-1]) for l in cores}
    order = sorted(latest_mm3, key=latest_mm3.get)
    axR.barh(range(len(order)), [latest_mm3[l] for l in order],
             color=[COLORS.get(l, "#1E4E79") for l in order])
    axR.set_yticks(range(len(order)))
    axR.set_yticklabels(order, fontsize=8)
    axR.axvline(0, color="#9CA3AF", lw=0.6)
    axR.set_title(f"Momentum recente — MM3M (%/mês), {last:%Y-%m}")
    axR.set_xlabel("%/mês")
    axR.grid(alpha=0.25, axis="x")
    for i, l in enumerate(order):
        axR.text(latest_mm3[l], i, f" {latest_mm3[l]:.1f}", va="center", fontsize=8)
    fig.suptitle("Quem empurra a inflação chilena: a energia lidera o momentum; "
                 "serviços é o persistente")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIGURES / "ipc_cores_drivers_bcch.png", dpi=170)
    plt.close(fig)

    print(f"Wrote chile_inflation_cores_bcch.csv + ipc_cores_momentum.png "
          f"+ ipc_cores_drivers_bcch.png (through {last:%Y-%m}).")
    for label, df in cores.items():
        print(f"  {label:28s} YoY {df['YoY'].dropna().iloc[-1]:5.1f}%  "
              f"MM3M {df['MM3M'].dropna().iloc[-1]:5.1f}%")


if __name__ == "__main__":
    main()
