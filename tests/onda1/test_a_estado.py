"""Frente A — co_estado.py via co.py: init, ledger encadeado, fold, ev (guardas, contadores, I6), status, retomar,
RETOMAR.md, write-ahead/em voo perdida, maquina check. Oráculo O1 (onda 1). Ver ESPEC.md."""
import copy
import json
import os
import re
import stat
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comum import (CABECALHO_RETOMAR, CAMPOS_LEDGER, CO, CO_ESTADO, CO_HOOK, HEX64, REFS, SECOES_RETOMAR, TS_RE,  # noqa: E402
                    Base, Ledger, cadeia_problemas, hash_estado_de, json5_load, maquina, now_ts, rec_hash, sha_file,
                    sha_obj)


class EstadoBase(Base):
    exige = (CO, CO_ESTADO)

    def ev(self, *argv):
        return self.co("ev", *argv)

    def payload_file(self, obj, nome="payload.json"):
        return self.write_json(os.path.join(self.tmp, nome), obj)

    def assertInalterado(self, L, antes, code, out, err, esperado):
        self.assertEqual(code, esperado, out + err)
        self.assertEqual(L.raw(), antes, "ledger mudou numa transição recusada (deveria ser idêntico byte a byte)")


# ====================================================================== init + gênese

class TestInit(EstadoBase):
    def test_init_cria_obra_pontos_e_genese_no_formato(self):
        L = self.init()
        obra = json5_load(os.path.join(self.ws, "obra.json5"))
        self.assertEqual(obra["alvo"], self.alvo)
        self.assertEqual(os.path.realpath(obra["workspace"]), self.ws)
        self.assertEqual(obra["tipo"], "cli")
        self.assertEqual(obra["pedido"], "CLI que soma")
        self.assertEqual(obra["stop"]["texto"], "pass_hat_3 >= 1.0")
        self.assertEqual(obra["max_rodadas"], 3)
        self.assertEqual(obra["teto"], 5)
        self.assertEqual(obra["contrato_hash"], sha_file(os.path.join(REFS, "contrato.json5")))
        self.assertEqual(obra["maquina_hash"], sha_file(os.path.join(REFS, "maquina.json5")))
        self.assertTrue(TS_RE.match(obra["criado_em"]))
        self.assertEqual(json5_load(os.path.join(self.ws, "pontos.json5"))["pontos"], [])
        g = L.records()[0]
        self.assertEqual(list(sorted(g.keys())), sorted(CAMPOS_LEDGER))
        self.assertEqual((g["seq"], g["prev"], g["evento"], g["ator"], g["nivel"], g["de"], g["para"]),
                         (1, "0", "genese", "script", "operacional", None, None))
        self.assertEqual(g["payload"], {"alvo": self.alvo, "tipo": "cli", "contrato_hash": obra["contrato_hash"],
                                        "maquina_hash": obra["maquina_hash"]})
        self.assertEqual(g["payload_hash"], sha_obj(g["payload"]))
        self.assertEqual(g["hash"], rec_hash(g))
        self.assertEqual(cadeia_problemas(L.records()), [])

    def test_init_workspace_dentro_do_alvo_sai_2_e_nada_cria(self):
        dentro = os.path.join(self.alvo, "obra")
        code, out, err = self.co("init", "--alvo", self.alvo, "--tipo", "cli", "--pedido", "p", "--stop", "s",
                                 work=dentro)
        self.assertEqual(code, 2, out + err)
        self.assertFalse(os.path.exists(os.path.join(dentro, ".construcao")), "criou estado dentro do alvo")
        self.assertFalse(os.path.exists(os.path.join(dentro, "obra.json5")))
        self.init()  # controle: fora do alvo funciona

    def test_init_tipo_invalido_sai_2(self):
        code, out, err = self.co("init", "--alvo", self.alvo, "--tipo", "repo", "--pedido", "p", "--stop", "s")
        self.assertEqual(code, 2, out + err)
        self.assertFalse(os.path.exists(os.path.join(self.ws, ".construcao", "ledger.jsonl")))

    def test_init_em_obra_existente_nao_reescreve_o_ledger(self):
        L = self.init()
        antes = L.raw()
        code, out, err = self.co("init", "--alvo", self.alvo, "--tipo", "cli", "--pedido", "outro", "--stop", "s")
        self.assertNotEqual(code, 0, "init sobre obra existente não pode passar: " + out + err)
        self.assertEqual(L.raw(), antes)


# ====================================================================== ledger, fold, status

class TestLedgerEFold(EstadoBase):
    def test_cada_ev_estende_a_cadeia_pela_regra_de_formatos(self):
        L = self.init()
        for i in range(3):
            code, out, err = self.ev("nota", "--texto", "nota %d" % i)
            self.assertEqual(code, 0, out + err)
            self.assertLimpo(out, err)
        recs = L.records()
        self.assertEqual(cadeia_problemas(recs), [])
        notas = [r for r in recs if r["evento"] == "nota"]
        self.assertEqual([n["payload"] for n in notas], [{"texto": "nota %d" % i} for i in range(3)])
        for n in notas:
            self.assertEqual((n["ator"], n["nivel"], n["de"], n["para"]), ("script", "operacional", None, None))

    def test_nota_nao_muda_estado_nem_hash_estado(self):
        self.init()
        a = self.status()
        code, out, err = self.ev("nota", "--texto", "só narrativa")
        self.assertEqual(code, 0, out + err)
        b = self.status()
        self.assertEqual(a["obra"], b["obra"])
        self.assertEqual(a["hash_estado"], b["hash_estado"])
        self.assertGreater(b["ledger_seq"], a["ledger_seq"])

    def test_status_json_tem_os_campos_e_hash_estado_D8(self):
        L = self.init()
        st = self.status()
        for k in ["schema_version", "ledger_seq", "ledger_hash", "obra", "contadores", "constantes", "teto_vigente",
                  "vivos", "tasks", "campanhas", "contrato_hash", "oraculo", "janela", "retomar_apos", "trava",
                  "simulado", "hash_estado"]:
            self.assertIn(k, st)
        self.assertEqual(st["obra"], {"estado": "INICIO", "portao": None, "retorno": None})
        self.assertEqual(st["ledger_seq"], L.last()["seq"])
        self.assertEqual(st["ledger_hash"], L.last()["hash"])
        self.assertEqual(st["contadores"], {"tentativas": 0, "rodada": 0, "replanejamentos": 0, "pausas": 0,
                                            "despachos": 0})
        self.assertEqual(st["constantes"], maquina()["constantes"])
        self.assertEqual(st["teto_vigente"], 5)
        self.assertEqual(st["vivos"], [])
        self.assertTrue(HEX64.match(st["hash_estado"]))
        self.assertEqual(st["hash_estado"], hash_estado_de(st))

    def test_ledger_vence_o_cache_adulterado(self):
        L = self.init()
        self.ev("nota", "--texto", "gera o cache")
        cache = os.path.join(self.ws, ".construcao", "state.json")
        self.assertTrue(os.path.isfile(cache), "state.json (cache do fold) não foi gravado")
        with open(cache) as fh:
            st = json.load(fh)
        st["obra"]["estado"] = "ENTREGUE"
        with open(cache, "w") as fh:
            json.dump(st, fh)
        code, out, err = self.co("status", "--json")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(json.loads(out)["obra"]["estado"], "INICIO", "status leu o cache, não o fold")
        self.assertRegex((out + err).lower(), r"cache|diverg", "não avisou a divergência cache × fold")
        self.assertEqual(L.records()[-1]["evento"], "nota")

    def test_fold_dobra_registros_validos_gravados_no_ledger(self):
        L = self.init()
        L.ate_lote()
        st = self.status()
        self.assertEqual(st["obra"]["estado"], "LOTE")
        self.assertEqual(st["oraculo"]["hash"], "f" * 64)
        self.assertEqual((st["oraculo"]["n_testes"], st["oraculo"]["n_assercoes"]), (1, 1))
        self.assertEqual(st["contrato_hash"], "a" * 64)
        L.lote_ate_verificar_tent3()
        st = self.status()
        self.assertEqual(st["obra"]["estado"], "VERIFICAR")
        self.assertEqual(st["contadores"]["tentativas"], 3)
        self.assertEqual(st["ledger_hash"], L.last()["hash"])

    def test_ah_guarda_portao_e_retorno_no_fold(self):
        L = self.init()
        L.ate_ah_stop()
        st = self.status()
        self.assertEqual(st["obra"], {"estado": "AGUARDANDO_HUMANO", "portao": "stop", "retorno": None})


# ====================================================================== ev: guardas, I6, contadores com teto

class TestEvGuardas(EstadoBase):
    def test_iniciar_sem_hook_vivo_sai_1_e_ledger_byte_a_byte(self):
        L = self.init()
        antes = L.raw()
        code, out, err = self.ev("iniciar")
        self.assertInalterado(L, antes, code, out, err, 1)
        self.assertEqual(self.status()["obra"]["estado"], "INICIO")

    def test_transicao_humana_via_ev_sai_2_D9_I6(self):
        L = self.init()
        L.ate_ah_stop()
        for evento in ("aprovado", "rejeitado", "abandonar"):
            antes = L.raw()
            code, out, err = self.ev(evento)
            self.assertInalterado(L, antes, code, out, err, 2)
            self.assertLimpo(out, err)
        self.assertEqual(self.status()["obra"]["estado"], "AGUARDANDO_HUMANO")
        code, out, err = self.ev("nota", "--texto", "controle: ev funciona neste estado")
        self.assertEqual(code, 0, out + err)

    def test_evento_inexistente_sai_2(self):
        L = self.init()
        antes = L.raw()
        code, out, err = self.ev("voar_para_entregue")
        self.assertInalterado(L, antes, code, out, err, 2)
        self.assertLimpo(out, err)

    def test_evento_que_nao_sai_do_estado_atual_nao_grava(self):
        L = self.init()
        antes = L.raw()
        code, out, err = self.ev("merge_ok")
        self.assertIn(code, (1, 2), out + err)
        self.assertLimpo(out, err)
        self.assertEqual(L.raw(), antes)

    def test_vermelho_com_tentativas_no_teto_vai_para_replanejar(self):
        L = self.init()
        L.ate_lote()
        L.lote_ate_verificar_tent3()
        code, out, err = self.ev("vermelho")
        self.assertEqual(code, 0, out + err)
        st = self.status()
        self.assertEqual(st["obra"]["estado"], "REPLANEJAR")
        t = [r for r in L.records() if r["evento"] == "vermelho"][-1]
        self.assertEqual((t["de"], t["para"], t["ator"], t["nivel"]), ("VERIFICAR", "REPLANEJAR", "script", "obra"))
        self.assertEqual(cadeia_problemas(L.records()), [])

    def test_campanhas_abertas_com_tentativas_no_teto_vai_para_replanejar(self):
        L = self.init()
        L.ate_lote()
        L.lote_ate_corrigir_tent3()
        self.assertEqual(self.status()["contadores"]["tentativas"], 3)
        code, out, err = self.ev("campanhas_abertas")
        self.assertEqual(code, 0, out + err)
        st = self.status()
        self.assertEqual(st["obra"]["estado"], "REPLANEJAR", "teto de tentativas ignorado")
        self.assertEqual(st["contadores"]["tentativas"], 3)

    def test_novo_plano_incrementa_replanejamentos_e_zera_tentativas(self):
        L = self.init()
        L.ate_replanejar()
        code, out, err = self.ev("novo_plano")
        self.assertEqual(code, 0, out + err)
        st = self.status()
        self.assertEqual(st["obra"]["estado"], "PLANO")
        self.assertEqual(st["contadores"]["replanejamentos"], 1)
        self.assertEqual(st["contadores"]["tentativas"], 0)

    def test_novo_plano_no_teto_sai_1_e_ledger_inalterado(self):
        L = self.init()
        L.ate_replanejar(replanejamentos=2)
        st = self.status()
        self.assertEqual((st["obra"]["estado"], st["contadores"]["replanejamentos"]), ("REPLANEJAR", 2))
        antes = L.raw()
        code, out, err = self.ev("novo_plano")
        self.assertInalterado(L, antes, code, out, err, 1)
        self.assertEqual(self.status()["obra"]["estado"], "REPLANEJAR")

    def test_desistir_vai_para_ah_abandonar_e_gera_aprovar_sh(self):
        L = self.init()
        L.ate_replanejar()
        code, out, err = self.ev("desistir")
        self.assertEqual(code, 0, out + err)
        st = self.status()
        self.assertEqual((st["obra"]["estado"], st["obra"]["portao"]), ("AGUARDANDO_HUMANO", "abandonar"))
        sh = os.path.join(self.ws, "aprovacoes", "aprovar-abandonar.sh")
        self.assertTrue(os.path.isfile(sh), "aprovar-<portao>.sh não foi gerado ao entrar em AGUARDANDO_HUMANO")
        with open(sh, encoding="utf-8") as fh:
            txt = fh.read()
        self.assertTrue(txt.startswith("#!/bin/sh\n"))
        self.assertIn(st["hash_estado"], txt)
        for dec in ("aprovado", "rejeitado", "abandonar"):
            self.assertRegex(txt, r"co\.py --work %s aprovar abandonar --decisao %s" % (re.escape(self.ws), dec))
        self.assertEqual(stat.S_IMODE(os.stat(sh).st_mode) & 0o077, 0, "aprovar-*.sh deve ser chmod 600")
        self.assertEqual(stat.S_IMODE(os.stat(sh).st_mode) & 0o111, 0, "aprovar-*.sh não pode ser executável")


class TestPausa(EstadoBase):
    def limite(self, causa, offset):
        f = self.payload_file({"causa": causa, "retomar_apos": now_ts(offset), "mensagem": "429"})
        return self.ev("limite_uso", "--payload", f)

    def test_limite_uso_rate_limit_pausa_incrementa_e_recua_o_teto(self):
        L = self.init()
        L.ate_plano()
        h0 = self.status()["hash_estado"]
        code, out, err = self.limite("rate_limit", -60)
        self.assertEqual(code, 0, out + err)
        st = self.status()
        self.assertEqual(st["obra"], {"estado": "PAUSADO", "portao": None, "retorno": "PLANO"})
        self.assertEqual(st["contadores"]["pausas"], 1)
        self.assertEqual(st["teto_vigente"], 3)
        self.assertIn("teto_recuado", L.eventos())
        self.assertNotEqual(st["hash_estado"], h0)

    def test_limite_uso_por_janela_nao_recua_o_teto(self):
        L = self.init()
        L.ate_plano()
        code, out, err = self.limite("janela", -60)
        self.assertEqual(code, 0, out + err)
        st = self.status()
        self.assertEqual(st["teto_vigente"], 5)
        self.assertNotIn("teto_recuado", L.eventos())

    def test_retomar_volta_ao_retorno_e_recuo_dura_o_resto_da_obra(self):
        L = self.init()
        L.ate_plano()
        self.assertEqual(self.limite("rate_limit", -60)[0], 0)
        code, out, err = self.ev("retomar")
        self.assertEqual(code, 0, out + err)
        st = self.status()
        self.assertEqual(st["obra"]["estado"], "PLANO")
        self.assertEqual(st["teto_vigente"], 3)

    def test_retomar_antes_do_prazo_sai_1_e_ledger_inalterado(self):
        L = self.init()
        L.ate_plano()
        self.assertEqual(self.limite("janela", 3600)[0], 0)
        antes = L.raw()
        code, out, err = self.ev("retomar")
        self.assertInalterado(L, antes, code, out, err, 1)
        self.assertEqual(self.status()["obra"]["estado"], "PAUSADO")

    def test_retomar_com_pausas_no_teto_vai_para_ah_continuar(self):
        L = self.init()
        L.ate_plano()
        passado = {"causa": "janela", "retomar_apos": now_ts(-3600), "mensagem": "m"}
        for _ in range(5):
            L.t("limite_uso", "PLANO", "PAUSADO", "script", payload=passado)
            L.t("retomar", "PAUSADO", "PLANO", "orquestrador")
        L.t("limite_uso", "PLANO", "PAUSADO", "script", payload=passado)
        self.assertEqual(self.status()["contadores"]["pausas"], 6)
        code, out, err = self.ev("retomar")
        self.assertEqual(code, 0, out + err)
        st = self.status()
        self.assertEqual((st["obra"]["estado"], st["obra"]["portao"]), ("AGUARDANDO_HUMANO", "continuar"),
                         "teto de pausas (MAX_PAUSAS=6) ignorado")


# ====================================================================== RETOMAR.md, retomar, write-ahead

class TestRetomada(EstadoBase):
    def ler_retomar(self):
        p = os.path.join(self.ws, "RETOMAR.md")
        self.assertTrue(os.path.isfile(p), "RETOMAR.md não foi gerado")
        with open(p, encoding="utf-8") as fh:
            return fh.read()

    def assertRetomarValido(self, L):
        txt = self.ler_retomar()
        m = CABECALHO_RETOMAR.search(txt.splitlines()[0])
        self.assertTrue(m, "cabeçalho fora do formato: %r" % txt.splitlines()[0])
        self.assertEqual(int(m.group(1)), L.last()["seq"])
        self.assertEqual(m.group(2), L.last()["hash"], "RETOMAR.md não reflete o último registro do ledger")
        pos = [txt.find("\n" + s + "\n") for s in SECOES_RETOMAR]
        self.assertTrue(all(p >= 0 for p in pos), "seções faltando: %s" % pos)
        self.assertEqual(pos, sorted(pos), "seções fora da ordem")
        prox = txt.split("\n## Próximo comando\n", 1)[1]
        bloco = re.search(r"```[^\n]*\n(.*?)```", prox, re.S)
        self.assertTrue(bloco, "Próximo comando sem bloco ```")
        linhas = [x for x in bloco.group(1).splitlines() if x.strip()]
        self.assertEqual(len(linhas), 1, "Próximo comando deve ter exatamente 1 comando: %r" % linhas)
        return txt

    def test_retomar_md_regenerado_a_cada_ev(self):
        L = self.init()
        self.assertEqual(self.ev("nota", "--texto", "um")[0], 0)
        self.assertRetomarValido(L)
        self.assertEqual(self.ev("nota", "--texto", "dois")[0], 0)
        self.assertRetomarValido(L)

    def test_retomar_cli_com_cadeia_ok_sai_0_e_grava_retomada(self):
        L = self.init()
        L.ate_premissas()
        code, out, err = self.co("retomar")
        self.assertEqual(code, 0, out + err)
        self.assertLimpo(out, err)
        r = [x for x in L.records() if x["evento"] == "retomada"]
        self.assertTrue(r, "retomar não gravou o evento retomada")
        self.assertIs(r[-1]["payload"]["cadeia_ok"], True)
        self.assertEqual(r[-1]["payload"]["perdidas"], [])
        self.assertTrue(r[-1]["payload"]["proximo_comando"].strip())
        self.assertEqual(cadeia_problemas(L.records()), [])
        self.assertRetomarValido(L)

    def test_retomar_com_linha_do_ledger_editada_sai_1(self):
        L = self.init()
        for i in range(2):
            self.ev("nota", "--texto", "n%d" % i)
        linhas = L.raw().decode("utf-8").splitlines(True)
        rec = json.loads(linhas[1])
        rec["payload"] = {"texto": "editado"}
        linhas[1] = json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n"
        with open(L.path, "w", encoding="utf-8") as fh:
            fh.write("".join(linhas))
        antes = L.raw()
        code, out, err = self.co("retomar")
        self.assertEqual(code, 1, out + err)
        self.assertLimpo(out, err)
        self.assertEqual(L.raw(), antes, "retomar com cadeia quebrada não pode gravar nada")

    def _em_voo(self, L, chave="obra/1/T-01/1"):
        L.ate_lote()
        L.tt("T-01", "task.pronta", "PENDENTE", "PRONTA", "script")
        L.t("lote_ok", "LOTE", "DESPACHADO", "orquestrador")
        L.append("despachada", chave=chave, task="T-01",
                 payload={"task": "T-01", "papel": "construtor", "chave": chave, "agent_type": "builder-A",
                          "writes": ["src/**"], "reads": [], "tentativa": 1, "brief_hash": "9" * 64,
                          "isolation": None, "teto_vigente": 5, "vivos_antes": 0})
        L.tt("T-01", "task.despachar", "PRONTA", "EM_VOO", "orquestrador", chave=chave, payload={"chave": chave})

    def test_write_ahead_conta_vivo_e_retomar_detecta_task_em_voo_perdida(self):
        L = self.init()
        chave = "obra/1/T-01/1"
        self._em_voo(L, chave)
        st = self.status()
        self.assertEqual(st["vivos"], [chave], "despachada (write-ahead) é a fonte única de vivos")
        self.assertEqual(st["tasks"]["T-01"]["estado"], "EM_VOO")
        code, out, err = self.co("retomar")
        self.assertEqual(code, 0, out + err)
        recs = L.records()
        perd = [r for r in recs if r["evento"] == "perdida"]
        self.assertTrue(perd, "em voo perdida não registrada")
        self.assertEqual(perd[-1]["payload"]["chave"], chave)
        self.assertEqual([r for r in recs if r["evento"] == "retomada"][-1]["payload"]["perdidas"], [chave])
        st = self.status()
        self.assertEqual(st["vivos"], [], "a vaga da perdida não foi fechada")
        self.assertEqual(st["tasks"]["T-01"]["estado"], "PRONTA")
        self.assertEqual(st["tasks"]["T-01"]["tentativas"], 1)
        self.assertEqual(cadeia_problemas(recs), [])

    def test_retomar_nao_acusa_perdida_quando_retornou(self):
        L = self.init()
        chave = "obra/1/T-01/1"
        self._em_voo(L, chave)
        L.append("retornou", chave=chave, task="T-01",
                 payload={"task": "T-01", "chave": chave, "relatorio": os.path.join(self.ws, "r.json"),
                          "relatorio_hash": "8" * 64})
        L.tt("T-01", "task.retornar", "EM_VOO", "RETORNADA", "orquestrador", chave=chave)
        code, out, err = self.co("retomar")
        self.assertEqual(code, 0, out + err)
        self.assertNotIn("perdida", L.eventos())
        st = self.status()
        self.assertEqual(st["vivos"], [])
        self.assertEqual(st["tasks"]["T-01"]["estado"], "RETORNADA")

    def test_vivos_contam_todo_subagente_so_por_despachada(self):
        L = self.init()
        L.ate_lote()
        for chave, papel in (("obra/1/-/V1", "verificador"), ("obra/1/-/O2", "oraculo")):
            L.append("despachada", chave=chave,
                     payload={"task": None, "papel": papel, "chave": chave, "agent_type": "x", "writes": [],
                              "reads": [], "tentativa": 1, "brief_hash": "9" * 64, "isolation": None,
                              "teto_vigente": 5, "vivos_antes": 0})
        L.append("retornou", chave="obra/1/-/V1",
                 payload={"task": None, "chave": "obra/1/-/V1", "relatorio": "/x", "relatorio_hash": "8" * 64})
        self.assertEqual(self.status()["vivos"], ["obra/1/-/O2"])


# ====================================================================== maquina check (invariantes.json5)

class TestMaquinaCheck(EstadoBase):
    def check(self, m, nivel="todos"):
        f = self.write_json(os.path.join(self.tmp, "maquina-plantada.json"), m)
        return self.co("maquina", "check", "--machine", f, "--nivel", nivel)

    def assertViola(self, m, inv, nivel="todos"):
        code, out, err = self.check(m, nivel)
        self.assertEqual(code, 1, "máquina plantada (%s) aceita: %s" % (inv, out + err))
        self.assertLimpo(out, err)
        self.assertIn(inv, out + err, "relatório não aponta %s" % inv)

    def test_maquina_real_passa(self):
        code, out, err = self.co("maquina", "check")
        self.assertEqual(code, 0, out + err)
        self.assertLimpo(out, err)
        code, out, err = self.co("maquina", "check", "--machine", os.path.join(REFS, "maquina.json5"),
                                 "--nivel", "todos")
        self.assertEqual(code, 0, out + err)

    def test_I1_estado_orfao(self):
        m = maquina()
        m["niveis"]["obra"]["states"].append("ORFAO")
        self.assertViola(m, "I1")

    def test_I2_estado_trancado(self):
        m = maquina()
        o = m["niveis"]["obra"]
        o["states"].append("TRANCADO")
        o["transitions"]["trancar"] = {"evento": "trancar", "from": ["MEDIR"], "to": "TRANCADO", "actor": "script",
                                       "guard": "true"}
        self.assertViola(m, "I2")

    def test_I3_atalho_que_pula_verificar(self):
        m = maquina()
        m["niveis"]["obra"]["transitions"]["atalho"] = {"evento": "atalho", "from": ["INTEGRAR"], "to": "MEDIR",
                                                        "actor": "script", "guard": "true"}
        self.assertViola(m, "I3")

    def test_I4_lote_ok_sem_incrementa(self):
        m = maquina()
        del m["niveis"]["obra"]["transitions"]["lote_ok"]["incrementa"]
        self.assertViola(m, "I4")

    def test_I5_guardas_sobrepostas(self):
        m = maquina()
        t = m["niveis"]["obra"]["transitions"]["vermelho_replanejar"]
        t["guard"] = t["guard"].replace("tentativas >= MAX_TENTATIVAS", "tentativas >= 2")
        self.assertNotEqual(t["guard"], maquina()["niveis"]["obra"]["transitions"]["vermelho_replanejar"]["guard"])
        self.assertViola(m, "I5")

    def test_I6_transicao_humana_fora_de_aguardando_humano(self):
        m = maquina()
        m["niveis"]["obra"]["transitions"]["aprova_direto"] = {
            "evento": "aprovado", "from": ["VERIFICAR"], "to": "MEDIR", "actor": "humano",
            "guard": "aprovacao_humana"}
        self.assertViola(m, "I6")

    def test_I7_reentrada_direta_no_oraculo(self):
        m = maquina()
        m["niveis"]["obra"]["transitions"]["volta_oraculo"] = {"evento": "volta_oraculo", "from": ["VERIFICAR"],
                                                               "to": "ORACULO", "actor": "orquestrador",
                                                               "guard": "true"}
        self.assertViola(m, "I7")

    def test_json_invalido_sai_2(self):
        f = os.path.join(self.tmp, "quebrada.json")
        with open(f, "w") as fh:
            fh.write("{ niveis: [ ")
        code, out, err = self.co("maquina", "check", "--machine", f)
        self.assertEqual(code, 2, out + err)
        self.assertLimpo(out, err)


# ====================================================================== integração A+B (hook vivo)

class TestIntegracaoHookVivo(EstadoBase):
    """Verde só quando B (co_hook.py) também estiver integrado: hook_vivo = selftest estático + vivo (A4)."""
    exige = (CO, CO_ESTADO, CO_HOOK)

    def test_iniciar_com_hook_vivo_vai_para_premissas(self):
        L = self.init()
        antes = L.raw()
        self.assertEqual(self.ev("iniciar")[0], 1)
        self.assertEqual(L.raw(), antes)
        self.grava_hook_vivo()
        code, out, err = self.ev("iniciar")
        self.assertEqual(code, 0, out + err)
        st = self.status()
        self.assertEqual(st["obra"]["estado"], "PREMISSAS")
        t = [r for r in L.records() if r["evento"] == "iniciar"][-1]
        self.assertEqual((t["de"], t["para"], t["ator"]), ("INICIO", "PREMISSAS", "script"))


if __name__ == "__main__":
    unittest.main()
