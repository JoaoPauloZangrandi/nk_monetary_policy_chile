"""A direct-answer 'outlook' figure: where is Chile's economy heading?

Reads the native Dynare unconditional forecast and draws a clean, presentation-
ready dashboard for the next 8 quarters (TPM, inflation, output gap), with the
1-year-ahead point clearly annotated. The 1-year horizon is highlighted because
the pseudo-out-of-sample test (evaluate_forecasts.py) is where the NK model
actually beats naive benchmarks for inflation and the gap.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import DATA_CLEAN, DYNARE_OUTPUTS, FIGURES, ensure_directories
from hybrid_solution import hybrid_forecast, hybrid_params, solve_hybrid

FORECAST = DYNARE_OUTPUTS / "forecast" / "forecast_unconditional.csv"


def main() -> None:
    ensure_directories()
    macro = pd.read_csv(DATA_CLEAN / "chile_macro_quarterly.csv")
    fc = pd.read_csv(FORECAST)

    mean_infl_q = float(macro["infl_q"].mean())
    mean_i_q = float(macro["i_q"].mean())
    target_q = (1.03) ** 0.25 - 1.0  # inflation observable is centred on the 3% target
    mean_infl_annual = ((1.0 + mean_infl_q) ** 4 - 1.0) * 100.0
    mean_tpm_annual = ((1.0 + mean_i_q) ** 4 - 1.0) * 100.0

    def to_level(var, dev):
        dev = np.asarray(dev, dtype=float)
        if var == "x":
            return 100.0 * dev
        if var == "pi":
            return ((1.0 + target_q + dev) ** 4 - 1.0) * 100.0
        return ((1.0 + mean_i_q + dev) ** 4 - 1.0) * 100.0

    last_period = pd.Period(str(macro.iloc[-1]["date"]), freq="Q")
    horizon = int(fc["horizon"].max())
    future = [str(last_period + h) for h in range(1, horizon + 1)]

    # Hybrid (data-preferred) forecast from the current state, for robustness.
    hybrid_sol = solve_hybrid(hybrid_params(0.35))
    i_dev0 = float(macro["i_q"].iloc[-1] - mean_i_q)
    pi_dev0 = float(macro["infl_q"].iloc[-1] - target_q)
    hybrid_dev = np.array(
        [hybrid_forecast(hybrid_sol, i_dev0, pi_dev0, h) for h in range(1, horizon + 1)]
    )  # (horizon, 3) deviations of [x, pi, i]
    var_col = {"x": 0, "pi": 1, "i": 2}

    hist = macro.tail(8).copy()
    hist_dates = hist["date"].tolist()
    n_hist = len(hist_dates)
    all_dates = hist_dates + future
    x_hist = np.arange(n_hist)
    x_fc = np.arange(n_hist - 1, n_hist - 1 + horizon + 1)  # connect last obs to forecast

    panels = [
        ("i", hist["tpm_annual_pct"].to_numpy(), "Taxa de política (TPM, % a.a.)", mean_tpm_annual, None),
        ("pi", hist["infl_annual_pct"].to_numpy(), "Inflação (% a.a.)", mean_infl_annual, 3.0),
        ("x", 100.0 * hist["output_gap"].to_numpy(), "Hiato do produto (%)", 0.0, None),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 5.0))
    for ax, (var, hist_vals, title, neutral, target) in zip(axes, panels):
        sub = fc[fc["variable"] == var].sort_values("horizon")
        mean_lv = to_level(var, sub["mean"].to_numpy())
        inf_lv = to_level(var, sub["hpd_inf"].to_numpy())
        sup_lv = to_level(var, sub["hpd_sup"].to_numpy())
        last_obs = float(hist_vals[-1])

        ax.plot(x_hist, hist_vals, color="black", marker="o", markersize=3.5,
                linewidth=1.6, label="Observado")
        ax.plot(x_fc, np.concatenate([[last_obs], mean_lv]), color="#1E4E79",
                linewidth=2.6, label="Previsão (central)")
        ax.fill_between(x_fc, np.concatenate([[last_obs], inf_lv]),
                        np.concatenate([[last_obs], sup_lv]),
                        color="#1E4E79", alpha=0.15, label="Banda 90%")
        # Hybrid forecast (data-preferred model) for robustness.
        hyb_lv = to_level(var, hybrid_dev[:, var_col[var]])
        ax.plot(x_fc, np.concatenate([[last_obs], hyb_lv]), color="#B91C1C",
                linewidth=1.7, linestyle="--", label="Híbrida (preferida pelos dados)")
        # Highlight the 1-year-ahead (horizon 4) point.
        h1y = 4
        x1y = n_hist - 1 + h1y
        y1y = float(mean_lv[h1y - 1])
        ax.scatter([x1y], [y1y], color="#B91C1C", zorder=5, s=45)
        ax.annotate(f"1 ano:\n{y1y:.1f}%", (x1y, y1y), textcoords="offset points",
                    xytext=(8, 10), fontsize=9, color="#B91C1C", fontweight="bold")

        ax.axvline(n_hist - 1, color="#9CA3AF", linewidth=0.9, linestyle="-")
        if target is not None:
            ax.axhline(target, color="#B45309", linestyle="--", linewidth=1, label="Meta 3%")
        ax.axhline(neutral, color="#6B7280", linestyle=":", linewidth=1,
                   label="Neutro/média" if var != "x" else "Potencial")
        ax.set_title(title, fontsize=11)
        step = 2
        ticks = list(range(0, len(all_dates), step))
        ax.set_xticks(ticks)
        ax.set_xticklabels([all_dates[t] for t in ticks], rotation=70, fontsize=7)
        ax.grid(alpha=0.22)
        ax.legend(fontsize=7, loc="best")

    fig.suptitle("Previsão do modelo para o Chile — próximos 8 trimestres (incondicional, Dynare)",
                 fontsize=13)
    fig.text(0.01, 0.005,
             "Linha vertical = último dado (2026Q1). Ponto vermelho = horizonte de 1 ano. A linha "
             "tracejada é a NKPC híbrida (preferida pelos dados): segura mais a inflação no curto "
             "prazo, mas converge para a mesma previsão de 1 ano. Não é previsão oficial do BCCh.",
             fontsize=7.5)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(FIGURES / "forecast_outlook.png", dpi=180)
    plt.close(fig)
    print("Wrote forecast_outlook.png")


if __name__ == "__main__":
    main()
