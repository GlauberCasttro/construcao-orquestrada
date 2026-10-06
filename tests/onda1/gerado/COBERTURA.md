# COBERTURA — oráculo gerado da onda 1

Gerado por `gerar.py` a partir de `references/*.json5` (não edite à mão). Rodar: `python3 -m unittest discover -s tests/onda1/gerado -t tests/onda1/gerado`.

## Totais

| categoria | itens | linhas |
|---|---:|---:|
| a — átomos de guarda | 62 | 177 |
| b — transições | 82 | 246 |
| c — contadores com teto | 20 | 35 |
| d — campos do ledger | 14 | 93 |
| e — hashes conferidos | 7 | 14 |
| f — portões G0..G14 | 16 | 37 |
| g — subcomandos | 21 | 67 |
| h — operacionais via ev | 18 | 18 |
| i — entrega | 1 | 41 |
| **total** | 241 | 728 |

## Contagem do contrato

- átomos distintos nas guardas: 62 (com evidência na onda 1: 62; sem — só injeção: 0)
- transições: 60 (pares transição × estado de origem: 82)
- contadores: 7; constantes: 7
- campos do ledger: 13
- hashes conferidos: 7
- portões: 15 (núcleo da onda 1: G0, G1, G3, G4, G7)
- subcomandos: 20
- eventos operacionais: 18

Átomos sem evidência computável na onda 1 (o produto os trata como indeterminados até as ondas 2–3; cobertos por injeção V/F + omitido ⇒ recusa): 

sha256 de payload SEM conferência na onda 1 (não listados como `conferidos`): genese.contrato_hash, genese.maquina_hash, checkpoint_janela_50.retomar_md_hash, despachada.brief_hash, retornou.relatorio_hash, colhida.diff_hash, aprovacao.hash_estado, manifest_gravado.manifest_hash, medicao_registrada.sistema_hash, contrato_hash.contrato_hash, contrato_hash.plano_hash, premissas_ok.pontos_hash, rodada_fechada.comparacao_hash, task.reabrir.hash_entradas_antes, task.reabrir.hash_entradas_depois, task.verificada.diff_hash

## Item × caso

### a — átomos de guarda

| id | item | caso |
|---|---|---|
| A-0001 | átomo ac_decisao_parar | V por evidência em campanha.pronta [ATIVA] ⇒ pronta |
| A-0002 | átomo ac_decisao_parar | F por evidência em campanha.pronta [ATIVA] ⇒ recusa |
| A-0003 | átomo ac_decisao_parar | disco F + injeção V em campanha.pronta [ATIVA] ⇒ o disco vence (recusa) |
| A-0004 | átomo agora_apos_retomar | V por evidência em obra.retomar [PAUSADO@LOTE] ⇒ retomar |
| A-0005 | átomo agora_apos_retomar | F por evidência em obra.retomar [PAUSADO@LOTE] ⇒ recusa |
| A-0006 | átomo agora_apos_retomar | disco F + injeção V em obra.retomar [PAUSADO@LOTE] ⇒ o disco vence (recusa) |
| A-0007 | átomo aprovacao_humana | V: `aprovar stop` no pty grava |
| A-0008 | átomo aprovacao_humana | F: sem canal humano (ev e API com átomo forjado) recusa |
| A-0009 | átomo autor_fora_dos_construtores | V por evidência em obra.oraculo_pronto [ORACULO] ⇒ oraculo_pronto |
| A-0010 | átomo autor_fora_dos_construtores | F por evidência em obra.oraculo_pronto [ORACULO] ⇒ recusa |
| A-0011 | átomo autor_fora_dos_construtores | disco F + injeção V em obra.oraculo_pronto [ORACULO] ⇒ o disco vence (recusa) |
| A-0012 | átomo baseline_reprodutivel | V por evidência em obra.baseline_medido [BASELINE] ⇒ baseline_medido |
| A-0013 | átomo baseline_reprodutivel | F por evidência em obra.baseline_medido [BASELINE] ⇒ recusa |
| A-0014 | átomo baseline_reprodutivel | disco F + injeção V em obra.baseline_medido [BASELINE] ⇒ o disco vence (recusa) |
| A-0015 | átomo brief_valido | V por evidência em task.pronta [PENDENTE] ⇒ pronta |
| A-0016 | átomo brief_valido | F por evidência em task.pronta [PENDENTE] ⇒ recusa |
| A-0017 | átomo brief_valido | disco F + injeção V em task.pronta [PENDENTE] ⇒ o disco vence (recusa) |
| A-0018 | átomo campanhas_ativas_abaixo_de_2 | V por evidência em campanha.ativar [RASCUNHO] ⇒ ativar |
| A-0019 | átomo campanhas_ativas_abaixo_de_2 | F por evidência em campanha.ativar [RASCUNHO] ⇒ recusa |
| A-0020 | átomo campanhas_ativas_abaixo_de_2 | disco F + injeção V em campanha.ativar [RASCUNHO] ⇒ o disco vence (recusa) |
| A-0021 | átomo colisao_vazia | V por evidência em campanha.integrar [PRONTA_INTEGRAR] ⇒ integrar |
| A-0022 | átomo colisao_vazia | F por evidência em campanha.integrar [PRONTA_INTEGRAR] ⇒ reintegrar |
| A-0023 | átomo colisao_vazia | disco F + injeção V em campanha.integrar [PRONTA_INTEGRAR] ⇒ o disco vence (reintegrar) |
| A-0024 | átomo copia_limpa | V por evidência em obra.medido [MEDIR] ⇒ medido |
| A-0025 | átomo copia_limpa | F por evidência em obra.medido [MEDIR] ⇒ recusa |
| A-0026 | átomo copia_limpa | disco F + injeção V em obra.medido [MEDIR] ⇒ o disco vence (recusa) |
| A-0027 | átomo criterio_parada_ok | V por evidência em obra.parar [FECHAR_RODADA] ⇒ parar |
| A-0028 | átomo criterio_parada_ok | F por evidência em obra.parar [FECHAR_RODADA] ⇒ escalar |
| A-0029 | átomo criterio_parada_ok | disco F + injeção V em obra.parar [FECHAR_RODADA] ⇒ o disco vence (escalar) |
| A-0030 | átomo criterios_classificados | V por evidência em obra.oraculo_pronto [ORACULO] ⇒ oraculo_pronto |
| A-0031 | átomo criterios_classificados | F por evidência em obra.oraculo_pronto [ORACULO] ⇒ recusa |
| A-0032 | átomo criterios_classificados | disco F + injeção V em obra.oraculo_pronto [ORACULO] ⇒ o disco vence (recusa) |
| A-0033 | átomo defeitos_classificados | V por evidência em obra.campanhas_abertas [CORRIGIR] ⇒ campanhas_abertas |
| A-0034 | átomo defeitos_classificados | F por evidência em obra.campanhas_abertas [CORRIGIR] ⇒ recusa |
| A-0035 | átomo defeitos_classificados | disco F + injeção V em obra.campanhas_abertas [CORRIGIR] ⇒ o disco vence (recusa) |
| A-0036 | átomo deps_aceitas | V por evidência em obra.lote_ok [LOTE] ⇒ lote_ok |
| A-0037 | átomo deps_aceitas | F por evidência em obra.lote_ok [LOTE] ⇒ recusa |
| A-0038 | átomo deps_aceitas | disco F + injeção V em obra.lote_ok [LOTE] ⇒ o disco vence (recusa) |
| A-0039 | átomo diff_no_territorio | V por evidência em obra.merge_ok [INTEGRAR] ⇒ merge_ok |
| A-0040 | átomo diff_no_territorio | F por evidência em obra.merge_ok [INTEGRAR] ⇒ recusa |
| A-0041 | átomo diff_no_territorio | disco F + injeção V em obra.merge_ok [INTEGRAR] ⇒ o disco vence (recusa) |
| A-0042 | átomo evidencia_registrada | V por evidência em obra.oraculo_mudar [PLANO] ⇒ oraculo_mudar |
| A-0043 | átomo evidencia_registrada | F por evidência em obra.oraculo_mudar [PLANO] ⇒ recusa |
| A-0044 | átomo g3_reprovou | V por evidência em obra.violou [INTEGRAR] ⇒ violou |
| A-0045 | átomo g3_reprovou | F por evidência em obra.violou [INTEGRAR] ⇒ recusa |
| A-0046 | átomo g3_reprovou | disco F + injeção V em obra.violou [INTEGRAR] ⇒ o disco vence (recusa) |
| A-0047 | átomo g4_reprovou | V por evidência em obra.violou [INTEGRAR] ⇒ violou |
| A-0048 | átomo g4_reprovou | F por evidência em obra.violou [INTEGRAR] ⇒ recusa |
| A-0049 | átomo g4_reprovou | disco F + injeção V em obra.violou [INTEGRAR] ⇒ o disco vence (recusa) |
| A-0050 | átomo ha_decisoes | V por evidência em obra.plano_com_decisoes [PLANO] ⇒ plano_com_decisoes |
| A-0051 | átomo ha_decisoes | F por evidência em obra.plano_com_decisoes [PLANO] ⇒ plano_sem_decisoes |
| A-0052 | átomo ha_decisoes | disco F + injeção V em obra.plano_com_decisoes [PLANO] ⇒ o disco vence (plano_sem_decisoes) |
| A-0053 | átomo hash_entradas_mudou | V por evidência em task.reabrir [ACEITA] ⇒ reabrir |
| A-0054 | átomo hash_entradas_mudou | F por evidência em task.reabrir [ACEITA] ⇒ recusa |
| A-0055 | átomo hash_entradas_mudou | disco F + injeção V em task.reabrir [ACEITA] ⇒ o disco vence (recusa) |
| A-0056 | átomo hook_vivo | V por evidência em obra.iniciar [INICIO] ⇒ iniciar |
| A-0057 | átomo hook_vivo | F por evidência em obra.iniciar [INICIO] ⇒ recusa |
| A-0058 | átomo hook_vivo | disco F + injeção V em obra.iniciar [INICIO] ⇒ o disco vence (recusa) |
| A-0059 | átomo limite_detectado | V por evidência em obra.limite_uso [INICIO] ⇒ limite_uso |
| A-0060 | átomo limite_detectado | F por evidência em obra.limite_uso [INICIO] ⇒ recusa |
| A-0061 | átomo lote_cabe_no_teto | V por evidência em obra.lote_ok [LOTE] ⇒ lote_ok |
| A-0062 | átomo lote_cabe_no_teto | F por evidência em obra.lote_ok [LOTE] ⇒ recusa |
| A-0063 | átomo lote_cabe_no_teto | disco F + injeção V em obra.lote_ok [LOTE] ⇒ o disco vence (recusa) |
| A-0064 | átomo lote_disjunto | V por evidência em obra.lote_ok [LOTE] ⇒ lote_ok |
| A-0065 | átomo lote_disjunto | F por evidência em obra.lote_ok [LOTE] ⇒ recusa |
| A-0066 | átomo lote_disjunto | disco F + injeção V em obra.lote_ok [LOTE] ⇒ o disco vence (recusa) |
| A-0067 | átomo medicao_posterior_ao_merge | V por evidência em obra.medido [MEDIR] ⇒ medido |
| A-0068 | átomo medicao_posterior_ao_merge | F por evidência em obra.medido [MEDIR] ⇒ recusa |
| A-0069 | átomo medicao_posterior_ao_merge | disco F + injeção V em obra.medido [MEDIR] ⇒ o disco vence (recusa) |
| A-0070 | átomo merge_ordenado | V por evidência em obra.merge_ok [INTEGRAR] ⇒ merge_ok |
| A-0071 | átomo merge_ordenado | F por evidência em obra.merge_ok [INTEGRAR] ⇒ recusa |
| A-0072 | átomo merge_ordenado | disco F + injeção V em obra.merge_ok [INTEGRAR] ⇒ o disco vence (recusa) |
| A-0073 | átomo mesma_rejeicao_2x | V por evidência em obra.vermelho_corrigir [VERIFICAR] ⇒ vermelho_replanejar |
| A-0074 | átomo mesma_rejeicao_2x | F por evidência em obra.vermelho_corrigir [VERIFICAR] ⇒ vermelho_corrigir |
| A-0075 | átomo mesma_rejeicao_2x | disco F + injeção V em obra.vermelho_corrigir [VERIFICAR] ⇒ o disco vence (vermelho_corrigir) |
| A-0076 | átomo motivo_registrado | V por evidência em obra.baseline_dispensado [BASELINE] ⇒ baseline_dispensado |
| A-0077 | átomo motivo_registrado | F por evidência em obra.baseline_dispensado [BASELINE] ⇒ recusa |
| A-0078 | átomo nenhuma_em_voo | V por evidência em obra.todos_retornaram [DESPACHADO] ⇒ todos_retornaram |
| A-0079 | átomo nenhuma_em_voo | F por evidência em obra.todos_retornaram [DESPACHADO] ⇒ recusa |
| A-0080 | átomo nenhuma_em_voo | disco F + injeção V em obra.todos_retornaram [DESPACHADO] ⇒ o disco vence (recusa) |
| A-0081 | átomo obra_replanejou | V por evidência em task.descartar [PENDENTE] ⇒ descartar |
| A-0082 | átomo obra_replanejou | F por evidência em task.descartar [PENDENTE] ⇒ recusa |
| A-0083 | átomo obra_replanejou | disco F + injeção V em task.descartar [PENDENTE] ⇒ o disco vence (recusa) |
| A-0084 | átomo oraculo_apos_cada_merge | V por evidência em obra.merge_ok [INTEGRAR] ⇒ merge_ok |
| A-0085 | átomo oraculo_apos_cada_merge | F por evidência em obra.merge_ok [INTEGRAR] ⇒ recusa |
| A-0086 | átomo oraculo_apos_cada_merge | disco F + injeção V em obra.merge_ok [INTEGRAR] ⇒ o disco vence (recusa) |
| A-0087 | átomo oraculo_campanha_congelado | V por evidência em campanha.ativar [RASCUNHO] ⇒ ativar |
| A-0088 | átomo oraculo_campanha_congelado | F por evidência em campanha.ativar [RASCUNHO] ⇒ recusa |
| A-0089 | átomo oraculo_campanha_congelado | disco F + injeção V em campanha.ativar [RASCUNHO] ⇒ o disco vence (recusa) |
| A-0090 | átomo oraculo_congelado | V por evidência em obra.baseline_medido [BASELINE] ⇒ baseline_medido |
| A-0091 | átomo oraculo_congelado | F por evidência em obra.baseline_medido [BASELINE] ⇒ recusa |
| A-0092 | átomo oraculo_congelado | disco F + injeção V em obra.baseline_medido [BASELINE] ⇒ o disco vence (recusa) |
| A-0093 | átomo oraculos_fechados_verdes | V por evidência em campanha.integrar [PRONTA_INTEGRAR] ⇒ integrar |
| A-0094 | átomo oraculos_fechados_verdes | F por evidência em campanha.integrar [PRONTA_INTEGRAR] ⇒ reintegrar |
| A-0095 | átomo oraculos_fechados_verdes | disco F + injeção V em campanha.integrar [PRONTA_INTEGRAR] ⇒ o disco vence (reintegrar) |
| A-0096 | átomo orcamento_esgotado | V por evidência em obra.continuar_rodada [FECHAR_RODADA] ⇒ escalar |
| A-0097 | átomo orcamento_esgotado | F por evidência em obra.continuar_rodada [FECHAR_RODADA] ⇒ continuar_rodada |
| A-0098 | átomo orcamento_esgotado | disco F + injeção V em obra.continuar_rodada [FECHAR_RODADA] ⇒ o disco vence (continuar_rodada) |
| A-0099 | átomo orcamento_restante | V por evidência em obra.lote_ok [LOTE] ⇒ lote_ok |
| A-0100 | átomo orcamento_restante | F por evidência em obra.lote_ok [LOTE] ⇒ recusa |
| A-0101 | átomo orcamento_restante | disco F + injeção V em obra.lote_ok [LOTE] ⇒ o disco vence (recusa) |
| A-0102 | átomo oscilacao | V por evidência em obra.vermelho_corrigir [VERIFICAR] ⇒ vermelho_replanejar |
| A-0103 | átomo oscilacao | F por evidência em obra.vermelho_corrigir [VERIFICAR] ⇒ vermelho_corrigir |
| A-0104 | átomo oscilacao | disco F + injeção V em obra.vermelho_corrigir [VERIFICAR] ⇒ o disco vence (vermelho_corrigir) |
| A-0105 | átomo pass3_final | V por evidência em obra.entrega_aprovada [AH:entrega] ⇒ entrega_aprovada |
| A-0106 | átomo pass3_final | F por evidência em obra.entrega_aprovada [AH:entrega] ⇒ recusa |
| A-0107 | átomo perdida_na_retomada | V: `retomar` com T-01 EM_VOO e vaga aberta grava task.perdida |
| A-0108 | átomo perdida_na_retomada | F: `ev task.perdida` fora da retomada recusa |
| A-0109 | átomo plano_valido | V por evidência em obra.plano_com_decisoes [PLANO] ⇒ plano_com_decisoes |
| A-0110 | átomo plano_valido | F por evidência em obra.plano_com_decisoes [PLANO] ⇒ recusa |
| A-0111 | átomo plano_valido | disco F + injeção V em obra.plano_com_decisoes [PLANO] ⇒ o disco vence (recusa) |
| A-0112 | átomo plato_2 | V por evidência em obra.continuar_rodada [FECHAR_RODADA] ⇒ escalar |
| A-0113 | átomo plato_2 | F por evidência em obra.continuar_rodada [FECHAR_RODADA] ⇒ continuar_rodada |
| A-0114 | átomo plato_2 | disco F + injeção V em obra.continuar_rodada [FECHAR_RODADA] ⇒ o disco vence (continuar_rodada) |
| A-0115 | átomo pontos_atualizados | V por evidência em obra.parar [FECHAR_RODADA] ⇒ parar |
| A-0116 | átomo pontos_atualizados | F por evidência em obra.parar [FECHAR_RODADA] ⇒ recusa |
| A-0117 | átomo pontos_atualizados | disco F + injeção V em obra.parar [FECHAR_RODADA] ⇒ o disco vence (recusa) |
| A-0118 | átomo pontos_cobertos | V por evidência em obra.oraculo_pronto [ORACULO] ⇒ oraculo_pronto |
| A-0119 | átomo pontos_cobertos | F por evidência em obra.oraculo_pronto [ORACULO] ⇒ recusa |
| A-0120 | átomo pontos_cobertos | disco F + injeção V em obra.oraculo_pronto [ORACULO] ⇒ o disco vence (recusa) |
| A-0121 | átomo pontos_completos | V por evidência em obra.premissas_ok [PREMISSAS] ⇒ premissas_ok |
| A-0122 | átomo pontos_completos | F por evidência em obra.premissas_ok [PREMISSAS] ⇒ recusa |
| A-0123 | átomo pontos_completos | disco F + injeção V em obra.premissas_ok [PREMISSAS] ⇒ o disco vence (recusa) |
| A-0124 | átomo portao_regressao_go | V por evidência em obra.verde [VERIFICAR] ⇒ verde |
| A-0125 | átomo portao_regressao_go | F por evidência em obra.verde [VERIFICAR] ⇒ recusa |
| A-0126 | átomo portao_regressao_go | disco F + injeção V em obra.verde [VERIFICAR] ⇒ o disco vence (recusa) |
| A-0127 | átomo relatorio_presente | V por evidência em task.retornar [EM_VOO] ⇒ retornar |
| A-0128 | átomo relatorio_presente | F por evidência em task.retornar [EM_VOO] ⇒ recusa |
| A-0129 | átomo relatorio_presente | disco F + injeção V em task.retornar [EM_VOO] ⇒ o disco vence (recusa) |
| A-0130 | átomo resultado_no_worktree | V por evidência (valor_atomo, sem injeção): V: despachada isolation worktree + colhida com diff_hash |
| A-0131 | átomo resultado_no_worktree | F por evidência (valor_atomo, sem injeção): F: isolation null (valor_atomo |
| A-0132 | átomo retomar_md_valido | V por evidência em obra.parar [FECHAR_RODADA] ⇒ parar |
| A-0133 | átomo retomar_md_valido | F por evidência em obra.parar [FECHAR_RODADA] ⇒ recusa |
| A-0134 | átomo retomar_md_valido | disco F + injeção V em obra.parar [FECHAR_RODADA] ⇒ o disco vence (recusa) |
| A-0135 | átomo sem_perdidas_pendentes | V por evidência em obra.retomar [PAUSADO@LOTE] ⇒ retomar |
| A-0136 | átomo sem_perdidas_pendentes | F por evidência em obra.retomar [PAUSADO@LOTE] ⇒ recusa |
| A-0137 | átomo sem_perdidas_pendentes | disco F + injeção V em obra.retomar [PAUSADO@LOTE] ⇒ o disco vence (recusa) |
| A-0138 | átomo sistema_congelado_na_medicao | V por evidência em obra.medido [MEDIR] ⇒ medido |
| A-0139 | átomo sistema_congelado_na_medicao | F por evidência em obra.medido [MEDIR] ⇒ recusa |
| A-0140 | átomo sistema_congelado_na_medicao | disco F + injeção V em obra.medido [MEDIR] ⇒ o disco vence (recusa) |
| A-0141 | átomo so_sistema_vira_task | V por evidência em obra.campanhas_abertas [CORRIGIR] ⇒ campanhas_abertas |
| A-0142 | átomo so_sistema_vira_task | F por evidência em obra.campanhas_abertas [CORRIGIR] ⇒ recusa |
| A-0143 | átomo so_sistema_vira_task | disco F + injeção V em obra.campanhas_abertas [CORRIGIR] ⇒ o disco vence (recusa) |
| A-0144 | átomo stop_numerico | V por evidência em obra.premissas_ok [PREMISSAS] ⇒ premissas_ok |
| A-0145 | átomo stop_numerico | F por evidência em obra.premissas_ok [PREMISSAS] ⇒ recusa |
| A-0146 | átomo stop_numerico | disco F + injeção V em obra.premissas_ok [PREMISSAS] ⇒ o disco vence (recusa) |
| A-0147 | átomo teste_falha_antes | V por evidência em obra.campanhas_abertas [CORRIGIR] ⇒ campanhas_abertas |
| A-0148 | átomo teste_falha_antes | F por evidência em obra.campanhas_abertas [CORRIGIR] ⇒ recusa |
| A-0149 | átomo teste_falha_antes | disco F + injeção V em obra.campanhas_abertas [CORRIGIR] ⇒ o disco vence (recusa) |
| A-0150 | átomo tipo_exige_baseline | V por evidência em obra.baseline_dispensado [BASELINE] ⇒ recusa |
| A-0151 | átomo tipo_exige_baseline | F por evidência em obra.baseline_dispensado [BASELINE] ⇒ baseline_dispensado |
| A-0152 | átomo tipo_exige_baseline | disco V + injeção F em obra.baseline_dispensado [BASELINE] ⇒ o disco vence (recusa) |
| A-0153 | átomo todas_tasks_retornadas_ou_aceitas | V por evidência em obra.fronteira_vazia [LOTE] ⇒ fronteira_vazia |
| A-0154 | átomo todas_tasks_retornadas_ou_aceitas | F por evidência em obra.fronteira_vazia [LOTE] ⇒ recusa |
| A-0155 | átomo todas_tasks_retornadas_ou_aceitas | disco F + injeção V em obra.fronteira_vazia [LOTE] ⇒ o disco vence (recusa) |
| A-0156 | átomo trava_adquirida | V por evidência em obra.merge_ok [INTEGRAR] ⇒ merge_ok |
| A-0157 | átomo trava_adquirida | F por evidência em obra.merge_ok [INTEGRAR] ⇒ recusa |
| A-0158 | átomo trava_adquirida | disco F + injeção V em obra.merge_ok [INTEGRAR] ⇒ o disco vence (recusa) |
| A-0159 | átomo veredito_go_final | V por evidência em obra.entrega_aprovada [AH:entrega] ⇒ entrega_aprovada |
| A-0160 | átomo veredito_go_final | F por evidência em obra.entrega_aprovada [AH:entrega] ⇒ recusa |
| A-0161 | átomo verificacao_ok | V por evidência em task.aceitar [RETORNADA] ⇒ aceitar |
| A-0162 | átomo verificacao_ok | F por evidência em task.aceitar [RETORNADA] ⇒ rejeitar |
| A-0163 | átomo verificador_nao_autor | V por evidência em obra.verde [VERIFICAR] ⇒ verde |
| A-0164 | átomo verificador_nao_autor | F por evidência em obra.verde [VERIFICAR] ⇒ recusa |
| A-0165 | átomo verificador_nao_autor | disco F + injeção V em obra.verde [VERIFICAR] ⇒ o disco vence (recusa) |
| A-0166 | átomo vermelho_baseline_e_stub | V por evidência em obra.oraculo_pronto [ORACULO] ⇒ oraculo_pronto |
| A-0167 | átomo vermelho_baseline_e_stub | F por evidência em obra.oraculo_pronto [ORACULO] ⇒ recusa |
| A-0168 | átomo vermelho_baseline_e_stub | disco F + injeção V em obra.oraculo_pronto [ORACULO] ⇒ o disco vence (recusa) |
| A-0169 | átomo vivos_abaixo_do_teto | V por evidência em task.despachar [PRONTA] ⇒ despachar |
| A-0170 | átomo vivos_abaixo_do_teto | F por evidência em task.despachar [PRONTA] ⇒ recusa |
| A-0171 | átomo vivos_abaixo_do_teto | disco F + injeção V em task.despachar [PRONTA] ⇒ o disco vence (recusa) |
| A-0172 | átomo workspace_fora_do_alvo | V por evidência em obra.iniciar [INICIO] ⇒ iniciar |
| A-0173 | átomo workspace_fora_do_alvo | F por evidência em obra.iniciar [INICIO] ⇒ recusa |
| A-0174 | átomo workspace_fora_do_alvo | disco F + injeção V em obra.iniciar [INICIO] ⇒ o disco vence (recusa) |
| A-0175 | átomo writes_disjuntos_dos_vivos | V por evidência em task.despachar [PRONTA] ⇒ despachar |
| A-0176 | átomo writes_disjuntos_dos_vivos | F por evidência em task.despachar [PRONTA] ⇒ recusa |
| A-0177 | átomo writes_disjuntos_dos_vivos | disco F + injeção V em task.despachar [PRONTA] ⇒ o disco vence (recusa) |

### b — transições

| id | item | caso |
|---|---|---|
| B-0178 | obra.iniciar [INICIO] | evento certo no estado certo grava |
| B-0179 | obra.iniciar [INICIO] | evento no estado errado AH:entrega recusa sem gravar |
| B-0180 | obra.iniciar [INICIO] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0181 | obra.premissas_ok [PREMISSAS] | evento certo no estado certo grava |
| B-0182 | obra.premissas_ok [PREMISSAS] | evento no estado errado INICIO recusa sem gravar |
| B-0183 | obra.premissas_ok [PREMISSAS] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0184 | obra.stop_aprovado [AH:stop] | evento certo no estado certo grava |
| B-0185 | obra.stop_aprovado [AH:stop] | evento no estado errado REPLANEJAR recusa sem gravar |
| B-0186 | obra.stop_aprovado [AH:stop] | registro com ator orquestrador (≠ humano) ⇒ fold recusa |
| B-0187 | obra.stop_rejeitado [AH:stop] | evento certo no estado certo grava |
| B-0188 | obra.stop_rejeitado [AH:stop] | evento no estado errado VERIFICAR recusa sem gravar |
| B-0189 | obra.stop_rejeitado [AH:stop] | registro com ator orquestrador (≠ humano) ⇒ fold recusa |
| B-0190 | obra.oraculo_pronto [ORACULO] | evento certo no estado certo grava |
| B-0191 | obra.oraculo_pronto [ORACULO] | evento no estado errado FECHAR_RODADA recusa sem gravar |
| B-0192 | obra.oraculo_pronto [ORACULO] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0193 | obra.oraculo_aprovado [AH:oraculo] | evento certo no estado certo grava |
| B-0194 | obra.oraculo_aprovado [AH:oraculo] | evento no estado errado LOTE recusa sem gravar |
| B-0195 | obra.oraculo_aprovado [AH:oraculo] | registro com ator orquestrador (≠ humano) ⇒ fold recusa |
| B-0196 | obra.oraculo_rejeitado [AH:oraculo] | evento certo no estado certo grava |
| B-0197 | obra.oraculo_rejeitado [AH:oraculo] | evento no estado errado ORACULO recusa sem gravar |
| B-0198 | obra.oraculo_rejeitado [AH:oraculo] | registro com ator orquestrador (≠ humano) ⇒ fold recusa |
| B-0199 | obra.baseline_medido [BASELINE] | evento certo no estado certo grava |
| B-0200 | obra.baseline_medido [BASELINE] | evento no estado errado PAUSADO@LOTE recusa sem gravar |
| B-0201 | obra.baseline_medido [BASELINE] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0202 | obra.baseline_dispensado [BASELINE] | evento certo no estado certo grava |
| B-0203 | obra.baseline_dispensado [BASELINE] | evento no estado errado AH:oraculo recusa sem gravar |
| B-0204 | obra.baseline_dispensado [BASELINE] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0205 | obra.plano_com_decisoes [PLANO] | evento certo no estado certo grava |
| B-0206 | obra.plano_com_decisoes [PLANO] | evento no estado errado ENTREGUE recusa sem gravar |
| B-0207 | obra.plano_com_decisoes [PLANO] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0208 | obra.plano_sem_decisoes [PLANO] | evento certo no estado certo grava |
| B-0209 | obra.plano_sem_decisoes [PLANO] | evento no estado errado AH:oraculo recusa sem gravar |
| B-0210 | obra.plano_sem_decisoes [PLANO] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0211 | obra.plano_aprovado [AH:plano] | evento certo no estado certo grava |
| B-0212 | obra.plano_aprovado [AH:plano] | evento no estado errado BASELINE recusa sem gravar |
| B-0213 | obra.plano_aprovado [AH:plano] | registro com ator orquestrador (≠ humano) ⇒ fold recusa |
| B-0214 | obra.plano_rejeitado [AH:plano] | evento certo no estado certo grava |
| B-0215 | obra.plano_rejeitado [AH:plano] | evento no estado errado INICIO recusa sem gravar |
| B-0216 | obra.plano_rejeitado [AH:plano] | registro com ator orquestrador (≠ humano) ⇒ fold recusa |
| B-0217 | obra.lote_ok [LOTE] | evento certo no estado certo grava |
| B-0218 | obra.lote_ok [LOTE] | evento no estado errado BASELINE recusa sem gravar |
| B-0219 | obra.lote_ok [LOTE] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0220 | obra.fronteira_vazia [LOTE] | evento certo no estado certo grava |
| B-0221 | obra.fronteira_vazia [LOTE] | evento no estado errado PAUSADO@LOTE recusa sem gravar |
| B-0222 | obra.fronteira_vazia [LOTE] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0223 | obra.todos_retornaram [DESPACHADO] | evento certo no estado certo grava |
| B-0224 | obra.todos_retornaram [DESPACHADO] | evento no estado errado ORACULO recusa sem gravar |
| B-0225 | obra.todos_retornaram [DESPACHADO] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0226 | obra.merge_ok [INTEGRAR] | evento certo no estado certo grava |
| B-0227 | obra.merge_ok [INTEGRAR] | evento no estado errado PREMISSAS recusa sem gravar |
| B-0228 | obra.merge_ok [INTEGRAR] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0229 | obra.violou [INTEGRAR] | evento certo no estado certo grava |
| B-0230 | obra.violou [INTEGRAR] | evento no estado errado ENTREGUE recusa sem gravar |
| B-0231 | obra.violou [INTEGRAR] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0232 | obra.verde [VERIFICAR] | evento certo no estado certo grava |
| B-0233 | obra.verde [VERIFICAR] | evento no estado errado PLANO recusa sem gravar |
| B-0234 | obra.verde [VERIFICAR] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0235 | obra.vermelho_corrigir [VERIFICAR] | evento certo no estado certo grava |
| B-0236 | obra.vermelho_corrigir [VERIFICAR] | evento no estado errado AH:stop recusa sem gravar |
| B-0237 | obra.vermelho_corrigir [VERIFICAR] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0238 | obra.vermelho_replanejar [VERIFICAR] | evento certo no estado certo grava |
| B-0239 | obra.vermelho_replanejar [VERIFICAR] | evento no estado errado BASELINE recusa sem gravar |
| B-0240 | obra.vermelho_replanejar [VERIFICAR] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0241 | obra.medido [MEDIR] | evento certo no estado certo grava |
| B-0242 | obra.medido [MEDIR] | evento no estado errado AH:stop recusa sem gravar |
| B-0243 | obra.medido [MEDIR] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0244 | obra.campanhas_abertas [CORRIGIR] | evento certo no estado certo grava |
| B-0245 | obra.campanhas_abertas [CORRIGIR] | evento no estado errado AH:continuar@LOTE recusa sem gravar |
| B-0246 | obra.campanhas_abertas [CORRIGIR] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0247 | obra.corrigir_esgotado [CORRIGIR] | evento certo no estado certo grava (tentativas=3) |
| B-0248 | obra.corrigir_esgotado [CORRIGIR] | evento no estado errado FECHAR_RODADA recusa sem gravar |
| B-0249 | obra.corrigir_esgotado [CORRIGIR] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0250 | obra.parar [FECHAR_RODADA] | evento certo no estado certo grava |
| B-0251 | obra.parar [FECHAR_RODADA] | evento no estado errado PLANO recusa sem gravar |
| B-0252 | obra.parar [FECHAR_RODADA] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0253 | obra.continuar_rodada [FECHAR_RODADA] | evento certo no estado certo grava |
| B-0254 | obra.continuar_rodada [FECHAR_RODADA] | evento no estado errado MEDIR recusa sem gravar |
| B-0255 | obra.continuar_rodada [FECHAR_RODADA] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0256 | obra.escalar [FECHAR_RODADA] | evento certo no estado certo grava |
| B-0257 | obra.escalar [FECHAR_RODADA] | evento no estado errado CORRIGIR recusa sem gravar |
| B-0258 | obra.escalar [FECHAR_RODADA] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0259 | obra.entrega_aprovada [AH:entrega] | evento certo no estado certo grava |
| B-0260 | obra.entrega_aprovada [AH:entrega] | evento no estado errado ORACULO recusa sem gravar |
| B-0261 | obra.entrega_aprovada [AH:entrega] | registro com ator orquestrador (≠ humano) ⇒ fold recusa |
| B-0262 | obra.entrega_rejeitada [AH:entrega] | evento certo no estado certo grava |
| B-0263 | obra.entrega_rejeitada [AH:entrega] | evento no estado errado ENTREGUE recusa sem gravar |
| B-0264 | obra.entrega_rejeitada [AH:entrega] | registro com ator orquestrador (≠ humano) ⇒ fold recusa |
| B-0265 | obra.escalar_aprovado [AH:escalar] | evento certo no estado certo grava |
| B-0266 | obra.escalar_aprovado [AH:escalar] | evento no estado errado PLANO recusa sem gravar |
| B-0267 | obra.escalar_aprovado [AH:escalar] | registro com ator orquestrador (≠ humano) ⇒ fold recusa |
| B-0268 | obra.escalar_rejeitado [AH:escalar] | evento certo no estado certo grava |
| B-0269 | obra.escalar_rejeitado [AH:escalar] | evento no estado errado PREMISSAS recusa sem gravar |
| B-0270 | obra.escalar_rejeitado [AH:escalar] | registro com ator orquestrador (≠ humano) ⇒ fold recusa |
| B-0271 | obra.novo_plano [REPLANEJAR] | evento certo no estado certo grava |
| B-0272 | obra.novo_plano [REPLANEJAR] | evento no estado errado ORACULO recusa sem gravar |
| B-0273 | obra.novo_plano [REPLANEJAR] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0274 | obra.desistir [REPLANEJAR] | evento certo no estado certo grava |
| B-0275 | obra.desistir [REPLANEJAR] | evento no estado errado AH:plano recusa sem gravar |
| B-0276 | obra.desistir [REPLANEJAR] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0277 | obra.abandono_confirmado [AH:abandonar] | evento certo no estado certo grava |
| B-0278 | obra.abandono_confirmado [AH:abandonar] | evento no estado errado PAUSADO@LOTE recusa sem gravar |
| B-0279 | obra.abandono_confirmado [AH:abandonar] | registro com ator orquestrador (≠ humano) ⇒ fold recusa |
| B-0280 | obra.abandono_rejeitado [AH:abandonar] | evento certo no estado certo grava |
| B-0281 | obra.abandono_rejeitado [AH:abandonar] | evento no estado errado LOTE recusa sem gravar |
| B-0282 | obra.abandono_rejeitado [AH:abandonar] | registro com ator orquestrador (≠ humano) ⇒ fold recusa |
| B-0283 | obra.oraculo_mudar [PLANO] | evento certo no estado certo grava |
| B-0284 | obra.oraculo_mudar [PLANO] | evento no estado errado AH:continuar@LOTE recusa sem gravar |
| B-0285 | obra.oraculo_mudar [PLANO] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0286 | obra.oraculo_mudar [LOTE] | evento certo no estado certo grava |
| B-0287 | obra.oraculo_mudar [LOTE] | evento no estado errado AH:continuar@LOTE recusa sem gravar |
| B-0288 | obra.oraculo_mudar [LOTE] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0289 | obra.oraculo_mudar [INTEGRAR] | evento certo no estado certo grava |
| B-0290 | obra.oraculo_mudar [INTEGRAR] | evento no estado errado AH:continuar@LOTE recusa sem gravar |
| B-0291 | obra.oraculo_mudar [INTEGRAR] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0292 | obra.oraculo_mudar [VERIFICAR] | evento certo no estado certo grava |
| B-0293 | obra.oraculo_mudar [VERIFICAR] | evento no estado errado AH:continuar@LOTE recusa sem gravar |
| B-0294 | obra.oraculo_mudar [VERIFICAR] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0295 | obra.oraculo_mudar [CORRIGIR] | evento certo no estado certo grava |
| B-0296 | obra.oraculo_mudar [CORRIGIR] | evento no estado errado AH:continuar@LOTE recusa sem gravar |
| B-0297 | obra.oraculo_mudar [CORRIGIR] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0298 | obra.oraculo_mudar [FECHAR_RODADA] | evento certo no estado certo grava |
| B-0299 | obra.oraculo_mudar [FECHAR_RODADA] | evento no estado errado AH:continuar@LOTE recusa sem gravar |
| B-0300 | obra.oraculo_mudar [FECHAR_RODADA] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0301 | obra.oraculo_mudar [REPLANEJAR] | evento certo no estado certo grava |
| B-0302 | obra.oraculo_mudar [REPLANEJAR] | evento no estado errado AH:continuar@LOTE recusa sem gravar |
| B-0303 | obra.oraculo_mudar [REPLANEJAR] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0304 | obra.oraculo_mudar_aprovado [AH:oraculo_mudar@LOTE] | evento certo no estado certo grava |
| B-0305 | obra.oraculo_mudar_aprovado [AH:oraculo_mudar@LOTE] | evento no estado errado REPLANEJAR recusa sem gravar |
| B-0306 | obra.oraculo_mudar_aprovado [AH:oraculo_mudar@LOTE] | registro com ator orquestrador (≠ humano) ⇒ fold recusa |
| B-0307 | obra.oraculo_mudar_rejeitado [AH:oraculo_mudar@LOTE] | evento certo no estado certo grava |
| B-0308 | obra.oraculo_mudar_rejeitado [AH:oraculo_mudar@LOTE] | evento no estado errado CORRIGIR recusa sem gravar |
| B-0309 | obra.oraculo_mudar_rejeitado [AH:oraculo_mudar@LOTE] | registro com ator orquestrador (≠ humano) ⇒ fold recusa |
| B-0310 | obra.limite_uso [INICIO] | evento certo no estado certo grava |
| B-0311 | obra.limite_uso [INICIO] | evento no estado errado AH:stop recusa sem gravar |
| B-0312 | obra.limite_uso [INICIO] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0313 | obra.limite_uso [PREMISSAS] | evento certo no estado certo grava |
| B-0314 | obra.limite_uso [PREMISSAS] | evento no estado errado AH:stop recusa sem gravar |
| B-0315 | obra.limite_uso [PREMISSAS] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0316 | obra.limite_uso [ORACULO] | evento certo no estado certo grava |
| B-0317 | obra.limite_uso [ORACULO] | evento no estado errado AH:stop recusa sem gravar |
| B-0318 | obra.limite_uso [ORACULO] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0319 | obra.limite_uso [BASELINE] | evento certo no estado certo grava |
| B-0320 | obra.limite_uso [BASELINE] | evento no estado errado AH:stop recusa sem gravar |
| B-0321 | obra.limite_uso [BASELINE] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0322 | obra.limite_uso [PLANO] | evento certo no estado certo grava |
| B-0323 | obra.limite_uso [PLANO] | evento no estado errado AH:stop recusa sem gravar |
| B-0324 | obra.limite_uso [PLANO] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0325 | obra.limite_uso [LOTE] | evento certo no estado certo grava |
| B-0326 | obra.limite_uso [LOTE] | evento no estado errado AH:stop recusa sem gravar |
| B-0327 | obra.limite_uso [LOTE] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0328 | obra.limite_uso [DESPACHADO] | evento certo no estado certo grava |
| B-0329 | obra.limite_uso [DESPACHADO] | evento no estado errado AH:stop recusa sem gravar |
| B-0330 | obra.limite_uso [DESPACHADO] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0331 | obra.limite_uso [INTEGRAR] | evento certo no estado certo grava |
| B-0332 | obra.limite_uso [INTEGRAR] | evento no estado errado AH:stop recusa sem gravar |
| B-0333 | obra.limite_uso [INTEGRAR] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0334 | obra.limite_uso [VERIFICAR] | evento certo no estado certo grava |
| B-0335 | obra.limite_uso [VERIFICAR] | evento no estado errado AH:stop recusa sem gravar |
| B-0336 | obra.limite_uso [VERIFICAR] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0337 | obra.limite_uso [MEDIR] | evento certo no estado certo grava |
| B-0338 | obra.limite_uso [MEDIR] | evento no estado errado AH:stop recusa sem gravar |
| B-0339 | obra.limite_uso [MEDIR] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0340 | obra.limite_uso [CORRIGIR] | evento certo no estado certo grava |
| B-0341 | obra.limite_uso [CORRIGIR] | evento no estado errado AH:stop recusa sem gravar |
| B-0342 | obra.limite_uso [CORRIGIR] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0343 | obra.limite_uso [FECHAR_RODADA] | evento certo no estado certo grava |
| B-0344 | obra.limite_uso [FECHAR_RODADA] | evento no estado errado AH:stop recusa sem gravar |
| B-0345 | obra.limite_uso [FECHAR_RODADA] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0346 | obra.limite_uso [REPLANEJAR] | evento certo no estado certo grava |
| B-0347 | obra.limite_uso [REPLANEJAR] | evento no estado errado AH:stop recusa sem gravar |
| B-0348 | obra.limite_uso [REPLANEJAR] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0349 | obra.retomar [PAUSADO@LOTE] | evento certo no estado certo grava |
| B-0350 | obra.retomar [PAUSADO@LOTE] | evento no estado errado AH:abandonar recusa sem gravar |
| B-0351 | obra.retomar [PAUSADO@LOTE] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0352 | obra.pausas_esgotadas [PAUSADO@LOTE] | evento certo no estado certo grava (pausas=6) |
| B-0353 | obra.pausas_esgotadas [PAUSADO@LOTE] | evento no estado errado ABANDONADO recusa sem gravar |
| B-0354 | obra.pausas_esgotadas [PAUSADO@LOTE] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0355 | obra.continuar_aprovado [AH:continuar@LOTE] | evento certo no estado certo grava |
| B-0356 | obra.continuar_aprovado [AH:continuar@LOTE] | evento no estado errado FECHAR_RODADA recusa sem gravar |
| B-0357 | obra.continuar_aprovado [AH:continuar@LOTE] | registro com ator orquestrador (≠ humano) ⇒ fold recusa |
| B-0358 | obra.continuar_rejeitado [AH:continuar@LOTE] | evento certo no estado certo grava |
| B-0359 | obra.continuar_rejeitado [AH:continuar@LOTE] | evento no estado errado DESPACHADO recusa sem gravar |
| B-0360 | obra.continuar_rejeitado [AH:continuar@LOTE] | registro com ator orquestrador (≠ humano) ⇒ fold recusa |
| B-0361 | obra.abandonar [AH:stop] | evento certo no estado certo grava |
| B-0362 | obra.abandonar [AH:stop] | evento no estado errado ENTREGUE recusa sem gravar |
| B-0363 | obra.abandonar [AH:stop] | registro com ator orquestrador (≠ humano) ⇒ fold recusa |
| B-0364 | task.pronta [PENDENTE] | evento certo no estado certo grava |
| B-0365 | task.pronta [PENDENTE] | evento no estado errado EM_VOO recusa sem gravar |
| B-0366 | task.pronta [PENDENTE] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0367 | task.despachar [PRONTA] | evento certo no estado certo grava |
| B-0368 | task.despachar [PRONTA] | evento no estado errado EM_VOO recusa sem gravar |
| B-0369 | task.despachar [PRONTA] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0370 | task.retornar [EM_VOO] | evento certo no estado certo grava |
| B-0371 | task.retornar [EM_VOO] | evento no estado errado RETORNADA recusa sem gravar |
| B-0372 | task.retornar [EM_VOO] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0373 | task.colher [EM_VOO] | fora da onda 1 (colhida é onda 2): `ev task.colher` fora da retomada recusa |
| B-0374 | task.colher [EM_VOO] | evento no estado errado PENDENTE recusa sem gravar |
| B-0375 | task.colher [EM_VOO] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0376 | task.perdida [EM_VOO] | evento certo no estado certo grava |
| B-0377 | task.perdida [EM_VOO] | evento no estado errado PRONTA recusa sem gravar |
| B-0378 | task.perdida [EM_VOO] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0379 | task.perdida_esgotada [EM_VOO] | evento certo no estado certo grava (tentativas=3) |
| B-0380 | task.perdida_esgotada [EM_VOO] | evento no estado errado REJEITADA recusa sem gravar |
| B-0381 | task.perdida_esgotada [EM_VOO] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0382 | task.aceitar [RETORNADA] | evento certo no estado certo grava |
| B-0383 | task.aceitar [RETORNADA] | evento no estado errado PRONTA recusa sem gravar |
| B-0384 | task.aceitar [RETORNADA] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0385 | task.rejeitar [RETORNADA] | evento certo no estado certo grava |
| B-0386 | task.rejeitar [RETORNADA] | evento no estado errado PENDENTE recusa sem gravar |
| B-0387 | task.rejeitar [RETORNADA] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0388 | task.retentar [REJEITADA] | evento certo no estado certo grava |
| B-0389 | task.retentar [REJEITADA] | evento no estado errado PRONTA recusa sem gravar |
| B-0390 | task.retentar [REJEITADA] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0391 | task.descartar [PENDENTE] | evento certo no estado certo grava |
| B-0392 | task.descartar [PENDENTE] | evento no estado errado EM_VOO recusa sem gravar |
| B-0393 | task.descartar [PENDENTE] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0394 | task.descartar [PRONTA] | evento certo no estado certo grava |
| B-0395 | task.descartar [PRONTA] | evento no estado errado EM_VOO recusa sem gravar |
| B-0396 | task.descartar [PRONTA] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0397 | task.descartar [REJEITADA] | evento certo no estado certo grava |
| B-0398 | task.descartar [REJEITADA] | evento no estado errado EM_VOO recusa sem gravar |
| B-0399 | task.descartar [REJEITADA] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0400 | task.reabrir [ACEITA] | evento certo no estado certo grava |
| B-0401 | task.reabrir [ACEITA] | evento no estado errado PRONTA recusa sem gravar |
| B-0402 | task.reabrir [ACEITA] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0403 | campanha.ativar [RASCUNHO] | evento certo no estado certo grava |
| B-0404 | campanha.ativar [RASCUNHO] | evento no estado errado PRONTA_INTEGRAR recusa sem gravar |
| B-0405 | campanha.ativar [RASCUNHO] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0406 | campanha.pronta [ATIVA] | evento certo no estado certo grava |
| B-0407 | campanha.pronta [ATIVA] | evento no estado errado RASCUNHO recusa sem gravar |
| B-0408 | campanha.pronta [ATIVA] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0409 | campanha.integrar [PRONTA_INTEGRAR] | evento certo no estado certo grava |
| B-0410 | campanha.integrar [PRONTA_INTEGRAR] | evento no estado errado RASCUNHO recusa sem gravar |
| B-0411 | campanha.integrar [PRONTA_INTEGRAR] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0412 | campanha.reintegrar [PRONTA_INTEGRAR] | evento certo no estado certo grava |
| B-0413 | campanha.reintegrar [PRONTA_INTEGRAR] | evento no estado errado RASCUNHO recusa sem gravar |
| B-0414 | campanha.reintegrar [PRONTA_INTEGRAR] | registro com ator humano (≠ script) ⇒ fold recusa |
| B-0415 | campanha.abandonar [RASCUNHO] | evento certo no estado certo grava |
| B-0416 | campanha.abandonar [RASCUNHO] | evento no estado errado ABANDONADA recusa sem gravar |
| B-0417 | campanha.abandonar [RASCUNHO] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0418 | campanha.abandonar [ATIVA] | evento certo no estado certo grava |
| B-0419 | campanha.abandonar [ATIVA] | evento no estado errado ABANDONADA recusa sem gravar |
| B-0420 | campanha.abandonar [ATIVA] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |
| B-0421 | campanha.abandonar [PRONTA_INTEGRAR] | evento certo no estado certo grava |
| B-0422 | campanha.abandonar [PRONTA_INTEGRAR] | evento no estado errado ABANDONADA recusa sem gravar |
| B-0423 | campanha.abandonar [PRONTA_INTEGRAR] | registro com ator humano (≠ orquestrador) ⇒ fold recusa |

### c — contadores com teto

| id | item | caso |
|---|---|---|
| C-0424 | despachos < MAX_DESPACHOS (obra.lote_ok) | abaixo do teto (despachos=29) ⇒ lote_ok grava |
| C-0425 | despachos < MAX_DESPACHOS (obra.lote_ok) | no teto (despachos=30) ⇒ lote_ok recusa |
| C-0426 | tentativas < MAX_TENTATIVAS (obra.vermelho_corrigir) | abaixo do teto (tentativas=2) ⇒ vermelho_corrigir grava |
| C-0427 | tentativas < MAX_TENTATIVAS (obra.vermelho_corrigir) | no teto (tentativas=3) ⇒ vermelho_corrigir recusa (vai vermelho_replanejar) |
| C-0428 | tentativas >= MAX_TENTATIVAS (obra.vermelho_replanejar) | abaixo do teto (tentativas=2) ⇒ vermelho_replanejar recusa (vai vermelho_corrigir) |
| C-0429 | tentativas >= MAX_TENTATIVAS (obra.vermelho_replanejar) | no teto (tentativas=3) ⇒ vermelho_replanejar grava |
| C-0430 | tentativas < MAX_TENTATIVAS (obra.campanhas_abertas) | abaixo do teto (tentativas=2) ⇒ campanhas_abertas grava |
| C-0431 | tentativas < MAX_TENTATIVAS (obra.campanhas_abertas) | no teto (tentativas=3) ⇒ campanhas_abertas recusa (vai corrigir_esgotado) |
| C-0432 | tentativas >= MAX_TENTATIVAS (obra.corrigir_esgotado) | abaixo do teto (tentativas=2) ⇒ corrigir_esgotado recusa (vai campanhas_abertas) |
| C-0433 | tentativas >= MAX_TENTATIVAS (obra.corrigir_esgotado) | no teto (tentativas=3) ⇒ corrigir_esgotado grava |
| C-0434 | rodada < MAX_RODADAS (obra.continuar_rodada) | abaixo do teto (rodada=2) ⇒ continuar_rodada grava |
| C-0435 | rodada < MAX_RODADAS (obra.continuar_rodada) | no teto (rodada=3) ⇒ continuar_rodada recusa (vai escalar) |
| C-0436 | zera tentativas em obra.continuar_rodada | tentativas=1 antes ⇒ 0 depois de continuar_rodada |
| C-0437 | rodada >= MAX_RODADAS (obra.escalar) | abaixo do teto (rodada=2) ⇒ escalar recusa (vai continuar_rodada) |
| C-0438 | rodada >= MAX_RODADAS (obra.escalar) | no teto (rodada=3) ⇒ escalar grava |
| C-0439 | zera tentativas em obra.escalar_aprovado | tentativas=1 antes ⇒ 0 depois de escalar_aprovado |
| C-0440 | replanejamentos < MAX_REPLANEJAMENTOS (obra.novo_plano) | abaixo do teto (replanejamentos=1) ⇒ novo_plano grava |
| C-0441 | replanejamentos < MAX_REPLANEJAMENTOS (obra.novo_plano) | no teto (replanejamentos=2) ⇒ novo_plano recusa |
| C-0442 | zera tentativas em obra.novo_plano | tentativas=3 antes ⇒ 0 depois de novo_plano |
| C-0443 | zera despachos em obra.novo_plano | despachos=2 antes ⇒ 0 depois de novo_plano |
| C-0444 | pausas < MAX_PAUSAS (obra.retomar) | abaixo do teto (pausas=5) ⇒ retomar grava |
| C-0445 | pausas < MAX_PAUSAS (obra.retomar) | no teto (pausas=6) ⇒ retomar recusa (vai pausas_esgotadas) |
| C-0446 | pausas >= MAX_PAUSAS (obra.pausas_esgotadas) | abaixo do teto (pausas=5) ⇒ pausas_esgotadas recusa (vai retomar) |
| C-0447 | pausas >= MAX_PAUSAS (obra.pausas_esgotadas) | no teto (pausas=6) ⇒ pausas_esgotadas grava |
| C-0448 | zera pausas em obra.continuar_aprovado | pausas=6 antes ⇒ 0 depois de continuar_aprovado |
| C-0449 | tentativas < MAX_TENTATIVAS (task.perdida) | abaixo do teto (tentativas=2) ⇒ perdida grava |
| C-0450 | tentativas < MAX_TENTATIVAS (task.perdida) | no teto (tentativas=3) ⇒ perdida recusa (vai perdida_esgotada) |
| C-0451 | tentativas >= MAX_TENTATIVAS (task.perdida_esgotada) | abaixo do teto (tentativas=2) ⇒ perdida_esgotada recusa (vai perdida) |
| C-0452 | tentativas >= MAX_TENTATIVAS (task.perdida_esgotada) | no teto (tentativas=3) ⇒ perdida_esgotada grava |
| C-0453 | tentativas < MAX_TENTATIVAS (task.retentar) | abaixo do teto (tentativas=2) ⇒ retentar grava |
| C-0454 | tentativas < MAX_TENTATIVAS (task.retentar) | no teto (tentativas=3) ⇒ retentar recusa |
| C-0455 | reaberturas < MAX_REABERTURAS (task.reabrir) | abaixo do teto (reaberturas=1) ⇒ reabrir grava |
| C-0456 | reaberturas < MAX_REABERTURAS (task.reabrir) | no teto (reaberturas=2) ⇒ reabrir recusa |
| C-0457 | reintegracoes < MAX_REINTEGRACOES (campanha.reintegrar) | abaixo do teto (reintegracoes=1) ⇒ reintegrar grava |
| C-0458 | reintegracoes < MAX_REINTEGRACOES (campanha.reintegrar) | no teto (reintegracoes=2) ⇒ reintegrar recusa |

### d — campos do ledger

| id | item | caso |
|---|---|---|
| D-0459 | ledger.seq | seq com lacuna (+1) em gênese (op) ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0460 | ledger.seq | seq com lacuna (+1) em operacional nota ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0461 | ledger.seq | seq com lacuna (+1) em operacional despachada ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0462 | ledger.seq | seq com lacuna (+1) em operacional oraculo_congelado ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0463 | ledger.seq | seq com lacuna (+1) em transição obra ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0464 | ledger.seq | seq com lacuna (+1) em operacional aprovacao ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0465 | ledger.seq | seq com lacuna (+1) em transição humana ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0466 | ledger.seq | seq com lacuna (+1) em transição task ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0467 | ledger.ts | ts fora do formato ISO-8601 Z em gênese (op) ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0468 | ledger.ts | ts fora do formato ISO-8601 Z em operacional nota ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0469 | ledger.ts | ts fora do formato ISO-8601 Z em operacional despachada ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0470 | ledger.ts | ts fora do formato ISO-8601 Z em operacional oraculo_congelado ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0471 | ledger.ts | ts fora do formato ISO-8601 Z em transição obra ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0472 | ledger.ts | ts fora do formato ISO-8601 Z em operacional aprovacao ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0473 | ledger.ts | ts fora do formato ISO-8601 Z em transição humana ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0474 | ledger.ts | ts fora do formato ISO-8601 Z em transição task ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0475 | ledger.ator | ator orquestrador em gênese (op) ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0476 | ledger.ator | ator orquestrador em operacional nota ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0477 | ledger.ator | ator humano em operacional despachada ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0478 | ledger.ator | ator orquestrador em operacional oraculo_congelado ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0479 | ledger.ator | ator orquestrador em transição obra ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0480 | ledger.ator | ator humano em operacional aprovacao ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0481 | ledger.ator | ator orquestrador em transição humana ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0482 | ledger.ator | ator script em transição task ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0483 | ledger.nivel | nivel obra em gênese (op) ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0484 | ledger.nivel | nivel xpto em operacional nota ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0485 | ledger.nivel | nivel task em operacional despachada ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0486 | ledger.nivel | nivel obra em operacional oraculo_congelado ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0487 | ledger.nivel | nivel task em transição obra ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0488 | ledger.nivel | nivel obra em operacional aprovacao ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0489 | ledger.nivel | nivel task em transição humana ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0490 | ledger.nivel | nivel obra em transição task ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0491 | ledger.evento | evento evento_inexistente_zz em gênese (op) ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0492 | ledger.evento | evento evento_inexistente_zz em operacional nota ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0493 | ledger.evento | evento evento_inexistente_zz em operacional despachada ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0494 | ledger.evento | evento evento_inexistente_zz em operacional oraculo_congelado ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0495 | ledger.evento | evento evento_inexistente_zz em transição obra ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0496 | ledger.evento | evento evento_inexistente_zz em operacional aprovacao ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0497 | ledger.evento | evento evento_inexistente_zz em transição humana ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0498 | ledger.evento | evento task.inexistente_zz em transição task ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0499 | ledger.de | de LOTE em gênese (op) ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0500 | ledger.de | de LOTE em operacional nota ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0501 | ledger.de | de LOTE em operacional despachada ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0502 | ledger.de | de LOTE em operacional oraculo_congelado ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0503 | ledger.de | de LOTE em transição obra ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0504 | ledger.de | de LOTE em operacional aprovacao ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0505 | ledger.de | de LOTE em transição humana ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0506 | ledger.de | de RETORNADA em transição task ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0507 | ledger.para | para LOTE em gênese (op) ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0508 | ledger.para | para LOTE em operacional nota ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0509 | ledger.para | para LOTE em operacional despachada ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0510 | ledger.para | para LOTE em operacional oraculo_congelado ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0511 | ledger.para | para ORACULO em transição obra ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0512 | ledger.para | para LOTE em operacional aprovacao ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0513 | ledger.para | para ENTREGUE em transição humana ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0514 | ledger.para | para ACEITA em transição task ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0515 | ledger.task | task null num evento de task em transição task ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0516 | ledger.chave | chave trocada (cadeia recalculada) em operacional despachada ⇒ status avisa cache ≠ fold |
| D-0517 | ledger.chave | chave trocada (cadeia recalculada) em transição task ⇒ status avisa cache ≠ fold |
| D-0518 | ledger.payload | payload trocado com payload_hash velho em gênese (op) ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0519 | ledger.payload | payload trocado com payload_hash velho em operacional nota ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0520 | ledger.payload | payload trocado com payload_hash velho em operacional despachada ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0521 | ledger.payload | payload trocado com payload_hash velho em operacional oraculo_congelado ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0522 | ledger.payload | payload trocado com payload_hash velho em transição obra ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0523 | ledger.payload | payload trocado com payload_hash velho em operacional aprovacao ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0524 | ledger.payload | payload trocado com payload_hash velho em transição humana ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0525 | ledger.payload | payload trocado com payload_hash velho em transição task ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0526 | ledger.payload_hash | payload_hash trocado em gênese (op) ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0527 | ledger.payload_hash | payload_hash trocado em operacional nota ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0528 | ledger.payload_hash | payload_hash trocado em operacional despachada ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0529 | ledger.payload_hash | payload_hash trocado em operacional oraculo_congelado ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0530 | ledger.payload_hash | payload_hash trocado em transição obra ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0531 | ledger.payload_hash | payload_hash trocado em operacional aprovacao ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0532 | ledger.payload_hash | payload_hash trocado em transição humana ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0533 | ledger.payload_hash | payload_hash trocado em transição task ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0534 | ledger.prev | prev da gênese ≠ '0' em gênese (op) ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0535 | ledger.prev | prev quebrado em operacional nota ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0536 | ledger.prev | prev quebrado em operacional despachada ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0537 | ledger.prev | prev quebrado em operacional oraculo_congelado ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0538 | ledger.prev | prev quebrado em transição obra ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0539 | ledger.prev | prev quebrado em operacional aprovacao ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0540 | ledger.prev | prev quebrado em transição humana ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0541 | ledger.prev | prev quebrado em transição task ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0542 | ledger.hash | hash trocado em gênese (op) ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0543 | ledger.hash | hash trocado em operacional nota ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0544 | ledger.hash | hash trocado em operacional despachada ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0545 | ledger.hash | hash trocado em operacional oraculo_congelado ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0546 | ledger.hash | hash trocado em transição obra ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0547 | ledger.hash | hash trocado em operacional aprovacao ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0548 | ledger.hash | hash trocado em transição humana ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0549 | ledger.hash | hash trocado em transição task ⇒ status/retomar/ev/veredito ≠ 0, nada gravado |
| D-0550 | ledger.payload | payload de oraculo_congelado trocado com cadeia recalculada ⇒ status avisa cache ≠ fold |
| D-0551 | ledger (controle) | forja sem adulteração é aceita (controle) |

### e — hashes conferidos

| id | item | caso |
|---|---|---|
| E-0552 | hash obra (premissas_ok.obra_hash) | controle: intacto ⇒ PASS/GO |
| E-0553 | hash obra (premissas_ok.obra_hash) | obra.json5 alterado depois de premissas_ok ⇒ G1 e G3 FAIL/ERRO; veredito NO-GO |
| E-0554 | hash plano (plano_ok.plano_hash) | controle: intacto ⇒ PASS/GO |
| E-0555 | hash plano (plano_ok.plano_hash) | PLANO.json5 alterado depois de plano_ok ⇒ G3 (diff) reprova |
| E-0556 | hash regressao (plano_ok.regressao_hash) | controle: intacto ⇒ PASS/GO |
| E-0557 | hash regressao (plano_ok.regressao_hash) | regressao.json5 alterado depois de plano_ok ⇒ veredito NO-GO |
| E-0558 | hash gate_report (portao_relatorio.gate_report_hash) | controle: intacto ⇒ PASS/GO |
| E-0559 | hash gate_report (portao_relatorio.gate_report_hash) | gate-report.json alterado depois do evento ⇒ veredito NO-GO e entrega recusada |
| E-0560 | hash oraculo (oraculo_congelado.hash) | controle: intacto ⇒ PASS/GO |
| E-0561 | hash oraculo (oraculo_congelado.hash) | arquivo do oráculo alterado depois do congelamento ⇒ G0 FAIL |
| E-0562 | hash ac_py (estado da campanha-mãe do ac.py (oracle.hash)) | controle: intacto ⇒ PASS/GO |
| E-0563 | hash ac_py (estado da campanha-mãe do ac.py (oracle.hash)) | oráculo alterado E recongelado só no ac.py ⇒ G0 FAIL (hash ≠ oraculo_congelado do ledger) |
| E-0564 | hash manifest (oraculo_congelado.manifest_hash) | controle: intacto ⇒ PASS/GO |
| E-0565 | hash manifest (oraculo_congelado.manifest_hash) | MANIFEST.json5 alterado depois do congelamento ⇒ G0 FAIL |

### f — portões G0..G14

| id | item | caso |
|---|---|---|
| F-0566 | veredito (sistema_hash) | relatório obsoleto (alvo mudou depois do run) ⇒ veredito NO-GO |
| F-0567 | portão G0 (oráculo intacto) | PASS por efeito real |
| F-0568 | portão G0 (oráculo intacto) | FAIL por efeito real (remover uma asserção do oráculo congelado ⇒ FAIL) |
| F-0569 | portão G0 (oráculo intacto) | relatório registrado adulterado (G0 FAIL→PASS, veredito→GO) ⇒ veredito NO-GO |
| F-0570 | portão G1 (suítes verdes) | PASS por efeito real |
| F-0571 | portão G1 (suítes verdes) | FAIL por efeito real (suíte com 0 testes coletados ⇒ FAIL; runner ausente ⇒ FAIL (exit 2)) |
| F-0572 | portão G1 (suítes verdes) | relatório registrado adulterado (G1 FAIL→PASS, veredito→GO) ⇒ veredito NO-GO |
| F-0573 | portão G2 (runtimes) | fora da onda 1: `portao run --only G2` (cli) ⇒ nunca PASS por vácuo |
| F-0574 | portão G2 (runtimes) | waiver de G2 com aprovação do portão G6 (outro item) ⇒ veredito NO-GO |
| F-0575 | portão G2 (runtimes) | relatório registrado adulterado (G2 FAIL→PASS, veredito→GO) ⇒ veredito NO-GO |
| F-0576 | portão G3 (território) | PASS por efeito real |
| F-0577 | portão G3 (território) | FAIL por efeito real (rename de arquivo fora do território ⇒ FAIL) |
| F-0578 | portão G3 (território) | relatório registrado adulterado (G3 FAIL→PASS, veredito→GO) ⇒ veredito NO-GO |
| F-0579 | portão G4 (gaming no diff) | PASS por efeito real |
| F-0580 | portão G4 (gaming no diff) | FAIL por efeito real (pytest.skip novo ⇒ FAIL; literal do held-out no código ⇒ FAIL) |
| F-0581 | portão G4 (gaming no diff) | relatório registrado adulterado (G4 FAIL→PASS, veredito→GO) ⇒ veredito NO-GO |
| F-0582 | portão G5 (força do oráculo) | fora da onda 1: `portao run --only G5` (cli) ⇒ nunca PASS por vácuo |
| F-0583 | portão G5 (força do oráculo) | relatório registrado adulterado (G5 FAIL→PASS, veredito→GO) ⇒ veredito NO-GO |
| F-0584 | portão G6 (superfície pública) | fora da onda 1: `portao run --only G6` (cli) ⇒ nunca PASS por vácuo |
| F-0585 | portão G6 (superfície pública) | relatório registrado adulterado (G6 FAIL→PASS, veredito→GO) ⇒ veredito NO-GO |
| F-0586 | portão G7 (checks provam efeito) | PASS por efeito real |
| F-0587 | portão G7 (checks provam efeito) | FAIL por efeito real (check que aceita stub 'exit 0' ⇒ FAIL) |
| F-0588 | portão G7 (checks provam efeito) | relatório registrado adulterado (G7 FAIL→PASS, veredito→GO) ⇒ veredito NO-GO |
| F-0589 | portão G8 (máquina) | fora da onda 1: `portao run --only G8` (cli) ⇒ NA com motivo |
| F-0590 | portão G8 (máquina) | relatório registrado adulterado (G8 FAIL→PASS, veredito→GO) ⇒ veredito NO-GO |
| F-0591 | portão G9 (E2E) | fora da onda 1: `portao run --only G9` (cli) ⇒ nunca PASS por vácuo |
| F-0592 | portão G9 (E2E) | relatório registrado adulterado (G9 FAIL→PASS, veredito→GO) ⇒ veredito NO-GO |
| F-0593 | portão G10 (instalação limpa) | fora da onda 1: `portao run --only G10` (cli) ⇒ nunca PASS por vácuo |
| F-0594 | portão G10 (instalação limpa) | relatório registrado adulterado (G10 FAIL→PASS, veredito→GO) ⇒ veredito NO-GO |
| F-0595 | portão G11 (upgrade legado) | fora da onda 1: `portao run --only G11` (cli) ⇒ NA com motivo |
| F-0596 | portão G11 (upgrade legado) | relatório registrado adulterado (G11 FAIL→PASS, veredito→GO) ⇒ veredito NO-GO |
| F-0597 | portão G12 (docs ↔ CLI) | fora da onda 1: `portao run --only G12` (cli) ⇒ nunca PASS por vácuo |
| F-0598 | portão G12 (docs ↔ CLI) | relatório registrado adulterado (G12 FAIL→PASS, veredito→GO) ⇒ veredito NO-GO |
| F-0599 | portão G13 (medição) | fora da onda 1: `portao run --only G13` (cli) ⇒ nunca PASS por vácuo |
| F-0600 | portão G13 (medição) | relatório registrado adulterado (G13 FAIL→PASS, veredito→GO) ⇒ veredito NO-GO |
| F-0601 | portão G14 (pontos do founder) | fora da onda 1: `portao run --only G14` (cli) ⇒ nunca PASS por vácuo |
| F-0602 | portão G14 (pontos do founder) | relatório registrado adulterado (G14 FAIL→PASS, veredito→GO) ⇒ veredito NO-GO |

### g — subcomandos

| id | item | caso |
|---|---|---|
| G-0603 | co.py init | flag desconhecida ⇒ 2 sem traceback |
| G-0604 | co.py init | entrada inválida `init --alvo {alvo} --tipo nao-e-tipo --pedido p --stop s` ⇒ 2 sem traceback |
| G-0605 | co.py init | erro interno (work_e_arquivo) ⇒ ≠ 0 sem traceback |
| G-0606 | co.py ev | flag desconhecida ⇒ 2 sem traceback |
| G-0607 | co.py ev | entrada inválida `ev evento_que_nao_existe_zz` ⇒ 2 sem traceback |
| G-0608 | co.py ev | entrada inválida `ev nota --payload {payload_ruim}` ⇒ 2 sem traceback |
| G-0609 | co.py ev | erro interno (ledger_corrompido) ⇒ ≠ 0 sem traceback |
| G-0610 | co.py status | flag desconhecida ⇒ 2 sem traceback |
| G-0611 | co.py status | entrada inválida `status --formato-zz` ⇒ 2 sem traceback |
| G-0612 | co.py status | erro interno (ledger_corrompido) ⇒ ≠ 0 sem traceback |
| G-0613 | co.py load | flag desconhecida ⇒ 2 sem traceback |
| G-0614 | co.py load | entrada inválida `load` ⇒ 2 sem traceback |
| G-0615 | co.py load | erro interno (ledger_corrompido) ⇒ ≠ 0 sem traceback |
| G-0616 | co.py maquina | flag desconhecida ⇒ 2 sem traceback |
| G-0617 | co.py maquina | entrada inválida `maquina check --machine {payload_ruim}` ⇒ 2 sem traceback |
| G-0618 | co.py maquina | entrada inválida `maquina acao_zz` ⇒ 2 sem traceback |
| G-0619 | co.py maquina | erro interno (maquina_tipo_errado) ⇒ ≠ 0 sem traceback |
| G-0620 | co.py pontos | flag desconhecida ⇒ 2 sem traceback |
| G-0621 | co.py pontos | entrada inválida `pontos acao_zz` ⇒ 2 sem traceback |
| G-0622 | co.py pontos | erro interno (ledger_corrompido) ⇒ ≠ 0 sem traceback |
| G-0623 | co.py oraculo | flag desconhecida ⇒ 2 sem traceback |
| G-0624 | co.py oraculo | entrada inválida `oraculo mudar --motivo m` ⇒ 2 sem traceback |
| G-0625 | co.py oraculo | entrada inválida `oraculo acao_zz` ⇒ 2 sem traceback |
| G-0626 | co.py oraculo | erro interno (ledger_corrompido) ⇒ ≠ 0 sem traceback |
| G-0627 | co.py plano | flag desconhecida ⇒ 2 sem traceback |
| G-0628 | co.py plano | entrada inválida `plano acao_zz` ⇒ 2 sem traceback |
| G-0629 | co.py plano | erro interno (ledger_corrompido) ⇒ ≠ 0 sem traceback |
| G-0630 | co.py lote | flag desconhecida ⇒ 2 sem traceback |
| G-0631 | co.py lote | entrada inválida `lote acao_zz` ⇒ 2 sem traceback |
| G-0632 | co.py lote | erro interno (ledger_corrompido) ⇒ ≠ 0 sem traceback |
| G-0633 | co.py diff | flag desconhecida ⇒ 2 sem traceback |
| G-0634 | co.py diff | entrada inválida `diff T-99 --base {base} --repo {alvo}` ⇒ 2 sem traceback |
| G-0635 | co.py diff | entrada inválida `diff` ⇒ 2 sem traceback |
| G-0636 | co.py diff | erro interno (ledger_corrompido) ⇒ ≠ 0 sem traceback |
| G-0637 | co.py colisao | flag desconhecida ⇒ 2 sem traceback |
| G-0638 | co.py colisao | entrada inválida `colisao` ⇒ 2 sem traceback |
| G-0639 | co.py colisao | erro interno (ledger_corrompido) ⇒ ≠ 0 sem traceback |
| G-0640 | co.py trava | flag desconhecida ⇒ 2 sem traceback |
| G-0641 | co.py trava | entrada inválida `trava integracao acao_zz` ⇒ 2 sem traceback |
| G-0642 | co.py trava | erro interno (ledger_corrompido) ⇒ ≠ 0 sem traceback |
| G-0643 | co.py medir | flag desconhecida ⇒ 2 sem traceback |
| G-0644 | co.py medir | entrada inválida `medir --config zz` ⇒ 2 sem traceback |
| G-0645 | co.py medir | erro interno (ledger_corrompido) ⇒ ≠ 0 sem traceback |
| G-0646 | co.py comparar | flag desconhecida ⇒ 2 sem traceback |
| G-0647 | co.py comparar | entrada inválida `comparar --rodada nao-int` ⇒ 2 sem traceback |
| G-0648 | co.py comparar | erro interno (ledger_corrompido) ⇒ ≠ 0 sem traceback |
| G-0649 | co.py portao | flag desconhecida ⇒ 2 sem traceback |
| G-0650 | co.py portao | entrada inválida `portao acao_zz` ⇒ 2 sem traceback |
| G-0651 | co.py portao | entrada inválida `portao run --only G99` ⇒ 2 sem traceback |
| G-0652 | co.py portao | erro interno (ledger_corrompido) ⇒ ≠ 0 sem traceback |
| G-0653 | co.py veredito | flag desconhecida ⇒ 2 sem traceback |
| G-0654 | co.py veredito | entrada inválida `veredito --formato-zz` ⇒ 2 sem traceback |
| G-0655 | co.py veredito | erro interno (ledger_corrompido) ⇒ ≠ 0 sem traceback |
| G-0656 | co.py aprovar | flag desconhecida ⇒ 2 sem traceback |
| G-0657 | co.py aprovar | entrada inválida `aprovar stop --decisao aprovado` ⇒ 2 sem traceback |
| G-0658 | co.py aprovar | entrada inválida `aprovar stop --decisao talvez` ⇒ 2 sem traceback |
| G-0659 | co.py aprovar | erro interno (ledger_corrompido) ⇒ ≠ 0 sem traceback |
| G-0660 | co.py hook | flag desconhecida ⇒ 2 sem traceback |
| G-0661 | co.py hook | entrada inválida `hook acao_zz` ⇒ 2 sem traceback |
| G-0662 | co.py hook | erro interno (stdin_tipo_errado) ⇒ ≠ 0 sem traceback |
| G-0663 | co.py retomar | flag desconhecida ⇒ 2 sem traceback |
| G-0664 | co.py retomar | entrada inválida `retomar --flag-zz` ⇒ 2 sem traceback |
| G-0665 | co.py retomar | erro interno (ledger_corrompido) ⇒ ≠ 0 sem traceback |
| G-0666 | co.py reabrir | flag desconhecida ⇒ 2 sem traceback |
| G-0667 | co.py reabrir | entrada inválida `reabrir T-01` ⇒ 2 sem traceback |
| G-0668 | co.py reabrir | erro interno (ledger_corrompido) ⇒ ≠ 0 sem traceback |
| G-0669 | co.py (global) | sem --work ⇒ 2 |

### h — operacionais via ev

| id | item | caso |
|---|---|---|
| H-0670 | ev genese | operacional fora de nota/checkpoint ⇒ recusa sem gravar |
| H-0671 | ev janela_inicio | operacional fora de nota/checkpoint ⇒ recusa sem gravar |
| H-0672 | ev checkpoint_janela_50 | controle: aceito, estado e hash_estado inalterados |
| H-0673 | ev nota | controle: aceito, estado e hash_estado inalterados |
| H-0674 | ev despachada | operacional fora de nota/checkpoint ⇒ recusa sem gravar |
| H-0675 | ev retornou | operacional fora de nota/checkpoint ⇒ recusa sem gravar |
| H-0676 | ev colhida | operacional fora de nota/checkpoint ⇒ recusa sem gravar |
| H-0677 | ev perdida | operacional fora de nota/checkpoint ⇒ recusa sem gravar |
| H-0678 | ev aprovacao | operacional fora de nota/checkpoint ⇒ recusa sem gravar |
| H-0679 | ev manifest_gravado | operacional fora de nota/checkpoint ⇒ recusa sem gravar |
| H-0680 | ev oraculo_congelado | operacional fora de nota/checkpoint ⇒ recusa sem gravar |
| H-0681 | ev trava_adquirida | operacional fora de nota/checkpoint ⇒ recusa sem gravar |
| H-0682 | ev trava_liberada | operacional fora de nota/checkpoint ⇒ recusa sem gravar |
| H-0683 | ev medicao_registrada | operacional fora de nota/checkpoint ⇒ recusa sem gravar |
| H-0684 | ev portao_relatorio | operacional fora de nota/checkpoint ⇒ recusa sem gravar |
| H-0685 | ev teto_recuado | operacional fora de nota/checkpoint ⇒ recusa sem gravar |
| H-0686 | ev contrato_hash | operacional fora de nota/checkpoint ⇒ recusa sem gravar |
| H-0687 | ev retomada | operacional fora de nota/checkpoint ⇒ recusa sem gravar |

### i — entrega

| id | item | caso |
|---|---|---|
| I-0688 | entrega | controle: run completo, final, GO, pass^3, aprovações com audit ⇒ ENTREGUE |
| I-0689 | entrega | controle: GO (com waiver) em G2 com aprovação ⇒ ENTREGUE |
| I-0690 | entrega | relatório parcial (only=[G0..G4]) ⇒ não entrega (nada gravado) |
| I-0691 | entrega | relatório final=false ⇒ não entrega (nada gravado) |
| I-0692 | entrega | GO (simulado) com medição simulada ⇒ não entrega (nada gravado) |
| I-0693 | entrega | veredito NO-GO ⇒ não entrega (nada gravado) |
| I-0694 | entrega | item G9 FAIL com veredito GO gravado ⇒ não entrega (nada gravado) |
| I-0695 | entrega | item G12 ERRO com veredito GO ⇒ não entrega (nada gravado) |
| I-0696 | entrega | medição final com k=1 ⇒ não entrega (nada gravado) |
| I-0697 | entrega | medição k=3 simulada ⇒ não entrega (nada gravado) |
| I-0698 | entrega | medição final com k=0 (nenhuma execução) ⇒ não entrega (nada gravado) |
| I-0699 | entrega | gate-report alterado após o evento ⇒ não entrega (nada gravado) |
| I-0700 | entrega | gate-report sem evento portao_relatorio ⇒ não entrega (nada gravado) |
| I-0701 | entrega | aprovação feita por tool_call permitida no audit ⇒ não entrega (nada gravado) |
| I-0702 | entrega | relatório sem o item G0 ⇒ não entrega (nada gravado) |
| I-0703 | entrega | relatório sem o item G1 ⇒ não entrega (nada gravado) |
| I-0704 | entrega | relatório sem o item G2 ⇒ não entrega (nada gravado) |
| I-0705 | entrega | relatório sem o item G3 ⇒ não entrega (nada gravado) |
| I-0706 | entrega | relatório sem o item G4 ⇒ não entrega (nada gravado) |
| I-0707 | entrega | relatório sem o item G5 ⇒ não entrega (nada gravado) |
| I-0708 | entrega | relatório sem o item G6 ⇒ não entrega (nada gravado) |
| I-0709 | entrega | relatório sem o item G7 ⇒ não entrega (nada gravado) |
| I-0710 | entrega | relatório sem o item G8 ⇒ não entrega (nada gravado) |
| I-0711 | entrega | relatório sem o item G9 ⇒ não entrega (nada gravado) |
| I-0712 | entrega | relatório sem o item G10 ⇒ não entrega (nada gravado) |
| I-0713 | entrega | relatório sem o item G11 ⇒ não entrega (nada gravado) |
| I-0714 | entrega | relatório sem o item G12 ⇒ não entrega (nada gravado) |
| I-0715 | entrega | relatório sem o item G13 ⇒ não entrega (nada gravado) |
| I-0716 | entrega | relatório sem o item G14 ⇒ não entrega (nada gravado) |
| I-0717 | entrega | núcleo G0 WAIVED (com aprovação completa) ⇒ não entrega (nada gravado) |
| I-0718 | entrega | núcleo G1 WAIVED (com aprovação completa) ⇒ não entrega (nada gravado) |
| I-0719 | entrega | núcleo G3 WAIVED (com aprovação completa) ⇒ não entrega (nada gravado) |
| I-0720 | entrega | núcleo G4 WAIVED (com aprovação completa) ⇒ não entrega (nada gravado) |
| I-0721 | entrega | waiver G2 com arquivo de aprovação sem seq ⇒ não entrega (nada gravado) |
| I-0722 | entrega | waiver G2 sem linha tipo aprovacao no audit ⇒ não entrega (nada gravado) |
| I-0723 | entrega | waiver G2 com aprovação de decisão rejeitado ⇒ não entrega (nada gravado) |
| I-0724 | entrega | waiver G2 apontando arquivo solto sem evento nem audit ⇒ não entrega (nada gravado) |
| I-0725 | entrega | waiver G2 com aprovação do portão G6 (outro item) ⇒ não entrega (nada gravado) |
| I-0726 | entrega | relatório obsoleto (alvo mudou depois do run) ⇒ não entrega (nada gravado) |
| I-0727 | entrega | aprovação stop sem linha tipo aprovacao no audit ⇒ não entrega (nada gravado) |
| I-0728 | entrega | aprovação oraculo sem linha tipo aprovacao no audit ⇒ não entrega (nada gravado) |

## Itens sem caso (falha do gerador)

nenhum
