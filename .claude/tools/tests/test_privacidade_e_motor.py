"""guard-privacidade.sh (termos privados fora do que é versionado) e motor de campanhas embutido (.claude/tools/ac/)."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

from _util import GIT, TOOLS, escrever, ler, run

GP = os.path.join(TOOLS, "guard-privacidade.sh")
AC = os.path.join(TOOLS, "ac")


class Privacidade(unittest.TestCase):
    def setUp(self):
        self.raiz = os.path.realpath(tempfile.mkdtemp(prefix="gp-"))
        os.makedirs(os.path.join(self.raiz, ".claude", "tools"))
        for f in ("_lib.sh", "guard-privacidade.sh"):
            shutil.copy2(os.path.join(TOOLS, f), os.path.join(self.raiz, ".claude", "tools", f))
        self.fora = tempfile.mkdtemp(prefix="gp-termos-")  # a lista fica FORA do repo (como local/, ignorado)
        self.termos = os.path.join(self.fora, "termos.txt")
        escrever(self.termos, "# comentário\nprojeto-secreto\nfulano.de.tal\n")
        escrever(os.path.join(self.raiz, "ok.md"), "nada de mais\n")
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.raiz, check=True)
        subprocess.run(["git", "add", "-A"], cwd=self.raiz, check=True)
        subprocess.run(GIT + ["commit", "-q", "-m", "base"], cwd=self.raiz, check=True)
        self.env = {"PRIV_TERMOS": self.termos}

    def tearDown(self):
        shutil.rmtree(self.raiz, ignore_errors=True)
        shutil.rmtree(self.fora, ignore_errors=True)

    def gp(self, *a):
        return run(["bash", os.path.join(self.raiz, ".claude", "tools", "guard-privacidade.sh")] + list(a),
                   cwd=self.raiz, env=self.env)

    def test_arvore_limpa_e_suja(self):
        self.assertEqual(self.gp().returncode, 0)
        escrever(os.path.join(self.raiz, "x.md"), "linha com Projeto-Secreto dentro\n")  # case-insensitive
        r = self.gp()
        self.assertEqual(r.returncode, 1)
        self.assertIn("x.md:1", r.stdout)

    def test_padroes_genericos_sem_lista(self):
        self.env = {"PRIV_TERMOS": os.path.join(self.raiz, "nao-existe.txt")}
        r = self.gp()
        self.assertEqual(r.returncode, 0)
        self.assertIn("AVISO", r.stderr)
        escrever(os.path.join(self.raiz, "e.md"), "contato: alguem" + "@" + "gmail.com\n")
        self.assertEqual(self.gp().returncode, 1)

    def test_local_e_ignorado(self):
        os.makedirs(os.path.join(self.raiz, "local"))
        escrever(os.path.join(self.raiz, "local", "n.md"), "projeto-secreto\n")
        self.assertEqual(self.gp().returncode, 0)

    def test_staged_msg_e_log(self):
        escrever(os.path.join(self.raiz, "s.md"), "fulano.de.tal\n")
        subprocess.run(["git", "add", "s.md"], cwd=self.raiz, check=True)
        self.assertEqual(self.gp("--staged").returncode, 1)
        subprocess.run(["git", "rm", "-q", "--cached", "s.md"], cwd=self.raiz, check=True)
        os.remove(os.path.join(self.raiz, "s.md"))
        self.assertEqual(self.gp("--staged").returncode, 0)
        m = os.path.join(self.raiz, "msg.txt")
        escrever(m, "feat: coisa do projeto-secreto\n")
        self.assertEqual(self.gp("--staged", "--msg", m).returncode, 1)
        self.assertEqual(self.gp("--log").returncode, 0)

    def test_install_hook_barra_commit(self):
        self.assertEqual(self.gp("--install-hook").returncode, 0)
        escrever(os.path.join(self.raiz, "h.md"), "projeto-secreto\n")
        subprocess.run(["git", "add", "h.md"], cwd=self.raiz, check=True)
        r = subprocess.run(GIT + ["commit", "-q", "-m", "x"], cwd=self.raiz, capture_output=True, text=True,
                           env=dict(os.environ, PRIV_TERMOS=self.termos))
        self.assertNotEqual(r.returncode, 0)

    def test_help(self):
        r = run(["bash", GP, "--help"])
        self.assertEqual(r.returncode, 0)
        self.assertIn("termos-privados", r.stdout)


class MotorEmbutido(unittest.TestCase):
    def test_origem_confere_sha256(self):
        t = ler(os.path.join(AC, "ORIGEM.txt"))
        self.assertRegex(t, r"commit [0-9a-f]{40}")
        pares = re.findall(r"^([0-9a-f]{64})  (\S+)$", t, re.M)
        self.assertGreaterEqual(len(pares), 7)
        for sha, rel in pares:
            with open(os.path.join(AC, rel), "rb") as fh:
                self.assertEqual(hashlib.sha256(fh.read()).hexdigest(), sha, rel)

    def test_lancadores_respondem(self):
        r = run(["python3", os.path.join(AC, "ac.py"), "--help"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("auto-correcao", r.stdout)
        r = run(["python3", os.path.join(AC, "hook_aprovacao.py"), "--selftest"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_hook_embutido_nega_aprovacao_pelo_agente(self):
        h = os.path.join(AC, "hook_aprovacao.py")
        nega = {"tool_name": "Bash", "tool_input": {"command": "python3 .claude/tools/ac/ac.py --work w gate stop"}}
        r = run(["python3", h], stdin=json.dumps(nega))
        self.assertEqual(r.returncode, 2, r.stderr)
        ok = {"tool_name": "Bash", "tool_input": {"command": "python3 .claude/tools/ac/ac.py --work w status"}}
        self.assertEqual(run(["python3", h], stdin=json.dumps(ok)).returncode, 0)

    def test_init_e_status_numa_campanha_temporaria(self):
        d = tempfile.mkdtemp(prefix="ac-")
        try:
            w = os.path.join(d, "camp")
            r = run(["python3", os.path.join(AC, "ac.py"), "--work", w, "init", "--problem", "p", "--scope", "x/**",
                     "--stop", "s"])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = run(["python3", os.path.join(AC, "ac.py"), "--work", w, "status"])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        finally:
            shutil.rmtree(d)

    def test_harness_usa_o_motor_embutido(self):
        lib = ler(os.path.join(TOOLS, "_lib.sh"))
        self.assertIn('AC="$HD_TOOLS/ac/ac.py"', lib)
        for n in ("new-front", "close-front", "load-session"):
            t = ler(os.path.join(TOOLS, "..", "skills", n, "SKILL.md"))
            self.assertNotIn("skills/auto-correcao/scripts/ac.py", t, n)


if __name__ == "__main__":
    unittest.main()
