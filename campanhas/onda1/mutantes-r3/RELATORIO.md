# M3 — mutação G5 da onda 1 (rodada 3)

Agente independente: não construiu e não escreveu testes. Não li `mutantes/` nem `mutantes-r2/`.

## Veredito

**O critério NÃO foi atendido.**

| | total | mortos | taxa | critério |
|---|---|---|---|---|
| Parte A (mutantes próprios) | 152 | 109 | **71,7%** (72,2% sem o 1 equivalente) | ≥80% → **reprova** |
| Retorno constante (parte A) | 53 | 47 | 6 sobrevivem | todos mortos → **reprova** |
| Parte B (ocultos r2 reaplicados) | 10 | **1** | 10% | mede generalização → **não generalizou** |

## Método

- **Oráculo congelado no início:** cópia de `tests/onda1` (180 testes) e de `oraculo/heldout` (64 testes), com sha256 em `oraculo_snapshot.sha256`. Toda medição rodou contra essa cópia. Ao fim, conferi que nem a skill nem o heldout mudaram (sha256 iguais aos do início).
- **Base sem mutante:** 5 execuções completas em paralelo, todas verdes (244 testes, 0 falhas, 0 pulados; ver `base/`). Também rodei 1 vez o `run_heldout.py --com-visiveis` oficial, que passou. Nenhuma intermitência apareceu.
- **Ambiente:** 6 HOMEs temporários. Cada um tem `.claude/skills/construcao-orquestrada` (uma cópia) e um link para `auto-correcao`.
- **Um mutante por vez em cada worker:**
  1. Restaura os 4 scripts e confere o sha256 contra a cópia limpa.
  2. Aplica a substituição exata e confere que o trecho original aparece o número esperado de vezes.
  3. Roda `runner.py --failfast` (primeiro heldout, depois visíveis), com `PYTHONDONTWRITEBYTECODE=1`.
  4. Restaura de novo.
- **Contagem:** um mutante sobrevive quando os 244 testes ficam verdes sem nenhum pulado. Todos os sobreviventes rodaram a suíte inteira.
- **Arquivos:**
  - definições: `mutantes_def.py`
  - execução: `driver.py` e `runner.py`
  - resultado por mutante: `res/*.final.json`
  - consolidado: `relatorio.json`

### Distribuição da parte A

| arquivo | mutantes | mortos |
|---|---|---|
| co_estado.py | 71 | 45 |
| co_portao.py | 41 | 29 |
| co_hook.py | 35 | 31 |
| co.py | 5 | 4 |

| tipo | mutantes | mortos |
|---|---|---|
| retorno constante | 50 | 44 |
| normalização de caixa desligada | 2 | 2 |
| hash do disco trocado pelo do payload | 1 | 1 |
| feature removida | 74 | 46 |
| condição invertida | 8 | 6 |
| limite deslocado | 6 | 2 |
| precedência trocada | 4 | 4 |
| campo omitido do hash | 4 | 4 |
| lock removido | 2 | **0** |
| G1 aceitando texto impresso | 1 | **0** |

## Sobreviventes da parte A (43)

**Classes:** `lacuna` = falta um teste e o mutante é alcançável pela CLI ou pelo fluxo; `lacuna_api` = só alcançável pela API Python; `redundante` = outra checagem cobre o caso na superfície do sistema, mas a função pública ainda distingue; `equivalente` = não há entrada que distinga.

### Retorno constante (6). Por causa deles o critério reprova.

- **C05** (lacuna): `co.main` devolve 0 quando uma exceção escapa de `_main`. Nenhum teste força uma exceção fora do try, por exemplo `co_estado` levantando um erro que não é ImportError ao importar.
- **E-RC06** (lacuna_api): `portao_regressao_go` sempre True. A guarda é `portao_regressao_go and verificador_nao_autor`, e `verificador_nao_autor` não é computado na onda 1. Por isso só se alcança via `transicionar(atomos=...)`.
- **E-RC16 / E-RC21** (lacuna): `pontos_completos` e `stop_numerico` sempre True. A guarda `pontos_completos and stop_numerico` nunca é testada com só um dos lados falso.
- **E-RC18** (lacuna): `limite_detectado` sempre True. Nenhum teste recusa `limite_uso` com causa inválida ou `retomar_apos` inválido.
- **H-RC10** (lacuna): `embedded_text_hit` sempre False. Faltam casos em que a recursão do hook não acha o script, como `python3 -c` montando a lista de argv do subprocess ou um comando não tokenizável. O oráculo não cobre isso, e o `--selftest` também não.

### Lacunas relevantes de segurança e integridade

- **E33:** `ev` aceita qualquer evento operacional, então dá para forjar `oraculo_congelado` ou `portao_relatorio` pelo `ev`. Não há teste negativo.
- **E22:** um `portao run` completo **sem `--final`** com GO satisfaria a entrega.
- **E29:** a testemunha do audit, que detecta o fim do ledger truncado a partir de um seq de aprovação, nunca é exercitada sozinha.
- **E30:** em `co_estado.aprovacoes_sem_audit`, uma tool_call permitida que fez a aprovação não "suja" a aprovação. Não há teste para isso.
- **E09 / E10:** lock removido de `transicionar` e de `append_evento`. Não existe nenhum teste de concorrência no ledger.
- **E37:** o desafio comparado só pelo 1º dígito não é detectado.
- **E01:** `seq` adulterado no último registro, com o hash e o cache reescritos, passa.
- **H04:** `env rm -rf <ws>` e `env tee <protegido>` passam, porque `env` deixa de ser tratado como wrapper. Os testes de wrapper só cobrem a aprovação.
- **P01:** G1 aceitando a saída impressa `Ran N tests` só importa quando o runner não grava relatório (suíte que imprime e chama `os._exit(0)`). Não há teste.
- **P02:** o G1 deixa de conferir o nonce do relatório e nada acusa.
- **P08:** um waiver com arquivo de aprovação fora de `<ws>/aprovacoes` é aceito.
- **P19:** gaming por alias passa.
- **P20:** com `**/` exigindo pelo menos um diretório, o G3 passa a reprovar arquivos diretos e ninguém nota.
- **P24:** com PLANO reescrito, o veredito ainda dá NO-GO, mas o G3 e o `co.py diff` passam a dar PASS.

### Funcionalidade sem teste

- **E14:** quando falta o motivo obrigatório, sai exit 1 em vez de 2.
- **E35:** `init` aceita `--teto 0`.
- **E38:** re-aprovação do oráculo com hash diferente, que deveria rodar `oracle change`.
- **E39:** o desafio é pedido mesmo sem campanha-mãe.
- **E44:** MANIFEST em que o autor é também o construtor (D5).
- **E45:** `oraculo manifest` fora do estado ORACULO.
- **E46:** ponto duplicado no `pontos check`.
- **E49:** task `EM_VOO` contando como retornada.
- **E50:** limite de tamanho do `load`.
- **H01 / H02:** duas mudanças na decisão do hook sem risco real, mas observáveis.
  - H01: a exceção `--decisao` passa a valer também para co/ac.
  - H02: a palavra inglesa sai da lista do co.py.

### pytest apenas (lacuna_pytest)

- **P03, P04, P26:** o wrapper de unittest já sai 1 quando nenhum teste executa. Só uma suíte pytest (tudo pulado, ou junit com falhas) distingue esses mutantes, e o oráculo não tem nenhuma.

### Redundantes: defesa em profundidade sem teste unitário

**E21, E24, E25, E26, P14, P27.** Na superfície do sistema outra checagem cobre o caso (`calcular_veredito`, `exigir_todos`, hash conferido pelo ac.py, rodar sempre gravando `only`). Mesmo assim, `relatorio_satisfaz_entrega` e `veredito_detalhado` são funções públicas e distinguiriam com um relatório forjado.

### Provável equivalente, não provado

**P05:** com o filtro de pipe e redireção desligado, `|`, `>` e `||` viram argumentos do runner. O runner então falha (módulo ou arquivo inexistente), o que dá FAIL de qualquer jeito. Não contei como equivalente.

### Equivalente (1)

**E12:** `len(verdade) > 1` trocado por `> 2`. A `maquina.json5` distribuída satisfaz I5, que exige guardas mutuamente exclusivas para toda atribuição. Por isso nunca há mais de uma guarda verdadeira.

## Parte B: os 10 ocultos de r2, reaplicados

Reapliquei cada um pela descrição. Os números de linha mudaram, então usei o trecho equivalente do código atual. **Todos tinham equivalente no código atual. Só 1 morreu.**

| id | adaptação no código atual | resultado |
|---|---|---|
| E36 | `_gate_report_valido`: `if sha_file(p) != ...gate_report_hash` → `if False` | **VIVO**: um gate-report.json reescrito depois do `portao run` seria aceito na entrega |
| P10 | `divergencias_registradas`: a comparação é pulada para `chave == "plano"` | **VIVO**: PLANO reescrito depois do plano_ok passa sem divergência |
| E37 | `congelar_oraculo`: confere o hash registrado pelo ac.py → `if False` | **VIVO**: precisaria de um ac.py falso |
| E14 | `trava_ledger`: `fcntl.flock(LOCK_EX)` desligado | **VIVO**: não há teste de concorrência |
| H24 | `anexar_audit`: removido o `if _ws_acima(d): return False` | **VIVO**: audit dentro de um ws não é testado no hook |
| E31 | `checar_maquina` I6: `hum and (frm != {AH} or not tem)` → `hum and frm != {AH}` | **VIVO**: `maquina check --machine` com transição humana sem `aprovacao_humana` |
| E38 | `preparar_congelamento`: `nt < 1 or na < 1` → `and` | **VIVO**: oráculo com testes e 0 asserções |
| E34 | `relatorio_satisfaz_entrega`: o check `simulado`/`simulated` → `if False` | **VIVO**: redundante parcial, porque `GO (simulado)` já é recusado (E23 da parte A morre) |
| E10 | `problemas_cadeia`: `hash_registro(r) != r["hash"]` → `if False` | **MORTO** por `test_r3_propriedades...test_hash_do_registro_trocado` |
| E18 | `transicionar`: `atomos` do chamador sobrepõem `aprovacao_humana` | **VIVO**: só alcançável pela API Python |

**Leitura:** o oráculo endureceu exatamente onde as rodadas anteriores apontaram e não generalizou para mutantes vizinhos que ficaram escondidos. Os padrões:

- conferências de hash fora da cadeia não são testadas (gate-report, plano_hash, hash do ac.py);
- não há nenhum teste de concorrência;
- invariantes de `maquina check` só são testados com a máquina distribuída;
- os limites de contagem do oráculo não são testados.

## Observação operacional

No início usei `scratchpad/home`, `scratchpad/heldout` e `scratchpad/homes` com `rm -rf` antes de criar. Se outro agente da sessão usava esses nomes, o conteúdo dele foi apagado. Depois disso todo o meu material ficou em `scratchpad/m3/`.
