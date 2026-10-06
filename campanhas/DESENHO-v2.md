# construcao-orquestrada — desenho v2 (consolidado, NÃO implementado)

Data: 2026-10-04. Consolida `DESENHO.md` (8 etapas E0–E7), `pesquisa/loops-e-grafos.md` (máquina, ledger, retomada),
`pesquisa/gates-mecanicos.md` (G0–G12, 15 scripts), `pesquisa/evals-e-oraculos.md` (G1–G9, R1–R6),
`perguntas-ao-founder.md` e `auto-correcao-v03-defeitos.md` (AC-01..AC-04, L17). Onde este texto e o v1 divergirem,
vale este. Princípio: **o LLM decide o conteúdo; o script decide a transição; o hook bloqueia; o ledger prova.**

## 1. Máquina de estado única

Três níveis, uma tabela cada, todas em `references/maquina.json5` (fonte única; `etapas.json5` do v1 deixa de existir):
**obra** (abaixo), **task** (dentro de DESPACHADO) e **campanha** (é a máquina de `ac.py`/`ciclo.json5`, intacta;
o `co.py` só acompanha o status dela: `RASCUNHO → ATIVA → PRONTA_INTEGRAR → INTEGRADA | ABANDONADA`).
Etapas do v1 viram estados: E0=PREMISSAS, E1=ORACULO+BASELINE, E2=PLANO, E3=LOTE+DESPACHADO, E4=INTEGRAR+VERIFICAR,
E5=MEDIR, E6=CORRIGIR, E7=FECHAR_RODADA. `co.py load <estado>` continua dando o pacote ≤6.000 caracteres.

| De | Evento | Para | Guarda (predicado nomeado em Python) |
|---|---|---|---|
| INICIO | iniciar | PREMISSAS | `hook_vivo` (selftest estático + vivo, §4) ∧ workspace fora do alvo |
| PREMISSAS | premissas_ok | AGUARDANDO_HUMANO(`stop`,`pontos`) | todo ponto tem status e cenário ou motivo; `stop` numérico |
| ORACULO | oraculo_pronto | AGUARDANDO_HUMANO(`oracle:requisito`) | autor ∉ construtores; **vermelho** contra baseline e stub (anti-vácuo); cada ponto → ≥1 cenário; critérios classificados (R2) |
| ORACULO | (aprovado) | BASELINE | `ac.py oracle freeze` gravou hash; contagem de testes/asserções gravada |
| BASELINE | medido | PLANO | `baseline.json` com comando reprodutível e hash do alvo |
| BASELINE | dispensado | PLANO | tipo ∉ {skill, agente} ∧ motivo registrado (dispensa explícita) |
| PLANO | plano_ok | AGUARDANDO_HUMANO(`plan:DEC-*`) se há DEC, senão LOTE | `plan check`: DAG acíclico, `writes` disjuntos, nenhuma task no oráculo, todo nome no contrato, cada task cobre ≥1 cenário; `contrato_hash` gravado |
| LOTE | lote_ok | DESPACHADO | `len(lote) ≤ teto_livre` (teto global 3) ∧ writes/reads disjuntos ∧ deps aceitas ∧ orçamento > 0 |
| LOTE | fronteira_vazia | INTEGRAR | toda task do plano RETORNADA ou ACEITA |
| DESPACHADO | todos_retornaram | LOTE | cada DESPACHADA tem RETORNOU no ledger (write-ahead, §6) |
| DESPACHADO | limite_uso | PAUSADO | grava `retomar_apos`; nenhum despacho novo |
| INTEGRAR | merge_ok | VERIFICAR | trava `integracao.lock` adquirida; merge em ordem de id; **oráculo rodado após cada merge**; diff ⊆ writes (G3) |
| INTEGRAR | violou | CORRIGIR | G3 ou G4 (gaming) reprovou; a task volta REJEITADA |
| VERIFICAR | verde | MEDIR | portão de regressão GO (§3) ∧ verificador ≠ autor (relatório do verificador cego) |
| VERIFICAR | vermelho | CORRIGIR | `tentativas < 3` ∧ ¬`mesma_rejeicao_2x` |
| VERIFICAR | vermelho | REPLANEJAR | `tentativas ≥ 3` ∨ `mesma_rejeicao_2x` ∨ `oscilacao` (hash de diff repetido) |
| MEDIR | medido | FECHAR_RODADA | sistema com hash congelado durante a medição; execuções em cópia limpa; registro **posterior** ao último merge (AC-01) |
| CORRIGIR | campanhas_abertas | LOTE | defeitos classificados; só classe `sistema` vira task (L08); cada uma com teste que falha antes; incrementa `tentativas` |
| FECHAR_RODADA | parar | AGUARDANDO_HUMANO(`entrega`) | critério de parada cumprido (§9 do v1) ∧ pontos atualizados ∧ RETOMAR.md válido |
| FECHAR_RODADA | continuar | CORRIGIR | `rodada < max_rodadas` (padrão 3) ∧ progresso medido ∧ ¬`plato_2` |
| FECHAR_RODADA | escalar | AGUARDANDO_HUMANO(`escalar`) | `plato_2` ∨ orçamento esgotado ∨ `rodada = max_rodadas` |
| REPLANEJAR | novo_plano | PLANO | incrementa `replanejamentos` (teto 2); invalida aceites cujo `hash_entradas` mudou |
| REPLANEJAR | desistir | AGUARDANDO_HUMANO(`abandonar`) | sempre |
| AGUARDANDO_HUMANO | aprovado | `retorno` (anotado) ou ENTREGUE se portão=`entrega` | `aprovacao_humana(portao, hash_estado)` (§4) |
| AGUARDANDO_HUMANO | rejeitado | REPLANEJAR (ou PREMISSAS se portão=`stop`) | idem, decisão=reject |
| AGUARDANDO_HUMANO | abandonar | ABANDONADO | idem |
| (qualquer não final) | limite_uso / janela_50 | PAUSADO / AGUARDANDO_HUMANO(`continuar`) | `retorno` gravado; `pausas` incrementa (teto 6 → AGUARDANDO_HUMANO) |
| PAUSADO | retomar | `retorno` | `agora ≥ retomar_apos` ∧ `co.py retomar` sem tasks perdidas não resolvidas |
| ENTREGUE, ABANDONADO | — | — | finais |

**Task**: `PENDENTE → PRONTA → EM_VOO → RETORNADA → ACEITA | REJEITADA`; `REJEITADA → PRONTA` com tentativa+1 (teto 3);
`ACEITA → PRONTA` só por `reabrir --motivo` (hash de entrada mudou). `ORACULO` é reentrado só por `oracle change
--why --evidence` (portão humano; requisito novo entra como extensão, nunca ajuste para passar).

**Invariantes checáveis** (`co.py maquina check`, BFS sobre o JSON, sem LLM; roda em INICIO e no G8):
1. Alcançabilidade: todo estado alcançável de INICIO. 2. Vivacidade: de todo não final há caminho a ENTREGUE ou
ABANDONADO; AGUARDANDO_HUMANO e PAUSADO nunca finais e têm saídas aprovar/rejeitar/abandonar/retomar (L16).
3. Sem atalho: removendo VERIFICAR, ENTREGUE fica inalcançável; removendo AGUARDANDO_HUMANO também.
4. Todo ciclo contém transição que incrementa contador com teto (`tentativas`, `rodada`, `replanejamentos`, `pausas`).
5. Determinismo: para cada (estado, evento) as guardas são mutuamente exclusivas — testado por tabela-verdade.
6. Transição `ator: humano` só por `aprovacao_humana`; nenhuma outra porta grava `gates`.
7. Monotonicidade: ACEITA/ENTREGUE só saem por evento explícito com motivo (`reabrir`, `oracle change`).

## 2. Scripts — um `co.py`, quatro módulos, reaproveitamento explícito

Os 7 (loops) + 15 (gates) + 9 (evals) scripts propostos colapsam em `scripts/co.py` (CLI, argparse único — é a
superfície que o G12 confere) + módulos sem CLI própria: `co_estado.py` (máquina, ledger, fold, retomar),
`co_portao.py` (G0–G14), `co_medir.py` (cópia limpa, k execuções, IC, mutantes, anti-vácuo), `co_hook.py`
(hook PreToolUse, arquivo separado para ser pequeno e falhar fechado). Python 3 stdlib, 3.9 e 3.13 (L10).
Convenção: **0 = passa/GO · 1 = reprova/NO-GO · 2 = entrada inválida ou ferramenta ausente (falha fechado)**.

| Subcomando | Entrada | Saída | Teste negativo com que nasce (L03) |
|---|---|---|---|
| `init --alvo --tipo skill\|cli\|repo\|harness` | pedido | `obra.json5`, `pontos.json5`, ledger gênese | workspace dentro do alvo ⇒ 2 |
| `ev <evento> [--payload f]` | estado + guarda | append no ledger, `state.json` (cache), `RETOMAR.md` | guarda falsa ⇒ 1 e ledger inalterado (byte a byte) |
| `status` / `load <estado>` | ledger | fold (nunca o cache) / pacote ≤6k | cache adulterado ≠ fold ⇒ `status` mostra o fold e avisa (AC-02) |
| `maquina check [--machine f] [--events f]` | JSON da máquina (do processo **ou** do alvo) | invariantes 1–7; matriz arestas/guardas OK+RECUSA | máquina com estado trancado plantado ⇒ 1 |
| `pontos check` | pontos.json5 | ponto sem status/cenário/motivo | ponto sem cenário ⇒ 1 |
| `oraculo vacuo --stub` | oráculo + baseline + stub | ambos devem reprovar | oráculo que passa no stub ⇒ 1 |
| `oraculo forca --mutantes n` | solução integrada | score; mata 100% de "retorno constante"/"feature removida", ≥80% total | oráculo sem asserção de efeito ⇒ 1 |
| `plano check` | PLANO.json5 | DAG, disjunção, contrato, cobertura | duas tasks com glob sobreposto ⇒ 1 |
| `lote proximo` / `lote despachar <task>` / `lote retornar <task> --relatorio` | DAG + ledger | fronteira ≤ teto livre; DESPACHADA **antes** do Agent; RETORNOU | 4ª task viva ⇒ 1; `retornar` sem `despachar` ⇒ 2 |
| `diff <task> --base <sha>` | git diff (inclui deleção/rename) | território (G3) + padrões de gaming (G4) | `sed` indireto num arquivo fora; `pytest.skip` novo ⇒ 1 |
| `colisao A B` / `trava integracao acquire\|release` | writes+oráculo de A e B | disjunto ou lista de colisões; lock com dono | colisão via oráculo de A ⇒ 1; 2º acquire ⇒ 1 |
| `medir --k 3 [--config]` | sistema + oráculo held-out | `rodadas/N/runs/<id>/` em `tempfile`, pass@k, pass^k, hash do sistema | sistema mudou durante a medição ⇒ 1; run anterior ao merge ⇒ 1 (AC-01) |
| `comparar --base --com` | runs pareados por item | delta pareado, IC95 bootstrap; [Q] e [S] em colunas | totais de [Q] diferentes sem `oracle change` ⇒ 1 (AC-03) |
| `portao run [--only] ` / `portao selftest` | `regressao.json5` | `gate-report.json` + veredito | `selftest`: cada item reprova seu negativo plantado, senão 1 |
| `veredito` | gate-report + state | GO / GO (com waiver) / GO (simulado) / NO-GO | waiver presente e saída "GO" puro ⇒ teste falha |
| `aprovar <portao> --decisao` | **só terminal humano** | registro (usuário SO, tty, hash do estado) | chamada com stdin sem tty ⇒ 2; via hook ⇒ bloqueio |
| `hook` / `hook selftest` | payload PreToolUse | exit 2 + motivo / matriz de payloads | ver §4 |
| `retomar` | ledger + worktrees | cadeia verificada, tasks perdidas, **um** próximo comando | linha do ledger editada ⇒ 1 |

**Reaproveita, não reescreve.** De `auto-correcao/scripts/ac.py`: o laço inteiro de cada campanha (`--work
<ws>/campanhas/<nome>`: `init`, `oracle freeze|verify|change`, calibração modo `requisito`, `plan check`, `front
report`, `run record`, `round new`); o oráculo da obra mora numa campanha-mãe `campanhas/construcao`. Funções puras
(`json5_loads`, `sha_files`, `globs_overlap`) são importadas via `importlib` do caminho da skill, não copiadas.
**Pré-requisito**: `ac.py` v0.3 com AC-01..AC-03 corrigidos (decisão 2); até lá `co.py` recusa a fronteira afetada
(`medir` exige seq posterior; `comparar` confere totais). De `orquestrar-subagentes/scripts/`: `roster.py` (o tipo
escolhido tem Write+Bash para construtor / sem Write para verificador), `mission.py` (carta da missão de verificação
de cada lote), `synthesize.py` (GO/NO-GO dos relatórios do verificador cego — o `veredito` o chama e não reimplementa
dedup/E0–E3). `ledger.py` de lá (rótulos tp/fp) **não** é o ledger de eventos daqui.
**Não se escreve**: `estado.py`/`retomar.py`/`lote.py`/`territorio.py`/`medir.py`/`aprovar.py`/`checar_maquina.py`
(loops), `gate.py`/`oracle.py`/`territory.py`/`surface.py`/`machine.py`/`checkproof.py`/`runtimes.py`/
`install_clean.py`/`legacy.py`/`doccheck.py`/`approve.py`/`verdict.py` (gates), `oracle_freeze.py`…`canary_impossible.py`
(evals) como arquivos — cada um virou subcomando acima ou item de `co_portao.py`.

## 3. Portão de regressão genérico (G0..G14)

`regressao.json5` nasce em PLANO a partir de `references/portao.json5` filtrado por `tipo`; cada item `{id, cmd,
limiar, falha_fechado: true, waiver}`. Não aplicável aparece `N/A (motivo)`, nunca some. **[S]** = sem waiver.

| Item | Prova | skill | CLI | feature em repo | harness c/ máquina |
|---|---|---|---|---|---|
| G0 oráculo intacto **[S]** | hash = congelado; nº de testes/asserções ≥ congelado | ✓ | ✓ | ✓ | ✓ |
| G1 suítes **[S]** | 0 falhas; ≥1 teste coletado por suíte; ferramenta ausente = FAIL | ✓ | ✓ | ✓ (suíte existente = PASS_TO_PASS) | ✓ |
| G2 runtimes | G1 em cada célula (mínimo declarado + atual); skip = FAIL | py 3.9/3.13 | declarados | CI do repo | 3.9/3.13 |
| G3 território **[S]** | diff × writes; nada em protegido; deleção/rename contam | ✓ | ✓ | ✓ | ✓ |
| G4 gaming no diff **[S]** | toque em tests/conftest/config de teste; `skip`/`xfail`/`sys.exit(0)`/`os._exit`/`except: pass`/`assert True`/`__eq__` novo/monkeypatch de avaliador; literal do held-out no código | ✓ | ✓ | ✓ | ✓ |
| G5 força do oráculo **[S]** | anti-vácuo (vermelho em baseline e stub) no freeze + mutantes plantados na solução em VERIFICAR | ✓ | ✓ | ✓ | ✓ |
| G6 superfície pública | snapshot vs base: remoção/incompatível = FAIL, adição = INFO | frontmatter+scripts+flags | subcomandos, flags, exit codes | rotas/OpenAPI, schema | comandos, estados, transições |
| G7 checks provam efeito **[S]** | todo check/subcomando de gate tem par negativo (stub sai 0 sem efeito ⇒ check reprova) | ✓ | ✓ | se cria gate | ✓ |
| G8 máquina | invariantes 1–7 + cobertura de arestas e guardas OK **e** RECUSA | N/A salvo se tiver estado | N/A | se workflow | ✓ **[S]** |
| G9 E2E | caminhos ponta a ponta terminam coerentes (nada trancado) | fluxo da skill | pipeline CI (exit 1 em diff) | rota completa | ✓ |
| G10 instalação limpa | build/cópia em `HOME`/venv temporário + smoke; dry-run lista escrita fora | ✓ | ✓ | N/A | ✓ |
| G11 upgrade legado | fixture por versão publicada migra com invariantes; VERSION ⇒ migração | N/A | N/A | se migração | ✓ |
| G12 docs ↔ CLI | todo comando/flag citado parseia no argparse real (PENDENTES com motivo) | ✓ | README↔`--help` | se doc | ✓ |
| G13 medição | cópia limpa; pass^3 no aceite final; delta pareado com IC95 vs baseline; custo ao lado | ✓ (skill-creator) | requisito: sem baseline | PASS_TO_PASS + FAIL_TO_PASS | ✓ |
| G14 pontos do founder | todo ponto mudou de status ou tem motivo; nada removido sem ponto | ✓ | ✓ | ✓ | ✓ |

- **Força do oráculo**: mutantes AST (inverter comparação, off-by-one, remover ramo, retorno constante) + 3–5
  semânticos pedidos a um subagente que **não** é construtor nem autor do oráculo; equivalentes descontados com nota.
- **Medição em cópia limpa**: `co_medir` copia o produto para `tempfile` sem `.git`, injeta o held-out só ali,
  roda em subprocess com timeout, compara por JSON serializado (nunca `==` de objeto); uma execução por vez.
- **Comparação pareada**: delta por item (com − sem), IC95 bootstrap (cluster por cenário). "Melhora" só se o IC
  exclui 0; senão "indício" ou "sem efeito". n<30: faixas, não decimais. [Q] e [S] nunca somados (L02).
- **Juiz LLM** só onde nada mecânico serve: rubrica binária, citação literal conferida por `in`, troca A/B, controles
  vazio/ouro/ruim-verboso; descalibrado ⇒ INCONCLUSIVO. Monitor LLM do diff = **veto auditado**, nunca feedback (R5).

## 4. Gate humano não forjável (até onde dá)

1. **Canal**: aprovação só por `co.py aprovar` (e `ac.py gate|preauth`) digitado pelo founder num terminal fora da
   sessão. `co.py` gera `aprovar-<portao>.sh` com os comandos exatos e para em AGUARDANDO_HUMANO; nunca o executa.
2. **Hook** (`co_hook.py`, PreToolUse em `~/.claude/settings.json`, matcher `Bash|Write|Edit|MultiEdit|NotebookEdit`):
   bloqueia (exit 2, "peça ao founder que rode no terminal") **qualquer** tool call — principal ou subagente, pois o
   principal não tem `agent_id` e é indistinguível do humano pelo payload — que (a) invoque `aprovar`, `gate`,
   `preauth`, `oracle change` de `co.py`/`ac.py`, inclusive via `python3 -c`, `bash -c`, variável ou caminho
   relativo (normaliza e procura os tokens), salvo `--simulated` em estado MEDIR; (b) escreva em `.construcao/**`,
   `aprovacoes/**`, `oraculo/**` (exceto o agente-oráculo listado no MANIFEST, identificado por `agent_type`), ou
   (c) leia `oraculo/heldout/**` vindo de subagente construtor. Subagente sem `agent_type` ⇒ fail-closed.
3. **Prova extra no comando**: `aprovar` exige `stdin` e `/dev/tty` interativos e um desafio de 4 palavras impresso e
   redigitado; grava usuário do SO, `ttyname`, ts e `hash_estado` aprovado (aprovação vale só para aquele estado).
4. **Auditoria independente**: o hook registra toda chamada que cite `co.py`/`ac.py` em
   `~/.claude/construcao-orquestrada/audit.jsonl` (fora do workspace); `veredito` cruza cada aprovação do ledger
   com a ausência de chamada de ferramenta correspondente no audit.
5. **Selftest**: `hook selftest` alimenta payloads sintéticos (subagente e principal chamando `aprovar`; variantes
   ofuscadas; Write em `.construcao/state.json`; Read do held-out por construtor; comando benigno ⇒ 0). **Vivo**: em
   INICIO o orquestrador despacha um subagente mínimo que tenta `co.py aprovar __selftest__`; guarda `hook_vivo` exige
   o bloqueio registrado no audit — cobre o relato de PreToolUse não disparando em subagente (issue #34692).
6. **Limite honesto**: com shell sem sandbox, nada é criptograficamente impossível de forjar (pseudo-tty via
   `script`, editar o hook, reescrever a cadeia do ledger). O desenho garante que forjar exige ato deliberado,
   fora do padrão e visível no audit — não impossibilidade. Mais forte (fora do escopo v1): aprovação por PR review
   ou assinatura ssh/gpg com chave fora do alcance do agente. A SKILL.md declara isso como premissa.

## 5. Paralelismo

- **Teto global: 3 subagentes vivos** somando construtores, agente-oráculo, verificador cego e campanhas; contado no
  ledger (DESPACHADA sem RETORNOU), imposto por `lote proximo`. **≤2 campanhas ativas.** Lote em primeiro plano;
  ninguém redespacha antes de o lote voltar (L06). `isolation: "worktree"` com chave `obra/rodada/task/tentativa`
  quando duas tasks tocam o mesmo repo (rede de segurança: disjunção já evita conflito).
- **Intra-rodada**: contrato de nomes congelado antes; tasks com writes/reads disjuntos; task que toca quase tudo
  (rename, formato de estado) roda sozinha e por último. Só `co.py` grava estado, em série.
- **Campanhas sobrepostas (L17)**: B roda intake/oráculo/base/diagnóstico/plano (escreve só em seu `--work` e
  `oraculo/` dele) enquanto A corrige ou integra. B congela e entra em correção cedo **só se** `colisao A B` vazio
  **e** A não muda o contrato de nomes; senão espera A integrar e **re-mede o base**.
- **Integração serial**: `trava integracao` (uma por vez, ordem determinística por id); oráculo completo após
  **cada** merge (bisect barato); o portão roda os oráculos de todas as campanhas já fechadas (não regressão).
- **Pipelining da construção**: o agente-oráculo da onda N+1 escreve enquanto a onda N integra (§8).

## 6. Retomada entre janelas e limite de 5 h

- **Ledger** `.construcao/ledger.jsonl` append-only: `{seq, ts, ator, evento, de, para, task, chave, payload_hash,
  prev, hash}`, `hash = sha256(prev + json canônico)`. `state.json` é cache do fold; divergiu, o ledger vence
  (AC-02 não se repete: status nunca lê o cache). Gravação por temporário + `rename` atômico.
- **Write-ahead**: `lote despachar` grava DESPACHADA **antes** da chamada `Agent`; `lote retornar` grava RETORNOU.
  Na retomada, DESPACHADA sem RETORNOU = em voo perdido: `retomar` inspeciona worktree/branch pela chave; há
  resultado ⇒ colhe; não há ⇒ re-despacha com tentativa+1. Task ACEITA com `hash_entradas` igual não reabre.
- **RETOMAR.md gerado pelo script** a cada `ev` (o LLM lê, não edita): obra, estado e `retorno`, portões pendentes
  com o `aprovar-*.sh`, contrato e oráculo (hash + como rodar), critério de parada, orçamento gasto, tasks em voo,
  fora do escopo e **o próximo comando único**. Notas narrativas entram por `co.py ev nota --texto` (ficam no ledger).
- **5 h**: `janela_inicio` gravado no 1º evento da janela; em 2,5 h ⇒ `janela_50` → AGUARDANDO_HUMANO(`continuar`);
  429/limite ⇒ `limite_uso` → PAUSADO com `retomar_apos` (parede, não erro: sem backoff em rajada). Proxies de
  orçamento: rodadas, horas de parede, subagentes despachados, execuções de eval (uma por vez). 1 rodada por janela.

## 7. Conflitos entre os documentos e a escolha

| # | Conflito | Escolha | Porquê |
|---|---|---|---|
| 1 | 8 etapas com `load/done` (v1) × máquina de eventos (loops) | etapas viram estados; `done` vira `ev`; `load` fica | uma fonte de transição; invariantes checáveis por BFS |
| 2 | `co.py` fino (v1) × 7 + 15 + 9 scripts | 1 CLI + 4 módulos; campanha delegada a `ac.py` | sem sobreposição; G12 confere uma superfície só |
| 3 | `aprovar-*.sh` (v1) × token no terminal (loops) × `approve.py` + hook (gates) | `.sh` gerado + hook + tty/desafio + audit | token mostrado num terminal que o agente lê não prova nada; o canal é o que segura |
| 4 | `oraculo/` legível no workspace (v1) × gabarito oculto (evals) | dev set visível; held-out em `oraculo/heldout/` bloqueado a construtor e injetado só na cópia limpa | METR: hack 43× mais comum vendo o score; construtor ainda precisa saber o que fazer |
| 5 | G0–G12 (gates) × G1–G9 (evals) × 10 itens (v1) | numeração única G0–G14 | um relatório, um veredito |
| 6 | Portão de 10 itens só como placar (iter5) | `regressao.json5` com cmd por item + `gate-report.json` | o v1 já exigia; reforçado por selftest |
| 7 | `RETOMADA.md` escrita pelo LLM e validada (v1) × `RETOMAR.md` gerado (loops) | gerado; narrativa via `ev nota` | texto do LLM sobre o próprio estado deriva |
| 8 | 3 tentativas/2 rejeições (loops) × 2 rodadas sem progresso (v1) × máx. 2 rodadas (perguntas) | task: 3 tentativas, mesma rejeição 2× ⇒ REPLANEJAR; obra: `max_rodadas` 3, platô 2 ⇒ escalar | níveis diferentes, contadores diferentes; platô cobre "sem progresso" |
| 9 | BASELINE obrigatório (loops) × dispensável (v1) | estado obrigatório; evento `dispensado` só se tipo ∉ {skill, agente} com motivo | requisito novo não tem comparável (campanhas 5–8) |
| 10 | Oráculo N+1 só congela após N aceita (loops) × B corrige se disjunto (v1) | congela cedo só se colisão vazia **e** contrato intacto | mantém o ganho de L17 sem congelar contra contrato que muda |
| 11 | 1 execução por eval (v1) × k ≥ 3 pass^k (evals) | k=1 nas rodadas intermediárias rotulado "indício"; pass^3 só no aceite final | cabe nas 5 h sem vender ruído como melhora |
| 12 | `ledger.jsonl` (v1/loops) × `ledger.py` tp/fp (orquestrar) | nomes mantidos, papéis distintos documentados | evitar que alguém rotule eventos como achados |
| 13 | `ac.py gate --by` texto livre (AC-04) × v1 usando portões do `ac.py` | o mesmo hook cobre `ac.py` e `co.py` | brecha real confirmada em ac.py:679/685 |
| 14 | Self-refine/monitor como laço (loops/evals) | monitor só veta; feedback do laço = dev tests + falhas do G13 | otimizar contra monitor ensina ofuscação |
| 15 | "orquestrador pode escrever oráculo" (v1 §12) × "quem testa ≠ quem constrói" | permitido só se o orquestrador não constrói nada daquela frente; MANIFEST registra autor | caso real (vivacidade na iter5) sem abrir exceção silenciosa |

Defeitos AC que a skill não repete: AC-01 (check satisfeito por evento anterior) ⇒ guardas de ordem por `seq` do
ledger; AC-02 (status ≠ estado) ⇒ status é o fold; AC-03 (totais de [Q] trocados) ⇒ `comparar` recusa; AC-04
(aprovação forjável) ⇒ §4.

## 8. Plano de construção da própria skill (bootstrap)

Enquanto `co.py` não existe, o método roda sobre o que já existe: uma campanha `ac.py --work
<ws>/campanhas/construcao` em modo `requisito` (oráculo, freeze, `plan check`, `front report`) +
`orquestrar-subagentes` (verificador cego, `synthesize.py`). A partir da onda 2 a skill se hospeda: o ledger de
`co_estado.py` passa a registrar as próprias ondas. Regra fixa: **o autor do oráculo de X nunca constrói X**; um
agente-oráculo por onda (tipo com Write, sem a tarefa de implementação) escreve os testes da onda N+1 enquanto a
onda N integra; os mutantes semânticos de G5 vêm de um terceiro agente.

| Onda | Frentes (writes disjuntos, ≤3 em paralelo) | Oráculo escrito por | Fecha quando |
|---|---|---|---|
| 0 (serial) | orquestrador: contrato de nomes (`co.py` argparse com todos os subcomandos devolvendo 2 "pendente"), `references/maquina.json5`, `portao.json5`, `formatos.json5`; **campanha prévia ac.py v0.3** (AC-01..03 + L17 em `licoes.json5`) se o founder aprovar | agente-oráculo O1 (testes da onda 1) | `oracle:requisito` aprovado no terminal; oráculo vermelho; `maquina check` do JSON passa pelo protótipo do O1 |
| 1 | A `co_estado.py` (ev, ledger, fold, maquina check, retomar, RETOMAR.md) · B `co_hook.py` (+ `aprovar`, selftest estático/vivo, trecho de settings) · C `co_portao.py` núcleo (G0, G1, G3, G4, G7, `veredito` chamando `synthesize.py`) | O1 | G0/G1/G3/G4 verdes; `hook selftest` 100%; verificador cego confirma "aprovação bloqueada para subagente e principal" |
| 2 | D `co_medir.py` (cópia limpa, k, pass^k, `comparar` IC, `oraculo vacuo/forca`) · E `co.py` plano/lote/colisao/trava (DAG, write-ahead, teto 3) · F `SKILL.md` + `references/*.md` (só explica; cita só nomes do contrato) | O2 (escrito durante a integração da onda 1) | G5 com mutantes do agente M; G12 docs↔CLI; G2 em 3.9/3.13 |
| 3 (serial) | integração final + G6/G8/G9/G10 do próprio `co.py` (a skill é alvo `harness` de si mesma) | O3 | portão completo GO sem waiver nos [S]; `maquina check` da máquina do processo |
| Prova | **obra 1 = eval 2 `jsonl-diff`** (barata, sem repo do founder, exercita requisito sem baseline, 2 runtimes, memória, exit code); depois eval 1 `changelog-pt` (exercita baseline skill-creator e pass^3); eval 3 `loja-api` só após conferir que o repo existe | evals do `evals-propostos.json` como held-out, gabarito por agente ≠ construtor | eval 2: ENTREGUE com 0 contornos manuais, RETOMAR.md retomado numa janela nova pelo menos uma vez, 0 aprovações fora do terminal no audit |

Ordem interna justificada: A antes de E (lote depende do ledger) — por isso E está na onda 2; B e C não dependem de
A além do contrato da onda 0. Cada frente reporta `files_changed`, testes vermelho→verde e nível de evidência; o
orquestrador re-executa toda evidência E2.

## 9. Decisões que só o founder toma (com recomendação)

1. **Hook global de aprovação** em `~/.claude/settings.json`, cobrindo `co.py` **e** `ac.py` (fecha AC-04), com o
   limite honesto do §4 aceito por escrito. *Recomendo: sim, agora; assinatura gpg/PR review fica para v2.*
2. **Editar a `auto-correcao` antes do bootstrap** (v0.3: AC-01..03 + L17 em `licoes.json5`), como campanha prévia na
   onda 0. *Recomendo: sim — o `co.py` delega o laço ao `ac.py` e herdaria os defeitos; trava de integração e
   `colisao` ficam no `co.py` (a auto-correcao continua sabendo de uma campanha só).*
3. **Teto de paralelismo**: 3 subagentes vivos no total, ≤2 campanhas, sobreposição só com colisão vazia e contrato
   intacto, integração serial. *Recomendo: sim (L06 e 5 h); rever após a obra 1 com custo medido.*
4. **Rigor de medição × orçamento**: baseline obrigatório para skill/agente e dispensável com motivo nos demais;
   k=1 "indício" nas rodadas, pass^3 + IC pareado só no aceite final; held-out oculto do construtor.
   *Recomendo: sim; muda o v1 (que media 1 vez) por causa da conta de ruído (n=20 ⇒ ±0,20).*
5. **Ritmo e autonomia na janela de 5 h**: 1 rodada por janela, pergunta em 50%, `max_rodadas` 3 (platô 2 ⇒
   escalar), sem `preauth continue`; primeira obra de prova = `jsonl-diff`. *Recomendo: sim; `preauth continue` até
   80% só depois que a obra 1 provar que o checkpoint retoma limpo.*
