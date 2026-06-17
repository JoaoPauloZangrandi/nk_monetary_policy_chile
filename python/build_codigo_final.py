"""Generate "Codigo Final": ONE PDF document with ALL project code.

Reads every python/*.py and dynare/*.mod, transliterates non-ASCII characters in
the *code* to ASCII (pi, ->, --, accents stripped) so pdflatex + listings never
chokes, and writes entrega_aula5/Codigo_Final.tex. Prose/titles keep their
accents via inputenc utf8. Build with: entrega_aula5/build.sh Codigo_Final

The file order is grouped to read like the pipeline; any file not listed is
appended automatically, so the document always contains *all* the code.
"""

from __future__ import annotations

import datetime as dt
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent          # python/
ROOT = HERE.parent
MOD = ROOT / "dynare"
OUT = ROOT / "entrega_aula5" / "Codigo_Final.tex"

# Non-ASCII -> ASCII so the code listings are pure ASCII.
GREEK = {
    "π": "pi", "κ": "kappa", "β": "beta", "σ": "sigma", "φ": "phi", "ρ": "rho",
    "α": "alpha", "θ": "theta", "λ": "lambda", "γ": "gamma", "δ": "delta",
    "ε": "epsilon", "η": "eta", "μ": "mu", "ν": "nu", "τ": "tau", "ω": "omega",
    "Φ": "Phi", "Σ": "Sigma", "Π": "Pi", "Δ": "Delta", "Ω": "Omega",
}
SYM = {
    "—": "--", "–": "-", "×": "x", "→": "->", "←": "<-", "²": "^2", "³": "^3",
    "≈": "~=", "≤": "<=", "≥": ">=", "≠": "!=", "·": "*", "…": "...", "•": "-",
    "’": "'", "‘": "'", "“": '"', "”": '"', "°": "deg", "±": "+/-", "∞": "inf",
    "√": "sqrt", "∑": "sum", "∈": "in", "∂": "d", "≡": "==", "∆": "Delta",
    " ": " ", " ": " ", "​": "",
}


def translit(text: str) -> str:
    out = []
    for ch in text:
        if ord(ch) < 128:
            out.append(ch)
        elif ch in GREEK:
            out.append(GREEK[ch])
        elif ch in SYM:
            out.append(SYM[ch])
        else:
            d = unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode()
            out.append(d if d else "?")
    return "".join(out)


# Grouped, pipeline-ordered. Remaining files are appended in a final group.
GROUPS: list[tuple[str, list[str]]] = [
    ("Infraestrutura compartilhada", ["common.py"]),
    ("Dados (BCCh / FRED / filtro de Kalman)", [
        "build_chile_dataset.py", "reprocess_dataset.py",
        "build_open_economy_dataset.py", "discover_ipc_series.py"]),
    ("Geracao dos modelos Dynare", [
        "generate_dynare_models.py", "generate_macro_extension_models.py"]),
    ("Modelos Dynare (.mod)", [
        "nk_chile_base.mod", "nk_chile_estim.mod", "nk_chile_hybrid.mod",
        "nk_chile_hybrid_estim.mod", "nk_chile_forecast.mod",
        "nk_chile_history.mod", "nk_chile_history_hybrid.mod",
        "nk_chile_mcmc.mod", "nk_chile_open.mod"]),
    ("Solucao e calibracao", [
        "hybrid_solution.py", "calibrate_shocks.py", "analyze_determinacy.py"]),
    ("Estimacao dos parametros", [
        "estimate_nkpc.py", "estimate_taylor_rule.py", "estimate_rhoi_chile.py",
        "estimate_rstar.py", "estimate_time_varying_rstar.py"]),
    ("Execucao (Octave/Dynare + Bayesiano)", [
        "run_dynare_batch.py", "run_bayesian.py", "run_mcmc.py",
        "run_forecast.py", "run_history.py", "run_macro_extensions.py"]),
    ("Previsao e avaliacao", [
        "forecast_model.py", "evaluate_forecasts.py"]),
    ("Analise (SVAR, Bayes, resultados)", [
        "analyze_svar.py", "compare_bayesian_models.py",
        "analyze_model_results.py", "analyze_macro_extensions.py"]),
    ("Nucleos da inflacao e mercado de trabalho", [
        "build_inflation_cores.py", "build_inflation_cores_bcch.py",
        "build_labor_activity.py"]),
    ("Graficos", [
        "plot_history.py", "plot_ipc_decomposition.py", "plot_forecast_outlook.py",
        "plot_hybrid_test.py", "plot_irfs.py", "plot_mcmc.py"]),
    ("Tabelas, coleta e entregaveis", [
        "collect_outputs.py", "make_tables.py", "build_final_html.py",
        "build_codigo_final.py"]),
]


def resolve(name: str) -> Path:
    return (MOD / name) if name.endswith(".mod") else (HERE / name)


def latex_escape_title(name: str) -> str:
    return name.replace("\\", r"\textbackslash{}").replace("_", r"\_") \
               .replace("&", r"\&").replace("%", r"\%").replace("#", r"\#")


PREAMBLE = r"""\documentclass[9pt]{extarticle}
\usepackage[a4paper,margin=1.8cm]{geometry}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{xcolor}
\usepackage{listings}
\usepackage[hidelinks]{hyperref}
\definecolor{cmt}{RGB}{96,139,84}
\definecolor{kw}{RGB}{0,0,170}
\definecolor{str}{RGB}{163,21,21}
\definecolor{ln}{RGB}{150,150,150}
\lstset{
  basicstyle=\ttfamily\scriptsize,
  breaklines=true,breakatwhitespace=false,
  columns=fullflexible,keepspaces=true,
  showstringspaces=false,upquote=true,tabsize=4,
  commentstyle=\color{cmt},keywordstyle=\color{kw},stringstyle=\color{str},
  numbers=left,numberstyle=\tiny\color{ln},numbersep=6pt,xleftmargin=2.2em,
  frame=lines,framesep=4pt,
}
\title{\textbf{C\'odigo Final}\\[2mm]\large Modelo Novo-Keynesiano de Pol\'itica
Monet\'aria para o Chile\\\normalsize Todo o c\'odigo (Python + Dynare) em um
\'unico documento}
\author{Daniel Colli e Jo\~ao Zangrandi}
\date{REPLACE_DATE}
\begin{document}
\maketitle
{\small Este documento re\'une \textbf{todo} o c\'odigo do projeto: TARGET_NFILES
arquivos (Python e Dynare \texttt{.mod}), agrupados na ordem do \emph{pipeline}.
Caracteres n\~ao-ASCII do c\'odigo (letras gregas, acentos) foram transliterados
para ASCII na listagem para garantir a compila\c{c}\~ao; a l\'ogica \'e id\^entica
\`a dos arquivos-fonte do reposit\'orio.\par}
\tableofcontents
\clearpage
"""


def main() -> None:
    used: list[str] = []
    for _, names in GROUPS:
        used.extend(names)
    # Append any file not explicitly grouped.
    extra = sorted(p.name for p in HERE.glob("*.py") if p.name not in used)
    extra += sorted(p.name for p in MOD.glob("*.mod") if p.name not in used)
    groups = GROUPS + ([("Outros", extra)] if extra else [])

    nfiles = sum(len(n) for _, n in groups)
    parts = [PREAMBLE.replace("REPLACE_DATE", dt.date.today().strftime("%d/%m/%Y"))
             .replace("TARGET_NFILES", str(nfiles))]

    for title, names in groups:
        parts.append(f"\\part*{{{title}}}\\addcontentsline{{toc}}{{part}}{{{title}}}\n")
        for name in names:
            path = resolve(name)
            if not path.exists():
                continue
            code = translit(path.read_text(encoding="utf-8", errors="replace"))
            code = code.replace("\t", "    ").rstrip("\n")
            lang = "Python" if name.endswith(".py") else "{}"
            rel = ("dynare/" if name.endswith(".mod") else "python/") + name
            parts.append(f"\\section{{{latex_escape_title(rel)}}}")
            parts.append(f"\\begin{{lstlisting}}[language={lang}]")
            parts.append(code)
            parts.append("\\end{lstlisting}\n\\clearpage")

    parts.append("\\end{document}\n")
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote {OUT} ({nfiles} files, {OUT.stat().st_size//1024} KB).")


if __name__ == "__main__":
    main()
