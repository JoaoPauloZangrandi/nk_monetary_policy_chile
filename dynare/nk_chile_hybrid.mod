// Hybrid Phillips-curve extension with intrinsic inflation persistence.
var x pi i;
varexo e_x e_pi e_i;
parameters beta sigma kappa rho_i phi_pi phi_x gamma_pi;

beta = 0.992637536145;
sigma = 1;
kappa = 0.1;
rho_i = 0.934095195259;
phi_pi = 1.75;
phi_x = 0.5;
gamma_pi = 0.35;

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
  var e_x; stderr 0.005;
  var e_pi; stderr 0.00277;
  var e_i; stderr 0.00068;
end;

stoch_simul(order=1, irf=20, nograph);
verbatim;
  export_extension('hybrid_nkpc');
end;
