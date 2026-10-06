"""Frente C — co_portao.py núcleo: regressao.json5, G0 oráculo intacto, G1 suítes (falha fechada), G3 território e
G4 gaming via `co.py diff`, veredito com precedência NO-GO > GO (simulado) > GO (com waiver) > GO; G0/G1/G3/G4 sem
waiver. Oráculo O1 (onda 1). Cada gate tem um caso em que o comando roda mas o efeito não acontece (L03)."""
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comum import (AC, CO, CO_ESTADO, CO_PORTAO, HEX64, REFS, Base, contrato, git, json5_load, now_ts,  # noqa: E402
                    py_call, sha_file, sha_obj)

SENTINELA = "zq-heldout-7731-sentinela"


def sistema_hash_real(t):
    """hash do sistema do alvo pela função do motor (co_estado.hash_sistema = formatos.convencoes.hash_sistema)."""
    code, out, err = py_call(t.env, "import co_estado\nprint(co_estado.hash_sistema(%r))" % t.alvo)
    h = out.strip().splitlines()[-1] if out.strip() else ""
    t.assertRegex(h, r"^[0-9a-f]{64}$", out + err)
    return h


def waiver_aprovado(t, gid, decisao="aprovado", com_seq=True, com_audit=True, portao=None):
    """Waiver com aprovação de verdade: evento `aprovacao` no ledger (seq s), arquivo aprovacoes/<portao>-<s>.json
    no formato de formatos.aprovacao (decisao, seq) e linha `tipo aprovacao` no audit FORA do ws (mesma fixture de
    aprovação com audit dos outros testes). O portão aprovado é o do PRÓPRIO item (`Gn`). Os parâmetros desligam
    uma peça por vez para os casos NÃO (portao= aprova outro item)."""
    portao = portao or gid
    s = t.L.last()["seq"] + 1
    arq = os.path.join(t.ws, "aprovacoes", "%s-%d.json" % (portao, s))
    t.L.append("aprovacao", payload={"portao": portao, "decisao": decisao, "arquivo": arq, "hash_estado": "1" * 64,
                                     "usuario_so": "teste", "ttyname": "/dev/ttys000"})
    ap = {"schema_version": 1, "portao": portao, "decisao": decisao, "nota": None, "usuario_so": "teste",
          "uid": os.getuid(), "ttyname": "/dev/ttys000", "ts": now_ts(), "hash_estado": "1" * 64,
          "estado": {"estado": "AGUARDANDO_HUMANO", "portao": portao, "retorno": None}, "desafio_ok": True,
          "transicao_seq": s + 1}
    if com_seq:
        ap["seq"] = s
    t.write_json(arq, ap)
    if com_audit:
        os.makedirs(os.path.dirname(t.audit), exist_ok=True)
        with open(t.audit, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": now_ts(), "tipo": "aprovacao", "cmd": "aprovar", "name": portao,
                                 "decision": decisao, "by": "humano", "work": t.ws, "user": "teste",
                                 "tty": "/dev/ttys000", "seq": s, "hash_estado": "1" * 64}) + "\n")
    return {gid: {"status": "WAIVED", "motivo": "dispensado pelo founder", "aprovacao": arq, "exit": None}}


class PortaoBase(Base):
    exige = (CO, CO_ESTADO, CO_PORTAO)

    def setUp(self):
        super().setUp()
        a = self.alvo
        os.makedirs(os.path.join(a, "tests"))
        self.wfile("src/core.py", "import sys\n\n\ndef soma(a, b):\n    return a + b\n")
        self.wfile("tests/test_core.py", "import unittest\nimport sys\nsys.path.insert(0, 'src')\nfrom core import soma\n\n\n"
                   "class T(unittest.TestCase):\n    def test_soma(self):\n        self.assertEqual(soma(1, 2), 3)\n")
        self.wfile("README.md", "# alvo\n")
        git(a, "init", "-q", env=self.env)
        git(a, "add", "-A", env=self.env)
        git(a, "commit", "-q", "-m", "base", env=self.env)
        self.base = git(a, "rev-parse", "HEAD", env=self.env)
        self.L = self.init()
        self.write_json(os.path.join(self.ws, "PLANO.json5"), {
            "schema_version": 1, "rodada": 1, "decisoes": [], "contrato": {}, "parada": "pass^3",
            "tasks": [
                {"id": "T-01", "titulo": "núcleo", "writes": ["src/**"], "deps": [], "cenarios": ["C-01"],
                 "construtor": "builder-A", "criterio": "C-01 vermelho→verde"},
                {"id": "T-02", "titulo": "tudo", "writes": ["**"], "deps": [], "cenarios": ["C-01"],
                 "construtor": "builder-B", "criterio": "C-01 vermelho→verde"}]})
        self.write_json(os.path.join(self.ws, "oraculo", "heldout", "casos", "C-01.json"),
                        {"id": "h-01", "cenario": "C-01", "classe": "Q", "entrada": {"a": SENTINELA},
                         "esperado": {"exit": 0}})

    def wfile(self, rel, txt, repo=None):
        p = os.path.join(repo or self.alvo, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write(txt)
        return p

    def commit(self, msg="mudanca"):
        git(self.alvo, "add", "-A", env=self.env)
        git(self.alvo, "commit", "-q", "-m", msg, env=self.env)

    def diff(self, task="T-01"):
        code, out, err = self.co("diff", task, "--base", self.base, "--repo", self.alvo)
        self.assertNotIn("Traceback", out + err)
        self.assertNotIn("pendente", out + err)
        return code, out + err

    def assertReprova(self, gate, task="T-01"):
        code, out = self.diff(task)
        self.assertEqual(code, 1, "%s deveria reprovar: %s" % (gate, out))
        self.assertIn(gate, out)

    def assertAprova(self, task="T-01"):
        code, out = self.diff(task)
        self.assertEqual(code, 0, out)

    def gerar_regressao(self, tipo="cli"):
        code, out, err = py_call(self.env, "import co_portao\nco_portao.gerar_regressao(%r, %r)" % (self.ws, tipo),
                                 cwd=self.tmp)
        self.assertEqual(code, 0, out + err)
        return json5_load(os.path.join(self.ws, "regressao.json5"))

    def portao(self, only):
        code, out, err = self.co("portao", "run", "--only", only)
        self.assertNotIn("Traceback", out + err)
        self.assertNotIn("pendente", out + err)
        rep = os.path.join(self.ws, "gate-report.json")
        self.assertTrue(os.path.isfile(rep), "gate-report.json não gravado: " + out + err)
        with open(rep) as fh:
            r = json.load(fh)
        item = {i["id"]: i for i in r["itens"]}
        return code, r, item, out + err


# ====================================================================== regressao.json5

class TestRegressao(PortaoBase):
    def test_gerar_regressao_tem_os_15_itens_com_na_e_waiver(self):
        reg = self.gerar_regressao("cli")
        ids = [i["id"] for i in reg["itens"]]
        self.assertEqual(ids, ["G%d" % n for n in range(15)])
        self.assertEqual(reg["tipo"], "cli")
        self.assertTrue(HEX64.match(reg["portoes_hash"]))
        sem_waiver = contrato()["sem_waiver"]
        for it in reg["itens"]:
            self.assertIs(it["falha_fechado"], True)
            if it["id"] in sem_waiver:
                self.assertIs(it["waiver"], False, it["id"])
            if not it["aplica"]:
                self.assertTrue(it["na_motivo"], "N/A sem motivo em %s" % it["id"])
        g = {i["id"]: i for i in reg["itens"]}
        self.assertIs(g["G8"]["aplica"], False)
        self.assertIs(g["G0"]["aplica"], True)
        self.assertIs(g["G3"]["aplica"], True)


# ====================================================================== G3 território

class TestG3Territorio(PortaoBase):
    def test_mudanca_dentro_do_territorio_passa(self):
        self.wfile("src/core.py", "import sys\n\n\ndef soma(a, b):\n    return b + a\n")
        self.wfile("src/novo.py", "X = 1\n")
        self.commit()
        self.assertAprova()

    def test_arquivo_fora_do_territorio_reprova(self):
        self.wfile("README.md", "# alvo editado por sed indireto\n")
        self.commit()
        self.assertReprova("G3")

    def test_delecao_fora_do_territorio_reprova(self):
        os.remove(os.path.join(self.alvo, "README.md"))
        self.commit()
        self.assertReprova("G3")

    def test_rename_de_fora_para_dentro_reprova(self):
        git(self.alvo, "mv", "README.md", "src/README.md", env=self.env)
        self.commit()
        self.assertReprova("G3")

    def test_task_desconhecida_ou_base_invalida_sai_2(self):
        code, out = self.diff("T-99")
        self.assertEqual(code, 2, out)
        code, out, err = self.co("diff", "T-01", "--base", "0" * 40, "--repo", self.alvo)
        self.assertEqual(code, 2, out + err)
        self.assertNotIn("Traceback", out + err)
        self.assertAprova()  # controle: o mesmo comando com entrada válida e diff vazio passa


# ====================================================================== G4 gaming

class TestG4Gaming(PortaoBase):
    def test_edicao_de_teste_reprova_mesmo_dentro_do_territorio(self):
        self.wfile("tests/test_core.py", "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_soma(self):\n"
                   "        pass\n")
        self.commit()
        self.assertReprova("G4", task="T-02")

    def test_pytest_skip_novo_reprova(self):
        self.wfile("src/core.py", "import pytest\n\n\ndef soma(a, b):\n    pytest.skip('depois')\n    return a + b\n")
        self.commit()
        self.assertReprova("G4")

    def test_sys_exit_zero_reprova(self):
        self.wfile("src/core.py", "import sys\n\n\ndef soma(a, b):\n    sys.exit(0)\n")
        self.commit()
        self.assertReprova("G4")

    def test_assert_true_reprova(self):
        self.wfile("src/core.py", "import sys\n\n\ndef soma(a, b):\n    assert True\n    return a + b\n")
        self.commit()
        self.assertReprova("G4")

    def test_literal_do_heldout_no_codigo_reprova(self):
        self.wfile("src/core.py", "import sys\n\n\ndef soma(a, b):\n    if a == %r:\n        return 0\n"
                   "    return a + b\n" % SENTINELA)
        self.commit()
        self.assertReprova("G4")

    def test_sys_exit_de_main_nao_e_gaming(self):
        self.wfile("src/cli.py", "import sys\n\n\ndef main():\n    return 0\n\n\nif __name__ == '__main__':\n"
                   "    sys.exit(main())\n")
        self.commit()
        self.assertAprova()


# ====================================================================== G0 oráculo intacto

class TestG0(PortaoBase):
    def congelar(self, n_testes=1, n_assercoes=1, manifest=True):
        dev = os.path.join(self.ws, "oraculo", "dev")
        man = os.path.join(self.ws, "oraculo", "MANIFEST.json5")
        if manifest:
            self.write_json(man, {"schema_version": 1, "frentes": {"T-01": {
                "autores": ["oraculo-O1"], "dev": ["oraculo/dev/**"], "heldout": ["oraculo/heldout/**"]}},
                "construtores": {"T-01": "builder-A"}, "congelado": None})
        self.oraculo_arq = self.wfile("test_o.py", "import unittest\n\n\nclass O(unittest.TestCase):\n"
                                      "    def test_a(self):\n        self.assertEqual(1, 1)\n        self.assertTrue(1)\n\n"
                                      "    def test_b(self):\n        self.assertIn(1, [1])\n", repo=dev)
        camp = os.path.join(self.ws, "campanhas", "construcao")
        for argv in (["init", "--target", self.alvo, "--scope", "src/**", "--problem", "p", "--stop", "s",
                      "--max-rounds", "3"], ["oracle", "freeze", "--file", self.oraculo_arq]):
            p = subprocess.run([sys.executable, AC, "--work", camp] + argv, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, universal_newlines=True, env=self.env, timeout=60)
            self.assertEqual(p.returncode, 0, p.stdout)
        with open(os.path.join(camp, ".auto-correcao", "state.json")) as fh:
            h = json.load(fh)["oracle"]["hash"]
        self.L.append("oraculo_congelado", payload={"hash": h, "n_testes": n_testes, "n_assercoes": n_assercoes,
                                                     "manifest_hash": sha_file(man) if manifest else "e" * 64})
        self.gerar_regressao()

    def test_g0_passa_com_oraculo_intacto(self):
        self.congelar()
        code, r, item, out = self.portao("G0")
        self.assertEqual(item["G0"]["status"], "PASS", out)
        self.assertEqual(r["only"], ["G0"])
        self.assertTrue(r["itens"][0]["evidencia"])
        ev = [x for x in self.L.records() if x["evento"] == "portao_relatorio"]
        self.assertTrue(ev, "portao run não gravou portao_relatorio no ledger")
        self.assertTrue(HEX64.match(ev[-1]["payload"]["gate_report_hash"]))

    def test_g0_reprova_sem_manifest(self):
        self.congelar(manifest=False)
        code, r, item, out = self.portao("G0")
        self.assertIn(item["G0"]["status"], ("FAIL", "ERRO"), "oráculo congelado sem MANIFEST passou: " + out)

    def test_g0_reprova_com_manifest_alterado_depois_do_congelamento(self):
        self.congelar()
        man = os.path.join(self.ws, "oraculo", "MANIFEST.json5")
        m = json5_load(man)
        m["frentes"]["T-01"]["autores"].append("builder-A")
        self.write_json(man, m)
        code, r, item, out = self.portao("G0")
        self.assertIn(item["G0"]["status"], ("FAIL", "ERRO"), "MANIFEST ≠ manifest_hash congelado passou: " + out)

    def test_g0_reprova_com_assercao_removida(self):
        self.congelar()
        with open(self.oraculo_arq) as fh:
            txt = fh.read()
        with open(self.oraculo_arq, "w") as fh:
            fh.write(txt.replace("        self.assertTrue(1)\n", ""))
        code, r, item, out = self.portao("G0")
        self.assertIn(item["G0"]["status"], ("FAIL", "ERRO"), out)
        self.assertEqual(code, 1, out)
        self.assertEqual(r["veredito"], "NO-GO")


# ====================================================================== G1 suítes

class TestG1(PortaoBase):
    def suites(self, cmd):
        p = os.path.join(self.ws, "obra.json5")
        obra = json5_load(p)
        obra["suites"] = [{"nome": "unit", "cmd": cmd}]
        self.write_json(p, obra)
        self.gerar_regressao()

    def test_g1_passa_com_suite_verde_e_testes_coletados(self):
        self.suites("cd %s && %s -m unittest discover -s tests -v" % (self.alvo, sys.executable))
        code, r, item, out = self.portao("G1")
        self.assertEqual(item["G1"]["status"], "PASS", out)

    def test_g1_reprova_com_teste_falhando(self):
        self.wfile("src/core.py", "def soma(a, b):\n    return a - b\n")
        self.suites("cd %s && %s -m unittest discover -s tests -v" % (self.alvo, sys.executable))
        code, r, item, out = self.portao("G1")
        self.assertEqual(item["G1"]["status"], "FAIL", out)
        self.assertEqual(code, 1)

    def test_g1_reprova_suite_que_sai_0_sem_coletar_teste(self):
        self.suites("%s -c pass" % sys.executable)
        code, r, item, out = self.portao("G1")
        self.assertIn(item["G1"]["status"], ("FAIL", "ERRO"), "0 testes coletados não pode ser PASS: " + out)
        self.assertEqual(code, 1)

    def test_g1_reprova_ferramenta_ausente(self):
        self.suites("runner-que-nao-existe-xyz --tudo")
        code, r, item, out = self.portao("G1")
        self.assertIn(item["G1"]["status"], ("FAIL", "ERRO"), out)
        self.assertNotEqual(code, 0)


# ====================================================================== veredito

class TestVeredito(PortaoBase):
    def relatorio(self, mudancas=None, veredito_gravado="GO", tirar=(), ancorar=True, sistema_hash=None):
        reg = self.gerar_regressao("cli")
        itens = []
        for it in reg["itens"]:
            if it["id"] in tirar:
                continue
            st = "PASS" if it["aplica"] else "NA"
            itens.append({"id": it["id"], "status": st, "exit": 0 if st == "PASS" else None, "cmd": it["cmd"],
                          "evidencia": "ok", "motivo": None if st == "PASS" else it["na_motivo"], "aprovacao": None})
        for i in itens:
            i.update((mudancas or {}).get(i["id"], {}))
        rep = {"schema_version": 1, "ts": now_ts(), "seq_ledger": self.L.last()["seq"], "final": True, "only": None,
               "sistema_hash": sistema_hash or sistema_hash_real(self),
               "regressao_hash": sha_file(os.path.join(self.ws, "regressao.json5")),
               "itens": itens, "veredito": veredito_gravado}
        p = self.write_json(os.path.join(self.ws, "gate-report.json"), rep)
        if ancorar:  # como `portao run` grava: evento portao_relatorio com o hash do arquivo
            self.L.append("portao_relatorio", payload={"gate_report_hash": sha_file(p), "veredito": veredito_gravado,
                                                        "final": True})

    def waiver(self, gid, **kw):
        return waiver_aprovado(self, gid, **kw)

    def simular(self):
        self.L.append("medicao_registrada", payload={
            "config": "sistema", "k": 1, "final": False, "run_ids": ["sistema-r1-1"], "sistema_hash": "d" * 64,
            "seq_ultimo_merge": None, "pass_at_k": 1.0, "pass_hat_k": 1.0, "rotulo": "indício", "simulated": True})

    def veredito(self):
        code, out, err = self.co("veredito", "--json")
        self.assertNotIn("Traceback", out + err)
        self.assertNotIn("pendente", out + err)
        v = json.loads(out)
        for k in ("veredito", "motivo", "falhas", "waivers", "simulado", "gate_report_hash", "sintese",
                  "aprovacoes_sem_audit_limpo"):
            self.assertIn(k, v)
        return code, v

    def test_tudo_pass_e_go(self):
        self.relatorio()
        code, v = self.veredito()
        self.assertEqual((code, v["veredito"], v["falhas"], v["waivers"], v["simulado"]), (0, "GO", [], [], False))
        rep = os.path.join(self.ws, "gate-report.json")
        with open(rep) as fh:
            obj = json.load(fh)
        self.assertIn(v["gate_report_hash"], (sha_file(rep), sha_obj(obj)))

    def test_waiver_em_item_com_waiver_e_go_com_waiver(self):
        self.relatorio(self.waiver("G2"))
        code, v = self.veredito()
        self.assertEqual((code, v["veredito"], v["waivers"]), (0, "GO (com waiver)", ["G2"]))

    def test_fail_e_no_go(self):
        self.relatorio({"G3": {"status": "FAIL", "exit": 1}})
        code, v = self.veredito()
        self.assertEqual((code, v["veredito"]), (1, "NO-GO"))
        self.assertIn("G3", v["falhas"])

    def test_veredito_recalcula_e_ignora_o_go_gravado_no_relatorio(self):
        self.relatorio({"G1": {"status": "FAIL", "exit": 1}}, veredito_gravado="GO")
        code, v = self.veredito()
        self.assertEqual((code, v["veredito"]), (1, "NO-GO"))

    def test_item_sem_waiver_dispensado_e_no_go(self):
        for gid in ("G0", "G1", "G3", "G4"):
            with self.subTest(gid=gid):
                self.relatorio(self.waiver(gid))
                code, v = self.veredito()
                self.assertEqual((code, v["veredito"]), (1, "NO-GO"))

    def test_simulado_vence_waiver_e_go(self):
        self.simular()
        self.relatorio()
        code, v = self.veredito()
        self.assertEqual((code, v["veredito"], v["simulado"]), (0, "GO (simulado)", True))
        self.relatorio(self.waiver("G2"))
        code, v = self.veredito()
        self.assertEqual(v["veredito"], "GO (simulado)")

    def test_no_go_vence_simulado(self):
        self.simular()
        self.relatorio({"G4": {"status": "FAIL", "exit": 1}})
        code, v = self.veredito()
        self.assertEqual((code, v["veredito"]), (1, "NO-GO"))

    def test_aprovacao_no_ledger_sem_linha_no_audit_e_no_go(self):
        self.L.ate_oraculo()  # grava `aprovacao` + transição humana sem passar por co.py aprovar
        self.relatorio()
        code, v = self.veredito()
        self.assertEqual((code, v["veredito"]), (1, "NO-GO"))
        self.assertTrue(v["aprovacoes_sem_audit_limpo"])

    def test_relatorio_de_outro_estado_do_alvo_e_no_go(self):
        h_velho = sistema_hash_real(self)
        self.wfile("src/core.py", "def soma(a, b):\n    return a + b + 0\n")  # o alvo mudou depois do relatório
        self.assertNotEqual(sistema_hash_real(self), h_velho)
        self.relatorio(sistema_hash=h_velho)
        code, v = self.veredito()
        self.assertEqual((code, v["veredito"]), (1, "NO-GO"), "relatório de outro estado do alvo aceito")
        self.relatorio(sistema_hash="d" * 64)
        code, v = self.veredito()
        self.assertEqual((code, v["veredito"]), (1, "NO-GO"), "sistema_hash inventado aceito")

    def test_waiver_aprovado_em_portao_de_outro_item_e_no_go(self):
        self.relatorio(self.waiver("G2", portao="G5"))
        code, v = self.veredito()
        self.assertEqual((code, v["veredito"]), (1, "NO-GO"), "aprovação de G5 serviu de waiver para G2")
        self.relatorio(self.waiver("G2", portao="entrega"))
        code, v = self.veredito()
        self.assertEqual((code, v["veredito"]), (1, "NO-GO"), "aprovação de entrega serviu de waiver para G2")

    def test_relatorio_sem_ancora_no_ledger_e_no_go(self):
        self.relatorio(ancorar=False)
        code, v = self.veredito()
        self.assertEqual((code, v["veredito"]), (1, "NO-GO"), "veredito sem relatório ancorado no ledger")

    def test_relatorio_alterado_depois_de_ancorado_e_no_go(self):
        self.relatorio()
        p = os.path.join(self.ws, "gate-report.json")
        with open(p) as fh:
            rep = json.load(fh)
        rep["ts"] = "2026-10-04T00:00:00Z"
        self.write_json(p, rep)
        code, v = self.veredito()
        self.assertEqual((code, v["veredito"]), (1, "NO-GO"))

    def test_waiver_sem_aprovacao_completa_e_no_go(self):
        for nome, kw in (("sem seq", {"com_seq": False}), ("decisao rejeitado", {"decisao": "rejeitado"}),
                         ("sem linha no audit", {"com_audit": False})):
            with self.subTest(caso=nome):
                self.tearDown()
                self.setUp()
                self.relatorio(self.waiver("G2", **kw))
                code, v = self.veredito()
                self.assertEqual((code, v["veredito"]), (1, "NO-GO"), "waiver %s aceito" % nome)

    def test_waiver_com_aprovacao_que_nao_existe_no_ledger_e_no_go(self):
        arq = self.write_json(os.path.join(self.ws, "aprovacoes", "entrega-90.json"), {"portao": "entrega"})
        self.relatorio({"G2": {"status": "WAIVED", "motivo": "m", "aprovacao": arq, "exit": None}})
        code, v = self.veredito()
        self.assertEqual((code, v["veredito"]), (1, "NO-GO"))

    def test_selftest_do_portao_sai_0(self):
        code, out, err = self.co("portao", "selftest")
        self.assertEqual(code, 0, out + err)
        self.assertNotIn("pendente", out + err)


if __name__ == "__main__":
    unittest.main()
