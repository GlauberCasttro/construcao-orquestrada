#!/usr/bin/env python3
"""log-sessao.py — acrescenta UMA linha ao state/logs/sessoes.jsonl (append-only, nunca reescreve).

  log-sessao.py --evento {load,save,front-open,front-close,decisao,nota} --resumo TXT [--frente NOME] [--dry-run]
Grava ts (relógio do sistema), branch, HEAD curto e a(s) frente(s) ativa(s) lidas do WORKFLOW.md.
  log-sessao.py --tail [N]      mostra as últimas N linhas (padrão 5)
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
STATE = os.environ.get("HARNESS_STATE") or os.path.join(HERE, "..", "state")
LOG = os.path.join(STATE, "logs", "sessoes.jsonl")


def git(*a):
    try:
        r = subprocess.run(["git", "-C", HERE] + list(a), capture_output=True, text=True, timeout=15)
        return r.stdout.strip() if r.returncode == 0 else "?"
    except Exception:
        return "?"


def ativas():
    try:
        sys.path.insert(0, HERE)
        import frente
        return [f["nome"] for f in frente.carregar()[1]["ativas"]]
    except SystemExit:
        return []
    except Exception:
        return []


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--evento", choices=["load", "save", "front-open", "front-close", "decisao", "nota"])
    ap.add_argument("--resumo"); ap.add_argument("--frente"); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--tail", nargs="?", const=5, type=int)
    a = ap.parse_args()
    if a.tail is not None:
        if os.path.exists(LOG):
            for l in open(LOG, encoding="utf-8").read().splitlines()[-a.tail:]:
                print(l)
        return 0
    if not a.evento or not a.resumo:
        ap.error("--evento e --resumo são obrigatórios")
    reg = {"ts": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "evento": a.evento,
           "resumo": a.resumo, "frente": a.frente, "frentes_ativas": ativas(),
           "branch": git("rev-parse", "--abbrev-ref", "HEAD"), "head": git("rev-parse", "--short", "HEAD")}
    linha = json.dumps(reg, ensure_ascii=False)
    if a.dry_run:
        print("[dry-run] " + linha); return 0
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linha + "\n")
    print("log: " + linha)
    return 0


if __name__ == "__main__":
    sys.exit(main())
