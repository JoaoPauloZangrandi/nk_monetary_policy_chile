# Model notes

## Variables and shocks

`x` is the output gap, `pi` is quarterly inflation, and `i` is the quarterly
nominal policy rate. The exogenous innovations are a demand shock `e_x`, a
cost-push shock `e_pi`, and a monetary-policy shock `e_i`.

## Equations

The IS equation makes current demand depend positively on its expected future
level and negatively on the ex ante real interest-rate gap. The Phillips curve
links inflation to expected inflation and economic slack. The Taylor rule
introduces interest-rate smoothing and systematic reactions to inflation and
the output gap.

## Calibration

| Parameter | Baseline | Interpretation |
|---|---:|---|
| `rstar_annual` | 0.03 | Annual neutral real rate assumption |
| `rstar` | `(1.03)^(1/4)-1` | Quarterly neutral real rate |
| `beta` | `1/(1+rstar)` | Discount factor consistent with `rstar` |
| `sigma` | 1.00 | Inverse intertemporal-substitution parameter |
| `kappa` | 0.10 | Phillips-curve slope |
| `rho_i` | estimated; 0.80 fallback | Policy-rate persistence |
| `phi_pi` | 1.75 | Taylor-rule inflation response |
| `phi_x` | 0.50 | Taylor-rule output-gap response |

The current real-data run uses shock standard deviations of 0.00500 for demand,
0.00277 for cost-push, and 0.00068 for monetary policy. They are chosen against
an illustrative model-based FEVD target. They are not empirical shock estimates
and do not reproduce an official BCCh decomposition.

## Steady state

With no shocks, the model has `x = 0`, `pi = 0`, and `i = rstar`. Dynare is
given this initial steady-state candidate before `steady;` and `check;`.

## Sensitivity design

- Annual `rstar`: 2%, 3%, and 4%.
- `kappa`: 0.07, 0.10, and 0.13.
- `phi_pi`: 1.3, 1.4, ..., 2.2 with `phi_x = 0.5`.
- Horizon: 20 quarters.

Dynare's generalized eigenvalue check is the primary determinacy diagnostic.
The Python fallback is a pipeline test and must not replace that diagnostic in
the substantive interpretation.
