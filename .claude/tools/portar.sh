#!/usr/bin/env bash
# portar.sh — leva os arquivos da frente da cópia de trabalho para a skill VIVA.
#   portar.sh <frente> [--src DIR] [--dry-run] -- <arquivo>...
# Por arquivo: base = versão de HEAD (ou campanhas/work/<frente>.base/ para não versionados).
#   vivo == base        -> copia a versão da frente
#   vivo == frente      -> nada a fazer
#   vivo mudou (outra sessão) -> merge de 3 vias (git merge-file) em temporário; limpo -> aplica;
#                          conflito -> NÃO toca o vivo, grava o resultado com marcas em
#                          campanhas/work/<frente>.conflitos/ e sai com exit 1.
#   vivo existe, sem base e diferente -> para (não há como mesclar).
# Nada é apagado. Depois: tools/conferir-commit.sh e commit só dos arquivos da frente.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"
frente=""; src=""; dry=0; files=()
while [ $# -gt 0 ]; do case "$1" in
  -h|--help) sed -n '2,13p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0;;
  --src) [ $# -ge 2 ] || die "--src precisa de DIR"; src="$2"; shift;; --dry-run) dry=1;;
  --) shift; files=("$@"); break;;
  -*) die "opção desconhecida: $1";; *) [ -z "$frente" ] && frente="$1" || die "argumento extra: $1";;
esac; shift; done
[ -n "$frente" ] || die "uso: portar.sh <frente> -- <arquivos>"
valid_frente "$frente"; need_repo
[ "${#files[@]}" -gt 0 ] || die "lista de arquivos vazia"
[ -n "$src" ] || src="$WS/work/$frente"
[ -d "$src" ] || die "origem não existe: $src"
bdir="$WS/work/$frente.base"; cdir="$WS/work/$frente.conflitos"
conf=0; tmpd="$(mktemp -d "${TMPDIR:-/tmp}/portar.XXXXXX")"
trap 'rm -rf "$tmpd"' EXIT
for f in "${files[@]}"; do
  valid_rel "$f"
  [ -f "$src/$f" ] || { echo "ERRO: arquivo ausente na cópia de trabalho: $f"; conf=$((conf+1)); continue; }
  vivo="$SKILL_DIR/$f"; base="$tmpd/base"; : > "$base"; tembase=0
  if git -C "$REPO" cat-file -e "$HEAD_TREE/$f" 2>/dev/null; then git -C "$REPO" show "$HEAD_TREE/$f" > "$base"; tembase=1
  elif [ -f "$bdir/$f" ]; then cp "$bdir/$f" "$base"; tembase=1; fi
  if [ ! -e "$vivo" ]; then acao="criar"
  elif cmp -s "$vivo" "$src/$f"; then echo "igual (nada a fazer): $f"; continue
  elif [ "$tembase" = 1 ] && cmp -s "$vivo" "$base"; then acao="copiar"
  elif [ "$tembase" = 1 ]; then acao="merge"
  else echo "CONFLITO (vivo existe, sem base para mesclar): $f"; conf=$((conf+1)); continue; fi
  if [ "$dry" = 1 ]; then echo "[dry-run] $acao: $f"; continue; fi
  case "$acao" in
    criar|copiar) mkdir -p "$(dirname "$vivo")"; cp -p "$src/$f" "$vivo"; echo "$acao: $f";;
    merge)
      cp "$vivo" "$tmpd/merged"
      if git merge-file -L vivo -L base -L frente "$tmpd/merged" "$base" "$src/$f" 2>/dev/null; then
        cp "$tmpd/merged" "$vivo"; echo "merge limpo (3 vias): $f"
      else
        mkdir -p "$cdir/$(dirname "$f")"; cp "$tmpd/merged" "$cdir/$f"
        echo "CONFLITO no merge: $f (vivo intocado; marcas em $cdir/$f)"; conf=$((conf+1))
      fi;;
  esac
done
[ "$conf" -eq 0 ] || { echo "PORTAR: $conf arquivo(s) com problema — resolva e rode de novo"; exit 1; }
echo "PORTAR: ok"
