"""Q2 — portões/veredito. O núcleo G0/G1/G3/G4 é forçado a PASS por monkeypatch (simula uma obra cujo núcleo
passa) para isolar a decisão de veredito; `portao run` é o cmd_portao real (grava gate-report + portao_relatorio)
e o veredito é o `co.py veredito` real."""
import json
import os
import unittest

from _base import Base

RUN = r'''
import argparse, json, os, co_portao as P, co_estado as E
ws = %(ws)r
P.gerar_regressao(ws, "cli")
p = os.path.join(ws, "regressao.json5")
reg = json.load(open(p))
for it in reg["itens"]:
    if it["id"] not in ("G0", "G1", "G3", "G4") and %(editar)r:
        it["aplica"], it["na_motivo"] = False, "orquestrador marcou N/A"
json.dump(reg, open(p, "w"))
PASS = lambda gid: P._res(gid, "PASS", 0, "x", "ok", None)
P.g0_oraculo_intacto = lambda ws, recs=None: PASS("G0")
P.g1_suites = lambda ws, obra=None, d=None: PASS("G1")
P._g_diff_portao = lambda ws, obra, gid, recs: PASS(gid)
rc = P.cmd_portao(argparse.Namespace(acao="run", work=ws, final=True, only=None))
rep = json.load(open(os.path.join(ws, "gate-report.json")))
print("RC=%%s VEREDITO=%%s ENTREGA=%%s" %% (rc, rep["veredito"],
      E.relatorio_satisfaz_entrega(rep, ws, E.ler_ledger(ws))[0]))
'''


class Portao(Base):
    def _run(self, editar=True):
        self.init(tipo="cli")
        with open(os.path.join(self.alvo, "main.py"), "w") as fh:
            fh.write("print(1)\n")
        rc, out, err = self.in_proc(RUN % {"ws": self.ws, "editar": editar})
        self.assertEqual(rc, 0, out + err)
        return out.strip().splitlines()[-1]

    def test_controle_regressao_gerada_da_nogo(self):
        self.assertIn("VEREDITO=NO-GO", self._run(editar=False))

    def test_regressao_editada_sem_waiver_vira_na_e_da_go(self):
        """contrato.sem_waiver = G0,G1,G3,G4,G5,G7,G13; calcular_veredito só força o núcleo G0/G1/G3/G4
        (co_portao.py:1267) e aceita G5/G7/G13 'NA' se regressao.json5 (gravável pelo orquestrador; o hash de
        plano_ok é o do que estiver no disco) disser aplica:false ⇒ GO e entrega satisfeita sem G5/G7/G13."""
        linha = self._run(editar=True)
        rc, out, err = self.run_co("veredito", "--json")
        v = json.loads(out)["veredito"] if out.strip() else err
        self.assertEqual(v, "NO-GO", "portao run: %s | co.py veredito => %r (exit %d)" % (linha, v, rc))

    def test_relatorio_obsoleto_continua_go(self):
        """gate-report grava sistema_hash, mas veredito/veredito_go_final não o comparam com o alvo atual: o
        produto muda depois do portão e o veredito segue GO."""
        self._run(editar=True)
        with open(os.path.join(self.alvo, "main.py"), "w") as fh:
            fh.write("raise SystemExit('quebrado depois do portao')\n")
        rc, out, err = self.run_co("veredito", "--json")
        v = json.loads(out)["veredito"] if out.strip() else err
        self.assertEqual(v, "NO-GO", "alvo alterado após o portão e `co.py veredito` => %r (exit %d)" % (v, rc))


if __name__ == "__main__":
    unittest.main()
