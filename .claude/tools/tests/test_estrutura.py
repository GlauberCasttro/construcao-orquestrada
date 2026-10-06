"""Estrutura do harness: settings.json, tools, skills finas, nomes proibidos, limites do CLAUDE.md."""
import json
import os
import re
import subprocess
import sys
import unittest

from _util import SKILL, TOOLS, run, escrever, ler

HD = os.path.join(SKILL, ".claude")
PROIBIDOS = ["salvar-sessao", "carregar-sessao", "planejar-sprint", "new-epico", "close-epico", "/corrigir"]
SKILLS = ["load-session", "save-session", "new-front", "close-front"]


def arquivos_de_texto():
    for base, dirs, files in os.walk(HD):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith(".pyc") or f == ".DS_Store":
                continue
            yield os.path.join(base, f)


class Estrutura(unittest.TestCase):
    def test_settings_json(self):
        s = json.loads(ler(os.path.join(HD, "settings.json")))
        pre = {h["matcher"]: h["hooks"][0]["command"] for h in s["hooks"]["PreToolUse"]}
        self.assertIn("guard-git.sh", pre["Bash"])
        self.assertIn("guard-entrega.py", pre["Edit|Write|NotebookEdit"])
        bash = [h for h in s["hooks"]["PreToolUse"] if h["matcher"] == "Bash"][0]["hooks"]
        self.assertTrue(any(".claude/tools/ac/hook_aprovacao.py" in c["command"] for c in bash))  # motor embutido
        self.assertTrue(re.search(r"carimbo\.sh\"? --brief", s["hooks"]["SessionStart"][0]["hooks"][0]["command"]))
        for h in [x for v in s["hooks"].values() for x in v]:
            for c in h["hooks"]:
                m = re.search(r"\.claude/tools/([\w./-]+\.(?:sh|py))", c["command"])
                self.assertTrue(os.path.isfile(os.path.join(TOOLS, m.group(1))), c["command"])

    def test_tools_sintaxe_e_help(self):
        for f in sorted(os.listdir(TOOLS)):
            p = os.path.join(TOOLS, f)
            if not os.path.isfile(p) or f.startswith("_lib"):
                continue
            if f.endswith(".sh"):
                self.assertEqual(subprocess.run(["bash", "-n", p]).returncode, 0, f)
                self.assertTrue(os.access(p, os.X_OK), f + " sem +x")
                r = run(["bash", p, "--help"])
            elif f.endswith(".py"):
                self.assertEqual(subprocess.run([sys.executable, "-m", "py_compile", p],
                                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode, 0, f)
                r = run([sys.executable, p, "--help"])
            else:
                continue
            self.assertEqual(r.returncode, 0, "%s --help: %s" % (f, r.stderr))
            self.assertTrue(r.stdout.strip(), f + " --help vazio")

    def test_skills_finas_com_frontmatter(self):
        for n in SKILLS:
            t = ler(os.path.join(HD, "skills", n, "SKILL.md"), encoding="utf-8")
            m = re.match(r"^---\nname: ([\w-]+)\ndescription: (.+)\n(?:disable-model-invocation: true\n)?---\n", t)
            self.assertTrue(m, n)
            self.assertEqual(m.group(1), n)
            self.assertLessEqual(len(t.splitlines()), 30, n + " não é fina")
            for tool in re.findall(r"tools/([\w./-]+\.(?:sh|py))", t):
                self.assertTrue(os.path.isfile(os.path.join(TOOLS, tool)), "%s cita tool inexistente %s" % (n, tool))
        for n in ("save-session", "new-front", "close-front"):  # mudam estado: só o humano
            self.assertIn("disable-model-invocation: true", ler(os.path.join(HD, "skills", n, "SKILL.md")))
        self.assertFalse(os.path.exists(os.path.join(HD, "skills", "publish")))  # só codebase-specialists

    def test_nomes_proibidos_ausentes(self):
        este = os.path.abspath(__file__)
        for p in arquivos_de_texto():
            if os.path.abspath(p) == este or p.endswith("test_guard_git.py") or p.endswith("test_guard_entrega.py"):
                continue
            try:
                t = ler(p, encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for n in PROIBIDOS:
                self.assertNotIn(n, t, "%s contém nome proibido %r" % (p, n))

    def test_claude_md_limites(self):
        t = ler(os.path.join(HD, "CLAUDE.md"), encoding="utf-8")
        self.assertLessEqual(len(t.splitlines()), 90)
        for secao in ("Fluxo de entrega", "Retomada da onda 1", "Git e privacidade", "Lições", "Rituais", "O que NÃO existe"):
            self.assertIn(secao, t)
        for tool in re.findall(r"tools/([\w./-]+\.(?:sh|py))", t):
            self.assertTrue(os.path.isfile(os.path.join(TOOLS, tool)), "CLAUDE.md cita tool inexistente: " + tool)

    def test_state_completo(self):
        for f in ("RESUME.md", "WORKFLOW.md", "BACKLOG.md", "DECISIONS.md", "CAMPANHA_ATIVA"):
            self.assertTrue(os.path.isfile(os.path.join(HD, "state", f)), f)
        self.assertTrue(os.path.isdir(os.path.join(HD, "state", "logs")))
        r = run(["python3", os.path.join(TOOLS, "frente.py"), "check"])
        self.assertEqual(r.returncode, 0, r.stdout)
        resume = ler(os.path.join(HD, "state", "RESUME.md"), encoding="utf-8")
        self.assertIn("<!-- carimbo:begin -->", resume)
        bl = ler(os.path.join(HD, "state", "BACKLOG.md"), encoding="utf-8")
        self.assertRegex(bl, r"P0")
        self.assertIn("onda 1", bl.lower())

    def test_sem_segredos_nem_caminho_privado_novo(self):
        for p in arquivos_de_texto():
            if p.endswith("sessoes.jsonl"):
                continue
            t = ler(p, encoding="utf-8", errors="ignore")
            self.assertNotRegex(t, r"(?i)(password|senha)\s*[=:]\s*\S{4,}", p)
            self.assertNotRegex(t, r"sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}", p)
            self.assertNotRegex(t, r"[A-Za-z0-9._%+-]+@(gmail|hotmail|outlook|yahoo|icloud)\.com", p)

    def test_nao_ha_instrucao_de_aprovar_pela_ia(self):
        t = ler(os.path.join(HD, "CLAUDE.md"), encoding="utf-8")
        self.assertIn("Nunca aprove pela IA", t)


if __name__ == "__main__":
    unittest.main()
