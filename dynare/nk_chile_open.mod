// Illustrative small-open-economy extension for Chile.
var x pi i q copper;
varexo e_x e_pi e_i e_q e_copper;
parameters beta sigma kappa rho_i phi_pi phi_x alpha_q alpha_copper
           gamma_q eta_i phi_q rho_copper;

beta = 0.992637536145;
sigma = 1;
kappa = 0.1;
rho_i = 0.934095195259;
phi_pi = 1.75;
phi_x = 0.5;
alpha_q = 0.05;
alpha_copper = 0.03;
gamma_q = 0.03;
eta_i = 1;
phi_q = 0.05;
rho_copper = 0.941182126643;

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
  var e_x; stderr 0.005;
  var e_pi; stderr 0.00277;
  var e_i; stderr 0.00068;
  var e_q; stderr 0.0460980810142;
  var e_copper; stderr 0.12;
end;

stoch_simul(order=1, irf=20, nograph);
verbatim;
  export_extension('open_economy');
end;
