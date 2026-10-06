# Oráculo de aceite — auto-correcao v0.3

Autor: escritor do oráculo, separado do corretor (L15). Arquivo: `test_v03_oraculo.py` (unittest puro, Python 3.9+).
Rodar: `python3 -m unittest test_v03_oraculo -v` dentro desta pasta. Base de hoje: `base.txt` (**27/27 falham**).
Regressão: `python3 ~/.claude/skills/auto-correcao/scripts/tests/test_ac.py` (22 testes), rodado pelo integrador.

## Requisito → testes

| Req | Testes (classe.método) |
|---|---|
| AC-01 remedição só com execução pós-correção e com `decision` | `AC01RemedicaoPosCorrecaoTest.test_base_run_alone_does_not_close_remedicao` (negativo: só a base → `check remedicao.1` e `done remedicao` ≠0; depois positivo com execução nova + `--decision` → 0) · `…test_post_correction_run_without_decision_does_not_close` |
| AC-02 `stage` acompanha `done` | `AC02StatusEtapaTest.test_done_advances_stage_and_failed_done_does_not` · `…test_done_skips_already_completed_stages` · `…test_all_done_shows_concluida` |
| AC-03 total de qualidade = base, salvo `oracle change` posterior | `AC03TotalQualidadeTest.test_mismatched_total_refused_citing_L02` · `…test_oracle_change_after_base_allows_new_total` · `…test_oracle_change_before_base_does_not_excuse` |
| AC-04(a) tty + desafio | `AC04aCanalHumanoTest.test_gate_refused_without_tty` · `…test_preauth_refused_without_tty` · `…test_env_vars_do_not_bypass_tty` · `…test_simulated_gate_without_tty_never_satisfies_a_gate` · `…test_gate_in_tty_with_retyped_challenge` · `…test_gate_in_tty_wrong_challenge_refused` · `…test_preauth_in_tty_with_retyped_challenge` · `…test_challenge_varies_between_calls` |
| AC-04(b) hook PreToolUse | `AC04bHookTest.test_denies_approval_commands_and_variants` (21 comandos × principal/subagente) · `…test_allows_unrelated_and_read_only_ac_commands` (11) · `…test_allows_non_bash_tools` |
| AC-04(c) selftest | `AC04cHookSelftestTest.test_selftest_exits_zero` |
| AC-04(d) auditoria | `AC04dAuditoriaTest.test_each_approval_appends_audit_line_outside_work` · `…test_audit_log_inside_work_dir_refused` |
| L17 | `L17CampanhasSobrepostasTest.test_licao_L17_registered` · `…test_overlap_disjoint_scopes_ok` · `…test_overlap_colliding_scopes_exit_1` · `…test_same_globs_on_different_targets_do_not_collide` · `…test_scope_over_other_campaign_oracle_collides` |

## Interfaces FIXADAS (o corretor segue)

**AC-01** — `check remedicao.1` (e `done remedicao`) só passa se houver na rodada ≥1 execução com `at` estritamente
posterior a `done["correcao.1"]` E `decision` não vazia. A recusa (exit 1) cita `correcao.1` na mensagem. O teste
separa base e correção por ≥1,1 s (timestamps têm resolução de segundo), então comparar `at` ou ordem do ledger serve.

**AC-02** — `done <etapa>` bem-sucedido grava `state.stage` = primeira etapa de `ciclo.order` (depois dela) ainda não
totalmente concluída; se todas estão concluídas, `stage = "concluida"`. `done` que falha não muda `stage`. `status`
imprime `etapa: <stage>` (regex `etapa:\s*<nome>`).

**AC-03** — "base" = primeira execução **com nota** (`quality.total`) registrada na rodada. `run record` com
`quality.total` diferente → exit ≠0, mensagem contém `L02`, nada gravado em `runs.jsonl`. Exceção: existe evento
`oracle change` com timestamp posterior ao da base (o teste usa ≥1,1 s de separação). `oracle change` anterior à base
não desculpa.

**AC-04(a)** — `gate` e `preauth` exigem stdin tty (e `/dev/tty`); sem tty → **exit 2**, nada gravado. Num tty o
comando imprime uma linha `DESAFIO: <palavras>` (regex `DESAFIO:[ \t]*([^\r\n]+)`), lê uma linha e só grava se ela
for idêntica ao desafio; desafio aleatório (duas chamadas dão desafios diferentes). Errou → exit ≠0, nada gravado.
`--simulated` sem tty: pode ser recusado OU gravado, mas nunca pode satisfazer `gate:X` em `require` (hoje
`chk_require` aceita simulado como aprovado — é furo). Nenhuma variável de ambiente dispensa o tty; o teste tenta
`AC_TEST_TTY, AC_ALLOW_NONTTY, AC_FORCE_TTY, AC_TEST, AC_SKIP_TTY, AC_TTY_BYPASS, AC_HUMAN, AC_INTERACTIVE, CI`.
*Escolha documentada:* o caminho de terminal é testado com `pty.fork()` (pseudo-terminal real, o teste lê o desafio
e redigita). Por isso não há variável de teste alguma; o corretor não deve criar uma.

**AC-04(b)** — `scripts/hook_aprovacao.py`: lê o payload PreToolUse (JSON na stdin). Bloqueia = exit 2, ou stdout JSON
com `hookSpecificOutput.permissionDecision: "deny"` (ou legado `decision: "block"`). Permite = exit 0 sem deny.
Bloqueia `ac.py … gate|preauth` e `co.py … approve`, com e sem `agent_id`, inclusive: caminho absoluto/`~`/`./`,
`python3 -m ac`, aspas em qualquer token, `sh -c`/`bash -c`, `;`, `&&`, `|`, quebra de linha, `AC=…; python3 "$AC"`,
`$AC`/`${AC}` não resolvidos, `python3 -c '…runpy.run_path(ac.py)…'`. Permite: comandos alheios, `echo gate`,
`python3 other.py gate`, `ac.py status|check|done|run record` (inclusive via `"$AC"`), `co.py status`, e ferramentas
não-Bash (ex.: Read).

**AC-04(c)** — `hook_aprovacao.py --selftest` → exit 0 (payloads sintéticos positivos e negativos internos).

**AC-04(d)** — cada aprovação bem-sucedida (`gate`, `preauth`) acrescenta 1 linha JSON em `$AC_AUDIT_LOG`
(padrão sugerido: `~/.claude/auto-correcao/audit.jsonl`) com campos `cmd` (`gate`|`preauth`), `name`, `decision`
(gate), `by`, `work` (realpath da campanha), `user` (usuário do SO), `tty` (ttyname), `ts`. `AC_AUDIT_LOG` é só
CAMINHO; se resolver para dentro do `--work` da campanha → recusa (exit ≠0, nada gravado).

**L17** — `references/licoes.json5` ganha `{id: "L17", …}` cujo texto contém "campanha", "disjunt" e
sobrep/simult/concorr/paralel, com `evidencia` e `regra`. Novo subcomando
`ac.py --work A overlap --other B` (`--other` repetível): compara os `scope` de A com os de B como caminhos absolutos
(`target` + glob) **e** o `scope` de A com os arquivos de oráculo congelados de B; colisão → **exit 1** citando o
glob; disjunto → 0. Mesmos globs em alvos diferentes não colidem.

## Testes que passam hoje

Nenhum (27/27 falham, ver `base.txt`). Os casos positivos de controle (ex.: execução pós-correção com `decision`
fecha a remedição; `done` que falha não avança) passam hoje isoladamente, por isso foram fundidos no mesmo teste do
caso negativo — cada teste falha hoje pela trava ausente, não por erro de fixture. Conferido: cada falha da base é a
asserção do requisito (ver mensagens), nenhuma é ERROR. O helper de pty foi validado à parte com um script falso
que imprime `DESAFIO:` (redigitação certa → 0; errada → ≠0).

## Tensão a decidir (escalar ao tech-lead)

AC-04(a) quebra a regressão literal: 5 testes de `test_ac.py` chamam `gate`/`preauth` em processo via `ac.main()`
sem tty (`GatesTest.test_stop_criterion_needs_human_gate`, `RequisitoModeTest`, `PreauthTest`,
`PlanTest.test_disjoint_plan_ok_and_product_decision_needs_gate`, `LockBypassTest.test_change_requires_prior_freeze_and_round_resets_gates`).
Manter `ac.main()` sem exigência de tty seria bypass (`python3 -c "import ac; ac.main([...'gate'...])"`).
Recomendação: o corretor migra só essas chamadas para fixture de estado (gravar `gates`/`preauth` no state.json, como
este oráculo faz) ou para o helper de pty, preservando a intenção de cada teste; o integrador confere que nenhuma
outra asserção mudou.

Fixtures deste oráculo gravam `state.json` direto (gates, `done`) para chegar às etapas sem passar pelo canal humano;
se a v0.3 introduzir integridade do estado (hash/cadeia), essas fixtures precisarão do mesmo ajuste.
