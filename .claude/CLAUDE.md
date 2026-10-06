# construcao-orquestrada — harness de desenvolvimento

Este `.claude/` entrega a EVOLUÇÃO da skill `construcao-orquestrada` (o produto = tudo fora de `.claude/state/`,
`campanhas/` e `local/`). Vale quando o Claude é aberto na raiz do projeto (`cd <projeto> && claude`).
**Markdown explica. Script decide. Nunca fabrique aprovação, execução, contagem ou data.**

## O método (o que a skill ensina, aplicado a ela mesma)
Quem testa não é quem constrói. Testes GERADOS do contrato (decisão do founder, rodada 1 da onda 1); o held-out
fica fora do alcance do construtor e o oráculo só muda por mudança oficial feita pelo autor. Portão humano só com
a senha do founder. Tudo mecânico vira script (`tools/`); as skills do harness são finas e só chamam script.

## Fluxo de entrega (o `.claude/tools/` impõe; este arquivo descreve)
1. `new-front`: campanha no motor EMBUTIDO (`python3 .claude/tools/ac/ac.py --work campanhas/<nome> init`,
   caminho LITERAL, um `--scope` por glob) + `tools/frente.py open`. Uma frente ativa por vez (ou todas `--paralela`).
2. Oráculo por agente SEPARADO, congelado (`oracle freeze`); mudança só oficial (`oracle change --why --evidence`).
   Defeito conhecido: `oracle change --file X` SUBSTITUI a lista inteira — passe TODOS os arquivos do oráculo.
3. Aprovação humana: script `aprovar-<frente>.sh` que o founder roda no terminal com a senha (gate stop, gate
   oracle:requisito, preauth commit, frase conferir). Nunca peça a senha no chat. Nunca aprove pela IA.
4. Corretor (agente) só na cópia de trabalho: `tools/copia.sh <frente>` (cria `campanhas/work/<frente>/`).
5. `tools/portao.sh <frente> -- <arquivos>` (cópia limpa = HEAD + só os arquivos da frente; 2 Pythons; oráculos
   `--oraculo campanhas/<c>/...:MOD`, rodados com `CO_SKILL_DIR` = cópia limpa; nenhum def removido).
6. `tools/portar.sh` -> `tools/conferir-commit.sh` -> commit SÓ dos arquivos da frente (mensagem em arquivo, `-F`).
7. Fechar: `close-front` (ac.py front report/done, run record --decision, decision/report) + `frente.py close`.
Achados de uso real vindos de outras sessões entram como item do BACKLOG/frente; ninguém edita o produto por fora.

## Retomada da onda 1 (primeira frente do BACKLOG)
No projeto a onda 1 está VERSIONADA (primeiro commit, "em andamento"): `scripts/co*.py`, `tests/onda1/**`,
`references/hook-settings.json5`. As suítes estão verdes nos 2 Pythons (veja `state/RESUME.md`); falta a prova
independente (mutação >= 80% + verificador cego NOVOS). Oráculos: `campanhas/onda1/oraculo/heldout/`
(held-out — o construtor não lê) e `campanhas/revisao-v4/`. Confirme o CUSTO com o founder antes de cada rodada de
mutação (leva horas). Decisão pendente CO-1 (portão humano para waiver) muda a onda 0: só o founder decide.

## Git e privacidade
- Repo próprio do projeto (branch `main`). Commit só dos arquivos da frente, listados um a um (`git add <lista>`,
  nunca `-A`/`.`/`commit -a`); mensagem via `git commit -F arquivo` (o hook de aprovação nega texto com
  "approve" + ac.py). Push e criação de remoto: só o humano. Sem stash/reset --hard/clean -f.
- Privacidade: `tools/guard-privacidade.sh` (pre-commit e commit-msg instalados por `--install-hook`; `--log`
  confere o histórico). A lista literal de termos fica em `local/termos-privados.txt`, fora do git.
- Nenhuma senha, token ou caminho absoluto de usuário em arquivo versionado. Comandos em inglês, prosa em português.

## Lições (curtas)
zsh não faz word-split de `$VAR` (passe arquivos literais); mensagem de commit em arquivo; `ac.py` por caminho
literal (o hook de aprovação nega `$VAR` + frase); AC-09: `run record` no mesmo segundo do `done` -> re-registrar;
`oracle change` substitui a lista; conferir commit × portão; máx. 5 agentes (3 se 429); confirmar custo antes de
medição pesada; suítes nos 2 Pythons (`python3` e `/usr/bin/python3`).

## Rituais (skills em `.claude/skills/`)
`load-session` retomar · `save-session` salvar (state + log; commit só do state se o founder pedir) ·
`new-front` abrir · `close-front` fechar. Estado: `state/RESUME.md` (carimbo gerado por `tools/carimbo.sh`),
`WORKFLOW.md`, `BACKLOG.md`, `DECISIONS.md`, `logs/sessoes.jsonl` (append-only).

## Motor de campanhas embutido
`.claude/tools/ac/` = cópia verbatim da auto-correcao (`scripts/`, `references/`) + lançadores `ac.py`,
`frase.py`, `hook_aprovacao.py`; `ORIGEM.txt` tem commit, data e sha256. Não edite: atualizar = recopiar.
O harness NÃO depende de `~/.claude/skills/auto-correcao`. O hook de aprovação embutido está no `settings.json`.

## O que NÃO existe (não alegar proteção inexistente)
- O guard-entrega só cobre Edit/Write/NotebookEdit; escrita por Bash (`sed -i`, `>`) NÃO é interceptada.
- O guard-git lê o texto do comando; não vê scripts que chamam git por dentro nem aliases.
- O hook de aprovação é filtro sintático, não sandbox; a garantia forte é a frase-senha do founder.
- Nada impede o humano de editar o produto fora do Claude; o fluxo é disciplina + portão, não cadeado.
- Não há `publish` nesta skill. Não há CI; o portão é local. O pre-commit de privacidade só existe depois de
  `guard-privacidade.sh --install-hook` em cada clone.
- `PENDENTE.md` na raiz é anterior ao harness; a verdade de estado é `.claude/state/`.
