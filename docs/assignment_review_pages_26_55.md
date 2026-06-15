# Revisao de aderencia: Aula 5, paginas 26 a 55

Este documento resume, em palavras proprias, como o projeto atende ao roteiro de
calibracao, solucao, simulacao e previsao apresentado nas paginas 26 a 55 da
Aula 5. O PDF da disciplina foi usado apenas como referencia local. Nenhuma
pagina, figura ou trecho do material privado foi copiado para o repositorio.

## Matriz de conformidade

| Bloco do roteiro | Implementacao no projeto | Evidencia produzida |
|---|---|---|
| Taxa neutra anual de 2%, 3% e 4% | Conversao exata para taxa trimestral e derivacao de `beta` | `outputs/tables/rstar_beta_table.csv` e cenarios `rstar_2`, `rstar_3`, `rstar_4` |
| Persistencia da taxa de politica | AR(1) com constante e erros-padrao HAC usando a TPM trimestral do BCCh; comparacao com a calibracao 0,80 | `rhoi_estimate.csv`, `irf_rho_comparison.png`, `moments_model_vs_data.csv` |
| Inclinacao da Phillips | Grade `kappa = 0.07, 0.10, 0.13`, com IRFs e medidas de impacto, persistencia e custo real | `irf_kappa_comparison.png`, `irf_kappa_tradeoffs.png`, `irf_summary_metrics.csv` |
| Reacao a inflacao | Grade `phi_pi = 1.3, ..., 2.2`, mantendo `phi_x = 0.5` | `irf_phi_pi_comparison.png`, `irf_phi_pi_tradeoffs.png`, `scenario_determinacy.csv` |
| Estabilidade e determinacao | Contagem de raizes de Blanchard-Kahn e mapa ampliado de `phi_pi = 0.5, ..., 3.0` | `determinacy_map.png`, `determinacy_map.csv` |
| Calibracao dos choques | Duas alternativas: alvo didatico do roteiro e alvo alternativo do pesquisador | `fevd_calibration_comparison.png`, `fevd_calibration_comparison.csv`, `shock_sigmas_comparison.csv` |
| Solucao no Dynare | `steady;`, `check;` e `stoch_simul(order=1, irf=20)` em todos os modelos | `outputs/dynare/<cenario>/` e logs do lote |
| IRFs e sinais economicos | Nove respostas do baseline, checagem automatica dos sinais de impacto e horizonte de reversao | `irf_baseline_all_shocks.png`, `irf_sign_checks.csv` |
| Momentos, correlacoes e FEVD | Comparacao entre momentos teoricos, dados completos e amostra sem o episodio mais agudo da pandemia | `moments_model_vs_data.png`, `correlations_model_vs_data.csv`, `fevd_summary.csv` |
| Previsao incondicional | Dynare nativo: `estimation(datafile=..., mode_compute=0, forecast=8)` com suavizador de Kalman; `oo_.forecast.Mean` e bandas `HPDinf/HPDsup` | `dynare/nk_chile_forecast.mod`, `outputs/dynare/forecast/forecast_unconditional.csv`, `forecast_fanchart.png` |
| Previsao condicional: caminho do juro | Dynare `conditional_forecast`: TPM mantida em 4,5% por 2 trimestres e aperto para ~5,1% por 4; tambem ancorado ao estado atual pela forma reduzida | `conditional_cond_hold_2q.csv`, `conditional_cond_hike_4q.csv`, `conditional_scenarios.png`, `conditional_policy_shocks.png` |
| Previsao condicional: meta de inflacao | Dynare `conditional_forecast` forcando a inflacao a meta de 3% (gap -0,00192) por 4 trimestres, via `e_i` | `conditional_cond_pi_to_target_4q.csv`, `conditional_scenarios.png` |
| Exportacao e reprodutibilidade | Tabelas CSV, figuras PNG, logs, modelos gerados e HTML autocontido | `outputs/`, `dynare/generated/`, `Entrega Final.html` |

## Escolhas tratadas pelas duas alternativas

O roteiro apresenta pontos em que o pesquisador pode escolher entre caminhos.
Para evitar que a conclusao dependa silenciosamente de uma unica escolha, o
projeto executa os dois lados:

1. **Persistencia calibrada ou estimada.** O baseline usa `rho_i` estimado por
   AR(1), mas existe um cenario separado com `rho_i = 0.80`.
2. **Meta didatica ou meta alternativa de FEVD.** As duas matrizes de
   participacao de variancia sao calibradas e comparadas.
3. **Condicionar a trajetoria do juro ou a trajetoria da inflacao.** O projeto
   produz cenarios condicionais dos dois tipos, alem do caminho incondicional.
4. **Analise estrutural calibrada ou verificacao econometrica.** A calibracao
   principal e preservada, e os parametros tambem recebem referencias de AR(1),
   regra de Taylor, curva de Phillips e moda posterior exploratoria.

## Correcoes conceituais incorporadas

- As respostas de impacto do baseline apresentam os nove sinais esperados, mas
  algumas IRFs trocam de sinal no trimestre seguinte. Portanto, nao se afirma
  que toda resposta seja monotona.
- Um `phi_pi` maior reduz o impacto inicial de um choque de custo sobre a
  inflacao e acelera ligeiramente a convergencia da raiz estavel, mas exige
  movimentos maiores de juros e produto. A soma absoluta da inflacao pode ate
  aumentar por causa de undershooting.
- A previsao condicional de primeira ordem usa choques controlados que os
  agentes nao antecipam antes de cada periodo. Isso nao equivale a uma solucao
  deterministica de previsao perfeita.
- A FEVD e resultado da calibracao dos desvios-padrao. Ela nao e uma
  decomposicao historica identificada para o Chile.
- O AR(1) da TPM mede persistencia reduzida. Ele nao identifica isoladamente o
  coeficiente estrutural de suavizacao da regra de Taylor.
- O modelo tem apenas `i(-1)` como estado predeterminado. Logo, os cenarios
  projetivos nao conseguem condicionar de forma independente o hiato e a
  inflacao observados no ultimo trimestre.

## Resultado geral da auditoria

O projeto cobre todos os exercicios quantitativos centrais das paginas 26 a 55
e amplia os itens apresentados como alternativas. Os resultados sao
computacionalmente reproduziveis, mas devem ser lidos como um laboratorio
estrutural pequeno. Eles nao constituem previsao oficial, recomendacao de
politica ou estimacao completa de um DSGE para uma economia aberta.
