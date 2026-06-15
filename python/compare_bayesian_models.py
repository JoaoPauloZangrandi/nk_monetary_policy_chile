"""Compare the forward-looking and hybrid NK models by marginal likelihood.

Both models use the same Chilean observables and common priors. Dynare finds
each posterior mode and Hessian. The script then applies the Laplace
approximation:

    log p(y|M) ~= log p(y, theta_hat|M)
                  + k/2 log(2*pi) - 1/2 log|H(theta_hat)|.

This is a formal marginal-data-density comparison, but an approximation around
one mode. It complements, rather than replaces, the full baseline MCMC.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.io import loadmat

from common import DATA_CLEAN, FIGURES, LOGS, ROOT, TABLES, find_dynare_matlab, find_octave


MODELS = {
    "forward_nkpc": "nk_chile_estim.mod",
    "hybrid_nkpc": "nk_chile_hybrid_estim.mod",
}


def octave_literal(path: Path) -> str:
    return str(path).replace("\\", "/").replace("'", "''")


def kill_tree(proc: subprocess.Popen) -> None:
    subprocess.run(
        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
        capture_output=True,
        check=False,
    )


def run_mode(
    model_id: str,
    filename: str,
    work: Path,
    octave: Path,
    dynare: Path,
    timeout: int,
) -> tuple[Path, str]:
    model_work = work / model_id
    model_work.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "dynare" / filename, model_work / filename)
    pd.read_csv(DATA_CLEAN / "chile_observables.csv")[["pi", "i", "x"]].to_csv(
        model_work / "chile_observables_dynare.csv", index=False
    )
    expression = (
        f"addpath('{octave_literal(dynare)}'); "
        f"dynare('{filename}','noclearall','nolog');"
    )
    proc = subprocess.Popen(
        [str(octave), "--quiet", "--eval", expression],
        cwd=model_work,
        env=os.environ.copy(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_tree(proc)
        stdout, stderr = proc.communicate()
        raise TimeoutError(f"{model_id} posterior mode exceeded {timeout}s")
    log = f"RC={proc.returncode}\nSTDOUT\n{stdout}\nSTDERR\n{stderr}\n"
    mode_files = list(model_work.rglob("*_mode.mat"))
    if proc.returncode != 0 or not mode_files:
        raise RuntimeError(
            f"{model_id} mode failed (rc={proc.returncode}); "
            f"tail={log[-1800:]}"
        )
    return mode_files[0], log


def laplace_summary(model_id: str, path: Path) -> dict[str, object]:
    payload = loadmat(path)
    mode = np.asarray(payload["xparam1"], dtype=float).ravel()
    hessian = np.asarray(payload["hh"], dtype=float)
    objective = float(np.asarray(payload["fval"]).ravel()[0])
    sign, logdet = np.linalg.slogdet(hessian)
    eigenvalues = np.linalg.eigvalsh(hessian)
    if sign <= 0 or eigenvalues.min() <= 0:
        raise ValueError(f"{model_id}: mode Hessian is not positive definite")
    parameter_names = [
        str(item[0]) if isinstance(item, np.ndarray) else str(item)
        for item in np.asarray(payload["parameter_names"]).ravel()
    ]
    k = len(mode)
    log_joint_mode = -objective
    log_mdd = log_joint_mode + 0.5 * k * np.log(2 * np.pi) - 0.5 * logdet
    gamma = np.nan
    if "gamma_pi" in parameter_names:
        gamma = float(mode[parameter_names.index("gamma_pi")])
    return {
        "model": model_id,
        "parameters": k,
        "log_joint_at_mode": log_joint_mode,
        "hessian_log_determinant": logdet,
        "laplace_log_marginal_likelihood": log_mdd,
        "gamma_pi_mode": gamma,
        "hessian_min_eigenvalue": float(eigenvalues.min()),
        "method": "Laplace approximation at Dynare posterior mode",
        "same_observables": "pi,i,x",
        "observations": len(pd.read_csv(DATA_CLEAN / "chile_observables.csv")),
    }


def make_figure(frame: pd.DataFrame) -> None:
    best = frame["laplace_log_marginal_likelihood"].max()
    relative = frame["laplace_log_marginal_likelihood"] - best
    labels = frame["model"].map(
        {"forward_nkpc": "NKPC prospectiva", "hybrid_nkpc": "NKPC híbrida"}
    )
    colors = ["#7A9E9F" if value < 0 else "#145DA0" for value in relative]
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    bars = ax.bar(labels, relative, color=colors, width=0.58)
    ax.axhline(0, color="#333333", linewidth=0.9)
    ax.set_ylabel("Log evidência relativa ao melhor modelo")
    ax.set_title("Comparação bayesiana de modelos: evidência marginal (Laplace)")
    ax.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, relative, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + (0.25 if value >= 0 else -0.25),
            f"{value:.2f}",
            ha="center",
            va="bottom" if value >= 0 else "top",
            fontweight="bold",
        )
    fig.text(
        0.5,
        0.01,
        "Mesma amostra e mesmos observáveis. A evidência penaliza o parâmetro extra "
        "da Phillips híbrida; aproximação local, não estimativa MCMC da evidência.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(FIGURES / "bayesian_model_comparison.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=420)
    parser.add_argument(
        "--reuse-baseline",
        action="store_true",
        help="Reuse the existing baseline mode in the system temp directory.",
    )
    args = parser.parse_args()
    octave = find_octave()
    dynare = find_dynare_matlab()
    if octave is None or dynare is None:
        print("ERROR: Octave/Dynare not found.", file=sys.stderr)
        return 1

    work = Path(tempfile.gettempdir()) / "nk_model_comparison_work"
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    logs: list[str] = []
    summaries: list[dict[str, object]] = []

    for model_id, filename in MODELS.items():
        if model_id == "forward_nkpc" and args.reuse_baseline:
            cached = (
                Path(tempfile.gettempdir())
                / "nk_estim_work"
                / "nk_chile_estim"
                / "Output"
                / "nk_chile_estim_mode.mat"
            )
            if cached.exists():
                mode_file = cached
                log = f"Reused baseline mode: {cached}\n"
            else:
                mode_file, log = run_mode(
                    model_id, filename, work, octave, dynare, args.timeout
                )
        else:
            mode_file, log = run_mode(
                model_id, filename, work, octave, dynare, args.timeout
            )
        logs.append(f"\n===== {model_id} =====\n{log}")
        summaries.append(laplace_summary(model_id, mode_file))

    frame = pd.DataFrame(summaries)
    best = float(frame["laplace_log_marginal_likelihood"].max())
    frame["log_bayes_factor_vs_best"] = (
        frame["laplace_log_marginal_likelihood"] - best
    )
    weights = np.exp(frame["log_bayes_factor_vs_best"])
    frame["posterior_model_probability_equal_prior"] = weights / weights.sum()
    preferred = frame.loc[
        frame["laplace_log_marginal_likelihood"].idxmax(), "model"
    ]
    frame["preferred_model"] = preferred
    frame.to_csv(TABLES / "bayesian_model_comparison.csv", index=False)
    make_figure(frame)
    (LOGS / "bayesian_model_comparison.log").write_text(
        "".join(logs), encoding="utf-8"
    )
    print(frame.to_string(index=False))
    print(f"Preferred model under equal prior odds: {preferred}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
