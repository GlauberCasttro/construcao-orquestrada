"""Utilidades dos testes do harness-dev (unittest, Python 3.9+, só stdlib)."""
import json
import warnings
import os
import shutil
import subprocess
import tempfile

warnings.simplefilter("ignore", ResourceWarning)
TOOLS = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SKILL = os.path.realpath(os.path.join(TOOLS, "..", ".."))
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]


def run(cmd, stdin=None, cwd=None, env=None):
    e = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    e.update(env or {})
    return subprocess.run(cmd, input=stdin, capture_output=True, text=True, cwd=cwd, env=e)


def decisao(saida):
    """'deny' se a saída do hook nega; 'allow' se vazia."""
    if not saida.strip():
        return "allow"
    return json.loads(saida)["hookSpecificOutput"]["permissionDecision"]


def fake_repo():
    """Repo git temporário com uma skill falsa 'fake' (tools copiados), commitada. Retorna (raiz, skill, ws);
    ws = <skill>/campanhas (layout de projeto: campanhas, cópias e portões dentro da skill, fora das cópias)."""
    raiz = os.path.realpath(tempfile.mkdtemp(prefix="hd-"))
    skill = os.path.join(raiz, "skills", "fake")
    os.makedirs(os.path.join(skill, ".claude", "tools"))
    for f in os.listdir(TOOLS):
        p = os.path.join(TOOLS, f)
        if os.path.isfile(p):
            shutil.copy2(p, os.path.join(skill, ".claude", "tools", f))
    os.makedirs(os.path.join(skill, ".claude", "state"))
    os.makedirs(os.path.join(skill, "tests", "t1"))
    escrever(os.path.join(skill, "a.py"), "def f():\n    return 1\n\n\ndef g():\n    return 2\n")
    escrever(os.path.join(skill, "SKILL.md"), "---\nname: fake\n---\n")
    escrever(os.path.join(skill, "tests", "t1", "test_ok.py"), 
        "import unittest\n\nclass T(unittest.TestCase):\n    def test_a(self):\n        self.assertTrue(True)\n")
    subprocess.run(["git", "init", "-q", "-b", "master"], cwd=raiz, check=True)
    subprocess.run(["git", "add", "-A"], cwd=raiz, check=True)
    subprocess.run(GIT + ["commit", "-q", "-m", "base"], cwd=raiz, check=True)
    return raiz, skill, os.path.join(skill, "campanhas")


def tool(skill, nome):
    return os.path.join(skill, ".claude", "tools", nome)


def escrever(path, texto, modo="w"):
    with open(path, modo, encoding="utf-8") as f:
        f.write(texto)


def ler(path, encoding="utf-8", errors=None):
    with open(path, encoding=encoding, errors=errors) as f:
        return f.read()
