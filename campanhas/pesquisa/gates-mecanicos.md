# Gates mecânicos e testes mecânicos de regressão

Pesquisa para a skill `construcao-orquestrada` (2026-10-04). Tema: **tudo que um script decide em vez do modelo**.
Princípio herdado de um harness anterior (v8): *Markdown explica. JSON decide. Hook bloqueia. Log prova. Verificar não é fazer.*
Fontes: leitura local (ac.py, synthesize.py, suítes do codebase-specialists) + web (links ao fim de cada seção).

## 1. Por que o gate tem de ser script

O construtor (LLM) e o avaliador (LLM) compartilham o mesmo viés: "rodei, então funcionou". Toda decisão que
pode ser **contada, comparada por hash, parseada ou executada** sai do modelo e vai para um script com exit code.
O modelo fica com o que não é mecanizável (interpretar spec, classificar defeito) — e mesmo isso passa por
um portão humano não forjável quando muda o critério de aceite.

Benchmarks recentes confirmam o risco: agentes de código (Codex, Claude Code, Gemini) passam testes sem resolver a
tarefa — hardcode de saída, edição/deleção de arquivo de teste, edição do runner, até prompt-injection no
verificador. As defesas que funcionam são mecânicas: **testes held-out, detecção de edição de teste, juízes
separados e revisão humana** (EvilGenie); e **testes randomizados com teto conhecido** — passar acima do teto
alcançável é evidência estatística de trapaça (CapCode, ICML 2026).
Fontes: [EvilGenie](https://arxiv.org/abs/2511.21654) · [CapCode](https://arxiv.org/abs/2606.07379) ·
[SpecBench](https://arxiv.org/pdf/2605.21384) · [escalation channels](https://arxiv.org/abs/2608.29460)

## 2. O que a experiência local já provou (com onde está)

| Mecanismo | Onde | O que ensina |
|---|---|---|
| Etapas com `check` executável que prova EFEITO | `auto-correcao/references/ciclo.json5` (cada sub-etapa tem `check:`), `ac.py check/done` | `done` só fecha se o check passa; `require_previous_closed` impede pular etapa. |
| L03 "check prova o efeito" | `licoes.json5` L03 | Check que testa "o subcomando rodou" passa sem a etapa acontecer. **Regra: todo check nasce com um teste em que o subcomando passa e o efeito não acontece.** |
| Oráculo congelado por hash | `ac.py oracle freeze/verify/change` (`sha_files`) | `freeze` recusa 2ª vez; `change` exige `--why` + `--evidence` e registra from→to + rodada; toda medição anterior deve ser recorrigida. `plan check` recusa frente cujo glob sobrepõe arquivos do oráculo. |
| Calibração do oráculo | `chk_calibration` | Saída vazia ≤0,10; saída boa conhecida ≥0,90; ≥2 conferências à mão por config, cada uma com evidência `arq:linha`. L01: "o corretor mente com frequência". |
| Modo requisito (L15) | `chk_calibration_requisito` | Requisito novo não tem "bom conhecido": vazio medido ≈0 (oráculo vermelho antes), cada arquivo de oráculo ligado a seção da spec, portão humano `oracle:requisito` **não simulado**. Testes escritos por agente separado de quem implementa. |
| Estado protegido | `ac.py set` + `PROTECTED` | `gates`, `done`, `oracle.hash`, `preauth`… não se escrevem por `set` genérico, só pelo comando próprio (que valida). |
| Pré-autorização condicional | `cmd_preauth`, `chk_gate_ok` | Humano pré-autoriza um portão (ex. commit) **condicionado** a sub-etapas concluídas (`--requires integracao.1 integracao.2`); nunca incondicional; nunca `--simulated`. |
| Aprovação simulada visível | L13, `gate --simulated` | Veredito traz "GO (simulado)", não nota de rodapé. |
| GO/NO-GO por script | `orquestrar-subagentes/scripts/synthesize.py` | Exit 0=GO, 1=NO-GO, 2=entrada inválida. Dedup por arquivo±3 linhas, vereditos dos verificadores (refuted derruba), FATO/SUSPEITA por nível de evidência E0–E3 × severidade × rigor. |
| Cobertura ancorada | `synthesize.py check_anchor` | Agente declara "li X" com âncora (texto ≥8 chars na linha N±2); só a cobertura cujas âncoras conferem no arquivo conta. Declarado ≠ ancorado — e o relatório mostra os dois. |
| Vivacidade de máquina de estado (L16) | `harness/tests/test_maquinas_vivacidade.py` | Lê `machines.json5` em runtime: estado sem saída tem de estar em `terminal`; estados "aguardando humano" nunca terminais e com saídas retomar/trocar/descartar; todo estado alcançável do inicial. Achado real: 480 testes verdes e ESCALATED trancado. |
| Cobertura de transições e guardas, medida | `test_cobertura_maquinas.py` | Universo lido do JSON (nada de lista fixa); cenários rodam CLI/hook reais em subprocesso num repo git temporário; matriz montada de **evidência** (events.jsonl, observador que só registra qual guarda recusou). Falha se alguma aresta nunca exercitada, guarda nunca vista OK **ou nunca vista RECUSANDO**. Guarda inalcançável por caminho legal é provada por adulteração e vira achado. |
| E2E de workflow | `test_workflow_e2e.py` | Cada caminho termina em `assert_coerente`: validate --strict, nada trancado, `next` responde. "Este arquivo é contrato: quem implementa não o edita." Falha de ambiente simulada (exit 127) separada de falha de asserção (`failure_kind`). |
| Ator vindo do hook | `engine/guard.py` (`agent_id` no payload ⇒ subagente) | `legacy-ack`, `waive-verify` bloqueados se vierem de qualquer tool call de agente: "peça ao usuário que rode no terminal". Subagente sem `agent_type` ⇒ fail-closed. |
| Instalação que escreve fora | `test_install_outside.py` | `--dry-run` lista o bloco `outside` e nada escreve; escrever fora exige `--allow-outside`. |
| Dados legados | `test_legacy_hierarquia.py`, `test_trabalho_na_arvore.py`, `doctests/tests/test_version_migrations.py` | Estado deixado por motor antigo precisa de saída (ack humano) sem esconder incoerência nova; VERSION sem migração cadastrada reprova; validador testado com o caso ruim. |
| Docs ↔ CLI | `doctests/tests/test_commands_parse.py` | Todo comando citado em SKILL.md/references/templates é parseado contra o **argparse real** (subcomando, `choices`, flags por nível). `PENDENTES` com motivo permite a transição enquanto a frente cria o comando; contrato de nomes do plano tem de aparecer na doc e parsear. |
| Múltiplos runtimes (L10) | `licoes.json5` L10, `integracao.1` | Regressões só em Python 3.9 (doctest), pegas porque a integração roda todas as suítes em todas as versões. |
| Precedência de gates | `test_gate_precedence.py` | Qualquer FAIL vence; NEEDS_SPECIALIST roteia. Regra de decisão escrita e testada no caso de borda (L11). |

Lacunas observadas no próprio ac.py: `gate --by` e `preauth --by` recebem o humano **como texto** — um agente
com Bash consegue forjar. A defesa correta é a do codebase-specialists: o guard identifica o ator pelo payload do
hook e bloqueia comando de portão humano vindo de agente (ver §3.6).

## 3. Estado da arte (web), por tema

**3.1 Quality gates em CI.** Gate = job com exit code em branch protegida/ruleset como *required status check*.
Regra prática: o gate falha fechado (ferramenta ausente, relatório vazio, 0 testes coletados = FAIL). Achado
recorrente em issues reais: "mutation testing instala o Stryker em runtime e não tem threshold, então nunca
falha" — gate sem limiar é decoração. [issue Perihelion#768](https://github.com/Perihelion-Protocol/Perihelion/issues/768)

**3.2 "Check prova o efeito".** Equivalente acadêmico/industrial: testar o *observable outcome*, não a chamada.
Padrão: cada check tem par (positivo, negativo) e um **teste de mutação do próprio check** — stub do subcomando que
sai 0 sem produzir o efeito; o check tem de reprovar. Mesma lógica do CapCode: o avaliador precisa ser capaz de
distinguir "fez" de "fingiu".

**3.3 Cobertura de transições.** Model-based testing: o modelo (JSON da máquina) é o universo; cobertura de
estados < cobertura de transições < cobertura de pares de transição; guardas exigem visto-OK **e** visto-recusando.
Somar vivacidade (sem deadlock acidental) e alcançabilidade — ambos são checagens de grafo, baratas.

**3.4 Mutation score como gate.** Stryker `thresholds.break` (exit≠0 abaixo do limiar; configs comuns 50–80);
PIT `mutationThreshold`; modo incremental (Stryker ≥6.2 `--incremental`, PIT `historyInput/OutputLocation`)
re-testa só mutantes cujo código/testes mudaram e o limiar vale sobre o conjunto inteiro. Para código gerado por IA
é o antídoto contra "100% de cobertura que não testa nada"; diff-scoped em PR, completo em main.
[Stryker gate PR](https://github.com/afahy/fluent-measures/pull/15) · [incremental](https://github.com/fderuiter/deruiter.dev/issues/1772) ·
[Augment: mutation p/ código de IA](https://www.augmentcode.com/guides/mutation-testing-ai-generated-code) · [Angular 100% cobertura](https://loiane.com/2026/08/mutation-testing-angular-stryker/)

**3.5 Snapshot/diff de API pública ("nada removido").** api-extractor (TS: `.api.md` versionado, CI falha se
diverge), cargo-semver-checks (Rust), japicmp (Java), oasdiff (OpenAPI, ~755 tipos de mudança classificados por
severidade; quebra sem bump major falha o build). Genérico: extrair superfície (símbolos exportados, subcomandos +
flags, rotas, schema, tabelas/colunas, chaves de config) → JSON ordenado → diff contra baseline: **remoção ou mudança
incompatível = FAIL**, adição = INFO, exceção só por waiver humano.
[oasdiff](https://www.oasdiff.com/) · [OpenAPI diff em CI](https://dev.to/jeff_pdc/detect-breaking-api-changes-in-ci-with-openapi-diffs-before-your-customers-do-18lf) · [NDepend](https://www.ndepend.com/docs/detect-api-breaking-changes)

**3.6 Detecção de edição de teste pelo construtor.** Camadas, da mais forte à mais fraca:
(a) **held-out**: oráculo que o construtor nunca vê (fora do workspace dele) — o mais forte;
(b) **hash congelado** dos arquivos do oráculo verificado no gate (ac.py `oracle verify`);
(c) **hook PreToolUse** bloqueando Write/Edit/Bash em paths protegidos para subagentes (território = `allowed_paths`);
(d) **diff × allowed_paths** pós-execução (git), que pega escrita por caminho indireto (script, `sed`);
(e) CODEOWNERS + ruleset `require_code_owner_review` sobre `tests/`, `.github/workflows/`, `.claude/` — só vale se
a review for obrigatória (falso senso de segurança comum: CODEOWNERS sem ruleset é sugestão; repo de uma pessoa não
consegue auto-aprovar). Contagem de testes/asserções não pode cair (deleção de teste também é edição).
[rulesets](https://blog.stephane-robert.info/en/docs/pipeline-cicd/github/gouvernance/rulesets/) · [CODEOWNERS](https://blog.stephane-robert.info/en/docs/pipeline-cicd/github/gouvernance/codeowners/) · [issue semilla#45](https://github.com/manoochehri/semilla/issues/45)

**3.7 Gates humanos não forjáveis por IA.** O ator vem do **canal**, não do texto. No Claude Code, o payload do hook
traz `agent_id`/`agent_type` só quando a chamada vem de subagente; o agente principal não tem `agent_id`, então
"humano" não é distinguível do principal pelo payload — logo, o comando de aprovação humana é **bloqueado para
qualquer tool call** e só roda digitado pelo usuário no terminal (ou via `!`/fora da sessão), e o registro grava
`tty`/usuário do SO. Alternativas mais fortes: aprovação via PR review do GitHub (identidade do provedor), assinatura
(gpg/ssh) de um arquivo de aprovação com chave fora do alcance do agente. Cuidado reportado: há issue de hooks
Pre/PostToolUse não disparando para subagentes em certas versões — o harness precisa de **selftest** do hook
(payload sintético de subagente tentando escrever em path protegido ⇒ exit 2).
[Hooks reference](https://code.claude.com/docs/en/hooks) · [issue #34692](https://github.com/anthropics/claude-code/issues/34692)

**3.8 Múltiplos runtimes.** Matriz (tox/nox, GitHub Actions `strategy.matrix`) com a **versão mínima declarada** e a
mais nova; doctests e formatação de saída costumam quebrar só na mínima. Gate: todas as células verdes; célula
pulada = FAIL, não "skipped".

**3.9 Instalação limpa.** Construir o artefato (wheel/sdist, `npm pack`, imagem) e instalar num ambiente vazio
(venv novo, container, `HOME` temporário), rodar smoke dos entrypoints. Pega arquivo esquecido no pacote, dependência
implícita do ambiente do dev e path absoluto. Inclui "escreve fora do esperado?" (dry-run listando efeitos externos).

**3.10 Upgrade de dados legados.** Migração testada só em banco vazio é o erro clássico. Padrão: **legacy fixture
pack** por versão publicada (dados determinísticos, IDs/timestamps fixos) → migrar → verificar contagens
preservadas, invariantes, operações CRUD sobre registros migrados, diff de schema zero contra instalação nova; e a
regra "versão nova ⇒ migração cadastrada" (test_version_migrations).
[legacy fixture pack](https://github.com/Obiajulu-gif/eduvault-archive/pull/933) · [snapshot da release anterior](https://github.com/ChalidNL/todoless/issues/39) · [GitLab](https://gitlab.com/gitlab-org/gitlab-foss/-/issues/14549)

**3.11 Docs que não mentem.** Exemplos executáveis: trycmd/cram (rodam o binário real e comparam stdout/stderr/exit
com blocos ```console), mdoctest, doctest, Sphinx/MkDocs falhando o build; "doc-coverage" — doc voltada a agentes
tratada como contrato de capacidade testado. Mais barato e quase tão bom: parse de todo comando citado contra o
parser real (o que `test_commands_parse.py` já faz) + lista PENDENTES com motivo.
[trycmd](https://docs.rs/trycmd) · [mdoctest](https://pypi.org/project/mdoctest/) · [doc-coverage tests](https://zylos.ai/research/2026-08-02-doc-coverage-tests-agent-capability-drift/) · [docs examples em CI](https://dev.to/ingridowusu/test-the-code-examples-in-your-mkdocs-and-sphinx-docs-on-every-build-3emi)

## 4. Anti-padrões que o gate tem de pegar (checklist de "o gate mente?")

1. Gate sem limiar ou que passa com 0 testes coletados / relatório vazio / ferramenta ausente.
2. Check que verifica a execução, não o efeito (L03).
3. Oráculo editável pelo construtor, ou alterado sem registro de por quê + evidência.
4. Teste deletado/skipado/`xfail` novo sem waiver — conta de testes e asserções caiu.
5. Lista fixa de "o que cobrir" no teste (o universo deve vir do artefato real: máquinas, parser, schema).
6. Aprovação humana registrada por texto que o agente digita (`--by humano`).
7. "Skipped" numa célula de runtime contado como verde.
8. Agregado que mistura qualidade comparável com baseline e estrutura própria do sistema (L02).
9. Mesmo estado → vereditos diferentes em alvos diferentes (L11): regra de decisão sem teste de borda.
10. Mudar o sistema enquanto mede (L04) — exige hash do sistema congelado durante a remedição também.

## Recomendações para a skill

### A. Portão de regressão GENÉRICO (`gate.json5` por alvo)

Cada item: `id`, `aplica_a` (tipos de alvo), `cmd` (parametrizável), `limiar`, `falha_fechado: true`, `waiver`
(só humano, via canal não forjável, com motivo e validade). Itens marcados **[sempre]** não têm waiver.

| id | Prova | Parâmetros por tipo de alvo | Limiar padrão |
|---|---|---|---|
| G0 oraculo-intacto **[sempre]** | hash dos arquivos do oráculo = congelado; nº de testes/asserções ≥ baseline | `oracle.files` | igualdade; queda = FAIL |
| G1 suites-verdes **[sempre]** | todas as suítes, ≥1 teste coletado por suíte | `suites[]` (pytest/jest/go test/cargo/…) | 0 falhas, 0 coletas vazias |
| G2 runtimes | G1 em cada célula da matriz | `runtimes[]` (mín. declarado + atual) | todas verdes; skip = FAIL |
| G3 territorio **[sempre]** | diff git × `allowed_paths` da task; nada fora; nada em path protegido | `allowed_paths`, `protected[]` | 0 violações |
| G4 superficie-publica | snapshot da superfície vs baseline: nada removido/incompatível | lib: símbolos exportados · CLI: subcomandos+flags+exit codes · HTTP: OpenAPI · DB: schema · config: chaves | remoção = FAIL; adição = INFO |
| G5 efeito-dos-checks | cada check tem teste negativo (subcomando ok, efeito ausente ⇒ FAIL) | `checks[]` | 100% dos checks com par negativo |
| G6 maquina | vivacidade, alcançabilidade, cobertura de arestas e guardas (OK e RECUSA) | só se o alvo tem `machines`/workflow | 100% arestas; 100% guardas OK+RECUSA ou achado registrado |
| G7 e2e | caminhos de ponta a ponta terminam coerentes (nada trancado) | `e2e.paths[]` | todos |
| G8 mutacao | mutation score nos arquivos tocados (incremental) | stryker/pit/mutmut/cargo-mutants | ≥ baseline e ≥ `break` (ex. 60) |
| G9 instalacao-limpa | build do artefato + instalação em ambiente vazio + smoke; dry-run lista efeitos fora | pacote/imagem/skill/harness | smoke verde; escrita externa só com flag |
| G10 upgrade-legado | fixture de cada versão publicada migra para a atual com invariantes preservados; VERSION ⇒ migração | só se há dados/estado persistido | todas as versões |
| G11 docs-verdadeiras | todo comando/flag/exemplo citado parseia (ou executa) contra a implementação real | `docs_globs`, `parser` | 0 divergências (PENDENTES com motivo) |
| G12 baseline | métrica de qualidade ≥ baseline sem o sistema e ≥ rodada anterior; custo ao lado | do ciclo de medição | sem regressão; delta reportado em 2 colunas |

Decisão: `GO` só se todos os itens aplicáveis passam; itens não aplicáveis aparecem como `N/A (motivo)`;
qualquer waiver ou aprovação simulada vira `GO (com waiver)`/`GO (simulado)` no próprio veredito.

### B. Scripts a escrever (stdlib Python, sem rede, saída JSON + humana)

Convenção de exit: **0 = passa/GO · 1 = reprova/NO-GO · 2 = entrada inválida/ferramenta ausente (falha fechado)**.

| Script / subcomando | Entrada | Saída | Exit |
|---|---|---|---|
| `gate.py run --target <dir> --gate gate.json5 [--only G1,G4] [--json]` | gate.json5 + estado | `gate-report.json` (item, status, evidência, comando, duração) + resumo | 0/1/2 |
| `gate.py selftest --gate gate.json5` | gate.json5 | para cada item, roda o caso negativo semeado (teste removido, arquivo fora, símbolo apagado…) e confirma que o item reprova | 0 se todo item reprova seu negativo |
| `oracle.py freeze --file … / verify / change --why --evidence` | arquivos do oráculo | hash + contagem de testes/asserções no estado; log de mudança | verify: 0 intacto, 1 mudou |
| `oracle.py calibrate --empty <cmd> --good <cmd> [--mode requisito --spec map.json]` | comandos de oráculo | pontuações vazio/bom, conferências exigidas | 0 calibrado, 1 não |
| `territory.py check --base <sha> --allowed <globs> --protected <globs>` | git diff | arquivos fora/protegidos tocados (inclui deleções e renomeações) | 0/1 |
| `surface.py snapshot --kind lib\|cli\|http\|db\|config --out s.json` | código/parser/OpenAPI/schema | superfície normalizada e ordenada | 0/2 |
| `surface.py diff --base s0.json --head s1.json [--allow waivers.json]` | dois snapshots | removidos/incompatíveis/adicionados | 0 nada removido, 1 quebra |
| `machine.py check --machines m.json5 --events events.jsonl` | modelo + log de eventos | vivacidade, alcançabilidade, matriz arestas/guardas (OK/RECUSA) | 0 100%, 1 lacuna |
| `checkproof.py --check "<cmd>" --stub "<subcomando sem efeito>"` | check + stub | confirma que o check reprova quando o efeito falta | 0 check honesto, 1 check mente |
| `runtimes.py matrix --runtimes 3.9,3.13 --cmd "<suite>"` | lista de interpretadores | célula × resultado; ausente = FAIL | 0/1/2 |
| `install_clean.py --build "<cmd>" --install "<cmd>" --smoke "<cmd>"` | comandos | log em ambiente temporário + lista de escritas fora | 0/1 |
| `legacy.py upgrade --fixtures fixtures/legacy/ --migrate "<cmd>" --invariants inv.json` | fixtures por versão | por versão: contagens, invariantes, diff de schema | 0/1 |
| `doccheck.py --docs "<globs>" --parser module:build_parser [--pending p.json]` | docs + parser real | ocorrências inválidas (subcomando, choice, flag) | 0/1 |
| `approve.py <portao> --decision approve\|reject --note` | **só terminal humano**; hook bloqueia de qualquer tool call (exit 2) | registro com usuário do SO, tty, timestamp, hash do estado aprovado | 0/1 |
| `verdict.py --report gate-report.json --state st.json` | relatórios | GO / GO (com waiver) / GO (simulado) / NO-GO + razões (estilo synthesize.py) | 0 GO, 1 NO-GO |

Ordem de construção sugerida: `oracle.py` + `territory.py` + `verdict.py` (mínimo viável, cobre G0/G1/G3) →
`approve.py` com hook e selftest → `gate.py selftest` → `surface.py`/`doccheck.py` → `machine.py`, `legacy.py`,
mutação e runtimes conforme o tipo de alvo. Cada script nasce com seu próprio teste negativo (L03).
