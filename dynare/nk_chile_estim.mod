// Posterior-mode estimation of the minimal New Keynesian model on Chilean data.
// Written in pure deviation form (r* drops out), so the steady state is x=pi=i=0 and
// matches the demeaned observables (pi, i, x are quarterly fractions, mean-zero).
// Three observables and three structural shocks => no stochastic singularity.

var x pi i;
varexo e_x e_pi e_i;
parameters beta sigma kappa rho_i phi_pi phi_x;

beta   = 0.992637536145;   // 1/(1+r*), r* from the 3% annual scenario
sigma  = 1.0;
kappa  = 0.10;
rho_i  = 0.90;
phi_pi = 1.75;
phi_x  = 0.50;

model(linear);
x  = x(+1) - (1/sigma)*(i - pi(+1)) + e_x;
pi = beta*pi(+1) + kappa*x + e_pi;
i  = rho_i*i(-1) + (1-rho_i)*(phi_pi*pi + phi_x*x) + e_i;
end;

steady;

varobs pi i x;

estimated_params;
  sigma,       gamma_pdf,     1.00,  0.40;
  kappa,       gamma_pdf,     0.10,  0.05;
  rho_i,       beta_pdf,      0.80,  0.10;
  phi_pi,      gamma_pdf,     1.50,  0.25;
  phi_x,       gamma_pdf,     0.50,  0.25;
  stderr e_x,  inv_gamma_pdf, 0.005, inf;
  stderr e_pi, inv_gamma_pdf, 0.0025, inf;
  stderr e_i,  inv_gamma_pdf, 0.002, inf;
end;

// Posterior-mode (MAP) estimation: fast and robust in Octave. Standard errors come from
// the mode Hessian (recovered in Python). mh_replic can be raised to add a full MCMC.
estimation(datafile='chile_observables_dynare.csv', mode_compute=4,
           mh_replic=0, plot_priors=0, nograph);

verbatim;
export_bayesian('estimation');
end;
