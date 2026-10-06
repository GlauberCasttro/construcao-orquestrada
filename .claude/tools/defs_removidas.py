#!/usr/bin/env python3
"""defs_removidas.py <limpa_dir> <repo> <skill_rel> <arquivo.py>...
Para cada .py existente em HEAD, lista def/class (qualificadas) presentes em HEAD e ausentes na versão
da cópia limpa. Exit 1 se alguma foi removida (regra do portão: nada some sem decisão)."""
import ast
import os
import subprocess
import sys


def nomes(src):
    out = set()

    def visita(no, pref):
        for c in ast.iter_child_nodes(no):
            if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                q = pref + c.name
                out.add(q); visita(c, q + ".")
            else:
                visita(c, pref)
    visita(ast.parse(src), "")
    return out


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__); return 0
    limpa, repo, rel, files = argv[1], argv[2], argv[3], argv[4:]
    ruim = 0
    for f in files:
        if not f.endswith(".py"):
            continue
        path = (rel + "/" + f) if rel else f
        r = subprocess.run(["git", "-C", repo, "show", "HEAD:" + path], capture_output=True, text=True)
        if r.returncode != 0:
            print("novo (não existe em HEAD): " + f); continue
        atual = os.path.join(limpa, f)
        if not os.path.exists(atual):
            print("REMOVIDO o arquivo inteiro: " + f); ruim += 1; continue
        try:
            antes, depois = nomes(r.stdout), nomes(open(atual, encoding="utf-8").read())
        except SyntaxError as e:
            print("ERRO de sintaxe em %s: %s" % (f, e)); ruim += 1; continue
        for n in sorted(antes - depois):
            print("REMOVIDO %s: %s" % (f, n)); ruim += 1
        if not (antes - depois):
            print("ok (%d defs/classes preservadas): %s" % (len(antes), f))
    return 1 if ruim else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
