---
name: new-front
description: Abre uma frente de evolução da skill construcao-orquestrada — cria a campanha auto-correcao (um --scope por glob) e registra a frente no WORKFLOW. Uma frente ativa por vez, salvo paralelas declaradas sem colisão.
disable-model-invocation: true
---
# new-front <nome> <objetivo>

Fina: chama scripts; os portões humanos continuam do founder (senha só no terminal dele).

1. `python3 .claude/tools/frente.py check` e `status` — se há frente ativa, pare (ou declare `--paralela` em TODAS,
   após `ac.py --work <dir> overlap`).
2. Campanha: `python3 .claude/tools/ac/ac.py --work campanhas/<nome> init ...` (motor embutido)
   com um `--scope` por glob do que a frente toca (caminho do ac.py LITERAL; nunca `$VAR` junto de aprovação).
3. `python3 .claude/tools/frente.py open <nome> --campanha <dir> --objetivo "<texto>" [--paralela] --dry-run`,
   depois sem `--dry-run`.
4. Oráculo: peça a um agente SEPARADO; congelar com `oracle freeze`. Gerar `aprovar-<nome>.sh` para o founder rodar.
5. `bash .claude/tools/copia.sh <nome>` (`--com-untracked` se a frente precisa de arquivo não versionado) e `log-sessao.py --evento front-open`.
