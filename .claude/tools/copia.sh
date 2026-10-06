#!/usr/bin/env bash
# copia.sh — cria a cópia de trabalho de uma frente: git archive HEAD da skill -> campanhas/work/<frente>/
#   copia.sh <frente> [--com-untracked] [--dry-run]
# --com-untracked também copia os arquivos NÃO versionados da skill (sem .claude/, campanhas/, local/, __pycache__),
# guardando a base deles em campanhas/work/<frente>.base/ (para o merge de 3 vias do portar.sh).
# A cópia não leva campanhas/, local/ nem dist/ (oráculos são passados ao portão por --oraculo).
# Nunca sobrescreve uma cópia existente. Imprime o caminho da cópia.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"
frente=""; untracked=0; dry=0
while [ $# -gt 0 ]; do case "$1" in
  -h|--help) sed -n '2,8p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0;;
  --com-untracked) untracked=1;; --dry-run) dry=1;;
  -*) die "opção desconhecida: $1";; *) [ -z "$frente" ] && frente="$1" || die "argumento extra: $1";;
esac; shift; done
[ -n "$frente" ] || die "uso: copia.sh <frente> [--com-untracked] [--dry-run]"
valid_frente "$frente"; need_repo
dest="$WS/work/$frente"; base="$WS/work/$frente.base"
[ -e "$dest" ] && die "a cópia já existe: $dest (não sobrescrevo; use outro nome de frente ou remova você mesmo)"
untr=()
if [ "$untracked" = 1 ]; then
  while IFS= read -r -d '' f; do
    fora_da_copia "$f" && continue
    untr+=("$f")
  done < <(git -C "$SKILL_DIR" ls-files --others --exclude-standard -z -- .)
fi
if [ "$dry" = 1 ]; then
  echo "[dry-run] criaria $dest a partir de git archive $HEAD_TREE de $REPO"
  echo "[dry-run] arquivos não versionados a copiar: ${#untr[@]}"; for f in ${untr[@]+"${untr[@]}"}; do echo "  $f"; done
  exit 0
fi
mkdir -p "$dest" "$WS/work"
arquivar | tar -x -C "$dest" || die "git archive falhou"
if [ "${#untr[@]}" -gt 0 ]; then
  mkdir -p "$base"
  for f in "${untr[@]}"; do
    mkdir -p "$dest/$(dirname "$f")" "$base/$(dirname "$f")"
    cp -p "$SKILL_DIR/$f" "$dest/$f"; cp -p "$SKILL_DIR/$f" "$base/$f"
  done
  echo "copiados ${#untr[@]} arquivos não versionados (base em $base)" >&2
fi
echo "$dest"
