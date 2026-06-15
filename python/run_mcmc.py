"""Run the full Dynare MCMC extension and compute chain diagnostics."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import loadmat

from common import DATA_CLEAN, LOGS, ROOT, TABLES, find_dynare_matlab, find_octave


PARAMETER_ORDER = [
    "stderr e_x",
    "stderr e_pi",
    "stderr e_i",
    "sigma",
    "kappa",
    "rho_i",
    "phi_pi",
    "phi_x",
]


def octave_literal(path: Path) -> str:
    return str(path).replace("\\", "/").replace("'", "''")


def split_rhat(chains: list[np.ndarray]) -> np.ndarray:
    if len(chains) < 2:
        return np.full(chains[0].shape[1], np.nan)
    n = min(len(chain) for chain in chains)
    arrays = np.stack([chain[-n:] for chain in chains])
    chain_means = arrays.mean(axis=1)
    between = n * chain_means.var(axis=0, ddof=1)
    within = arrays.var(axis=1, ddof=1).mean(axis=0)
    variance = ((n - 1) / n) * within + between / n
    return np.sqrt(variance / within)


def effective_sample_size(chains: list[np.ndarray]) -> np.ndarray:
    n = min(len(chain) for chain in chains)
    arrays = np.stack([chain[-n:] for chain in chains])
    m, _, k = arrays.shape
    result = np.empty(k)
    for parameter in range(k):
        autocorrelations = []
        for chain in arrays[:, :, parameter]:
            centered = chain - chain.mean()
            fft_size = 1 << (2 * n - 1).bit_length()
            spectrum = np.fft.rfft(centered, fft_size)
            covariance = np.fft.irfft(spectrum * spectrum.conjugate(), fft_size)[:n]
            covariance /= np.arange(n, 0, -1)
            autocorrelations.append(covariance / covariance[0])
        mean_acf = np.mean(autocorrelations, axis=0)
        autocorr_sum = 0.0
        for rho in mean_acf[1 : min(1001, n)]:
            if rho <= 0:
                break
            autocorr_sum += float(rho)
        result[parameter] = m * n / (1.0 + 2.0 * autocorr_sum)
    return result


def load_chains(work: Path) -> list[np.ndarray]:
    files = sorted(work.rglob("*_mh*_blck*.mat"))
    grouped: dict[int, list[np.ndarray]] = {}
    for path in files:
        match = re.search(r"blck(\d+)", path.name)
        block = int(match.group(1)) if match else len(grouped) + 1
        payload = loadmat(path)
        draws = payload.get("x2")
        if draws is None or draws.ndim != 2:
            continue
        grouped.setdefault(block, []).append(np.asarray(draws, dtype=float))
    return [np.vstack(parts) for _, parts in sorted(grouped.items())]


def save_chain_outputs(chains: list[np.ndarray], burn_fraction: float = 0.30) -> None:
    retained = [chain[int(len(chain) * burn_fraction) :] for chain in chains]
    draws = np.vstack(retained)
    posterior = pd.DataFrame(
        {
            "parameter": PARAMETER_ORDER,
            "type": ["shock_std"] * 3 + ["param"] * 5,
            "posterior_mean": draws.mean(axis=0),
            "posterior_median": np.median(draws, axis=0),
            "posterior_std": draws.std(axis=0, ddof=1),
            "hpd90_low": np.quantile(draws, 0.05, axis=0),
            "hpd90_high": np.quantile(draws, 0.95, axis=0),
        }
    )
    posterior.to_csv(TABLES / "mcmc_posterior.csv", index=False)

    diagnostics = pd.DataFrame(
        {
            "parameter": PARAMETER_ORDER,
            "rhat": split_rhat(retained),
            "effective_sample_size": effective_sample_size(retained),
            "chains": len(retained),
            "draws_per_chain_loaded": min(len(chain) for chain in retained),
        }
    )
    diagnostics["rhat_pass_1p05"] = diagnostics["rhat"] < 1.05
    diagnostics.to_csv(TABLES / "mcmc_diagnostics.csv", index=False)
    print(diagnostics.to_string(index=False))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument(
        "--recover-dir",
        type=Path,
        help="Post-process completed Dynare chain files without rerunning MCMC.",
    )
    args = parser.parse_args()
    if args.recover_dir:
        chains = load_chains(args.recover_dir)
        if len(chains) < 2 or any(
            chain.shape[1] != len(PARAMETER_ORDER) for chain in chains
        ):
            print(f"ERROR: invalid MCMC chain shapes: {[c.shape for c in chains]}")
            return 1
        save_chain_outputs(chains)
        print(f"Recovered MCMC outputs from {args.recover_dir}")
        return 0

    octave = find_octave()
    dynare = find_dynare_matlab()
    if octave is None or dynare is None:
        print("ERROR: Octave/Dynare not found.", file=sys.stderr)
        return 1

    work = Path(tempfile.gettempdir()) / "nk_mcmc_work"
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    (work / "outputs" / "tables").mkdir(parents=True, exist_ok=True)
    for filename in ["nk_chile_mcmc.mod", "export_mcmc.m"]:
        shutil.copy(ROOT / "dynare" / filename, work / filename)
    pd.read_csv(DATA_CLEAN / "chile_observables.csv")[["pi", "i", "x"]].to_csv(
        work / "chile_observables_dynare.csv", index=False
    )

    expression = (
        f"addpath('{octave_literal(dynare)}'); "
        "dynare('nk_chile_mcmc.mod','noclearall','nolog');"
    )
    command = [str(octave), "--quiet", "--eval", expression]
    env = os.environ.copy()
    env["NK_REPO_ROOT"] = str(work)
    proc = subprocess.Popen(
        command,
        cwd=work,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = proc.communicate(timeout=args.timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
            check=False,
        )
        stdout, stderr = proc.communicate()
        timed_out = True

    posterior = work / "outputs" / "tables" / "mcmc_posterior.csv"
    copied = False
    if posterior.exists():
        shutil.copy(posterior, TABLES / posterior.name)
        copied = True

    chains = load_chains(work)
    if chains and all(chain.shape[1] == len(PARAMETER_ORDER) for chain in chains):
        save_chain_outputs(chains)
    else:
        print(
            f"WARNING: could not load two {len(PARAMETER_ORDER)}-column MCMC chains; "
            f"shapes={[chain.shape for chain in chains]}",
            file=sys.stderr,
        )

    (LOGS / "mcmc_run.log").write_text(
        f"TIMEOUT: {timed_out}\nRC: {proc.returncode}\nCOPIED: {copied}\n"
        f"CHAIN_SHAPES: {[chain.shape for chain in chains]}\n\n"
        f"STDOUT\n{stdout}\n\nSTDERR\n{stderr}\n",
        encoding="utf-8",
    )
    print(stdout[-4000:] if stdout else "")
    if stderr:
        print(stderr[-1600:], file=sys.stderr)
    return 0 if copied and not timed_out else 1


if __name__ == "__main__":
    raise SystemExit(main())
