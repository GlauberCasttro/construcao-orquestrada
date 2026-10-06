"""Rodada 3 da onda 1: achados R3-3..R3-10 do 2º verificador cego. Oráculo O1. Cada teste falha no código
anterior à correção do achado; controles positivos no mesmo teste quando cabe. Ver ESPEC.md, seção "Rodada 3".
(R3-1/R3-2, forja de aprovação por import/pty, ficam para a frase-senha da auto-correcao v0.4 — não cobertos aqui.)"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comum import (CO, Ledger, bash, json5_load, maquina, payload, rec_hash, run_tty, sha_file, sha_obj, sub,  # noqa: E402
                    HookBase)
from test_a_estado import EstadoBase  # noqa: E402
from test_r2_achados import R2Base  # noqa: E402


def recadeia(L, fn):
    """Reescreve o ledger aplicando fn(registros) e recalcula payload_hash/prev/hash de TODA a cadeia
    (falsificação completa — só testemunhas externas ao ledger podem acusar)."""
    recs = L.records()
    fn(recs)
    prev = "0"
    for i, r in enumerate(recs, 1):
        r["seq"] = i
        r["payload_hash"] = sha_obj(r["payload"])
        r["prev"] = prev
        r["hash"] = rec_hash(r)
        prev = r["hash"]
    with open(L.path, "w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


# ====================================================================== R3-3 testemunha apagada

class TestR3_3Testemunha(EstadoBase):
    def _obra_com_notas(self):
        L = self.init()
        for i in range(3):
            self.assertEqual(self.co("ev", "nota", "--texto", "n%d" % i)[0], 0)
        self.assertEqual(self.co("status", "--json")[0], 0, "controle: obra íntegra com cache")
        return L

    def test_R3_3_ledger_reescrito_e_cache_apagado_sai_1(self):
        L = self._obra_com_notas()

        def falsifica(recs):
            for r in recs:
                if r["evento"] == "nota" and r["payload"].get("texto") == "n1":
                    r["payload"] = {"texto": "reescrito"}
            del recs[-1]
        recadeia(L, falsifica)
        os.remove(os.path.join(self.ws, ".construcao", "state.json"))
        antes = L.raw()
        self.assertEqual(self.co("status", "--json")[0], 1, "testemunha apagada não acusou o ledger reescrito")
        self.assertNotEqual(self.co("ev", "nota", "--texto", "por cima")[0], 0)
        self.assertEqual(L.raw(), antes)
        self.assertEqual(self.co("retomar")[0], 1)

    def test_R3_3_cache_ausente_com_ledger_nao_vazio_e_incoerente(self):
        L = self._obra_com_notas()
        os.remove(os.path.join(self.ws, ".construcao", "state.json"))
        antes = L.raw()
        code, out, err = self.co("status", "--json")
        self.assertEqual(code, 1, out + err)
        self.assertNotEqual(self.co("ev", "nota", "--texto", "x")[0], 0)
        self.assertEqual(L.raw(), antes)


# ====================================================================== R3-5 hash escolhido pelo agente

class TestR3_5HashDoMotor(EstadoBase):
    def _premissas(self):
        L = self.init()
        p = os.path.join(self.ws, "obra.json5")
        obra = json5_load(p)
        obra["stop"]["numerico"] = {"metrica": "pass_hat_3", "op": ">=", "valor": 1.0}
        self.write_json(p, obra)
        self.write_json(os.path.join(self.ws, "pontos.json5"), {"schema_version": 1, "pontos": [
            {"id": "P-01", "texto": "soma", "origem": "pedido", "status": "coberto", "cenarios": ["C-01"],
             "motivo": None}]})
        L.ate_premissas()
        return L

    def test_R3_5_premissas_ok_ignora_ou_recusa_hash_do_payload(self):
        L = self._premissas()
        f = self.write_json(os.path.join(self.tmp, "pl.json"),
                            {"obra_hash": "0" * 64, "pontos_hash": "0" * 64, "pontos_ids": ["P-01"]})
        antes = L.raw()
        code, out, err = self.co("ev", "premissas_ok", "--payload", f)
        if code == 0:
            pl = [r for r in L.records() if r["evento"] == "premissas_ok"][-1]["payload"]
            self.assertEqual(pl["obra_hash"], sha_file(os.path.join(self.ws, "obra.json5")),
                             "obra_hash veio do agente, não do disco")
            self.assertEqual(pl["pontos_hash"], sha_file(os.path.join(self.ws, "pontos.json5")))
        else:
            self.assertEqual(L.raw(), antes)

    def test_R3_5_premissas_ok_sem_payload_grava_hash_do_disco(self):
        L = self._premissas()
        code, out, err = self.co("ev", "premissas_ok")
        self.assertEqual(code, 0, out + err)
        pl = [r for r in L.records() if r["evento"] == "premissas_ok"][-1]["payload"]
        self.assertIn("obra_hash", pl, "o motor não calculou obra_hash do disco")
        self.assertEqual(pl["obra_hash"], sha_file(os.path.join(self.ws, "obra.json5")))


# ====================================================================== R3-6 G1 com suíte que só imprime

class TestR3_6SuiteFalsa(R2Base):
    def test_R3_6_suite_registrada_que_so_imprime_nao_passa(self):
        for cmd in ("echo ok fake", "echo 'Ran 7 tests'"):
            with self.subTest(cmd=cmd):
                self.tearDown()
                self.setUp()
                self.ledger_coerente(suite=cmd)
                code, r, item, out = self.portao("G1")
                self.assertIn(item["G1"]["status"], ("FAIL", "ERRO"), "saída impressa contou como teste: " + out)

    def test_R3_6_controle_suite_unittest_real_passa(self):
        self.ledger_coerente()
        code, r, item, out = self.portao("G1")
        self.assertEqual(item["G1"]["status"], "PASS", out)


# ====================================================================== R3-7 I4 com contador zerado no ciclo

class TestR3_7CicloComZera(EstadoBase):
    def test_R3_7_contador_zerado_dentro_do_ciclo_nao_e_teto(self):
        m = maquina()
        m["niveis"]["obra"]["transitions"]["fronteira_vazia"]["zera"] = ["tentativas"]
        f = self.write_json(os.path.join(self.tmp, "m.json"), m)
        code, out, err = self.co("maquina", "check", "--machine", f, "--nivel", "obra")
        self.assertEqual(code, 1, "laço CORRIGIR→LOTE→INTEGRAR→CORRIGIR zera o próprio teto e passou: " + out + err)
        self.assertIn("I4", out + err)
        self.assertEqual(self.co("maquina", "check")[0], 0, "controle: máquina real passa")


# ====================================================================== R3-8 G4 com variações

class TestR3_8Gaming(R2Base):
    def test_R3_8_skip_importado_e_exit_por_getattr(self):
        for src in ("from pytest import skip\n\n\ndef soma(a, b):\n    skip()\n    return a + b\n",
                    "import sys\n\n\ndef soma(a, b):\n    getattr(sys, 'exit')(0)\n"):
            with self.subTest(src=src[:40]):
                self.tearDown()
                self.setUp()
                self.wfile("src/core.py", src)
                self.commit()
                self.assertReprova("G4")


# ====================================================================== R3-4 / R3-9 hook

class TestR3_4Caixa(HookBase):
    def test_R3_4_heldout_e_protegidos_com_outra_caixa(self):
        w = self.ws
        self.assertBloqueia(sub(payload("Read", {"file_path": os.path.join(w, "oraculo", "HELDOUT", "casos",
                                                                            "C-01.json")})))
        self.assertBloqueia(sub(bash("cat %s/oraculo/HeldOut/casos/C-01.json" % w)))
        self.assertBloqueia(payload("Write", {"file_path": os.path.join(w, ".CONSTRUCAO", "ledger.jsonl"),
                                              "content": "x"}))
        self.assertBloqueia(bash("rm %s/.CONSTRUCAO/state.json" % w))
        self.assertPermite(sub(payload("Read", {"file_path": os.path.join(w, "oraculo", "DEV", "test_dev.py")})))


class TestR3_9Git(HookBase):
    def test_R3_9_git_lendo_heldout(self):
        w = self.ws
        for c in ["git -C %s diff --no-index /dev/null oraculo/heldout/casos/C-01.json" % w,
                  "git --work-tree=%s show HEAD:oraculo/heldout/casos/C-01.json" % w]:
            with self.subTest(cmd=c):
                self.assertBloqueia(sub(bash(c)))
        self.assertPermite(sub(bash("git -C %s diff --stat" % self.alvo)))


# ====================================================================== R3-10 entrega cruza o audit

class TestR3_10EntregaAudit(R2Base):
    def test_R3_10_aprovacao_sem_audit_nao_libera_entrega(self):
        self.ledger_coerente(ate="ENTREGA")
        self.relatorio_completo()
        os.remove(self.audit)  # as `aprovacao` do ledger ficam sem a linha tipo aprovacao do audit
        antes = self.L.raw()
        code, out, _ = run_tty(["--work", self.ws, "aprovar", "entrega", "--decisao", "aprovado"], self.env)
        self.assertNotEqual(code, 0, "entrega aprovada com aprovações sem audit: " + out)
        self.assertEqual(self.L.raw(), antes)


if __name__ == "__main__":
    unittest.main()
