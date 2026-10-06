"""HELD-OUT frente C (co_portao) — oráculo O1, onda 1. Variações de G3 (mudança não commitada, staged, untracked,
modo), G4 (skip/xfail/_exit/except-pass/__eq__/conftest; remoção de skip não é gaming), G0/G1 falha fechada e
veredito (ERRO, item ausente, waiver sem aprovação, NA indevido, aprovação com audit limpo)."""
import json
import os
import sys
import unittest

VIS = os.path.expanduser("~/.claude/skills/construcao-orquestrada/tests/onda1")
sys.path.insert(0, os.path.realpath(VIS))
from _comum import git, json5_load, now_ts  # noqa: E402
from test_c_portao import PortaoBase  # noqa: E402
import test_c_portao as V  # noqa: E402


class HeldoutG3(PortaoBase):
    def test_arquivo_novo_fora_do_territorio_nao_commitado(self):
        self.wfile("fora.txt", "x\n")
        self.assertReprova("G3")

    def test_mudanca_staged_fora_do_territorio(self):
        self.wfile("README.md", "# staged\n")
        git(self.alvo, "add", "README.md", env=self.env)
        self.assertReprova("G3")

    def test_mudanca_nao_commitada_fora_do_territorio(self):
        self.wfile("README.md", "# sujo\n")
        self.assertReprova("G3")

    def test_mudanca_de_modo_fora_do_territorio(self):
        os.chmod(os.path.join(self.alvo, "README.md"), 0o755)
        self.commit()
        self.assertReprova("G3")


class HeldoutG4(PortaoBase):
    def test_unittest_skip(self):
        self.wfile("src/core.py", "import unittest\n\n\n@unittest.skip('x')\ndef soma(a, b):\n    return a + b\n")
        self.commit()
        self.assertReprova("G4")

    def test_pytest_xfail(self):
        self.wfile("src/core.py", "import pytest\n\n\n@pytest.mark.xfail\ndef soma(a, b):\n    return a + b\n")
        self.commit()
        self.assertReprova("G4")

    def test_os_exit(self):
        self.wfile("src/core.py", "import os\n\n\ndef soma(a, b):\n    os._exit(0)\n")
        self.commit()
        self.assertReprova("G4")

    def test_except_pass_nu(self):
        self.wfile("src/core.py", "def soma(a, b):\n    try:\n        return a + b\n    except:\n        pass\n")
        self.commit()
        self.assertReprova("G4")

    def test_eq_novo(self):
        self.wfile("src/core.py", "class Qualquer:\n    def __eq__(self, o):\n        return True\n\n\n"
                   "def soma(a, b):\n    return Qualquer()\n")
        self.commit()
        self.assertReprova("G4")

    def test_conftest_novo(self):
        self.wfile("conftest.py", "import pytest\n")
        self.commit()
        self.assertReprova("G4", task="T-02")

    def test_remover_skip_existente_nao_e_gaming(self):
        self.wfile("src/core.py", "import pytest\n\n\ndef soma(a, b):\n    pytest.skip('x')\n    return a + b\n")
        self.commit("base com skip")
        self.base = git(self.alvo, "rev-parse", "HEAD", env=self.env)
        self.wfile("src/core.py", "def soma(a, b):\n    return a + b\n")
        self.commit("remove skip")
        self.assertAprova()


class HeldoutG0G1(V.TestG0):
    def test_g0_reprova_se_contagem_congelada_maior_que_a_atual(self):
        self.congelar(n_testes=50, n_assercoes=90)
        code, r, item, out = self.portao("G0")
        self.assertIn(item["G0"]["status"], ("FAIL", "ERRO"), out)
        self.assertEqual(code, 1)

    def test_g0_sem_campanha_mae_falha_fechado(self):
        self.L.append("oraculo_congelado", payload={"hash": "f" * 64, "n_testes": 1, "n_assercoes": 1,
                                                     "manifest_hash": "e" * 64})
        self.gerar_regressao()
        code, r, item, out = self.portao("G0")
        self.assertIn(item["G0"]["status"], ("FAIL", "ERRO"), out)
        self.assertNotEqual(code, 0)

    def suites(self, cmd):
        V.TestG1.suites(self, cmd)

    def test_g1_unittest_sem_nenhum_teste_coletado(self):
        vazio = os.path.join(self.tmp, "vazio")
        os.makedirs(vazio)
        self.suites("cd %s && %s -m unittest discover -s . -v" % (vazio, sys.executable))
        code, r, item, out = self.portao("G1")
        self.assertIn(item["G1"]["status"], ("FAIL", "ERRO"), out)

    def test_g1_cli_sem_suites_declaradas_falha_fechado(self):
        self.gerar_regressao()
        code, r, item, out = self.portao("G1")
        self.assertIn(item["G1"]["status"], ("FAIL", "ERRO"), out)
        self.assertNotEqual(code, 0)

    # não reexecutar os testes visíveis herdados de TestG0
    # não reexecutar NENHUM teste visível herdado de TestG0 (inclusive os que o visível ganhar depois)
    for _n in [n for n in dir(V.TestG0) if n.startswith("test_")]:
        locals()[_n] = None
    del _n


class HeldoutVeredito(V.TestVeredito):
    def test_erro_e_no_go(self):
        self.relatorio({"G1": {"status": "ERRO", "exit": 2}})
        code, v = self.veredito()
        self.assertEqual((code, v["veredito"]), (1, "NO-GO"))

    def test_item_sem_waiver_ausente_do_relatorio_e_no_go(self):
        self.relatorio(tirar=("G3",))
        code, v = self.veredito()
        self.assertEqual((code, v["veredito"]), (1, "NO-GO"))

    def test_waived_sem_arquivo_de_aprovacao_e_no_go(self):
        self.relatorio({"G2": {"status": "WAIVED", "motivo": "x", "aprovacao": None}})
        code, v = self.veredito()
        self.assertEqual((code, v["veredito"]), (1, "NO-GO"))

    def test_na_em_item_que_aplica_e_no_go(self):
        self.relatorio({"G4": {"status": "NA", "motivo": "não quis rodar", "exit": None}})
        code, v = self.veredito()
        self.assertEqual((code, v["veredito"]), (1, "NO-GO"))

    def test_aprovacao_com_linha_de_audit_correspondente_e_go(self):
        # premissas_ok com o hash REAL de obra.json5 (A4: hash divergente já é NO-GO por outro motivo)
        from _comum import sha_file
        self.L.ate_premissas()
        self.L.t("premissas_ok", "PREMISSAS", "AGUARDANDO_HUMANO", "orquestrador",
                 payload={"obra_hash": sha_file(os.path.join(self.ws, "obra.json5")),
                          "pontos_hash": sha_file(os.path.join(self.ws, "pontos.json5")), "pontos_ids": []})
        self.L.humano("stop", "aprovado", "ORACULO")
        ap = [r for r in self.L.records() if r["evento"] == "aprovacao"][-1]
        os.makedirs(os.path.dirname(self.audit), exist_ok=True)
        with open(self.audit, "a") as fh:
            fh.write(json.dumps({"ts": now_ts(), "tipo": "aprovacao", "cmd": "aprovar", "name": "stop",
                                 "decision": "aprovado", "by": "humano", "work": self.ws, "user": "teste",
                                 "tty": "/dev/ttys000", "seq": ap["seq"],
                                 "hash_estado": ap["payload"]["hash_estado"]}) + "\n")
        self.relatorio()
        code, v = self.veredito()
        self.assertEqual((code, v["veredito"], v["aprovacoes_sem_audit_limpo"]), (0, "GO", []))

    # não reexecutar os testes visíveis herdados
    for _n in [n for n in dir(V.TestVeredito) if n.startswith("test_")]:
        locals()[_n] = None
    del _n


if __name__ == "__main__":
    unittest.main()
