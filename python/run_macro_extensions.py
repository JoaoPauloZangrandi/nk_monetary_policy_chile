"""Run the open-economy and hybrid-NKPC Dynare extensions via ASCII staging."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from common import DYNARE_OUTPUTS, LOGS, ROOT, find_dynare_matlab, find_octave


def octave_literal(path: Path) -> str:
    return str(path).replace("\\", "/").replace("'", "''")


def kill_tree(proc: subprocess.Popen) -> None:
    subprocess.run(
        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
        capture_output=True,
        check=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    octave = find_octave()
    dynare = find_dynare_matlab()
    if octave is None or dynare is None:
        print("ERROR: Octave/Dynare not found.", file=sys.stderr)
        return 1

    work = Path(tempfile.gettempdir()) / "nk_macro_extensions"
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    (work / "outputs" / "dynare").mkdir(parents=True, exist_ok=True)
    for name in [
        "nk_chile_open.mod",
        "nk_chile_hybrid.mod",
        "export_extension.m",
        "export_stability.m",
    ]:
        shutil.copy(ROOT / "dynare" / name, work / name)
    runner = (
        "addpath('" + octave_literal(dynare) + "');"
        "dynare('nk_chile_open.mod','noclearall','nolog');"
        "dynare('nk_chile_hybrid.mod','noclearall','nolog');"
    )
    command = [str(octave), "--quiet", "--eval", runner]
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
        kill_tree(proc)
        stdout, stderr = proc.communicate()
        timed_out = True

    copied = []
    for scenario in ["open_economy", "hybrid_nkpc"]:
        source = work / "outputs" / "dynare" / scenario
        if not source.exists():
            continue
        destination = DYNARE_OUTPUTS / scenario
        destination.mkdir(parents=True, exist_ok=True)
        for item in source.glob("*"):
            if item.is_file():
                shutil.copy(item, destination / item.name)
        copied.append(scenario)
    (LOGS / "macro_extensions.log").write_text(
        f"TIMEOUT: {timed_out}\nRC: {proc.returncode}\nCOPIED: {copied}\n\n"
        f"STDOUT\n{stdout}\n\nSTDERR\n{stderr}\n",
        encoding="utf-8",
    )
    print(stdout[-3500:] if stdout else "")
    if stderr:
        print(stderr[-1500:], file=sys.stderr)
    print(f"Copied: {copied}; timeout={timed_out}; rc={proc.returncode}")
    return 0 if len(copied) == 2 and not timed_out else 1


if __name__ == "__main__":
    raise SystemExit(main())
