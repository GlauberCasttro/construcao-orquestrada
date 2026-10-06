"""Frente B — co_hook.py (PreToolUse global) + references/hook-settings.json5. Oráculo O1 (onda 1).

Bloqueia (exit 2): aprovação vinda de agente (principal ou subagente) — co.py aprovar | oraculo mudar, ac.py gate |
preauth | oracle change — com variações; escrita em <ws>/.construcao|aprovacoes|oraculo (exceto agente-oráculo do
MANIFEST); leitura de <ws>/oraculo/heldout por construtor (Read/Grep/Glob/Bash). Permite o resto (exit 0).
Falha fechada só quando o payload bruto menciona aprovação/held-out."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comum import (CO, CO_HOOK, HEX64, HOOK_SETTINGS, SCRIPTS, HookBase, bash, json5_load, payload, py_call,  # noqa: E402
                    sub)

COP = "~/.claude/skills/construcao-orquestrada/scripts/co.py"
ACP = "~/.claude/skills/auto-correcao/scripts/ac.py"


class TestHookAprovacao(HookBase):
    def casos_aprovar(self):
        w = self.ws
        return [
            "python3 %s --work %s aprovar stop --decisao aprovado" % (COP, w),
            "python3 %s --work %s aprovar entrega --decisao aprovado" % (CO, w),
            "cd %s && python3 ./co.py --work %s aprovar stop --decisao aprovado" % (SCRIPTS, w),
            '"python3" "%s" --work "%s" "aprovar" stop' % (CO, w),
            "python3 '%s' --work %s 'aprovar' 'oraculo' --decisao rejeitado" % (CO, w),
            "bash -c 'python3 co.py --work %s aprovar stop --decisao aprovado'" % w,
            'sh -c "python3 %s --work %s aprovar plano --decisao aprovado"' % (CO, w),
            "python3 -c 'import runpy,sys; sys.argv=[\"co.py\",\"--work\",\"%s\",\"aprovar\",\"stop\"]; "
            "runpy.run_path(\"%s\", run_name=\"__main__\")'" % (w, CO),
            'CO=%s; python3 "$CO" --work %s aprovar stop --decisao aprovado' % (CO, w),
            'eval "python3 co.py --work %s aprovar stop --decisao aprovado"' % w,
            "true && python3 co.py --work %s aprovar stop --decisao abandonar" % w,
            "env FOO=1 python3 %s --work %s aprovar stop --decisao aprovado" % (CO, w),
            "python3 %s --work %s oraculo mudar --motivo m --evidencia e" % (CO, w),
        ]

    def casos_ac(self):
        return [
            "python3 %s --work /tmp/c gate stop --by founder --decision approve" % ACP,
            "python3 %s --work /tmp/c preauth commit --by f --requires a.1" % ACP,
            "python3 %s --work /tmp/c oracle change --why w --evidence e" % ACP,
            "bash -c 'python3 ac.py --work /tmp/c gate stop --by f --decision approve'",
        ]

    def test_bloqueia_aprovacao_pelo_principal_com_variacoes(self):
        for c in self.casos_aprovar() + self.casos_ac():
            with self.subTest(cmd=c):
                self.assertBloqueia(bash(c, cwd=self.tmp))

    def test_bloqueia_aprovacao_por_subagente(self):
        for c in self.casos_aprovar()[:4] + self.casos_ac()[:2]:
            with self.subTest(cmd=c):
                self.assertBloqueia(sub(bash(c, cwd=self.tmp)))
        self.assertBloqueia(sub(bash("python3 %s --work %s aprovar __selftest__" % (CO, self.ws))),
                            "selftest vivo: subagente chamando aprovar __selftest__")

    def test_permite_comandos_benignos_inclusive_co_py_nao_aprovador(self):
        w = self.ws
        for c in ["ls -la", "git status", "echo aprovar", "python3 %s --work %s status --json" % (CO, w),
                  "python3 %s --work %s ev nota --texto checkpoint" % (CO, w),
                  "python3 %s --work %s medir --k 3 --simulated" % (CO, w),
                  "python3 %s --work %s veredito --json" % (CO, w),
                  "python3 %s --work /tmp/c status" % ACP,
                  "python3 %s --work /tmp/c oracle verify" % ACP,
                  "grep -n aprovar %s" % CO,
                  "cat %s/aprovacoes/aprovar-stop.sh" % w,
                  "cat %s/.construcao/ledger.jsonl | tail -3" % w]:
            with self.subTest(cmd=c):
                self.assertPermite(bash(c, cwd=self.tmp))

    def test_permite_ferramentas_de_leitura_e_escrita_fora_dos_protegidos(self):
        a = self.alvo
        for p in [payload("Write", {"file_path": os.path.join(a, "src", "novo.py"), "content": "x = 1\n"}),
                  payload("Edit", {"file_path": os.path.join(a, "src", "core.py"), "old_string": "a", "new_string": "b"}),
                  payload("Read", {"file_path": os.path.join(self.ws, "RETOMAR.md")}),
                  payload("Read", {"file_path": os.path.join(self.ws, ".construcao", "ledger.jsonl")}),
                  sub(payload("Read", {"file_path": os.path.join(self.ws, "oraculo", "dev", "test_dev.py")})),
                  sub(payload("Grep", {"pattern": "def ", "path": os.path.join(a, "src")})),
                  sub(payload("Glob", {"pattern": "src/**/*.py", "path": a}))]:
            with self.subTest(p=json.dumps(p)[:160]):
                self.assertPermite(p)


class TestHookProtegidos(HookBase):
    def test_bloqueia_escrita_no_estado_e_nas_aprovacoes(self):
        w = self.ws
        casos = [
            payload("Write", {"file_path": os.path.join(w, ".construcao", "state.json"), "content": "{}"}),
            sub(payload("Edit", {"file_path": os.path.join(w, ".construcao", "ledger.jsonl"), "old_string": "a",
                                 "new_string": "b"})),
            payload("Write", {"file_path": os.path.join(w, "aprovacoes", "stop-9.json"), "content": "{}"}),
            bash("echo '{}' > %s/.construcao/state.json" % w),
        ]
        for p in casos:
            with self.subTest(p=json.dumps(p)[:200]):
                self.assertBloqueia(p)

    def test_oraculo_so_o_autor_do_manifest_escreve(self):
        dev = os.path.join(self.ws, "oraculo", "dev", "test_novo.py")
        held = os.path.join(self.ws, "oraculo", "heldout", "casos", "C-09.json")
        self.assertBloqueia(sub(payload("Write", {"file_path": dev, "content": "x"}), agent_type="builder-A"),
                            "construtor escrevendo no oráculo")
        self.assertBloqueia(payload("Write", {"file_path": dev, "content": "x"}), "principal escrevendo no oráculo")
        self.assertPermite(sub(payload("Write", {"file_path": dev, "content": "x"}), agent_type="oraculo-O1"),
                           "agente-oráculo listado no MANIFEST")
        self.assertPermite(sub(payload("Write", {"file_path": held, "content": "{}"}), agent_type="oraculo-O1"))

    def test_bloqueia_leitura_do_heldout_por_construtor(self):
        h = os.path.join(self.ws, "oraculo", "heldout")
        casos = [
            payload("Read", {"file_path": self.heldout_caso}),
            payload("Grep", {"pattern": "sentinela", "path": h}),
            payload("Glob", {"pattern": "**/*.json", "path": h}),
            payload("Glob", {"pattern": "oraculo/heldout/**", "path": self.ws}),
            bash("cat %s" % self.heldout_caso),
            bash("grep -rn sentinela %s" % h),
            bash("python3 -c \"print(open('%s').read())\"" % self.heldout_caso),
        ]
        for p in casos:
            with self.subTest(p=json.dumps(p)[:200]):
                self.assertBloqueia(sub(p, agent_type="builder-A"))

    def test_subagente_sem_agent_type_falha_fechado(self):
        self.assertBloqueia(sub(payload("Read", {"file_path": self.heldout_caso}), agent_type=None))
        self.assertBloqueia(sub(payload("Write", {"file_path": os.path.join(self.ws, "oraculo", "dev", "t.py"),
                                                  "content": "x"}), agent_type=None))


class TestHookFalhaFechada(HookBase):
    def test_payload_quebrado_so_bloqueia_se_menciona_aprovacao_ou_heldout(self):
        for raw, want in [("{nao json", 0), ("", 0), ("[1,2]", 0), ('{"tool_name": "Bash", "tool_input": 5}', 0),
                          ("{quebrado co.py aprovar stop", 2), ('["aprovar"]', 2),
                          ("{lixo oraculo/heldout/casos", 2), ('{"tool_name": "Read", "tool_input": "heldout"', 2)]:
            with self.subTest(raw=raw):
                code, out = self.hook(raw)
                self.assertEqual(code, want, out)


class TestHookAudit(HookBase):
    def test_bloqueio_e_chamada_que_cita_co_py_vao_ao_audit_fora_do_ws(self):
        p = sub(bash("python3 %s --work %s aprovar stop --decisao aprovado" % (CO, self.ws), cwd=self.tmp))
        self.assertBloqueia(p)
        self.assertPermite(bash("python3 %s --work %s status" % (CO, self.ws), cwd=self.tmp))
        linhas = self.audit_lines()
        self.assertGreaterEqual(len(linhas), 2, "audit.jsonl (~/.claude/construcao-orquestrada) sem as linhas")
        b = [x for x in linhas if x.get("decisao") == "bloqueado"]
        self.assertTrue(b)
        b = b[-1]
        self.assertEqual((b["tipo"], b["tool"], b["exit"], b["agent_id"], b["agent_type"]),
                         ("tool_call", "Bash", 2, "ag-1", "builder-A"))
        self.assertIn("co.py", b["tokens"])
        self.assertIn("aprovar", b["tokens"])
        self.assertIn("aprovar stop", b["alvo"])
        self.assertTrue(HEX64.match(b["payload_hash"]))
        self.assertTrue(b["motivo"])
        for k in ("ts", "session_id", "cwd"):
            self.assertIn(k, b)
        self.assertTrue([x for x in linhas if x.get("decisao") == "permitido" and "status" in x.get("alvo", "")])
        for raiz, _, fs in os.walk(self.ws):
            self.assertNotIn("audit.jsonl", fs, "audit gravado dentro do workspace")


class TestHookSelftestESettings(HookBase):
    def test_selftest_estatico_sai_0(self):
        code, out = self.hook("", argv=["--selftest"])
        self.assertEqual(code, 0, out)

    def test_selftest_via_co_py(self):
        self.assertTrue(os.path.isfile(CO))
        code, out, err = self.co("hook", "selftest")
        self.assertEqual(code, 0, out + err)
        self.assertNotIn("pendente", out + err)

    def test_selftest_reprova_se_classificar_deixar_tudo_passar(self):
        """L03: o selftest precisa exercitar a decisão de verdade (contrato.modulos.co_hook.classificar)."""
        code, out, err = py_call(self.env, (
            "import co_hook\n"
            "co_hook.classificar = lambda payload: (False, 'sabotado')\n"
            "sys.argv = ['co_hook.py', '--selftest']\n"
            "try:\n"
            "    rc = co_hook.main(sys.stdin)\n"
            "except SystemExit as e:\n"
            "    rc = e.code\n"
            "print('RC=%r' % (rc,))\n"), cwd=self.tmp)
        self.assertIn("RC=", out, out + err)
        rc = out.rsplit("RC=", 1)[1].strip()
        self.assertNotIn(rc, ("0", "None", "False"), "selftest passou com classificar sabotado: " + out + err)

    def test_payloads_selftest_cobre_a_matriz_do_desenho(self):
        code, out, err = py_call(self.env, "import co_hook, json\nprint(json.dumps(co_hook.payloads_selftest()))",
                                 cwd=self.tmp)
        self.assertEqual(code, 0, out + err)
        txt = out
        self.assertGreaterEqual(len(json.loads(out)), 8)
        for frag in ("aprovar", "agent_id", ".construcao", "heldout", "ac.py", "gate"):
            self.assertIn(frag, txt, "matriz do selftest sem caso com %r" % frag)

    def test_hook_via_co_py_le_o_payload_do_stdin(self):
        p = sub(bash("python3 %s --work %s aprovar stop --decisao aprovado" % (CO, self.ws)))
        code, out, err = self.co("hook", input=json.dumps(p))
        self.assertEqual(code, 2, out + err)
        code, out, err = self.co("hook", input=json.dumps(bash("ls -la")))
        self.assertEqual(code, 0, out + err)

    def test_selftest_vivo_exige_o_bloqueio_registrado_no_audit(self):
        code, out, err = self.co("hook", "selftest", "--vivo")
        self.assertEqual(code, 1, "vivo sem bloqueio no audit deve reprovar: " + out + err)
        self.assertNotIn("Traceback", out + err)
        self.assertBloqueia(sub(bash("python3 %s --work %s aprovar __selftest__" % (CO, self.ws)),
                                agent_type="general-purpose"))
        code, out, err = self.co("hook", "selftest", "--vivo")
        self.assertEqual(code, 0, out + err)

    def test_hook_settings_json5(self):
        self.assertTrue(os.path.isfile(HOOK_SETTINGS), "references/hook-settings.json5 ausente")
        s = json5_load(HOOK_SETTINGS)
        pre = s["hooks"]["PreToolUse"]
        self.assertEqual(len(pre), 1)
        self.assertEqual(pre[0]["matcher"], "Bash|Write|Edit|MultiEdit|NotebookEdit|Read|Grep|Glob")
        self.assertEqual(pre[0]["hooks"], [{"type": "command",
                                            "command": "python3 ~/.claude/skills/construcao-orquestrada/scripts/co_hook.py"}])


if __name__ == "__main__":
    unittest.main()
