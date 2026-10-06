#!/usr/bin/env bash
# portao.sh — portão em cópia limpa: HEAD da skill + SÓ os arquivos da frente, suítes nos 2 Pythons.
#   portao.sh <frente> [--src DIR] [--oraculo DIR:MOD]... [--timeout S] [--dry-run] -- <arquivo>...
# --src      de onde vêm os arquivos da frente (padrão: a cópia de trabalho campanhas/work/<frente>/)
# --oraculo  oráculo externo: DIR com o módulo unittest MOD (ex.: campanhas/revisao-v4:test_estado). Roda com
#            CO_SKILL_DIR = cópia LIMPA e HOME falso cujo ~/.claude/skills/<skill> é a cópia limpa (o oráculo
#            testa o que está no portão); CO_AC_DIR = a auto-correcao (irmã, instalada ou o motor embutido).
# --timeout  limite por suíte em segundos (padrão 1800; 0 = sem limite)
# Arquivos: lista EXPLÍCITA, relativa à skill (zsh não faz word-split de $VAR: passe os arquivos literais).
# Suítes: cada pasta sob tests/ (e .claude/tools/tests/) com test*.py, em python3 E /usr/bin/python3.
# Também confere que nenhum def/class de arquivo .py sumiu em relação ao HEAD.
# Saída incremental em campanhas/portao-<frente>/portao.out (termina em FIM) e portao.json.
# Exit 0 só se TUDO verde. O portão reporta o estado real; não esconde vermelho.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"
frente=""; src=""; dry=0; tmo=1800; oraculos=(); files=()
while [ $# -gt 0 ]; do case "$1" in
  -h|--help) sed -n '2,13p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0;;
  --src) [ $# -ge 2 ] || die "--src precisa de DIR"; src="$2"; shift;;
  --oraculo) [ $# -ge 2 ] || die "--oraculo precisa de DIR:MOD"; oraculos+=("$2"); shift;;
  --timeout) [ $# -ge 2 ] || die "--timeout precisa de segundos"; tmo="$2"; shift;;
  --dry-run) dry=1;;
  --) shift; files=("$@"); break;;
  -*) die "opção desconhecida: $1";; *) [ -z "$frente" ] && frente="$1" || die "argumento extra antes de --: $1";;
esac; shift; done
[ -n "$frente" ] || die "uso: portao.sh <frente> [--src DIR] [--oraculo DIR:MOD]... -- <arquivos>"
valid_frente "$frente"; need_repo
[ "${#files[@]}" -gt 0 ] || die "lista de arquivos vazia (passe os arquivos da frente depois de --)"
for f in "${files[@]}"; do valid_rel "$f"; done
[ -n "$src" ] || src="$WS/work/$frente"
[ -d "$src" ] || die "origem dos arquivos não existe: $src (rode tools/copia.sh $frente)"
src="$(cd "$src" && pwd -P)"
for f in "${files[@]}"; do [ -f "$src/$f" ] || die "arquivo da frente não existe em $src: $f"; done
for o in ${oraculos[@]+"${oraculos[@]}"}; do
  case "$o" in *:*) [ -d "${o%%:*}" ] || die "dir do oráculo não existe: ${o%%:*}";; *) die "--oraculo precisa de DIR:MOD, recebi '$o'";; esac
done
out="$WS/portao-$frente"; limpa="$out/limpa"
if [ "$dry" = 1 ]; then
  echo "[dry-run] portão '$frente': limpa=$limpa (HEAD $HEAD_TREE + ${#files[@]} arquivos de $src)"
  for f in "${files[@]}"; do echo "  arquivo: $f"; done
  for o in ${oraculos[@]+"${oraculos[@]}"}; do echo "  oráculo: $o"; done
  echo "[dry-run] pythons: python3 ($(python3 --version 2>&1)) e /usr/bin/python3 ($(/usr/bin/python3 --version 2>&1))"
  exit 0
fi
mkdir -p "$out"
here="$HD_TOOLS"

portao() {
  echo "PORTAO $frente · $(date +%Y-%m-%dT%H:%M:%S%z) · HEAD $(git -C "$REPO" rev-parse --short HEAD)"
  case "$limpa" in */portao-"$frente"/limpa) rm -rf "$limpa";; *) die "caminho inesperado: $limpa";; esac
  mkdir -p "$limpa"
  arquivar | tar -x -C "$limpa" || die "git archive falhou"
  for f in "${files[@]}"; do mkdir -p "$limpa/$(dirname "$f")"; cp -p "$src/$f" "$limpa/$f"; done
  echo "limpa montada: HEAD + ${#files[@]} arquivos"
  res="$out/resultados.tsv"; : > "$res"
  falhas=0

  echo "--- def/class removidos vs HEAD"
  if python3 "$here/defs_removidas.py" "$limpa" "$REPO" "$SKILL_REL" "${files[@]}"; then
    printf 'defs-removidas\t-\t0\tok\n' >> "$res"
  else
    printf 'defs-removidas\t-\t1\tFALHOU\n' >> "$res"; falhas=$((falhas+1))
  fi

  suites=()
  while IFS= read -r d; do suites+=("$d"); done < <(cd "$limpa" && find tests .claude/tools/tests -type d ! -name __pycache__ 2>/dev/null | sort | while read -r d; do
    ls "$d"/test*.py >/dev/null 2>&1 && echo "$d"; done)
  [ "${#suites[@]}" -gt 0 ] || echo "(nenhuma suíte de teste encontrada na cópia limpa)"
  for py in python3 /usr/bin/python3; do
    for d in ${suites[@]+"${suites[@]}"}; do
      tmp="$out/_suite.tmp"
      (cd "$limpa" && PYTHONDONTWRITEBYTECODE=1 python3 "$here/_runlimit.py" "$tmo" -- "$py" -m unittest discover -s "$d") > "$tmp" 2>&1
      rc=$?
      ran="$(sed -n 's/^Ran \([0-9]*\) test.*/\1/p' "$tmp" | tail -1)"; last="$(tail -1 "$tmp" | cut -c1-80)"
      echo "--- suíte $py $d: rc=$rc · $ran testes · $last"
      [ "$rc" -ne 0 ] && tail -12 "$tmp" | sed 's/^/    /'
      printf 'suite:%s\t%s\t%s\t%s testes; %s\n' "$d" "$py" "$rc" "${ran:-?}" "$last" >> "$res"
      [ "$rc" -ne 0 ] && falhas=$((falhas+1))
    done
  done

  if [ "${#oraculos[@]}" -gt 0 ]; then
    fh="$out/home"; case "$fh" in */portao-"$frente"/home) rm -rf "$fh";; *) die "caminho inesperado: $fh";; esac
    mkdir -p "$fh/.claude/skills"
    ln -s "$limpa" "$fh/.claude/skills/$SKILL_NAME"
    acd=""
    for c in "$(dirname "$SKILL_DIR")/auto-correcao" "$HOME/.claude/skills/auto-correcao" "$limpa/.claude/tools/ac"; do
      [ -f "$c/scripts/ac.py" ] && { acd="$(cd "$c" && pwd -P)"; break; }
    done
    [ -n "$acd" ] && ln -s "$acd" "$fh/.claude/skills/auto-correcao"
    for o in "${oraculos[@]}"; do
      odir="${o%%:*}"; omod="${o#*:}"
      for py in python3 /usr/bin/python3; do
        tmp="$out/_suite.tmp"
        (cd "$limpa" && HOME="$fh" CO_SKILL_DIR="$limpa" CO_AC_DIR="$acd" PYTHONPATH="$odir" REV_PY="$py" PYTHONDONTWRITEBYTECODE=1 python3 "$here/_runlimit.py" "$tmo" -- "$py" -m unittest "$omod") > "$tmp" 2>&1
        rc=$?
        ran="$(sed -n 's/^Ran \([0-9]*\) test.*/\1/p' "$tmp" | tail -1)"; last="$(tail -1 "$tmp" | cut -c1-80)"
        echo "--- oráculo $py $omod: rc=$rc · $ran testes · $last"
        [ "$rc" -ne 0 ] && tail -12 "$tmp" | sed 's/^/    /'
        printf 'oraculo:%s\t%s\t%s\t%s testes; %s\n' "$omod" "$py" "$rc" "${ran:-?}" "$last" >> "$res"
        [ "$rc" -ne 0 ] && falhas=$((falhas+1))
      done
    done
  fi
  rm -f "$out/_suite.tmp"

  veredito=VERDE; [ "$falhas" -gt 0 ] && veredito=VERMELHO
  python3 - "$out" "$frente" "$veredito" "$falhas" "$(git -C "$REPO" rev-parse HEAD)" "${files[@]}" <<'PY'
import json, sys
out, frente, ver, falhas, head, *files = sys.argv[1:]
rows = [l.rstrip("\n").split("\t") for l in open(out + "/resultados.tsv")]
json.dump({"frente": frente, "veredito": ver, "falhas": int(falhas), "head": head, "arquivos": files,
           "resultados": [{"item": r[0], "python": r[1], "rc": int(r[2]), "resumo": r[3]} for r in rows]},
          open(out + "/portao.json", "w"), ensure_ascii=False, indent=1)
PY
  echo "PORTAO $frente: $veredito ($falhas falha(s)) — resumo em $out/portao.json"
  echo "FIM"
  [ "$falhas" -eq 0 ]
}
portao 2>&1 | tee "$out/portao.out"
exit "${PIPESTATUS[0]}"
