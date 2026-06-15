# New Keynesian Monetary Policy - Chile

Public, reproducible final-assignment project implementing a minimal
three-equation New Keynesian model for **Chile**. It uses official Banco Central
de Chile (BCCh) data when credentials are available, solves the model with
**Octave + Dynare**, and uses **Python** for data preparation, econometrics,
tables, figures, and exploratory scenarios. The written report is in
`report/relatorio_final.md` (Portuguese). The evaluator-facing, self-contained
deliverable is **`Entrega Final.html`**.

## Public repository and private material

Private course PDFs and supporting files are intentionally excluded. They must
remain only in:

```text
C:\Users\joaoz\OneDrive\Documentos\AI-OS Joao\02_Areas\FGV EESP\Política Monetária\_private_course_pdfs
```

The repository ignores `_private_course_pdfs/` and all PDFs. No private course
text, figures, tables, or benchmark outputs are included.

## Model

Quarterly model in output gap `x`, inflation `pi`, nominal policy rate `i`:

```text
x_t  = E_t[x_{t+1}] - (1/sigma)(i_t - E_t[pi_{t+1}] - rstar) + e_x,t      (IS curve)
pi_t = beta*E_t[pi_{t+1}] + kappa*x_t + e_pi,t                            (NK Phillips curve)
i_t  = rho_i*i_{t-1} + (1-rho_i)(rstar + phi_pi*pi_t + phi_x*x_t) + e_i,t (smoothed Taylor rule)
```

Current baseline calibration: `sigma=1`, `kappa=0.10`, **`rho_i=0.934` (estimated)**, `phi_pi=1.75`,
`phi_x=0.50`, annual `rstar=3%` → `rstar_q=(1.03)^(1/4)-1=0.00742`, `beta=1/(1+rstar_q)=0.99264`.
Shock standard deviations are calibrated to an explicitly **illustrative**
variance-share target (`sigma_ex=0.00500`, `sigma_epi=0.00277`,
`sigma_ei=0.00068`; see `python/calibrate_shocks.py`). This target is a
modelling choice, not a historical BCCh decomposition.

## Software

- Python 3.10+ with `numpy`, `pandas`, `statsmodels`, `scipy`, `matplotlib` (`requirements.txt`).
- GNU Octave (tested 11.1) and Dynare configured for Octave (tested 7.1). This project does **not**
  install them. Override autodetection with environment variables if needed:

```powershell
$env:OCTAVE_BIN   = 'C:\Program Files\GNU Octave\Octave-11.1.0\mingw64\bin\octave-cli.exe'
$env:DYNARE_MATLAB = 'C:\dynare\7.1\matlab'
```

## Data and credentials (Banco Central de Chile)

`python/build_chile_dataset.py` downloads three series from the BCCh statistics REST API
(SieteRestWS): the TPM policy rate (`F022.TPM.TIN.D001.NO.Z.D`), CPI monthly variation
(`F074.IPC.VAR.Z.Z.C.M`) and real seasonally-adjusted GDP (`F032.PIB.FLU.R.CLP.EP18.Z.Z.1.T`), and
builds a quarterly panel, model-unit observables, and full provenance in
`data/clean/dataset_metadata.json`.

Official references:

- [BCCh monetary-policy framework](https://www.bcentral.cl/web/banco-central/areas/politica-monetaria)
- [BCCh Statistical Database](https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_TASA_INTERES/MN_TASA_INTERES_09/TPM_C1)
- [BCCh conditions of use](https://www.bcentral.cl/web/banco-central/condiciones-de-uso)

The BCCh API requires a free account (register at <https://si3.bcentral.cl/Siete>). Provide the
credentials **without committing them** in either of two ways:

```powershell
# Option A: environment variables (persist with setx and open a new shell)
$env:BCCH_USER = 'your_email'; $env:BCCH_PASS = 'your_password'
# Option B: a local, git-ignored file  data/raw/bcch_credentials.json
#   {"user": "your_email", "pass": "your_password"}
```

`data/raw/` is git-ignored (only `.gitkeep` is tracked) and credential files are excluded by
`.gitignore`. Downloaded clean CSVs are also excluded from Git to avoid
redistributing the source database; the provenance JSON, analysis tables, and
figures remain public. If no credentials are found the script falls back to a
**clearly labelled synthetic** panel for pipeline testing only, never presented
as Chilean evidence.

## Reproduce from scratch

Run from the repository root, after providing BCCh credentials:

```powershell
python -m pip install -r requirements.txt

python python/build_chile_dataset.py      # real BCCh data -> data/clean/
python python/estimate_rhoi_chile.py      # AR(1) persistence rho_i (HAC)
python python/estimate_taylor_rule.py     # reduced-form Taylor rule (OLS + IV/2SLS)
python python/estimate_nkpc.py            # Phillips-curve slope kappa (OLS + IV)
python python/estimate_rstar.py           # empirical r* anchors
python python/calibrate_shocks.py         # shock sigmas for an illustrative FEVD target
python python/make_tables.py              # parameter<->target and r*/beta tables
python python/generate_dynare_models.py   # regenerate baseline + 18 scenarios + manifest
python python/run_dynare_batch.py --all   # Dynare: baseline + scenarios (omit --all for baseline only)
python python/run_bayesian.py             # optional posterior-mode DSGE exercise
python python/collect_outputs.py          # aggregate IRFs/moments/FEVD/determinacy
python python/analyze_determinacy.py      # determinacy map vs phi_pi
python python/analyze_model_results.py    # moments, correlations, signs and transition coefficients
python python/run_forecast.py             # NATIVE Dynare forecast=8 + conditional_forecast (pages 48-55)
python python/forecast_model.py           # level fan chart + current-state-anchored scenario figures
python python/plot_irfs.py                # figures

# Deep macro extensions (optional, but included in the final deliverables)
python python/run_history.py               # smoother + historical decomposition
python python/plot_history.py              # narrative + policy counterfactual
python python/analyze_svar.py              # recursive SVAR versus DSGE
python python/estimate_time_varying_rstar.py
python python/evaluate_forecasts.py        # pseudo-out-of-sample comparison
python python/build_open_economy_dataset.py
python python/generate_macro_extension_models.py
python python/run_macro_extensions.py      # open economy + hybrid NKPC
python python/analyze_macro_extensions.py
python python/run_mcmc.py                  # slow: two full Dynare chains
python python/plot_mcmc.py
python python/compare_bayesian_models.py --reuse-baseline

python python/build_final_html.py         # self-contained Entrega Final.html
```

The full MCMC is intentionally not part of the routine fast pipeline. The
published tables use two completed 10,000-draw Dynare chains with a 30% burn-in.
`run_mcmc.py --recover-dir <dynare-work-directory>` can post-process completed
chain files without rerunning Dynare.

## How the Dynare runner avoids OneDrive problems

Dynare's preprocessor creates and renames `+model` folders; inside a OneDrive-synced, accented path
this can lock files or hang. `python/run_dynare_batch.py` therefore **stages** the `.mod` files, the
export helpers and `dynare/run_models.m` into a disposable **ASCII** temp directory (copying from the
accented source in Python, which is reliable), runs Octave entirely there with `NK_REPO_ROOT` pointing
to it, and copies the resulting CSVs back into `outputs/dynare/`. A hard timeout terminates the Octave
process tree (baseline default 150 s; `--all` default 600 s). `python/run_bayesian.py` uses the same
staging approach for the estimation.

If a previous run leaves a stalled `octave-cli`/`run_dynare_batch.py` process, kill it before
re-running (`Get-Process | Where-Object { $_.ProcessName -match 'octave|python' }`). Concurrent runs
must be avoided because they share the temp work directory.

## Troubleshooting

**Octave not found.** Set `OCTAVE_BIN` to the full path of `octave-cli.exe`, for example:
`$env:OCTAVE_BIN='C:\Program Files\GNU Octave\Octave-11.1.0\mingw64\bin\octave-cli.exe'`.

**Dynare is undefined in Octave.** Set `DYNARE_MATLAB` to Dynare's `matlab` directory, for example:
`$env:DYNARE_MATLAB='C:\dynare\7.1\matlab'`.

**Permission denied or locked folders under OneDrive.** Use `python/run_dynare_batch.py`; it stages
the run in a temporary ASCII-only path. Do not run the same batch concurrently.

**A Dynare run reaches the timeout.** Confirm that no stale `octave-cli` process remains, then rerun
the baseline before the full batch. Increase `--timeout` only after checking the log.

**No BCCh credentials are available.** The dataset builder creates an explicitly labelled synthetic
panel for pipeline testing. Synthetic results must not be described as empirical evidence for Chile.

## Bayesian extensions

`dynare/nk_chile_estim.mod` writes the model in deviation form and estimates a
posterior mode (MAP). Reported uncertainty uses a local Laplace approximation
from the mode Hessian. This is an exploratory extension, not a full MCMC
posterior exercise and not the source of the baseline calibration.

`dynare/nk_chile_mcmc.mod` is the full posterior extension. Its final
diagnostics have R-hat below 1.05 for all eight estimated objects, but effective
sample sizes remain modest; inference is reported with explicit convergence and
model-conditioning caveats.

`python/compare_bayesian_models.py` compares the forward-looking and hybrid
Phillips specifications on the same 101 observations and observables. It uses
the Laplace approximation to each model's marginal data density at the Dynare
posterior mode. The hybrid specification is preferred by 12.02 log-evidence
points, conditional on the priors and local Gaussian approximation.

## Deep macro analysis

The project also contains a historical shock decomposition, a conditional
hawkish-rule counterfactual, a recursive SVAR, a statistical time-varying
`rstar` proxy, pseudo-out-of-sample forecast evaluation, a small-open-economy
extension with exchange-rate pass-through and copper, and a hybrid Phillips
curve with inflation indexation. These are enrichment exercises:

- the historical decomposition is exact because three observables are matched
  by three shocks without measurement error;
- the SVAR depends on Cholesky ordering and displays an initial activity puzzle;
- time-varying `rstar` is a local-level proxy, not a structural
  Laubach-Williams estimate;
- forecast evaluation uses revised data and a full-sample HP output gap;
- open-economy and indexation coefficients are illustrative calibrations.
- marginal-likelihood comparison is a local Laplace approximation, not a
  bridge-sampling or modified-harmonic-mean estimate from both models' chains.

## Outputs

`outputs/tables/` (CSV): `parameter_targets`, `rstar_beta_table`, `rhoi_estimate`,
`taylor_rule_estimates`, `nkpc_estimates`, `rstar_estimates`, `shock_calibration`,
`shock_sigmas`, `shock_sigmas_comparison`, `fevd_calibration_comparison`,
`scenario_manifest`, `scenario_determinacy`, `determinacy_map`, `irfs_long`,
`irf_summary_metrics`, `irf_sign_checks`, `moments`, `moments_model_vs_data`,
`correlations_model_vs_data`, `fevd_summary`, `forecast`, `forecast_summary`,
`policy_transition_coefficients`, `bayesian_estimates`.

`outputs/figures/` (PNG): `data_overview`, `irf_baseline_all_shocks`, `irf_kappa_comparison`,
`irf_kappa_tradeoffs`, `irf_phi_pi_comparison`, `irf_phi_pi_tradeoffs`,
`irf_rho_comparison`, `determinacy_map`, `moments_model_vs_data`,
`fevd_calibration_comparison`, `forecast_fanchart`, `conditional_scenarios`,
`conditional_policy_shocks`, plus the historical, SVAR, time-varying-rstar,
forecast-evaluation, open-economy, hybrid-NKPC, and MCMC figures documented in
`docs/macro_analysis_progress.md`.

`outputs/dynare/<scenario>/`: per-scenario `irfs.csv`, `moments.csv`, `fevd.csv`, `stability.csv`,
`eigenvalues.csv` for the 19 models (baseline, rstar/kappa/phi_pi grids, rho_i comparison and
didactic-FEVD scenario).
`outputs/logs/`: run logs. When Dynare output is unavailable for a scenario, Python fills it with the
**exact linear-RE solution** of the same model (labelled `synthetic_model_fallback`) as a cross-check.

`Entrega Final.html`: self-contained report in Portuguese. It embeds all public figures, the main
CSV tables, the assignment compliance review, the monetary-policy interpretation and the complete
Python/Octave/Dynare source code used by the project.

## Source labelling and honesty

Every output carries its source. BCCh data is marked real with provenance; the
Python solver is a cross-check of the linear model; synthetic fallbacks are
labelled and never presented as evidence. Forecast files are illustrative model
scenarios, not forecasts from the BCCh or investment advice.

## Reproducibility checklist

- [ ] BCCh credentials provided via env vars or `data/raw/bcch_credentials.json` (never committed).
- [ ] `data/clean/dataset_metadata.json` reports `is_synthetic=false` with series codes and access date.
- [ ] `requirements.txt` installs in a clean environment.
- [ ] All 19 `.mod` models regenerated before the Dynare batch; `steady`/`check`/`stoch_simul` complete.
- [ ] Required tables and all public figures exist in `outputs/`.
- [ ] `python python/build_final_html.py` regenerates `Entrega Final.html`.
- [ ] `git status` shows no PDFs, credentials, `__pycache__`, or compiled `+model` folders.

## Documentation

- `docs/assignment_brief.md` — the assignment in original words.
- `docs/assignment_review_pages_26_55.md` — compliance audit of the calibration/forecast block.
- `docs/model_notes.md` — variables, equations, calibration and sensitivity design.
- `report/relatorio_final.md` — full report (Portuguese) with all results.
- `Entrega Final.html` — complete self-contained final deliverable.
