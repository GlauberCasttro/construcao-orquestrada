"""Base da revisão v4: cópia da skill num HOME temporário (.claude/skills/construcao-orquestrada = cópia;
.claude/skills/auto-correcao = link para a auto-correcao). Nada aqui toca a skill real. Python 3.9+, só stdlib."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

# Skill sob teste: CO_SKILL_DIR, senão a raiz do projeto (campanhas/revisao-v4 -> ../..).
SRC = os.path.realpath(os.environ.get("CO_SKILL_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
# auto-correcao (o produto reusa o json5 do ac.py): CO_AC_DIR, a instalada, o projeto irmão, ou o motor embutido.
_ACS = [os.environ.get("CO_AC_DIR", ""), os.path.expanduser("~/.claude/skills/auto-correcao"),
        os.path.join(os.path.dirname(SRC), "auto-correcao"), os.path.join(SRC, ".claude", "tools", "ac")]
AC_DIR = os.path.realpath(next((d for d in _ACS if d and os.path.isfile(os.path.join(d, "scripts", "ac.py"))), _ACS[1]))
PY = os.environ.get("REV_PY", sys.executable)


class Base(unittest.TestCase):
    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="rev4-"))
        self.home = os.path.join(self.root, "home")
        sk = os.path.join(self.home, ".claude", "skills")
        os.makedirs(sk)
        self.skill = os.path.join(sk, "construcao-orquestrada")
        shutil.copytree(SRC, self.skill, ignore=shutil.ignore_patterns("__pycache__", "tests", ".git", "campanhas",
                                                                       "local", "dist"))
        os.symlink(AC_DIR, os.path.join(sk, "auto-correcao"))
        self.scripts = os.path.join(self.skill, "scripts")
        self.co = os.path.join(self.scripts, "co.py")
        self.hook = os.path.join(self.scripts, "co_hook.py")
        self.env = dict(os.environ, HOME=self.home, PYTHONDONTWRITEBYTECODE="1")
        self.alvo = os.path.join(self.home, "proj", "alvo")
        self.ws = os.path.join(self.home, "obras", "ws1")
        os.makedirs(self.alvo)
        os.makedirs(os.path.dirname(self.ws))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def run_co(self, *args, stdin=None):
        p = subprocess.run([PY, self.co, "--work", self.ws] + list(args), env=self.env, cwd=self.root,
                           input=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
                           timeout=300)
        return p.returncode, p.stdout, p.stderr

    def init(self, tipo="cli", stop="pass_hat_3 >= 1.0"):
        rc, out, err = self.run_co("init", "--alvo", self.alvo, "--tipo", tipo, "--pedido", "x", "--stop", stop)
        self.assertEqual(rc, 0, out + err)

    def hook_payload(self, tool, ti, cwd, agent_type=None, agent_id=None):
        p = {"session_id": "s", "cwd": cwd, "hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": ti}
        if agent_id:
            p["agent_id"] = agent_id
            if agent_type:
                p["agent_type"] = agent_type
        r = subprocess.run([PY, self.hook], input=json.dumps(p), env=self.env, cwd=cwd, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True, timeout=60)
        return r.returncode, r.stderr

    def in_proc(self, code):
        """Roda `code` num processo com HOME temporário e scripts/ da cópia no sys.path; devolve (rc, out, err)."""
        boot = "import sys; sys.path.insert(0, %r)\n" % self.scripts + code
        p = subprocess.run([PY, "-c", boot], env=self.env, cwd=self.root, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True, timeout=300)
        return p.returncode, p.stdout, p.stderr
