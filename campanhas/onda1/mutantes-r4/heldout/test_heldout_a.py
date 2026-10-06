"""HELD-OUT frente A (co_estado/co.py) — oráculo O1, onda 1. Não visível ao construtor (hook bloqueia leitura).
Variações de adulteração da cadeia, write-ahead (D3), teto de tentativas da task, invariantes plantados restantes,
e "nada é gravado" estendido ao cache e ao RETOMAR.md."""
import json
import os
import sys
import unittest

VIS = os.path.expanduser("~/.claude/skills/construcao-orquestrada/tests/onda1")
sys.path.insert(0, os.path.realpath(VIS))
from _comum import cadeia_problemas, maquina, now_ts, rec_hash, sha_obj  # noqa: E402
from test_a_estado import EstadoBase  # noqa: E402


class HeldoutCadeia(EstadoBase):
    def _notas(self, n=3):
        L = self.init()
        for i in range(n):
            self.assertEqual(self.ev("nota", "--texto", "n%d" % i)[0], 0)
        return L

    def test_retomar_com_linha_do_meio_removida_sai_1(self):
        L = self._notas()
        linhas = L.raw().decode("utf-8").splitlines(True)
        del linhas[2]
        with open(L.path, "w", encoding="utf-8") as fh:
            fh.write("".join(linhas))
        code, out, err = self.co("retomar")
        self.assertEqual(code, 1, out + err)

    def test_retomar_com_cadeia_reencadeada_mas_payload_hash_velho_sai_1(self):
        L = self._notas()
        recs = L.records()
        recs[1]["payload"] = {"texto": "reescrito"}  # payload_hash fica velho; hash/prev recalculados em toda a cadeia
        prev = "0"
        for r in recs:
            r["prev"] = prev
            r["hash"] = rec_hash(r)
            prev = r["hash"]
        with open(L.path, "w", encoding="utf-8") as fh:
            for r in recs:
                fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
        self.assertTrue(cadeia_problemas(recs))
        code, out, err = self.co("retomar")
        self.assertEqual(code, 1, out + err)

    def test_retomar_com_seq_com_lacuna_sai_1(self):
        L = self._notas()
        recs = L.records()
        recs[-1]["seq"] += 1
        recs[-1]["hash"] = rec_hash(recs[-1])
        with open(L.path, "w", encoding="utf-8") as fh:
            for r in recs:
                fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
        code, out, err = self.co("retomar")
        self.assertEqual(code, 1, out + err)

    def test_guarda_falsa_nao_toca_cache_nem_retomar_md(self):
        L = self.init()
        self.assertEqual(self.ev("nota", "--texto", "gera cache")[0], 0)
        L.ate_replanejar(replanejamentos=2)
        self.status()
        arqs = [os.path.join(self.ws, ".construcao", "state.json"), os.path.join(self.ws, "RETOMAR.md")]
        antes = [open(a, "rb").read() if os.path.exists(a) else None for a in arqs]
        led = L.raw()
        code, out, err = self.ev("novo_plano")
        self.assertEqual(code, 1, out + err)
        self.assertEqual(L.raw(), led)
        self.assertEqual([open(a, "rb").read() if os.path.exists(a) else None for a in arqs], antes)

    def test_status_com_cache_atrasado_refaz_do_ledger(self):
        # R3-3: cache AUSENTE com ledger não vazio é incoerente (exit 1). Cache ATRASADO (ledger andou além dele)
        # é legítimo: o status refaz o fold do ledger.
        L = self.init()
        L.ate_plano()
        self.assertTrue(os.path.isfile(os.path.join(self.ws, ".construcao", "state.json")))
        self.assertEqual(self.status()["obra"]["estado"], "PLANO")

    def test_ev_payload_json_invalido_sai_2(self):
        L = self.init()
        L.ate_plano()
        f = os.path.join(self.tmp, "ruim.json")
        with open(f, "w") as fh:
            fh.write("{causa: ")
        antes = L.raw()
        code, out, err = self.ev("limite_uso", "--payload", f)
        self.assertEqual(code, 2, out + err)
        self.assertEqual(L.raw(), antes)


class HeldoutWriteAhead(EstadoBase):
    def test_queda_entre_despachada_e_task_despachar_fecha_vaga_e_task_segue_pronta(self):
        L = self.init()
        L.ate_lote()
        chave = "obra/1/T-01/1"
        L.tt("T-01", "task.pronta", "PENDENTE", "PRONTA", "script")
        L.t("lote_ok", "LOTE", "DESPACHADO", "orquestrador")
        L.append("despachada", chave=chave, task="T-01",
                 payload={"task": "T-01", "papel": "construtor", "chave": chave, "agent_type": "builder-A",
                          "writes": ["src/**"], "reads": [], "tentativa": 1, "brief_hash": "9" * 64,
                          "isolation": None, "teto_vigente": 5, "vivos_antes": 0})
        self.assertEqual(self.status()["vivos"], [chave])
        code, out, err = self.co("retomar")
        self.assertEqual(code, 0, out + err)
        perd = [r for r in L.records() if r["evento"] == "perdida"]
        self.assertTrue(perd)
        self.assertEqual(perd[-1]["payload"]["chave"], chave)
        st = self.status()
        self.assertEqual(st["vivos"], [])
        self.assertEqual(st["tasks"]["T-01"]["estado"], "PRONTA")
        self.assertEqual(st["tasks"]["T-01"]["tentativas"], 0)

    def test_task_perdida_com_tentativas_no_teto_vai_para_rejeitada(self):
        L = self.init()
        L.ate_lote()
        L.tt("T-01", "task.pronta", "PENDENTE", "PRONTA", "script")
        L.t("lote_ok", "LOTE", "DESPACHADO", "orquestrador")
        for i in range(1, 5):
            chave = "obra/1/T-01/%d" % i
            L.append("despachada", chave=chave, task="T-01",
                     payload={"task": "T-01", "papel": "construtor", "chave": chave, "agent_type": "builder-A",
                              "writes": ["src/**"], "reads": [], "tentativa": i, "brief_hash": "9" * 64,
                              "isolation": None, "teto_vigente": 5, "vivos_antes": 0})
            L.tt("T-01", "task.despachar", "PRONTA", "EM_VOO", "orquestrador", chave=chave, payload={"chave": chave})
            if i < 4:
                L.append("perdida", chave=chave, task="T-01",
                         payload={"task": "T-01", "chave": chave, "tentativa_nova": i + 1})
                L.tt("T-01", "task.perdida", "EM_VOO", "PRONTA", "script", chave=chave)
        st = self.status()
        self.assertEqual((st["tasks"]["T-01"]["estado"], st["tasks"]["T-01"]["tentativas"]), ("EM_VOO", 3))
        code, out, err = self.co("retomar")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.status()["tasks"]["T-01"]["estado"], "REJEITADA")


class HeldoutMaquina(EstadoBase):
    def check(self, m, nivel="todos"):
        f = self.write_json(os.path.join(self.tmp, "maquina-plantada.json"), m)
        return self.co("maquina", "check", "--machine", f, "--nivel", nivel)

    def assertViola(self, m, inv, nivel="todos"):
        code, out, err = self.check(m, nivel)
        self.assertEqual(code, 1, "máquina plantada (%s) aceita: %s" % (inv, out + err))
        self.assertLimpo(out, err)
        self.assertIn(inv, out + err, "relatório não aponta %s" % inv)

    def test_I6_transicao_de_script_saindo_de_aguardando_humano(self):
        m = maquina()
        m["niveis"]["obra"]["transitions"]["auto_entrega"] = {
            "evento": "auto", "from": ["AGUARDANDO_HUMANO"], "to": "ENTREGUE", "actor": "script", "guard": "true"}
        self.assertViola(m, "I6")

    def test_I6_guarda_humana_com_ator_orquestrador(self):
        m = maquina()
        m["niveis"]["obra"]["transitions"]["stop_aprovado"]["actor"] = "orquestrador"
        self.assertViola(m, "I6")

    def test_I7_estavel_saindo_sem_motivo_no_nivel_task(self):
        m = maquina()
        m["niveis"]["task"]["transitions"]["reabrir"]["motivo_obrigatorio"] = False
        self.assertViola(m, "I7", nivel="task")

    def test_S2_ator_desconhecido(self):
        m = maquina()
        m["niveis"]["obra"]["transitions"]["verde"]["actor"] = "robo"
        self.assertViola(m, "S2")

    def test_S3_terminal_com_saida(self):
        m = maquina()
        m["niveis"]["obra"]["transitions"]["reabrir_obra"] = {
            "evento": "reabrir_obra", "from": ["ENTREGUE"], "to": "PLANO", "actor": "orquestrador", "guard": "true"}
        code, out, err = self.check(m)
        self.assertEqual(code, 1, out + err)
        self.assertRegex(out + err, r"S3|I7")

    def test_I4_campanha_reintegrar_sem_incrementa(self):
        m = maquina()
        del m["niveis"]["campanha"]["transitions"]["reintegrar"]["incrementa"]
        self.assertViola(m, "I4", nivel="campanha")

    def test_nivel_obra_isolado_nao_acusa_defeito_plantado_so_na_task(self):
        m = maquina()
        m["niveis"]["task"]["transitions"]["reabrir"]["motivo_obrigatorio"] = False
        code, out, err = self.check(m, nivel="obra")
        self.assertEqual(code, 0, out + err)
        self.assertViola(m, "I7", nivel="todos")


if __name__ == "__main__":
    unittest.main()
