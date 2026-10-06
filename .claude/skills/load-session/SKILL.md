---
name: load-session
description: Retoma o desenvolvimento da skill construcao-orquestrada — imprime o carimbo real (branch, HEAD, sujos, campanha), lê RESUME e WORKFLOW e mostra o status da campanha ativa. Use ao abrir o Claude nesta pasta ou quando perguntarem "onde paramos".
---
# load-session

Fina: só chama scripts e lê o state. Não altera nada.

1. `bash .claude/tools/carimbo.sh` — âncora real (nunca a de memória).
2. `python3 .claude/tools/frente.py check` e `status` — frente(s) ativa(s), pausadas, últimas entregas.
3. Leia `.claude/state/RESUME.md` e `.claude/state/WORKFLOW.md`; se houver campanha ativa:
   `python3 .claude/tools/ac/ac.py --work <campanha> status` (motor embutido).
4. Se o carimbo do RESUME difere do carimbo de agora (HEAD/sujos), diga: o RESUME está velho; confie no carimbo.
5. Resuma ao founder em 5 linhas: estado, frente ativa, próximo passo do BACKLOG, bloqueios. Não inicie trabalho.
