"""A two-panel 'what the hybrid is, and whether it pays off' figure for the slide.

Left  : inflation response to a cost-push shock, baseline vs hybrid -- the hybrid
        carries inflation forward (intrinsic persistence 0.05 -> 0.38).
Right : out-of-sample inflation RMSE, baseline vs hybrid, at 1 and 4 quarters --
        the inertia cuts the 1-quarter error by ~19% and ties at 1 year.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import DYNARE_OUTPUTS, FIGURES, TABLES, ensure_directories

BASE = "#1E4E79"
HYB = "#B91C1C"


def main() -> None:
    ensure_directories()
    base_irf = pd.read_csv(DYNARE_OUTPUTS / "baseline" / "irfs.csv")
    hyb_irf = pd.read_csv(DYNARE_OUTPUTS / "hybrid_nkpc" / "irfs.csv")
    oos = pd.read_csv(TABLES / "forecast_oos_metrics.csv")

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(12, 4.7))

    # ---- Left: inflation IRF to a cost-push shock (annualised p.p.) ----
    h = base_irf["horizon"].to_numpy()
    axL.plot(h, base_irf["pi_e_pi"].to_numpy() * 400, color=BASE, linewidth=2.4,
             label="Baseline (sem inércia)")
    axL.plot(h, hyb_irf["pi_e_pi"].to_numpy() * 400, color=HYB, linewidth=2.4,
             linestyle="--", label="Híbrida (com inércia)")
    axL.axhline(0, color="black", linewidth=0.7)
    axL.set_title("Como a inflação reage a um choque de custo")
    axL.set_xlabel("Trimestres após o choque")
    axL.set_ylabel("Resposta da inflação (p.p. anual)")
    axL.grid(alpha=0.25)
    axL.legend(fontsize=9)
    axL.annotate("Persistência da inflação:\nbaseline 0,05  →  híbrida 0,38",
                 xy=(7.5, axL.get_ylim()[1] * 0.55), fontsize=9,
                 bbox=dict(boxstyle="round", fc="#FEF3C7", ec="#B45309", alpha=0.9))

    # ---- Right: out-of-sample inflation RMSE, baseline vs hybrid ----
    pi = oos[(oos["variable"] == "pi") & oos["model"].isin(["NK", "NK híbrido"])]
    def rmse(model, horizon):
        return float(pi[(pi["model"] == model) & (pi["horizon"] == horizon)]["rmse"].iloc[0])

    groups = ["1 trimestre", "1 ano (4 trim.)"]
    base_vals = [rmse("NK", 1), rmse("NK", 4)]
    hyb_vals = [rmse("NK híbrido", 1), rmse("NK híbrido", 4)]
    xpos = np.arange(2)
    width = 0.36
    axR.bar(xpos - width / 2, base_vals, width, color=BASE, label="Baseline")
    axR.bar(xpos + width / 2, hyb_vals, width, color=HYB, label="Híbrida")
    improvement = 100.0 * (base_vals[0] - hyb_vals[0]) / base_vals[0]
    axR.annotate(f"-{improvement:.0f}%", xy=(0, hyb_vals[0]), xytext=(0, hyb_vals[0] + 0.4),
                 ha="center", fontsize=11, fontweight="bold", color=HYB,
                 arrowprops=dict(arrowstyle="->", color=HYB))
    axR.annotate("empate", xy=(1, max(base_vals[1], hyb_vals[1])),
                 xytext=(1, max(base_vals[1], hyb_vals[1]) + 0.4), ha="center",
                 fontsize=10, color="#374151")
    axR.set_xticks(xpos)
    axR.set_xticklabels(groups)
    axR.set_title("Erro de previsão da inflação (fora-da-amostra)")
    axR.set_ylabel("RMSE (p.p.)")
    axR.set_ylim(0, max(base_vals) * 1.25)
    axR.grid(alpha=0.25, axis="y")
    axR.legend(fontsize=9)

    fig.suptitle("A NKPC híbrida: inércia de inflação e ganho de previsão de curto prazo",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(FIGURES / "hybrid_test.png", dpi=180)
    plt.close(fig)
    print(f"Wrote hybrid_test.png (1q improvement {improvement:.1f}%)")


if __name__ == "__main__":
    main()
