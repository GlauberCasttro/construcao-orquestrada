#!/usr/bin/env bash
# conferir-commit.sh — antes do commit: cada arquivo VIVO tem de ser idêntico (cmp) ao que o portão testou.
#   conferir-commit.sh <frente> -- <arquivo>...
# Exit 0 se todos idênticos; exit 1 e lista os que diferem/faltam (regra: só entra no commit o que o portão testou).
set -u
. "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"
frente=""; files=()
while [ $# -gt 0 ]; do case "$1" in
  -h|--help) sed -n '2,5p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0;;
  --) shift; files=("$@"); break;;
  -*) die "opção desconhecida: $1";; *) [ -z "$frente" ] && frente="$1" || die "argumento extra: $1";;
esac; shift; done
[ -n "$frente" ] || die "uso: conferir-commit.sh <frente> -- <arquivos>"
valid_frente "$frente"
[ "${#files[@]}" -gt 0 ] || die "lista de arquivos vazia"
limpa="$WS/portao-$frente/limpa"
[ -d "$limpa" ] || die "não há cópia de portão para '$frente' ($limpa): rode tools/portao.sh antes"
ruim=0
for f in "${files[@]}"; do
  valid_rel "$f"
  if [ ! -f "$SKILL_DIR/$f" ]; then echo "FALTA no vivo: $f"; ruim=$((ruim+1))
  elif [ ! -f "$limpa/$f" ]; then echo "NÃO TESTADO (ausente na cópia do portão): $f"; ruim=$((ruim+1))
  elif ! cmp -s "$SKILL_DIR/$f" "$limpa/$f"; then echo "DIFERE do portão: $f"; ruim=$((ruim+1))
  else echo "ok: $f"; fi
done
if [ "$ruim" -gt 0 ]; then echo "CONFERIR: $ruim arquivo(s) fora do que o portão testou — não commitar"; exit 1; fi
echo "CONFERIR: ok (${#files[@]} arquivos idênticos ao portão)"
