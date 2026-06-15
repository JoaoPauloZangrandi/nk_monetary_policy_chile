// Historical analysis of the calibrated Chilean New Keynesian model.
// Runs the Kalman smoother over 2001Q1-2026Q1 at the fixed calibration and
// asks the macro-narrative question: which structural shocks (demand,
// cost-push, monetary) actually drove inflation, the output gap and the policy
// rate over the sample? Uses Dynare's shock_decomposition, plus the smoothed
// structural shock series. Same deviation-form model as the forecast file.

var x pi i;
varexo e_x e_pi e_i;
parameters beta sigma kappa rho_i phi_pi phi_x;

beta   = 0.992637536145;
sigma  = 1.0;
kappa  = 0.10;
rho_i  = 0.934095195259;
phi_pi = 1.75;
phi_x  = 0.50;

model(linear);
  x  = x(+1) - (1/sigma)*(i - pi(+1)) + e_x;
  pi = beta*pi(+1) + kappa*x + e_pi;
  i  = rho_i*i(-1) + (1-rho_i)*(phi_pi*pi + phi_x*x) + e_i;
end;

steady;
check;

shocks;
  var e_x;  stderr 0.005;
  var e_pi; stderr 0.00277;
  var e_i;  stderr 0.00068;
end;

varobs pi i x;

estimated_params;
  stderr e_x,  inv_gamma_pdf, 0.005,   inf;
  stderr e_pi, inv_gamma_pdf, 0.00277, inf;
  stderr e_i,  inv_gamma_pdf, 0.00068, inf;
end;

estimated_params_init(use_calibration);
  stderr e_x,  0.005;
  stderr e_pi, 0.00277;
  stderr e_i,  0.00068;
end;

// Kalman smoother at the fixed calibration (no estimation).
estimation(datafile='chile_observables_dynare.csv', mode_compute=0, mh_replic=0,
           smoother, nograph, nodisplay) x pi i;

// Historical decomposition: contribution of each shock to each variable.
shock_decomposition(parameter_set=calibration, nograph) pi i x;

verbatim;
  export_history('history');
end;
