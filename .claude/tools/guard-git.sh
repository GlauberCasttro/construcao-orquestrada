#!/usr/bin/env bash
# guard-git.sh — hook PreToolUse(Bash): lê o payload JSON do hook na stdin e nega git destrutivo
# (reset --hard, checkout --/., restore, clean -f, stash, push, add -A/--all/. na raiz, commit -a/--amend,
# branch -D, rebase). A lógica fica em guard_git.py (testável). Falha FECHADA: payload ilegível => nega.
#   guard-git.sh --help
if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  sed -n '2,5p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0
fi
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/guard_git.py"
