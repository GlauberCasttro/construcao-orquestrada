#!/usr/bin/env bash
# carimbo.sh — imprime a âncora real do estado: branch, HEAD, versão, campanha, sujos, data.
#   carimbo.sh               âncora completa
#   carimbo.sh --brief       3-5 linhas (hook SessionStart)
#   carimbo.sh --write-resume  reescreve o bloco entre <!-- carimbo:begin --> e <!-- carimbo:end --> do RESUME.md
#   carimbo.sh --json        saída em JSON
set -u
. "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"
mode=full
case "${1:-}" in
  -h|--help) sed -n '2,6p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0;;
  --brief) mode=brief;; --write-resume) mode=write;; --json) mode=json;; "") ;;
  *) die "opção desconhecida: $1 (veja --help)";;
esac

data="$(date +%Y-%m-%dT%H:%M:%S%z)"
branch="(sem git)"; head="-"; ultimo="-"; sujos_t=0; sujos_u=0; lista=""
if [ -n "$REPO" ]; then
  branch="$(git -C "$REPO" symbolic-ref --short -q HEAD 2>/dev/null || git -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo '?')"
  head="$(git -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo '?')"
  ultimo="$(git -C "$SKILL_DIR" log -1 --format='%h %s' -- . 2>/dev/null || echo '?')"
  st="$(git -C "$SKILL_DIR" status --short -- . 2>/dev/null | grep -v '__pycache__' || true)"
  if [ -n "$st" ]; then
    sujos_u="$(printf '%s\n' "$st" | grep -c '^??' || true)"
    sujos_t="$(printf '%s\n' "$st" | grep -vc '^??' || true)"
    lista="$(printf '%s\n' "$st" | head -8)"
  fi
fi
versao="sem arquivo VERSION"
if [ -f "$SKILL_DIR/VERSION" ]; then versao="$(head -1 "$SKILL_DIR/VERSION")"
elif [ -f "$SKILL_DIR/SKILL.md" ]; then
  v="$(sed -n 's/^version:[[:space:]]*//p' "$SKILL_DIR/SKILL.md" | head -1)"; [ -n "$v" ] && versao="$v"
fi
camp="nenhuma"; camp_status=""
if [ -f "$STATE/CAMPANHA_ATIVA" ]; then
  c="$(head -1 "$STATE/CAMPANHA_ATIVA" | sed "s|^~|$HOME|")"
  if [ -n "$c" ] && [ "$c" != "nenhuma" ]; then
    camp="$c"
    if [ -d "$c" ] && [ -f "$AC" ]; then
      camp_status="$(python3 "$AC" --work "$c" status 2>&1 | sed -n '2,3p' | cut -c1-160 | tr '\n' ' ')"
    else camp_status="(diretório da campanha ou ac.py ausente)"; fi
  fi
fi
pausadas="$(python3 "$HD_TOOLS/frente.py" status --json 2>/dev/null | python3 -c 'import sys,json
try: print(", ".join(f["nome"] for f in json.load(sys.stdin)["pausadas"]) or "nenhuma")
except Exception: print("?")')"

if [ "$mode" = json ]; then
  python3 - "$data" "$branch" "$head" "$ultimo" "$versao" "$camp" "$camp_status" "$sujos_t" "$sujos_u" <<'PY'
import json, sys
k = ["data","branch","head","ultimo_commit_skill","versao","campanha","campanha_status","sujos_tracked","sujos_untracked"]
d = dict(zip(k, sys.argv[1:]))
for x in ("sujos_tracked","sujos_untracked"): d[x] = int(d[x])
print(json.dumps(d, ensure_ascii=False))
PY
  exit 0
fi

out="carimbo $SKILL_NAME · $data
branch $branch @ $head (repo $(basename "${REPO:-?}")) · último commit da skill: $ultimo
versão: $versao
campanha ativa: $camp ${camp_status} · frentes pausadas: $pausadas
arquivos sujos na skill: $sujos_t modificados, $sujos_u não versionados"
if [ "$mode" != brief ] && [ -n "$lista" ]; then out="$out
$lista"; fi

case "$mode" in
  brief) printf '%s\n' "[harness-dev] $out" ;;
  write)
    f="$STATE/RESUME.md"; [ -f "$f" ] || die "RESUME.md não existe: $f"
    python3 - "$f" "$out" <<'PY'
import sys, re
f, out = sys.argv[1], sys.argv[2]
t = open(f, encoding="utf-8").read()
b, e = "<!-- carimbo:begin -->", "<!-- carimbo:end -->"
if b not in t or e not in t: sys.exit("marcadores do carimbo ausentes no RESUME.md")
new = b + "\n```\n" + out + "\n```\n" + e
t = re.sub(re.escape(b) + r".*?" + re.escape(e), lambda m: new, t, flags=re.S)
open(f, "w", encoding="utf-8").write(t)
print("carimbo gravado em", f)
PY
    ;;
  *) printf '%s\n' "$out" ;;
esac
