# Mutantes G5 — onda 1 (agente M)

**Resultado: 51/79 mortos (64,6%). Retorno constante: 18/22 mortos.** O critério do founder (taxa de pelo menos 80% e todos os mutantes de retorno constante mortos) **NÃO foi atendido**.

| tipo | mortos/total |
|---|---|
| retorno_constante | 18/22 |
| hash_sem_prev | 1/1 |
| aprovacao_sem_tty | 2/3 |
| feature_removida | 19/34 |
| inversao_limite | 11/19 |

Por arquivo: co_hook 17/22, co_portao 17/22, co.py 4/4, co_estado 13/31. O ponto fraco é o `co_estado`: cadeia, fold, guardas e aprovação.

## Método
- Copiei a skill para um HOME temporário em `$HOME/.claude/skills/construcao-orquestrada`, com symlink para `auto-correcao`. O `_comum.py` e o `run_heldout.py` resolvem `~/.claude/skills` via `expanduser`, então rodaram contra a cópia.
- Plantei um mutante por vez e restaurei `scripts/` entre um e outro.
- Rodei primeiro a suíte visível (`unittest discover -f -s tests/onda1`). O held-out só rodou quando a visível passou.
- Usei `PYTHONDONTWRITEBYTECODE=1`.
- Na linha de base, sem mutante, as duas suítes passaram: 99 testes visíveis e 39 do held-out.
- Oráculo medido: o snapshot da rodada 1. O `test_heldout_r2.py` e o `tests/onda1/test_r2_achados.py` apareceram durante a medição e ficaram **de fora**. O r2 importa `test_r2_achados`, que no código atual falha 19 vezes (é teste vermelho da rodada 2). Na primeira passada, esse erro de import "matava" todo mutante que chegava ao held-out. Descartei essa passada e refiz tudo com uma cópia congelada do held-out a/b/c.
- O held-out matou só 2 mutantes que a suíte visível deixou passar: E05 (payload_hash velho numa cadeia re-encadeada) e E07 (seq com lacuna).

## Sobreviventes e o teste que falta

### Retorno constante (bloqueiam o critério)
- **E01 `verificar_cadeia` sempre True** (co_estado.py:308). É função de contrato (`contrato.modulos`) sem chamador interno, e nenhum teste a chama. Falta um teste com `py_call`: cadeia adulterada (linha editada ou removida) ⇒ `verificar_cadeia(ws) is False`. Também falta o caso positivo, cadeia íntegra ⇒ True.
- **E15 `avaliar_guarda` sempre True** (co_estado.py:506). Também é função de contrato sem uso interno, porque `transicionar` usa `avaliar_ast`. Falta um teste com `py_call`: guarda falsa (`"tentativas >= MAX_TENTATIVAS"` com valores abaixo do teto), identificador ausente (indeterminado ⇒ False) e and/or de Kleene.
- **E26 átomo `workspace_fora_do_alvo` sempre True** (co_estado.py:819). O `cmd_init` já recusa um ws dentro do alvo, então o átomo só serve se o `obra.json5` mudar depois. Falta um teste que, depois do `init`, reescreva `obra.json5` com `alvo` = ancestral do ws (ou faça um `ev iniciar` com hook vivo gravado) e espere exit 1 com o ledger byte a byte intacto.
- **P06 `cadeia_ok` sempre True** (co_portao.py:128). Nenhum teste quebra o ledger antes de `veredito`/`portao run`. Falta um teste: gate-report todo PASS + linha do ledger editada ⇒ `co.py veredito` = NO-GO com "cadeia quebrada" (exit 1). Também falta `portao run` com cadeia quebrada ⇒ nada gravado.

### Aprovação / tty
- **E08 `_stdin_tty` sempre True**. Hoje sobrevive porque `human_channel` ainda exige `/dev/tty`, e sem terminal controlador a chamada é recusada. Só a defesa em profundidade segura. Falta um teste que rode `aprovar` com stdin = pipe **dentro** de uma sessão com tty controlador (pty.fork + `stdin=PIPE` no filho) e espere exit 2, nada gravado.
- **E12 sem checagem TOCTOU**. Falta um teste no pty que grave um evento no ledger entre a exibição do DESAFIO e a resposta, e espere exit 1, sem `aprovacao` e sem arquivo.
- **E13 `transicionar` aceita evento humano sem canal humano**. O `cmd_ev` barra antes, então só é alcançável via API. Falta um teste com `py_call`: `transicionar(ws, "aprovado")` em AGUARDANDO_HUMANO ⇒ `Bad` e ledger intacto.
- **E17 o fold aceita transição humana sem `aprovacao` imediatamente antes (I6/D9)**. Falta um teste em que `Ledger.t("aprovado", "AGUARDANDO_HUMANO", ...)` seja escrito à mão **sem** o `humano()` anterior: `status`/`retomar` ⇒ exit 1. Também falta o caso com `aprovacao` de outro portão ou de outra decisão.

### Cadeia / ledger
- **E04 (prev não conferido), E06 (gênese não exigida)**. Falta re-encadear a cadeia à mão com `prev` errado mas `hash` recalculado, e outra com seq 1 ≠ `genese`, esperando exit 1 em `retomar`/`status`.
- **E23 / E30 / E24 (append_evento, transicionar e fold sobre cadeia quebrada)**. Hoje só o `retomar` é testado com cadeia quebrada. Falta: linha editada ⇒ `ev nota`, `ev iniciar` e `status` saem ≠0 e o ledger fica byte a byte igual.

### Guardas / limites
- **E14 (não-determinismo com >2)**. Provavelmente equivalente com a máquina atual, que não tem duas guardas verdadeiras ao mesmo tempo. Seria morto por um teste de `transicionar` com `maquina` sintética de duas guardas true ⇒ `Bad` I5.
- **E16 / E19 (indeterminado vira verdadeiro, fail-open)**. Falta um evento cuja guarda depende de um átomo indeterminado (ex.: `ev oraculo_pronto` sem `atomos`) ⇒ exit 1 "guarda falsa". Esse teste mataria os dois.
- **E22 (`lote_cabe_no_teto` < → <=)**. Falta a fronteira: `vivos == teto_vigente` ⇒ o despacho é recusado.
- **E28 (pass3_final aceita k=2)**. Falta a fronteira: `medicao_registrada {final:true,k:2}` ⇒ a guarda de entrega é falsa.
- **E29 (hook_vivo aceita linha `permitido`)**. Falta um audit com linha `aprovar __selftest__` com decisao=permitido ⇒ `ev iniciar` sai 1.

### Hook
- **H13 (profundidade >6 → >60)**. Falta um comando aninhado em 7 a 10 níveis de `bash -c` citando `co.py aprovar` ⇒ bloqueia por "aninhamento profundo".
- **H14 (ARG_EXECUTORS ignorado)**. Falta `echo stop | xargs python3 co.py --work W aprovar` e `eval "python3 co.py aprovar stop"` como **subagente**/principal ⇒ exit 2. A rota por texto embutido cobre parte, mas não o `xargs` com argumentos separados.
- **H18 (escrita via `python -c` ignorada)**. Falta `python3 -c "open('<ws>/.construcao/ledger.jsonl','a').write('x')"` ⇒ bloqueia.
- **H20 (glob vs held-out >= → >)**. Falta Glob/Read com padrão de profundidade exata `<ws>/oraculo/heldout` (ex.: `<ws>/oraculo/heldou?`) por construtor ⇒ bloqueia.
- **H22 (destrutivo sobre o próprio ws)**. Falta `rm -rf <ws>` e `mv <ws> /tmp/x` ⇒ exit 2. Hoje só ancestral e protegidos são testados.

### Portão
- **P13 (G0 tolera 1 teste a menos)**. Hoje só a remoção de asserção é testada. Falta remover **uma função de teste** mantendo as asserções ⇒ G0 FAIL.
- **P14 (G0 não compara o hash do ledger com o da campanha)**. Falta um `oraculo_congelado` no ledger com hash ≠ do `state.json` da campanha ⇒ G0 FAIL.
- **P17 (G3 ignora protegidos)**. Falta um ws dentro do repo-alvo, com writes `**` cobrindo `<ws>/oraculo/x` ⇒ G3 FAIL "em protegido".
- **P20 (gate duplicado aceito)**. Falta um gate-report com G1 duas vezes (uma FAIL, uma PASS) ⇒ NO-GO.

## Para chegar a pelo menos 80%
Com os 4 testes de retorno constante (E01, E15, E26, P06), os de cadeia (E04/E06/E23/E24/E30), E16/E19, E17, E13 e H22/H14/H18, o total vai a ≥66/79 (≥83%), sem contar os prováveis equivalentes E14 e E08.

## Artefatos
- `relatorio.json` (este diretório).
- Driver reprodutível: `mutantes.py` e `driver.py` no scratchpad da sessão (não versionado).
- A skill original não foi editada.
