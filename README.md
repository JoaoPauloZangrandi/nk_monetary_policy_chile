# New Keynesian Monetary Policy - Chile

Public, reproducible final-assignment project implementing a minimal
three-equation New Keynesian model for **Chile**. It uses official Banco Central
de Chile (BCCh) data when credentials are available, solves the model with
**Octave + Dynare**, and uses **Python** for data preparation, econometrics,
tables, figures, and exploratory scenarios. The written report is in
`report/relatorio_final.md` (Portuguese).

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
python python/generate_dynare_models.py   # regenerate baseline + 16 scenarios + manifest
python python/run_dynare_batch.py --all   # Dynare: baseline + scenarios (omit --all for baseline only)
python python/run_bayesian.py             # optional posterior-mode DSGE exercise
python python/collect_outputs.py          # aggregate IRFs/moments/FEVD/determinacy
python python/analyze_determinacy.py      # determinacy map vs phi_pi
python python/forecast_model.py           # optional 8-quarter illustrative scenarios
python python/plot_irfs.py                # figures
```

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

## Posterior-mode extension

`dynare/nk_chile_estim.mod` writes the model in deviation form and estimates a
posterior mode (MAP). Reported uncertainty uses a local Laplace approximation
from the mode Hessian. This is an exploratory extension, not a full MCMC
posterior exercise and not the source of the baseline calibration.

## Outputs

`outputs/tables/` (CSV): `parameter_targets`, `rstar_beta_table`, `rhoi_estimate`,
`taylor_rule_estimates`, `nkpc_estimates`, `rstar_estimates`, `shock_calibration`, `shock_sigmas`,
`scenario_manifest`, `scenario_determinacy`, `determinacy_map`, `irfs_long`, `moments`,
`fevd_summary`, `forecast`, `bayesian_estimates`.

`outputs/figures/` (PNG): `data_overview`, `irf_baseline_all_shocks`, `irf_kappa_comparison`,
`irf_phi_pi_comparison`, `determinacy_map`, `forecast_fanchart`.

`outputs/dynare/<scenario>/`: per-scenario `irfs.csv`, `moments.csv`, `fevd.csv`, `stability.csv`,
`eigenvalues.csv` for the 17 models (baseline and the rstar/kappa/phi_pi grids).
`outputs/logs/`: run logs. When Dynare output is unavailable for a scenario, Python fills it with the
**exact linear-RE solution** of the same model (labelled `synthetic_model_fallback`) as a cross-check.

## Source labelling and honesty

Every output carries its source. BCCh data is marked real with provenance; the
Python solver is a cross-check of the linear model; synthetic fallbacks are
labelled and never presented as evidence. Forecast files are illustrative model
scenarios, not forecasts from the BCCh or investment advice.

## Reproducibility checklist

- [ ] BCCh credentials provided via env vars or `data/raw/bcch_credentials.json` (never committed).
- [ ] `data/clean/dataset_metadata.json` reports `is_synthetic=false` with series codes and access date.
- [ ] `requirements.txt` installs in a clean environment.
- [ ] All 17 `.mod` models regenerated before the Dynare batch; `steady`/`check`/`stoch_simul` complete.
- [ ] Required tables and the six figures exist in `outputs/`.
- [ ] `git status` shows no PDFs, credentials, `__pycache__`, or compiled `+model` folders.

## Documentation

- `docs/assignment_brief.md` — the assignment in original words.
- `docs/model_notes.md` — variables, equations, calibration and sensitivity design.
- `report/relatorio_final.md` — full report (Portuguese) with all results.
