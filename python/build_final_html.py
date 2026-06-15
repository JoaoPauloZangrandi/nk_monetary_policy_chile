"""Build the self-contained, evaluator-facing final HTML report.

The output embeds every public figure, the main result tables, the full source
code, and a detailed Portuguese narrative. No network connection is required
to read the resulting file.
"""

from __future__ import annotations

import base64
import html
import json
from datetime import date
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"
OUTPUT = ROOT / "Entrega Final.html"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def fmt(value: object) -> object:
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        if abs(value) >= 100:
            return f"{value:,.2f}"
        if abs(value) >= 1:
            return f"{value:.3f}"
        if value == 0:
            return "0"
        return f"{value:.6f}"
    return value


def csv_table(
    filename: str,
    *,
    columns: list[str] | None = None,
    query: str | None = None,
    max_rows: int | None = None,
    table_class: str = "",
) -> str:
    path = TABLES / filename
    if not path.exists():
        return f'<div class="warning">Tabela ausente: <code>{esc(filename)}</code>.</div>'
    df = pd.read_csv(path)
    if query:
        df = df.query(query)
    if columns:
        df = df[[column for column in columns if column in df.columns]]
    if max_rows:
        df = df.head(max_rows)
    df = df.map(fmt)
    return df.to_html(index=False, border=0, classes=f"data-table {table_class}".strip(), escape=True)


def image(filename: str, alt: str, caption: str, analysis: str = "") -> str:
    path = FIGURES / filename
    if not path.exists():
        return f'<div class="warning">Figura ausente: <code>{esc(filename)}</code>.</div>'
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    note = f'<div class="figure-analysis">{analysis}</div>' if analysis else ""
    return f"""
    <figure>
      <img src="data:image/png;base64,{encoded}" alt="{esc(alt)}" loading="lazy">
      <figcaption><strong>{esc(caption)}</strong><br><span>Arquivo: outputs/figures/{esc(filename)}</span></figcaption>
      {note}
    </figure>
    """


def callout(kind: str, title: str, body: str) -> str:
    return f'<aside class="callout {esc(kind)}"><strong>{esc(title)}</strong><div>{body}</div></aside>'


def code_details(path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix()
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        source = path.read_text(encoding="latin-1")
    language = {
        ".py": "python",
        ".m": "matlab",
        ".mod": "dynare",
        ".md": "markdown",
        ".txt": "text",
    }.get(path.suffix.lower(), "text")
    lines = source.count("\n") + 1
    return f"""
    <details class="code-file">
      <summary><code>{esc(relative)}</code><span>{lines} linhas</span></summary>
      <pre><code class="language-{language}">{html.escape(source)}</code></pre>
    </details>
    """


def section(section_id: str, kicker: str, title: str, body: str) -> str:
    return f"""
    <section id="{esc(section_id)}">
      <div class="section-kicker">{esc(kicker)}</div>
      <h2>{title}</h2>
      {body}
    </section>
    """


def read_metadata() -> dict:
    path = ROOT / "data" / "clean" / "dataset_metadata.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def build() -> None:
    metadata = read_metadata()
    scenario_manifest = pd.read_csv(TABLES / "scenario_manifest.csv")
    determinacy = pd.read_csv(TABLES / "scenario_determinacy.csv")
    sign_checks = pd.read_csv(TABLES / "irf_sign_checks.csv")
    n_generated_scenarios = len(scenario_manifest)
    n_models = len(determinacy)
    n_determinate = int(determinacy["status"].eq("determinate_bk_count").sum())
    n_signs = int(sign_checks["impact_sign_matches"].astype(str).str.lower().eq("true").sum())

    nav = [
        ("resumo", "Resumo"),
        ("auditoria", "Aderência à aula"),
        ("chile", "Chile e dados"),
        ("glossario", "Conceitos e siglas"),
        ("modelo", "Modelo teórico"),
        ("calibracao", "Calibração"),
        ("solucao", "Dynare e solução"),
        ("momentos", "Momentos e correlações"),
        ("fevd", "FEVD"),
        ("irfs", "IRFs baseline"),
        ("kappa", "Sensibilidade κ"),
        ("phi", "Sensibilidade φπ"),
        ("rho", "Persistência ρi"),
        ("econometria", "Econometria"),
        ("previsoes", "Previsões"),
        ("politica", "Análise monetária"),
        ("limitacoes", "Limitações"),
        ("reproducao", "Reprodução"),
        ("codigo", "Código completo"),
    ]

    parts: list[str] = []
    parts.append(
        section(
            "resumo",
            "Entrega final",
            "Política monetária no Chile em um modelo Novo-Keynesiano",
            f"""
            <p class="lead">Calibração, solução, diagnóstico de determinação, funções
            impulso-resposta, decomposição de variância, econometria e cenários condicionais
            em um projeto reproduzível com <strong>Python, GNU Octave e Dynare</strong>.</p>
            <div class="metric-grid">
              <div class="metric"><span>{metadata.get("observations", 101)}</span><small>trimestres de dados reais</small></div>
              <div class="metric"><span>{n_models}</span><small>modelos Dynare executados</small></div>
              <div class="metric"><span>{n_determinate}/{n_models}</span><small>cenários principais determinados</small></div>
              <div class="metric"><span>{n_signs}/9</span><small>sinais de impacto corretos</small></div>
            </div>
            {callout("success", "Resultado central",
                "O baseline é determinado e seus sinais de impacto são coerentes com a teoria. "
                "Ao mesmo tempo, o confronto com os dados mostra que o modelo pequeno subestima "
                "volatilidades e persistências; por isso, os resultados são um laboratório de "
                "mecanismos, não uma descrição completa ou uma previsão oficial do Chile.")}
            <div class="two-col">
              <div>
                <h3>O que foi feito</h3>
                <ul>
                  <li>Dados oficiais trimestrais do Banco Central de Chile, 2001Q1–2026Q1.</li>
                  <li>Modelo NK linear de três equações resolvido no Dynare 7.1 via Octave 11.1.</li>
                  <li>Baseline e {n_generated_scenarios} cenários gerados para as grades e alternativas.</li>
                  <li>Duas rotas para <code>rho_i</code> e duas calibrações de FEVD.</li>
                  <li>Previsão incondicional e condicionamento por juro e por inflação.</li>
                  <li>Regra de Taylor, NKPC, taxa neutra e moda posterior exploratórias.</li>
                </ul>
              </div>
              <div>
                <h3>Leitura correta</h3>
                <ul>
                  <li>Calibração não é estimação.</li>
                  <li>FEVD calibrada não é decomposição histórica.</li>
                  <li>AR(1) da TPM não identifica sozinho a suavização estrutural.</li>
                  <li>IRFs podem apresentar <em>overshooting</em> sem invalidar o modelo.</li>
                  <li>Cenários condicionais são experimentos internos, não recomendações.</li>
                </ul>
              </div>
            </div>
            """,
        )
    )

    parts.append(
        section(
            "auditoria",
            "Páginas 26–55 da Aula 5",
            "O que o roteiro pediu e como o projeto respondeu",
            f"""
            <p>A revisão foi feita a partir do PDF privado disponível localmente. O texto abaixo é
            uma síntese original: nenhuma página ou passagem foi incorporada ao repositório.</p>
            <div class="audit-grid">
              <article><b>Taxa neutra</b><span>2%, 3% e 4% a.a.; conversão trimestral e beta.</span></article>
              <article><b>Persistência</b><span>AR(1) real e alternativa calibrada em 0,80.</span></article>
              <article><b>Phillips</b><span>κ = 0,07; 0,10; 0,13 com IRFs e custos reais.</span></article>
              <article><b>Regra monetária</b><span>φπ = 1,3,…,2,2 e mapa ampliado de determinação.</span></article>
              <article><b>Choques e FEVD</b><span>Alvo didático e alvo alternativo executados.</span></article>
              <article><b>Previsões</b><span>Incondicional, juro condicionado e inflação condicionada.</span></article>
            </div>
            {callout("info", "Quando o roteiro diz “isto ou aquilo”",
                "A entrega não escolhe silenciosamente uma opção. Ela testa as duas: rho estimado "
                "e calibrado; FEVD didática e alternativa; condicionamento pelo juro e pela inflação.")}
            <h3>Correções resultantes da auditoria</h3>
            <ol>
              <li>Os nove sinais de impacto estão corretos, mas algumas respostas cruzam zero no
              trimestre seguinte. Portanto, não se exige monotonicidade das IRFs.</li>
              <li>Um φπ maior reduz o impacto da inflação, mas eleva o movimento de produto e juro;
              a soma absoluta da inflação pode subir por <em>undershooting</em>.</li>
              <li>O comando de previsão condicional de primeira ordem usa choques controlados não
              antecipados antes de cada período. Isso não é previsão perfeita determinística.</li>
              <li>Momentos e FEVD precisam ser confrontados com dados e identificados como resultados
              internos da calibração.</li>
            </ol>
            <p class="source-note">Documento de auditoria:
            <code>docs/assignment_review_pages_26_55.md</code>.</p>
            """,
        )
    )

    parts.append(
        section(
            "chile",
            "Contexto empírico",
            "Por que Chile, quais dados e quais transformações",
            f"""
            <p>O Chile combina um regime de metas de inflação, uma taxa de política claramente
            identificada e séries oficiais acessíveis. A meta é interpretada como inflação projetada
            de 3% em horizonte de dois anos. A variável operacional é a <strong>TPM</strong>
            (Tasa de Política Monetaria). Esse ambiente é adequado para ilustrar o núcleo de um
            modelo NK, embora o caráter de economia pequena e aberta seja uma limitação decisiva.</p>
            <div class="three-col">
              <article class="card"><h3>TPM</h3><p>Série diária, convertida em média trimestral e
              em taxa trimestral composta.</p><code>F022.TPM.TIN.D001.NO.Z.D</code></article>
              <article class="card"><h3>IPC</h3><p>Variação mensal composta dentro do trimestre e
              anualizada para apresentação.</p><code>F074.IPC.VAR.Z.Z.C.M</code></article>
              <article class="card"><h3>PIB real</h3><p>Log do PIB dessazonalizado; ciclo do filtro HP
              com λ=1600 usado como hiato.</p><code>F032.PIB.FLU.R.CLP.EP18.Z.Z.1.T</code></article>
            </div>
            {image("data_overview.png", "TPM, inflação e hiato do produto no Chile",
                "Figura 1 — Dados trimestrais utilizados",
                "A amostra cobre 101 trimestres. A pandemia produz um hiato extremo em 2020Q2, "
                "enquanto o ciclo inflacionário de 2021–2023 é acompanhado por forte elevação da TPM. "
                "Esses episódios explicam por que momentos de amostra e estimações são sensíveis ao período.")}
            <h3>Proveniência e unidades</h3>
            <table class="data-table">
              <thead><tr><th>Item</th><th>Valor</th></tr></thead>
              <tbody>
                <tr><td>Instituição</td><td>{esc(metadata.get("institution", "BCCh"))}</td></tr>
                <tr><td>Período</td><td>{esc(metadata.get("period", ""))}</td></tr>
                <tr><td>Observações</td><td>{esc(metadata.get("observations", ""))}</td></tr>
                <tr><td>Acesso</td><td>{esc(metadata.get("access_date", ""))}</td></tr>
                <tr><td>Base sintética?</td><td><strong>{esc(metadata.get("is_synthetic", ""))}</strong></td></tr>
                <tr><td>Transformações</td><td>{esc(metadata.get("transformations", ""))}</td></tr>
              </tbody>
            </table>
            {callout("warning", "Hiato do produto não é observado",
                "O filtro HP separa tendência e ciclo mecanicamente e sofre viés de ponta. O hiato "
                "resultante é uma proxy, não uma medida estrutural inequívoca de capacidade ociosa.")}
            """,
        )
    )

    glossary = [
        ("NK", "Novo-Keynesiano: estrutura com expectativas racionais, rigidez nominal e política monetária."),
        ("DSGE", "Modelo dinâmico estocástico de equilíbrio geral; o modelo desta entrega é um núcleo DSGE mínimo."),
        ("IS", "Equação de demanda intertemporal que liga hiato ao juro real ex ante."),
        ("NKPC", "New Keynesian Phillips Curve: curva de Phillips prospectiva."),
        ("Calvo", "Mecanismo em que apenas uma fração das firmas pode reajustar preços a cada período."),
        ("EIS", "Elasticidade intertemporal de substituição; no modelo é inversamente relacionada a sigma."),
        ("TPM", "Tasa de Política Monetaria do Banco Central de Chile."),
        ("BCCh", "Banco Central de Chile."),
        ("IPC", "Índice de Preços ao Consumidor."),
        ("PIB", "Produto Interno Bruto."),
        ("IRF", "Impulse Response Function: trajetória após um choque isolado."),
        ("FEVD", "Forecast Error Variance Decomposition: parcela da variância atribuída a cada choque."),
        ("BK", "Condições de Blanchard-Kahn para existência e unicidade da solução racional."),
        ("MQO/OLS", "Mínimos Quadrados Ordinários / Ordinary Least Squares."),
        ("HAC", "Matriz de covariância robusta a heterocedasticidade e autocorrelação."),
        ("Newey-West", "Estimador HAC usado nos erros-padrão das regressões."),
        ("VI/IV", "Variáveis instrumentais, usadas quando regressores podem ser endógenos."),
        ("2SLS", "Mínimos Quadrados em Dois Estágios."),
        ("MAP", "Moda a posteriori: ponto de maior densidade posterior."),
        ("Laplace", "Aproximação local gaussiana da incerteza em torno da moda."),
        ("MCMC", "Simulação de Monte Carlo via cadeias de Markov para a distribuição posterior."),
        ("HPD", "Intervalo de maior densidade posterior."),
        ("HP", "Filtro Hodrick-Prescott, aqui com lambda 1600 para dados trimestrais."),
        ("UIP", "Paridade descoberta de juros, ausente no modelo fechado."),
        ("SVAR", "Vetor autorregressivo estrutural, alternativa empírica para identificar choques."),
        ("p.b.", "Ponto-base: 0,01 ponto percentual."),
    ]
    glossary_html = "".join(
        f"<dt>{esc(term)}</dt><dd>{esc(definition)}</dd>" for term, definition in glossary
    )
    parts.append(
        section(
            "glossario",
            "Base conceitual",
            "Glossário de conceitos, parâmetros e siglas",
            f"""
            <dl class="glossary">{glossary_html}</dl>
            <h3>Parâmetros e objetos do modelo</h3>
            <div class="parameter-grid">
              <article><b>β</b><span>Fator de desconto. Quanto maior, maior o peso do futuro.</span></article>
              <article><b>σ</b><span>Inverso da EIS. Regula a sensibilidade da demanda ao juro real.</span></article>
              <article><b>κ</b><span>Inclinação da NKPC. Transmissão do hiato para inflação.</span></article>
              <article><b>ρ<sub>i</sub></b><span>Persistência/suavização da taxa de política.</span></article>
              <article><b>φ<sub>π</sub></b><span>Resposta de longo prazo do juro à inflação.</span></article>
              <article><b>φ<sub>x</sub></b><span>Resposta de longo prazo do juro ao hiato.</span></article>
              <article><b>r*</b><span>Taxa real neutra compatível com equilíbrio no modelo.</span></article>
              <article><b>e<sub>x</sub></b><span>Choque de demanda ou preferência.</span></article>
              <article><b>e<sub>π</sub></b><span>Choque de custo/markup.</span></article>
              <article><b>e<sub>i</sub></b><span>Inovação monetária não explicada pela regra.</span></article>
            </div>
            <h3>Dinâmica e solução</h3>
            <p><strong>Variável predeterminada</strong> tem seu valor corrente herdado do passado;
            aqui, <code>i(-1)</code>. <strong>Variáveis de salto</strong> podem reagir imediatamente
            às notícias; aqui, <code>x</code> e <code>pi</code>. Um <strong>autovalor estável</strong>
            tem módulo menor que um. A determinação exige que o número de raízes instáveis seja
            igual ao número de variáveis prospectivas.</p>
            <p><strong>Momento</strong> é uma característica da distribuição, como média, variância,
            desvio-padrão, correlação ou autocorrelação. <strong>Convergência</strong> descreve o
            retorno à vizinhança do estado estacionário. <strong>Overshooting</strong> ou
            <strong>undershooting</strong> ocorre quando a variável cruza seu nível de equilíbrio
            antes de convergir.</p>
            """,
        )
    )

    parts.append(
        section(
            "modelo",
            "Estrutura teórica",
            "As três equações e a transmissão monetária",
            """
            <div class="equation">x<sub>t</sub> = E<sub>t</sub>x<sub>t+1</sub>
            − (1/σ)[i<sub>t</sub> − E<sub>t</sub>π<sub>t+1</sub> − r*] + e<sub>x,t</sub></div>
            <div class="equation">π<sub>t</sub> = βE<sub>t</sub>π<sub>t+1</sub>
            + κx<sub>t</sub> + e<sub>π,t</sub></div>
            <div class="equation">i<sub>t</sub> = ρ<sub>i</sub>i<sub>t−1</sub>
            + (1−ρ<sub>i</sub>)[r* + φ<sub>π</sub>π<sub>t</sub>
            + φ<sub>x</sub>x<sub>t</sub>] + e<sub>i,t</sub></div>
            <div class="three-col">
              <article class="card"><h3>Curva IS</h3><p>Se o juro real ex ante supera r*, adiar
              consumo fica relativamente atraente e a demanda corrente cai. Expectativas futuras
              afetam a decisão hoje.</p></article>
              <article class="card"><h3>Curva de Phillips</h3><p>Firmas que não reajustam preços
              tornam a inflação dependente do custo marginal, aproximado pelo hiato, e da inflação
              esperada.</p></article>
              <article class="card"><h3>Regra de Taylor</h3><p>O banco central reage à inflação e
              atividade, mas suaviza alterações da taxa. O princípio de Taylor requer resposta
              nominal suficiente para elevar o juro real.</p></article>
            </div>
            <h3>Cadeias de transmissão</h3>
            <ul>
              <li><b>Demanda positiva:</b> x sobe → π sobe → regra eleva i → juro real freia x.</li>
              <li><b>Custo positivo:</b> π sobe e x cai sob aperto → surge o trade-off de estabilização.</li>
              <li><b>Aperto monetário:</b> i sobe → juro real sobe → x cai → π cai.</li>
            </ul>
            <h3>Estado estacionário e unidades</h3>
            <p>Na representação do arquivo principal, <code>x=0</code>, <code>pi=0</code> e
            <code>i=rstar</code>. As IRFs são convertidas para pontos percentuais. Para previsões em
            nível, inflação recebe de volta a meta de 3% e o juro recebe o neutro nominal de 6,09%,
            composto a partir de r* real de 3% e meta de inflação de 3%.</p>
            """,
        )
    )

    parts.append(
        section(
            "calibracao",
            "Parâmetro ↔ alvo",
            "Calibração, taxa neutra, beta e persistência",
            f"""
            <h3>Mapa de parâmetros</h3>
            {csv_table("parameter_targets.csv")}
            <h3>Taxa neutra anual, taxa trimestral e beta</h3>
            {csv_table("rstar_beta_table.csv")}
            <p>A conversão é <code>rstar_q = (1+rstar_annual)^(1/4)-1</code> e
            <code>beta = 1/(1+rstar_q)</code>. Elevar r* de 2% para 4% reduz beta de 0,99506 para
            0,99024. Esses são cenários; não são três estimativas concorrentes da taxa neutra chilena.</p>
            <h3>AR(1) da TPM</h3>
            {csv_table("rhoi_estimate.csv", columns=[
                "rho_i_estimate", "rho_i_se_hac", "rho_i_ci95_low", "rho_i_ci95_high",
                "half_life_quarters", "r_squared", "observations", "sample_start", "sample_end"
            ])}
            {callout("warning", "Persistência reduzida não é parâmetro estrutural puro",
                "O valor 0,934 descreve a inércia da TPM observada. Mudanças de regime, movimentos "
                "do neutro e resposta sistemática a inflação e atividade também afetam o AR(1).")}
            """,
        )
    )

    parts.append(
        section(
            "solucao",
            "Octave + Dynare",
            "Pré-processamento, estado estacionário e Blanchard-Kahn",
            f"""
            <p>O Dynare pré-processa o arquivo <code>.mod</code>, monta as equações estáticas e
            dinâmicas, calcula o estado estacionário, lineariza o sistema e aplica uma decomposição
            generalizada para obter a solução racional de primeira ordem. O comando
            <code>check;</code> reporta os autovalores; <code>stoch_simul(order=1, irf=20);</code>
            calcula momentos, FEVD e IRFs.</p>
            <div class="metric-grid">
              <div class="metric"><span>0,656</span><small>raiz estável dominante</small></div>
              <div class="metric"><span>1,040</span><small>menor raiz instável</small></div>
              <div class="metric"><span>2</span><small>raízes instáveis</small></div>
              <div class="metric"><span>2</span><small>variáveis forward-looking</small></div>
            </div>
            {callout("success", "Condição de Blanchard-Kahn satisfeita",
                "Há exatamente duas raízes fora do círculo unitário para x e pi, as duas variáveis "
                "prospectivas. O baseline possui solução local única e estável.")}
            {image("determinacy_map.png", "Mapa de determinação por phi pi",
                "Figura 2 — Determinação na grade ampliada de φπ",
                "A fronteira numérica ocorre em torno de φπ=1 para esta parametrização. A grade "
                "principal de 1,3 a 2,2 é inteiramente determinada; o ganho marginal passa a ser "
                "avaliado pela dinâmica e pelo custo em produto e juros.")}
            <h3>Diagnóstico de todos os cenários</h3>
            {csv_table("scenario_determinacy.csv", columns=[
                "scenario", "status", "n_forward", "n_unstable",
                "dominant_stable_modulus", "convergence_half_life_quarters",
                "smallest_unstable_modulus"
            ])}
            """,
        )
    )

    parts.append(
        section(
            "momentos",
            "Ajuste quantitativo",
            "Momentos teóricos, dados e correlações",
            f"""
            {image("moments_model_vs_data.png", "Momentos do modelo comparados aos dados",
                "Figura 3 — Volatilidade e autocorrelação",
                "O modelo subestima fortemente a volatilidade. Mesmo retirando 2020Q2–2021Q4, "
                "o hiato observado continua mais volátil. A TPM empírica também é bem mais "
                "persistente do que o juro endógeno do modelo.")}
            {csv_table("moments_model_vs_data.csv")}
            <h3>Correlações contemporâneas</h3>
            {csv_table("correlations_model_vs_data.csv")}
            <p>O baseline produz correlação negativa entre juro e hiato porque um aperto contrai
            atividade. Nos dados, a correlação incondicional é positiva: o banco central também
            sobe juros quando a economia e a inflação estão fortes. Essa inversão ilustra por que
            correlação observada não identifica causalidade monetária.</p>
            {callout("info", "O objetivo não é maximizar ajuste",
                "A calibração de choques prioriza uma FEVD transparente e IRFs plausíveis. Uma "
                "estimação completa exigiria mais fricções, observáveis, regimes e tratamento de outliers.")}
            """,
        )
    )

    parts.append(
        section(
            "fevd",
            "Decomposição de variância",
            "Duas metas de FEVD e o que elas significam",
            f"""
            {image("fevd_calibration_comparison.png", "FEVD calibrada em duas metas",
                "Figura 4 — Meta versus FEVD alcançada",
                "Com três desvios-padrão não se ajustam livremente nove parcelas. A calibração "
                "minimiza o erro conjunto. A matriz alternativa tem RMSE de 0,95 p.p.; a didática, "
                "1,82 p.p. Ambas reproduzem a narrativa de inflação dominada por custo e juro "
                "dominado por inovação monetária.")}
            <h3>Desvios-padrão resultantes</h3>
            {csv_table("shock_sigmas_comparison.csv")}
            <h3>Alvo e resultado, célula por célula</h3>
            {csv_table("fevd_calibration_comparison.csv")}
            <h3>FEVD baseline</h3>
            {csv_table("fevd_summary.csv")}
            <p>No baseline, o hiato é explicado em aproximadamente 45% por demanda e 45% por
            política; a inflação, em 80% pelo choque de custo; o juro, em 75% pelo choque monetário.
            Isso valida o procedimento de calibração, mas não demonstra que esses percentuais
            descrevem historicamente o Chile.</p>
            """,
        )
    )

    parts.append(
        section(
            "irfs",
            "Mecanismos dinâmicos",
            "IRFs do baseline: todos os choques e todas as variáveis",
            f"""
            {image("irf_baseline_all_shocks.png", "Grade 3 por 3 de IRFs do baseline",
                "Figura 5 — Respostas a demanda, custo e política monetária",
                "Todos os sinais de impacto correspondem à teoria. Demanda positiva eleva x, pi e i; "
                "custo positivo eleva pi e i e reduz x; aperto monetário eleva i e reduz x e pi. "
                "As reversões de sinal no horizonte 1 em algumas respostas são overshooting, não erro.")}
            <h3>Checagem automática dos sinais</h3>
            {csv_table("irf_sign_checks.csv")}
            <div class="three-col">
              <article class="card"><h3>Choque de demanda</h3><p>Impactos: x +0,400 p.p.,
              π +0,021 p.p., i +0,016 p.p. A reação da política faz x e π cruzarem zero no
              trimestre seguinte.</p></article>
              <article class="card"><h3>Choque de custo</h3><p>Impactos: π +0,236 p.p.,
              x −0,144 p.p., i +0,022 p.p. É o trade-off de estabilização: reduzir inflação
              requer contração real.</p></article>
              <article class="card"><h3>Choque monetário</h3><p>Impactos: i +0,048 p.p.,
              x −0,307 p.p., π −0,088 p.p. A inflação cai imediatamente na solução prospectiva.</p></article>
            </div>
            <h3>Forma reduzida da política de decisão</h3>
            {csv_table("policy_transition_coefficients.csv")}
            <p>Os coeficientes unitários explicam como o estado <code>i(-1)</code> e cada inovação
            movem as variáveis. A coluna calibrada multiplica cada resposta pelo desvio-padrão do
            choque e coincide com o impacto das IRFs.</p>
            """,
        )
    )

    parts.append(
        section(
            "kappa",
            "Rigidez de preços",
            "Sensibilidade a κ = 0,07; 0,10; 0,13",
            f"""
            {image("irf_kappa_comparison.png", "Inflação sob três valores de kappa",
                "Figura 6 — Resposta da inflação a um choque de demanda",
                "Quanto maior κ, mais rapidamente a atividade se converte em inflação. O impacto "
                "sobe de 0,0145 para 0,0279 p.p. quando κ passa de 0,07 para 0,13.")}
            {image("irf_kappa_tradeoffs.png", "Trade-offs de kappa",
                "Figura 7 — Efeitos de κ em diferentes choques",
                "Após choque de custo, κ maior reduz o impacto inflacionário e o custo real "
                "acumulado. Após demanda ou política, porém, preços mais flexíveis transmitem mais "
                "fortemente a atividade para inflação.")}
            <ul>
              <li>Inflação de impacto após demanda: 0,0145 → 0,0212 → 0,0279 p.p.</li>
              <li>Inflação de impacto após custo: 0,2451 → 0,2357 → 0,2276 p.p.</li>
              <li>Custo real acumulado após custo: 0,4627 → 0,4187 → 0,3851 p.p.</li>
              <li>Raiz estável dominante: 0,6869 → 0,6561 → 0,6301.</li>
            </ul>
            <p>A leitura monetária correta depende do choque. Uma Phillips mais inclinada facilita
            a desinflação induzida pela contração do hiato, mas também faz choques de demanda
            aparecerem mais rapidamente nos preços.</p>
            """,
        )
    )

    parts.append(
        section(
            "phi",
            "Princípio de Taylor",
            "Sensibilidade a φπ de 1,3 a 2,2",
            f"""
            {image("irf_phi_pi_comparison.png", "Inflação sob diferentes phi pi",
                "Figura 8 — Resposta da inflação ao choque de custo",
                "A reação mais forte reduz o impacto inicial, mas produz maior reversão posterior. "
                "Por isso, o pico e a soma absoluta contam histórias diferentes.")}
            {image("irf_phi_pi_tradeoffs.png", "Trade-offs de phi pi",
                "Figura 9 — Inflação, produto, juro e convergência",
                "Entre 1,3 e 2,2, o impacto da inflação cai de 0,2423 para 0,2303 p.p. e a "
                "convergência acelera pouco. Em troca, os movimentos acumulados de juro e hiato "
                "sobem de 0,0501 para 0,0796 e de 0,3519 para 0,4734 p.p.")}
            {callout("warning", "Mais reação não melhora toda métrica",
                "A soma absoluta da inflação cresce ligeiramente, de 0,3107 para 0,3167 p.p., "
                "devido ao undershooting. A conclusão robusta é menor impacto inicial com maior "
                "custo real e financeiro, não estabilização uniforme.")}
            <p>Todos os valores da grade principal satisfazem BK. O mapa ampliado mostra
            indeterminação abaixo do limiar numérico em torno de um. Esse limiar depende de toda a
            parametrização, não apenas de uma regra verbal sobre φπ.</p>
            """,
        )
    )

    parts.append(
        section(
            "rho",
            "Gradualismo",
            "ρi estimado em 0,934 versus calibrado em 0,80",
            f"""
            {image("irf_rho_comparison.png", "Comparação de IRFs por rho i",
                "Figura 10 — Persistência estimada e calibrada",
                "A maior persistência estende os efeitos do choque monetário. No baseline, os "
                "efeitos acumulados absolutos sobre inflação e hiato são aproximadamente quatro "
                "e três vezes os do cenário com rho=0,80.")}
            <table class="data-table">
              <thead><tr><th>Resposta ao choque monetário</th><th>ρ=0,934</th><th>ρ=0,80</th></tr></thead>
              <tbody>
                <tr><td>Juro, soma absoluta</td><td>0,1388 p.p.</td><td>0,0976 p.p.</td></tr>
                <tr><td>Inflação, soma absoluta</td><td>0,2555 p.p.</td><td>0,0592 p.p.</td></tr>
                <tr><td>Hiato, soma absoluta</td><td>0,8911 p.p.</td><td>0,2777 p.p.</td></tr>
                <tr><td>Meia-vida da raiz estável</td><td>1,645 trim.</td><td>1,107 trim.</td></tr>
              </tbody>
            </table>
            <p>Esta é uma das análises “ou/ou” executadas dos dois modos. O valor estimado é mais
            aderente à persistência bruta da TPM, enquanto 0,80 separa melhor uma calibração
            estrutural convencional. A diferença entre eles é economicamente grande.</p>
            """,
        )
    )

    parts.append(
        section(
            "econometria",
            "Evidência complementar",
            "Regra de Taylor, NKPC, r* e moda posterior",
            f"""
            <h3>Regra de Taylor reduzida</h3>
            {csv_table("taylor_rule_estimates.csv")}
            <p>MQO-HAC sugere φπ=0,83; VI/2SLS-HAC, 3,05. O primeiro estágio da inflação tem
            F=5,82, sinal de instrumento potencialmente fraco. A divergência não autoriza escolher
            mecanicamente a estimativa mais compatível com a teoria; ela revela identificação frágil.</p>
            <h3>Curva de Phillips</h3>
            {csv_table("nkpc_estimates.csv")}
            <p>A especificação backward encontra κ≈0,098, próximo da calibração. A versão forward
            apresenta sinal negativo, erro-padrão elevado e primeiro estágio fraco. Isso não valida
            empiricamente a NKPC prospectiva; apenas mostra que a grade escolhida é compatível com
            uma relação reduzida backward.</p>
            <h3>Referências empíricas para r*</h3>
            {csv_table("rstar_estimates.csv")}
            <p>A tendência HP do juro real é uma proxy descritiva, sujeita a viés de ponta. Uma
            estimativa estrutural de r* exigiria espaço de estados e dinâmica de produto potencial.</p>
            <h3>Moda posterior do DSGE</h3>
            {csv_table("bayesian_estimates.csv")}
            {callout("warning", "MAP não é posterior completo",
                "Como mh_replic=0, não há cadeias MCMC. Os intervalos são aproximações locais de "
                "Laplace em torno da moda e podem ser pouco informativos fora dessa vizinhança.")}
            """,
        )
    )

    parts.append(
        section(
            "previsoes",
            "Exercícios prospectivos",
            "Previsão incondicional e duas formas de condicionamento",
            f"""
            <p>A previsão é gerada pelo próprio Dynare, como nas páginas 48–55 da aula. O comando
            <code>estimation(datafile=..., mode_compute=0, forecast=8)</code> mantém a calibração
            fixa, roda o filtro/suavizador de Kalman sobre o histórico e projeta oito trimestres à
            frente, devolvendo <code>oo_.forecast.Mean</code> e as bandas <code>HPDinf/HPDsup</code>.
            Os observáveis são desvios da média amostral; aqui as séries voltam ao nível anualizado
            (TPM média 4,09% a.a.; inflação média 3,79% a.a.; meta oficial de 3%).</p>
            {image("forecast_fanchart.png", "Fan chart da previsão incondicional",
                "Figura 11 — Cenário incondicional (Dynare) e bandas HPD",
                "Partindo do estado suavizado do último trimestre, o modelo projeta inflação de "
                "3,30% no primeiro horizonte convergindo para 3,76% no oitavo, e a TPM caindo de "
                "4,36% para ~4,11% (a média amostral). As bandas são as faixas de credibilidade do "
                "próprio Dynare, dadas as variâncias dos choques calibrados.")}
            {image("conditional_scenarios.png", "Cenários condicionais para juro e inflação",
                "Figura 12 — Caminhos condicionados (conditional_forecast)",
                "As duas formas de condicionamento da aula: controlar a TPM (manter em 4,5% por 2 "
                "trimestres; apertar para ~5,1% por 4) e controlar a inflação (forçar a meta de 3% "
                "por 4 trimestres). Os caminhos estão ancorados no estado atual via a forma reduzida "
                "exata, idêntica à solução do Dynare.")}
            {image("conditional_policy_shocks.png", "Choques monetários implícitos",
                "Figura 13 — Inovações e_i necessárias para cumprir as restrições",
                "Os choques implícitos tornam explícito o custo de impor cada caminho: o aperto de "
                "~5,1% exige a maior inovação inicial; forçar a inflação à meta de 3% exige um "
                "aperto pontual mais modesto.")}
            <h3>Resumo numérico dos horizontes 1, 4 e 8</h3>
            {csv_table("forecast_summary.csv", columns=[
                "horizon", "date", "scenario", "variable", "value_level",
                "p05_level", "p95_level", "implied_e_i_q"
            ])}
            {callout("danger", "Não interpretar como previsão oficial",
                "O modelo não carrega separadamente o último x e a última pi observados (o único "
                "estado é a taxa passada), não contém câmbio, cobre ou condições externas e não "
                "incorpora julgamento do BCCh. Por não ter inércia de inflação, a projeção reverte "
                "rápido à média — é um laboratório mecânico, não previsão perfeita.")}
            """,
        )
    )

    parts.append(
        section(
            "politica",
            "Síntese econômica",
            "Revisão aprofundada da análise monetária",
            """
            <h3>1. Determinação e credibilidade</h3>
            <p>A determinação requer que expectativas privadas sejam ancoradas por uma regra
            suficientemente ativa. No baseline, φπ=1,75 coloca o sistema acima da fronteira BK.
            Entretanto, a evidência reduzida para o Chile é ampla: MQO, VI e MAP não entregam um
            mesmo número. A conclusão correta é que a calibração representa um regime ativo
            plausível, não uma estimativa pontual incontroversa da reação do BCCh.</p>

            <h3>2. Gradualismo e horizonte de transmissão</h3>
            <p>O AR(1) elevado faz os movimentos da TPM durarem e amplia o efeito acumulado de uma
            inovação monetária. Isso é consistente com decisões graduais e comunicação por
            trajetórias, mas o AR(1) também absorve mudanças lentas do neutro e persistência dos
            próprios fundamentos. A comparação com ρ=0,80 mostra que a escolha altera
            substancialmente a transmissão.</p>

            <h3>3. Choques de custo e o trade-off</h3>
            <p>Quando a inflação sobe por custo, elevar juros reduz demanda, mas não remove
            diretamente o choque. A inflação cai ao custo de hiato negativo. Um φπ mais alto reduz
            o impacto inicial e acelera pouco a convergência, mas aprofunda a contração. O
            undershooting mostra que “mais agressivo” não equivale automaticamente a menor
            variabilidade total.</p>

            <h3>4. Rigidez nominal e razão de sacrifício</h3>
            <p>Com κ maior, uma dada contração do hiato produz mais desinflação; por isso, o custo
            real do choque de custo cai. Mas a mesma inclinação faz expansões de demanda aparecerem
            mais rapidamente nos preços. A estrutura da inflação determina tanto a eficácia quanto
            o custo da política.</p>

            <h3>5. Taxa neutra e postura da política</h3>
            <p>A postura não deve ser avaliada apenas pelo nível nominal da TPM. É necessário
            compará-la com inflação esperada e r*. No exercício prospectivo, r*=3% e meta de 3%
            implicam neutro nominal de 6,09%. Essa hipótese faz 4,5% parecer expansionista. Como r*
            é incerto e variável no tempo, a conclusão é condicional à calibração, não avaliação
            histórica definitiva.</p>

            <h3>6. FEVD, narrativa e identificação</h3>
            <p>A FEVD foi desenhada para uma narrativa transparente: inflação majoritariamente por
            custo, taxa por inovação monetária e hiato por demanda e política. Ela organiza o
            experimento, mas não identifica choques chilenos. Para uma afirmação histórica seriam
            necessárias restrições de identificação, dados adicionais e comparação com SVAR ou
            DSGE estimado.</p>

            <h3>7. Implicação para o Chile</h3>
            <p>O núcleo NK ajuda a pensar expectativas, gradualismo e trade-offs, mas omite canais
            centrais de uma economia pequena e aberta. Câmbio, preço do cobre, prêmio de risco,
            inflação importada e demanda externa podem alterar tanto a origem quanto a transmissão
            da inflação. A recomendação metodológica é usar este modelo como benchmark e não como
            sistema completo para prescrição.</p>
            """,
        )
    )

    parts.append(
        section(
            "limitacoes",
            "Escopo e honestidade",
            "O que a entrega não demonstra",
            """
            <div class="two-col">
              <div>
                <h3>Limitações econômicas</h3>
                <ul>
                  <li>Economia fechada: sem câmbio, UIP, cobre, termos de troca ou risco-país.</li>
                  <li>Sem indexação, hábitos, capital, salários rígidos ou fricções financeiras.</li>
                  <li>r* constante e hiato obtido por filtro estatístico.</li>
                  <li>Uma única regra linear para regimes monetários distintos.</li>
                </ul>
              </div>
              <div>
                <h3>Limitações empíricas</h3>
                <ul>
                  <li>Covid-19 é um outlier grande para amostra e filtro.</li>
                  <li>Instrumentos fracos na NKPC forward e na inflação da regra de Taylor.</li>
                  <li>MAP sem MCMC e intervalos apenas locais.</li>
                  <li>Choques calibrados, não identificados por likelihood no baseline.</li>
                </ul>
              </div>
            </div>
            <h3>Extensões prioritárias</h3>
            <ol>
              <li>Modelo NK de economia aberta com câmbio, inflação importada e prêmio de risco.</li>
              <li>r* e produto potencial em espaço de estados.</li>
              <li>Estimação bayesiana completa com MCMC, erros de medida e tratamento da pandemia.</li>
              <li>Identificação externa ou SVAR para comparar choques monetários e de oferta.</li>
              <li>Avaliação fora da amostra das previsões e comparação com projeções do BCCh.</li>
            </ol>
            """,
        )
    )

    parts.append(
        section(
            "reproducao",
            "Projeto reproduzível",
            "Arquitetura, comandos e verificações",
            """
            <div class="pipeline">
              <span>BCCh API</span><b>→</b><span>dados trimestrais</span><b>→</b>
              <span>estimações</span><b>→</b><span>calibração</span><b>→</b>
              <span>modelos .mod</span><b>→</b><span>Octave + Dynare</span><b>→</b>
              <span>tabelas, figuras e HTML</span>
            </div>
            <h3>Execução completa a partir da raiz</h3>
            <pre><code>python -m pip install -r requirements.txt
python python/build_chile_dataset.py
python python/estimate_rhoi_chile.py
python python/estimate_taylor_rule.py
python python/estimate_nkpc.py
python python/estimate_rstar.py
python python/calibrate_shocks.py
python python/make_tables.py
python python/generate_dynare_models.py
python python/run_dynare_batch.py --all --timeout 300
python python/run_bayesian.py
python python/collect_outputs.py
python python/analyze_determinacy.py
python python/analyze_model_results.py
python python/run_forecast.py
python python/forecast_model.py
python python/plot_irfs.py
python python/build_final_html.py</code></pre>
            <h3>Tratamento do Windows e OneDrive</h3>
            <p>O runner copia os modelos para uma pasta temporária com caminho ASCII antes de
            iniciar o Octave. Isso evita travamentos do pré-processador do Dynare ao criar e
            renomear pastas em caminhos sincronizados, com espaços e acentos. Resultados CSV são
            copiados de volta para <code>outputs/dynare/</code>.</p>
            <h3>Checklist</h3>
            <ul class="checklist">
              <li>Dados marcados como reais em <code>dataset_metadata.json</code>.</li>
              <li>19 modelos com saídas Dynare e diagnóstico BK.</li>
              <li>13 figuras públicas incorporadas neste arquivo.</li>
              <li>Tabelas carregadas diretamente dos CSVs produzidos pelo pipeline.</li>
              <li>Código integral incorporado abaixo.</li>
              <li>PDF privado e credenciais fora do versionamento.</li>
            </ul>
            """,
        )
    )

    python_files = sorted((ROOT / "python").glob("*.py"))
    dynare_core = sorted(
        path for path in (ROOT / "dynare").iterdir()
        if path.is_file() and path.suffix.lower() in {".m", ".mod"}
    )
    generated_mods = sorted((ROOT / "dynare" / "generated").glob("*.mod"))
    code_blocks = [
        "<h3>Python</h3>",
        *(code_details(path) for path in python_files),
        "<h3>Octave e Dynare: arquivos centrais</h3>",
        *(code_details(path) for path in dynare_core),
        "<h3>Dynare: cenários gerados</h3>",
        *(code_details(path) for path in generated_mods),
        "<h3>Configuração</h3>",
        code_details(ROOT / "requirements.txt"),
    ]
    parts.append(
        section(
            "codigo",
            "Apêndice técnico",
            "Código-fonte integral usado na entrega",
            """
            <p>Cada bloco é expansível. Os arquivos são incorporados como texto no momento da
            geração do HTML; portanto, este apêndice representa exatamente a versão usada para
            produzir as tabelas e figuras desta entrega.</p>
            <div class="code-toolbar">
              <button type="button" onclick="toggleAll(true)">Expandir todos</button>
              <button type="button" onclick="toggleAll(false)">Recolher todos</button>
              <input id="codeSearch" type="search" placeholder="Filtrar arquivos..." oninput="filterCode(this.value)">
            </div>
            """
            + "\n".join(code_blocks),
        )
    )

    nav_html = "".join(f'<a href="#{sid}">{esc(label)}</a>' for sid, label in nav)
    body = "\n".join(parts)
    styles = """
    :root{--ink:#132238;--muted:#5d6b7d;--paper:#f5f1e8;--card:#fffdf8;--navy:#0d3558;
    --blue:#1b668f;--teal:#19756f;--gold:#bd7d16;--red:#a53c35;--line:#d8d1c3;
    --shadow:0 12px 36px rgba(20,35,52,.10)}
    *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);
    color:var(--ink);font:16px/1.67 "Segoe UI",Arial,sans-serif}
    header{min-height:76vh;padding:8rem max(6vw,2rem) 5rem;color:white;position:relative;overflow:hidden;
    background:linear-gradient(125deg,#071d31 0%,#0d3f63 52%,#16756f 100%)}
    header:after{content:"";position:absolute;right:-12vw;top:-12vw;width:46vw;height:46vw;
    border:1px solid rgba(255,255,255,.2);border-radius:50%;box-shadow:0 0 0 5vw rgba(255,255,255,.025),
    0 0 0 11vw rgba(255,255,255,.02)}.eyebrow{letter-spacing:.18em;text-transform:uppercase;
    font-weight:700;color:#a6e4dc}h1{font-family:Georgia,serif;font-size:clamp(3rem,7vw,6.8rem);
    max-width:1100px;line-height:1.02;margin:.4rem 0 1.5rem}.subtitle{font-size:1.3rem;max-width:780px;
    color:#dceaf2}.cover-meta{display:flex;gap:1rem;flex-wrap:wrap;margin-top:2rem}
    .cover-meta span{border:1px solid rgba(255,255,255,.35);padding:.45rem .8rem;border-radius:999px}
    nav{position:sticky;top:0;z-index:20;background:rgba(255,253,248,.96);backdrop-filter:blur(12px);
    border-bottom:1px solid var(--line);display:flex;gap:.2rem;overflow-x:auto;padding:.55rem 2vw;
    box-shadow:0 3px 15px rgba(0,0,0,.05)}nav a{white-space:nowrap;color:var(--navy);
    text-decoration:none;padding:.4rem .65rem;border-radius:6px;font-size:.86rem;font-weight:650}
    nav a:hover{background:#e4eee9}main{max-width:1180px;margin:auto;padding:1rem 2rem 6rem}
    section{padding:5rem 0;border-bottom:1px solid var(--line);scroll-margin-top:4rem}
    .section-kicker{text-transform:uppercase;letter-spacing:.16em;color:var(--teal);font-weight:800;
    font-size:.78rem}h2{font:700 clamp(2.2rem,4vw,4rem)/1.08 Georgia,serif;margin:.35rem 0 2rem;
    color:var(--navy)}h3{color:var(--navy);margin-top:2rem}p{max-width:920px}.lead{font-size:1.3rem;
    line-height:1.65}.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin:2rem 0}
    .metric{background:var(--navy);color:white;padding:1.4rem;border-radius:10px;box-shadow:var(--shadow)}
    .metric span{display:block;font:700 2.3rem Georgia,serif;color:#8ed7cc}.metric small{display:block}
    .two-col,.three-col{display:grid;grid-template-columns:repeat(2,1fr);gap:1.2rem;margin:1.5rem 0}
    .three-col{grid-template-columns:repeat(3,1fr)}.card,.audit-grid article,.parameter-grid article{
    background:var(--card);border:1px solid var(--line);border-radius:10px;padding:1.2rem;box-shadow:0 4px 18px rgba(0,0,0,.04)}
    .audit-grid,.parameter-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:.8rem;margin:1.5rem 0}
    .audit-grid b,.parameter-grid b{display:block;color:var(--navy);font-size:1.05rem}
    .audit-grid span,.parameter-grid span{display:block;color:var(--muted);margin-top:.35rem}
    .callout{padding:1.2rem 1.4rem;border-left:5px solid;margin:1.5rem 0;background:white;
    border-radius:4px 10px 10px 4px;box-shadow:0 5px 20px rgba(0,0,0,.05)}
    .callout strong{display:block;font-size:1.05rem;margin-bottom:.25rem}.callout.success{border-color:var(--teal)}
    .callout.info{border-color:var(--blue)}.callout.warning{border-color:var(--gold)}
    .callout.danger{border-color:var(--red)}figure{margin:2rem 0;background:var(--card);padding:1rem;
    border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow)}figure img{display:block;width:100%;
    height:auto;border-radius:7px}figcaption{padding:1rem .4rem .5rem;color:var(--navy)}
    figcaption span,.source-note{color:var(--muted);font-size:.88rem}.figure-analysis{background:#edf4f1;
    padding:1rem;border-radius:7px;margin:.5rem .3rem;color:#24443f}.data-table{width:100%;border-collapse:collapse;
    display:block;overflow-x:auto;background:var(--card);margin:1rem 0 2rem;font-size:.88rem}
    .data-table th{background:var(--navy);color:white;text-align:left}.data-table th,.data-table td{
    border:1px solid #ddd6c9;padding:.55rem .65rem;white-space:nowrap}.data-table tr:nth-child(even){background:#f1eee7}
    .equation{font:1.18rem Georgia,serif;text-align:center;background:var(--card);border:1px solid var(--line);
    border-left:5px solid var(--teal);padding:1.2rem;margin:.8rem 0;overflow-x:auto}.glossary{display:grid;
    grid-template-columns:minmax(80px,150px) 1fr;gap:.2rem 1rem}.glossary dt{font-weight:800;color:var(--navy);
    padding:.45rem}.glossary dd{margin:0;padding:.45rem;border-bottom:1px dotted var(--line)}
    code{font-family:Consolas,"Courier New",monospace;background:#e9e5dd;padding:.08rem .25rem;border-radius:3px}
    pre{background:#081521;color:#d7e4ec;padding:1.2rem;border-radius:8px;overflow:auto;max-height:70vh;
    line-height:1.45;font-size:.82rem}pre code{background:none;padding:0}.pipeline{display:flex;flex-wrap:wrap;
    align-items:center;gap:.5rem;margin:1.5rem 0}.pipeline span{background:var(--navy);color:white;padding:.6rem .8rem;
    border-radius:6px}.pipeline b{color:var(--gold)}.checklist{list-style:none;padding:0}.checklist li:before{
    content:"✓";color:var(--teal);font-weight:900;margin-right:.6rem}.code-file{background:var(--card);
    border:1px solid var(--line);border-radius:7px;margin:.55rem 0}.code-file summary{cursor:pointer;padding:.8rem 1rem;
    display:flex;justify-content:space-between;gap:1rem}.code-file summary span{color:var(--muted);font-size:.85rem}
    .code-file pre{margin:0;border-radius:0 0 7px 7px}.code-toolbar{position:sticky;top:3.8rem;z-index:10;
    display:flex;gap:.5rem;flex-wrap:wrap;background:var(--paper);padding:.7rem 0}.code-toolbar button,
    .code-toolbar input{border:1px solid var(--line);background:white;padding:.55rem .75rem;border-radius:6px}
    .code-toolbar button{cursor:pointer;background:var(--navy);color:white}.warning{padding:1rem;background:#fff0d7;
    border-left:4px solid var(--gold)}footer{background:#071d31;color:#dceaf2;padding:3rem max(5vw,2rem)}
    footer a{color:#8ed7cc}@media(max-width:850px){.metric-grid,.audit-grid,.parameter-grid,.three-col,.two-col{
    grid-template-columns:1fr 1fr}header{min-height:auto;padding-top:5rem}}@media(max-width:560px){
    main{padding:1rem}.metric-grid,.audit-grid,.parameter-grid,.three-col,.two-col{grid-template-columns:1fr}
    h1{font-size:3rem}.glossary{grid-template-columns:1fr}.glossary dd{padding-top:0}}
    @media print{nav,.code-toolbar{display:none}header{min-height:auto;padding:3rem;background:#123!important;
    -webkit-print-color-adjust:exact}section{break-inside:auto}figure,.card,.callout{break-inside:avoid}
    details:not([open])>*:not(summary){display:block}.code-file pre{max-height:none}}
    """

    script = """
    function toggleAll(openState){
      document.querySelectorAll('.code-file').forEach(function(d){d.open=openState;});
    }
    function filterCode(term){
      term=term.toLowerCase();
      document.querySelectorAll('.code-file').forEach(function(d){
        d.style.display=d.querySelector('summary').innerText.toLowerCase().includes(term)?'block':'none';
      });
    }
    const observer=new IntersectionObserver(entries=>{
      entries.forEach(entry=>{
        if(entry.isIntersecting){
          document.querySelectorAll('nav a').forEach(a=>a.classList.remove('active'));
          const link=document.querySelector('nav a[href="#'+entry.target.id+'"]');
          if(link) link.classList.add('active');
        }
      });
    },{rootMargin:'-20% 0px -70% 0px'});
    document.querySelectorAll('main section').forEach(s=>observer.observe(s));
    """

    document = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="Entrega final de política monetária: modelo Novo-Keynesiano calibrado para o Chile.">
  <title>Entrega Final | Política Monetária no Chile</title>
  <style>{styles}</style>
</head>
<body>
<header>
  <div class="eyebrow">FGV EESP · Política Monetária · 2026</div>
  <h1>Entrega Final</h1>
  <p class="subtitle">Modelo Novo-Keynesiano calibrado para o Chile: dados, teoria,
  solução, evidência, política monetária e código reproduzível.</p>
  <div class="cover-meta">
    <span>Chile</span><span>2001Q1–2026Q1</span><span>Octave 11.1</span>
    <span>Dynare 7.1</span><span>Python</span><span>Gerado em {date.today().strftime("%d/%m/%Y")}</span>
  </div>
</header>
<nav aria-label="Navegação do relatório">{nav_html}</nav>
<main>{body}</main>
<footer>
  <strong>Entrega Final — Política Monetária no Chile</strong>
  <p>Dados: Banco Central de Chile. Resultados do modelo: pipeline público deste projeto.
  Este documento é autocontido e pode ser aberto sem conexão com a internet.</p>
  <p>Referências oficiais:
  <a href="https://www.bcentral.cl/web/banco-central/areas/politica-monetaria">marco de política monetária</a> ·
  <a href="https://si3.bcentral.cl/Siete">Base de Datos Estadísticos</a> ·
  <a href="https://www.dynare.org/manual/">manual do Dynare</a>.</p>
</footer>
<script>{script}</script>
</body>
</html>"""
    OUTPUT.write_text(document, encoding="utf-8")
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size / 1024 / 1024:.2f} MiB)")
    print(f"Embedded {len(list(FIGURES.glob('*.png')))} PNG figures")
    print(f"Embedded {len(python_files) + len(dynare_core) + len(generated_mods) + 1} source files")


if __name__ == "__main__":
    build()
