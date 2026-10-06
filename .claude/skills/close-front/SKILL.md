---
name: close-front
description: Fecha uma frente de evolução da skill construcao-orquestrada — portão verde, conferir-commit, commit só dos arquivos da frente, registro da campanha auto-correcao, frase conferir pelo humano e arquivamento no WORKFLOW.
disable-model-invocation: true
---
# close-front <nome>

Fina: só encadeia scripts. Nunca fabrique aprovação; `frase conferir` e senhas são do founder, no terminal.

1. `bash .claude/tools/portao.sh <nome> [--oraculo DIR:MOD]... -- <arquivos>` deve terminar `VERDE` (leia `portao.out`).
2. `bash .claude/tools/portar.sh <nome> -- <arquivos>` (conflito para tudo) e
   `bash .claude/tools/conferir-commit.sh <nome> -- <arquivos>` (exit 0 obrigatório).
3. Commit só desses arquivos: `git add <um a um>`, mensagem em arquivo, `git commit -F <arquivo>`. Sem push.
4. Campanha (`python3 .claude/tools/ac/ac.py`, caminho literal): `front report`, `done ...`, `run record --decision`, `decision`/`report`,
   `done decisao`. AC-09: se o `run record` caiu no mesmo segundo do `done`, registre de novo.
5. O founder roda `frase conferir` no terminal dele.
6. `python3 .claude/tools/frente.py close <nome> --commit <hash>` e `log-sessao.py --evento front-close`.
