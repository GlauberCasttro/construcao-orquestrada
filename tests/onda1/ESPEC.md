# Oráculo da onda 1 — ESPEC (agente-oráculo O1)

Fonte: `references/{contrato,maquina,portoes,invariantes,ondas,formatos}.json5`, `DESENHO-v2.md`,
`DECISOES-FOUNDER.md`. Nomes seguidos à letra do contrato. Testes: `unittest` puro, Python 3.9+, stdlib, tudo em
`tempfile`. Rodar: `python3 -m unittest discover -s tests/onda1 -t tests/onda1`.
Existe também um held-out que o construtor não vê. O integrador roda esse conjunto, que inclui variações de
G3/G4, de bypass do hook e de adulteração do ledger.

Isolamento: `HOME` vira um diretório temporário com `.claude/skills` como link simbólico para as skills reais.
Assim `~/.claude/skills/...` continua resolvendo e o audit (`~/.claude/construcao-orquestrada/audit.jsonl`) vai
parar no temporário. Nenhuma variável de ambiente nova foi criada.

## Requisito → testes

| Requisito (contrato) | Testes visíveis |
|---|---|
| `init`: obra.json5, pontos.json5, gênese (`prev "0"`, `payload_hash`, hash da regra), contrato/maquina_hash | `TestInit.test_init_cria_obra_pontos_e_genese_no_formato` |
| `init`: workspace dentro do alvo ⇒ 2, nada criado; tipo inválido ⇒ 2; reinit não reescreve o ledger | `TestInit.*` |
| Ledger append-only encadeado (formatos.ledger.hash), campos exatos, ts ISO | `TestLedgerEFold.test_cada_ev_estende_a_cadeia_pela_regra_de_formatos` |
| Estado = fold do ledger; o ledger vence o cache; `status --json` com os campos de `estado_cache`; hash_estado D8 | `TestLedgerEFold.*` |
| `nota` não muda estado nem hash_estado (D8) | `test_nota_nao_muda_estado_nem_hash_estado` |
| Guarda falsa ⇒ 1 e ledger idêntico byte a byte | `test_iniciar_sem_hook_vivo_sai_1_...`, `test_novo_plano_no_teto_sai_1_...`, `test_retomar_antes_do_prazo_sai_1_...` |
| I6/D9: `ev aprovado|rejeitado|abandonar` ⇒ 2 | `test_transicao_humana_via_ev_sai_2_D9_I6` |
| Evento inexistente ⇒ 2; evento que não sai do estado ⇒ não grava | `TestEvGuardas.*` |
| Contadores com teto: tentativas (vermelho, campanhas_abertas), replanejamentos, pausas; zera_em | `TestEvGuardas.*`, `TestPausa.*` |
| AGUARDANDO_HUMANO com portao/retorno; `aprovar-<portao>.sh` gerado (chmod 600) | `test_ah_guarda_portao_e_retorno_no_fold`, `test_desistir_vai_para_ah_abandonar_e_gera_aprovar_sh` |
| limite_uso (rate_limit recua o teto 5→3 pelo resto da obra), retomar, pausas_esgotadas | `TestPausa.*` |
| RETOMAR.md gerado a cada ev (cabeçalho seq/hash = último registro, 9 seções em ordem, 1 comando) | `TestRetomada.test_retomar_md_regenerado_a_cada_ev` |
| `retomar`: cadeia ok ⇒ 0 + `retomada`; linha editada ⇒ 1 sem gravar | `TestRetomada.*` |
| Write-ahead: `despachada` é a única fonte de vivos; em voo perdida ⇒ `perdida` + task.perdida | `test_write_ahead_conta_vivo_...`, `test_retomar_nao_acusa_perdida_...`, `test_vivos_contam_...` |
| `maquina check`: máquina real ⇒ 0; negativos plantados de invariantes.json5 ⇒ 1 citando o invariante; JSON inválido ⇒ 2 | `TestMaquinaCheck.*` |
| hook_vivo (A4) libera `iniciar` (integração A+B) | `TestIntegracaoHookVivo` |
| co.py: 20 subcomandos com `--help` listando flags/ações; inválido ⇒ 2 (usage); sem traceback; formato `pendente: <sub>` | `test_a_cli.py` |
| co_hook bloqueia aprovação do principal e do subagente (co.py aprovar/oraculo mudar, ac.py gate/preauth/oracle change), com variações | `TestHookAprovacao.*` |
| co_hook bloqueia escrita em `.construcao/aprovacoes/oraculo` (exceto o autor no MANIFEST) e leitura do held-out por construtor (Read/Grep/Glob/Bash) | `TestHookProtegidos.*` |
| Falha fechada só quando o payload bruto menciona aprovação/held-out | `TestHookFalhaFechada` |
| Audit tool_call fora do workspace | `TestHookAudit` |
| `--selftest` sai 0; o selftest reprova se `classificar` for sabotado (L03); matriz de `payloads_selftest()`; `co.py hook` lê do stdin; `hook selftest --vivo` | `TestHookSelftestESettings.*` |
| `references/hook-settings.json5` = trecho de settings do contrato | `test_hook_settings_json5` |
| `aprovar`: sem tty ⇒ 2 e nada gravado; variáveis de ambiente não dispensam; pty + desafio numérico `DESAFIO: NNNN` (≥4 dígitos, só dígitos; AC-07) ⇒ arquivo + `aprovacao` + transição humana (seq+1) + audit; desafio errado (número ≠) ⇒ 1; desafio varia; audit dentro do ws ⇒ 1 | `test_b_aprovar.py` |
| `gerar_regressao`: G0..G14, N/A com motivo, sem_waiver ⇒ waiver false | `TestRegressao` |
| G3 território (diff × writes; deleção e rename contam) | `TestG3Territorio.*` |
| G4 gaming (teste editado, pytest.skip, sys.exit(0), assert True, literal do held-out); `sys.exit(main())` não é gaming | `TestG4Gaming.*` |
| G0 oráculo intacto (ac.py oracle verify + contagens) | `TestG0.*` |
| G1 suítes: verde passa; teste falhando, 0 coletados ou ferramenta ausente ⇒ FAIL | `TestG1.*` |
| Veredito: precedência NO-GO > GO (simulado) > GO (com waiver) > GO; G0/G1/G3/G4 sem waiver; o veredito é recalculado; aprovação sem audit ⇒ NO-GO | `TestVeredito.*` |

**L03 (o subcomando roda mas o efeito não acontece ⇒ reprova)**:
- co_estado: todo `ev` positivo é conferido pelo `status`, pelo ledger e pelo RETOMAR.md, nunca só pelo exit.
- Hook: `classificar` sabotado tem de fazer o selftest reprovar. Todo bloqueio tem um par permitido.
- G0: com asserção removida, reprova.
- G1: a suíte que sai 0 sem coletar teste reprova.
- G3/G4: todo caso de reprovação tem um controle que passa.
- Veredito: o "GO" gravado no relatório com um FAIL dentro dá NO-GO.

Todo teste que espera exit 2 confere antes, no `setUp`, que o script existe. Com isso, "arquivo ausente" (que
também sai 2) não passa por vácuo.

## Interpretações (pontos que o contrato não fixa)

1. **Fold**: replica todo registro com cadeia válida e coerente com maquina.json5. A transição é identificada por
   (evento, de, para, portao), `@retorno` resolvido. As guardas só são avaliadas na escrita (`ev`/`aprovar`),
   nunca no replay. Task desconhecida começa em `PENDENTE`. `vivos` segue a ordem dos `despachada`.
2. **Ator do registro `aprovacao`**: `script`, pela regra "operacional = script". A transição humana seguinte tem
   ator `humano`.
3. **`ev`**: evento inexistente ⇒ 2. Evento que existe mas não sai do estado atual ⇒ 1 ou 2, sem gravar nada.
   `init` sobre obra já existente ⇒ ≠ 0, com o ledger intacto. `--payload` com JSON inválido ⇒ 2.
4. **`hook_vivo`** = selftest estático do co_hook ok **e** linha `tool_call` bloqueada citando
   `aprovar __selftest__` no audit, com ts ≥ gênese. `hook selftest --vivo` sai 0 ou 1 por essa linha. O teste de
   `iniciar` positivo só fica verde depois que B for integrado.
5. **`status --json`**: o stdout é só o JSON. Divergência entre cache e fold gera um aviso, em qualquer stream,
   contendo "cache" ou "diverg".
6. **`aprovar-<portao>.sh`**: gerado ao entrar em AGUARDANDO_HUMANO, com `#!/bin/sh`, o hash_estado e 3 linhas
   `co.py --work <ws> aprovar <portao> --decisao X` (podem vir comentadas, como no exemplo de formatos), sem bit
   de execução.
7. **`limite_uso`** via `ev limite_uso --payload FILE` ({causa, retomar_apos, mensagem}).
   - `limite_detectado` = payload com causa.
   - `teto_recuado` é gravado na mesma chamada quando causa = rate_limit.
   - `agora_apos_retomar` = now ≥ retomar_apos.
8. **`retomar`**:
   - Cadeia ok ⇒ grava `retomada`.
   - Cada `despachada` sem `retornou` e sem resultado ⇒ `perdida` (fecha a vaga).
   - Se a task está EM_VOO ⇒ `task.perdida`, com a tentativa da task +1. Com 3 tentativas ⇒ REJEITADA.
   - Queda entre `despachada` e `task.despachar` ⇒ a task segue PRONTA com as tentativas inalteradas (D3).
   - Cadeia quebrada (edição, lacuna, payload_hash velho) ⇒ 1 e nada gravado.
   - `colhida` (worktree) fica fora da onda 1.
9. **`maquina check`** cita o id do invariante violado (S1..S4, I1..I7) e respeita `--nivel`.
   **Achado:** o negativo de I3 em invariantes.json5 ("MEDIR→ENTREGUE") **não** viola I3 na semântica de remoção
   de nó, porque MEDIR só é alcançável via VERIFICAR. Usei INTEGRAR→MEDIR (a variante "LOTE→MEDIR→..." do mesmo
   texto).
10. **co.py pendente**: só os subcomandos da onda 2 podem responder `pendente: <sub>`. Na onda 1 têm de estar
    implementados: `init`, `ev`, `status`, `maquina check`, `retomar`, `aprovar`, `hook`, `diff`,
    `portao run|selftest` e `veredito`.
11. **Hook: workspace e permissões**
    - Workspace = diretório ancestral que contém `.construcao/`. Fora de um workspace, caminhos chamados
      `aprovacoes/` ou `oraculo/` são livres.
    - Ninguém escreve no `MANIFEST.json5` pelo hook (só o script).
    - Autor = `agent_type` em `frentes[*].autores`. Construtor = subagente cujo agent_type não é autor.
    - Leitura do held-out pelo principal: não testada.
12. **Hook no Bash**
    - Escrita (`>`, `cp`, `sed -i`, ...) em protegido ⇒ bloqueia. Leitura de `.construcao`/`aprovacoes` ⇒ permite.
    - Leitura do held-out inclui: caminho relativo ao `cwd` do payload, `..`, glob (`held*`) e ferramenta
      recursiva sobre um ancestral (`Grep` em `oraculo/`, `find oraculo`, `Glob **` a partir do ws).
    - Executar `aprovar-*.sh` ⇒ bloqueia.
    - Leitores (`grep`/`cat`/`git log`) citando `aprovar` ⇒ permite.
13. **Falha fechada** só quando o texto bruto casa `aprovar|approve|gate|preauth|heldout|held-out`.
14. **`co_hook.main(stdin)`** respeita `--selftest` em `sys.argv`, e o selftest decide via
    `classificar(payload) -> (bloqueia, motivo)`. `payloads_selftest()` devolve uma lista serializável em JSON com
    pelo menos 8 itens.
15. **`aprovar`**:
    - hash_estado = fold no momento de aprovar.
    - Sem tty (stdin `/dev/null` ou pipe) ⇒ 2.
    - Audit dentro do ws ⇒ 1 (contrato; o ac.py usa 2).
    - Portão errado e TOCTOU de hash_estado não são testados na onda 1.
16. **`diff`**:
    - Compara a base com a árvore atual: commits + staged + não staged + untracked + mudança de modo.
    - `--repo` (padrão: alvo). PLANO em `<ws>/PLANO.json5`, com writes relativos ao repo.
    - G4 olha só as linhas adicionadas e toques em `tests/**`, `test_*.py`, `conftest.py` e config de teste.
    - Literal do held-out = string de `oraculo/heldout/casos/*.json` que aparece no código.
    - A saída cita G3/G4. Task desconhecida ou base inválida ⇒ 2.
17. **`portao run --only`**:
    - Grava gate-report.json (`only`) e o evento `portao_relatorio`.
    - Num run parcial que passa, o exit não é testado. FAIL ⇒ exit 1 e NO-GO.
    - Os testes chamam `co_portao.gerar_regressao(ws, tipo)`; o `portao run` pode chamá-la também.
18. **G0** = `ac.py --work <ws>/campanhas/construcao oracle verify` **e** contagens atuais ≥ as do `oraculo_congelado`
    do fold. Campanha ausente ⇒ FAIL/ERRO.
    **G1**:
    - PASS exige exit 0 **e** evidência de ≥ 1 teste coletado.
    - cli sem `suites` ⇒ FAIL.
19. **Veredito**:
    - Recalcula a partir dos itens e ignora o `veredito` gravado.
    - Todo item da regressão precisa estar presente.
    - WAIVED só vale em item com waiver e com arquivo de aprovação existente. NA só quando `aplica=false`.
    - Aprovação no ledger casa com o audit `tipo aprovacao` por seq + work.
    - `gate_report_hash` = sha256 do arquivo (ou sha_obj).
    - Exit: GO* ⇒ 0, NO-GO ⇒ 1.
20. **Local do held-out**: segui a instrução do orquestrador (`campanhas/onda1/oraculo/heldout/`). O ondas.json5
    diz `campanhas/construcao/oraculo/heldout/onda1/`.

## Rodada 2 — achados do verificador cego (A1..A11)

Os testes ficam em `tests/onda1/test_r2_achados.py`. As variações de bypass estão no held-out (`test_heldout_r2.py`).
Cada teste reproduz o achado. Quando há controle positivo, ele roda no mesmo teste.

**Fixture coerente (`R2Base.ledger_coerente`)**
- `premissas_ok.obra_hash`, `plano_ok.plano_hash` e `plano_ok.regressao_hash` são o **sha256 dos bytes** do
  arquivo.
- Toda `aprovacao` gravada à mão ganha a linha `tipo aprovacao` correspondente no audit.

**A1 / A5 — entrega**
- `portao run --only ... --final` não pode produzir um relatório que conte como regressão ou entrega: `final`
  e `GO` não podem andar juntos num relatório parcial.
- `aprovar entrega` com esse relatório, ou com `GO (simulado)`, sai ≠ 0 e não grava nada.
- Só `GO` ou `GO (com waiver)` de um run **completo** (`only = null`), `final`, não simulado, satisfaz
  `veredito_go_final` e `portao_regressao_go`.
- Não há controle positivo de entrega na onda 1, porque G2/G5..G14 ainda não passam. Ele fica para a onda 3.

**A2 — regressão**
- G0/G1/G3/G4 são sempre aplicáveis e sempre avaliados no `portao run`, mesmo marcados `aplica:false` ou
  removidos de `regressao.json5`.
- `veredito`: se o ledger tem `plano_ok`, o sha256 de `regressao.json5` precisa ser igual a
  `plano_ok.regressao_hash`; senão NO-GO. Antes de PLANO não há comparação, o que mantém os testes antigos.
- Hook: construtor não escreve `<ws>/regressao.json5` (Write/Edit/Bash). Leitura é permitida.

**A3 — hook**: busca recursiva a partir de **qualquer** ancestral de um workspace (não só do pai ou de filhos
imediatos) que alcance `oraculo/heldout` ⇒ bloqueia. Vale para Grep/Glob, `grep -r`, `find`, `rg` e `ls -R`.

**A4 — obra e PLANO reescritos**
- Com `premissas_ok` no ledger, `obra.json5` diferente do hash gravado ⇒ G1 e G3 FAIL/ERRO. Isso cobre a suíte
  trocada e a `base` trocada.
- Com `plano_ok`, `PLANO.json5` diferente de `plano_hash` ⇒ G3 reprova.
- `writes` amplos (`**` ou equivalente na raiz) sem portão humano `plano` aprovado ⇒ G3 reprova. Isso vale também
  para o diff por task.
- "Contar testes de verdade" além do hash, por exemplo distinguir `echo 'Ran 3 tests'` registrado desde o início,
  não tem definição determinística. Não foi testado. Fica coberto pela conferência de hash e pelo portão humano
  `stop`, que vê a suíte.

**A5**: coberto pelo teste `GO (simulado)` em A1/A5.

**A6 — hook nega aprovação por**
- `python3 -c 'import co...'` com os argumentos fora do código (`sys.argv`);
- `git -c alias.X='!...'`;
- `vim`/`vi`/`nvim` com `-c`/`+` executando `!...`.

`git -c core.pager=cat log` e `vim arquivo` continuam permitidos.

**A7 — hook**: `cd` encadeado (`&&`, `;`, relativo, `..`) é resolvido cumulativamente antes de checar o caminho.

**A8 — truncamento do ledger** sai 1 em `retomar`, `status` e `ev` (e `ev` não grava). Dois casos:
- `state.json` tem `ledger_seq` ou `ledger_hash` além do fim do ledger.
- O audit tem uma linha `tipo aprovacao` com seq/work que o ledger não tem, mesmo sem `state.json`.

**A9 — `aprovar oraculo --decisao aprovado`**: na mesma chamada roda `ac.py --work <ws>/campanhas/construcao
oracle freeze` sobre os arquivos de `MANIFEST.frentes[*].dev|heldout` e grava `oraculo_congelado` (hash, n_testes,
n_assercoes ≥ 1) depois da transição. `status.oraculo` ≠ null e G0 passa em seguida. A campanha-mãe já
inicializada é pré-condição do teste.

**A10 (baixo, TOCTOU de hash_estado em `aprovar`)**
- Não foi testado: não há como intercalar uma escrita entre a exibição do desafio e a redigitação sem depender de
  tempo.
- Exigência: recalcular o fold **depois** do desafio. Se o hash_estado mudou, sair 1 sem gravar nada.

**A11 (baixo, pós-gravação fora do lock)**
- Não foi testado: exige concorrência real entre processos e não é determinístico.
- Exigência: append, cache e RETOMAR.md sob o mesmo lock exclusivo do ledger.

## Rodada 2 — G5 (mutantes sobreviventes do agente M)

Os testes ficam em `tests/onda1/test_r2_mutantes.py` (27 testes). As variações de bypass estão no held-out
(`test_heldout_r2b.py`, 4 testes).

**Como os mortes foram conferidas**: reapliquei cada mutante numa cópia temporária da skill (HOME temporário),
sobre os scripts que o agente M mediu (`mut/pristine`). Os testes novos matam 27 dos 28 sobreviventes:
- E01, E04, E06, E08, E12, E13, E15, E16, E17, E19, E22, E23, E24, E26, E28, E29, E30;
- H13, H14, H18, H20, H22;
- P06, P13, P14, P17, P20.

Taxa estimada: 78/79 (98,7%). Retorno constante: 22/22.

**E14 (não-determinismo com mais de 2 guardas)**: equivalente na máquina atual. Nenhum (estado, evento) tem três
guardas que possam ser verdadeiras ao mesmo tempo, e transicionar recarrega `maquina.json5` (não há como injetar
uma máquina sintética pela API pública).

**Classificação**
- (a) Passa hoje, só faltava o teste: os 27 visíveis e 3 dos 4 ocultos.
- (b) Defeito real: só o caso `python3 -c "import shutil; shutil.rmtree('<ws>')"` (H22 por código embutido),
  em que o hook não bloqueia a destruição do workspace.

**Interpretações novas**
- `avaliar_guarda(expr, {nome: valor})` usa lógica de Kleene; indeterminado nunca satisfaz.
- `transicionar(ws, ev, atomos=...)`: átomos passados completam os indeterminados. Os computados do disco
  (`lote_cabe_no_teto`: vivos < teto_vigente) continuam valendo.
- Aninhamento de shell além do analisável (mais de 6 níveis) falha fechado, mesmo com um comando inócuo no
  fundo. Dois níveis comuns continuam permitidos.
- Glob cujo padrão pode casar `<ws>/oraculo/heldout` na profundidade exata é bloqueado, mesmo sem o diretório em
  disco.
- `aprovar` com stdin que não é tty sai 2, mesmo com terminal controlador disponível.

**Correção de fixture no held-out**: `test_heldout_c.test_aprovacao_com_linha_de_audit_correspondente_e_go` usava
`premissas_ok.obra_hash` fictício. Com a correção de A4, isso dá NO-GO legítimo. Passou a gravar o hash real de
`obra.json5`; o requisito testado continua o mesmo.

## Rodada 3 — achados do 2º verificador cego (R3-3..R3-10)

Os testes ficam em `tests/onda1/test_r3_achados.py`. As variações estão no held-out (`test_heldout_r3.py`).
Todos falham no código anterior à correção, salvo os controles.

- **R3-3**: cache (`state.json`) ausente numa obra com ledger não vazio ⇒ `status`, `ev` e `retomar` saem 1 e
  nada é gravado (estado incoerente).
  - Vale também quando o ledger foi totalmente re-encadeado e truncado depois do apagamento, e quando o cache é
    `{}`.
  - O fold cruza com o audit mesmo sem o cache (A8).
  - Cache atrasado (o ledger andou além dele) continua legítimo. Por isso o teste oculto antigo
    `test_status_sem_cache_refaz_do_ledger` virou `test_status_com_cache_atrasado_refaz_do_ledger`.
- **R3-4 — hook**: caminhos comparados com caixa normalizada (APFS) e unicode NFC/NFD, tanto para o held-out
  quanto para os protegidos (`.construcao`, `aprovacoes`, `oraculo`). Vale para Read/Write/Edit/Grep/Glob e Bash.
- **R3-5**: em `premissas_ok`, o motor calcula `obra_hash` e `pontos_hash` dos arquivos em disco no momento do
  evento. Hash vindo no `--payload` é ignorado (o gravado é o do disco) ou a escrita é recusada (nada gravado).
  Sem payload, o motor grava os hashes mesmo assim.
- **R3-6 — G1**: só conta teste executado de verdade, com evidência estruturada (junit/json) gerada pelo próprio
  runner num caminho escolhido pelo G1.
  - Uma suíte que só imprime "Ran N tests", "N passed" ou "ok" ⇒ FAIL/ERRO.
  - A suíte `python3 -m unittest discover -s tests -v` real continua PASS.
- **R3-7 — I4**: contador zerado dentro do próprio ciclo (por `zera` na transição ou por `zera_em` do contador)
  não limita o ciclo. A máquina real continua passando.
- **R3-8 — G4** também pega:
  - `from pytest import skip` seguido de `skip()`;
  - `getattr(sys, 'exit')(0)`;
  - `assertTrue(True)`;
  - `from sys import exit` seguido de `exit(0)`.
- **R3-9 — hook**: nega git com `-C`, `--git-dir` ou `--work-tree` quando `diff --no-index`, `show` ou `cat-file`
  alcançam o held-out.
- **R3-10**: `aprovar entrega` é recusado (nada gravado) quando há `aprovacao` no ledger sem a linha `tipo aprovacao`
  correspondente no audit, porque `veredito_go_final` cruza `aprovacoes_sem_audit`.
- **R3-1/R3-2 (forja de aprovação por import/pty)**: fora deste oráculo. A onda 1 **depende** da frase-senha da
  auto-correcao v0.4, a ser integrada no `aprovar` por campanha separada. Até lá, o limite honesto do DESENHO-v2 §4
  continua valendo e o GO da onda 1 deve citar essa dependência.

## Rodada 3 — propriedades (medição M2)

Os testes ficam em `tests/onda1/test_r3_propriedades.py`. As variações estão no held-out (`test_heldout_r3b.py`).
Eles miram a **classe** do defeito, não o mutante; li só `sobreviventes-visiveis.json`.

**Forja coerente (`forja`)**: o adversário re-encadeia seq, payload_hash, prev e hash e alinha
`state.json.ledger_seq/ledger_hash`, deixando sem recalcular só o campo sob teste. Um controle sem adulteração
precisa ser aceito. Assim cada conferência de integridade é provada sozinha.

**Propriedades exigidas**
- **Ledger, campo a campo**: cada um destes sozinho ⇒ `retomar`/`status`/`ev` ≠ 0, sem gravar:
  - payload com payload_hash velho;
  - payload_hash trocado;
  - prev quebrado (meio e gênese);
  - hash trocado;
  - seq com lacuna;
  - ts fora do formato;
  - gênese ausente.
- **Operacional coerente**: ator script, de/para nulos, evento operacional conhecido e nível válido. Transição com
  `de`, `ator` ou `evento` adulterados ⇒ fold recusa.
- **`avaliar_guarda`**: precedência `not` > `and` > `or`, parênteses e comparações, com casos SIM e NÃO.
- **`transicionar`**:
  - evento humano sem canal humano é recusado, mesmo com `atomos={'aprovacao_humana': True}`;
  - com canal, o `hash_estado` aprovado tem de ser o atual sob a trava (o de um estado anterior é recusado);
  - controle: com o hash atual, grava.
- **`retomar_md_valido`**: RETOMAR.md ausente, velho ou com hash adulterado ⇒ `parar` recusado; válido ⇒ grava e
  vai para AGUARDANDO_HUMANO[entrega].
- **`hook_selftest_estatico`**: numa cópia da skill com um `co_hook --selftest` que reprova ⇒ False e
  `ev iniciar` sai 1; com a cópia intacta ⇒ True e sai 0.
- **`co_portao.veredito(ws)`** concorda com a CLI: GO, GO (com waiver), NO-GO por FAIL e por ERRO.
- **`veredito`**: `regressao_hash` do relatório adulterado ⇒ NO-GO.
- **`--only`**: nunca grava `final=true`, inclusive com o núcleo inteiro. O run completo `--final` grava `true`.
- **G3**: reprova escrita em cada protegido do ws (`.construcao`, `aprovacoes`, `oraculo/dev`, `oraculo/heldout`),
  mesmo quando os writes da task os cobrem (`obra/**`). Arquivo do ws fora dos protegidos passa.
- **Hook**:
  - escrita no audit (Write, Edit, `>>`, `tee`, `cp`, `sed -i`, `python -c`, `rm`) ⇒ nega; leitura do audit e
    escrita em outro lugar de `~/.claude` ⇒ permite;
  - destrutivo (`rm -rf`, `mv`, `find -delete`, `shutil.rmtree`) sobre **qualquer** ancestral de um workspace
    ⇒ nega.
- **CLI**: arquivo de estado com tipo errado (lista no lugar de objeto) ⇒ exit ≠ 0, sem traceback.

**Classificação**
- (a) Passa hoje: 25 de 26 visíveis e 7 de 8 ocultos.
- (b) Defeito real: destrutivo sobre ancestral **não imediato** do workspace (mesma classe de A3).
  - Na primeira execução, `rm -rf <avô>`, `mv <avô>`, `find <avô> -delete` e `shutil.rmtree(<avô>)` passavam.
  - Na execução final, depois das correções paralelas da rodada 3, só `find <avô> -delete` continua passando
    (held-out).

## Endurecimento (mudança oficial pós-rodada 3)

Três exigências frouxas do oráculo foram endurecidas, sem afrouxar nada.

1. **Veredito exige relatório ancorado.** `gate-report.json` sem evento `portao_relatorio` no ledger, ou com hash
   ≠ do ancorado, ⇒ NO-GO.
   - O positivo ancora pelo mesmo evento que `portao run` grava.
   - Um `portao run` completo não pode dar GO na onda 1, porque G2 e G5..G14 ainda saem ERRO.
2. **G0 exige MANIFEST real**, com `sha256(bytes de oraculo/MANIFEST.json5)` igual a `oraculo_congelado.manifest_hash`.
   MANIFEST ausente ou alterado depois do congelamento ⇒ FAIL.
3. **Waiver exige aprovação de verdade** (`waiver_aprovado` em `test_c_portao.py`), com estas peças ao mesmo tempo:
   - evento `aprovacao` no ledger;
   - arquivo `aprovacoes/<portao>-<seq>.json` com `decisao: aprovado` e `seq` igual ao do evento;
   - linha `tipo aprovacao` no audit fora do ws (seq + work).

   Faltar qualquer peça (sem seq, decisão rejeitado, sem audit, arquivo sem evento no ledger) ⇒ NO-GO.

**Outros pontos permissivos que ficaram como estão**: comportamento pré-PLANO, pendente de decisão.
- `TestG1.test_g1_passa_...`: G1 PASS sem `premissas_ok` no ledger ancorando `obra.json5`.
- `TestG3Territorio`/`TestG4Gaming`: positivos de `diff` sem `plano_ok` ancorando `PLANO.json5`.
- `TestVeredito`: GO sem `plano_ok`; o `regressao_hash` só é cruzado com o ledger depois de PLANO.
- `grava_hook_vivo`: a linha de audit fabricada basta como evidência de hook vivo, junto do selftest estático.
- **Fora do meu território:** `tests/onda1/gerado/test_gerado.py:810` (oráculo "O1-gerado") usa o mesmo waiver
  frouxo `{"portao": "entrega"}`.

## Rodada 2 do V4 (mudança oficial): `sistema_hash` real e waiver do próprio item

- Relatórios de fixture gravam `sistema_hash = co_estado.hash_sistema(alvo)` (helper `sistema_hash_real`), tanto
  em `TestVeredito.relatorio` quanto em `R2Base.relatorio_completo`. Relatório com `sistema_hash` de outro estado
  do alvo (o alvo mudou depois) ou inventado ⇒ NO-GO.
- `waiver_aprovado` aprova o portão do **próprio** item (`Gn`). Aprovação de outro item (`G5` para waiver de `G2`)
  ou de `entrega` ⇒ NO-GO.
- O `sistema_hash` dentro do payload de `medicao_registrada` nas fixtures continua fictício: não entra no veredito.
- **Oráculo gerado (não editado, avisado ao autor)**:
  - `gerado/test_gerado.py:194` grava `sistema_hash "d"*64` no gate-report;
  - `:1082` usa waiver `{"portao": "entrega"}` sem o portão do item.
