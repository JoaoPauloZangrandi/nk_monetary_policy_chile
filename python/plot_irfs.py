"""Create the three required IRF figures with matplotlib."""

from __future__ import annotations

import json
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import DATA_CLEAN, FIGURES, TABLES, ensure_directories


def load_irfs() -> pd.DataFrame:
    path = TABLES / "irfs_long.csv"
    if not path.exists():
        from collect_outputs import main as collect_main

        collect_main()
    return pd.read_csv(path)


def source_note(frame: pd.DataFrame) -> str:
    sources = sorted(frame["source"].dropna().unique())
    if sources == ["dynare"]:
        return "Source: Dynare"
    return "Source includes clearly labeled synthetic model fallback"


def plot_kappa(irfs: pd.DataFrame) -> None:
    selected = irfs[
        irfs["scenario"].str.startswith("kappa_")
        & (irfs["variable"] == "pi")
        & (irfs["shock"] == "e_x")
    ]
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    for scenario, frame in selected.groupby("scenario"):
        label = scenario.removeprefix("kappa_").replace("p", ".")
        ax.plot(frame["horizon"], 100 * frame["response"], linewidth=2, label=label)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set(
        title="Inflation response to a demand shock: Phillips-slope (kappa) sensitivity",
        xlabel="Quarters",
        ylabel="Percentage points",
    )
    ax.legend(title="kappa")
    ax.grid(alpha=0.25)
    fig.text(0.01, 0.01, source_note(selected), fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIGURES / "irf_kappa_comparison.png", dpi=180)
    plt.close(fig)


def plot_phi_pi(irfs: pd.DataFrame) -> None:
    selected = irfs[
        irfs["scenario"].str.startswith("phi_pi_")
        & (irfs["variable"] == "pi")
        & (irfs["shock"] == "e_pi")
    ]
    scenarios = sorted(selected["scenario"].unique())
    colors = plt.cm.viridis(np.linspace(0.05, 0.95, len(scenarios)))
    fig, ax = plt.subplots(figsize=(8.8, 5.4))
    for color, scenario in zip(colors, scenarios):
        frame = selected[selected["scenario"] == scenario]
        label = scenario.removeprefix("phi_pi_").replace("p", ".")
        ax.plot(
            frame["horizon"],
            100 * frame["response"],
            color=color,
            linewidth=1.6,
            label=label,
        )
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set(
        title="Inflation response to a cost-push shock: Taylor-rule sensitivity",
        xlabel="Quarters",
        ylabel="Percentage points",
    )
    ax.legend(title="phi_pi", ncol=2, fontsize=8)
    ax.grid(alpha=0.25)
    fig.text(0.01, 0.01, source_note(selected), fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIGURES / "irf_phi_pi_comparison.png", dpi=180)
    plt.close(fig)


def plot_baseline(irfs: pd.DataFrame) -> None:
    selected = irfs[irfs["scenario"] == "baseline"]
    variables = ("x", "pi", "i")
    shocks = ("e_x", "e_pi", "e_i")
    labels = {"x": "Output gap", "pi": "Inflation", "i": "Policy rate"}
    shock_labels = {
        "e_x": "Demand shock",
        "e_pi": "Cost-push shock",
        "e_i": "Monetary-policy shock",
    }
    fig, axes = plt.subplots(3, 3, figsize=(11.5, 8.5), sharex=True)
    for row, variable in enumerate(variables):
        for column, shock in enumerate(shocks):
            ax = axes[row, column]
            frame = selected[
                (selected["variable"] == variable) & (selected["shock"] == shock)
            ]
            ax.plot(frame["horizon"], 100 * frame["response"], linewidth=1.8)
            ax.axhline(0, color="black", linewidth=0.7)
            ax.grid(alpha=0.22)
            if row == 0:
                ax.set_title(shock_labels[shock])
            if column == 0:
                ax.set_ylabel(f"{labels[variable]}\npp")
            if row == 2:
                ax.set_xlabel("Quarters")
    fig.suptitle("Baseline impulse responses across all shocks", fontsize=14)
    fig.text(0.01, 0.01, source_note(selected), fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 0.96))
    fig.savefig(FIGURES / "irf_baseline_all_shocks.png", dpi=180)
    plt.close(fig)


def plot_data_overview() -> None:
    path = DATA_CLEAN / "chile_macro_quarterly.csv"
    if not path.exists():
        return
    df = pd.read_csv(path)
    metadata_path = DATA_CLEAN / "dataset_metadata.json"
    metadata = (
        json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata_path.exists()
        else {"is_synthetic": True}
    )
    is_synthetic = bool(metadata.get("is_synthetic", True))
    source = (
        "Banco Central de Chile (TPM, IPC, PIB)"
        if not is_synthetic
        else "Synthetic fallback for pipeline testing"
    )
    fig, axes = plt.subplots(3, 1, figsize=(9, 8.2), sharex=True)
    axes[0].plot(df["date"], df["tpm_annual_pct"], color="#1E4E79")
    axes[0].set_ylabel("TPM (% a.a.)")
    axes[1].plot(df["date"], df["infl_annual_pct"], color="#FF6B35")
    axes[1].axhline(3.0, color="gray", ls="--", lw=0.8)
    axes[1].set_ylabel("Inflacao IPC (% a.a.)")
    axes[2].plot(df["date"], 100.0 * df["output_gap"], color="#16a34a")
    axes[2].axhline(0.0, color="black", lw=0.7)
    axes[2].set_ylabel("Hiato (%)")
    for ax in axes:
        ax.grid(alpha=0.25)
    step = max(1, len(df) // 12)
    axes[2].set_xticks(df["date"][::step])
    axes[2].tick_params(axis="x", rotation=90, labelsize=7)
    title_kind = "official quarterly data" if not is_synthetic else "synthetic test data"
    axes[0].set_title(f"Chile: {title_kind} - policy rate, inflation, output gap")
    fig.text(
        0.01,
        0.005,
        f"Source: {source}; output gap = HP cycle of log real GDP.",
        fontsize=7,
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIGURES / "data_overview.png", dpi=180)
    plt.close(fig)


def main() -> None:
    ensure_directories()
    plot_data_overview()
    irfs = load_irfs()
    plot_kappa(irfs)
    plot_phi_pi(irfs)
    plot_baseline(irfs)
    print(f"Wrote IRF figures to {FIGURES}")


if __name__ == "__main__":
    main()
