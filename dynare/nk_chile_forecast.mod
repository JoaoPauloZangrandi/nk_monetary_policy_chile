// Native Dynare forecast for the calibrated Chilean New Keynesian model.
// Implements the "projections from observed data" workflow: read quarterly
// observables, keep the calibration fixed (no Bayesian estimation), and project
// pi, i and x eight quarters ahead, both unconditionally and under controlled
// interest-rate and inflation paths.
//
// The model is written in pure deviation form (r* drops out), so the steady
// state is x=pi=i=0 and matches the demeaned observables. Three observables and
// three structural shocks => no stochastic singularity.

var x pi i;
varexo e_x e_pi e_i;
parameters beta sigma kappa rho_i phi_pi phi_x;

// Baseline calibration (same values used by the stoch_simul baseline):
beta   = 0.992637536145;   // 1/(1+r*), r* from the 3% annual scenario
sigma  = 1.0;              // log-utility benchmark
kappa  = 0.10;             // Phillips-curve slope
rho_i  = 0.934095195259;   // interest-rate smoothing, AR(1) of the quarterly TPM
phi_pi = 1.75;             // inflation response (Taylor principle satisfied)
phi_x  = 0.50;             // output-gap response

model(linear);
  // IS (expectational), deviation form
  x  = x(+1) - (1/sigma)*(i - pi(+1)) + e_x;
  // New Keynesian Phillips curve
  pi = beta*pi(+1) + kappa*x + e_pi;
  // Taylor rule with interest-rate smoothing
  i  = rho_i*i(-1) + (1-rho_i)*(phi_pi*pi + phi_x*x) + e_i;
end;

steady;
check;

// Calibrated shock sizes (same as the baseline stoch_simul):
shocks;
  var e_x;  stderr 0.005;
  var e_pi; stderr 0.00277;
  var e_i;  stderr 0.00068;
end;

varobs pi i x;

// The three shock standard deviations are declared so the estimation machinery
// has something to "estimate", but mode_compute=0 together with
// estimated_params_init(use_calibration) means nothing is optimised: every
// parameter stays at its calibrated value. The priors below are never used.
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

// Kalman smoother over the history + 8-quarter unconditional forecast, at the
// fixed calibration. forecast=8 fills oo_.forecast.Mean / HPDinf / HPDsup.
estimation(datafile='chile_observables_dynare.csv', mode_compute=0, mh_replic=0,
           smoother, forecast=8, nograph, nodisplay) x pi i;

verbatim;
  export_forecast('forecast');
end;

// ----------------------------------------------------------------------------
// Conditional projections. The controlled exogenous variable is the monetary
// policy shock e_i, which is solved for so that the constrained path is hit.
// Values are in model (deviation) units; the steady state is zero.
// ----------------------------------------------------------------------------

// Scenario 1: hold the policy-rate gap at its last observed level for 2 quarters.
conditional_forecast_paths;
  var i;
  periods 1 2;
  values  0.000988 0.000988;
end;
conditional_forecast(parameter_set=calibration, controlled_varexo=(e_i),
                     periods=8, replic=2000);
verbatim;
  export_conditional('cond_hold_2q');
end;

// Scenario 2: tighten and hold the policy-rate gap ~1 p.p. (annual) above its
// historical mean for 4 quarters.
conditional_forecast_paths;
  var i;
  periods 1 2 3 4;
  values  0.0025 0.0025 0.0025 0.0025;
end;
conditional_forecast(parameter_set=calibration, controlled_varexo=(e_i),
                     periods=8, replic=2000);
verbatim;
  export_conditional('cond_hike_4q');
end;

// Scenario 3: force inflation to the 3% official target for 4 quarters.
// The steady state corresponds to the sample-mean inflation (~3.79% annual), so
// the 3% target maps to a NEGATIVE inflation gap of (1.03)^(1/4)-1 minus the
// mean quarterly inflation = -0.0019233. Imposing this gap is a genuine
// disinflation experiment (not vacuous), enforced through the policy shock e_i.
conditional_forecast_paths;
  var pi;
  periods 1 2 3 4;
  values  -0.0019233 -0.0019233 -0.0019233 -0.0019233;
end;
conditional_forecast(parameter_set=calibration, controlled_varexo=(e_i),
                     periods=8, replic=2000);
verbatim;
  export_conditional('cond_pi_to_target_4q');
end;
