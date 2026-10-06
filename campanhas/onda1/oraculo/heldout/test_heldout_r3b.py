"""HELD-OUT da medição M2 (propriedades) — oráculo O1. Variações das classes de defeito de test_r3_propriedades que
o construtor não vê: integridade por campo de transição, precedência de guardas, audit, destrutivo em ancestral,
erro interno, relatório parcial, função veredito e hash_estado de estado anterior."""
import json
import os
import sys
import unittest

VIS = os.path.realpath(os.path.join(os.environ["CO_SKILL_DIR"], "tests", "onda1") if os.environ.get("CO_SKILL_DIR")
                       else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "tests", "onda1"))  # projeto: campanhas/onda1/oraculo/heldout -> raiz
sys.path.insert(0, VIS)
from _comum import Base, CO, HookBase, Ledger, bash, py_call, sub  # noqa: E402
from test_a_estado import EstadoBase  # noqa: E402
from test_r2_achados import R2Base  # noqa: E402
import test_r3_propriedades as P  # noqa: E402


class HeldoutR3bIntegridade(EstadoBase):
    def _caso(self, fn):
        L = self.init()
        L.ate_premissas()
        self.assertEqual(self.co("ev", "nota", "--texto", "n")[0], 0)
        P.forja(self.ws, fn)
        return L

    def test_transicao_com_de_ou_ator_adulterados(self):
        def de(recs):
            for r in recs:
                if r["evento"] == "iniciar":
                    r["de"] = "PLANO"

        def ator(recs):
            for r in recs:
                if r["evento"] == "iniciar":
                    r["ator"] = "humano"

        def evento(recs):
            for r in recs:
                if r["evento"] == "iniciar":
                    r["evento"] = "pular_para_entrega"
        for nome, fn in (("de", de), ("ator", ator), ("evento", evento)):
            with self.subTest(campo=nome):
                self.tearDown()
                self.setUp()
                self._caso(fn)
                self.assertEqual(self.co("status", "--json")[0], 1)


class HeldoutR3bGuardas(Base):
    exige = (CO,)

    def test_precedencia_variacoes(self):
        casos = [("a or not b and c", {"a": False, "b": False, "c": True}, True),
                 ("a or not b and c", {"a": False, "b": True, "c": True}, False),
                 ("not not a", {"a": True}, True),
                 ("((a))", {"a": False}, False),
                 ("x == 3 or y != 2", {"x": 1, "y": 2}, False),
                 ("x == 3 or y != 2", {"x": 3, "y": 2}, True),
                 ("a and (b or c) and not d", {"a": True, "b": False, "c": True, "d": False}, True)]
        code, out, err = py_call(self.env, "import co_estado, json\ncasos = %r\n"
                                 "print(json.dumps([co_estado.avaliar_guarda(g, c) for g, c, _ in casos]))" % casos)
        self.assertEqual(code, 0, out + err)
        self.assertEqual(json.loads(out), [c[2] for c in casos])


class HeldoutR3bHook(HookBase):
    def test_audit_por_outras_rotas(self):
        aud = self.audit
        os.makedirs(os.path.dirname(aud), exist_ok=True)
        open(aud, "a").close()
        for c in ("echo x | tee -a %s" % aud, "python3 -c \"open('%s','a').write('x')\"" % aud,
                  "cp /tmp/x.jsonl %s" % aud, "sed -i '' '1d' %s" % aud):
            with self.subTest(cmd=c):
                self.assertBloqueia(sub(bash(c)))

    def test_destrutivo_em_ancestral_por_outras_rotas(self):
        fundo = os.path.join(self.tmp, "x", "y", "obra2")
        os.makedirs(os.path.join(fundo, ".construcao"))
        x = os.path.join(self.tmp, "x")
        for c in ("find %s -delete" % x, "rm -r %s/y" % x,
                  "python3 -c \"import shutil; shutil.rmtree('%s')\"" % x):
            with self.subTest(cmd=c):
                self.assertBloqueia(bash(c))


class HeldoutR3bCli(EstadoBase):
    def test_erro_interno_variacoes(self):
        self.init()
        m = os.path.join(self.tmp, "m.json")
        with open(m, "w") as fh:
            fh.write("[]")
        with open(os.path.join(self.ws, "PLANO.json5"), "w") as fh:
            json.dump({"tasks": 5}, fh)
        for argv in (("maquina", "check", "--machine", m), ("diff", "T-01", "--base", "HEAD", "--repo", self.alvo)):
            with self.subTest(argv=argv):
                code, out, err = self.co(*argv)
                self.assertNotEqual(code, 0, out + err)
                self.assertNotIn("Traceback", out + err)


class HeldoutR3bPortao(R2Base):
    def test_only_com_todo_o_nucleo_continua_parcial(self):
        self.ledger_coerente()
        self.co("portao", "run", "--only", "G0,G1,G3,G4", "--final")
        with open(os.path.join(self.ws, "gate-report.json")) as fh:
            self.assertIs(json.load(fh)["final"], False)

    def test_veredito_funcao_com_waiver(self):
        self.ledger_coerente()
        from test_c_portao import waiver_aprovado
        self.relatorio_completo(mudancas=waiver_aprovado(self, "G2"))
        code, out, err = py_call(self.env, "import co_portao\nprint(co_portao.veredito(%r))" % self.ws)
        self.assertEqual(out.strip().splitlines()[-1], "GO (com waiver)", out + err)


class HeldoutR3bHashEstado(EstadoBase):
    def test_hash_estado_de_estado_anterior_e_recusado(self):
        L = self.init()
        L.ate_ah_stop()
        h = self.status()["hash_estado"]
        L.append("teto_recuado", payload={"de": 5, "para": 3, "seq_limite_uso": 1})
        self.assertNotEqual(self.status()["hash_estado"], h)
        antes = L.raw()
        ap = {"portao": "stop", "decisao": "aprovado", "arquivo": "/x", "hash_estado": h, "usuario_so": "t",
              "ttyname": "/dev/ttys0"}
        code, out, err = py_call(self.env, (
            "import co_estado\ntry:\n    co_estado.transicionar(%r, 'aprovado', _humano={'payload_aprovacao': %r, "
            "'hash_estado': %r})\n    print('GRAVOU')\nexcept Exception as e:\n    print('RECUSOU')\n")
            % (self.ws, ap, h))
        self.assertIn("RECUSOU", out, out + err)
        self.assertEqual(L.raw(), antes)


if __name__ == "__main__":
    unittest.main()
