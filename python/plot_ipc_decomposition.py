"""Decomposition of Chilean IPC (CPI) inflation into structural drivers.

Two figures:

1. ipc_inflation_decomposition.png -- the observed IPC inflation (annualised %) and
   how much of each quarter's deviation from the sample mean (3.8%) came from
   DEMAND, COST-PUSH and MONETARY shocks, per the Kalman-smoothed baseline model.
   The 2008 and 2022 inflation surges are highlighted.

2. ipc_inflation_models.png -- the SAME IPC inflation read by TWO models: the
   forward-looking baseline and the hybrid NKPC (with inflation memory). The hybrid
   needs much smaller cost-push shocks, because intrinsic persistence carries part
   of the inflation -- i.e., the macro story of 2022 depends on the model.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import DATA_CLEAN, DYNARE_OUTPUTS, FIGURES, ensure_directories

HIST = DYNARE_OUTPUTS / "history"
HIST_HYB = DYNARE_OUTPUTS / "history_hybrid"
SHOCKS = {
    "e_x": ("Demanda", "#1E4E79"),
    "e_pi": ("Custo (cost-push)", "#B45309"),
    "e_i": ("Política monetária", "#16A34A"),
    "initial": ("Condição inicial", "#9CA3AF"),
}
ANN = 400.0  # linear annualisation of a quarterly inflation deviation (keeps additivity)


def main() -> None:
    ensure_directories()
    macro = pd.read_csv(DATA_CLEAN / "chile_macro_quarterly.csv")
    dates = macro["date"].tolist()
    n = len(dates)
    mean_infl_annual = ((1.0 + macro["infl_q"].mean()) ** 4 - 1.0) * 100.0
    ipc = macro["infl_annual_pct"].to_numpy()

    decomp = pd.read_csv(HIST / "shock_decomp.csv")
    pi = decomp[decomp["variable"] == "pi"].sort_values("period").reset_index(drop=True)

    xticks = list(range(0, n, 8))
    xlabels = [dates[t] for t in xticks]
    # Episode shading (2008 and 2022 surges).
    def idx(label):
        return dates.index(label) if label in dates else None
    episodes = [("2008Q3", "2009Q2"), ("2021Q4", "2023Q1")]

    # ------------------------------------------------------------------ #
    # Figure 1: IPC inflation decomposition (baseline).                  #
    # ------------------------------------------------------------------ #
    fig, ax = plt.subplots(figsize=(12.5, 6.2))
    xs = np.arange(n)
    pos = np.full(n, mean_infl_annual)
    neg = np.full(n, mean_infl_annual)
    for comp in ("e_x", "e_pi", "e_i", "initial"):
        vals = pi[comp].to_numpy() * ANN
        p = np.where(vals > 0, vals, 0.0)
        m = np.where(vals < 0, vals, 0.0)
        label, color = SHOCKS[comp]
        ax.bar(xs, p, bottom=pos, color=color, width=0.92, label=label, edgecolor="none")
        ax.bar(xs, m, bottom=neg, color=color, width=0.92, edgecolor="none")
        pos += p
        neg += m
    ax.plot(xs, ipc, color="black", linewidth=1.6, label="IPC observado (% a.a.)")
    ax.axhline(mean_infl_annual, color="#374151", linewidth=1.0, linestyle="-",
               label=f"Média 2001--2026 ({mean_infl_annual:.1f}%)")
    ax.axhline(3.0, color="#B45309", linewidth=1.0, linestyle="--", label="Meta 3%")
    for a, b in episodes:
        ia, ib = idx(a), idx(b)
        if ia is not None and ib is not None:
            ax.axvspan(ia, ib, color="#FCD34D", alpha=0.18)
    ax.set_title("Decomposição da inflação do IPC chileno (modelo baseline, suavizador de Kalman)")
    ax.set_ylabel("Inflação anualizada (% a.a.)")
    ax.set_xticks(xticks)
    ax.set_xticklabels(xlabels, rotation=70, fontsize=7)
    ax.grid(alpha=0.2, axis="y")
    ax.legend(ncol=3, fontsize=8, loc="upper center")
    fig.text(0.01, 0.005, "Barras = contribuição de cada choque ao desvio da média (anualizado, "
             "aproximação linear). Faixas amarelas: surtos de 2008 e 2022. "
             "Decomposição do modelo, não identificação oficial.", fontsize=7)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIGURES / "ipc_inflation_decomposition.png", dpi=170)
    plt.close(fig)

    # ------------------------------------------------------------------ #
    # Figure 2: the same IPC inflation, two models.                      #
    # ------------------------------------------------------------------ #
    sh_base = pd.read_csv(HIST / "smoothed_shocks.csv")
    sh_hyb = pd.read_csv(HIST_HYB / "smoothed_shocks.csv")
    std_base = sh_base["e_pi"].std()
    std_hyb = sh_hyb["e_pi"].std()

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(13.5, 5.0))

    # Left: cost-push shock series, baseline vs hybrid.
    axA.bar(xs - 0.2, sh_base["e_pi"].to_numpy() * 100, width=0.4, color="#B45309",
            label=f"Baseline (σ={std_base*100:.2f} p.p.)")
    axA.bar(xs + 0.2, sh_hyb["e_pi"].to_numpy() * 100, width=0.4, color="#B91C1C",
            label=f"Híbrida (σ={std_hyb*100:.2f} p.p.)")
    axA.axhline(0, color="black", linewidth=0.7)
    for a, b in episodes:
        ia, ib = idx(a), idx(b)
        if ia is not None and ib is not None:
            axA.axvspan(ia, ib, color="#FCD34D", alpha=0.18)
    axA.set_title("Choque de custo recuperado (e_pi)")
    axA.set_ylabel("p.p. trimestral")
    axA.set_xticks(xticks)
    axA.set_xticklabels(xlabels, rotation=70, fontsize=7)
    axA.grid(alpha=0.2, axis="y")
    axA.legend(fontsize=9)

    # Right: cost-push contribution to inflation, baseline vs hybrid.
    pi_hyb = pd.read_csv(HIST_HYB / "shock_decomp.csv")
    pi_hyb = pi_hyb[pi_hyb["variable"] == "pi"].sort_values("period").reset_index(drop=True)
    axB.plot(xs, pi["e_pi"].to_numpy() * ANN, color="#B45309", linewidth=2.2,
             label="Baseline")
    axB.plot(xs, pi_hyb["e_pi"].to_numpy() * ANN, color="#B91C1C", linewidth=2.2,
             linestyle="--", label="Híbrida")
    axB.axhline(0, color="black", linewidth=0.7)
    for a, b in episodes:
        ia, ib = idx(a), idx(b)
        if ia is not None and ib is not None:
            axB.axvspan(ia, ib, color="#FCD34D", alpha=0.18)
    axB.set_title("Contribuição do custo à inflação (% a.a.)")
    axB.set_ylabel("p.p. anual")
    axB.set_xticks(xticks)
    axB.set_xticklabels(xlabels, rotation=70, fontsize=7)
    axB.grid(alpha=0.2, axis="y")
    axB.legend(fontsize=9)

    reduction = 100.0 * (std_base - std_hyb) / std_base
    fig.suptitle("A mesma inflação do IPC, dois modelos: com inércia (híbrida) os choques de custo "
                 f"caem {reduction:.0f}%", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(FIGURES / "ipc_inflation_models.png", dpi=170)
    plt.close(fig)

    print(f"Mean IPC inflation {mean_infl_annual:.2f}% a.a. | cost-push std baseline "
          f"{std_base*100:.2f} vs hybrid {std_hyb*100:.2f} p.p. (-{reduction:.0f}%)")
    print("Wrote ipc_inflation_decomposition.png and ipc_inflation_models.png")


if __name__ == "__main__":
    main()
