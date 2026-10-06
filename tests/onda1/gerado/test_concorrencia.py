"""test_concorrencia.py — escritores concorrentes no ledger/estado (A11: append, cache e RETOMAR.md sob a mesma trava).
Oráculo O1-gerado. Cada cenário roda N ≥ 20 vezes, num workspace novo por repetição, com dois processos que
começam juntos (barreira por relógio):
  * append × append (API append_evento e CLI `ev nota` misturados);
  * transição × append, e a MESMA transição disputada pelos dois (só um grava);
  * `aprovar` num pty (desafio redigitado) × processo gravando notas.
Invariantes conferidos ao fim de cada repetição: cadeia válida (formatos.ledger.hash.verificar_cadeia), nenhum seq
duplicado/lacuna, nenhuma escrita perdida (toda escrita que saiu 0 está no ledger), cache = fold (status sem aviso),
RETOMAR.md no último registro.
"""
import json
import os
import subprocess
import sys
import time
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
ONDA1 = os.path.dirname(AQUI)
for _p in (AQUI, ONDA1):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import motor as m  # noqa: E402
from _comum import (CABECALHO_RETOMAR, CO, SCRIPTS, Base, Ledger, cadeia_problemas, run_tty)  # noqa: E402

N = int(os.environ.get("GERADO_N_CONC", "20"))

DRIVER = r'''
import json, os, sys, time, subprocess
sys.path.insert(0, %(scripts)r)
import co_estado
ws, t0, modo, k, tag = sys.argv[1], float(sys.argv[2]), sys.argv[3], int(sys.argv[4]), sys.argv[5]
while time.time() < t0:
    time.sleep(0.001)
ok = []
for i in range(k):
    texto = "%%s-%%d" %% (tag, i)
    if modo == "api":
        try:
            co_estado.append_evento(ws, "nota", "script", {"texto": texto})
            ok.append(texto)
        except Exception as e:
            print("ERRO", type(e).__name__, e, file=sys.stderr)
    elif modo == "cli":
        p = subprocess.run([sys.executable, %(co)r, "--work", ws, "ev", "nota", "--texto", texto],
                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode == 0:
            ok.append(texto)
        elif b"Traceback" in p.stderr:
            print("TRACEBACK", p.stderr.decode()[-500:], file=sys.stderr)
    elif modo == "pausa":  # limite_uso + retomar (transições reais da máquina) k vezes
        for ev, pl in (("limite_uso", {"causa": "outro", "retomar_apos": "2020-01-01T00:00:00Z", "mensagem": "m"}),
                       ("retomar", {})):
            try:
                co_estado.transicionar(ws, ev, pl)
                ok.append(ev)
            except (co_estado.Fail, co_estado.Bad) as e:
                print("RECUSA", ev, e, file=sys.stderr)
    elif modo == "disputa":  # a mesma transição pelos dois processos
        try:
            co_estado.transicionar(ws, "fronteira_vazia", {})
            ok.append("fronteira_vazia")
        except (co_estado.Fail, co_estado.Bad) as e:
            pass
print(json.dumps(ok))
'''


class TestConcorrencia(Base):
    def driver(self, modo, k, tag, t0):
        code = DRIVER % {"scripts": SCRIPTS, "co": CO}
        return subprocess.Popen([sys.executable, "-c", code, self.ws, repr(t0), modo, str(k), tag],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env,
                                universal_newlines=True, cwd=self.tmp)

    def colher(self, p):
        out, err = p.communicate(timeout=300)
        self.assertNotIn("Traceback", err, err[-800:])
        self.assertNotIn("TRACEBACK", err, err[-800:])
        return json.loads(out.strip().splitlines()[-1]), err

    def fresh(self):
        self.tearDown()
        self.setUp()

    def obra_em(self, spec):
        L = self.init()
        for p in m.rota_obra(spec):
            if p["k"] == "op":
                L.append(p["evento"], payload=p["payload"], chave=p.get("chave"))
            elif p["k"] == "h":
                L.humano(p["portao"], p["evento"], p["para"])
                ap = [x for x in L.records() if x["evento"] == "aprovacao"][-1]
                os.makedirs(os.path.dirname(self.audit), exist_ok=True)
                with open(self.audit, "a") as fh:
                    fh.write(json.dumps({"ts": ap["ts"], "tipo": "aprovacao", "cmd": "aprovar",
                                         "name": ap["payload"]["portao"], "decision": ap["payload"]["decisao"],
                                         "by": "humano", "work": self.ws, "user": "t", "tty": "/dev/ttys0",
                                         "seq": ap["seq"], "hash_estado": ap["payload"]["hash_estado"]}) + "\n")
            else:
                L.append(p["evento"], ator=p["ator"], nivel=p["nivel"], de=p["de"], para=p["para"],
                         task=p.get("task"), chave=p.get("chave"), payload=p["payload"])
        code, out, err = self.co("ev", "nota", "--texto", "sync")
        self.assertEqual(code, 0, out + err)
        return L

    def invariantes(self, L, notas_ok=(), rep=0):
        recs = L.records()
        self.assertEqual(cadeia_problemas(recs), [], "rep %d: cadeia quebrada" % rep)
        seqs = [r["seq"] for r in recs]
        self.assertEqual(seqs, list(range(1, len(recs) + 1)), "rep %d: seq duplicado/lacuna" % rep)
        textos = {r["payload"].get("texto") for r in recs if r["evento"] == "nota"}
        perdidas = [t for t in notas_ok if t not in textos]
        self.assertEqual(perdidas, [], "rep %d: escrita perdida" % rep)
        code, out, err = self.co("status", "--json")
        self.assertEqual(code, 0, "rep %d: %s" % (rep, err[-400:]))
        self.assertNotIn("diverg", err.lower(), "rep %d: cache ≠ fold depois da concorrência" % rep)
        with open(os.path.join(self.ws, "RETOMAR.md"), encoding="utf-8") as fh:
            mm = CABECALHO_RETOMAR.search(fh.readline())
        self.assertTrue(mm and int(mm.group(1)) == recs[-1]["seq"] and mm.group(2) == recs[-1]["hash"],
                        "rep %d: RETOMAR.md fora do último registro" % rep)
        return json.loads(out)

    def test_append_x_append(self):
        for rep in range(N):
            with self.subTest(rep=rep):
                self.fresh()
                L = self.init()
                n0 = len(L.records())
                t0 = time.time() + 0.4
                ps = [self.driver("api", 15, "A", t0), self.driver("api", 15, "B", t0), self.driver("cli", 4, "C", t0)]
                oks = []
                for p in ps:
                    ok, _err = self.colher(p)
                    oks += ok
                self.assertEqual(len(oks), 34, "rep %d: alguma escrita recusada sob concorrência" % rep)
                self.invariantes(L, oks, rep)
                self.assertEqual(len(L.records()), n0 + len(oks))

    def test_transicao_x_append(self):
        for rep in range(N):
            with self.subTest(rep=rep):
                self.fresh()
                L = self.obra_em("LOTE")
                t0 = time.time() + 0.4
                p1, p2 = self.driver("api", 12, "N", t0), self.driver("pausa", 3, "P", t0)
                notas, _ = self.colher(p1)
                trans, err2 = self.colher(p2)
                self.assertEqual(trans, ["limite_uso", "retomar"] * 3, "rep %d: %s" % (rep, err2[-400:]))
                st = self.invariantes(L, notas, rep)
                self.assertEqual(len(notas), 12)
                self.assertEqual((st["obra"]["estado"], st["contadores"]["pausas"]), ("LOTE", 3))

    def test_mesma_transicao_disputada(self):
        for rep in range(N):
            with self.subTest(rep=rep):
                self.fresh()
                L = self.obra_em("LOTE")
                t0 = time.time() + 0.4
                ps = [self.driver("disputa", 1, "X", t0), self.driver("disputa", 1, "Y", t0),
                      self.driver("api", 6, "N", t0)]
                res = [self.colher(p)[0] for p in ps]
                self.assertEqual(len(res[0]) + len(res[1]), 1, "rep %d: a mesma transição gravou %d vezes" % (
                    rep, len(res[0]) + len(res[1])))
                st = self.invariantes(L, res[2], rep)
                self.assertEqual(st["obra"]["estado"], "INTEGRAR")
                self.assertEqual(sum(1 for r in L.records() if r["evento"] == "fronteira_vazia"), 1)

    def test_aprovar_pty_x_append(self):
        for rep in range(N):
            with self.subTest(rep=rep):
                self.fresh()
                L = self.obra_em("AH:stop")
                t0 = time.time() + 0.05 + (rep % 5) * 0.08  # varia o ponto de colisão com o desafio
                p = self.driver("api", 10, "N", t0)
                code, out, ch = run_tty(["--work", self.ws, "aprovar", "stop", "--decisao", "aprovado"], self.env)
                notas, _ = self.colher(p)
                self.assertEqual(code, 0, "rep %d: aprovar falhou sob notas concorrentes: %s" % (rep, out[-600:]))
                st = self.invariantes(L, notas, rep)
                self.assertEqual(len(notas), 10)
                self.assertEqual(st["obra"]["estado"], "ORACULO")
                recs = L.records()
                aps = [r for r in recs if r["evento"] == "aprovacao"]
                ult = aps[-1]
                self.assertEqual(recs[ult["seq"]]["evento"], "aprovado", "transição humana não colada na aprovação")
                with open(os.path.join(self.ws, "aprovacoes", "stop-%d.json" % ult["seq"])) as fh:
                    arq = json.load(fh)
                self.assertEqual(arq["transicao_seq"], ult["seq"] + 1)
                with open(self.audit) as fh:
                    aud = [json.loads(x) for x in fh if x.strip()]
                self.assertTrue(any(a.get("tipo") == "aprovacao" and a.get("seq") == ult["seq"] for a in aud))


if __name__ == "__main__":
    unittest.main()
