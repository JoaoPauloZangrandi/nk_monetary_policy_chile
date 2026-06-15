// Full Bayesian MCMC extension of the minimal Chilean NK model.
var x pi i;
varexo e_x e_pi e_i;
parameters beta sigma kappa rho_i phi_pi phi_x;

beta   = 0.992637536145;
sigma  = 1.0;
kappa  = 0.10;
rho_i  = 0.90;
phi_pi = 1.75;
phi_x  = 0.50;

model(linear);
  x  = x(+1) - (1/sigma)*(i-pi(+1)) + e_x;
  pi = beta*pi(+1) + kappa*x + e_pi;
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
  stderr e_x,  inv_gamma_pdf, 0.005, inf;
  stderr e_pi, inv_gamma_pdf, 0.0025, inf;
  stderr e_i,  inv_gamma_pdf, 0.002, inf;
end;

// Two independent chains. Ten thousand retained proposals per chain are enough
// for a serious course extension, but convergence is assessed rather than assumed.
estimation(datafile='chile_observables_dynare.csv', mode_compute=4,
           mh_replic=10000, mh_nblocks=2, mh_drop=0.30, mh_jscale=0.30,
           mh_conf_sig=0.90, plot_priors=0, nograph, nodisplay);

verbatim;
  export_mcmc('mcmc');
end;
