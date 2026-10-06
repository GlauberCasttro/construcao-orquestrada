#!/usr/bin/env python3
"""Runner do HELD-OUT da onda 1 (oráculo O1). Rodado pelo integrador (nunca pelo construtor; o hook bloqueia a
leitura deste diretório a construtores).

Uso:  python3 run_heldout.py [-v] [--json SAIDA.json] [--com-visiveis]
  --com-visiveis  também roda tests/onda1 (visíveis) e reporta os dois blocos separados.
Saída: 0 se todos passam; 1 se algum falha/erra; 2 se o diretório de testes visíveis (helpers) não existe.
Python 3.9+, só stdlib.
"""
import argparse
import json
import os
import sys
import time
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
VIS = os.path.realpath(os.path.expanduser("~/.claude/skills/construcao-orquestrada/tests/onda1"))


def rodar(start, pattern, verbosity):
    loader = unittest.TestLoader()
    suite = loader.discover(start, pattern=pattern, top_level_dir=start)
    t0 = time.time()
    res = unittest.TextTestRunner(verbosity=verbosity, stream=sys.stdout).run(suite)
    return {"dir": start, "rodados": res.testsRun, "falhas": len(res.failures), "erros": len(res.errors),
            "pulados": len(res.skipped), "ok": res.wasSuccessful() and res.testsRun > 0,
            "falharam": sorted({t.id() for t, _ in res.failures + res.errors}),
            "segundos": round(time.time() - t0, 1)}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="run_heldout.py")
    ap.add_argument("-v", action="store_true")
    ap.add_argument("--json")
    ap.add_argument("--com-visiveis", action="store_true")
    a = ap.parse_args(argv)
    if not os.path.isfile(os.path.join(VIS, "_comum.py")):
        print("helpers visíveis ausentes em %s" % VIS, file=sys.stderr)
        return 2
    sys.path.insert(0, VIS)
    sys.path.insert(0, AQUI)
    v = 2 if a.v else 1
    blocos = {"heldout": rodar(AQUI, "test_heldout_*.py", v)}
    if a.com_visiveis:
        blocos["visiveis"] = rodar(VIS, "test_*.py", v)
    for nome, b in blocos.items():
        print("[%s] rodados=%d falhas=%d erros=%d pulados=%d ok=%s (%.1fs)"
              % (nome, b["rodados"], b["falhas"], b["erros"], b["pulados"], b["ok"], b["segundos"]))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(blocos, fh, ensure_ascii=False, indent=1)
    return 0 if all(b["ok"] and b["pulados"] == 0 for b in blocos.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
