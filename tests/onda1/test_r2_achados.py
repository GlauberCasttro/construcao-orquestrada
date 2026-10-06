"""Rodada 2 da onda 1: testes que reproduzem os achados A1..A9 do verificador cego. Oráculo O1. Ver a seção
"Rodada 2" do ESPEC.md. Cada teste falha no código anterior à correção e passa quando o achado é corrigido.
Hashes de arquivo gravados no ledger (premissas_ok.obra_hash, plano_ok.plano_hash, plano_ok.regressao_hash) =
sha256 dos bytes do arquivo."""
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comum import (AC, CO, HEX64, Ledger, bash, git, json5_load, payload, py_call, run_tty, sha_file,  # noqa: E402
                    sub, HookBase)
from test_c_portao import PortaoBase, sistema_hash_real  # noqa: E402

SUITE_OK = "cd {alvo} && {py} -m unittest discover -s tests -v"


class R2Base(PortaoBase):
    """Alvo git + obra cli + PLANO (de PortaoBase) com ledger coerente: premissas_ok/plano_ok gravam o hash
    real de obra.json5, PLANO.json5 e regressao.json5."""

    def set_obra(self, **campos):
        p = os.path.join(self.ws, "obra.json5")
        obra = json5_load(p)
        obra.update(campos)
        self.write_json(p, obra)

    def ledger_coerente(self, ate="LOTE", so_t01=False, k_final=3, suite=None):
        L = self.L
        if so_t01:  # PLANO sem a T-02 de writes ["**"] (o portão une os writes de todas as tasks)
            p = os.path.join(self.ws, "PLANO.json5")
            pl = json5_load(p)
            pl["tasks"] = pl["tasks"][:1]
            self.write_json(p, pl)
        self.set_obra(suites=[{"nome": "unit", "cmd": suite or SUITE_OK.format(alvo=self.alvo, py=sys.executable)}],
                      base=self.base)
        self.gerar_regressao()
        obra_h = sha_file(os.path.join(self.ws, "obra.json5"))
        plano_h = sha_file(os.path.join(self.ws, "PLANO.json5"))
        reg_h = sha_file(os.path.join(self.ws, "regressao.json5"))
        L.t("iniciar", "INICIO", "PREMISSAS", "script")
        L.t("premissas_ok", "PREMISSAS", "AGUARDANDO_HUMANO", "orquestrador",
            payload={"obra_hash": obra_h, "pontos_hash": sha_file(os.path.join(self.ws, "pontos.json5")),
                     "pontos_ids": []})
        L.humano("stop", "aprovado", "ORACULO")
        L.t("oraculo_pronto", "ORACULO", "AGUARDANDO_HUMANO", "orquestrador")
        L.humano("oraculo", "aprovado", "BASELINE")
        L.append("oraculo_congelado", payload={"hash": "f" * 64, "n_testes": 1, "n_assercoes": 1,
                                                "manifest_hash": "e" * 64})
        L.t("dispensado", "BASELINE", "PLANO", "orquestrador", payload={"motivo": "cli"})
        L.t("plano_ok", "PLANO", "LOTE", "orquestrador",
            payload={"plano_hash": plano_h, "regressao_hash": reg_h, "ha_decisoes": False})
        L.append("contrato_hash", payload={"contrato_hash": "a" * 64, "plano_hash": plano_h, "max_despachos": 6})
        if ate == "ENTREGA":
            L.t("fronteira_vazia", "LOTE", "INTEGRAR", "script")
            L.t("merge_ok", "INTEGRAR", "VERIFICAR", "script")
            L.t("verde", "VERIFICAR", "MEDIR", "script")
            L.append("medicao_registrada", payload={
                "config": "sistema", "k": k_final, "final": True,
                "run_ids": ["sistema-r1-%d" % i for i in range(1, k_final + 1)],
                "sistema_hash": "d" * 64, "seq_ultimo_merge": None, "pass_at_k": 1.0, "pass_hat_k": 1.0,
                "rotulo": "final", "simulated": False})
            L.t("medido", "MEDIR", "FECHAR_RODADA", "script")
            L.t("rodada_fechada", "FECHAR_RODADA", "AGUARDANDO_HUMANO", "script",
                payload={"saida": "parar", "criterio_parada_ok": True, "plato_2": False, "comparacao_hash": None})
        self.audit_das_aprovacoes()
        return L

    def audit_das_aprovacoes(self):
        """Linhas tipo aprovacao no audit para cada `aprovacao` gravada à mão (senão o veredito acusa, com razão,
        aprovação fora do canal humano e o controle positivo não seria GO)."""
        os.makedirs(os.path.dirname(self.audit), exist_ok=True)
        with open(self.audit, "a", encoding="utf-8") as fh:
            for r in self.L.records():
                if r["evento"] == "aprovacao":
                    pl = r["payload"]
                    fh.write(json.dumps({"ts": r["ts"], "tipo": "aprovacao", "cmd": "aprovar", "name": pl["portao"],
                                         "decision": pl["decisao"], "by": "humano", "work": self.ws,
                                         "user": "teste", "tty": "/dev/ttys000", "seq": r["seq"],
                                         "hash_estado": pl["hash_estado"]}) + "\n")

    def relatorio_completo(self, veredito="GO", final=True, mudancas=None, tirar=()):
        """gate-report completo (G0..G14) + evento portao_relatorio com o hash, como `portao run` grava."""
        reg = json5_load(os.path.join(self.ws, "regressao.json5"))
        itens = []
        for it in reg["itens"]:
            if it["id"] in tirar:
                continue
            st = "PASS" if it["aplica"] else "NA"
            r = {"id": it["id"], "status": st, "exit": 0 if st == "PASS" else None, "cmd": it["cmd"],
                 "evidencia": "ok", "motivo": None if st == "PASS" else it["na_motivo"], "aprovacao": None}
            r.update((mudancas or {}).get(it["id"], {}))
            itens.append(r)
        rep = {"schema_version": 1, "ts": "2026-10-04T15:00:00Z", "seq_ledger": self.L.last()["seq"], "final": final,
               "only": None, "sistema_hash": sistema_hash_real(self),
               "regressao_hash": sha_file(os.path.join(self.ws, "regressao.json5")), "itens": itens,
               "veredito": veredito}
        p = self.write_json(os.path.join(self.ws, "gate-report.json"), rep)
        self.L.append("portao_relatorio", payload={"gate_report_hash": sha_file(p), "veredito": veredito,
                                                    "final": final})

    def veredito(self):
        code, out, err = self.co("veredito", "--json")
        self.assertNotIn("Traceback", out + err)
        return code, json.loads(out) if out.strip().startswith("{") else {"veredito": None, "raw": out + err}

    def aprovar_entrega(self):
        antes = self.L.raw()
        code, out, ch = run_tty(["--work", self.ws, "aprovar", "entrega", "--decisao", "aprovado"], self.env)
        return code, out, antes


# ====================================================================== A1 / A5 — entrega só com GO final real

class TestA1A5Entrega(R2Base):
    def test_A1_portao_run_only_final_nao_satisfaz_entrega(self):
        self.ledger_coerente(ate="ENTREGA")
        code, out, err = self.co("portao", "run", "--only", "G1", "--final")
        self.assertNotIn("Traceback", out + err)
        code, out, antes = self.aprovar_entrega()
        self.assertNotEqual(code, 0, "relatório com --only satisfez a entrega: " + out)
        self.assertEqual(self.L.raw(), antes)
        self.assertNotEqual(self.status()["obra"]["estado"], "ENTREGUE")

    def test_A1_relatorio_only_nunca_e_go_de_regressao(self):
        self.ledger_coerente()
        self.co("portao", "run", "--only", "G1", "--final")
        with open(os.path.join(self.ws, "gate-report.json")) as fh:
            rep = json.load(fh)
        self.assertEqual(rep["only"], ["G1"])
        self.assertFalse(str(rep["veredito"]).startswith("GO") and rep.get("final") is True,
                         "relatório parcial marcado como GO final: %s" % rep["veredito"])

    def test_A5_go_simulado_nao_satisfaz_entrega(self):
        self.ledger_coerente(ate="ENTREGA")
        self.L.append("medicao_registrada", payload={
            "config": "sistema", "k": 1, "final": False, "run_ids": ["sistema-r1-9"], "sistema_hash": "d" * 64,
            "seq_ultimo_merge": None, "pass_at_k": 1.0, "pass_hat_k": 1.0, "rotulo": "indício", "simulated": True})
        self.relatorio_completo(veredito="GO (simulado)")
        code, out, antes = self.aprovar_entrega()
        self.assertNotEqual(code, 0, "GO (simulado) satisfez a entrega: " + out)
        self.assertEqual(self.L.raw(), antes)


# ====================================================================== A2 — regressao.json5 não desliga o núcleo

class TestA2Regressao(R2Base):
    def editar_regressao(self, fn):
        p = os.path.join(self.ws, "regressao.json5")
        reg = json5_load(p)
        fn(reg)
        self.write_json(p, reg)

    def run_completo(self):
        code, out, err = self.co("portao", "run", "--final")
        self.assertNotIn("Traceback", out + err)
        with open(os.path.join(self.ws, "gate-report.json")) as fh:
            rep = json.load(fh)
        return code, rep, {i["id"]: i for i in rep["itens"]}

    def test_A2_regressao_toda_na_nao_vira_go_no_portao_run(self):
        self.ledger_coerente()

        def tudo_na(reg):
            for it in reg["itens"]:
                it["aplica"], it["na_motivo"], it["cmd"] = False, "desligado", ""
        self.editar_regressao(tudo_na)
        code, rep, item = self.run_completo()
        self.assertEqual(rep["veredito"], "NO-GO", "regressao.json5 editada desligou o núcleo")
        self.assertEqual(code, 1)
        for gid in ("G0", "G1", "G3", "G4"):
            self.assertNotEqual(item.get(gid, {}).get("status"), "NA", "%s tratado como N/A" % gid)

    def test_A2_nucleo_removido_da_regressao_nao_vira_go_no_portao_run(self):
        self.ledger_coerente()
        self.editar_regressao(lambda reg: reg.__setitem__("itens", [
            dict(i, aplica=False, na_motivo="x", cmd="") for i in reg["itens"] if i["id"] not in ("G0", "G1", "G3", "G4")]))
        code, rep, item = self.run_completo()
        self.assertEqual(rep["veredito"], "NO-GO")
        for gid in ("G0", "G1", "G3", "G4"):
            self.assertIn(gid, item, "%s sumiu do relatório" % gid)

    def test_A2_regressao_divergente_de_plano_ok_e_no_go(self):
        self.ledger_coerente()
        self.relatorio_completo()
        code, v = self.veredito()
        self.assertEqual((code, v["veredito"]), (0, "GO"), "controle: regressão intacta é GO")

        def mexe(reg):
            for it in reg["itens"]:
                if it["id"] == "G2":
                    it["cmd"] = "true"
        self.editar_regressao(mexe)
        self.relatorio_completo()
        code, v = self.veredito()
        self.assertEqual((code, v["veredito"]), (1, "NO-GO"), "regressao.json5 ≠ hash gravado em plano_ok")


class TestA2HookRegressao(HookBase):
    def test_A2_construtor_nao_escreve_regressao(self):
        r = os.path.join(self.ws, "regressao.json5")
        self.assertBloqueia(sub(payload("Write", {"file_path": r, "content": "{}"})))
        self.assertBloqueia(sub(bash("echo '{}' > %s" % r)))
        self.assertPermite(sub(payload("Read", {"file_path": r})), "ler a regressão é permitido")


# ====================================================================== A3 — busca recursiva de qualquer ancestral

class TestA3Ancestral(HookBase):
    def setUp(self):
        super().setUp()
        self.fundo = os.path.join(self.tmp, "x", "y", "obra2")
        for d in (".construcao", os.path.join("oraculo", "heldout", "casos")):
            os.makedirs(os.path.join(self.fundo, d))
        open(os.path.join(self.fundo, ".construcao", "ledger.jsonl"), "w").close()
        self.write_json(os.path.join(self.fundo, "oraculo", "heldout", "casos", "C-01.json"), {"id": "h"})

    def test_A3_grep_tool_e_grep_r_a_partir_do_avo(self):
        avo = os.path.join(self.tmp, "x")  # ws em x/y/obra2: não é filho imediato
        self.assertBloqueia(sub(payload("Grep", {"pattern": "h", "path": avo})))
        self.assertBloqueia(sub(bash("grep -rn sentinela %s" % avo)))
        self.assertPermite(sub(payload("Grep", {"pattern": "def", "path": os.path.join(self.alvo, "src")})))


# ====================================================================== A4 — obra/PLANO reescritos não enganam

class TestA4Reescrita(R2Base):
    def test_A4_obra_reescrita_com_suite_falsa_reprova_G1(self):
        self.ledger_coerente()
        code, r, item, out = self.portao("G1")
        self.assertEqual(item["G1"]["status"], "PASS", "controle: suíte registrada passa: " + out)
        self.set_obra(suites=[{"nome": "unit", "cmd": "echo 'Ran 3 tests'"}])
        code, r, item, out = self.portao("G1")
        self.assertIn(item["G1"]["status"], ("FAIL", "ERRO"), "obra.json5 ≠ premissas_ok aceito: " + out)
        self.assertNotEqual(code, 0)

    def test_A4_plano_reescrito_com_writes_amplos_reprova_G3(self):
        self.ledger_coerente(so_t01=True)
        p = os.path.join(self.ws, "PLANO.json5")
        pl = json5_load(p)
        pl["tasks"][0]["writes"] = ["**"]
        self.write_json(p, pl)
        self.wfile("README.md", "# fora do território original\n")
        self.commit()
        self.assertReprova("G3", task="T-01")

    def test_A4_writes_amplos_nao_aprovados_reprovam_G3(self):
        self.ledger_coerente()  # PLANO com T-02 writes ["**"], sem portão humano de plano
        self.wfile("src/core.py", "def soma(a, b):\n    return b + a\n")
        self.commit()
        self.assertAprova(task="T-01")  # controle
        self.assertReprova("G3", task="T-02")

    def test_A4_base_trocada_para_head_na_obra_reprova_G3(self):
        self.ledger_coerente(so_t01=True)
        self.wfile("README.md", "# fora\n")
        self.commit()
        code, r, item, out = self.portao("G3")
        self.assertIn(item["G3"]["status"], ("FAIL", "ERRO"), "controle: fora do território reprova: " + out)
        self.set_obra(base=git(self.alvo, "rev-parse", "HEAD", env=self.env))
        code, r, item, out = self.portao("G3")
        self.assertIn(item["G3"]["status"], ("FAIL", "ERRO"), "base=HEAD na obra reescrita esvaziou o diff: " + out)


# ====================================================================== A6 / A7 — bypass do hook

class TestA6A7Hook(HookBase):
    def test_A6_aprovacao_por_import_alias_git_e_vim(self):
        w = self.ws
        for c in ["cd %s && python3 -c 'import sys, co; co.main(sys.argv[1:])' --work %s oraculo mudar --motivo m "
                  "--evidencia e" % (os.path.dirname(CO), w),
                  "git -c alias.x='!python3 %s --work %s aprovar stop --decisao aprovado' x" % (CO, w),
                  "vim -c '!python3 %s --work %s aprovar stop --decisao aprovado' -c q" % (CO, w)]:
            with self.subTest(cmd=c):
                self.assertBloqueia(sub(bash(c, cwd=self.tmp)))
        self.assertPermite(bash("git -c core.pager=cat log --oneline"))
        self.assertPermite(bash("vim %s/README.md" % self.alvo))

    def test_A7_cd_encadeado_ate_o_heldout(self):
        self.assertBloqueia(sub(bash("cd %s && cd oraculo && cd heldout && cat casos/C-01.json" % self.ws)))
        self.assertPermite(sub(bash("cd %s && cd oraculo && cd dev && cat test_dev.py" % self.ws)))


# ====================================================================== A8 — truncar o fim do ledger

class TestA8Truncamento(R2Base):
    def truncar(self, n):
        linhas = self.L.raw().decode("utf-8").splitlines(True)
        with open(self.L.path, "w", encoding="utf-8") as fh:
            fh.write("".join(linhas[:-n]))

    def test_A8_fim_truncado_diverge_do_cache(self):
        for i in range(3):
            self.assertEqual(self.co("ev", "nota", "--texto", "n%d" % i)[0], 0)
        self.truncar(1)
        antes = self.L.raw()
        code, out, err = self.co("retomar")
        self.assertEqual(code, 1, "ledger truncado passou no retomar: " + out + err)
        code, out, err = self.co("status", "--json")
        self.assertEqual(code, 1, "ledger truncado passou no status: " + out + err)
        code, out, err = self.co("ev", "nota", "--texto", "por cima do truncado")
        self.assertNotEqual(code, 0)
        self.assertEqual(self.L.raw(), antes)

    def test_A8_aprovacao_do_audit_sumida_do_ledger(self):
        self.L.ate_ah_stop()
        code, out, _ = run_tty(["--work", self.ws, "aprovar", "stop", "--decisao", "aprovado"], self.env)
        self.assertEqual(code, 0, out)
        self.truncar(2)  # some com `aprovacao` + transição humana; o audit continua com a linha (seq)
        cache = os.path.join(self.ws, ".construcao", "state.json")
        if os.path.exists(cache):
            os.remove(cache)
        code, out, err = self.co("retomar")
        self.assertEqual(code, 1, "aprovação registrada no audit sumiu do ledger e retomar passou: " + out + err)


# ====================================================================== A9 — aprovar o oráculo congela

class TestA9Congelamento(R2Base):
    def test_A9_oraculo_aprovado_grava_oraculo_congelado_e_G0_passa(self):
        dev = os.path.join(self.ws, "oraculo", "dev")
        self.wfile("test_o.py", "import unittest\n\n\nclass O(unittest.TestCase):\n    def test_a(self):\n"
                   "        self.assertEqual(1, 1)\n", repo=dev)
        self.write_json(os.path.join(self.ws, "oraculo", "MANIFEST.json5"), {
            "schema_version": 1, "frentes": {"T-01": {"autores": ["oraculo-O1"], "dev": ["oraculo/dev/**"],
                                                      "heldout": ["oraculo/heldout/**"]}},
            "construtores": {}, "congelado": None})
        camp = os.path.join(self.ws, "campanhas", "construcao")
        p = subprocess.run([sys.executable, AC, "--work", camp, "init", "--target", self.alvo, "--scope", "src/**",
                            "--problem", "p", "--stop", "s", "--max-rounds", "3"], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True, env=self.env, timeout=60)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.L.ate_oraculo()
        self.L.t("oraculo_pronto", "ORACULO", "AGUARDANDO_HUMANO", "orquestrador")
        code, out, _ = run_tty(["--work", self.ws, "aprovar", "oraculo", "--decisao", "aprovado"], self.env)
        self.assertEqual(code, 0, out)
        recs = self.L.records()
        tr = [r for r in recs if r["evento"] == "aprovado" and r["para"] == "BASELINE"]
        self.assertTrue(tr)
        cong = [r for r in recs if r["evento"] == "oraculo_congelado" and r["seq"] > tr[-1]["seq"]]
        self.assertTrue(cong, "aprovar o oráculo não gravou oraculo_congelado")
        pl = cong[-1]["payload"]
        self.assertTrue(HEX64.match(pl["hash"]))
        self.assertGreaterEqual(pl["n_testes"], 1)
        self.assertGreaterEqual(pl["n_assercoes"], 1)
        self.assertIsNotNone(self.status()["oraculo"])
        with open(os.path.join(camp, ".auto-correcao", "state.json")) as fh:
            self.assertTrue((json.load(fh).get("oracle") or {}).get("hash"), "ac.py oracle freeze não rodou")
        self.gerar_regressao()
        code, r, item, out = self.portao("G0")
        self.assertEqual(item["G0"]["status"], "PASS", out)


if __name__ == "__main__":
    unittest.main()
