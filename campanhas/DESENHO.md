# construcao-orquestrada — desenho (NÃO implementado)

Data: 2026-10-04. Fonte da experiência: construção da `codebase-specialists` (iterações de eval 1–4 com
skill-creator + campanhas `campanha-iter5..8` com auto-correcao), `PONTOS-DO-FOUNDER.md`, `PROXIMA-RODADA.md`,
`auto-correcao/references/licoes.json5` (L01–L16).

## 1. Propósito e quando disparar

Construir **do zero** um sistema (skill, harness, ferramenta CLI, feature num repo) com uma equipe de subagentes,
prova mecânica de que foi construído e laço de autocorreção medido — "você desenvolveu com minhas premissas, você
testou, você corrigiu", sem que a IA aprove o próprio trabalho.

Dispara em: "constrói X do zero com agentes", "monta/desenvolve essa skill/ferramenta e testa até funcionar",
"quero do jeito que fizemos a codebase-specialists", "desenvolve com evals e autocorreção".
**Não** dispara para: bug pontual com teste falhando (corrige direto), refinar sistema que já existe e já tem
oráculo (é `/auto-correcao` direto), revisão/auditoria (é `/orquestrar-subagentes` direto).

Ela **compõe**, não duplica:

| Skill | Papel aqui | Em que ponto |
|---|---|---|
| `orquestrar-subagentes` | portão delegar/fazer, carta de missão, elenco por ferramenta, evidência E0–E3, verificador cego, síntese GO/NO-GO | E2 (decomposição/elenco), E3 (verificação dos relatórios), E4 (revisão do diff integrado) |
| `auto-correcao` (`ac.py`) | laço medido: oráculo congelado, diagnóstico classificado, frentes disjuntas, remedição, parar/continuar/escalar | E1 (calibração modo `requisito`, freeze), E6 (cada lote de defeitos = 1 campanha `--work`) |
| `skill-creator` | só quando o alvo é skill: `evals.json`, execuções com/sem skill, `grading.json`, viewer, benchmark | E1 (evals e baseline) e E5 (medição) |

## 2. Invariantes (acima de qualquer pressa)

1. **Quem testa ≠ quem constrói.** Testes de aceite e gabaritos são escritos por agente que não recebe a tarefa de
   implementação; nenhuma frente de construção ou correção grava em arquivo do oráculo (`plan check` recusa).
2. **A IA não aprova o próprio trabalho.** Critério de parada, oráculo de requisito, decisões de produto,
   commit/push e mudança de oráculo são portões humanos reais; aprovação simulada aparece no veredito (L13).
3. **Etapa fecha por prova de EFEITO**, não por "concluído" nem por "o subcomando rodou" (L03).
4. **Estado em arquivo, retomável**: qualquer janela nova retoma por `status` + `load` sem o histórico da conversa.

## 3. Etapas

Toda etapa: `co.py load <etapa>` (pacote ≤6.000 caracteres) → trabalho → `co.py done <etapa>` (roda os checks;
falha não avança). Fonte única das etapas: `references/etapas.json5` (mesmo formato de `ciclo.json5`).

| Etapa | Entrada | Saída (em disco) | Check de EFEITO (script) | Gate humano |
|---|---|---|---|---|
| **E0 premissas** | pedido do founder | `obra.json5` (alvo, escopo de escrita, runtimes, orçamento, critério de parada numérico); `pontos.json5` (cada premissa = ponto com id, texto literal, status, onde) | todo ponto tem status e referência a ≥1 cenário de aceite ou motivo "fora do escopo"; critério de parada tem número | `stop`, aceite da lista de pontos |
| **E1 oráculo** | `obra.json5`, `pontos.json5` | `oraculo/` com testes de aceite (agente separado), evals com gabarito oculto, cenários de invariante (vivacidade/E2E quando há estados — L16), baseline sem o sistema, manifesto com hash | **vermelho 100%** antes do código (vazio=0, L15); cada ponto do founder tem cenário; ≥2 asserções/config conferidas à mão; baseline registrado ou dispensa justificada; `oracle verify` | `oracle:requisito` (founder confere testes × premissas) |
| **E2 decomposição** | oráculo congelado | `PLANO.json5`: contrato de nomes (comandos, campos, caminhos), frentes com `escreve[]` disjuntos, ordem (frentes que tocam tudo — ex.: rename — por último e sozinhas), elenco com `model` declarado | `plan check`: disjunção, nenhuma frente no oráculo, todo nome citado no contrato, cada frente cobre ≥1 cenário | decisões de produto (`plan:DEC-*`) |
| **E3 construção** | PLANO | código por frente + relatório JSON (files_changed, testes que passaram de vermelho a verde, E-nível) | `fronts --reported`; diff de cada frente ⊆ `escreve[]`; cenários da frente verdes rodados **pelo orquestrador** | — |
| **E4 integração** | frentes reportadas | árvore integrada; `regressao.json5` com o resultado de cada item | **portão de regressão** 100% (§5); `oracle verify` | `commit` (ou pré-autorização condicionada a E4 verde) |
| **E5 medição** | sistema integrado e congelado | `rodadas/N/RESULTADOS.json5`: qualidade [Q] vs baseline, estrutura [S], custo (tempo, tokens) | execuções isoladas (diretório próprio), corrigidas pelo oráculo congelado; amostra conferida à mão; sistema não mudou durante a medição (hash) | — |
| **E6 correção** | defeitos medidos | `DEFEITOS.json5` classificado; 1 campanha `auto-correcao` por lote de arquivos disjuntos | só defeito de classe `sistema` vira frente (L08); cada um com teste que falha antes/passa depois; campanhas sobrepostas respeitam a regra de colisão (§6) | os da própria auto-correcao |
| **E7 fechamento de rodada** | resultados + campanhas | `pontos.json5` atualizado, `RETOMADA.md` (prompt autocontido da próxima rodada), `checkpoint.json5`, decisão parar/continuar/escalar | todo ponto mudou de status ou tem motivo; `RETOMADA.md` existe, cita só caminhos que existem e o comando de retomada; decisão compara com o critério | aceitar a decisão; continuar após ~50% da janela |

E5–E7 repetem por rodada (`co.py round new` exige a anterior fechada). E1 só reabre por `oracle change --why
--evidence` (requisito novo do founder entra como **extensão** do oráculo, nunca ajuste para passar).

### Como cada skill é chamada

- **E1**: o orquestrador cria a campanha-mãe (`ac.py --work <ws>/campanha-construcao init --stop ...`) e usa as
  etapas `oraculo` dela em modo `requisito` — não reimplementa calibração/freeze. Se o alvo é skill, o
  skill-creator gera `evals/evals.json` e roda o **baseline sem skill** (`without_skill/`) uma vez; nunca de novo.
- **E2–E3**: o passo 1–6 da `orquestrar-subagentes` (carta de missão = `PLANO.json5`; elenco via `roster.py`;
  tipo com `Write`+`Bash` para construtor; `isolation: "worktree"` quando dois construtores tocam o mesmo repo).
- **E3/E4**: afirmação de construtor de severidade alta ("passa", "não quebra X") vai ao **verificador cego**
  (passo 7); `synthesize.py` dá GO/NO-GO do lote. O orquestrador re-executa toda evidência E2.
- **E5**: alvo skill → fluxo do skill-creator (grader, `aggregate_benchmark`, viewer para o founder); outros alvos →
  `ac.py run record` + `results compare`.
- **E6**: cada campanha é um `--work` próprio da auto-correcao, com seu `aprovar-<campanha>.sh` para o founder.

## 4. Mecânico (script) vs julgamento (modelo)

| Script (`co.py` + `ac.py` + `synthesize.py`) | Modelo |
|---|---|
| estado, transições, `load`/`done`, checks de efeito | entender premissas, escrever contrato e PLANO |
| hash/freeze/verify do oráculo; vermelho-100% antes do código | escrever testes de aceite (agente separado) |
| disjunção de `escreve[]`, colisão entre campanhas, lote ≤3 | decompor em frentes e escolher elenco |
| diff de cada frente ⊆ território (git diff vs PLANO) | implementar dentro do território |
| portão de regressão (roda os itens, grava resultado) | classificar defeito (sistema/oráculo/ambiente/executor) |
| [Q]×[S]×custo, comparação com baseline e critério de parada | conferir amostra à mão; ler notes.md |
| registro de pontos, `RETOMADA.md` validado (caminhos existem), checkpoint | redigir a RETOMADA e o relatório |
| gerar `aprovar-*.sh` com os portões pendentes | — (nunca executa o script de aprovação) |

`co.py` é fino: guarda o **portfólio** (obra, pontos, rodadas, campanhas ativas, regressão, retomada) e delega o
laço a `ac.py`. Python 3 puro, testado em 3.13 e 3.9 (L10).

## 5. Portão de regressão (E4) — declarado em dados, rodado por script

`regressao.json5` nasce em E2 com itens executáveis (`{id, cmd, espera}`); `co.py regressao run` roda todos.
Padrão herdado do caso real (10 itens; na campanha-iter5 só o placar "10/10" ficou em disco — a lista não foi
persistida, defeito a não repetir):
1. todas as suítes em todos os runtimes declarados; 2. oráculo intacto (hash); 3. diff de máquinas/contratos
(nenhuma transição/guarda/comando removido — compara inventário antes/depois); 4. nada removido sem ponto do founder;
5. vivacidade (nenhum estado trancado); 6. E2E do workflow; 7. instalação limpa em diretório temporário;
8. upgrade de alvo legado; 9. doctests docs↔CLI (todo comando citado na doc existe — L09); 10. registro de pontos
coerente com o que foi entregue. Itens 5, 6 e 8 só se aplicam quando o alvo tem estado/instalação; dispensa é
explícita no arquivo, nunca silenciosa.

## 6. Paralelismo

- **Intra-rodada (E3)**: frentes com `escreve[]` disjuntos e contrato de nomes fixado antes; lotes ≤3 subagentes
  em primeiro plano; espera o lote; ninguém redespacha antes de o lote voltar (L06); cada subagente grava só o
  próprio território; **só o orquestrador grava estado**, em série.
- **Campanhas sobrepostas (E6, lição L17 nova)**: no caso real as campanhas iter5→iter8 rodaram em série, e o
  oráculo da seguinte só começava depois da integração da anterior — tempo de parede perdido. Regra:
  - campanha B pode rodar `intake/oraculo/base/diagnostico/plano` (só leitura no alvo; escrita só em `oraculo/`
    dela e no `--work` dela) enquanto A está em `correcao/integracao`;
  - B só entra em `correcao` se `escreve(B) ∩ (escreve(A) ∪ oraculo(A)) = ∅` (`co.py collide A B`);
    colisão → B espera A integrar e **re-mede o base** antes de corrigir;
  - **integração é serial** (trava `integracao.lock` no portfólio): uma campanha integra por vez, e o portão de
    regressão roda os oráculos de TODAS as campanhas já fechadas (não regressão — como iter6/iter7 fizeram);
  - teto global: ≤3 subagentes vivos somando todas as campanhas; ≤2 campanhas ativas.
- Frente que toca quase tudo (rename, mudança de formato de estado) nunca sobrepõe: roda sozinha, por último.

## 7. Modelo de estado em disco

Tudo fora do alvo, em `<workspace>/` (padrão `~/.claude/skills/<alvo>-workspace/` ou `<repo>/../<nome>-obra/`):
```
.construcao/state.json         etapa atual, rodada, campanhas ativas, travas, portões (escrito só por co.py)
.construcao/ledger.jsonl       eventos (etapa, gate, freeze, regressão, rodada) — append-only
obra.json5                     contrato: alvo, escopo, runtimes, orçamento, critério de parada
pontos.json5 (+ PONTOS.md)     registro do founder: {id, texto_literal, status, cenarios[], onde}; .md é renderizado
oraculo/MANIFEST.json5         arquivos do oráculo + hash + autor (agente ≠ construtor) + calibração
PLANO.json5, regressao.json5   contrato de nomes, frentes, elenco; itens do portão
rodadas/N/                     RESULTADOS.json5, DEFEITOS.json5, runs/<id>/ (execução isolada + notes.md)
campanhas/<nome>/.auto-correcao/   uma por campanha (formato da auto-correcao, intacto)
aprovar-<etapa|campanha>.sh    gerado; só o founder roda
RETOMADA.md, checkpoint.json5  prompt da próxima rodada; foto do estado para retomada
```
JSON5 para tudo que máquina lê; Markdown só explica (decisão de base E do founder).

## 8. Gates humanos

`stop` (E0), `oracle:requisito` (E1), `plan:DEC-*` (E2), `commit`/`push` (E4, ou `preauth commit --requires E4`),
`oracle change`, qualquer escrita fora do escopo da obra, e "continuar" após ~50% da janela de uso.
Mecanismo: o orquestrador **gera** `aprovar-*.sh` com os comandos exatos e para; o founder roda e avisa. Aprovação
`--simulated` (evals, sem humano) é permitida só em E5 e marca o veredito como "GO (simulado)" (L13).

## 9. Critério de parada

Fixado em E0, numérico, aprovado pelo founder; mudá-lo invalida o portão `stop` (pendência v0.3 da auto-correcao).
Formato: oráculo da obra 100% verde + oráculos de não regressão verdes + suítes em todos os runtimes + portão de
regressão completo + [Q] ≥ baseline (+ alvo de custo, se houver) + 0 contornos manuais nas execuções.
Saídas de E7: **parar** (critério cumprido → congela, relatório), **continuar** (progresso medido e orçamento),
**escalar** (2 rodadas sem progresso ou orçamento esgotado → limites documentados, decisão do founder). Nunca
"mais uma rodada" às cegas (L14).

## 10. Limite de uso (janela de contexto e 5 h)

- Uma janela de contexto por etapa; pacote de handoff ≤6.000 caracteres lido do disco.
- Orçamento em proxies observáveis (rodadas, horas de parede, subagentes simultâneos, execuções de eval).
- Execuções de eval **uma por vez**; frentes ≤3 em paralelo; lote em primeiro plano (L07).
- Em ~50% da janela de uso: checkpoint + pergunta. Em E7 (sempre) ou ao estourar: `RETOMADA.md` autocontido
  ("cole numa sessão nova após o reset"), com: alvo, estado, decisões já aprovadas (com o comando de gate a
  re-registrar), contrato de nomes, oráculo e como rodá-lo, critério de parada, orçamento, portões, fora do escopo.
  `co.py retomada check` falha se o prompt cita caminho inexistente ou etapa diferente da do `state.json`.
- Execução interrompida retoma pelo disco; nunca do zero.

## 11. Riscos e anti-padrões (das lições reais)

| Anti-padrão | Lição | Contramedida mecânica |
|---|---|---|
| confiar no placar do corretor | L01 (baseline 1/44 por corretor cego) | calibração vazio/bom/≥2 à mão; reabre se o formato muda |
| ganho inflado por misturar forma e conteúdo | L02 (+0,56 vs +0,23 real) | resumo sempre [Q] e [S] em colunas separadas |
| check que só prova que o comando rodou | L03 | todo check nasce com teste "comando passa, efeito não" |
| mexer no sistema durante a medição; sem baseline | L04 (skill 4–8× mais cara) | hash do sistema na medição; custo ao lado |
| execuções compartilhando scratch | L05 | diretório próprio por execução |
| 8 subagentes → 429 e sobrescrita | L06 | teto global ≤3, espera o lote |
| sessão cai no meio | L07 | estado em arquivo, `load` retoma |
| corrigir o sistema por defeito do oráculo | L08 (metade dos NO-GO) | classe obrigatória antes do plano |
| doc cita flag que não existe | L09 | contrato de nomes + doctest docs↔CLI |
| regressão só em Python antigo | L10 | todos os runtimes no portão |
| veredito diferente para o mesmo estado | L11 | regra de decisão escrita e testada no caso de borda |
| processo caro sem valor medido | L12 | medir modo barato ao lado do completo |
| GO simulado lido como aprovado | L13 | "GO (simulado)" no veredito |
| loop infinito de rodadas | L14 | stop numérico em E0 |
| requisito novo sem "saída boa" | L15 | modo `requisito`: vermelho 100% + founder confere |
| 480 testes verdes e máquina trancada | L16 | vivacidade + E2E no oráculo antes do freeze |
| campanhas em série com tempo ocioso | **L17 (nova)** | sobreposição com `collide` + integração serial |
| registro do founder desatualizado / pontos perdidos | (PONTOS-DO-FOUNDER) | E7 falha se ponto não mudou nem tem motivo |
| lista do portão só como placar "10/10" | (campanha-iter5) | `regressao.json5` com comandos, rodado por script |

## 12. Divergências do método observado (validado contra as fontes)

- **Duas fases reais, não uma**: iterações 1–4 foram evals do skill-creator (with/without skill, [Q] 13/13 vs
  baseline 9–10/13); campanhas 5–8 foram auto-correcao em modo `requisito` sem baseline (requisito novo não tem). O
  desenho mantém baseline em E1 só quando há tarefa comparável; senão dispensa registrada.
- **"Quem testa ≠ quem constrói" foi parcial**: na campanha-iter5 o teste de vivacidade foi escrito pelo
  orquestrador (o E2E e a cobertura, por agente separado). O invariante aqui é: autor do oráculo ≠ frente que
  implementa; o orquestrador pode escrever oráculo, mas então não implementa aquela frente.
- **Portão de regressão de 10 itens não está em disco** (só "10/10" no `state.json`) — a lista do §5 vem do brief;
  o desenho exige persistir os itens.
- **Campanhas 5–8 tiveram 1 rodada cada** e várias com 1 frente só (iter7): a autocorreção real foi "campanha por
  lote de defeitos", não "várias rodadas por campanha" — E6 reflete isso.
- **L17 não existe ainda** em `licoes.json5` (vai até L16); gravá-la exige editar a auto-correcao (pergunta 5).
