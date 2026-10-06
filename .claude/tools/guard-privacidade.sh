#!/usr/bin/env bash
# guard-privacidade.sh — procura termos privados no que pode ir a público. Exit 1 se achar (lista arquivo:linha).
#   guard-privacidade.sh              arquivos versionados + não versionados não ignorados do repositório
#   guard-privacidade.sh --staged     só o conteúdo STAGED (usado pelo pre-commit) + a mensagem, se passada
#   guard-privacidade.sh --log        todo o histórico: git log -p --all (conteúdo e mensagens)
#   guard-privacidade.sh --msg ARQ    também confere a mensagem de commit em ARQ (hook commit-msg)
#   guard-privacidade.sh --install-hook   instala .git/hooks/pre-commit e commit-msg chamando este script
# Termos: local/termos-privados.txt (um por linha, # comenta; NÃO versionado — PRIV_TERMOS troca o arquivo).
# Sem esse arquivo: avisa e usa só os padrões genéricos (caminho do usuário atual, scratch do Claude, e-mails
# de provedores comuns). A lista literal nunca vai para o repositório.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"
modo=arvore; msg=""
while [ $# -gt 0 ]; do case "$1" in
  -h|--help) sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0;;
  --staged) modo=staged;; --log) modo=log;; --install-hook) modo=install;;
  --msg) [ $# -ge 2 ] || die "--msg precisa de ARQ"; msg="$2"; shift;;
  *) die "opção desconhecida: $1 (veja --help)";;
esac; shift; done
need_repo
if [ "$modo" = install ]; then
  hd="$(git -C "$REPO" rev-parse --git-path hooks)"; case "$hd" in /*) ;; *) hd="$REPO/$hd";; esac
  mkdir -p "$hd"
  printf '#!/usr/bin/env bash\nexec bash "$(git rev-parse --show-toplevel)/%s.claude/tools/guard-privacidade.sh" --staged\n' "${SKILL_REL:+$SKILL_REL/}" > "$hd/pre-commit"
  printf '#!/usr/bin/env bash\nexec bash "$(git rev-parse --show-toplevel)/%s.claude/tools/guard-privacidade.sh" --staged --msg "$1"\n' "${SKILL_REL:+$SKILL_REL/}" > "$hd/commit-msg"
  chmod +x "$hd/pre-commit" "$hd/commit-msg"; echo "hooks instalados em $hd (pre-commit, commit-msg)"; exit 0
fi

termos="${PRIV_TERMOS:-$SKILL_DIR/local/termos-privados.txt}"
pat="$(mktemp "${TMPDIR:-/tmp}/privpat.XXXXXX")"; trap 'rm -f "$pat"' EXIT
if [ -f "$termos" ]; then
  grep -v '^[[:space:]]*#' "$termos" | sed '/^[[:space:]]*$/d' | python3 -c 'import re,sys
for l in sys.stdin.read().splitlines(): print(re.escape(l.strip()))' >> "$pat"
else
  echo "AVISO: $termos ausente — só os padrões genéricos (crie-o nesta máquina; ele não é versionado)" >&2
fi
# padrões genéricos (montados por partes para o próprio script não casar consigo)
u="$(id -un 2>/dev/null || echo "${USER:-}")"
{ [ -n "$u" ] && printf '%s\n' "/Users/$u([/\"' ]|$)" "/home/$u([/\"' ]|$)"
  printf '%s\n' "/private/tmp/""claude-" "[A-Za-z0-9._%+-]+@(gmail|hotmail|outlook|yahoo|icloud|live)\.com"; } >> "$pat"

achou=0
checar() { # $1 rótulo; texto na stdin
  local r; r="$(grep -inE -f "$pat" 2>/dev/null | cut -c1-160)"
  if [ -n "$r" ]; then printf '%s\n' "$r" | sed "s|^|$1:|"; achou=1; fi
}
cd "$REPO" || die "repo inacessível"
case "$modo" in
  arvore)
    while IFS= read -r -d '' f; do
      case "$f" in local/*|*/local/*|dist/*) continue;; esac
      [ -f "$f" ] || continue
      grep -Iq . "$f" 2>/dev/null || continue   # binário/vazio
      checar "$f" < "$f"
    done < <(git ls-files -co --exclude-standard -z);;
  staged)
    while IFS= read -r -d '' f; do
      checar "$f" < <(git show ":$f" 2>/dev/null)
    done < <(git diff --cached --name-only -z --diff-filter=ACMR);;
  log)
    if git rev-parse -q --verify HEAD >/dev/null; then checar "git-log" < <(git log -p --all --format='commit %H%n%B'); fi;;
esac
[ -n "$msg" ] && [ -f "$msg" ] && checar "mensagem-de-commit" < "$msg"
if [ "$achou" = 1 ]; then echo "PRIVACIDADE: termo privado encontrado (acima). Nada publicado/commitado com isso." >&2; exit 1; fi
echo "privacidade: ok ($modo)"
