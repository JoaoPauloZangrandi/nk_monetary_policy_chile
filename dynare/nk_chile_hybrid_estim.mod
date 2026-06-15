// Posterior-mode estimation of the hybrid-Phillips Chilean NK model.
// This model uses the same observables and common priors as nk_chile_estim.mod,
// adding one estimated indexation parameter gamma_pi. The matched data sample
// makes its marginal likelihood comparable with the forward-looking baseline.

var x pi i;
varexo e_x e_pi e_i;
parameters beta sigma kappa rho_i phi_pi phi_x gamma_pi;

beta     = 0.992637536145;
sigma    = 1.0;
kappa    = 0.10;
rho_i    = 0.90;
phi_pi   = 1.75;
phi_x    = 0.50;
gamma_pi = 0.35;

model(linear);
  x  = x(+1) - (1/sigma)*(i-pi(+1)) + e_x;
  pi = gamma_pi*pi(-1)
       + (1-gamma_pi)*(beta*pi(+1)+kappa*x) + e_pi;
  i  = rho_i*i(-1) + (1-rho_i)*(phi_pi*pi+phi_x*x) + e_i;
end;

steady;
check;
varobs pi i x;

estimated_params;
  sigma,       gamma_pdf,     1.00,  0.40;
  kappa,       gamma_pdf,     0.10,  0.05;
  rho_i,       beta_pdf,      0.80,  0.10;
  phi_pi,      gamma_pdf,     1.50,  0.25;
  phi_x,       gamma_pdf,     0.50,  0.25;
  gamma_pi,    beta_pdf,      0.35,  0.15;
  stderr e_x,  inv_gamma_pdf, 0.005, inf;
  stderr e_pi, inv_gamma_pdf, 0.0025, inf;
  stderr e_i,  inv_gamma_pdf, 0.002, inf;
end;

estimation(datafile='chile_observables_dynare.csv', mode_compute=4,
           mh_replic=0, plot_priors=0, nograph, nodisplay);
