"""Map Blanchard-Kahn determinacy and convergence speed against phi_pi.

The assignment's phi_pi grid (1.3-2.2) is entirely determinate, so a verbal "phi_pi>1"
rule is not enough. Here we sweep phi_pi (including values below 1) and, for each, count
the eigenvalues inside the unit circle from the model's characteristic cubic. With one
predetermined variable the model is determinate iff exactly one root is stable. We also
record the largest stable-root modulus, which governs how fast the economy converges
after a shock. This complements (and is cross-checked by) Dynare's per-scenario check.

Outputs: outputs/tables/determinacy_map.csv and outputs/figures/determinacy_map.png.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import (
    FIGURES,
    TABLES,
    calibration_rho,
    characteristic_roots,
    complete_parameters,
    ensure_directories,
)


def main() -> None:
    ensure_directories()
    rho_i = calibration_rho()
    grid = np.round(np.arange(0.5, 3.0001, 0.05), 2)
    rows = []
    for phi_pi in grid:
        params = complete_parameters({"rho_i": rho_i, "phi_pi": float(phi_pi)})
        roots = characteristic_roots(params)
        moduli = np.abs(roots)
        n_stable = int(np.sum(moduli < 1.0 - 1e-9))
        stable_moduli = moduli[moduli < 1.0 - 1e-9]
        dominant = float(stable_moduli.max()) if stable_moduli.size else np.nan
        rows.append(
            {
                "phi_pi": float(phi_pi),
                "n_stable_roots": n_stable,
                "n_unstable_roots": int(np.sum(moduli > 1.0 + 1e-9)),
                "determinate": n_stable == 1,
                "dominant_stable_modulus": dominant,
            }
        )
    table = pd.DataFrame(rows)
    table.to_csv(TABLES / "determinacy_map.csv", index=False)

    threshold = table.loc[table["determinate"], "phi_pi"].min()

    fig, ax1 = plt.subplots(figsize=(8.8, 5.0))
    colors = ["#16a34a" if d else "#b91c1c" for d in table["determinate"]]
    ax1.bar(table["phi_pi"], table["n_stable_roots"], width=0.045, color=colors, alpha=0.65)
    ax1.axhline(1.0, color="black", lw=0.8, ls=":")
    ax1.set_xlabel("phi_pi (Taylor-rule inflation response, phi_x = 0.5)")
    ax1.set_ylabel("Number of stable eigenvalues")
    ax1.set_ylim(0, 3.2)
    ax2 = ax1.twinx()
    ax2.plot(table["phi_pi"], table["dominant_stable_modulus"], color="#1E4E79",
             lw=2, marker="o", ms=3, label="Dominant stable |eigenvalue|")
    ax2.set_ylabel("Dominant stable |eigenvalue| (persistence)")
    ax1.axvline(1.0, color="gray", lw=1, ls="--")
    ax1.set_title(
        f"Determinacy and convergence vs phi_pi (rho_i={rho_i:.2f}); "
        f"determinate for phi_pi >= {threshold:.2f}"
    )
    ax2.legend(loc="upper right", fontsize=8)
    fig.text(0.01, 0.01, "Green = determinate (1 stable root); red = indeterminate/explosive. "
             "Source: characteristic roots of the calibrated model (cross-checked with Dynare).",
             fontsize=7)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIGURES / "determinacy_map.png", dpi=180)
    plt.close(fig)

    print(table.to_string(index=False))
    print(f"Determinate for phi_pi >= {threshold:.2f}")
    print(f"Wrote {TABLES / 'determinacy_map.csv'} and {FIGURES / 'determinacy_map.png'}")


if __name__ == "__main__":
    main()
