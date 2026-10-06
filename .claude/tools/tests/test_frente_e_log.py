import json
import os
import shutil
import tempfile
import unittest

from _util import TOOLS, run, escrever, ler

F = os.path.join(TOOLS, "frente.py")
L = os.path.join(TOOLS, "log-sessao.py")
WF = ("# W\n<!-- frentes:begin -->\n```json\n{\"ativas\": [], \"pausadas\": [], \"entregas\": []}\n```\n<!-- frentes:end -->\n\n"
      "<!-- tabela:begin -->\n<!-- tabela:end -->\n")


class Frente(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.d, "camp1")); os.makedirs(os.path.join(self.d, "camp2"))
        self.st = os.path.join(self.d, "state"); os.makedirs(self.st)
        escrever(os.path.join(self.st, "WORKFLOW.md"), WF, "w")
        self.env = {"HARNESS_STATE": self.st}

    def tearDown(self):
        shutil.rmtree(self.d)

    def f(self, *a):
        return run(["python3", F] + list(a), env=self.env)

    def dados(self):
        return json.loads(self.f("status", "--json").stdout)

    def test_ciclo_completo(self):
        c1, c2 = os.path.join(self.d, "camp1"), os.path.join(self.d, "camp2")
        r = self.f("open", "a", "--campanha", c1, "--objetivo", "x")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(ler(os.path.join(self.st, "CAMPANHA_ATIVA")).strip(), c1)
        self.assertNotEqual(self.f("open", "b", "--campanha", c2).returncode, 0)  # uma ativa por vez
        self.assertNotEqual(self.f("open", "a", "--campanha", c2).returncode, 0)  # nome repetido
        self.assertEqual(self.f("pause", "a").returncode, 0)
        self.assertEqual(ler(os.path.join(self.st, "CAMPANHA_ATIVA")).strip(), "nenhuma")
        self.assertEqual(self.f("open", "b", "--campanha", c2).returncode, 0)
        self.assertNotEqual(self.f("resume", "a").returncode, 0)  # b ativa
        self.assertEqual(self.f("close", "b", "--commit", "abc1234").returncode, 0)
        d = self.dados()
        self.assertEqual([x["nome"] for x in d["entregas"]], ["b"])
        self.assertEqual(d["entregas"][0]["commit"], "abc1234")
        self.assertRegex(d["entregas"][0]["em"], r"^\d{4}-\d\d-\d\dT")  # data do sistema
        self.assertEqual(self.f("resume", "a").returncode, 0)
        self.assertEqual(self.f("check").returncode, 0)
        self.assertIn("| entregue | b |", ler(os.path.join(self.st, "WORKFLOW.md")))

    def test_paralelas_so_se_todas_declaradas(self):
        c1, c2 = os.path.join(self.d, "camp1"), os.path.join(self.d, "camp2")
        self.f("open", "a", "--campanha", c1, "--paralela")
        self.assertEqual(self.f("open", "b", "--campanha", c2, "--paralela").returncode, 0)
        self.assertEqual(self.f("check").returncode, 0)

    def test_dry_run_nao_grava_e_campanha_inexistente_recusa(self):
        c1 = os.path.join(self.d, "camp1")
        self.assertEqual(self.f("open", "a", "--campanha", c1, "--dry-run").returncode, 0)
        self.assertEqual(self.dados()["ativas"], [])
        self.assertNotEqual(self.f("open", "z", "--campanha", self.d + "/nao").returncode, 0)
        self.assertNotEqual(self.f("open", "../x", "--campanha", c1).returncode, 0)

    def test_check_pega_violacao(self):
        p = os.path.join(self.st, "WORKFLOW.md")
        t = ler(p).replace('"ativas": []', '"ativas": [{"nome":"a","campanha":"/nao/existe"},{"nome":"b","campanha":"/x"}]')
        escrever(p, t, "w")
        r = self.f("check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("VIOLAÇÃO", r.stdout)

    def test_workflow_corrompido_falha(self):
        escrever(os.path.join(self.st, "WORKFLOW.md"), "sem bloco", "w")
        self.assertNotEqual(self.f("status").returncode, 0)

    def test_log_append_only(self):
        r = run(["python3", L, "--evento", "save", "--resumo", "um"], env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        run(["python3", L, "--evento", "nota", "--resumo", "dois", "--frente", "a"], env=self.env)
        linhas = ler(os.path.join(self.st, "logs", "sessoes.jsonl")).splitlines()
        self.assertEqual([json.loads(x)["resumo"] for x in linhas], ["um", "dois"])
        self.assertIn("ts", json.loads(linhas[0]))
        r = run(["python3", L, "--evento", "save", "--resumo", "x", "--dry-run"], env=self.env)
        self.assertEqual(len(ler(os.path.join(self.st, "logs", "sessoes.jsonl")).splitlines()), 2)
        self.assertNotEqual(run(["python3", L, "--resumo", "sem evento"], env=self.env).returncode, 0)

    def test_helps(self):
        for t in (F, L):
            r = run(["python3", t, "--help"])
            self.assertEqual(r.returncode, 0)
            self.assertTrue(r.stdout.strip())


if __name__ == "__main__":
    unittest.main()
