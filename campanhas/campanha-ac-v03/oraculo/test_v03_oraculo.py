"""Oráculo de aceite da auto-correcao v0.3 (AC-01..AC-04, L17).

Escrito por um agente SEPARADO de quem implementa (L15). Falha hoje; passa quando a v0.3 estiver pronta.
Interfaces fixadas: veja ESPEC.md ao lado. unittest puro, Python 3.9+, sem dependências.

Tudo roda em diretórios temporários. O único caminho externo escrito é o log de auditoria, redirecionado por
AC_AUDIT_LOG (variável de CAMINHO, não de bypass) para dentro do temporário do teste.

Escolha documentada para AC-04(a): o caminho de terminal é testado com `pty.fork()` — o processo filho recebe um
pseudo-terminal como stdin/stdout/tty controlador, lê o desafio impresso (linha `DESAFIO: <palavras>`) e o teste
redigita. NÃO existe (e o oráculo não aceita) variável de ambiente que dispense o tty.
"""
import importlib.util
import json
import os
import pty
import re
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

SKILL = os.path.expanduser("~/.claude/skills/auto-correcao")
AC = os.path.join(SKILL, "scripts", "ac.py")
HOOK = os.path.join(SKILL, "scripts", "hook_aprovacao.py")
LICOES = os.path.join(SKILL, "references", "licoes.json5")

_AC_MOD = None


def acmod():
    """Importa ac.py pelo caminho absoluto (só para json5_load e ciclo)."""
    global _AC_MOD
    if _AC_MOD is None:
        spec = importlib.util.spec_from_file_location("ac_oraculo_v03", AC)
        _AC_MOD = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_AC_MOD)
    return _AC_MOD


def ciclo():
    return acmod().ciclo()


# ------------------------------------------------------------------ helpers

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="ac-oraculo-v03-"))
        self.work = os.path.join(self.tmp, "camp")
        self.target = os.path.join(self.tmp, "alvo")
        os.makedirs(os.path.join(self.target, "evals"))
        os.makedirs(os.path.join(self.target, "src"))
        self.grader = os.path.join(self.target, "evals", "grader.py")
        with open(self.grader, "w") as fh:
            fh.write("print('ok')\n")
        self.audit = os.path.join(self.tmp, "auditoria", "audit.jsonl")  # fora de self.work
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("AC_")}
        self.env["AC_AUDIT_LOG"] = self.audit

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- CLI sem terminal (como um agente chamando via Bash)
    def cli(self, *argv, work=None, input=None, env=None):
        p = subprocess.run([sys.executable, AC, "--work", work or self.work] + list(argv),
                           input=input, stdin=None if input is not None else subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env or self.env,
                           timeout=60, universal_newlines=True)
        return p.returncode, p.stdout

    def init(self, work=None, target=None, scope="src/**"):
        code, out = self.cli("init", "--target", target or self.target, "--scope", scope, "--problem", "p",
                             "--stop", "qualidade>=6/6", "--max-rounds", "3", work=work)
        self.assertEqual(code, 0, out)

    # --- estado direto (fixture; evita depender do canal humano nos testes que não são de AC-04)
    def state_path(self, work=None):
        return os.path.join(work or self.work, ".auto-correcao", "state.json")

    def state(self, work=None):
        with open(self.state_path(work)) as fh:
            return json.load(fh)

    def save_state(self, st, work=None):
        with open(self.state_path(work), "w") as fh:
            json.dump(st, fh, indent=1, sort_keys=True)

    def forge_stop_gate(self):
        st = self.state()
        st.setdefault("gates", {})["stop"] = {"by": "founder", "decision": "approve", "note": "", "at": "x",
                                              "simulated": False}
        self.save_state(st)

    def mark_done(self, *stages):
        st = self.state()
        cy = ciclo()
        for name in stages:
            for sub in cy["stages"][name]["substages"]:
                st["done"][sub["id"]] = "2020-01-01T00:00:00Z"
        self.save_state(st)

    def round_file(self, rel, data, r=0):
        p = os.path.join(self.work, ".auto-correcao", "rounds", str(r), rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write(data)
        return p

    def grading(self, passed, total, name):
        g = os.path.join(self.tmp, name)
        with open(g, "w") as fh:
            json.dump({"summary": {"quality": {"passed": passed, "total": total},
                                   "structure": {"passed": 1, "total": 2}}}, fh)
        return g

    def runs(self, r=0):
        p = os.path.join(self.work, ".auto-correcao", "rounds", str(r), "runs.jsonl")
        if not os.path.isfile(p):
            return []
        with open(p) as fh:
            return [json.loads(l) for l in fh if l.strip()]

    # --- CLI dentro de um pseudo-terminal (o humano)
    def cli_tty(self, *argv, answer="echo", env=None, timeout=30):
        """Roda ac.py num pty. answer='echo' redigita o desafio; str redigita esse texto; None não responde.
        Retorna (exit, saída, desafio_ou_None)."""
        env = env or self.env
        pid, fd = pty.fork()
        if pid == 0:  # filho: stdin/stdout/stderr e tty controlador = escravo do pty
            try:
                os.execve(sys.executable, [sys.executable, AC, "--work", self.work] + list(argv), env)
            finally:
                os._exit(127)
        buf, challenge, deadline = b"", None, time.time() + timeout
        try:
            while True:
                if time.time() > deadline:
                    os.kill(pid, signal.SIGKILL)
                    self.fail("ac.py no tty não terminou em %ss; saída: %r" % (timeout, buf[-500:]))
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
                if challenge is None:
                    m = re.search(rb"DESAFIO:[ \t]*([^\r\n]+)\r?\n", buf)
                    if m:
                        challenge = m.group(1).decode().strip()
                        if answer is not None:
                            txt = challenge if answer == "echo" else answer
                            os.write(fd, (txt + "\n").encode())
        finally:
            _, status = os.waitpid(pid, 0)
            os.close(fd)
        code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else 128 + os.WTERMSIG(status)
        return code, buf.decode("utf-8", "replace"), challenge

    def audit_lines(self):
        if not os.path.isfile(self.audit):
            return []
        with open(self.audit) as fh:
            return [json.loads(l) for l in fh if l.strip()]


# ------------------------------------------------------------------ AC-01

class AC01RemedicaoPosCorrecaoTest(Base):
    """remedicao.1 exige execução registrada DEPOIS de correcao.1 concluída e com `decision` preenchida."""

    def _ate_correcao(self):
        self.init()
        self.forge_stop_gate()
        self.mark_done("intake", "oraculo", "base", "diagnostico", "plano")
        self.round_file("PLANO.json5", '{parada: "x", frentes: [{nome: "a", escreve: ["src/**"]}]}')
        rel = os.path.join(self.tmp, "rel-a.md")
        with open(rel, "w") as fh:
            fh.write("frente a: ok\n")
        code, out = self.cli("run", "record", "--config", "sistema", "--alvo", "py",
                             "--grading", self.grading(0, 6, "g-base.json"))  # execução da BASE
        self.assertEqual(code, 0, out)
        time.sleep(1.1)
        self.assertEqual(self.cli("front", "report", "a", "--file", rel)[0], 0)
        code, out = self.cli("check", "correcao.1")
        self.assertEqual(code, 0, out)
        self.mark_done("integracao")
        time.sleep(1.1)

    def test_base_run_alone_does_not_close_remedicao(self):
        self._ate_correcao()
        code, out = self.cli("check", "remedicao.1")
        self.assertNotEqual(code, 0, "remedicao.1 passou só com a execução da base (anterior a correcao.1)")
        self.assertIn("correcao.1", out, "a recusa deve dizer que falta execução posterior a correcao.1")
        self.assertNotEqual(self.cli("done", "remedicao")[0], 0)
        # positivo: execução depois de correcao.1, com decision
        code, out = self.cli("run", "record", "--config", "sistema", "--alvo", "py", "--decision", "continuar",
                             "--grading", self.grading(6, 6, "g-rem.json"))
        self.assertEqual(code, 0, out)
        code, out = self.cli("check", "remedicao.1")
        self.assertEqual(code, 0, out)
        code, out = self.cli("done", "remedicao")
        self.assertEqual(code, 0, out)

    def test_post_correction_run_without_decision_does_not_close(self):
        self._ate_correcao()
        code, out = self.cli("run", "record", "--config", "sistema", "--alvo", "py",
                             "--grading", self.grading(6, 6, "g-rem.json"))
        self.assertEqual(code, 0, out)
        code, out = self.cli("check", "remedicao.1")
        self.assertNotEqual(code, 0, "remedicao.1 passou com execução sem `decision`")
        self.assertNotEqual(self.cli("done", "remedicao")[0], 0)
        self.cli("run", "record", "--config", "sistema", "--alvo", "py", "--decision", "parar",
                 "--grading", self.grading(6, 6, "g-rem2.json"))
        self.assertEqual(self.cli("check", "remedicao.1")[0], 0)


# ------------------------------------------------------------------ AC-02

class AC02StatusEtapaTest(Base):
    """`done` avança state.stage para a próxima etapa não concluída; tudo concluído → 'concluida'."""

    def test_done_advances_stage_and_failed_done_does_not(self):
        self.init()
        self.assertEqual(self.cli("done", "intake")[0], 1)  # sem portão stop: não fecha
        self.assertEqual(self.state()["stage"], "intake")
        self.forge_stop_gate()
        code, out = self.cli("done", "intake")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.state()["stage"], "oraculo")
        code, out = self.cli("status")
        self.assertEqual(code, 0, out)
        self.assertRegex(out, r"etapa:\s*oraculo\b")

    def test_done_skips_already_completed_stages(self):
        self.init()
        self.forge_stop_gate()
        self.mark_done("oraculo")
        self.assertEqual(self.cli("done", "intake")[0], 0)
        self.assertEqual(self.state()["stage"], "base")
        self.assertRegex(self.cli("status")[1], r"etapa:\s*base\b")

    def test_all_done_shows_concluida(self):
        self.init()
        self.forge_stop_gate()
        self.mark_done(*[n for n in ciclo()["order"] if n != "decisao"])
        self.assertEqual(self.cli("set", "decision", "parar")[0], 0)
        self.assertEqual(self.cli("set", "report", "relatorio curto")[0], 0)
        code, out = self.cli("done", "decisao")
        self.assertEqual(code, 0, out)
        self.assertIn(self.state()["stage"], ("concluida", "concluída"))
        self.assertRegex(self.cli("status")[1], r"etapa:\s*conclu[ií]da")


# ------------------------------------------------------------------ AC-03

class AC03TotalQualidadeTest(Base):
    """`run record` recusa quality.total ≠ total da base na mesma rodada, salvo `oracle change` posterior à base."""

    def test_mismatched_total_refused_citing_L02(self):
        self.init()
        self.assertEqual(self.cli("run", "record", "--config", "sistema", "--alvo", "py",
                                  "--grading", self.grading(0, 6, "b.json"))[0], 0)
        code, out = self.cli("run", "record", "--config", "sistema", "--alvo", "py",
                             "--grading", self.grading(8, 8, "x.json"))
        self.assertNotEqual(code, 0, "aceitou total 8 contra base 6 (L02: qualidade misturada com estrutura)")
        self.assertIn("L02", out)
        self.assertFalse([r for r in self.runs() if (r.get("quality") or {}).get("total") == 8],
                         "o registro recusado não pode ser gravado")
        code, out = self.cli("run", "record", "--config", "sistema", "--alvo", "py",
                             "--grading", self.grading(6, 6, "ok.json"))
        self.assertEqual(code, 0, out)

    def test_oracle_change_after_base_allows_new_total(self):
        self.init()
        self.assertEqual(self.cli("oracle", "freeze", "--file", self.grader)[0], 0)
        self.assertEqual(self.cli("run", "record", "--config", "sistema", "--alvo", "py",
                                  "--grading", self.grading(0, 6, "b.json"))[0], 0)
        self.assertNotEqual(self.cli("run", "record", "--config", "sistema", "--alvo", "py",
                                     "--grading", self.grading(8, 8, "x.json"))[0], 0)
        time.sleep(1.1)
        with open(self.grader, "a") as fh:
            fh.write("# +2 asserções de requisito\n")
        self.assertEqual(self.cli("oracle", "change", "--why", "requisito ampliado",
                                  "--evidence", "conferido à mão: grader.py linha 2")[0], 0)
        time.sleep(1.1)
        code, out = self.cli("run", "record", "--config", "sistema", "--alvo", "py",
                             "--grading", self.grading(8, 8, "x2.json"))
        self.assertEqual(code, 0, out)

    def test_oracle_change_before_base_does_not_excuse(self):
        self.init()
        self.assertEqual(self.cli("oracle", "freeze", "--file", self.grader)[0], 0)
        self.assertEqual(self.cli("oracle", "change", "--why", "a", "--evidence", "b")[0], 0)
        time.sleep(1.1)
        self.assertEqual(self.cli("run", "record", "--config", "sistema", "--alvo", "py",
                                  "--grading", self.grading(0, 6, "b.json"))[0], 0)
        code, out = self.cli("run", "record", "--config", "sistema", "--alvo", "py",
                             "--grading", self.grading(8, 8, "x.json"))
        self.assertNotEqual(code, 0, "oracle change ANTERIOR à base não justifica total diferente")
        self.assertIn("L02", out)


# ------------------------------------------------------------------ AC-04 (a) tty + desafio

BYPASS_ENV = {"AC_TEST_TTY": "1", "AC_ALLOW_NONTTY": "1", "AC_FORCE_TTY": "1", "AC_TEST": "1",
              "AC_SKIP_TTY": "1", "AC_TTY_BYPASS": "1", "AC_HUMAN": "1", "AC_INTERACTIVE": "1", "CI": "1"}


class AC04aCanalHumanoTest(Base):
    def test_gate_refused_without_tty(self):
        self.init()
        code, out = self.cli("gate", "stop", "--by", "founder", "--decision", "approve")
        self.assertEqual(code, 2, "gate sem tty deveria sair 2; saiu %d: %s" % (code, out))
        code, out = self.cli("gate", "stop", "--by", "founder", "--decision", "approve", input="sim\napprove\n")
        self.assertEqual(code, 2, "gate com stdin em pipe deveria sair 2")
        self.assertNotIn("stop", self.state().get("gates") or {})
        self.assertEqual(self.cli("check", "intake.3")[0], 1)

    def test_preauth_refused_without_tty(self):
        self.init()
        code, out = self.cli("preauth", "commit", "--by", "founder", "--requires", "integracao.1", "integracao.2")
        self.assertEqual(code, 2, out)
        self.assertNotIn("commit", self.state().get("preauth") or {})

    def test_env_vars_do_not_bypass_tty(self):
        self.init()
        env = dict(self.env, **BYPASS_ENV)
        self.assertEqual(self.cli("gate", "stop", "--by", "founder", "--decision", "approve", env=env)[0], 2)
        self.assertEqual(self.cli("preauth", "commit", "--by", "f", "--requires", "integracao.1", env=env)[0], 2)
        self.assertEqual(self.cli("check", "intake.3")[0], 1)

    def test_simulated_gate_without_tty_never_satisfies_a_gate(self):
        self.init()
        self.cli("gate", "stop", "--by", "bot", "--decision", "approve", "--simulated")
        self.assertNotEqual(self.cli("check", "intake.3")[0], 0,
                            "portão simulado gravado sem tty não pode satisfazer gate:stop")

    def test_gate_in_tty_with_retyped_challenge(self):
        self.init()
        code, out, ch = self.cli_tty("gate", "stop", "--by", "founder", "--decision", "approve")
        self.assertIsNotNone(ch, "nenhuma linha 'DESAFIO: <palavras>' exibida no terminal; saída: %r" % out[-400:])
        self.assertEqual(code, 0, out)
        g = self.state()["gates"]["stop"]
        self.assertEqual(g["decision"], "approve")
        self.assertFalse(g.get("simulated"))
        self.assertEqual(self.cli("check", "intake.3")[0], 0)

    def test_gate_in_tty_wrong_challenge_refused(self):
        self.init()
        code, out, ch = self.cli_tty("gate", "stop", "--by", "founder", "--decision", "approve",
                                     answer="palavra errada aqui agora")
        self.assertIsNotNone(ch, "desafio não exibido")
        self.assertNotEqual(code, 0)
        self.assertNotIn("stop", self.state().get("gates") or {})

    def test_preauth_in_tty_with_retyped_challenge(self):
        self.init()
        code, out, ch = self.cli_tty("preauth", "commit", "--by", "founder", "--requires", "integracao.1")
        self.assertIsNotNone(ch, "desafio não exibido")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.state()["preauth"]["commit"]["requires"], ["integracao.1"])

    def test_challenge_varies_between_calls(self):
        self.init()
        _, _, c1 = self.cli_tty("gate", "x1", "--by", "founder", "--decision", "approve")
        _, _, c2 = self.cli_tty("gate", "x2", "--by", "founder", "--decision", "approve")
        self.assertIsNotNone(c1)
        self.assertIsNotNone(c2)
        self.assertNotEqual(c1, c2, "desafio fixo pode ser pré-digitado")


# ------------------------------------------------------------------ AC-04 (d) auditoria

class AC04dAuditoriaTest(Base):
    def test_each_approval_appends_audit_line_outside_work(self):
        self.init()
        self.assertEqual(self.cli_tty("gate", "stop", "--by", "founder", "--decision", "approve")[0], 0)
        self.assertEqual(self.cli_tty("preauth", "commit", "--by", "founder", "--requires", "integracao.1")[0], 0)
        lines = self.audit_lines()
        self.assertEqual(len(lines), 2, "esperado 1 linha por aprovação em %s" % self.audit)
        self.assertFalse(os.path.realpath(self.audit).startswith(self.work + os.sep))
        g, p = lines
        self.assertEqual((g.get("cmd"), g.get("name"), g.get("decision"), g.get("by")),
                         ("gate", "stop", "approve", "founder"))
        self.assertEqual((p.get("cmd"), p.get("name")), ("preauth", "commit"))
        for x in lines:
            self.assertEqual(os.path.realpath(x.get("work") or ""), self.work)
            self.assertTrue(x.get("user"), "linha sem usuário do SO")
            self.assertTrue(x.get("tty"), "linha sem ttyname")
            self.assertTrue(x.get("ts"), "linha sem timestamp")

    def test_audit_log_inside_work_dir_refused(self):
        self.init()
        env = dict(self.env, AC_AUDIT_LOG=os.path.join(self.work, ".auto-correcao", "audit.jsonl"))
        code, out, _ = self.cli_tty("gate", "stop", "--by", "founder", "--decision", "approve", env=env)
        self.assertNotEqual(code, 0, "log de auditoria dentro do diretório da campanha deve ser recusado")
        self.assertNotIn("stop", self.state().get("gates") or {})


# ------------------------------------------------------------------ AC-04 (b,c) hook PreToolUse

def run_hook(payload, *args):
    p = subprocess.run([sys.executable, HOOK] + list(args), input=json.dumps(payload), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=30, universal_newlines=True)
    return p.returncode, p.stdout, p.stderr


def hook_denies(code, out):
    """Bloqueio pela doc de hooks do Claude Code: exit 2, ou JSON com permissionDecision=deny / decision=block."""
    if code == 2:
        return True
    try:
        j = json.loads(out) if out.strip() else {}
    except ValueError:
        return False
    hso = j.get("hookSpecificOutput") or {}
    return hso.get("permissionDecision") == "deny" or j.get("decision") == "block"


def bash(cmd, agent=False):
    p = {"session_id": "s", "transcript_path": "/tmp/t.jsonl", "cwd": "/tmp", "hook_event_name": "PreToolUse",
         "tool_name": "Bash", "tool_input": {"command": cmd, "description": "x"}}
    if agent:
        p.update(agent_id="a-1", agent_type="general-purpose")
    return p


ABS = AC
DENY = [
    "python3 %s --work /tmp/c gate stop --by founder --decision approve" % ABS,
    "python3 ~/.claude/skills/auto-correcao/scripts/ac.py --work /tmp/c preauth commit --by f --requires integracao.1",
    "cd ~/.claude/skills/auto-correcao/scripts && python3 ./ac.py --work /tmp/c gate stop --by f --decision approve",
    "python3 ac.py --work /tmp/c gate stop --by f --decision approve",
    "./ac.py --work /tmp/c gate stop --by f --decision approve",
    "PYTHONPATH=~/.claude/skills/auto-correcao/scripts python3 -m ac --work /tmp/c gate stop --by f --decision approve",
    '"python3" "%s" --work /tmp/c "gate" stop --by f --decision approve' % ABS,
    "python3 '%s' '--work' '/tmp/c' 'preauth' commit --by f --requires integracao.1" % ABS,
    "sh -c 'python3 %s --work /tmp/c gate stop --by f --decision approve'" % ABS,
    'bash -c "python3 ac.py --work /tmp/c preauth commit --by f --requires integracao.1"',
    "true; python3 ac.py --work /tmp/c gate stop --by f --decision approve",
    "echo ok && python3 ac.py --work /tmp/c gate stop --by f --decision approve",
    "yes | python3 ac.py --work /tmp/c gate stop --by f --decision approve",
    "ls\npython3 ac.py --work /tmp/c gate stop --by f --decision approve",
    "AC=%s; python3 \"$AC\" --work /tmp/c gate stop --by f --decision approve" % ABS,
    "python3 $AC --work /tmp/c gate stop --by f --decision approve",
    "python3 ${AC} --work /tmp/c preauth commit --by f --requires integracao.1",
    "python3 -c 'import runpy,sys; sys.argv=[\"ac.py\",\"--work\",\"/tmp/c\",\"gate\",\"stop\",\"--by\",\"f\","
    "\"--decision\",\"approve\"]; runpy.run_path(\"%s\", run_name=\"__main__\")'" % ABS,
    "python3 /x/construcao-orquestrada/scripts/co.py --work /tmp/o approve entrega",
    "python3 co.py approve plan:DEC-1",
    "sh -c \"cd /x && python3 ./co.py --work . approve stop\"",
]
ALLOW = [
    "ls -la",
    "git status",
    "echo gate",
    "python3 other.py gate stop",
    "cat docs/gate.md",
    "python3 %s --work /tmp/c status" % ABS,
    "python3 %s --work /tmp/c check intake.3" % ABS,
    "python3 ac.py --work /tmp/c done intake",
    "python3 ac.py --work /tmp/c run record --config sistema --alvo py",
    "python3 \"$AC\" --work /tmp/c status",
    "python3 co.py --work /tmp/o status",
]


class AC04bHookTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue(os.path.isfile(HOOK), "falta %s" % HOOK)

    def test_denies_approval_commands_and_variants(self):
        for cmd in DENY:
            for agent in (False, True):  # principal (sem agent_id) e subagente
                with self.subTest(cmd=cmd, agent=agent):
                    code, out, err = run_hook(bash(cmd, agent))
                    self.assertTrue(hook_denies(code, out), "não bloqueou (exit %d, out %r)" % (code, out))

    def test_allows_unrelated_and_read_only_ac_commands(self):
        for cmd in ALLOW:
            with self.subTest(cmd=cmd):
                code, out, err = run_hook(bash(cmd, agent=True))
                self.assertEqual(code, 0, "exit %d: %s" % (code, err))
                self.assertFalse(hook_denies(code, out), out)

    def test_allows_non_bash_tools(self):
        p = {"session_id": "s", "hook_event_name": "PreToolUse", "tool_name": "Read",
             "tool_input": {"file_path": "/tmp/ac.py"}}
        code, out, err = run_hook(p)
        self.assertEqual(code, 0, err)
        self.assertFalse(hook_denies(code, out))


class AC04cHookSelftestTest(unittest.TestCase):
    def test_selftest_exits_zero(self):
        self.assertTrue(os.path.isfile(HOOK), "falta %s" % HOOK)
        p = subprocess.run([sys.executable, HOOK, "--selftest"], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=60, universal_newlines=True)
        self.assertEqual(p.returncode, 0, p.stdout)


# ------------------------------------------------------------------ L17

class L17CampanhasSobrepostasTest(Base):
    def test_licao_L17_registered(self):
        ls = acmod().json5_load(LICOES)["licoes"]
        l17 = [x for x in ls if x.get("id") == "L17"]
        self.assertEqual(len(l17), 1, "L17 ausente em licoes.json5")
        txt = " ".join(str(l17[0].get(k, "")) for k in ("tema", "licao", "evidencia", "regra")).lower()
        self.assertIn("campanha", txt)
        self.assertIn("disjunt", txt)
        self.assertTrue(re.search(r"sobrep|simult|concorr|paralel", txt), txt)
        self.assertTrue(l17[0].get("evidencia") and l17[0].get("regra"))

    def _two(self, scope_a, scope_b, target_b=None):
        self.wa, self.wb = os.path.join(self.tmp, "campA"), os.path.join(self.tmp, "campB")
        self.init(work=self.wa, scope=scope_a)
        self.init(work=self.wb, target=target_b or self.target, scope=scope_b)

    def test_overlap_disjoint_scopes_ok(self):
        self._two("src/a/**", "src/b/**")
        code, out = self.cli("overlap", "--other", self.wb, work=self.wa)
        self.assertEqual(code, 0, out)

    def test_overlap_colliding_scopes_exit_1(self):
        self._two("src/a/**", "src/**")
        code, out = self.cli("overlap", "--other", self.wb, work=self.wa)
        self.assertEqual(code, 1, out)
        self.assertIn("src/**", out)

    def test_same_globs_on_different_targets_do_not_collide(self):
        other = os.path.join(self.tmp, "alvo2")
        os.makedirs(other)
        self._two("src/**", "src/**", target_b=other)
        code, out = self.cli("overlap", "--other", self.wb, work=self.wa)
        self.assertEqual(code, 0, out)

    def test_scope_over_other_campaign_oracle_collides(self):
        self._two("src/a/**", "docs/**")
        os.makedirs(os.path.join(self.target, "src", "a"))
        orc = os.path.join(self.target, "src", "a", "test_aceite.py")
        with open(orc, "w") as fh:
            fh.write("assert False\n")
        self.assertEqual(self.cli("oracle", "freeze", "--file", orc, work=self.wb)[0], 0)
        code, out = self.cli("overlap", "--other", self.wb, work=self.wa)
        self.assertEqual(code, 1, "escopo de A cobre o oráculo de B: %s" % out)


if __name__ == "__main__":
    unittest.main()
