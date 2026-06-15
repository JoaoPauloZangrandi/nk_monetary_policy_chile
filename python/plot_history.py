"""Phase 1 of the deep macro analysis: historical narrative + policy counterfactual.

Reads the Kalman-smoothed shocks and the Dynare historical shock decomposition
(produced by run_history.py) and answers two macro questions for Chile, 2001-2026:

1. Narrative: which structural shocks (demand, cost-push, monetary) drove the
   observed inflation, output gap and policy rate each quarter?
2. Counterfactual: feeding the same recovered demand and cost-push shocks through
   the model under a MORE HAWKISH Taylor rule, how different would inflation and
   output have been (especially in the 2021-2023 inflation surge)?

The reduced form  y_t = T i_{t-1} + R eps_t  is the exact first-order solution
(identical to Dynare's). Counterfactual = re-solve with new policy parameters and
re-run the same recovered shock sequence.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import (
    DATA_CLEAN,
    DYNARE_OUTPUTS,
    FIGURES,
    TABLES,
    _state_coefficients,
    calibration_rho,
    complete_parameters,
    ensure_directories,
)

HIST = DYNARE_OUTPUTS / "history"
SHOCK_LABELS = {
    "e_x": ("Demand", "#1E4E79"),
    "e_pi": ("Cost-push", "#B45309"),
    "e_i": ("Monetary", "#16A34A"),
    "initial": ("Initial cond.", "#9CA3AF"),
}


def solution_matrices(params: dict) -> tuple[np.ndarray, np.ndarray]:
    a_x, a_pi, a_i = _state_coefficients(params)
    sigma, beta, kappa = params["sigma"], params["beta"], params["kappa"]
    rho_i, phi_pi, phi_x = params["rho_i"], params["phi_pi"], params["phi_x"]
    c_i = a_x - (1.0 - a_pi) / sigma
    structural = np.array(
        [
            [1.0, 0.0, -c_i],
            [-kappa, 1.0, -beta * a_pi],
            [-(1.0 - rho_i) * phi_x, -(1.0 - rho_i) * phi_pi, 1.0],
        ]
    )
    return np.array([a_x, a_pi, a_i]), np.linalg.inv(structural)


def simulate(params: dict, shocks: np.ndarray, i0: float = 0.0) -> np.ndarray:
    transition, impact = solution_matrices(params)
    n = len(shocks)
    out = np.zeros((n, 3))
    prev_i = i0
    for t in range(n):
        out[t] = transition * prev_i + impact @ shocks[t]
        prev_i = out[t, 2]
    return out


def main() -> None:
    ensure_directories()
    params = complete_parameters({"rho_i": calibration_rho()})

    macro = pd.read_csv(DATA_CLEAN / "chile_macro_quarterly.csv")
    dates = macro["date"].tolist()
    n = len(dates)
    decomp = pd.read_csv(HIST / "shock_decomp.csv")
    shocks_df = pd.read_csv(HIST / "smoothed_shocks.csv")

    mean_infl_q = float(macro["infl_q"].mean())
    mean_i_q = float(macro["i_q"].mean())

    # Annualised percentage-point scaling (linear, keeps the decomposition additive).
    scale = {"pi": 400.0, "i": 400.0, "x": 100.0}
    unit = {"pi": "p.p. anual", "i": "p.p. anual", "x": "% do PIB"}
    titlevar = {"pi": "Inflação", "i": "Taxa de política (TPM)", "x": "Hiato do produto"}

    xticks = list(range(0, n, 8))
    xlabels = [dates[t] for t in xticks]

    # ------------------------------------------------------------------ #
    # Figure 1: historical shock decomposition (the macro narrative).    #
    # ------------------------------------------------------------------ #
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    comps = ["e_x", "e_pi", "e_i", "initial"]
    for ax, var in zip(axes, ["pi", "i", "x"]):
        sub = decomp[decomp["variable"] == var].sort_values("period").reset_index(drop=True)
        s = scale[var]
        pos_bottom = np.zeros(n)
        neg_bottom = np.zeros(n)
        xs = np.arange(n)
        for comp in comps:
            vals = sub[comp].to_numpy() * s
            pos = np.where(vals > 0, vals, 0.0)
            neg = np.where(vals < 0, vals, 0.0)
            label, color = SHOCK_LABELS[comp]
            ax.bar(xs, pos, bottom=pos_bottom, color=color, width=0.9,
                   label=label, edgecolor="none")
            ax.bar(xs, neg, bottom=neg_bottom, color=color, width=0.9, edgecolor="none")
            pos_bottom += pos
            neg_bottom += neg
        ax.plot(xs, sub["smoothed"].to_numpy() * s, color="black", linewidth=1.3,
                label="Observado (desvio)")
        ax.axhline(0, color="black", linewidth=0.6)
        ax.set_title(f"{titlevar[var]} — contribuição de cada choque")
        ax.set_ylabel(unit[var])
        ax.grid(alpha=0.2, axis="y")
    axes[0].legend(ncol=5, fontsize=8, loc="upper left")
    axes[-1].set_xticks(xticks)
    axes[-1].set_xticklabels(xlabels, rotation=70, fontsize=7)
    fig.suptitle("Chile: decomposição histórica de choques (modelo NK calibrado, suavizador de Kalman)")
    fig.text(0.01, 0.005, "Desvios da média amostral; escala anualizada linear. "
             "Fonte: BCCh; decomposição do modelo, não identificação histórica oficial.", fontsize=7)
    fig.tight_layout(rect=(0, 0.02, 1, 0.97))
    fig.savefig(FIGURES / "history_shock_decomposition.png", dpi=170)
    plt.close(fig)

    # ------------------------------------------------------------------ #
    # Figure 2: recovered structural shocks over time.                   #
    # ------------------------------------------------------------------ #
    fig, axes = plt.subplots(3, 1, figsize=(12, 7), sharex=True)
    for ax, comp in zip(axes, ["e_x", "e_pi", "e_i"]):
        label, color = SHOCK_LABELS[comp]
        ax.bar(np.arange(n), shocks_df[comp].to_numpy() * 100, color=color, width=0.9)
        ax.axhline(0, color="black", linewidth=0.6)
        ax.set_title(f"{label} shock ({comp})")
        ax.set_ylabel("p.p. trimestral")
        ax.grid(alpha=0.2, axis="y")
    axes[-1].set_xticks(xticks)
    axes[-1].set_xticklabels(xlabels, rotation=70, fontsize=7)
    fig.suptitle("Chile: choques estruturais recuperados pelo suavizador de Kalman")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIGURES / "history_smoothed_shocks.png", dpi=170)
    plt.close(fig)

    # ------------------------------------------------------------------ #
    # Figure 3: policy counterfactual (hawkish rule).                    #
    # ------------------------------------------------------------------ #
    shocks = shocks_df[["e_x", "e_pi", "e_i"]].to_numpy()
    base = simulate(params, shocks)                      # reproduces the data
    hawk_params = complete_parameters({"rho_i": params["rho_i"], "phi_pi": 2.5})
    hawk = simulate(hawk_params, shocks)
    # Validation: base-sim vs observed (deviations), after initial transient.
    obs = pd.read_csv(DATA_CLEAN / "chile_observables.csv")[["x", "pi", "i"]].to_numpy()
    rmse = float(np.sqrt(np.mean((base[15:] - obs[15:]) ** 2)))

    def to_annual_infl(dev):
        return ((1.0 + mean_infl_q + dev) ** 4 - 1.0) * 100.0

    def to_annual_tpm(dev):
        return ((1.0 + mean_i_q + dev) ** 4 - 1.0) * 100.0

    start = max(0, n - 40)  # focus on the last ~10 years
    xs = np.arange(start, n)
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    axes[0].plot(xs, [to_annual_infl(d) for d in base[start:, 1]], color="black",
                 linewidth=2, label="Atual (regra estimada, φπ=1,75)")
    axes[0].plot(xs, [to_annual_infl(d) for d in hawk[start:, 1]], color="#B91C1C",
                 linewidth=2, linestyle="--", label="Contrafactual (φπ=2,5)")
    axes[0].axhline(3.0, color="#B45309", linestyle=":", linewidth=1, label="Meta 3%")
    axes[0].set_title("Inflação (% a.a.)")
    axes[1].plot(xs, 100 * base[start:, 0], color="black", linewidth=2, label="Atual")
    axes[1].plot(xs, 100 * hawk[start:, 0], color="#B91C1C", linewidth=2,
                 linestyle="--", label="Contrafactual (φπ=2,5)")
    axes[1].axhline(0, color="#6B7280", linewidth=0.7)
    axes[1].set_title("Hiato do produto (%)")
    for ax in axes:
        ax.set_xticks(list(range(start, n, 4)))
        ax.set_xticklabels([dates[t] for t in range(start, n, 4)], rotation=70, fontsize=7)
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)
    fig.suptitle("Contrafactual de política: regra mais agressiva contra a inflação "
                 f"(validação base vs dados: RMSE={rmse:.2e})")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(FIGURES / "history_counterfactual.png", dpi=170)
    plt.close(fig)

    # Tidy export of the decomposition (annualised pp) for the report.
    rows = []
    for var in ["pi", "i", "x"]:
        sub = decomp[decomp["variable"] == var].sort_values("period").reset_index(drop=True)
        for t in range(n):
            rows.append({
                "date": dates[t], "variable": var,
                "demand": sub["e_x"][t] * scale[var],
                "cost_push": sub["e_pi"][t] * scale[var],
                "monetary": sub["e_i"][t] * scale[var],
                "initial": sub["initial"][t] * scale[var],
                "observed": sub["smoothed"][t] * scale[var],
            })
    pd.DataFrame(rows).to_csv(TABLES / "history_shock_decomposition.csv", index=False)

    print(f"Counterfactual validation RMSE (base-sim vs data, t>=15): {rmse:.3e}")
    print("Wrote history decomposition, smoothed shocks and counterfactual figures.")


if __name__ == "__main__":
    main()
