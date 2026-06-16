# Análise macro aprofundada — progresso e handoff

> **Para retomar:** leia este arquivo + a lista de tarefas, e continue a partir da
> primeira fase pendente. Frase de retomada sugerida: *"continue a análise macro
> de onde parou (veja docs/macro_analysis_progress.md)"*.

## Objetivo
Pacote completo de análise macro (Tier 1+2+3) **em cima** do trabalho da Aula 5
(slides 26–55), que já está 100% completo. Isto é enriquecimento, não requisito.

## Status por fase

| Fase | Conteúdo | Status |
|---|---|---|
| 1a | Decomposição histórica de choques (Dynare `shock_decomposition` + smoother) | **feito** |
| 1b | Contrafactual de política (regra mais agressiva, φπ=2,5) | **feito** |
| 2a | VAR estrutural (SVAR) — comparar IRF monetária empírica vs DSGE | **feito** |
| 2b | r* variável no tempo (componentes não observados / Kalman) | **feito** |
| 2c | Avaliação de previsão pseudo-out-of-sample (vs AR(1)/passeio aleatório/VAR) | **feito** |
| 3a | Dados de economia aberta (câmbio CLP/USD + cobre, fontes OECD/IMF via FRED) | **feito** |
| 3b | Modelo de economia aberta (UIP + pass-through + choque de cobre) | **feito** |
| 3c | NKPC híbrida com indexação e inércia inflacionária | **feito** |
| 3d | Bayesiano completo: duas cadeias MCMC + R-hat/ESS | **feito** |
| 3e | Comparação baseline vs NKPC híbrida por evidência marginal (Laplace) | **feito** |
| 4 | Integrar nas entregas (PDF/seções, apresentação, Comprehend) + commit | **feito** |

## Arquivos da Fase 1 (já criados)
- `dynare/nk_chile_history.mod` — estimation(smoother) + `shock_decomposition`.
- `dynare/export_history.m` — dump de `oo_.shock_decomposition` e `oo_.SmoothedShocks`.
- `python/run_history.py` — runner (staging ASCII).
- `python/plot_history.py` — 3 figuras + tabela.
- Saídas: `outputs/dynare/history/{shock_decomp,smoothed_shocks}.csv`,
  `outputs/figures/history_{shock_decomposition,smoothed_shocks,counterfactual}.png`,
  `outputs/tables/history_shock_decomposition.csv`.

## Decisões e gotchas (não óbvios)
- `oo_.shock_decomposition` tem layout `[endo, nexo+2, nobs]`: colunas =
  `[e_x, e_pi, e_i, initial, smoothed]`. A **última coluna é o valor suavizado
  (total)**, não o estado estacionário — não somar como componente.
- Como há 3 observáveis = 3 choques e sem erro de medida, o smoother recupera os
  choques **exatamente**: simular a forma reduzida com eles reproduz os dados
  (RMSE ≈ 3e-7, validado em `plot_history.py`).
- Choques recuperados têm σ ~10× os calibrados → reflete a volatilidade real
  (COVID, inflação 2022). É esperado e correto.
- Contrafactual: reusa os choques recuperados, re-resolve a forma reduzida com
  novos parâmetros de regra. Caveat de Lucas é mencionado.
- Toolchain/gotchas gerais: ver [project_nk_chile na memória] — gitdir separado,
  staging ASCII p/ Dynare e LaTeX, anaconda python, Octave 11 + Dynare 7.1.

## Resultados e cautelas das Fases 2–3
- O SVAR usa quatro defasagens, passa o teste de brancura dos resíduos
  (`p=0,169`), mas rejeita normalidade. A identificação recursiva produz um
  *activity puzzle* inicial; portanto, o SVAR desafia o DSGE e não deve ser
  vendido como validação causal definitiva.
- A proxy de `r*` variável no tempo termina em 0,85% a.a. É um componente local
  estatístico, não uma estimação estrutural Laubach–Williams.
- No pseudo-out-of-sample, o NK baseline perde em horizonte de um trimestre, mas
  tem ganho relativo para inflação e hiato em quatro trimestres. O exercício usa
  dados revisados e hiato HP da amostra completa.
- **Disputa baseline vs híbrida (hybrid_solution.py):** a forma reduzida da NKPC
  híbrida (2 estados) foi resolvida por iteração contrativa e validada contra as
  IRFs do Dynare a ~1e-14. No mesmo OOS, a híbrida reduz o RMSE da inflação em
  h=1 em ~19% (4,74→3,83), empata em h=1 ano, e sua previsão de nível converge
  com o baseline em 1 ano (~3,5%). Conclusão: o curto prazo melhora com inércia,
  mas a resposta-headline de 1 ano é robusta à escolha do modelo. Reportado nos
  slides "Resposta direta" e OOS (apêndice) e na Seção 17.5 do relatório.
- O modelo aberto é determinado e acrescenta câmbio real, pass-through e cobre.
  Seus coeficientes são ilustrativos; persistências/volatilidades de câmbio e
  cobre são ancoradas em dados públicos.
- A NKPC híbrida aumenta a persistência da inflação e altera o custo dinâmico da
  desinflação, mas o grau de indexação (`gamma_pi=0,35`) é calibrado.
- O MCMC recuperado contém duas cadeias de 10.000 propostas, com descarte de
  30%. Todos os R-hat ficaram abaixo de 1,05, mas ESS entre cerca de 92 e 268
  indica autocorrelação relevante. A aceitação próxima de 63% também sugere
  proposta conservadora. A posterior de `phi_pi` inclui valores abaixo de 1,
  reforçando a incerteza sobre a força da reação monetária.
- A comparação marginal usa os mesmos 101 trimestres e observáveis nos dois
  modelos. A NKPC híbrida vence por 12,02 log-pontos (fator de Bayes aproximado
  166 mil), com `gamma_pi=0,341` no modo. A evidência é de Laplace no modo,
  portanto local e condicionada aos priors.

## Entregas integradas
- `Entrega Final.html`: 25 figuras públicas, tabelas, narrativa e código completo.
- `entrega_aula5/Comprehend.pdf`: 41 páginas, em linguagem didática para público amador, cobrindo
  os 37 quadros substantivos da apresentação, 25 gráficos, 40 tabelas, variáveis, outputs, código,
  reprodução, glossário e limitações.
- `entrega_aula5/Apresentacao.pdf`: rota principal de 20 minutos e apêndice com
  todas as 25 figuras (46 páginas no PDF; 37 quadros substantivos).
- `entrega_aula5/Roteiro.pdf`: 5 páginas, com tempos e fala para a rota principal.

## Próximo passo imediato
Nenhuma fase técnica pendente. Apenas versionar e publicar o commit final.
