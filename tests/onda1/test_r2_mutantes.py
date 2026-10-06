"""Rodada 2 da onda 1: testes que matam os mutantes sobreviventes do G5 (agente M; ver
campanhas/onda1/mutantes/RELATORIO.md). Oráculo O1. Cada teste cita o mutante que mata e traz controle positivo
quando cabe. A classificação (a) já passa no produto / (b) defeito real está no ESPEC.md, seção "Rodada 2 — G5"."""
import json
import os
import pty
import select
import shlex
import signal
import subprocess
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comum import (CHALLENGE, CO, CO_HOOK, CO_ESTADO, HookBase, Ledger, bash, git, json5_load, payload,  # noqa: E402
                    py_call, rec_hash, run_tty, sub)
from test_a_estado import EstadoBase  # noqa: E402
from test_c_portao import PortaoBase  # noqa: E402
from test_r2_achados import R2Base  # noqa: E402


def run_tty2(argv, env, on_challenge=None, stdin_pipe=False, timeout=60):
    """Como _comum.run_tty, mas: stdin_pipe=True troca o stdin do filho por um pipe (o tty controlador continua
    existindo — /dev/tty abre); on_challenge() roda entre a exibição do DESAFIO e a redigitação."""
    pid, fd = pty.fork()
    if pid == 0:
        try:
            if stdin_pipe:
                r, w = os.pipe()
                os.dup2(r, 0)
                os.close(w)
            os.execve(sys.executable, [sys.executable, CO] + list(argv), env)
        finally:
            os._exit(127)
    buf, ch, deadline = b"", None, time.time() + timeout
    try:
        while True:
            if time.time() > deadline:
                os.kill(pid, signal.SIGKILL)
                raise AssertionError("tty não terminou: %r" % buf[-400:])
            r, _, _ = select.select([fd], [], [], 0.2)
            if not r:
                continue
            try:
                data = os.read(fd, 4096)
            except OSError:
                break
            if not data:
                break
            buf += data
            if ch is None:
                m = CHALLENGE.search(buf)
                if m:
                    ch = m.group(1).decode().strip()
                    if on_challenge:
                        on_challenge()
                    os.write(fd, (ch + "\n").encode())
    finally:
        _, status = os.waitpid(pid, 0)
        os.close(fd)
    return (os.WEXITSTATUS(status) if os.WIFEXITED(status) else 128 + os.WTERMSIG(status)), buf.decode("utf-8",
                                                                                                      "replace"), ch


def reescreve(L, fn):
    """Aplica fn(lista de registros) e regrava o ledger, re-encadeando hash (mas não prev/payload_hash)."""
    recs = L.records()
    fn(recs)
    with open(L.path, "w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def edita_meio(L):
    linhas = L.raw().decode("utf-8").splitlines(True)
    rec = json.loads(linhas[1])
    rec["payload"] = dict(rec["payload"], adulterado=True)
    linhas[1] = json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n"
    with open(L.path, "w", encoding="utf-8") as fh:
        fh.write("".join(linhas))


# ====================================================================== retorno constante: E01, E15/E19, E26, P06

class TestMutRetornoConstante(EstadoBase):
    def test_E01_verificar_cadeia(self):
        L = self.init()
        self.co("ev", "nota", "--texto", "x")
        code, out, err = py_call(self.env, "import co_estado\nprint(co_estado.verificar_cadeia(%r))" % self.ws)
        self.assertEqual(out.strip(), "True", out + err)
        edita_meio(L)
        code, out, err = py_call(self.env, "import co_estado\nprint(co_estado.verificar_cadeia(%r))" % self.ws)
        self.assertEqual(out.strip(), "False", "verificar_cadeia aceitou cadeia adulterada: " + out + err)

    def test_E15_E19_avaliar_guarda(self):
        casos = [("tentativas >= MAX_TENTATIVAS", {"tentativas": 1, "MAX_TENTATIVAS": 3}, False),
                 ("tentativas >= MAX_TENTATIVAS", {"tentativas": 3, "MAX_TENTATIVAS": 3}, True),
                 ("a and b", {"a": True}, False),          # b indeterminado ⇒ não satisfaz (Kleene, falha fechada)
                 ("a or b", {"a": True}, True),
                 ("not a", {}, False),
                 ("a and not b", {"a": True, "b": False}, True)]
        code, out, err = py_call(self.env, "import co_estado, json\ncasos = %r\n"
                                 "print(json.dumps([co_estado.avaliar_guarda(g, c) for g, c, _ in casos]))" % casos)
        self.assertEqual(code, 0, out + err)
        self.assertEqual(json.loads(out), [c[2] for c in casos])

    def test_E26_workspace_dentro_do_alvo_reescrito_na_obra_bloqueia_iniciar(self):
        L = self.init()
        self.grava_hook_vivo()
        p = os.path.join(self.ws, "obra.json5")
        obra = json5_load(p)
        orig = dict(obra)
        obra["alvo"] = self.tmp  # o ws passa a estar dentro do alvo
        self.write_json(p, obra)
        antes = L.raw()
        code, out, err = self.co("ev", "iniciar")
        self.assertEqual(code, 1, out + err)
        self.assertEqual(L.raw(), antes)
        self.write_json(p, orig)
        code, out, err = self.co("ev", "iniciar")
        self.assertEqual(code, 0, "controle: alvo original + hook vivo inicia: " + out + err)


class TestMutCadeiaPortao(PortaoBase):
    def test_P06_veredito_com_ledger_quebrado_e_no_go(self):
        from test_c_portao import TestVeredito
        TestVeredito.relatorio(self)
        code, out, err = self.co("veredito", "--json")
        self.assertEqual(code, 0, "controle: relatório todo PASS e ledger íntegro é GO: " + out + err)
        self.co("ev", "nota", "--texto", "x")
        edita_meio(self.L)
        code, out, err = self.co("veredito", "--json")
        self.assertEqual(code, 1, out + err)
        self.assertEqual(json.loads(out)["veredito"], "NO-GO")


# ====================================================================== cadeia: E04, E06, E23, E24, E30, E17

class TestMutCadeia(EstadoBase):
    def test_E04_prev_errado_com_hash_recalculado(self):
        L = self.init()
        for i in range(2):
            self.co("ev", "nota", "--texto", "n%d" % i)

        def f(recs):
            recs[-1]["prev"] = "0" * 64
            recs[-1]["hash"] = rec_hash(recs[-1])
        reescreve(L, f)
        self.assertEqual(self.co("retomar")[0], 1)

    def test_E06_seq1_que_nao_e_genese(self):
        L = self.init()
        self.co("ev", "nota", "--texto", "n")

        def f(recs):
            recs[0]["evento"] = "nota"
            prev = "0"
            for r in recs:
                r["prev"] = prev
                r["hash"] = rec_hash(r)
                prev = r["hash"]
        reescreve(L, f)
        self.assertEqual(self.co("retomar")[0], 1)

    def test_E23_E24_E30_nada_roda_sobre_cadeia_quebrada(self):
        L = self.init()
        L.ate_replanejar()
        edita_meio(L)
        antes = L.raw()
        code, out, err = self.co("status", "--json")
        self.assertNotEqual(code, 0, "status dobrou cadeia quebrada: " + out[:300] + err)
        for argv in (("ev", "nota", "--texto", "por cima"), ("ev", "desistir")):
            with self.subTest(argv=argv):
                code, out, err = self.co(*argv)
                self.assertNotEqual(code, 0, out + err)
                self.assertEqual(L.raw(), antes, "gravou sobre cadeia quebrada")

    def test_E17_transicao_humana_sem_aprovacao_antes(self):
        L = self.init()
        L.ate_ah_stop()
        L.t("aprovado", "AGUARDANDO_HUMANO", "ORACULO", "humano")
        self.assertEqual(self.co("status", "--json")[0], 1)
        self.assertEqual(self.co("retomar")[0], 1)

    def test_E17_aprovacao_de_outro_portao_ou_decisao(self):
        for portao, decisao in (("oraculo", "aprovado"), ("stop", "rejeitado")):
            with self.subTest(portao=portao, decisao=decisao):
                self.tearDown()
                self.setUp()
                L = self.init()
                L.ate_ah_stop()
                L.append("aprovacao", payload={"portao": portao, "decisao": decisao, "arquivo": "/x",
                                               "hash_estado": "1" * 64, "usuario_so": "t", "ttyname": "/dev/ttys0"})
                L.t("aprovado", "AGUARDANDO_HUMANO", "ORACULO", "humano")
                self.assertEqual(self.co("status", "--json")[0], 1)


# ====================================================================== guardas: E16, E29, E13, E28

class TestMutGuardas(EstadoBase):
    def test_E16_guarda_indeterminada_nao_satisfaz(self):
        L = self.init()
        L.ate_oraculo()
        antes = L.raw()
        code, out, err = self.co("ev", "oraculo_pronto")
        self.assertEqual(code, 1, "guarda com átomos indeterminados passou: " + out + err)
        self.assertEqual(L.raw(), antes)

    def test_E29_hook_vivo_exige_linha_bloqueada(self):
        L = self.init()
        self.grava_hook_vivo()
        with open(self.audit) as fh:
            linhas = [json.loads(x) for x in fh]
        for x in linhas:
            x["decisao"], x["exit"] = "permitido", 0
        with open(self.audit, "w") as fh:
            fh.write("".join(json.dumps(x) + "\n" for x in linhas))
        antes = L.raw()
        self.assertEqual(self.co("ev", "iniciar")[0], 1)
        self.assertEqual(L.raw(), antes)

    def test_E13_transicionar_recusa_canal_humano_em_transicao_nao_humana(self):
        L = self.init()
        L.ate_replanejar()
        antes = L.raw()
        code, out, err = py_call(self.env, (
            "import co_estado\n"
            "try:\n"
            "    co_estado.transicionar(%r, 'desistir', _humano={'payload_aprovacao': {'portao': 'x', 'decisao': "
            "'aprovado'}})\n"
            "    print('GRAVOU')\n"
            "except Exception as e:\n"
            "    print('RECUSOU', type(e).__name__)\n") % self.ws)
        self.assertIn("RECUSOU", out, out + err)
        self.assertEqual(L.raw(), antes)


class TestMutTeto(EstadoBase):
    def _lote_ok(self):
        return py_call(self.env, (
            "import co_estado\n"
            "try:\n"
            "    co_estado.transicionar(%r, 'lote_ok', atomos={'lote_disjunto': True, 'deps_aceitas': True, "
            "'orcamento_restante': True})\n"
            "    print('GRAVOU')\n"
            "except Exception as e:\n"
            "    print('RECUSOU', type(e).__name__)\n") % self.ws)

    def _vivos(self, L, n):
        for i in range(n):
            ch = "obra/1/-/V%d" % i
            L.append("despachada", chave=ch, payload={
                "task": None, "papel": "verificador", "chave": ch, "agent_type": "x", "writes": [], "reads": [],
                "tentativa": 1, "brief_hash": "9" * 64, "isolation": None, "teto_vigente": 5, "vivos_antes": i})

    def test_E22_lote_com_vivos_no_teto_e_recusado(self):
        L = self.init()
        L.ate_lote()
        self._vivos(L, 5)  # vivos == teto_vigente (5)
        antes = L.raw()
        code, out, err = self._lote_ok()
        self.assertIn("RECUSOU", out, out + err)
        self.assertEqual(L.raw(), antes)

    def test_E22_controle_abaixo_do_teto_despacha(self):
        L = self.init()
        L.ate_lote()
        self._vivos(L, 4)
        code, out, err = self._lote_ok()
        self.assertIn("GRAVOU", out, out + err)
        self.assertEqual(self.status()["obra"]["estado"], "DESPACHADO")


class TestMutEntrega(R2Base):
    def test_E28_pass3_exige_k3(self):
        self.ledger_coerente(ate="ENTREGA", k_final=2)
        self.relatorio_completo()
        antes = self.L.raw()
        code, out, _ = run_tty(["--work", self.ws, "aprovar", "entrega", "--decisao", "aprovado"], self.env)
        self.assertNotEqual(code, 0, "k=2 satisfez pass3_final: " + out)
        self.assertEqual(self.L.raw(), antes)

    def test_E28_controle_k3_entrega(self):
        self.ledger_coerente(ate="ENTREGA", k_final=3)
        self.relatorio_completo()
        code, out, _ = run_tty(["--work", self.ws, "aprovar", "entrega", "--decisao", "aprovado"], self.env)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.status()["obra"]["estado"], "ENTREGUE")


# ====================================================================== aprovar: E08 (stdin pipe com tty), E12 (TOCTOU)

class TestMutAprovar(EstadoBase):
    exige = (CO, CO_ESTADO, CO_HOOK)

    def test_E08_stdin_pipe_mesmo_com_tty_controlador_sai_2(self):
        L = self.init()
        L.ate_ah_stop()
        antes = L.raw()
        code, out, _ = run_tty2(["--work", self.ws, "aprovar", "stop", "--decisao", "aprovado"], self.env,
                                stdin_pipe=True)
        self.assertEqual(code, 2, out)
        self.assertEqual(L.raw(), antes)

    def test_E12_mudanca_decisoria_durante_o_desafio_sai_1(self):
        L = self.init()
        L.ate_ah_stop()

        def muda():
            L.append("teto_recuado", payload={"de": 5, "para": 3, "seq_limite_uso": 1})
        code, out, ch = run_tty2(["--work", self.ws, "aprovar", "stop", "--decisao", "aprovado"], self.env,
                                 on_challenge=muda)
        self.assertIsNotNone(ch, out)
        self.assertEqual(code, 1, "aprovação valeu para um estado que mudou durante o desafio: " + out)
        self.assertEqual(L.eventos()[-1], "teto_recuado")
        self.assertNotIn("aprovacao", L.eventos())


# ====================================================================== hook: H13, H14, H18, H20, H22

class TestMutHook(HookBase):
    def test_H13_aninhamento_profundo_falha_fechado(self):
        c = "python3 %s --work %s aprovar stop --decisao aprovado" % (CO, self.ws)
        for _ in range(8):
            c = "bash -c " + shlex.quote(c)
        self.assertBloqueia(sub(bash(c)))
        c = "echo oi"
        for _ in range(9):
            c = "bash -c " + shlex.quote(c)
        self.assertBloqueia(bash(c), "aninhamento além do analisável deve falhar fechado")
        self.assertPermite(bash("bash -c " + shlex.quote("bash -c 'echo oi'")))

    def test_H14_xargs_com_subcomando_vindo_do_stdin(self):
        self.assertBloqueia(sub(bash("echo aprovar stop | xargs python3 %s --work %s" % (CO, self.ws))))
        self.assertBloqueia(bash("printf 'aprovar\\nstop\\n' | xargs python3 %s --work %s" % (CO, self.ws)))
        self.assertPermite(bash("echo status | xargs python3 %s --work %s" % (CO, self.ws)))

    def test_H18_escrita_por_python_c_em_protegido(self):
        led = os.path.join(self.ws, ".construcao", "ledger.jsonl")
        self.assertBloqueia(sub(bash("python3 -c \"open('%s','a').write('x')\"" % led)))
        self.assertPermite(sub(bash("python3 -c \"print(open('%s/src/core.py').read())\"" % self.alvo)))

    def test_H20_glob_de_profundidade_exata_do_heldout(self):
        self.assertBloqueia(sub(payload("Glob", {"pattern": os.path.join(self.ws, "oraculo", "heldou?")})))
        import shutil
        shutil.rmtree(os.path.join(self.ws, "oraculo", "heldout"))  # sem o diretório em disco: só o padrão decide
        for pat in ("heldou?", "held*", "h[e]ldout"):
            with self.subTest(pat=pat):
                self.assertBloqueia(sub(payload("Glob", {"pattern": os.path.join(self.ws, "oraculo", pat)})))
        self.assertBloqueia(sub(payload("Read", {"file_path": os.path.join(self.ws, "oraculo", "heldout")})))

    def test_H22_destrutivo_sobre_o_proprio_ws(self):
        for c in ("rm -rf %s" % self.ws, "mv %s /tmp/x-obra" % self.ws):
            with self.subTest(cmd=c):
                self.assertBloqueia(bash(c))
                self.assertBloqueia(sub(bash(c)))
        self.assertPermite(bash("rm -rf %s/src/tmp-build" % self.alvo))


# ====================================================================== portão: P13, P14, P17, P20

class TestMutPortao(PortaoBase):
    def test_P13_um_teste_a_menos_que_o_congelado(self):
        from test_c_portao import TestG0
        TestG0.congelar(self, n_testes=3, n_assercoes=1)  # o arquivo tem 2 testes
        code, r, item, out = self.portao("G0")
        self.assertEqual(item["G0"]["status"], "FAIL", out)

    def test_P14_hash_do_ledger_diferente_da_campanha(self):
        from test_c_portao import TestG0
        TestG0.congelar(self)
        recs = self.L.records()
        # grava um novo oraculo_congelado com hash divergente (o último vale)
        self.L.append("oraculo_congelado", payload={"hash": "f" * 64, "n_testes": 1, "n_assercoes": 1,
                                                     "manifest_hash": "e" * 64})
        self.assertTrue(recs)
        code, r, item, out = self.portao("G0")
        self.assertEqual(item["G0"]["status"], "FAIL", out)

    def test_P17_diff_em_protegido_do_ws_reprova_G3(self):
        repo = self.tmp
        with open(os.path.join(repo, ".gitignore"), "w") as fh:
            fh.write("alvo/\nhome/\n")
        git(repo, "init", "-q", env=self.env)
        git(repo, "add", "-A", env=self.env)
        git(repo, "commit", "-q", "-m", "base", env=self.env)
        base = git(repo, "rev-parse", "HEAD", env=self.env)
        os.makedirs(os.path.join(self.ws, "oraculo", "dev"), exist_ok=True)
        with open(os.path.join(self.ws, "oraculo", "dev", "dados.json"), "w") as fh:
            fh.write("{}\n")
        code, out, err = self.co("diff", "T-02", "--base", base, "--repo", repo)
        self.assertEqual(code, 1, out + err)
        self.assertRegex(out + err, r"G3 FAIL", "G3 não acusou escrita em protegido (oraculo/** do ws)")

    def test_P20_gate_duplicado_no_relatorio(self):
        from test_c_portao import TestVeredito
        TestVeredito.relatorio(self)
        p = os.path.join(self.ws, "gate-report.json")
        with open(p) as fh:
            rep = json.load(fh)
        rep["itens"].append(dict([i for i in rep["itens"] if i["id"] == "G1"][0]))
        self.write_json(p, rep)
        code, out, err = self.co("veredito", "--json")
        self.assertEqual((code, json.loads(out)["veredito"]), (1, "NO-GO"))


if __name__ == "__main__":
    unittest.main()
