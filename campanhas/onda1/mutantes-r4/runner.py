#!/usr/bin/env python3
"""Oráculo congelado contra a skill em $HOME/.claude/skills/construcao-orquestrada.
Uso: runner.py HELDOUT_DIR SAIDA.json [--failfast] [--rapido|--gerado|--tudo]
 --rapido: heldout + tests/onda1 (sem gerado); --gerado: só tests/onda1/gerado; --tudo: os três."""
import io, json, os, sys, time, unittest
held, out = sys.argv[1], sys.argv[2]
ff = "--failfast" in sys.argv
modo = "--gerado" if "--gerado" in sys.argv else ("--tudo" if "--tudo" in sys.argv else "--rapido")
vis = os.path.realpath(os.path.expanduser("~/.claude/skills/construcao-orquestrada/tests/onda1"))
ger = os.path.join(vis, "gerado")
sys.path.insert(0, vis); sys.path.insert(0, held)
blocos = []
if modo in ("--rapido", "--tudo"):
    blocos += [("heldout", held, "test_heldout_*.py"), ("visiveis", vis, "test_*.py")]
if modo in ("--gerado", "--tudo"):
    blocos += [("gerado", ger, "test_*.py")]
res_all = {}; killed = False
for nome, d, pat in blocos:
    if killed and ff:
        break
    if nome == "gerado":
        sys.path.insert(0, ger)
    suite = unittest.TestLoader().discover(d, pattern=pat, top_level_dir=d)
    t0 = time.time(); buf = io.StringIO()
    r = unittest.TextTestRunner(stream=buf, verbosity=0, failfast=ff).run(suite)
    fal = sorted({t.id() for t, _ in r.failures + r.errors})
    # subtests: failures carry the subtest id
    res_all[nome] = {"rodados": r.testsRun, "falhas": len(r.failures), "erros": len(r.errors),
                     "pulados": len(r.skipped), "falharam": fal[:20], "s": round(time.time() - t0, 1)}
    if fal or r.testsRun == 0 or r.skipped:
        killed = True
res_all["morto"] = killed
json.dump(res_all, open(out, "w"), indent=1)
