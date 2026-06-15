"""Generate Dynare sensitivity models from the baseline specification."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from common import (
    BASELINE,
    ROOT,
    SHOCK_STD,
    TABLES,
    calibration_rho,
    complete_parameters,
    course_benchmark_shock_std,
    ensure_directories,
)

TEMPLATE = """// Auto-generated scenario: {scenario}
var x pi i;
varexo e_x e_pi e_i;
parameters beta sigma kappa rho_i phi_pi phi_x rstar;

beta = {beta:.12g};
sigma = {sigma:.12g};
kappa = {kappa:.12g};
rho_i = {rho_i:.12g};
phi_pi = {phi_pi:.12g};
phi_x = {phi_x:.12g};
rstar = {rstar:.12g};

model(linear);
x  = x(+1) - (1/sigma)*(i - pi(+1) - rstar) + e_x;
pi = beta*pi(+1) + kappa*x + e_pi;
i  = rho_i*i(-1) + (1-rho_i)*(rstar + phi_pi*pi + phi_x*x) + e_i;
end;

initval;
x = 0;
pi = 0;
i = rstar;
end;

shocks;
var e_x;  stderr {std_e_x:.12g};
var e_pi; stderr {std_e_pi:.12g};
var e_i;  stderr {std_e_i:.12g};
end;

steady;
check;
verbatim;
export_stability('{scenario}');
end;
stoch_simul(order=1, irf=20);
verbatim;
export_results('{scenario}');
end;
"""


def scenario_name(prefix: str, value: float, digits: int = 2) -> str:
    text = f"{value:.{digits}f}".replace(".", "p")
    return f"{prefix}_{text}"


def main() -> None:
    ensure_directories()
    generated = ROOT / "dynare" / "generated"
    generated.mkdir(parents=True, exist_ok=True)

    rho_i = calibration_rho()
    baseline_shocks = {
        "std_e_x": SHOCK_STD["e_x"],
        "std_e_pi": SHOCK_STD["e_pi"],
        "std_e_i": SHOCK_STD["e_i"],
    }

    # Regenerate the baseline .mod so it stays consistent with the estimated rho_i
    # and the current shock calibration (single source of truth for the baseline).
    baseline_params = complete_parameters({"rho_i": rho_i})
    (ROOT / "dynare" / "nk_chile_base.mod").write_text(
        TEMPLATE.format(
            scenario="baseline",
            **baseline_shocks,
            **baseline_params,
        ),
        encoding="ascii",
    )

    scenarios: list[dict] = []
    for annual in (0.02, 0.03, 0.04):
        params = complete_parameters({"rstar_annual": annual, "rho_i": rho_i})
        scenarios.append(
            {
                "scenario": scenario_name("rstar", annual * 100, 0),
                "scenario_type": "rstar",
                **baseline_shocks,
                **params,
            }
        )
    for kappa in (0.07, 0.10, 0.13):
        params = complete_parameters({"kappa": kappa, "rho_i": rho_i})
        scenarios.append(
            {
                "scenario": scenario_name("kappa", kappa, 2),
                "scenario_type": "kappa",
                **baseline_shocks,
                **params,
            }
        )
    for phi_pi in [round(value, 1) for value in
                   [1.3 + 0.1 * index for index in range(10)]]:
        params = complete_parameters({"phi_pi": phi_pi, "rho_i": rho_i})
        scenarios.append(
            {
                "scenario": scenario_name("phi_pi", phi_pi, 1),
                "scenario_type": "phi_pi",
                **baseline_shocks,
                **params,
            }
        )

    # "Calibrate or estimate rho_i": retain the empirical baseline and add the
    # lecture-style calibrated route as a clean one-parameter robustness case.
    scenarios.append(
        {
            "scenario": "rho_calibrated_0p80",
            "scenario_type": "rho_i",
            **baseline_shocks,
            **complete_parameters({"rho_i": BASELINE["rho_i"]}),
        }
    )

    # Alternative shock calibration fitted to the didactic FEVD benchmark,
    # holding all structural parameters at the Chilean empirical baseline.
    benchmark_shocks = course_benchmark_shock_std()
    scenarios.append(
        {
            "scenario": "fevd_didactic_benchmark",
            "scenario_type": "fevd",
            "std_e_x": benchmark_shocks["e_x"],
            "std_e_pi": benchmark_shocks["e_pi"],
            "std_e_i": benchmark_shocks["e_i"],
            **baseline_params,
        }
    )

    for row in scenarios:
        content = TEMPLATE.format(**row)
        (generated / f"{row['scenario']}.mod").write_text(
            content, encoding="ascii"
        )

    expected_models = {f"{row['scenario']}.mod" for row in scenarios}
    for old_model in generated.glob("*.mod"):
        if old_model.name not in expected_models:
            try:
                old_model.unlink()
            except PermissionError:
                print(
                    f"Warning: OneDrive locked obsolete model {old_model.name}; "
                    "remove it manually before publishing."
                )

    manifest_columns = [
        "scenario",
        "scenario_type",
        "rstar_annual",
        "rstar",
        "beta",
        "sigma",
        "kappa",
        "rho_i",
        "phi_pi",
        "phi_x",
        "std_e_x",
        "std_e_pi",
        "std_e_i",
    ]
    pd.DataFrame(scenarios)[manifest_columns].to_csv(
        TABLES / "scenario_manifest.csv", index=False
    )
    print(f"Generated {len(scenarios)} models in {generated}")


if __name__ == "__main__":
    main()
