"""Build an evaluator-facing HTML with all runnable project code.

The project mixes Python automation, Dynare model files and Octave helper
scripts. A single ".py" final-code file would therefore be misleading. This
script creates a standalone HTML deliverable that contains the maintained source
code grouped by pipeline stage, with commands that can be copied and run from
the repository root.
"""

from __future__ import annotations

import datetime as dt
import html
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "entrega_aula5"
OUT_PRIMARY = OUT_DIR / "Código Final.html"
OUT_COMPAT = OUT_DIR / "Codigo_Final.html"


GROUPS: list[tuple[str, list[str]]] = [
    ("Setup e dependencias", ["requirements.txt"]),
    ("Infraestrutura compartilhada", ["python/common.py"]),
    (
        "Dados macroeconomicos",
        [
            "python/build_chile_dataset.py",
            "python/reprocess_dataset.py",
            "python/build_open_economy_dataset.py",
            "python/discover_ipc_series.py",
            "python/build_inflation_cores.py",
            "python/build_inflation_cores_bcch.py",
            "python/build_labor_activity.py",
        ],
    ),
    (
        "Geracao de modelos Dynare",
        [
            "python/generate_dynare_models.py",
            "python/generate_macro_extension_models.py",
        ],
    ),
    (
        "Modelos Dynare principais",
        [
            "dynare/nk_chile_base.mod",
            "dynare/nk_chile_estim.mod",
            "dynare/nk_chile_hybrid.mod",
            "dynare/nk_chile_hybrid_estim.mod",
            "dynare/nk_chile_forecast.mod",
            "dynare/nk_chile_history.mod",
            "dynare/nk_chile_history_hybrid.mod",
            "dynare/nk_chile_mcmc.mod",
            "dynare/nk_chile_open.mod",
        ],
    ),
    (
        "Octave e exportadores Dynare",
        [
            "dynare/run_all_octave.m",
            "dynare/run_models.m",
            "dynare/export_results.m",
            "dynare/export_stability.m",
            "dynare/export_forecast.m",
            "dynare/export_conditional.m",
            "dynare/export_history.m",
            "dynare/export_extension.m",
            "dynare/export_bayesian.m",
            "dynare/export_mcmc.m",
        ],
    ),
    (
        "Solucao, calibracao e determinacao",
        [
            "python/hybrid_solution.py",
            "python/calibrate_shocks.py",
            "python/analyze_determinacy.py",
        ],
    ),
    (
        "Estimacao econometrica",
        [
            "python/estimate_nkpc.py",
            "python/estimate_taylor_rule.py",
            "python/estimate_rhoi_chile.py",
            "python/estimate_rstar.py",
            "python/estimate_time_varying_rstar.py",
        ],
    ),
    (
        "Execucao dos modelos",
        [
            "python/run_dynare_batch.py",
            "python/run_bayesian.py",
            "python/run_mcmc.py",
            "python/run_forecast.py",
            "python/run_history.py",
            "python/run_macro_extensions.py",
        ],
    ),
    (
        "Previsao e avaliacao",
        [
            "python/forecast_model.py",
            "python/evaluate_forecasts.py",
        ],
    ),
    (
        "Analise macro aprofundada",
        [
            "python/analyze_svar.py",
            "python/compare_bayesian_models.py",
            "python/analyze_model_results.py",
            "python/analyze_macro_extensions.py",
        ],
    ),
    (
        "Graficos",
        [
            "python/plot_irfs.py",
            "python/plot_history.py",
            "python/plot_ipc_decomposition.py",
            "python/plot_forecast_outlook.py",
            "python/plot_hybrid_test.py",
            "python/plot_mcmc.py",
        ],
    ),
    (
        "Tabelas, coleta e entregaveis",
        [
            "python/collect_outputs.py",
            "python/make_tables.py",
            "python/build_final_html.py",
            "python/build_codigo_final.py",
            "python/build_codigo_final_html.py",
        ],
    ),
]


PIPELINE_COMMANDS = [
    ("Instalar dependencias Python", "python -m pip install -r requirements.txt"),
    ("Preparar base macro do Chile", "python python/build_chile_dataset.py"),
    ("Reprocessar dados e hiato do produto", "python python/reprocess_dataset.py"),
    ("Estimar persistencia da taxa de politica", "python python/estimate_rhoi_chile.py"),
    ("Estimar r* fixo e proxy variavel no tempo", "python python/estimate_rstar.py\npython python/estimate_time_varying_rstar.py"),
    ("Calibrar choques para FEVD", "python python/calibrate_shocks.py"),
    ("Gerar tabelas principais", "python python/make_tables.py"),
    ("Gerar modelos Dynare de cenarios", "python python/generate_dynare_models.py"),
    ("Rodar lote Dynare/Octave, se Dynare estiver no path", "python python/run_dynare_batch.py"),
    ("Rodar previsao nativa do Dynare", "python python/run_forecast.py"),
    ("Rodar decomposicao historica", "python python/run_history.py"),
    ("Rodar extensoes macro", "python python/run_macro_extensions.py"),
    ("Rodar SVAR e avaliacao preditiva", "python python/analyze_svar.py\npython python/evaluate_forecasts.py"),
    ("Gerar graficos finais", "python python/plot_irfs.py\npython python/plot_history.py\npython python/plot_forecast_outlook.py"),
    ("Recriar este HTML", "python python/build_codigo_final_html.py"),
]


def as_posix(path: str | Path) -> str:
    return str(path).replace("\\", "/")


def source_groups() -> list[tuple[str, list[Path]]]:
    """Return grouped source files, appending unlisted maintained code."""

    used: set[str] = set()
    grouped: list[tuple[str, list[Path]]] = []
    for title, rels in GROUPS:
        paths: list[Path] = []
        for rel in rels:
            path = ROOT / rel
            if path.exists():
                paths.append(path)
                used.add(as_posix(path.relative_to(ROOT)))
        if paths:
            grouped.append((title, paths))

    generated = sorted((ROOT / "dynare" / "generated").glob("*.mod"))
    generated = [p for p in generated if as_posix(p.relative_to(ROOT)) not in used]
    if generated:
        grouped.append(("Modelos Dynare gerados para cenarios", generated))
        used.update(as_posix(p.relative_to(ROOT)) for p in generated)

    all_maintained = sorted((ROOT / "python").glob("*.py"))
    all_maintained += sorted((ROOT / "dynare").glob("*.mod"))
    all_maintained += sorted((ROOT / "dynare").glob("*.m"))
    extra = [p for p in all_maintained if as_posix(p.relative_to(ROOT)) not in used]
    if extra:
        grouped.append(("Outros codigos mantidos", extra))

    return grouped


def language_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".py":
        return "Python"
    if suffix == ".mod":
        return "Dynare"
    if suffix == ".m":
        return "Octave/MATLAB"
    if path.name == "requirements.txt":
        return "Dependencias"
    return "Texto"


def command_for(path: Path) -> str:
    rel = as_posix(path.relative_to(ROOT))
    if rel == "requirements.txt":
        return "python -m pip install -r requirements.txt"
    if rel.startswith("python/") and rel.endswith(".py"):
        return f"python {rel}"
    if rel == "dynare/run_all_octave.m":
        return "octave-cli dynare/run_all_octave.m"
    if rel == "dynare/run_models.m":
        return "octave-cli dynare/run_models.m"
    if rel.startswith("dynare/export_") and rel.endswith(".m"):
        return "Chamado automaticamente pelos modelos .mod; nao rode diretamente."
    if rel.startswith("dynare/") and rel.endswith(".m"):
        return f"octave-cli {rel}"
    if rel.startswith("dynare/") and rel.endswith(".mod"):
        dynare_rel = rel.removeprefix("dynare/")
        return f"octave-cli --eval \"cd('dynare'); dynare {dynare_rel}\""
    return ""


def file_id(path: Path, index: int) -> str:
    safe = as_posix(path.relative_to(ROOT))
    safe = "".join(ch if ch.isalnum() else "-" for ch in safe)
    return f"code-{index}-{safe}"


def render_copy_button(target: str, label: str = "Copiar") -> str:
    return f'<button class="copy" data-copy="{html.escape(target)}">{html.escape(label)}</button>'


def render_html(groups: list[tuple[str, list[Path]]]) -> str:
    today = dt.date.today().strftime("%d/%m/%Y")
    files = [path for _, paths in groups for path in paths]
    total_lines = 0
    file_cards: list[str] = []
    toc_items: list[str] = []

    for idx, path in enumerate(files, start=1):
        rel = as_posix(path.relative_to(ROOT))
        code = path.read_text(encoding="utf-8", errors="replace").rstrip() + "\n"
        total_lines += code.count("\n")
        cid = file_id(path, idx)
        lang = language_for(path)
        command = command_for(path)
        escaped_code = html.escape(code)
        escaped_command = html.escape(command)
        toc_items.append(f'<li><a href="#{cid}">{html.escape(rel)}</a></li>')

        command_html = ""
        if command:
            command_html = f"""
            <div class="runbox">
              <div class="runlabel">Como rodar / como este arquivo entra no projeto</div>
              <pre><code id="{cid}-cmd">{escaped_command}</code></pre>
              {render_copy_button(f"#{cid}-cmd", "Copiar comando")}
            </div>
            """

        file_cards.append(
            f"""
            <article class="file-card" id="{cid}">
              <header class="file-header">
                <div>
                  <div class="path">{html.escape(rel)}</div>
                  <div class="meta">{lang} · {code.count(chr(10))} linhas</div>
                </div>
                <div class="actions">
                  <a class="open-link" href="#top">Topo</a>
                  {render_copy_button(f"#{cid}-code", "Copiar codigo")}
                </div>
              </header>
              {command_html}
              <pre class="code"><code id="{cid}-code" data-language="{html.escape(lang)}">{escaped_code}</code></pre>
            </article>
            """
        )

    group_cards = []
    cursor = 0
    for title, paths in groups:
        links = []
        for path in paths:
            cursor += 1
            links.append(f'<li><a href="#{file_id(path, cursor)}">{html.escape(as_posix(path.relative_to(ROOT)))}</a></li>')
        group_cards.append(
            f"""
            <section class="group-card">
              <h3>{html.escape(title)}</h3>
              <ul>{''.join(links)}</ul>
            </section>
            """
        )

    pipeline_html = []
    for title, command in PIPELINE_COMMANDS:
        cid = "cmd-" + "".join(ch if ch.isalnum() else "-" for ch in title.lower())
        pipeline_html.append(
            f"""
            <div class="pipeline-step">
              <strong>{html.escape(title)}</strong>
              <pre><code id="{cid}">{html.escape(command)}</code></pre>
              {render_copy_button(f"#{cid}", "Copiar")}
            </div>
            """
        )

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Código Final · Modelo Novo-Keynesiano para o Chile</title>
  <style>
    :root {{
      --bg: #f6f7fb;
      --panel: #ffffff;
      --ink: #172033;
      --muted: #5d687a;
      --line: #d9deea;
      --accent: #173f8a;
      --accent-2: #0f766e;
      --code-bg: #0d1117;
      --code-ink: #e6edf3;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      font-family: Inter, Segoe UI, Roboto, Arial, sans-serif;
      background: var(--bg);
      color: var(--ink);
      line-height: 1.55;
    }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .hero {{
      background: linear-gradient(135deg, #0b1f44, #173f8a 55%, #0f766e);
      color: white;
      padding: 48px min(6vw, 72px);
    }}
    .hero h1 {{ margin: 0 0 12px; font-size: clamp(2rem, 4vw, 3.7rem); line-height: 1.05; }}
    .hero p {{ max-width: 980px; margin: 0; color: #e5edf8; font-size: 1.05rem; }}
    .badges {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 22px; }}
    .badge {{
      display: inline-flex;
      padding: 7px 11px;
      border: 1px solid rgba(255,255,255,.28);
      background: rgba(255,255,255,.12);
      border-radius: 999px;
      font-size: .9rem;
    }}
    main {{ width: min(1380px, calc(100% - 32px)); margin: 28px auto 72px; }}
    .grid {{ display: grid; grid-template-columns: 320px minmax(0, 1fr); gap: 22px; align-items: start; }}
    .sidebar {{ position: sticky; top: 16px; max-height: calc(100vh - 32px); overflow: auto; }}
    .panel, .group-card, .file-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: 0 10px 30px rgba(23,32,51,.06);
    }}
    .panel {{ padding: 18px; margin-bottom: 16px; }}
    .panel h2, .content h2 {{ margin: 0 0 12px; }}
    .panel ul {{ padding-left: 20px; margin: 8px 0; }}
    .panel li {{ margin: 4px 0; }}
    .content {{ display: grid; gap: 22px; }}
    .intro-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }}
    .metric {{ padding: 16px; background: var(--panel); border: 1px solid var(--line); border-radius: 14px; }}
    .metric strong {{ display: block; font-size: 1.7rem; color: var(--accent); }}
    .group-list {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
    .group-card {{ padding: 16px; }}
    .group-card h3 {{ margin: 0 0 8px; color: var(--accent); }}
    .group-card ul {{ margin: 0; padding-left: 20px; }}
    .pipeline-step {{ background: #f8fafc; border: 1px solid var(--line); border-radius: 12px; padding: 12px; margin: 10px 0; }}
    .pipeline-step pre, .runbox pre {{
      white-space: pre-wrap;
      word-break: break-word;
      background: #eef2ff;
      color: #18223a;
      border: 1px solid #d6ddff;
      border-radius: 10px;
      padding: 10px;
      margin: 8px 0;
    }}
    .file-card {{ overflow: hidden; }}
    .file-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 16px;
      padding: 16px 18px;
      border-bottom: 1px solid var(--line);
      background: #fbfcff;
    }}
    .path {{ font-weight: 700; font-family: Consolas, Monaco, monospace; word-break: break-all; }}
    .meta {{ color: var(--muted); font-size: .92rem; margin-top: 4px; }}
    .actions {{ display: flex; gap: 8px; align-items: center; flex-shrink: 0; }}
    .open-link, button.copy {{
      border: 1px solid var(--line);
      background: white;
      color: var(--accent);
      border-radius: 999px;
      padding: 7px 10px;
      font: inherit;
      font-size: .88rem;
      cursor: pointer;
    }}
    button.copy:hover, .open-link:hover {{ background: #eef4ff; text-decoration: none; }}
    .runbox {{ padding: 14px 18px; border-bottom: 1px solid var(--line); background: #fcfcff; }}
    .runlabel {{ font-size: .86rem; color: var(--muted); font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }}
    pre.code {{
      margin: 0;
      padding: 18px;
      overflow-x: auto;
      background: var(--code-bg);
      color: var(--code-ink);
      line-height: 1.45;
      font-size: 12.5px;
      tab-size: 4;
    }}
    pre.code code {{ font-family: Consolas, Cascadia Mono, Monaco, monospace; }}
    .note {{
      border-left: 4px solid var(--accent-2);
      background: #ecfdf5;
      padding: 12px 14px;
      border-radius: 10px;
      margin: 14px 0;
    }}
    @media (max-width: 980px) {{
      .grid, .intro-grid, .group-list {{ grid-template-columns: 1fr; }}
      .sidebar {{ position: static; max-height: none; }}
      .file-header {{ flex-direction: column; }}
    }}
    @media print {{
      .sidebar, .actions, button.copy {{ display: none !important; }}
      main {{ width: 100%; margin: 0; }}
      .grid {{ display: block; }}
      .file-card {{ break-inside: avoid; box-shadow: none; }}
      pre.code {{ white-space: pre-wrap; background: #fff; color: #000; border-top: 1px solid #ccc; }}
    }}
  </style>
</head>
<body id="top">
  <header class="hero">
    <h1>Código Final</h1>
    <p>
      Modelo Novo-Keynesiano de política monetária para o Chile. Este HTML reúne
      o código-fonte mantido do projeto em Python, Dynare e Octave, com comandos
      de execução copiáveis a partir da raiz do repositório.
    </p>
    <div class="badges">
      <span class="badge">Gerado em {html.escape(today)}</span>
      <span class="badge">{len(files)} arquivos</span>
      <span class="badge">{total_lines:,} linhas de código</span>
      <span class="badge">Python + Dynare + Octave</span>
    </div>
  </header>
  <main>
    <div class="grid">
      <aside class="sidebar">
        <section class="panel">
          <h2>Índice dos arquivos</h2>
          <ul>{''.join(toc_items)}</ul>
        </section>
      </aside>
      <section class="content">
        <section class="panel">
          <h2>Como usar este arquivo</h2>
          <p>
            Este é o substituto em HTML do PDF de código final. Ele não tenta
            transformar tudo em um único script, porque o projeto depende de três
            linguagens: Python prepara dados, estima parâmetros, gera tabelas e
            gráficos; Dynare resolve/simula os modelos; Octave executa Dynare e
            auxilia na exportação dos resultados.
          </p>
          <div class="note">
            Rode os comandos abaixo a partir da raiz do projeto:
            <code>{html.escape(as_posix(ROOT))}</code>.
            Os arquivos internos gerados automaticamente pelo Dynare, como pastas
            <code>+nk_chile_base</code>, não entram aqui porque não são código
            mantido do trabalho.
          </div>
        </section>

        <section class="intro-grid">
          <div class="metric"><strong>{len(files)}</strong> arquivos incluídos</div>
          <div class="metric"><strong>{total_lines:,}</strong> linhas de código</div>
          <div class="metric"><strong>{len(groups)}</strong> blocos do pipeline</div>
        </section>

        <section class="panel">
          <h2>Ordem recomendada de reprodução</h2>
          {''.join(pipeline_html)}
        </section>

        <section class="panel">
          <h2>Mapa do código</h2>
          <div class="group-list">{''.join(group_cards)}</div>
        </section>

        {''.join(file_cards)}
      </section>
    </div>
  </main>
  <script>
    async function copyTarget(selector, button) {{
      const node = document.querySelector(selector);
      if (!node) return;
      const text = node.innerText;
      try {{
        await navigator.clipboard.writeText(text);
        const old = button.innerText;
        button.innerText = "Copiado";
        setTimeout(() => button.innerText = old, 1200);
      }} catch (err) {{
        const range = document.createRange();
        range.selectNodeContents(node);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
      }}
    }}
    document.querySelectorAll("button.copy").forEach((button) => {{
      button.addEventListener("click", () => copyTarget(button.dataset.copy, button));
    }});
  </script>
</body>
</html>
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    groups = source_groups()
    html_text = render_html(groups)
    OUT_PRIMARY.write_text(html_text, encoding="utf-8")
    OUT_COMPAT.write_text(html_text, encoding="utf-8")
    nfiles = sum(len(paths) for _, paths in groups)
    print(f"Wrote {OUT_PRIMARY} ({nfiles} files, {OUT_PRIMARY.stat().st_size // 1024} KB).")
    print(f"Wrote {OUT_COMPAT} ({nfiles} files, {OUT_COMPAT.stat().st_size // 1024} KB).")


if __name__ == "__main__":
    main()
