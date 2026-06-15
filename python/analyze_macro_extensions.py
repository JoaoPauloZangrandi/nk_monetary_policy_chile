"""Plot and summarize the open-economy and hybrid-Phillips extensions."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import DYNARE_OUTPUTS, FIGURES, TABLES, ensure_directories


def load_irfs(scenario: str) -> pd.DataFrame:
    return pd.read_csv(DYNARE_OUTPUTS / scenario / "irfs.csv")


def main() -> None:
    ensure_directories()
    open_irf = load_irfs("open_economy")
    hybrid_irf = load_irfs("hybrid_nkpc")
    baseline = load_irfs("baseline")
    h = open_irf["horizon"].to_numpy()

    variables = ["x", "pi", "i", "q", "copper"]
    shocks = ["e_i", "e_q", "e_copper"]
    labels = {
        "x": "Hiato",
        "pi": "Inflacao",
        "i": "Juro",
        "q": "Cambio real/nominal gap",
        "copper": "Cobre",
        "e_i": "Choque monetario",
        "e_q": "Choque cambial/risco",
        "e_copper": "Choque de cobre",
    }
    scales = {"x": 100, "pi": 400, "i": 400, "q": 100, "copper": 100}
    fig, axes = plt.subplots(5, 3, figsize=(14, 14), sharex=True)
    for row, variable in enumerate(variables):
        for col, shock in enumerate(shocks):
            ax = axes[row, col]
            ax.plot(h, open_irf[f"{variable}_{shock}"] * scales[variable],
                    color="#1E4E79", linewidth=2)
            ax.axhline(0, color="black", linewidth=0.6)
            if row == 0:
                ax.set_title(labels[shock])
            if col == 0:
                ax.set_ylabel(labels[variable])
            ax.grid(alpha=0.2)
    fig.suptitle("Modelo NK aberto: transmissao monetaria, cambial e do cobre")
    fig.text(
        0.01,
        0.01,
        "Extensao calibrada ilustrativa. q>0 representa depreciacao; respostas de x/q/cobre "
        "em %, pi/i em p.p. anualizados.",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.03, 1, 0.96))
    fig.savefig(FIGURES / "open_economy_irfs.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(2, 3, figsize=(14, 7), sharex=True)
    for col, shock in enumerate(["e_x", "e_pi", "e_i"]):
        for row, variable in enumerate(["pi", "x"]):
            ax = axes[row, col]
            scale = 400 if variable == "pi" else 100
            ax.plot(
                baseline["horizon"],
                baseline[f"{variable}_{shock}"] * scale,
                color="#6B7280",
                linewidth=2,
                label="NK prospectivo",
            )
            ax.plot(
                hybrid_irf["horizon"],
                hybrid_irf[f"{variable}_{shock}"] * scale,
                color="#B45309",
                linestyle="--",
                linewidth=2,
                label="NKPC hibrida",
            )
            ax.axhline(0, color="black", linewidth=0.6)
            ax.set_title(f"{variable} a {shock}")
            ax.grid(alpha=0.2)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Persistencia intrinseca: Phillips prospectiva versus hibrida")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(FIGURES / "hybrid_nkpc_irfs.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), sharex=True)
    for ax, variable in zip(axes, ["x", "pi", "i"]):
        scale = 100 if variable == "x" else 400
        ax.plot(
            baseline["horizon"],
            baseline[f"{variable}_e_i"] * scale,
            color="#6B7280",
            linewidth=2,
            label="Fechado",
        )
        ax.plot(
            open_irf["horizon"],
            open_irf[f"{variable}_e_i"] * scale,
            color="#1E4E79",
            linewidth=2,
            linestyle="--",
            label="Aberto",
        )
        ax.axhline(0, color="black", linewidth=0.6)
        ax.set_title(labels[variable])
        ax.grid(alpha=0.2)
    axes[0].legend()
    fig.suptitle("Choque monetario: modelo fechado versus economia aberta")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(FIGURES / "open_vs_closed_monetary_irf.png", dpi=180)
    plt.close(fig)

    rows = []
    for scenario, frame in [
        ("baseline", baseline),
        ("hybrid_nkpc", hybrid_irf),
        ("open_economy", open_irf),
    ]:
        available_shocks = ["e_x", "e_pi", "e_i"]
        if scenario == "open_economy":
            available_shocks += ["e_q", "e_copper"]
        for variable in ["x", "pi", "i"]:
            scale = 100 if variable == "x" else 400
            for shock in available_shocks:
                values = frame[f"{variable}_{shock}"].to_numpy() * scale
                rows.append(
                    {
                        "scenario": scenario,
                        "variable": variable,
                        "shock": shock,
                        "impact": float(values[0]),
                        "peak_abs": float(np.max(np.abs(values))),
                        "cumulative_abs_20q": float(np.sum(np.abs(values))),
                        "response_h4": float(values[4]),
                    }
                )
    pd.DataFrame(rows).to_csv(TABLES / "macro_extension_irf_metrics.csv", index=False)
    print("Wrote macro-extension figures and metrics.")


if __name__ == "__main__":
    main()
