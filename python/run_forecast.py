"""Run the native Dynare forecast (estimation forecast=8 + conditional_forecast).

Mirrors run_bayesian.py: stages nk_chile_forecast.mod, the export helpers and a
numeric-only observables CSV into a disposable ASCII temp directory (to avoid the
OneDrive/accent issues that break Dynare's preprocessing inside the synced folder),
runs Dynare there, and copies the produced CSVs back to outputs/dynare/forecast/.
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


def copy_results_back(work: Path) -> list[str]:
    staged = work / "outputs" / "dynare" / "forecast"
    if not staged.exists():
        return []
    dest = DYNARE_OUTPUTS / "forecast"
    dest.mkdir(parents=True, exist_ok=True)
    copied = []
    for item in sorted(staged.glob("*.csv")) + sorted(staged.glob("*.txt")):
        shutil.copy(item, dest / item.name)
        copied.append(item.name)
    return copied


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    ensure_directories()

    octave = find_octave()
    dynare_matlab = find_dynare_matlab()
    if octave is None or dynare_matlab is None:
        print("WARNING: Octave/Dynare not found; forecast skipped.", file=sys.stderr)
        return 1

    observables = DATA_CLEAN / "chile_observables.csv"
    if not observables.exists():
        print("ERROR: chile_observables.csv missing; run build_chile_dataset.py first.",
              file=sys.stderr)
        return 1

    work = Path(tempfile.gettempdir()) / "nk_forecast_work"
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    (work / "outputs" / "dynare" / "forecast").mkdir(parents=True, exist_ok=True)
    (work / "outputs" / "logs").mkdir(parents=True, exist_ok=True)

    dynare_dir = ROOT / "dynare"
    for helper in ("nk_chile_forecast.mod", "export_forecast.m", "export_conditional.m"):
        shutil.copy(dynare_dir / helper, work / helper)
    # Numeric-only observables for Dynare's CSV reader (no date column).
    pd.read_csv(observables)[["pi", "i", "x"]].to_csv(
        work / "chile_observables_dynare.csv", index=False
    )

    expression = (
        f"addpath('{octave_literal(dynare_matlab)}'); "
        "dynare('nk_chile_forecast.mod','noclearall','nolog');"
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

    copied = copy_results_back(work)
    (LOGS / "forecast_run.log").write_text(
        f"TIMEOUT: {timed_out}\nRC: {proc.returncode}\nCOPIED: {copied}\n\n"
        f"STDOUT\n{stdout}\n\nSTDERR\n{stderr}\n",
        encoding="utf-8",
    )
    print(stdout[-3000:] if stdout else "")
    if stderr:
        print(stderr[-1500:], file=sys.stderr)
    print(f"Forecast CSVs copied back: {copied}; timed_out: {timed_out}")
    if timed_out and not copied:
        return 124
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
