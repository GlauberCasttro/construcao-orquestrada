#!/usr/bin/env python3
"""guard-entrega.py — hook PreToolUse(Edit|Write|NotebookEdit): lê o payload JSON na stdin.

Nega editar o PRODUTO da skill (tudo dentro de <skill>/ exceto .claude/state/**, campanhas/** e local/**).
Permite fora da skill e nas zonas livres: campanhas/ (oráculos de campanha, cópias de trabalho em
campanhas/work/, portões) e local/ (notas privadas desta máquina, fora do git). Payload ilegível ou sem
caminho => nega (falha fechada). Se a skill estiver DENTRO de campanhas/work/<frente>/ (cópia de trabalho),
o guard não se aplica (a cópia é o lugar de editar). Limite honesto: só cobre Edit/Write/NotebookEdit; escrita
por Bash (sed -i, redirecionamento) NÃO é interceptada por este guard.
  python3 guard-entrega.py --help
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.realpath(os.path.join(HERE, "..", ".."))  # <skill>/
STATE = os.path.join(ROOT, ".claude", "state")
LIVRES = (os.path.join(".claude", "state"), "campanhas", "local")  # zonas editáveis dentro da skill
MSG = ("O produto desta skill só muda pelo fluxo de entrega: new-front (campanha auto-correcao) -> "
       "tools/copia.sh <frente> (cópia em campanhas/work/<frente>/, edite lá) -> tools/portao.sh -> "
       "tools/portar.sh -> tools/conferir-commit.sh -> commit só dos arquivos da frente. "
       "Editáveis aqui: .claude/state/**, campanhas/**, local/**. Veja .claude/CLAUDE.md.")


def _within(path, base):
    try:
        return os.path.commonpath([path, base]) == base
    except ValueError:
        return False


def em_copia_de_trabalho(root=None):
    root = root or ROOT
    pai = os.path.dirname(root)
    avo = os.path.basename(os.path.dirname(pai))
    return os.path.basename(pai) == "work" and (avo == "campanhas" or avo.endswith("-workspace"))


def decide(payload, cwd=None, root=None, state=None):
    """Retorna (allow: bool, motivo: str)."""
    root = root or ROOT
    state = state or os.path.join(root, ".claude", "state")
    if em_copia_de_trabalho(root):
        return True, "cópia de trabalho"
    if not isinstance(payload, dict):
        return False, "payload não é um objeto JSON"
    ti = payload.get("tool_input")
    if not isinstance(ti, dict):
        return False, "payload sem tool_input"
    fp = ti.get("file_path") or ti.get("notebook_path")
    if not isinstance(fp, str) or not fp.strip():
        return False, "payload sem file_path/notebook_path"
    base = payload.get("cwd") if isinstance(payload.get("cwd"), str) and payload.get("cwd") else (cwd or os.getcwd())
    p = os.path.realpath(os.path.join(base, os.path.expanduser(fp)))
    if not _within(p, root):
        return True, "fora da skill"
    if _within(p, state):
        return True, ".claude/state"
    for z in LIVRES[1:]:
        if _within(p, os.path.join(root, z)):
            return True, z
    return False, "arquivo do produto da skill: " + p


def main(argv):
    if len(argv) > 1 and argv[1] in ("-h", "--help"):
        print(__doc__); return 0
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except Exception as e:
        payload, err = None, "payload JSON ilegível (%s)" % e
    else:
        err = None
    ok, why = (False, err) if err else decide(payload)
    if not ok:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny",
            "permissionDecisionReason": "guard-entrega (harness-dev): " + why + ". " + MSG}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
