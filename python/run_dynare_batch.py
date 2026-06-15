"""Locate Octave and Dynare and run the Dynare models robustly on Windows.

To avoid the OneDrive file-locking and accented-path problems that occur when Dynare
preprocesses inside the synced project folder, this wrapper:

  1. stages the requested .mod files, the export helpers and dynare/run_models.m into a
     disposable ASCII temp directory (copy is done in Python, which reads the accented
     source paths reliably);
  2. runs Octave entirely inside that ASCII directory with NK_REPO_ROOT pointing there;
  3. copies the resulting CSVs back into outputs/dynare/ in the repository.

By default only the baseline runs; pass --all to also run every generated scenario.
A hard timeout terminates the Octave process tree.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from common import (
    DYNARE_OUTPUTS,
    LOGS,
    ROOT,
    ensure_directories,
    find_dynare_matlab,
    find_octave,
)


def octave_literal(path) -> str:
    return str(path).replace("\\", "/").replace("'", "''")


def stage_work_dir(run_all: bool) -> Path:
    work = Path(tempfile.gettempdir()) / "nk_dynare_work"
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    (work / "outputs" / "dynare").mkdir(parents=True, exist_ok=True)
    (work / "outputs" / "logs").mkdir(parents=True, exist_ok=True)
    dynare_dir = ROOT / "dynare"
    for helper in ("export_results.m", "export_stability.m", "run_models.m"):
        shutil.copy(dynare_dir / helper, work / helper)
    shutil.copy(dynare_dir / "nk_chile_base.mod", work / "nk_chile_base.mod")
    if run_all:
        for mod in sorted((dynare_dir / "generated").glob("*.mod")):
            shutil.copy(mod, work / mod.name)
    return work


def copy_results_back(work: Path) -> list[str]:
    staged = work / "outputs" / "dynare"
    copied = []
    if not staged.exists():
        return copied
    for scenario_dir in sorted(staged.iterdir()):
        if not scenario_dir.is_dir():
            continue
        dest = DYNARE_OUTPUTS / scenario_dir.name
        dest.mkdir(parents=True, exist_ok=True)
        for csv in scenario_dir.glob("*.csv"):
            shutil.copy(csv, dest / csv.name)
        copied.append(scenario_dir.name)
    return copied


def kill_tree(proc: subprocess.Popen) -> None:
    try:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
            check=False,
        )
    except Exception:  # noqa: BLE001
        proc.kill()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true",
                        help="Run the baseline and every generated scenario.")
    parser.add_argument("--timeout", type=int, default=None,
                        help="Maximum runtime in seconds (default 150 baseline, 600 all).")
    parser.add_argument("--strict", action="store_true",
                        help="Return nonzero when Octave or Dynare is unavailable.")
    args = parser.parse_args()
    ensure_directories()

    octave = find_octave()
    dynare_matlab = find_dynare_matlab()
    if octave is None or dynare_matlab is None:
        message = (
            f"Dynare batch skipped. Octave found: {octave is not None}; "
            f"Dynare found: {dynare_matlab is not None}. "
            "Set OCTAVE_BIN and DYNARE_MATLAB if installed elsewhere."
        )
        print(f"WARNING: {message}")
        (LOGS / "dynare_batch.log").write_text(message + "\n", encoding="utf-8")
        return 1 if args.strict else 0

    work = stage_work_dir(args.all)
    expression = (
        f"addpath('{octave_literal(dynare_matlab)}'); run('run_models.m');"
    )
    command = [str(octave), "--quiet", "--eval", expression]
    environment = os.environ.copy()
    environment["NK_REPO_ROOT"] = str(work)
    timeout = args.timeout or (600 if args.all else 150)
    print(f"Octave: {octave}")
    print(f"Work dir (ASCII): {work}")
    print(f"Mode: {'all scenarios' if args.all else 'baseline only'}; timeout {timeout}s")

    proc = subprocess.Popen(
        command, cwd=str(work), env=environment, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        kill_tree(proc)
        stdout, stderr = proc.communicate()
        timed_out = True

    copied = copy_results_back(work)
    log_text = (
        f"COMMAND: {' '.join(command)}\nWORK: {work}\nTIMEOUT: {timed_out}\n"
        f"COPIED: {copied}\n\nSTDOUT\n{stdout}\n\nSTDERR\n{stderr}\n"
    )
    (LOGS / "dynare_wrapper.log").write_text(log_text, encoding="utf-8")
    print(stdout[-2000:] if stdout else "")
    if stderr:
        print(stderr[-1500:], file=sys.stderr)
    print(f"Scenarios copied back: {copied}")
    if timed_out:
        print(f"ERROR: Octave exceeded {timeout}s and was terminated.", file=sys.stderr)
        return 124
    return proc.returncode if proc.returncode is not None else 0


if __name__ == "__main__":
    raise SystemExit(main())
