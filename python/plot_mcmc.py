"""Plot Bayesian posterior summaries and convergence diagnostics."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import FIGURES, TABLES


LABELS = {
    "stderr e_x": r"$\sigma_{e_x}$",
    "stderr e_pi": r"$\sigma_{e_\pi}$",
    "stderr e_i": r"$\sigma_{e_i}$",
    "sigma": r"$\sigma$",
    "kappa": r"$\kappa$",
    "rho_i": r"$\rho_i$",
    "phi_pi": r"$\phi_\pi$",
    "phi_x": r"$\phi_x$",
}


def main() -> None:
    posterior = pd.read_csv(TABLES / "mcmc_posterior.csv")
    diagnostics = pd.read_csv(TABLES / "mcmc_diagnostics.csv")
    merged = posterior.merge(diagnostics, on="parameter", validate="one_to_one")

    y = np.arange(len(merged))
    means = merged["posterior_mean"].to_numpy()
    low = merged["hpd90_low"].to_numpy()
    high = merged["hpd90_high"].to_numpy()

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.8))
    axes[0].errorbar(
        means,
        y,
        xerr=np.vstack([means - low, high - means]),
        fmt="o",
        color="#145DA0",
        ecolor="#72A0C1",
        capsize=3,
    )
    axes[0].set_yticks(y, [LABELS.get(p, p) for p in merged["parameter"]])
    axes[0].invert_yaxis()
    axes[0].set_title("Posterior mean and 90% credible interval")
    axes[0].set_xlabel("Parameter value")
    axes[0].grid(axis="x", alpha=0.25)

    colors = np.where(merged["rhat"] < 1.05, "#2E8B57", "#C0392B")
    axes[1].barh(y, merged["rhat"] - 1.0, left=1.0, color=colors)
    axes[1].axvline(1.05, color="#333333", linestyle="--", linewidth=1)
    axes[1].set_yticks(y, [LABELS.get(p, p) for p in merged["parameter"]])
    axes[1].invert_yaxis()
    axes[1].set_xlim(0.99, max(1.08, merged["rhat"].max() * 1.02))
    axes[1].set_title(r"Convergence diagnostic ($\hat R$)")
    axes[1].set_xlabel(r"$\hat R$; values below 1.05 are preferred")
    axes[1].grid(axis="x", alpha=0.25)

    fig.suptitle("Bayesian MCMC extension: posterior uncertainty and convergence")
    fig.text(
        0.5,
        0.01,
        "Two Dynare chains; 10,000 proposals each; first 30% discarded. "
        "Results are model- and prior-conditional.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    target = FIGURES / "mcmc_posterior_diagnostics.png"
    fig.savefig(target, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()
