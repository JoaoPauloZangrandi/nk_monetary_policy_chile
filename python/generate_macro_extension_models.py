"""Generate Dynare files for the open-economy and hybrid-NKPC extensions."""

from __future__ import annotations

import pandas as pd

from common import ROOT, SHOCK_STD, TABLES, calibration_rho, complete_parameters


OPEN_TEMPLATE = """// Illustrative small-open-economy extension for Chile.
var x pi i q copper;
varexo e_x e_pi e_i e_q e_copper;
parameters beta sigma kappa rho_i phi_pi phi_x alpha_q alpha_copper
           gamma_q eta_i phi_q rho_copper;

beta = {beta:.12g};
sigma = {sigma:.12g};
kappa = {kappa:.12g};
rho_i = {rho_i:.12g};
phi_pi = {phi_pi:.12g};
phi_x = {phi_x:.12g};
alpha_q = {alpha_q:.12g};
alpha_copper = {alpha_copper:.12g};
gamma_q = {gamma_q:.12g};
eta_i = {eta_i:.12g};
phi_q = {phi_q:.12g};
rho_copper = {rho_copper:.12g};

model(linear);
  // Domestic demand: real rate, competitiveness and copper-income channel.
  x = x(+1) - (1/sigma)*(i-pi(+1)) + alpha_q*q + alpha_copper*copper + e_x;
  // Domestic inflation with direct exchange-rate pass-through.
  pi = beta*pi(+1) + kappa*x + gamma_q*q + e_pi;
  // Taylor rule may lean mildly against depreciation.
  i = rho_i*i(-1) + (1-rho_i)*(phi_pi*pi + phi_x*x + phi_q*q) + e_i;
  // UIP-style exchange-rate equation; q>0 means a weaker peso.
  q = q(+1) - eta_i*i + e_q;
  // Exogenous persistent copper-price gap.
  copper = rho_copper*copper(-1) + e_copper;
end;

steady;
check;
verbatim;
  export_stability('open_economy');
end;

shocks;
  var e_x; stderr {std_e_x:.12g};
  var e_pi; stderr {std_e_pi:.12g};
  var e_i; stderr {std_e_i:.12g};
  var e_q; stderr {std_e_q:.12g};
  var e_copper; stderr {std_e_copper:.12g};
end;

stoch_simul(order=1, irf=20, nograph);
verbatim;
  export_extension('open_economy');
end;
"""


HYBRID_TEMPLATE = """// Hybrid Phillips-curve extension with intrinsic inflation persistence.
var x pi i;
varexo e_x e_pi e_i;
parameters beta sigma kappa rho_i phi_pi phi_x gamma_pi;

beta = {beta:.12g};
sigma = {sigma:.12g};
kappa = {kappa:.12g};
rho_i = {rho_i:.12g};
phi_pi = {phi_pi:.12g};
phi_x = {phi_x:.12g};
gamma_pi = {gamma_pi:.12g};

model(linear);
  x = x(+1) - (1/sigma)*(i-pi(+1)) + e_x;
  pi = gamma_pi*pi(-1) + (1-gamma_pi)*(beta*pi(+1)+kappa*x) + e_pi;
  i = rho_i*i(-1) + (1-rho_i)*(phi_pi*pi+phi_x*x) + e_i;
end;

steady;
check;
verbatim;
  export_stability('hybrid_nkpc');
end;

shocks;
  var e_x; stderr {std_e_x:.12g};
  var e_pi; stderr {std_e_pi:.12g};
  var e_i; stderr {std_e_i:.12g};
end;

stoch_simul(order=1, irf=20, nograph);
verbatim;
  export_extension('hybrid_nkpc');
end;
"""


def main() -> None:
    params = complete_parameters({"rho_i": calibration_rho()})
    calibration_path = TABLES / "open_economy_calibration.csv"
    if calibration_path.exists():
        open_cal = pd.read_csv(calibration_path).iloc[0].to_dict()
    else:
        open_cal = {
            "rho_copper": 0.75,
            "std_e_copper": 0.08,
            "std_e_fx": 0.04,
            "alpha_q_is": 0.05,
            "alpha_copper_is": 0.03,
            "gamma_q_phillips": 0.03,
            "eta_i_uip": 1.0,
            "phi_q_taylor": 0.05,
        }
    open_values = {
        **params,
        "alpha_q": float(open_cal["alpha_q_is"]),
        "alpha_copper": float(open_cal["alpha_copper_is"]),
        "gamma_q": float(open_cal["gamma_q_phillips"]),
        "eta_i": float(open_cal["eta_i_uip"]),
        "phi_q": float(open_cal["phi_q_taylor"]),
        "rho_copper": float(open_cal["rho_copper"]),
        "std_e_x": SHOCK_STD["e_x"],
        "std_e_pi": SHOCK_STD["e_pi"],
        "std_e_i": SHOCK_STD["e_i"],
        "std_e_q": float(open_cal["std_e_fx"]),
        "std_e_copper": float(open_cal["std_e_copper"]),
    }
    (ROOT / "dynare" / "nk_chile_open.mod").write_text(
        OPEN_TEMPLATE.format(**open_values), encoding="ascii"
    )

    # Backward OLS estimate is around 0.34; use 0.35 as an illustrative
    # intrinsic-persistence share, not as a structural estimate of indexation.
    hybrid_values = {
        **params,
        "gamma_pi": 0.35,
        "std_e_x": SHOCK_STD["e_x"],
        "std_e_pi": SHOCK_STD["e_pi"],
        "std_e_i": SHOCK_STD["e_i"],
    }
    (ROOT / "dynare" / "nk_chile_hybrid.mod").write_text(
        HYBRID_TEMPLATE.format(**hybrid_values), encoding="ascii"
    )
    pd.DataFrame(
        [
            {"scenario": "open_economy", **open_values},
            {"scenario": "hybrid_nkpc", **hybrid_values},
        ]
    ).to_csv(TABLES / "macro_extension_calibration.csv", index=False)
    print("Generated nk_chile_open.mod and nk_chile_hybrid.mod")


if __name__ == "__main__":
    main()
