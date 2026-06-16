"""Chilean activity and labour-market analysis from public FRED data, with an
Atlanta-Fed-style labour-market spider chart.

FRED has no Chilean vacancies/hires/quits (JOLTS is US-only), so the spider uses
the available Chilean equivalents: unemployment, youth unemployment, employment
rate, participation, industrial production and the model's (Kalman) output gap --
each as a percentile of its own history, oriented so OUTWARD = stronger labour
market/activity, current versus pre-pandemic (2019).

Outputs: labor_activity_dashboard.png, labor_spider.png, data/clean/chile_labor.csv.
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
    "unemployment": "LRHUTTTTCLM156S",   # unemployment rate, %
    "youth_unemp": "SLUEM1524ZSCHL",     # youth (15-24) unemployment, %
    "employment": "LREM64TTCLM156S",     # employment rate 15-64, %
    "participation": "LRACTTTTCLM156S",  # participation rate, %
    "industrial": "CHLPROINDMISMEI",     # industrial production index
}


def download_fred(series_id: str) -> pd.Series:
    with urllib.request.urlopen(FRED_CSV.format(series_id=series_id), timeout=60) as resp:
        raw = resp.read().decode("utf-8", "replace")
    frame = pd.read_csv(io.StringIO(raw))
    frame.columns = ["date", "value"]
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.dropna()
    return pd.Series(frame["value"].to_numpy(), index=pd.DatetimeIndex(frame["date"])).sort_index()


def to_quarterly(series: pd.Series) -> pd.Series:
    q = series.resample("QS").mean()
    q.index = q.index.to_period("Q").astype(str)
    return q


def main() -> None:
    ensure_directories()
    raw = {name: download_fred(sid) for name, sid in SERIES.items()}
    quarterly = pd.DataFrame({name: to_quarterly(s) for name, s in raw.items()})
    quarterly["industrial_yoy"] = (quarterly["industrial"] /
                                   quarterly["industrial"].shift(4) - 1.0) * 100.0

    macro = pd.read_csv(DATA_CLEAN / "chile_macro_quarterly.csv").set_index("date")
    quarterly["output_gap"] = macro["output_gap"] * 100.0  # Kalman gap, %
    quarterly = quarterly.loc["2001Q1":]
    quarterly.index.name = "date"
    quarterly.to_csv(DATA_CLEAN / "chile_labor.csv")
    dates = quarterly.index.tolist()
    xt = list(range(0, len(dates), 8))

    # ------------------------------------------------------------------ #
    # Figure 1: activity + labour dashboard.                              #
    # ------------------------------------------------------------------ #
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.6))
    a = axes[0]
    a.plot(range(len(dates)), quarterly["unemployment"], color="#B91C1C", linewidth=2, label="Desemprego")
    a.plot(range(len(dates)), quarterly["youth_unemp"], color="#F59E0B", linewidth=1.6,
           linestyle="--", label="Desemprego jovem")
    a.set_title("Desemprego (%)"); a.legend(fontsize=8); a.grid(alpha=0.25)
    b = axes[1]
    b.plot(range(len(dates)), quarterly["employment"], color="#1E4E79", linewidth=2, label="Taxa de emprego")
    b.plot(range(len(dates)), quarterly["participation"], color="#16A34A", linewidth=2, label="Participação")
    b.set_title("Emprego e participação (%)"); b.legend(fontsize=8); b.grid(alpha=0.25)
    c = axes[2]
    c.axhline(0, color="black", linewidth=0.7)
    c.plot(range(len(dates)), quarterly["output_gap"], color="#7C3AED", linewidth=2, label="Hiato (Kalman)")
    c.plot(range(len(dates)), quarterly["industrial_yoy"], color="#6B7280", linewidth=1.4,
           linestyle="--", label="Prod. industrial (YoY)")
    c.set_title("Atividade (%)"); c.legend(fontsize=8); c.grid(alpha=0.25)
    for ax in axes:
        ax.set_xticks(xt); ax.set_xticklabels([dates[t] for t in xt], rotation=70, fontsize=7)
    fig.suptitle("Chile: mercado de trabalho e atividade (FRED + hiato do modelo)")
    fig.text(0.01, 0.01, "Fonte: OECD via FRED; hiato pelo filtro de Kalman. Sem dados de vagas/"
             "admissões para o Chile. Okun: desemprego move-se inversamente ao hiato.", fontsize=7.5)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    fig.savefig(FIGURES / "labor_activity_dashboard.png", dpi=170)
    plt.close(fig)

    # ------------------------------------------------------------------ #
    # Figure 2: Atlanta-Fed-style spider (percentiles, outward=stronger). #
    # ------------------------------------------------------------------ #
    # Orientation: higher percentile = stronger labour market.
    indicators = {
        "Emprego": ("employment", +1),
        "Participação": ("participation", +1),
        "Atividade\n(hiato)": ("output_gap", +1),
        "Prod.\nindustrial": ("industrial_yoy", +1),
        "Baixo desemp.\njovem": ("youth_unemp", -1),
        "Baixo\ndesemprego": ("unemployment", -1),
    }

    def percentile(series: pd.Series, value: float, sign: int) -> float:
        s = series.dropna()
        pct = 100.0 * (s < value).mean()
        return pct if sign > 0 else 100.0 - pct

    prepan = "2019Q4"
    labels, now_vals, pre_vals = [], [], []
    for label, (col, sign) in indicators.items():
        s = quarterly[col]
        labels.append(label)
        now_vals.append(percentile(s, float(s.dropna().iloc[-1]), sign))
        pre_vals.append(percentile(s, float(s.loc[prepan]) if prepan in s.index else float(s.dropna().iloc[-1]), sign))

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(8.2, 7.2), subplot_kw=dict(polar=True))
    for vals, color, name in ((pre_vals, "#9CA3AF", "Pré-pandemia (2019)"),
                              (now_vals, "#1E4E79", "Atual (último dado)")):
        v = vals + vals[:1]
        ax.plot(angles, v, color=color, linewidth=2.2, label=name)
        ax.fill(angles, v, color=color, alpha=0.18)
    ax.set_xticks(angles[:-1]); ax.set_xticklabels(labels, fontsize=9)
    ax.set_yticks([25, 50, 75]); ax.set_yticklabels(["25", "50", "75"], fontsize=7)
    ax.set_ylim(0, 100)
    ax.set_title("Spider do mercado de trabalho chileno (percentis vs história)\n"
                 "outward = mais forte", fontsize=11)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), fontsize=9)
    fig.text(0.01, 0.01, "Estilo FED Atlanta: cada indicador em percentil vs sua história (2001+), "
             "orientado p/ fora=mercado mais forte. Sem JOLTS/vagas para o Chile.", fontsize=7.5)
    fig.tight_layout()
    fig.savefig(FIGURES / "labor_spider.png", dpi=170)
    plt.close(fig)

    print("Latest labour percentiles (outward=stronger):")
    for label, nv in zip(labels, now_vals):
        print(f"  {label.replace(chr(10),' ')}: {nv:.0f}")
    print(f"Unemployment last {quarterly['unemployment'].dropna().iloc[-1]:.1f}% | "
          f"employment {quarterly['employment'].dropna().iloc[-1]:.1f}% | "
          f"gap {quarterly['output_gap'].dropna().iloc[-1]:.1f}%")
    print("Wrote labor_activity_dashboard.png, labor_spider.png, chile_labor.csv")


if __name__ == "__main__":
    main()
