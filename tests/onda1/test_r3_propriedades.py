"""Rodada 3 / medição M2: testes de PROPRIEDADE (classe do defeito, não o mutante). Oráculo O1.
Regras: cada função/guarda/conferência tem caso NÃO e caso SIM; cada conferência de integridade tem um teste por
campo adulterado (com as demais testemunhas forjadas de forma coerente, para isolar a conferência do campo);
check estático tem caso em que reprova; erro interno do CLI sai ≠ 0. Ver ESPEC.md, "Rodada 3 — propriedades"."""
import json
import os
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comum import (CO, REAL_SKILLS, SKILL, Base, HookBase, Ledger, bash, json5_load, payload, py_call,  # noqa: E402
                    rec_hash, sha_obj, sub)
from test_a_estado import EstadoBase  # noqa: E402
from test_c_portao import PortaoBase  # noqa: E402
from test_r2_achados import R2Base  # noqa: E402


# ---------------------------------------------------------------------------------------- forja coerente

def forja(ws, fn):
    """Adultera o ledger com fn(recs) e re-encadeia TUDO de forma coerente (seq, payload_hash, prev, hash), exceto
    o que fn marcar em recs[i]['_manter'] (campos que NÃO devem ser recalculados naquele registro). Depois alinha o
    cache state.json (ledger_seq/ledger_hash) ao novo fim — o adversário apaga as testemunhas que pode."""
    L = Ledger(ws)
    recs = L.records()
    fn(recs)
    prev = "0"
    for i, r in enumerate(recs, 1):
        manter = set(r.pop("_manter", ()))
        if "seq" not in manter:
            r["seq"] = i
        if "payload_hash" not in manter:
            r["payload_hash"] = sha_obj(r["payload"])
        if "prev" not in manter:
            r["prev"] = prev
        if "hash" not in manter:
            r["hash"] = rec_hash(r)
        prev = r["hash"]
    with open(L.path, "w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    cache = os.path.join(ws, ".construcao", "state.json")
    if os.path.isfile(cache):
        with open(cache) as fh:
            c = json.load(fh)
        c["ledger_seq"], c["ledger_hash"] = recs[-1]["seq"], recs[-1]["hash"]
        with open(cache, "w") as fh:
            json.dump(c, fh)
    return L


class TestIntegridadeLedgerPorCampo(EstadoBase):
    def _obra(self):
        L = self.init()
        for i in range(3):
            self.assertEqual(self.co("ev", "nota", "--texto", "n%d" % i)[0], 0)
        return L

    def assertIncoerente(self, fn, campo):
        L = self._obra()
        forja(self.ws, fn)
        antes = L.raw()
        for argv in (("retomar",), ("status", "--json"), ("ev", "nota", "--texto", "x")):
            code, out, err = self.co(*argv)
            self.assertNotEqual(code, 0, "%s adulterado passou em %s: %s" % (campo, argv[0], out[:200] + err))
            self.assertNotIn("Traceback", out + err)
        self.assertEqual(L.raw(), antes)

    def test_controle_forja_sem_adulteracao_e_aceita(self):
        self._obra()
        forja(self.ws, lambda recs: None)
        self.assertEqual(self.co("status", "--json")[0], 0)
        self.assertEqual(self.co("retomar")[0], 0)

    def test_payload_com_payload_hash_velho(self):
        def f(recs):
            recs[2]["payload"] = {"texto": "trocado"}
            recs[2]["_manter"] = ["payload_hash"]
        self.assertIncoerente(f, "payload")

    def test_payload_hash_trocado(self):
        def f(recs):
            recs[2]["payload_hash"] = "0" * 64
            recs[2]["_manter"] = ["payload_hash"]
        self.assertIncoerente(f, "payload_hash")

    def test_prev_quebrado_no_meio(self):
        def f(recs):
            recs[2]["prev"] = "f" * 64
            recs[2]["_manter"] = ["prev"]
        self.assertIncoerente(f, "prev")

    def test_prev_da_genese_diferente_de_zero(self):
        def f(recs):
            recs[0]["prev"] = "a" * 64
            recs[0]["_manter"] = ["prev"]
        self.assertIncoerente(f, "prev gênese")

    def test_hash_do_registro_trocado(self):
        def f(recs):
            recs[-1]["hash"] = "e" * 64
            recs[-1]["_manter"] = ["hash"]
        self.assertIncoerente(f, "hash")

    def test_seq_com_lacuna(self):
        def f(recs):
            recs[-1]["seq"] = recs[-1]["seq"] + 5
            recs[-1]["_manter"] = ["seq"]
        self.assertIncoerente(f, "seq")

    def test_ts_fora_do_formato(self):
        def f(recs):
            recs[2]["ts"] = "ontem"
        self.assertIncoerente(f, "ts")

    def test_genese_ausente(self):
        def f(recs):
            del recs[0]
        self.assertIncoerente(f, "gênese")


class TestFoldOperacionalCoerente(EstadoBase):
    """E27: operacional precisa de ator script e de/para nulos; evento operacional desconhecido também é incoerente."""

    def _obra_e(self, fn):
        L = self.init()
        self.assertEqual(self.co("ev", "nota", "--texto", "n")[0], 0)
        forja(self.ws, fn)
        return L

    def test_controle_operacional_coerente_dobra(self):
        self._obra_e(lambda recs: None)
        self.assertEqual(self.co("status", "--json")[0], 0)

    def test_operacional_incoerente(self):
        casos = {"ator humano": ("ator", "humano"), "ator orquestrador": ("ator", "orquestrador"),
                 "de preenchido": ("de", "PLANO"), "para preenchido": ("para", "ENTREGUE"),
                 "evento desconhecido": ("evento", "inventado_pelo_agente"), "nivel inválido": ("nivel", "xyz")}
        for nome, (campo, valor) in casos.items():
            with self.subTest(caso=nome):
                self.tearDown()
                self.setUp()

                def f(recs, campo=campo, valor=valor):
                    recs[-1][campo] = valor
                self._obra_e(f)
                code, out, err = self.co("status", "--json")
                self.assertEqual(code, 1, "%s aceito: %s" % (nome, out[:200] + err))


# ---------------------------------------------------------------------------------------- guardas

class TestParseGuardaPrecedencia(Base):
    exige = (CO,)

    def test_precedencia_not_and_or_e_parenteses(self):
        casos = [
            ("a or b and c", {"a": True, "b": False, "c": False}, True),     # and liga mais que or
            ("a and b or c", {"a": False, "b": False, "c": True}, True),
            ("a and b or c", {"a": True, "b": False, "c": False}, False),
            ("(a or b) and c", {"a": True, "b": False, "c": False}, False),
            ("not a and b", {"a": False, "b": True}, True),                  # not liga mais que and
            ("not a and b", {"a": True, "b": True}, False),
            ("not (a and b)", {"a": True, "b": False}, True),
            ("x < 3 and y >= 2 or z", {"x": 5, "y": 2, "z": False}, False),
            ("x < 3 and y >= 2 or z", {"x": 1, "y": 2, "z": False}, True),
            ("x >= MAX", {"x": 3, "MAX": 3}, True),
            ("x >= MAX", {"x": 2, "MAX": 3}, False),
            ("true", {}, True),
            ("false or a", {"a": False}, False),
        ]
        code, out, err = py_call(self.env, "import co_estado, json\ncasos = %r\n"
                                 "print(json.dumps([co_estado.avaliar_guarda(g, c) for g, c, _ in casos]))" % casos)
        self.assertEqual(code, 0, out + err)
        got = json.loads(out)
        for (g, ctx, want), v in zip(casos, got):
            self.assertEqual(v, want, "%s com %s" % (g, ctx))


class TestCanalHumanoNaApi(EstadoBase):
    """E19/E24: transicionar só grava transição humana com o canal humano, e o hash_estado aprovado tem de ser o
    hash do estado sob a trava."""

    def _ah(self):
        L = self.init()
        L.ate_ah_stop()
        return L

    def _tr(self, ev, extra):
        return py_call(self.env, (
            "import co_estado\n"
            "try:\n"
            "    co_estado.transicionar(%r, %r%s)\n"
            "    print('GRAVOU')\n"
            "except Exception as e:\n"
            "    print('RECUSOU', type(e).__name__)\n") % (self.ws, ev, extra))

    def test_evento_humano_sem_canal_e_recusado_mesmo_com_atomo_forjado(self):
        for ev in ("aprovado", "rejeitado", "abandonar"):
            for extra in ("", ", atomos={'aprovacao_humana': True}"):
                with self.subTest(ev=ev, extra=extra):
                    L = self._ah() if not os.path.exists(os.path.join(self.ws, "obra.json5")) else Ledger(self.ws)
                    antes = L.raw()
                    code, out, err = self._tr(ev, extra)
                    self.assertIn("RECUSOU", out, out + err)
                    self.assertEqual(L.raw(), antes)

    def test_hash_estado_aprovado_tem_de_ser_o_atual(self):
        L = self._ah()
        h = self.status()["hash_estado"]
        ap = "{'portao': 'stop', 'decisao': 'aprovado', 'arquivo': '/x', 'hash_estado': %r, 'usuario_so': 't', " \
             "'ttyname': '/dev/ttys0'}"
        antes = L.raw()
        code, out, err = self._tr("aprovado", ", _humano={'payload_aprovacao': %s, 'hash_estado': %r}"
                                  % (ap % ("0" * 64), "0" * 64))
        self.assertIn("RECUSOU", out, out + err)
        self.assertEqual(L.raw(), antes)
        code, out, err = self._tr("aprovado", ", _humano={'payload_aprovacao': %s, 'hash_estado': %r}" % (ap % h, h))
        self.assertIn("GRAVOU", out, "controle: hash atual aprova: " + out + err)
        self.assertEqual(self.status()["obra"]["estado"], "ORACULO")


class TestGuardaRetomarMd(EstadoBase):
    """E33: retomar_md_valido é NÃO quando RETOMAR.md falta, está velho ou tem cabeçalho adulterado; SIM quando
    reflete o último registro."""

    def _fechar(self):
        L = self.init()
        L.ate_lote()
        L.t("fronteira_vazia", "LOTE", "INTEGRAR", "script")
        L.t("merge_ok", "INTEGRAR", "VERIFICAR", "script")
        L.t("verde", "VERIFICAR", "MEDIR", "script")
        L.t("medido", "MEDIR", "FECHAR_RODADA", "script")
        return L

    def _parar(self):
        return py_call(self.env, (
            "import co_estado\n"
            "try:\n"
            "    co_estado.transicionar(%r, 'rodada_fechada', {'saida': 'parar', 'criterio_parada_ok': True, "
            "'plato_2': False, 'comparacao_hash': None}, atomos={'criterio_parada_ok': True, "
            "'pontos_atualizados': True, 'plato_2': False, 'orcamento_esgotado': False})\n"
            "    print('GRAVOU')\n"
            "except Exception as e:\n"
            "    print('RECUSOU', type(e).__name__, e)\n") % self.ws)

    def test_retomar_md_invalido_bloqueia_parar(self):
        for caso in ("velho", "ausente", "hash_adulterado"):
            with self.subTest(caso=caso):
                self.tearDown()
                self.setUp()
                md = os.path.join(self.ws, "RETOMAR.md")
                L = self._fechar()
                if caso == "ausente" and os.path.exists(md):
                    os.remove(md)
                elif caso == "hash_adulterado":
                    self.assertEqual(self.co("ev", "nota", "--texto", "regera")[0], 0)
                    with open(md, encoding="utf-8") as fh:
                        txt = fh.read()
                    with open(md, "w", encoding="utf-8") as fh:
                        fh.write(txt.replace("ledger_hash=" + L.last()["hash"], "ledger_hash=" + "0" * 64, 1))
                antes = L.raw()
                code, out, err = self._parar()
                self.assertIn("RECUSOU", out, "RETOMAR.md %s aceito: %s" % (caso, out + err))
                self.assertEqual(L.raw(), antes)

    def test_controle_retomar_md_valido_permite_parar(self):
        self._fechar()
        self.assertEqual(self.co("ev", "nota", "--texto", "regera RETOMAR.md")[0], 0)
        code, out, err = self._parar()
        self.assertIn("GRAVOU", out, out + err)
        st = self.status()
        self.assertEqual((st["obra"]["estado"], st["obra"]["portao"]), ("AGUARDANDO_HUMANO", "entrega"))


# ---------------------------------------------------------------------------------------- selftest estático reprova

class TestHookSelftestEstaticoReprova(Base):
    """E40: o selftest estático do hook entra em hook_vivo; com um co_hook cujo --selftest reprova, iniciar é NÃO."""
    exige = (CO,)

    def _copia(self, quebrar):
        home = os.path.join(self.tmp, "home2")
        sk = os.path.join(home, ".claude", "skills")
        os.makedirs(sk)
        dst = os.path.join(sk, "construcao-orquestrada")
        shutil.copytree(SKILL, dst, ignore=shutil.ignore_patterns("__pycache__", "tests"))
        os.symlink(os.path.join(REAL_SKILLS, "auto-correcao"), os.path.join(sk, "auto-correcao"))
        if quebrar:
            hp = os.path.join(dst, "scripts", "co_hook.py")
            with open(hp, encoding="utf-8") as fh:
                src = fh.read()
            with open(hp, "w", encoding="utf-8") as fh:
                fh.write("import sys\nif '--selftest' in sys.argv:\n    print('selftest: 0/1 ok')\n    sys.exit(1)\n"
                         + src)
        env = self.make_env(home)
        env["HOME"] = home
        return dst, env, home

    def _iniciar(self, quebrar):
        dst, env, home = self._copia(quebrar)
        co2 = os.path.join(dst, "scripts", "co.py")
        ws = os.path.join(self.tmp, "obra-copia")
        self.assertEqual(self.co("init", "--alvo", self.alvo, "--tipo", "cli", "--pedido", "p", "--stop", "s",
                                 work=ws, env=env, script=co2)[0], 0)
        aud = os.path.join(home, ".claude", "construcao-orquestrada", "audit.jsonl")
        os.makedirs(os.path.dirname(aud), exist_ok=True)
        from _comum import now_ts
        with open(aud, "a") as fh:
            fh.write(json.dumps({"ts": now_ts(), "tipo": "tool_call", "session_id": "s", "agent_id": "a",
                                 "agent_type": "general-purpose", "tool": "Bash",
                                 "alvo": "python3 co.py --work %s aprovar __selftest__" % ws,
                                 "tokens": ["co.py", "aprovar"], "decisao": "bloqueado", "motivo": "m", "exit": 2,
                                 "cwd": "/", "payload_hash": "2" * 64}) + "\n")
        code, out, err = py_call(env, "import sys; sys.path.insert(0, %r)\nimport co_estado\n"
                                 "print(co_estado.hook_selftest_estatico())" % os.path.join(dst, "scripts"))
        sf = out.strip().splitlines()[-1] if out.strip() else ""
        code_ini, o2, e2 = self.co("ev", "iniciar", work=ws, env=env, script=co2)
        return sf, code_ini, o2 + e2

    def test_selftest_que_reprova_bloqueia_iniciar(self):
        sf, code, out = self._iniciar(quebrar=True)
        self.assertEqual(sf, "False")
        self.assertEqual(code, 1, out)

    def test_controle_selftest_ok_permite_iniciar(self):
        sf, code, out = self._iniciar(quebrar=False)
        self.assertEqual(sf, "True")
        self.assertEqual(code, 0, out)


# ---------------------------------------------------------------------------------------- portão

class TestVereditoFuncaoECampos(R2Base):
    """P07/P12/P19: veredito(ws) (função de contrato) concorda com a CLI em NÃO e SIM; regressao_hash do relatório é
    conferido; relatório parcial nunca é final."""

    def _veredito_fn(self):
        code, out, err = py_call(self.env, "import co_portao\nprint(co_portao.veredito(%r))" % self.ws)
        return out.strip().splitlines()[-1] if out.strip() else err

    def test_veredito_funcao_nao_e_sim(self):
        self.ledger_coerente()
        self.relatorio_completo()
        self.assertEqual(self._veredito_fn(), "GO")
        self.relatorio_completo(mudancas={"G3": {"status": "FAIL", "exit": 1}})
        self.assertEqual(self._veredito_fn(), "NO-GO")
        self.relatorio_completo(mudancas={"G1": {"status": "ERRO", "exit": 2}})
        self.assertEqual(self._veredito_fn(), "NO-GO")

    def test_regressao_hash_do_relatorio_adulterado(self):
        self.ledger_coerente()
        self.relatorio_completo()
        code, v = self.veredito()
        self.assertEqual(v["veredito"], "GO", "controle")
        p = os.path.join(self.ws, "gate-report.json")
        with open(p) as fh:
            rep = json.load(fh)
        rep["regressao_hash"] = "0" * 64
        self.write_json(p, rep)
        from _comum import sha_file
        self.L.append("portao_relatorio", payload={"gate_report_hash": sha_file(p), "veredito": "GO", "final": True})
        code, v = self.veredito()
        self.assertEqual((code, v["veredito"]), (1, "NO-GO"))

    def test_relatorio_parcial_nunca_final_e_completo_sim(self):
        self.ledger_coerente()
        for only in ("G1", "G0,G1", "G3"):
            with self.subTest(only=only):
                self.co("portao", "run", "--only", only, "--final")
                with open(os.path.join(self.ws, "gate-report.json")) as fh:
                    rep = json.load(fh)
                self.assertIs(rep["final"], False, "--only %s gravou final=true" % only)
        self.co("portao", "run", "--final")
        with open(os.path.join(self.ws, "gate-report.json")) as fh:
            rep = json.load(fh)
        self.assertIsNone(rep["only"])
        self.assertIs(rep["final"], True, "controle: run completo --final grava final=true")


class TestG3CadaProtegido(PortaoBase):
    """P21: G3 reprova escrita em CADA protegido do ws (.construcao, aprovacoes, oraculo) mesmo com writes que os cobrem;
    arquivo do ws fora dos protegidos passa."""

    def _repo_com_ws(self):
        with open(os.path.join(self.tmp, ".gitignore"), "w") as fh:
            fh.write("alvo/\nhome/\n")
        from _comum import git
        git(self.tmp, "init", "-q", env=self.env)
        git(self.tmp, "add", "-A", env=self.env)
        git(self.tmp, "commit", "-q", "-m", "base", env=self.env)
        return git(self.tmp, "rev-parse", "HEAD", env=self.env)

    def _diff(self, rel):
        # task com writes cobrindo o ws inteiro, mas não amplo ("**"): isola a regra dos protegidos
        p = os.path.join(self.ws, "PLANO.json5")
        pl = json5_load(p)
        pl["tasks"].append({"id": "T-03", "titulo": "ws", "writes": ["obra/**"], "deps": [], "cenarios": ["C-01"],
                            "construtor": "builder-C", "criterio": "x"})
        self.write_json(p, pl)
        base = self._repo_com_ws()
        p = os.path.join(self.ws, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write("{}\n")
        code, out, err = self.co("diff", "T-03", "--base", base, "--repo", self.tmp)
        return code, out + err

    def test_cada_protegido(self):
        for rel in (".construcao/extra.json", "aprovacoes/stop-99.json", "oraculo/heldout/casos/C-09.json",
                    "oraculo/dev/dados.json"):
            with self.subTest(rel=rel):
                self.tearDown()
                self.setUp()
                code, out = self._diff(rel)
                self.assertEqual(code, 1, out)
                self.assertRegex(out, r"G3 FAIL.*(?i:proteg)")

    def test_controle_arquivo_do_ws_fora_dos_protegidos(self):
        code, out = self._diff("notas/rascunho.json")
        self.assertRegex(out, r"G3 PASS", out)


# ---------------------------------------------------------------------------------------- hook

class TestHookAuditEAncestral(HookBase):
    def test_H12_escrita_no_audit_negada_leitura_permitida(self):
        aud = self.audit
        os.makedirs(os.path.dirname(aud), exist_ok=True)
        open(aud, "a").close()
        for p in (payload("Write", {"file_path": aud, "content": ""}),
                  payload("Edit", {"file_path": aud, "old_string": "a", "new_string": "b"}),
                  bash("echo '{}' >> %s" % aud), sub(bash("rm %s" % aud))):
            with self.subTest(p=str(p)[:120]):
                self.assertBloqueia(p)
        self.assertPermite(payload("Read", {"file_path": aud}))
        self.assertPermite(payload("Write", {"file_path": os.path.join(self.home, ".claude", "outro.txt"),
                                             "content": "x"}))

    def test_H14_destrutivo_sobre_ancestral_do_ws(self):
        fundo = os.path.join(self.tmp, "x", "y", "obra2")
        os.makedirs(os.path.join(fundo, ".construcao"))
        for c in ("rm -rf %s" % self.tmp, "rm -rf %s" % os.path.join(self.tmp, "x"),
                  "mv %s /tmp/longe" % os.path.join(self.tmp, "x")):
            with self.subTest(cmd=c):
                self.assertBloqueia(bash(c))
        self.assertPermite(bash("rm -rf %s" % os.path.join(self.alvo, "build")))


# ---------------------------------------------------------------------------------------- CLI: erro interno ≠ 0

class TestErroInternoNaoSaiZero(EstadoBase):
    """C04: entrada malformada que estoura dentro do handler sai ≠ 0, sem traceback."""

    def test_arquivos_com_tipo_errado(self):
        self.init()
        casos = [("PLANO.json5", "[1, 2]", ("diff", "T-01", "--base", "HEAD", "--repo", self.alvo)),
                 ("gate-report.json", "[]", ("veredito", "--json")),
                 ("regressao.json5", "[]", ("veredito", "--json")),
                 ("obra.json5", "[\"lista\"]", ("portao", "run", "--only", "G1"))]
        for nome, conteudo, argv in casos:
            with self.subTest(arq=nome):
                with open(os.path.join(self.ws, nome), "w") as fh:
                    fh.write(conteudo)
                if nome == "regressao.json5":
                    with open(os.path.join(self.ws, "gate-report.json"), "w") as fh:
                        json.dump({"itens": [], "regressao_hash": "0" * 64}, fh)
                code, out, err = self.co(*argv)
                self.assertNotEqual(code, 0, "%s malformado ⇒ exit 0: %s" % (nome, out + err))
                self.assertNotIn("Traceback", out + err)


if __name__ == "__main__":
    unittest.main()
