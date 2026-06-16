"""Run the historical shock decomposition (Kalman smoother + shock_decomposition).

Stages nk_chile_history.mod, export_history.m and a numeric observables CSV into
an ASCII temp directory, runs Dynare, and copies outputs/dynare/history/*.csv back.
Mirrors run_forecast.py.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

from common import (
    DATA_CLEAN,
    DYNARE_OUTPUTS,
    LOGS,
    ROOT,
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=420)
    parser.add_argument("--mod", default="nk_chile_history.mod")
    args = parser.parse_args()
    ensure_directories()

    octave = find_octave()
    dynare_matlab = find_dynare_matlab()
    if octave is None or dynare_matlab is None:
        print("WARNING: Octave/Dynare not found; history skipped.", file=sys.stderr)
        return 1

    observables = DATA_CLEAN / "chile_observables.csv"
    if not observables.exists():
        print("ERROR: chile_observables.csv missing.", file=sys.stderr)
        return 1

    work = Path(tempfile.gettempdir()) / "nk_history_work"
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    (work / "outputs" / "dynare").mkdir(parents=True, exist_ok=True)
    (work / "outputs" / "logs").mkdir(parents=True, exist_ok=True)

    dynare_dir = ROOT / "dynare"
    for helper in (args.mod, "export_history.m"):
        shutil.copy(dynare_dir / helper, work / helper)
    pd.read_csv(observables)[["pi", "i", "x"]].to_csv(
        work / "chile_observables_dynare.csv", index=False
    )

    expression = (
        f"addpath('{octave_literal(dynare_matlab)}'); "
        f"dynare('{args.mod}','noclearall','nolog');"
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

    staged_root = work / "outputs" / "dynare"
    copied = []
    if staged_root.exists():
        for sub in sorted(staged_root.iterdir()):
            if not sub.is_dir():
                continue
            dest = DYNARE_OUTPUTS / sub.name
            dest.mkdir(parents=True, exist_ok=True)
            for csv in sorted(sub.glob("*.csv")):
                shutil.copy(csv, dest / csv.name)
                copied.append(f"{sub.name}/{csv.name}")

    (LOGS / "history_run.log").write_text(
        f"TIMEOUT: {timed_out}\nRC: {proc.returncode}\nCOPIED: {copied}\n\n"
        f"STDOUT\n{stdout}\n\nSTDERR\n{stderr}\n",
        encoding="utf-8",
    )
    print(stdout[-2500:] if stdout else "")
    if stderr:
        print(stderr[-1200:], file=sys.stderr)
    print(f"History CSVs copied back: {copied}; timed_out: {timed_out}")
    return 0 if copied else (124 if timed_out else 1)


if __name__ == "__main__":
    raise SystemExit(main())
