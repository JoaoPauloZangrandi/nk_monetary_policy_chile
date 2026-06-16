# Extensões profundas v2 — progresso e handoff

> **Retomar:** ler este arquivo + a lista de tarefas; seguir do primeiro WP não-concluído.
> Plano completo: `~/.claude/plans/quero-que-adicione-uma-inherited-quokka.md`.

## Objetivo (pedido do usuário)
Núcleos da inflação (energia/bens/serviços — o que mais impactou, por núcleo, anualizado,
dentro/fora da meta, como conversa com o modelo); atividade + mercado de trabalho profundo + spider
chart estilo FED Atlanta; **DSGE convergir à meta por construção** (hoje reverte a 3,79%, não 3%);
**Kalman em vez de HP sempre**; esclarecer SVAR vs VAR; 1–2 slides de conclusões de política.

## Decisões fixas
- **Dados núcleos/trabalho = FRED** (sem credenciais BCCh). Núcleos só até ~2023 (cobrem 2021–23,
  perdem 2024–26); food até 2018 (usar voláteis=cheio−core); sem vagas (spider reduzido); trabalho
  até 2026. Séries: `CHLCPIALLMINMEI`, `CHLCPICORMINMEI`, `CHLCPIENGMINMEI`, `CHLCPGRSE01IXOBM`,
  `LRHUTTTTCLM156S`, `LREM64TTCLM156S`, `CHLPROINDMISMEI`.
- **Re-centrar inflação na meta:** `pi = infl_q − target_q` (target_q=(1.03)^¼−1). Juro e hiato seguem
  na média/zero. Level-mapping de inflação muda: somar **target_q** (não a média) → níveis revertem a 3%.
- **Kalman, não HP:** helper `kalman_gap()` (statsmodels UnobservedComponents) p/ hiato e fx/copper gaps.
- **Sem repuxar BCCh:** reprocessar do cache (`reprocess_dataset.py` lê chile_macro_quarterly.csv,
  recomputa hiato Kalman + observáveis re-centrados). `build_chile_dataset.py` editado p/ consistência
  mas NÃO rodado (cairia em sintético).
- **SVAR é recursivo (Cholesky)** — não só VAR. Nota no slide.

## Status por WP
- [x] WP0 — progress doc + tarefas
- [x] WP1 — Kalman gap + converge-to-target. **Feito e verificado:** previsão de inflação converge a
  3% (2,5→3,0% em 8 trim.); hiato Kalman (std 2,3%, COVID −10%). `reprocess_dataset.py` reprocessa do
  cache. Level-mapping mean→target em forecast_model/outlook/history/ipc. Slides 6,21,25,31 atualizados.
  **Notas:** φπ posterior caiu p/ 0,97 com novo hiato/centragem (re-rodar MCMC+comparação no WP6);
  HP→Kalman de fx/copper em build_open_economy_dataset.py **adiado p/ WP4**.
- [x] WP2 — esclarecer SVAR (slide 27): nota de que é SVAR recursivo (Cholesky), não só VAR.
- [x] WP3 — núcleos da inflação (FRED). `build_inflation_cores.py` (headline/núcleo/energia/serviços,
  YoY, até 2023). Achado: **energia liderou o surto 2021-23 (pico 24%)**; núcleo/serviços persistentes
  (~11%). 2 slides novos (painel por núcleo vs banda 2-4%; ranking de impacto + mapa ao modelo
  custo/inércia). Figuras: ipc_cores_panel.png, ipc_cores_drivers.png. (README: add no WP6.)
- [x] WP4 — atividade + trabalho + spider (FRED). `build_labor_activity.py`: desemprego/jovem,
  emprego, participação, prod. industrial + hiato Kalman. **Spider estilo FED Atlanta** (percentis,
  atual vs pré-pandemia): forte em emprego (92º)/participação (76º), fraco em desemprego (34º, 8,7%) e
  atividade (32º). Okun no texto. 2 slides (dashboard + spider). Sem vagas/admissões (FRED não tem p/
  Chile). **Também:** câmbio/cobre agora por Kalman (build_open_economy_dataset.py), cadeia aberta
  re-rodada (ainda determinada). Figuras: labor_activity_dashboard.png, labor_spider.png.
- [x] WP5 — conclusões de política: 2 slides (diagnóstico + implicações) antes do "Obrigado".
  Síntese: energia puxou o surto; inflação com memória; economia no potencial; convergência à meta;
  gradualismo domina; φπ~1 é o risco. Apresentação agora 45 quadros.
- [ ] WP6 — atualizar Comprehend/relatório/HTML/Roteiro + push final

## Numeração atual da apresentação (39 quadros, antes da v2)
20 Como prevê · 21 incondicional · 22 condicionais · 23 choques · 24 decomp geral · 25 decomp IPC ·
26 IPC dois modelos · 27 SVAR · 28 economia aberta · 29 MCMC · 30 comparação Phillips · 31 resposta
direta · 32 robustez híbrida · 33 obrigado · 34–39 apêndice.

## Toolchain/gotchas
- gitdir separado `C:\Users\joaoz\nk_monetary_policy_chile_gitdir`; usar `git -C <gitdir>`. Remote
  JoaoPauloZangrandi/nk_monetary_policy_chile.
- Python `C:\Users\joaoz\anaconda3\python.exe`; rodar de `python/` (import common).
- Dynare via `run_*.py` (staging ASCII). PDFs via `entrega_aula5/build.sh` (staging ASCII).
- Octave 11 + Dynare 7.1. FRED CSV: `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<ID>`.
- Verificar cada slide novo renderizando com pdftocairo (figura+texto plenamente visíveis).

## Próximo passo
WP1: criar `kalman_gap` em common.py; `reprocess_dataset.py`.
