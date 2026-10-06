# Loops e grafos — pesquisa para a skill `construcao-orquestrada`

Filtro: o que um orquestrador Claude Code usa de fato (`Agent`, subagentes isolados, worktrees,
JSON no disco, Python stdlib). 2026-10-04. **[F]** fonte primária, **[S]** secundária, **[J]** julgamento.

## 1. Padrões de laço: o que cada um é, onde diverge, onde trava

| Padrão | Núcleo | Diverge/trava quando | Serve ao orquestrador? |
|---|---|---|---|
| Orchestrator-workers | LLM central quebra a tarefa dinamicamente e delega a workers; sintetiza | subtarefas mal delimitadas → trabalho duplicado, lacunas | **Sim, é o esqueleto** |
| Evaluator-optimizer | gerador produz, avaliador critica em laço até o critério | avaliador "generoso" (aprova mediocridade) ou critério vago → laço infinito | Sim, como laço de autocorreção com avaliador **separado** |
| Plan-execute-verify | plano explícito → execução → verificação por sinal externo | plano congelado cedo demais; verificação só no fim | Sim, por campanha |
| Ralph loop | `while :; do cat PROMPT.md \| claude; done`, contexto zerado a cada volta, progresso só em arquivos/git | sem critério de parada; reescreve o que já estava bom; caro | Parcial: copiar a **disciplina de disco**, não o laço cego |
| Reflexion | agente escreve reflexão verbal sobre a falha numa memória episódica e tenta de novo | sem sinal externo de falha, a reflexão vira racionalização | Parcial: "lições" persistidas por campanha |
| Self-refine | o mesmo modelo critica e reescreve a própria saída | autocorreção intrínseca sem feedback externo frequentemente **piora** | Não como gate; só como polimento local |
| Critic loop / LLM-as-judge | um segundo agente pontua por rubrica | juiz não calibrado deriva; viés de concordância | Sim, se calibrado com exemplos e rubrica fixa |

Fontes:
- Anthropic, *Building effective agents* — workflows (prompt chaining, routing, parallelization,
  orchestrator-workers, evaluator-optimizer) vs. agentes; "comece simples":
  https://www.anthropic.com/research/building-effective-agents **[F]**
- Anthropic, *How we built our multi-agent research system* — lead + subagentes paralelos; sem
  brief detalhado (objetivo, formato, ferramentas, fronteiras) duplicam e deixam lacunas; tokens
  explicam ~80% da variância; ~15x tokens de um chat: https://www.anthropic.com/engineering/multi-agent-research-system **[F]**
- Anthropic, *Effective harnesses for long-running agents* — agente inicializador cria `init.sh`,
  `claude-progress.txt`, `feature_list.json` e commit inicial; agente de código lê progresso + git
  log, faz **uma feature por sessão**, commita, atualiza o progresso:
  https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents **[F]**
- Anthropic, *Harness design for long-running application development* — planner → generator →
  evaluator; **sprint contract** negociado antes do código ("como saberemos que está pronto");
  avaliador calibrado com few-shot porque agentes elogiam o próprio trabalho medíocre; *context
  reset* com handoff estruturado venceu compaction para um modelo com "ansiedade de contexto";
  "todo componente do harness codifica uma premissa sobre o que o modelo não faz sozinho" e
  componentes caem quando o modelo melhora:
  https://www.anthropic.com/engineering/harness-design-long-running-apps **[F]**
- Ralph: https://github.com/ghuntley/how-to-ralph-wiggum ; crítica (sem parada/verificação): https://xr0am.substack.com/p/what-ralph-wiggum-loops-are-missing **[F/S]**
- Reflexion https://arxiv.org/abs/2303.11366 ; Self-Refine https://arxiv.org/abs/2303.17651 ;
  *LLMs Cannot Self-Correct Reasoning Yet* (ICLR'24) https://arxiv.org/abs/2310.01798 **[F]**
- MAST, *Why Do Multi-Agent LLM Systems Fail?* — 14 modos em 3 classes: design do sistema (44,2%),
  desalinhamento entre agentes, **verificação de tarefa (23,5%)**; checagem só no estágio final e de
  baixo nível é insuficiente: https://arxiv.org/abs/2503.13657 **[F]**

Julgamento **[J]**:
1. O único laço que converge de forma confiável é o que fecha sobre **sinal externo executável**
   (teste, oráculo, medição). Self-refine e reflexion sem sinal externo são decoração. Por isso o
   "oráculo antes do código" não é preferência: é o que transforma evaluator-optimizer em laço
   convergente.
2. Ralph prova uma coisa útil: **contexto descartável + estado no disco** escala além de uma janela.
   O que ele não tem — e a skill precisa ter — é guarda de parada, orçamento e proibição de
   reescrever trabalho aceito.
3. Avaliador nunca é o autor. MAST e o post de harness design convergem: o gargalo é verificação.

### Critérios de parada e orçamento (para qualquer laço)
Pare (em ordem de prioridade) quando: (a) oráculo verde **e** medição ≥ baseline; (b) orçamento de
tentativas esgotado (recomendo 3 por item; 2 rejeições pelo mesmo critério → escalar a
re-planejamento, não tentar a 3ª igual); (c) **sem progresso**: a métrica não melhorou em 2 voltas
consecutivas (detecção de platô); (d) **oscilação**: o hash do diff/da saída repetiu um estado já
visto (ciclo A→B→A); (e) orçamento de tokens/tempo da janela esgotado → checkpoint e sair limpo.
Tudo isso é mecânico e deve ser script, não julgamento do LLM. **[J]**

## 2. Grafos e máquinas de estado: o que copiar sem o framework

- **LangGraph**: grafo de nós sobre um estado tipado; *checkpointer* salva snapshot a cada
  super-step por `thread_id`; `interrupt()` pausa indefinidamente e retoma com `Command(resume=...)`;
  "time travel" a partir de checkpoints antigos. Docs:
  https://docs.langchain.com/oss/python/langgraph/checkpointers ,
  https://docs.langchain.com/oss/python/langgraph/interrupts **[F]**
  Copiar: (1) estado único serializável; (2) snapshot após **cada** transição; (3) interrupt como
  estado explícito `AWAITING_HUMAN` com payload do que se pede; (4) retomada por id. Não copiar: o
  runtime Python, o modelo de execução de nós — no Claude Code quem "executa o nó" é o próprio LLM
  orquestrador lendo o JSON. **[J]**
- **DAG de tarefas** (Make, Airflow, Bazel): nós com `depends_on`, ordenação topológica, execução
  da "fronteira" pronta, cache por hash de entrada. Copiar: `tasks.json` com `depends_on` +
  `writes` (arquivos) e um script que calcula a fronteira pronta e particiona em lotes. Bazel/Make
  ensinam **incrementalidade por hash**: se as entradas de um nó não mudaram, não reexecuta. **[J]**
- **Temporal / durable execution**: o workflow é código determinístico reconstruído por *replay*
  de um histórico de eventos durável; efeitos externos vão para *activities* cujo resultado é
  gravado uma vez e relido no replay; activities podem rodar mais de uma vez → **idempotência é
  requisito**, com chave estável (workflow id + activity id). https://docs.temporal.io/workflows ,
  https://docs.temporal.io/activities **[F]** Copiar: o *event log* como fonte da verdade (estado =
  fold dos eventos), chave de idempotência por task (`campanha/task/tentativa`), e a regra "efeito
  colateral só dentro de uma activity registrada". Não copiar: servidor, workers, SDK. **[J]**
- **Statecharts** (Harel, 1987; https://statecharts.dev ; XState https://stately.ai/docs): estados
  hierárquicos, guardas em transições, estados finais, histórico. Copiar: **tabela de transições
  declarativa** `{de, evento, para, guarda}` em JSON, validada por script; estados aninhados só
  dois níveis (processo → campanha → task). Guardas como predicados nomeados implementados em
  Python, não texto livre. **[J]**
- **Model checking** (TLA+/Petri): checar invariantes da máquina (§5) por BFS em Python puro. **[J]**

## 3. Paralelismo seguro

- Claude Code: `isolation: worktree` dá ao subagente worktree temporária (limpa se nada mudou; senão
  devolve path+branch). https://code.claude.com/docs/en/worktrees , .../sub-agents **[F]**
- **Partição por arquivos disjuntos** é a regra de ouro **[J]**: cada task declara `writes`
  (globs). O script de lote só agrupa tasks cujos `writes` têm interseção vazia, e cujo `reads` não
  inclui o `writes` de outra do mesmo lote (evita ler estado meio-escrito). Com interseção vazia,
  worktree vira rede de segurança, não mecanismo de merge — merges sem conflito por construção.
- **Contrato de interface antes das frentes**: uma task-zero (sequencial) congela tipos,
  assinaturas, schemas e o oráculo; só depois as frentes paralelas. Isto é o *sprint contract* do
  post de harness design aplicado a interfaces. Mudança de contrato no meio = evento que invalida
  o lote e volta a PLANEJAR. **[J]**
- **Integração** é um estado próprio, sequencial, feito pelo orquestrador (ou um integrador):
  merge das worktrees em ordem determinística (por id), rodar oráculo completo após **cada** merge
  para localizar a quebra (bisect barato). **[J]**
- **Limite ≤3 por lote** **[J]**: conciliação de resultados é o custo dominante do orquestrador
  (cada retorno ocupa contexto dele); o post multiagente mostra custo ~15x em tokens; e o limite de
  uso de 5h é compartilhado por todos os subagentes. 3 é um teto empírico razoável; o script deve
  impor, não sugerir.
- **Pipelining**: enquanto a campanha N está em INTEGRAR (trabalho do orquestrador + scripts),
  um subagente read-only pode preparar o oráculo da campanha N+1 — escreve só em
  `oraculos/N+1/**`, disjunto por construção. Guarda: o oráculo N+1 só é **congelado** depois que N
  é aceita (porque N pode mudar o contrato). **[J]**
- **Rate-limit**: tratar 429/limite de uso como evento `RATE_LIMITED` → checkpoint imediato e
  estado `PAUSADO` com `retomar_apos`; nunca re-despachar em rajada. Backoff exponencial com jitter
  só vale para erro transitório; limite de janela de 5h é parede, não erro. **[J]**

## 4. Checkpoint e retomada entre janelas

Princípio (Anthropic long-running + Temporal + Ralph): **a conversa é descartável; o disco é a
memória**. Qualquer janela nova deve conseguir, só lendo arquivos, saber: onde estamos, o que está
em voo, o que já foi aceito, qual o próximo passo único. **[F/J]**

- **Ledger append-only com hash encadeado** (ideia de logs de transparência, RFC 6962
  https://www.rfc-editor.org/rfc/rfc6962 , e de event sourcing
  https://martinfowler.com/eaaDev/EventSourcing.html) **[F]**: `ledger.jsonl`, uma linha por evento
  `{seq, ts, evento, task, de, para, payload_hash, prev_hash, hash}` com
  `hash = sha256(prev_hash + json canônico)`. O estado atual (`estado.json`) é um **cache**
  derivável pelo fold do ledger; se divergirem, o ledger vence. Detecta edição manual/truncamento.
- **Write-ahead**: registrar `DESPACHADA(task, tentativa, chave)` **antes** de chamar `Agent`;
  registrar `RETORNOU` depois. Na retomada, task com DESPACHADA sem RETORNOU = "em voo perdido":
  inspecionar worktree/branch pela chave; se houver resultado, colher; senão re-despachar com
  tentativa+1. Isso evita duplicata e evita perda. **[J]**
- **Idempotência**: chave `campanha/task/tentativa` nomeia branch/worktree; passo registrado =
  no-op; estado gravado via temporário + `rename` atômico. **[J]**
- **Anti-retrabalho**: task aceita guarda `hash_entradas` (hash dos arquivos lidos + contrato +
  oráculo). Retomada só reabre se o hash mudou (incrementalidade estilo Bazel). **[J]**
- `RETOMAR.md` é **gerado pelo script** (estado, tasks em voo, próximo comando exato); o LLM lê, não edita.
- **Checkpoint** após cada transição e antes de todo despacho; não existe "salvar no fim". **[J]**

## 5. Invariantes estruturais da máquina do processo

Verificáveis por script com BFS sobre a tabela de transições (sem LLM) **[J]**:
1. **Alcançabilidade**: todo estado é alcançável a partir de `INICIO`; nenhum estado órfão.
2. **Vivacidade (sem beco)**: de todo estado não-final existe caminho até um final
   (`ENTREGUE` ou `ABANDONADO`). Estados de espera (`AGUARDANDO_HUMANO`, `PAUSADO`) têm saída.
3. **Sem atalho para aceito**: todo caminho até `ACEITA` passa por `VERIFICANDO` e por guarda
   `oraculo_verde ∧ medicao>=baseline ∧ verificador!=autor`. Checar removendo `VERIFICANDO` do
   grafo: `ACEITA` deve ficar inalcançável.
4. **Laços com limite**: todo ciclo do grafo contém uma transição que incrementa um contador com
   teto (tentativas, voltas sem progresso); ciclo sem contador = possível laço infinito → erro.
5. **Determinismo**: para cada `(estado, evento)` no máximo uma transição com guarda verdadeira
   (guardas mutuamente exclusivas, testadas por tabela-verdade nos predicados).
6. **Gates humanos não simuláveis**: transições marcadas `ator: humano` só aceitam evento
   carregando prova fora do alcance do LLM — p.ex. arquivo `aprovacoes/<id>.ok` cujo conteúdo é um
   token gerado pelo script e **mostrado ao humano** só no terminal, ou edição feita pelo humano
   com hook bloqueando escrita do agente nesse path. Honestidade: num ambiente onde o agente tem
   shell sem restrição, nenhum gate é criptograficamente impossível de forjar; o que se consegue é
   (a) hook que bloqueia a escrita, (b) ledger que registra quem/como, (c) forjar exigir ato
   deliberado e visível. Documentar isso como premissa, não prometer o impossível.
7. **Monotonicidade do aceito**: `ACEITA → *` só via evento explícito `REABRIR` com motivo
   (mudança de contrato/hash de entrada), nunca silencioso.

## 6. Anti-padrões a proibir
Estado em Markdown editado pelo LLM; "verificar" = ler diff (MAST: verificar é executar);
paralelizar antes do contrato; laço sem detector de oscilação; subagente chamando subagente;
compaction como memória (preferir reset + disco); guarda "eterna" sem premissa registrada.

## Recomendações para a skill

### Máquina de estado proposta (nível processo/campanha)

Estados: `INICIO → ENTENDER → CONTRATO → ORACULO → BASELINE → PLANEJAR_LOTE → DESPACHADO →
INTEGRAR → VERIFICAR → (CORRIGIR ↺) → ACEITA_CAMPANHA → [próxima campanha | ENTREGUE]`, mais
transversais `AGUARDANDO_HUMANO`, `PAUSADO`, `REPLANEJAR`, `ABANDONADO`.

| De | Evento | Para | Guarda (predicado em script) |
|---|---|---|---|
| INICIO | iniciar | ENTENDER | `objetivo.json` existe |
| ENTENDER | escopo_ok | AGUARDANDO_HUMANO | sempre (gate humano de escopo) |
| AGUARDANDO_HUMANO | aprovado | (estado anotado em `retorno`) | `aprovacao_valida(id)` (token humano) |
| CONTRATO | contrato_congelado | ORACULO | schema de interfaces válido; `contrato_hash` gravado |
| ORACULO | oraculo_pronto | BASELINE | oráculo executa e **falha** no código atual (vermelho prova que mede algo) |
| BASELINE | medido | PLANEJAR_LOTE | `baseline.json` com métricas e comando reprodutível |
| PLANEJAR_LOTE | lote_ok | DESPACHADO | `len(lote)<=3 ∧ writes disjuntos ∧ deps satisfeitas ∧ orçamento>0` |
| PLANEJAR_LOTE | fronteira_vazia ∧ tudo_aceito | VERIFICAR | — |
| DESPACHADO | todos_retornaram | INTEGRAR | cada task tem `RETORNOU` no ledger |
| DESPACHADO | limite_uso | PAUSADO | grava `retomar_apos` |
| INTEGRAR | merge_ok | VERIFICAR | merges sem conflito; arquivos tocados ⊆ `writes` declarados |
| INTEGRAR | violou_territorio | CORRIGIR | diff fora de `writes` |
| VERIFICAR | verde | ACEITA_CAMPANHA | `oraculo_verde ∧ medicao>=baseline ∧ verificador!=autor` |
| VERIFICAR | vermelho | CORRIGIR | `tentativas < 3` |
| VERIFICAR | vermelho | REPLANEJAR | `tentativas>=3 ∨ mesma_rejeicao_2x ∨ platô_2 ∨ oscilação` |
| CORRIGIR | correcao_pronta | PLANEJAR_LOTE | incrementa `tentativas` |
| REPLANEJAR | novo_plano | CONTRATO | invalida aceites com `hash_entradas` alterado |
| REPLANEJAR | desistir | AGUARDANDO_HUMANO | sempre (humano decide abandonar) |
| ACEITA_CAMPANHA | proxima | ORACULO | há campanha pendente (oráculo N+1 pode já estar em rascunho) |
| ACEITA_CAMPANHA | fim | AGUARDANDO_HUMANO → ENTREGUE | gate humano final |
| PAUSADO | retomar | (estado salvo) | `agora >= retomar_apos` |

Nível task (dentro de DESPACHADO): `PENDENTE → PRONTA → EM_VOO → RETORNADA → ACEITA | REJEITADA`
(`REJEITADA → PRONTA` com tentativa+1 até teto). `ACEITA → PRONTA` só via `REABRIR`.

### O que vira script (Python stdlib, sem dependência)

1. `estado.py` — única porta de escrita: `transicionar(evento, payload)` lê a tabela
   `maquina.json`, avalia a guarda, faz append no `ledger.jsonl` (hash encadeado), reescreve
   `estado.json` atomicamente e regenera `RETOMAR.md`. Recusa transição inválida com código ≠0.
2. `checar_maquina.py` — valida `maquina.json`: alcançabilidade, vivacidade, sem atalho para
   aceito, ciclos com contador, determinismo das guardas (§5). Roda no início de toda sessão.
3. `lote.py` — calcula fronteira pronta do DAG (`tasks.json`), particiona em lotes ≤3 com `writes`
   disjuntos, emite os briefs; registra `DESPACHADA` write-ahead.
4. `retomar.py` — fold do ledger, verifica cadeia de hash, detecta tasks em voo perdidas, inspeciona
   worktrees/branches pela chave e imprime **o próximo passo único**.
5. `medir.py` — roda oráculo + métricas, compara com `baseline.json`, grava resultado com hash do
   código medido; detecta platô e oscilação (hash de saída repetido).
6. `territorio.py` — compara arquivos alterados por task com `writes` declarados (diff de worktree).
7. `aprovar.py` — gera token de gate humano exibido só no terminal; hook bloqueia escrita do agente
   em `aprovacoes/**`.

O LLM decide o **conteúdo** (contrato, oráculo, briefs, correções); o script decide a **transição**.
