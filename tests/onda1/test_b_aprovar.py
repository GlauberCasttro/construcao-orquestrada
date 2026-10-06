"""Frente B — `co.py aprovar` (co_hook.cmd_aprovar), modelo ESPEC AC-04 do ac.py v0.3: só terminal humano
(stdin e /dev/tty interativos, nenhuma variável de ambiente dispensa), desafio numérico `DESAFIO: NNNN` (≥4 dígitos, AC-07) redigitado, audit
fora do workspace, e na MESMA chamada: aprovacoes/<portao>-<seq>.json + evento `aprovacao` + transição humana (I6, D9).
Toda recusa: nada gravado. O caminho do humano é testado num pty real (pty.fork), como em auto-correcao."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comum import CO, CO_ESTADO, CO_HOOK, Base, Ledger, cadeia_problemas, run_tty  # noqa: E402


class AprovarBase(Base):
    exige = (CO, CO_ESTADO, CO_HOOK)

    def setUp(self):
        super().setUp()
        self.L = self.init()
        self.L.ate_ah_stop()

    def snapshot(self):
        aprov = os.path.join(self.ws, "aprovacoes")
        arqs = sorted(f for f in os.listdir(aprov) if f.endswith(".json")) if os.path.isdir(aprov) else []
        return self.L.raw(), arqs, len([x for x in self.audit_lines() if x.get("tipo") == "aprovacao"])

    def tty(self, *argv, answer="echo", env=None):
        return run_tty(["--work", self.ws] + list(argv), env or self.env, answer=answer)


class TestAprovarSemTerminal(AprovarBase):
    def test_sem_tty_sai_2_e_nada_gravado(self):
        antes = self.snapshot()
        code, out, err = self.co("aprovar", "stop", "--decisao", "aprovado")
        self.assertEqual(code, 2, out + err)
        self.assertNotIn("pendente", out + err)
        self.assertNotIn("Traceback", out + err)
        self.assertEqual(self.snapshot(), antes)
        code, out, err = self.co("aprovar", "stop", "--decisao", "aprovado", input="qualquer coisa\n")
        self.assertEqual(code, 2, out + err)
        self.assertEqual(self.snapshot(), antes)

    def test_variaveis_de_ambiente_nao_dispensam_o_tty(self):
        antes = self.snapshot()
        env = dict(self.env, CO_SIMULATED="1", CO_TTY="1", CO_APROVAR="1", CO_FORCE="1", CI="1",
                   AC_SIMULATED="1", CO_DESAFIO="ok", TERM="xterm")
        code, out, err = self.co("aprovar", "stop", "--decisao", "aprovado", env=env, input="ok\n")
        self.assertEqual(code, 2, out + err)
        self.assertEqual(self.snapshot(), antes)


class TestAprovarNoTerminal(AprovarBase):
    def test_aprovado_no_tty_grava_arquivo_evento_transicao_e_audit(self):
        h_antes = self.status()["hash_estado"]
        code, out, ch = self.tty("aprovar", "stop", "--decisao", "aprovado")
        self.assertEqual(code, 0, out)
        self.assertIsNotNone(ch, "nenhum `DESAFIO: ...` impresso no terminal")
        self.assertRegex(ch, r"^\d{4,}$", "desafio deve ter ≥4 dígitos, só dígitos (AC-07): %r" % ch)
        recs = self.L.records()
        self.assertEqual(cadeia_problemas(recs), [])
        ap = [r for r in recs if r["evento"] == "aprovacao"][-1]
        tr = recs[-1]
        self.assertEqual(tr["seq"], ap["seq"] + 1, "transição humana deve vir logo após `aprovacao`")
        self.assertEqual((tr["evento"], tr["ator"], tr["de"], tr["para"], tr["nivel"]),
                         ("aprovado", "humano", "AGUARDANDO_HUMANO", "ORACULO", "obra"))
        arq = os.path.join(self.ws, "aprovacoes", "stop-%d.json" % ap["seq"])
        self.assertTrue(os.path.isfile(arq), "arquivo de aprovação ausente: %s" % arq)
        with open(arq) as fh:
            a = json.load(fh)
        self.assertEqual((a["portao"], a["decisao"], a["seq"], a["transicao_seq"], a["desafio_ok"]),
                         ("stop", "aprovado", ap["seq"], tr["seq"], True))
        self.assertEqual(a["hash_estado"], h_antes, "hash_estado aprovado ≠ fold no momento de aprovar")
        self.assertEqual(a["estado"], {"estado": "AGUARDANDO_HUMANO", "portao": "stop", "retorno": None})
        self.assertTrue(a["ttyname"].startswith("/dev/"))
        self.assertEqual(a["uid"], os.getuid())
        for k in ("usuario_so", "ts", "nota", "schema_version"):
            self.assertIn(k, a)
        self.assertEqual(ap["payload"]["portao"], "stop")
        self.assertEqual(ap["payload"]["decisao"], "aprovado")
        self.assertEqual(ap["payload"]["hash_estado"], h_antes)
        aud = [x for x in self.audit_lines() if x.get("tipo") == "aprovacao"]
        self.assertEqual(len(aud), 1, "uma linha tipo aprovacao no audit (fora do ws)")
        self.assertEqual((aud[0]["cmd"], aud[0]["name"], aud[0]["decision"], aud[0]["by"], aud[0]["seq"]),
                         ("aprovar", "stop", "aprovado", "humano", ap["seq"]))
        self.assertEqual(aud[0]["work"], self.ws)
        self.assertEqual(aud[0]["hash_estado"], h_antes)
        self.assertEqual(self.status()["obra"]["estado"], "ORACULO")

    def test_rejeitado_no_portao_stop_volta_a_premissas(self):
        code, out, _ = self.tty("aprovar", "stop", "--decisao", "rejeitado")
        self.assertEqual(code, 0, out)
        tr = self.L.last()
        self.assertEqual((tr["evento"], tr["ator"], tr["para"]), ("rejeitado", "humano", "PREMISSAS"))
        self.assertEqual(self.status()["obra"]["estado"], "PREMISSAS")

    def test_abandonar_de_qualquer_portao(self):
        code, out, _ = self.tty("aprovar", "stop", "--decisao", "abandonar")
        self.assertEqual(code, 0, out)
        tr = self.L.last()
        self.assertEqual((tr["evento"], tr["ator"], tr["para"]), ("abandonar", "humano", "ABANDONADO"))
        self.assertEqual(self.status()["obra"]["estado"], "ABANDONADO")

    def test_desafio_errado_sai_1_e_nada_gravado(self):
        antes = self.snapshot()
        code, out, ch = self.tty("aprovar", "stop", "--decisao", "aprovado", answer="numero_errado")
        self.assertIsNotNone(ch)
        self.assertEqual(code, 1, out)
        self.assertEqual(self.snapshot(), antes)
        self.assertEqual(self.status()["obra"]["estado"], "AGUARDANDO_HUMANO")

    def test_desafio_varia_entre_chamadas(self):
        vistos = set()
        for _ in range(3):
            code, out, ch = self.tty("aprovar", "stop", "--decisao", "aprovado", answer="numero_errado")
            self.assertEqual(code, 1, out)
            vistos.add(ch)
        self.assertGreater(len(vistos), 1, "desafio repetido: pode ser pré-digitado")

    def test_audit_dentro_do_workspace_sai_1_e_nada_gravado(self):
        env = self.make_env(self.ws)  # HOME = ws  ⇒  ~/.claude/construcao-orquestrada/audit.jsonl dentro do ws
        antes = self.L.raw()
        code, out, _ = self.tty("aprovar", "stop", "--decisao", "aprovado", env=env)
        self.assertEqual(code, 1, out)
        self.assertEqual(self.L.raw(), antes)
        self.assertFalse(os.path.exists(os.path.join(self.ws, ".claude", "construcao-orquestrada", "audit.jsonl")))
        self.assertEqual([f for f in os.listdir(os.path.join(self.ws, "aprovacoes"))
                          if f.endswith(".json")] if os.path.isdir(os.path.join(self.ws, "aprovacoes")) else [], [])


if __name__ == "__main__":
    unittest.main()
