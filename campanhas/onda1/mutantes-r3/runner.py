#!/usr/bin/env python3
"""Roda oráculo congelado (heldout + visíveis) contra a skill em $HOME/.claude/skills/construcao-orquestrada.
Uso: runner.py HELDOUT_DIR SAIDA.json [--failfast]"""
import io, json, os, sys, time, unittest
held, out = sys.argv[1], sys.argv[2]
ff = "--failfast" in sys.argv
vis = os.path.realpath(os.path.expanduser("~/.claude/skills/construcao-orquestrada/tests/onda1"))
sys.path.insert(0, vis); sys.path.insert(0, held)
res_all = {}
killed = False
for nome, d, pat in (("heldout", held, "test_heldout_*.py"), ("visiveis", vis, "test_*.py")):
    if killed and ff:
        break
    suite = unittest.TestLoader().discover(d, pattern=pat, top_level_dir=d)
    t0 = time.time()
    buf = io.StringIO()
    r = unittest.TextTestRunner(stream=buf, verbosity=0, failfast=ff).run(suite)
    fal = sorted({t.id() for t, _ in r.failures + r.errors})
    res_all[nome] = {"rodados": r.testsRun, "falhas": len(r.failures), "erros": len(r.errors),
                     "pulados": len(r.skipped), "falharam": fal, "s": round(time.time() - t0, 1)}
    if fal or r.testsRun == 0 or r.skipped:
        killed = True
res_all["morto"] = killed
json.dump(res_all, open(out, "w"), indent=1)
