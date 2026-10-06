"""Frente A — co.py dispatcher: o esqueleto de subcomandos de contrato.json5#cli existe, `--help` de cada um sai 0
e lista as flags/ações do contrato; entrada inválida sai 2; nada termina em traceback. Oráculo O1 (onda 1)."""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comum import CO, Base, contrato  # noqa: E402


def flag_nomes(spec):
    """'--tipo {skill,...}' -> '--tipo'; '--max-rodadas INT=3' -> '--max-rodadas'."""
    return [f.split()[0] for f in spec.get("flags", [])]


class TestDispatcher(Base):
    exige = (CO,)

    def setUp(self):
        super().setUp()
        self.cli = contrato()["cli"]
        self.subs = self.cli["subcomandos"]

    def test_todo_subcomando_do_contrato_tem_help_com_flags_e_acoes(self):
        self.assertEqual(len(self.subs), 20)
        for nome, spec in self.subs.items():
            with self.subTest(sub=nome):
                code, out, err = self.co(nome, "--help")
                self.assertEqual(code, 0, "%s --help: %s" % (nome, out + err))
                self.assertNotIn("Traceback", out + err)
                for fl in flag_nomes(spec):
                    self.assertIn(fl, out, "%s --help não lista %s" % (nome, fl))
                for ac in spec.get("acoes", []):
                    if not ac.startswith("("):
                        self.assertIn(ac, out, "%s --help não lista a ação %s" % (nome, ac))

    def test_help_global_lista_os_20_subcomandos_e_work(self):
        code, out, err = self.co("--help", work=False)
        self.assertEqual(code, 0, out + err)
        self.assertIn("--work", out)
        for nome in self.subs:
            self.assertRegex(out, r"\b%s\b" % re.escape(nome))

    def test_sem_work_sai_2(self):
        code, out, err = self.co("status", work=False)
        self.assertEqual(code, 2, out + err)
        self.assertIn("usage", (out + err).lower())

    def test_subcomando_desconhecido_sai_2(self):
        code, out, err = self.co("aprovar_tudo")
        self.assertEqual(code, 2, out + err)
        self.assertIn("usage", (out + err).lower())

    def test_escolhas_invalidas_saem_2_pelo_argparse(self):
        casos = [
            ("init", "--alvo", self.alvo, "--tipo", "repo", "--pedido", "p", "--stop", "s"),
            ("maquina", "check", "--nivel", "galaxia"),
            ("maquina", "verificar"),
            ("medir", "--config", "outra"),
            ("trava", "integracao", "abrir"),
            ("aprovar", "stop", "--decisao", "talvez"),
            ("portao", "rodar"),
            ("lote", "voar"),
            ("oraculo", "apagar"),
            ("veredito", "--formato-x"),
            ("ev",),
        ]
        for argv in casos:
            with self.subTest(argv=argv):
                code, out, err = self.co(*argv)
                self.assertEqual(code, 2, out + err)
                self.assertIn("usage", (out + err).lower())
                self.assertNotIn("Traceback", out + err)

    def test_negativos_que_valem_com_ou_sem_handler(self):
        self.init()
        for argv in [("medir", "--final", "--k", "1"), ("reabrir", "T-01"), ("lote", "retornar", "T-01")]:
            with self.subTest(argv=argv):
                code, out, err = self.co(*argv)
                self.assertEqual(code, 2, out + err)
                self.assertNotIn("Traceback", out + err)

    def test_nenhum_subcomando_termina_em_traceback_e_pendente_tem_formato(self):
        self.init()
        f = os.path.join(self.tmp, "x.json")
        with open(f, "w") as fh:
            fh.write("{}")
        chamadas = {
            "status": [], "load": ["PLANO"], "maquina": ["check"], "pontos": ["check"],
            "oraculo": ["vacuo", "--stub", f], "plano": ["check", "--plano", f], "lote": ["proximo"],
            "diff": ["T-01", "--base", "HEAD"], "colisao": ["T-01", "T-02"], "trava": ["integracao", "acquire",
                                                                                     "--dono", "T-01"],
            "medir": ["--k", "3", "--simulated"], "comparar": ["--base", "baseline", "--com", "sistema"],
            "portao": ["selftest"], "veredito": ["--json"], "retomar": [], "reabrir": ["T-01", "--motivo", "m"],
            "hook": ["selftest"],
        }
        for nome, argv in chamadas.items():
            with self.subTest(sub=nome):
                code, out, err = self.co(nome, *argv, input="")
                self.assertIn(code, (0, 1, 2), out + err)
                self.assertNotIn("Traceback", out + err)
                if code == 2 and "pendente" in (out + err):
                    self.assertIn("pendente: %s" % nome, out + err)


if __name__ == "__main__":
    unittest.main()
