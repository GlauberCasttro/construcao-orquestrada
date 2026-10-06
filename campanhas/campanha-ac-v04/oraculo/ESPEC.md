# Oráculo de aceite — auto-correcao v0.4 (aprovação por FRASE-SENHA do founder)

Autor: escritor do oráculo, separado do corretor (L15). Arquivo: `test_v04_frase.py` (unittest puro, Python 3.9+, `pty`).
Rodar: `python3 -m unittest test_v04_frase -v` nesta pasta. Base de hoje (`base.txt`, contra a v0.4 já implementada): R0..R8 passam (39/39) e **R9LegadoTest falha (8/8)** em `python3` 3.13 e `/usr/bin/python3` 3.9.6/LibreSSL, sem nenhum ERROR. A base original, antes da v0.4, era 38/39 falhando, e o único que passava era o controle do hook `test_hook_allows_reading_about_frase`.

Motivo (decisão do founder): tty + desafio é forjável. Um agente com Python faz `pty.fork`, lê `DESAFIO: NNNN` e
responde, ou importa o módulo e chama a transição. Só um segredo que apenas o founder conhece resolve. O oráculo
usa exatamente o caminho do agente (pty real, espera o prompt e digita). O que separa os dois é só **conhecer a frase**.

Isolamento: `HOME`, `AC_FRASE_FILE` e `AC_AUDIT_LOG` apontam para um temporário por teste. O `~/.claude/auto-correcao/`
real nunca é tocado. Processos "agente" rodam com `start_new_session=True`, ou seja, sem terminal controlador.
`ORACULO_SCRIPTS` (env do processo de teste, nunca repassada ao filho) troca o diretório testado. Existe só para
validar o oráculo contra protótipos e não é interface do ac.py.

## Requisito → testes

| Req | Testes |
|---|---|
| 0 módulo `scripts/frase.py` | `R0ModuloFraseTest.test_canonical_and_tag` · `…test_strength_and_normalization` |
| 1 `frase definir` | `R1FraseDefinirTest.test_definir_stores_only_salt_and_pbkdf2_verifier_mode_0600` · `…test_unknown_kdf_or_weak_iter_refused` · `…test_default_path_is_home_dot_claude` · `…test_confirmation_mismatch_refused` · `…test_weak_phrases_refused` · `…test_definir_requires_tty` · `…test_change_requires_old_phrase` · `…test_password_mode_accepted_and_approves` · `…test_weak_passwords_refused` · `…test_definir_without_work` |
| 2 gate/preauth com frase e tag | `R2AprovacaoComFraseTest.test_gate_with_phrase_records_tag_in_state_ledger_and_audit` · `…test_preauth_with_phrase_records_tag` · `…test_wrong_phrase_exit_nonzero_nothing_recorded` · `…test_no_phrase_defined_refused_with_instruction` · `…test_reject_decision_also_tagged` |
| 3 `frase conferir` pega forja | `R3ConferirTest.test_legit_approvals_confer_and_record_frase_conferida` (controle) · `…test_state_only_forged_gate_caught` · `…test_forged_without_tag_caught` · `…test_forged_random_tag_caught` · `…test_forged_tag_from_wrong_phrase_caught` · `…test_replayed_valid_tag_caught` · `…test_replay_old_round_approval_in_state_caught` · `…test_replay_by_copying_ledger_line_caught` · `…test_forged_frase_conferida_caught` · `…test_audit_line_missing_caught` · `…test_in_audit_but_missing_from_ledger_caught` · `…test_wrong_phrase_at_conferir_refused_nothing_recorded` · `…test_agent_replacing_frase_file_is_caught_by_founder` · `…test_conferir_requires_tty` |
| 4 `done decisao` exige `frase-conferida` | `R4DoneDecisaoTest.test_done_decisao_needs_frase_conferida` · `…test_approval_after_conferida_requires_new_conferida` |
| 5 sem canal alternativo / sem vazamento | `R5SemCanalAlternativoTest.test_frase_flag_refused` · `…test_env_vars_never_supply_phrase` · `…test_piped_stdin_refused_even_with_correct_phrase_and_tty` · `…test_phrase_never_written_anywhere`. Além disso, o `tearDown` de **todo** teste confere que nenhuma saída de terminal contém a frase ou `Traceback`. |
| 6 forja por pty e por import | `R6ForjaTest.test_pty_agent_without_phrase_refused_with_phrase_accepted` · `…test_import_and_call_directly_refused` |
| 7 hook | `R7HookTest.test_hook_denies_frase_commands` (10 comandos × principal/subagente) · `…test_hook_allows_reading_about_frase` (controle) |
| 9 rollout: legado v0.3 (`--assinar-legado`) | `R9LegadoTest.test_definir_records_criada_em` · `…test_conferir_without_flag_lists_legacy_with_instruction` · `…test_assinar_legado_signs_each_then_conferir_passes` · `…test_assinar_legado_wrong_phrase_nothing_recorded` · `…test_untagged_after_criada_em_is_forgery` · `…test_mixed_legacy_and_forgery_signs_nothing` · `…test_backdated_untagged_after_first_tagged_event_refused` · `…test_forged_legado_assinado_caught` |
| 7b hook sem falso positivo (uso real) | `R7bHookUsoRealTest.test_legit_commands_allowed` (10 controles × principal/subagente) · `…test_approvals_still_denied` (10) |
| 8 AC-06 escopo com vírgula | `R8EscopoVirgulaTest.test_comma_glob_refused_or_split` (`'a/**, b/**'` e `'a/**,b/**'`) |

## Interfaces FIXADAS (o corretor segue)

**Módulo compartilhado `~/.claude/skills/auto-correcao/scripts/frase.py`** (stdlib). O `ac.py` importa este módulo. O
`co_estado` da construcao-orquestrada deve importá-lo por importlib, sem copiar o código (fora do escopo deste
oráculo). Funções puras testadas:
- `normalizar(f) -> str` = `unicodedata.normalize("NFC", f.strip())`.
- `problemas_forca(f) -> list[str]`: vazia se ok. Regra vigente desde a mudança oficial de 2026-10-05 (pedido do
  founder: aceitar SENHA além de frase). Com `n = normalizar(f)`, é forte se cumprir as três condições:
  1. `len(n) ≥ 12`;
  2. `len(set(n)) ≥ 6`: anti-repetição, conta caracteres distintos com espaço incluído e vale nos dois modos;
  3. **(a) frase**: `len(n.split()) ≥ 3`, **ou (b) senha**: ≥3 classes entre minúscula (`islower`), maiúscula
     (`isupper`), dígito (`isdigit`) e símbolo (não alfanumérico e não espaço).

  Exemplos:
  - Recusadas: `abcdefghijkl`, `abcdef123456`, `ABCDEF123456`, `abcdef-ghijk` (1–2 classes, 1 palavra),
    `aaaaaaaaaaaa`, `Aa1!Aa1!Aa1!`, `Ab1!Ab1!Ab1!Ab1!`, `aaa aaa aaaaaa`, `abab abab abab` (menos de 6 distintos),
    `Ab1!xyz` (curta).
  - Aceitas: `Lagoa#2026xy`, `Senha.Forte2026`, `lagoa9#serena`, `PEDRA-antiga-77` e frases como
    `lagoa serena de inverno`.

  Listas `FORTES`/`FRACAS` no teste. Prompts e mensagens continuam dizendo "FRASE"; uma senha é uma frase de uma palavra.
- `canonical(work, nome, decisao, seq, estado_hash) -> bytes` =
  `json.dumps({"work","nome","decisao","seq","estado_hash"}, sort_keys=True, separators=(",",":"), ensure_ascii=False).encode("utf-8")`.
- `tag(chave: bytes, work, nome, decisao, seq, estado_hash) -> str` = `hmac.new(chave, canonical(...), sha256).hexdigest()`.

**Arquivo da frase**: `$AC_FRASE_FILE` (só CAMINHO). O padrão é `$HOME/.claude/auto-correcao/frase.json`, modo **0600**.
Conteúdo exato: `{"versao": 1, "kdf": "pbkdf2-sha256", "iter": 600000, "salt_verificador": hex de 16 bytes
aleatórios, "salt_chave": hex de 16 bytes aleatórios e diferente do outro, "verificador": hex}`, com
`verificador = hashlib.pbkdf2_hmac("sha256", normalizar(f).encode("utf-8"), salt_verificador, iter, dklen=32)`.
A frase NUNCA é gravada.

*Mudança oficial (2026-10-05):* o KDF era scrypt e passou a ser PBKDF2. O `/usr/bin/python3` 3.9.6 com LibreSSL não
tem `hashlib.scrypt`, e a skill tem de rodar nos dois Pythons. 600000 iterações é o valor OWASP 2023.

O verificador **recusa** `frase.json` com `kdf` ≠ `"pbkdf2-sha256"`, com `iter` que não seja int ou com `iter < 600000`
(teste `test_unknown_kdf_or_weak_iter_refused`). A recusa vale para gate e conferir: exit ≠0 e nada gravado. Nenhuma
variável de ambiente reduz as iterações. Os testes aceitam o custo de cerca de 0,2 s por derivação e cacheiam no
próprio processo as derivações que eles mesmos fazem.

**Chave das tags**: `K = pbkdf2_hmac("sha256", normalizar(f), salt_chave, iter, dklen=32)`. A comparação é case-sensitive.
Espaços nas pontas são removidos pela normalização.

**Leitura da frase** (todos os comandos): exige stdin tty **e** `/dev/tty`. Sem isso → **exit 2**, nada gravado.
stdin em pipe é recusado mesmo que exista `/dev/tty` (mantém AC-04a). Cada leitura imprime um prompt que contém
`FRASE` em maiúsculas seguido de `:` na mesma linha (regex `FRASE[^\r\n:]*:`), com o **eco já desligado** antes do
prompt. Use `getpass.getpass`, que abre `/dev/tty` e desliga o eco antes de escrever. Nunca use o fallback do getpass
para stdin. Não pode haver outro texto que case com essa regex. A leitura é uma tentativa só, sem nova chance.
Nenhum argumento (`--frase` → erro do argparse, exit 2), nenhuma variável de ambiente (`AC_FRASE`, `AC_PASSPHRASE`,
`FRASE`, `CI`... ver `BYPASS_ENV`) e nenhuma stdin fornece a frase. A frase, certa ou errada, não aparece em saída,
audit, ledger, state nem traceback.

**`ac.py [--work W] frase definir`**: não exige campanha iniciada e **dispensa `--work`** (a frase é do founder, não
da campanha). Todos os outros comandos, inclusive `frase conferir` e `gate`, continuam exigindo `--work`; sem ele →
exit 2. Sem arquivo: 2 prompts (frase, confirmação). Com
arquivo: 3 prompts, nesta ordem: antiga, nova, nova de novo. A antiga errada → exit ≠0 e arquivo byte-idêntico.
Confirmação divergente ou frase fraca → exit ≠0 e nada gravado. Sem tty → exit 2.

**Aprovação (`gate` não simulado, `preauth`)**, nesta ordem: (a) validação de args e `AC_AUDIT_LOG` dentro do `--work`
→ exit 2 **antes** de qualquer prompt (o teste v0.3 `test_audit_log_inside_work_dir_refused` depende disso);
(b) sem tty → exit 2; (c) sem frase definida → exit 2, sem prompt, mensagem com `frase definir`; (d) 1 prompt, frase
errada → **exit 1**, nada gravado; (e) grava. Não existe mais a linha `DESAFIO:`.
Toda aprovação gravada leva `seq`, `estado_hash` e `tag`:
- `seq` = número 1-based da linha do evento em `ledger.jsonl`.
- `estado_hash` = sha256 hex dos bytes do `state.json` imediatamente antes do comando.
- `nome`/`decisao`: gate → `name` / `decision` (`approve` | `reject`); preauth → `name` / `"preauth:" + ",".join(requires)`
  na ordem dada; conferência → `"frase-conferida"` / `"ok"`.
- Ledger: `{"event": "gate"|"preauth"|"frase-conferida", "name", "decision"|"requires", "seq", "estado_hash", "tag", ...}`.
- Audit: os campos da v0.3 (`cmd`, `name`, `decision`, `by`, `work`, `user`, `tty`, `ts`) mais `seq`, `estado_hash` e `tag`.
- State: `gates[name]` e `preauth[name]` ganham `seq` e `tag`.
- Gate `--simulated`: sem tag, continua nunca satisfazendo `gate:X`, e `conferir` o ignora.

**`ac.py --work W frase conferir`**: tty e 1 prompt (frase errada, inclusive contra um `frase.json` trocado → exit ≠0,
nada gravado). Recalcula a tag de toda aprovação da campanha e sai **1** listando o nome de cada problema:
- evento do ledger (gate não simulado, preauth, frase-conferida) sem tag, com tag errada ou com `seq` ≠ posição;
- evento sem linha de audit correspondente (`work`, `seq` e `tag` iguais);
- linha de audit desta campanha ausente do ledger;
- entrada não simulada de `state.gates` ou `state.preauth` cujo (`seq`, `tag`) não seja o evento válido **mais recente**
  daquele nome no ledger. Para portões por rodada (todo gate exceto `stop`), esse evento também tem de ser posterior ao
  último evento `round-new`. Isso pega o reuso de aprovação de rodada anterior.

Tudo ok → grava o evento tagueado `frase-conferida` (ledger e audit) e sai **0**. Com problema → nada gravado. Sem tty → 2.

**`done decisao`**: exige no ledger um `frase-conferida` com `seq` maior que o de toda aprovação não simulada. Senão
→ exit 1 com `frase conferir` na mensagem, e o stage não vira `concluida`. Como `done` não conhece a frase, só confere
a ordem; a autenticidade vem do `frase conferir` do founder, que também reconfere os `frase-conferida` anteriores.

**Hook**: `hook_aprovacao.py` nega `ac.py … frase …` em todas as variantes da v0.3: caminho absoluto, `~`, `./`,
`-m ac`, aspas, `sh -c`, `;`, `|`, `$AC`, `python3 -c runpy`. Permite `grep frase ac.py`, `cat frase.py`,
`echo frase`, `other.py frase`. Os 21 DENY e os 11 ALLOW da v0.3 e o `--selftest` continuam valendo.

**Hook, regra fixada (7b, decisão do autor do oráculo, 2026-10-05).** Nega quando o `ac.py` é **executado** e
o seu **1º argumento posicional**, depois das opções globais (`--work W` ou `--work=W`), é `gate`, `preauth` ou
`frase`. Isso vale também para o `ac.py` executado dentro de `sh -c`, de heredoc entregue a um shell
(`bash -s <<EOF`, `bash <<EOF`, `cat <<EOF | bash`) e de texto canalizado para um shell (`printf '...' | sh`).

Não nega:
- `gate`, `preauth` ou `frase` em outra posição (ex.: `front report frase --file F`, onde é nome de frente);
- texto que não é executado (`printf`/`echo ... > arq`, `git commit -m '...'`, `git commit -F arq`, `grep`);
- `oracle change`, que **não** é aprovação humana: exige `--why`/`--evidence`, fica no ledger e é recalibrável. Não
  foi incluído.

Código entregue a um interpretador (`python3 -c`, `python3 - <<EOF`) que cita `ac.py` junto com
gate/preauth/frase continua negado (falha fechada), pois o hook não sabe se o texto será executado. O caminho
legítimo é gravar o script em arquivo e rodá-lo. Isso é visível no transcript e é o mesmo limite honesto da v0.3.
Base dos controles hoje, nos dois Pythons: 4 dos 20 comandos falham, cada um × principal/subagente (6 subtestes em
`base.txt` e no resumo final; a contagem 8 do quadro abaixo era só a estimativa feita antes de rodar):
- `front report frase` e `front report gate` são negados (falso positivo);
- `printf '...ac.py ... gate...' | sh` não é negado (furo novo).

Os comandos de printf/echo para arquivo, `git commit` e `grep` já passam.

**AC-06**: `init --scope` com vírgula num glob → recusa (exit 2, mensagem cita vírgula ou `,`, nenhum glob com vírgula
gravado) **ou** divide em `["a/**", "b/**"]`. As duas saídas são aceitas.

**Rollout (req. 9, mudança oficial de 2026-10-05).** Campanhas abertas sob a v0.3 têm aprovações sem tag.
- **`criada_em` no `frase.json`:** `frase definir` grava `"criada_em": "YYYY-MM-DDTHH:MM:SSZ"` (UTC, momento da gravação).
- **Legada:** evento de aprovação do ledger (gate não simulado ou preauth) que cumpre as três condições:
  - não tem `tag`;
  - tem `ts` < `criada_em` (comparação de string ISO);
  - está numa linha **anterior ao 1º evento com `tag`** do ledger.

  Qualquer outra aprovação sem tag é forja, inclusive uma retroativa (`ts` antigo) acrescentada depois de um evento
  tagueado.
- **`frase conferir` sem flag com legado pendente:** exit 1, cita cada legada pelo nome e cita `--assinar-legado`.
  Nada gravado.
- **`frase conferir --assinar-legado`:**
  - tty, 1 prompt. Frase errada → exit ≠0, nada gravado. Sem tty → exit 2.
  - Se houver qualquer problema que não seja legado pendente (forja sem tag, tag errada, `legado-assinado` forjado):
    exit 1, cita o nome, **nada é assinado** (nem as legadas legítimas).
  - Senão grava 1 evento humano `legado-assinado`, no ledger e no audit (`cmd`), com:
    - `itens: [{"linha", "nome", "decisao", "ts", "tag"}]` em ordem de linha;
    - `tag` de cada item = `frase.tag(K, work, nome, decisao, linha, "legado:" + ts)`;
    - `seq`, `estado_hash` e `tag` do evento com nome `"legado-assinado"` e decisão `"legado:" + ",".join(linhas)`.
  - Exit 0.
- **Depois de assinar:** `frase conferir` aceita cada legada assinada, cuja entrada v0.3 no state (sem `seq`/`tag`,
  `at` = `ts`) confere, e ignora as linhas v0.3 sem tag do audit dessas legadas. Um `legado-assinado` com tag
  inválida é problema citado como `legado-assinado`.
- **Limite:** um agente pode forjar uma aprovação sem tag com `ts` antigo antes do 1º evento tagueado, numa campanha
  que ainda não tem nenhum. O `--assinar-legado` lista cada item antes de assinar, e o founder decide.

Os testes de senha e de `frase definir` sem `--work` falham na v0.4 implementada hoje, nos dois Pythons
(`base.txt`). Contra um protótipo descartável com a regra acima e `--work` opcional só em `frase definir`, R0 e R1
passam.

## Validação do oráculo (feita, descartável)

Montei um protótipo mínimo numa cópia em scratchpad, sem tocar a skill: `frase.py` e os patches de ac.py e do hook.
Contra ele os **39/39 passam** nos dois Pythons. Mutações do protótipo que o oráculo pega:
- conferir sem checar o state;
- `done` sem trava;
- eco ligado no prompt;
- env fornecendo a frase;
- audit não cruzado;
- tag sem `nome`;
- iter=1000;
- kdf/iter não checados;
- vírgula aceita;
- stdin em pipe aceito;
- troca sem a frase antiga.

Uma mutação escapa, e é equivalente: não checar `seq == posição`. O reuso por cópia de linha já cai na regra
"mais recente e posterior ao round-new". A regra de posição fica como "deve", sem teste discriminante.

## Regressão — MIGRADA (mudança oficial aprovada pelo founder, 2026-10-05)

Os 11 testes abaixo foram migrados para a frase de teste via pty, com a mesma intenção. `_pty_helper.py` agora
digita a frase a cada prompt `FRASE...:` e gera, uma vez por processo, um `frase.json` de teste num
`AC_FRASE_FILE` temporário. Mudanças nos testes:
- `GatesTest` ganhou o caso "frase errada não aprova".
- AC04a: "desafio redigitado" virou "frase", "desafio errado" virou "frase errada recusa, sem auditoria", e
  "desafio varia" virou `test_tag_varies_by_gate_and_seq`.
- AC04d exige `tag` em cada linha e nenhuma linha numa tentativa errada.
- AC02 aprova `stop` pelo canal humano e roda `frase conferir` antes do `done decisao`.

Resultado contra a v0.4 implementada: **49/49 passam em python3 3.13 e em /usr/bin/python3 3.9.6**. A cópia histórica
em `campanha-ac-v03/oraculo/` ficou como estava; a versão viva é a de `scripts/tests/`.
Contra a v0.4 atual, o `test_v04_frase.py` passa em R0..R8 (39) e falha em R9 (8) nos dois Pythons (`base.txt`).
Contra um protótipo descartável do `--assinar-legado`, passa 47/47 nos dois. Mutações pegas:
- sem a regra de posição;
- sem `criada_em`;
- sem checar a tag do item.

### Histórico (antes da migração): 49 testes contra o protótipo, 38 passavam e 11 falhavam

**10 dependem do desafio numérico.** Mudam por mudança oficial (eu, após aprovação do founder): trocar a redigitação
por prompt `FRASE` e definir a frase de teste num `AC_FRASE_FILE` temporário. As intenções se mantêm.
- `test_ac.py`: `GatesTest.test_stop_criterion_needs_human_gate` · `RequisitoModeTest.test_requisito_mode` ·
  `PreauthTest.test_preauth_conditional_and_human` · `PlanTest.test_disjoint_plan_ok_and_product_decision_needs_gate` ·
  `LockBypassTest.test_change_requires_prior_freeze_and_round_resets_gates` (todos via `_pty_helper.run_tty`, que redigita `DESAFIO`).
- `test_v03_oraculo.py`: `AC04aCanalHumanoTest.test_gate_in_tty_with_retyped_challenge` · `…test_gate_in_tty_wrong_challenge_refused` ·
  `…test_preauth_in_tty_with_retyped_challenge` · `…test_challenge_varies_between_calls` · `AC04dAuditoriaTest.test_each_approval_appends_audit_line_outside_work`.

**1 depende do requisito 4, não do desafio** (tensão a decidir):
`test_v03_oraculo.AC02StatusEtapaTest.test_all_done_shows_concluida` fecha `done decisao` só com fixture de state, sem
`frase-conferida`. A recomendação é ajustar a fixture: rodar `frase conferir` por pty antes do `done decisao`, ou
injetar o evento tagueado. A alternativa seria isentar campanhas sem aprovação no ledger, mas isso abre brecha: basta
forjar o portão só no state.

Os testes que forjam o state.json direto (`forge_stop_gate`, `mark_done`) continuam passando em `check`/`done`, porque
estes não validam tag. A forja só é pega no `frase conferir`, e isso é proposital.

## Limites honestos (não testáveis pelo ac.py)

- Um agente pode apagar ou trocar o `frase.json` e definir a própria frase via pty. Daí em diante ele aprova e confere
  "com sucesso" com a frase dele. Só o `frase conferir` digitado pelo **founder** com a frase real denuncia a troca
  (`test_agent_replacing_frase_file_is_caught_by_founder`). O mesmo vale para um `frase-conferida` forjado: `done
  decisao` só vê a ordem, e o próximo `conferir` do founder o rejeita.
- A força real depende da entropia da frase. O PBKDF2 com 600000 iterações só encarece a força bruta offline sobre o `frase.json`,
  que é legível pelo agente.
