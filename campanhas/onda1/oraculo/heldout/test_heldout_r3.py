"""HELD-OUT da rodada 3 (onda 1) — oráculo O1. Variações dos achados R3-3..R3-9 que o construtor não vê."""
import json
import os
import sys
import unicodedata
import unittest

VIS = os.path.realpath(os.path.join(os.environ["CO_SKILL_DIR"], "tests", "onda1") if os.environ.get("CO_SKILL_DIR")
                       else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "tests", "onda1"))  # projeto: campanhas/onda1/oraculo/heldout -> raiz
sys.path.insert(0, VIS)
from _comum import HookBase, bash, json5_load, maquina, payload, sha_file, sub  # noqa: E402
from test_a_estado import EstadoBase  # noqa: E402
from test_r2_achados import R2Base  # noqa: E402
import test_r3_achados as V3  # noqa: E402
from test_r3_achados import recadeia  # noqa: E402


class HeldoutR3Hook(HookBase):
    def test_R3_4_caixa_por_outras_ferramentas(self):
        w = self.ws
        for p in [sub(payload("Grep", {"pattern": "x", "path": os.path.join(w, "Oraculo", "HeldOut")})),
                  payload("Edit", {"file_path": os.path.join(w, "APROVACOES", "stop-1.json"), "old_string": "a",
                                   "new_string": "b"}),
                  sub(payload("Glob", {"pattern": os.path.join(w, "ORACULO", "heldout", "**")})),
                  bash("cp /tmp/x.json %s/.Construcao/state.json" % w)]:
            with self.subTest(p=str(p)[:160]):
                self.assertBloqueia(p)

    def test_R3_4_unicode_nfd_no_caminho_do_ws(self):
        nfc = unicodedata.normalize("NFC", "construção")
        ws2 = os.path.join(self.tmp, nfc)
        os.makedirs(os.path.join(ws2, ".construcao"))
        open(os.path.join(ws2, ".construcao", "ledger.jsonl"), "w").close()
        self.write_json(os.path.join(ws2, "oraculo", "heldout", "casos", "C-01.json"), {"id": "h"})
        nfd = os.path.join(self.tmp, unicodedata.normalize("NFD", "construção"), "oraculo", "heldout", "casos",
                           "C-01.json")
        self.assertBloqueia(sub(payload("Read", {"file_path": nfd})))
        self.assertBloqueia(payload("Write", {"file_path": os.path.join(
            self.tmp, unicodedata.normalize("NFD", "construção"), ".construcao", "state.json"), "content": "{}"}))

    def test_R3_9_git_variacoes(self):
        w = self.ws
        for c in ["git -C %s cat-file -p :oraculo/heldout/casos/C-01.json" % w,
                  "git --git-dir=%s/.git --work-tree=%s diff --no-index /dev/null %s/oraculo/heldout/casos/C-01.json"
                  % (w, w, w)]:
            with self.subTest(cmd=c):
                self.assertBloqueia(sub(bash(c)))


class HeldoutR3Estado(EstadoBase):
    def test_R3_3_cache_substituido_por_objeto_vazio(self):
        L = self.init()
        for i in range(3):
            self.co("ev", "nota", "--texto", "n%d" % i)

        def f(recs):
            del recs[-1]
        recadeia(L, f)
        with open(os.path.join(self.ws, ".construcao", "state.json"), "w") as fh:
            fh.write("{}")
        self.assertEqual(self.co("status", "--json")[0], 1)

    def test_R3_7_zera_em_dentro_do_ciclo(self):
        m = maquina()
        m["contadores"]["tentativas"]["zera_em"] = list(m["contadores"]["tentativas"].get("zera_em") or []) + \
            ["fronteira_vazia"]
        f = self.write_json(os.path.join(self.tmp, "m.json"), m)
        code, out, err = self.co("maquina", "check", "--machine", f, "--nivel", "obra")
        self.assertEqual(code, 1, out + err)
        self.assertIn("I4", out + err)


class HeldoutR3Premissas(V3.TestR3_5HashDoMotor):
    def test_R3_5_hash_antigo_legitimo_apos_mudar_a_obra(self):
        L = self._premissas()
        velho = sha_file(os.path.join(self.ws, "obra.json5"))
        p = os.path.join(self.ws, "obra.json5")
        o = json5_load(p)
        o["pedido"] = "pedido trocado depois"
        self.write_json(p, o)
        f = self.write_json(os.path.join(self.tmp, "pl.json"), {"obra_hash": velho})
        antes = L.raw()
        code, out, err = self.co("ev", "premissas_ok", "--payload", f)
        if code == 0:
            pl = [r for r in L.records() if r["evento"] == "premissas_ok"][-1]["payload"]
            self.assertEqual(pl.get("obra_hash"), sha_file(p))
        else:
            self.assertEqual(L.raw(), antes)

    test_R3_5_premissas_ok_ignora_ou_recusa_hash_do_payload = None
    test_R3_5_premissas_ok_sem_payload_grava_hash_do_disco = None


class HeldoutR3Portao(R2Base):
    def test_R3_6_suites_que_imitam_runner(self):
        for cmd in ("%s -c \"print('Ran 7 tests'); print(); print('OK')\"" % sys.executable,
                    "echo '3 passed in 0.10s'"):
            with self.subTest(cmd=cmd):
                self.tearDown()
                self.setUp()
                self.ledger_coerente(suite=cmd)
                code, r, item, out = self.portao("G1")
                self.assertIn(item["G1"]["status"], ("FAIL", "ERRO"), out)

    def test_R3_8_gaming_variacoes(self):
        for src in ("import unittest\n\n\nclass T(unittest.TestCase):\n    def t(self):\n        self.assertTrue(True)\n",
                    "from sys import exit\n\n\ndef soma(a, b):\n    exit(0)\n"):
            with self.subTest(src=src[:40]):
                self.tearDown()
                self.setUp()
                self.wfile("src/core.py", src)
                self.commit()
                self.assertReprova("G4")


if __name__ == "__main__":
    unittest.main()
