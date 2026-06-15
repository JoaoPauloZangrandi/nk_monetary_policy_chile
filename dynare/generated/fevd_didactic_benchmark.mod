// Auto-generated scenario: fevd_didactic_benchmark
var x pi i;
varexo e_x e_pi e_i;
parameters beta sigma kappa rho_i phi_pi phi_x rstar;

beta = 0.992637536145;
sigma = 1;
kappa = 0.1;
rho_i = 0.934095195259;
phi_pi = 1.75;
phi_x = 0.5;
rstar = 0.00741707177773;

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
var e_x;  stderr 0.005;
var e_pi; stderr 0.00330833237973;
var e_i;  stderr 0.0007998211036;
end;

steady;
check;
verbatim;
export_stability('fevd_didactic_benchmark');
end;
stoch_simul(order=1, irf=20);
verbatim;
export_results('fevd_didactic_benchmark');
end;
