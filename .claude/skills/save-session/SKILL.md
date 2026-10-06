---
name: save-session
description: Salva o estado do desenvolvimento da skill construcao-orquestrada — atualiza RESUME/WORKFLOW/BACKLOG/DECISIONS com o carimbo gerado por script e acrescenta uma linha ao log append-only. Use ao pausar ou encerrar a sessão.
disable-model-invocation: true
---
# save-session

Muda estado: só por pedido explícito do founder. Só escreve em `.claude/state/`.

1. `python3 .claude/tools/frente.py check` (precisa passar).
2. Edite `RESUME.md` (seções "Onde paramos" e "Próximos passos"; nada de contagem ou data digitada à mão) e, se
   mudou, `BACKLOG.md` e `DECISIONS.md` (decisão nova do founder = `D-nn` com data do sistema, porquê, onde vale).
3. `bash .claude/tools/carimbo.sh --write-resume` — regrava o bloco de carimbo do RESUME.
4. `python3 .claude/tools/log-sessao.py --evento save --resumo "<uma linha>" [--frente NOME]` (use `--dry-run` antes).
5. Commit do state só se o founder pedir: `git add` dos arquivos de `.claude/state/` um a um, mensagem em arquivo (`-F`).
   Sem push.
