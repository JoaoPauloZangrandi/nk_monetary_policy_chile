"""Run posterior-mode estimation robustly via ASCII staging.

Stages nk_chile_estim.mod, export_bayesian.m and a numeric-only observables CSV into a
disposable ASCII temp directory (to avoid OneDrive/accent issues), runs the Dynare
estimation there, and copies the posterior CSV back to outputs/tables/. A hard timeout
terminates the Octave process tree.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

from common import (
    DATA_CLEAN,
    LOGS,
    ROOT,
    TABLES,
    ensure_directories,
    find_dynare_matlab,
    find_octave,
)


def octave_literal(path) -> str:
    return str(path).replace("\\", "/").replace("'", "''")


def kill_tree(proc: subprocess.Popen) -> None:
    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                       capture_output=True, check=False)
    except Exception:  # noqa: BLE001
        proc.kill()


def augment_with_std(work: Path, produced: Path) -> None:
    """Add Laplace standard errors and 95% intervals from the saved mode Hessian.

    Dynare saves the posterior mode and Hessian (hh) in <model>_mode.mat. The rows of
    xparam1/hh follow the same order as the CSV written by export_bayesian.m, so we map
    by row index. Done in Python (scipy) because it is far more robust than reading the
    Hessian out of Octave structures.
    """
    if not produced.exists():
        return
    mode_files = list(work.rglob("*_mode.mat"))
    if not mode_files:
        print("No mode .mat found; reporting posterior mode without standard errors.")
        return
    try:
        import numpy as np
        from scipy.io import loadmat

        frame = pd.read_csv(produced)
        payload = loadmat(str(mode_files[0]))
        hessian = payload.get("hh")
        if hessian is None or hessian.shape[0] != len(frame):
            print(f"Mode Hessian shape {None if hessian is None else hessian.shape} "
                  f"!= {len(frame)} rows; skipping std.")
            return
        std = np.sqrt(np.diag(np.linalg.inv(hessian)))
        xparam = payload.get("xparam1")
        if xparam is not None:
            xparam = np.asarray(xparam).ravel()
            if len(xparam) == len(frame):
                frame["posterior_mode"] = xparam  # authoritative mode (all params, in order)
        frame["posterior_std"] = std
        frame["ci95_low"] = frame["posterior_mode"] - 1.96 * std
        frame["ci95_high"] = frame["posterior_mode"] + 1.96 * std
        frame.to_csv(produced, index=False)
        print(f"Added mode/std from {mode_files[0].name}.")
    except Exception as exc:  # noqa: BLE001
        print(f"Standard-error augmentation failed ({exc}); reporting mode only.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    ensure_directories()

    octave = find_octave()
    dynare_matlab = find_dynare_matlab()
    if octave is None or dynare_matlab is None:
        print("WARNING: Octave/Dynare not found; Bayesian estimation skipped.")
        return 0

    observables = DATA_CLEAN / "chile_observables.csv"
    if not observables.exists():
        print("ERROR: chile_observables.csv missing; run build_chile_dataset.py first.",
              file=sys.stderr)
        return 1

    work = Path(tempfile.gettempdir()) / "nk_estim_work"
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    (work / "outputs" / "tables").mkdir(parents=True, exist_ok=True)
    (work / "outputs" / "logs").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "dynare" / "nk_chile_estim.mod", work / "nk_chile_estim.mod")
    shutil.copy(ROOT / "dynare" / "export_bayesian.m", work / "export_bayesian.m")
    # Numeric-only observables for Dynare's CSV reader (no date column).
    pd.read_csv(observables)[["pi", "i", "x"]].to_csv(
        work / "chile_observables_dynare.csv", index=False
    )

    expression = (
        f"addpath('{octave_literal(dynare_matlab)}'); "
        "dynare('nk_chile_estim.mod','noclearall','nolog');"
    )
    command = [str(octave), "--quiet", "--eval", expression]
    environment = os.environ.copy()
    environment["NK_REPO_ROOT"] = str(work)
    print(f"Octave: {octave}\nWork dir: {work}\nTimeout: {args.timeout}s")

    proc = subprocess.Popen(command, cwd=str(work), env=environment, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = proc.communicate(timeout=args.timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        kill_tree(proc)
        stdout, stderr = proc.communicate()
        timed_out = True

    produced = work / "outputs" / "tables" / "bayesian_estimates.csv"
    augment_with_std(work, produced)
    copied = False
    if produced.exists():
        metadata = json.loads(
            (DATA_CLEAN / "dataset_metadata.json").read_text(encoding="utf-8")
        )
        frame = pd.read_csv(produced)
        frame["is_synthetic"] = bool(metadata.get("is_synthetic", True))
        frame["data_source"] = str(
            metadata.get("institution", metadata.get("source", "unknown"))
        )
        frame["estimation_scope"] = "posterior_mode_laplace_not_mcmc"
        frame.to_csv(produced, index=False)
        shutil.copy(produced, TABLES / "bayesian_estimates.csv")
        copied = True

    (LOGS / "bayesian_run.log").write_text(
        f"TIMEOUT: {timed_out}\nCOPIED: {copied}\nRC: {proc.returncode}\n\n"
        f"STDOUT\n{stdout}\n\nSTDERR\n{stderr}\n",
        encoding="utf-8",
    )
    print(stdout[-2500:] if stdout else "")
    if stderr:
        print(stderr[-1200:], file=sys.stderr)
    print(f"bayesian_estimates.csv copied back: {copied}; timed_out: {timed_out}")
    if timed_out and not copied:
        return 124
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
