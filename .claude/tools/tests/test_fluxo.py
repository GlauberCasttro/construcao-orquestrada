"""copia -> portao -> conferir-commit -> portar, em repo git temporário com uma skill falsa."""
import json
import os
import shutil
import subprocess
import unittest

from _util import GIT, fake_repo, run, tool, escrever, ler

TEM_PY39 = os.path.exists("/usr/bin/python3")


def sh(skill, nome, *args, **kw):
    return run(["bash", tool(skill, nome)] + list(args), cwd=skill, **kw)


@unittest.skipUnless(TEM_PY39, "precisa de /usr/bin/python3")
class Fluxo(unittest.TestCase):
    def setUp(self):
        self.raiz, self.skill, self.ws = fake_repo()

    def tearDown(self):
        shutil.rmtree(self.raiz, ignore_errors=True)

    def edita_copia(self, frente, rel, texto):
        p = os.path.join(self.ws, "work", frente, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        escrever(p, texto, "w")

    def test_helps(self):
        for t in ("copia.sh", "portao.sh", "conferir-commit.sh", "portar.sh", "carimbo.sh", "guard-git.sh"):
            r = sh(self.skill, t, "--help")
            self.assertEqual(r.returncode, 0, t + r.stderr)
            self.assertTrue(r.stdout.strip(), t)

    def test_copia_cria_e_nao_sobrescreve(self):
        r = sh(self.skill, "copia.sh", "f1")
        self.assertEqual(r.returncode, 0, r.stderr)
        d = os.path.join(self.ws, "work", "f1")
        self.assertEqual(r.stdout.strip(), d)
        self.assertTrue(os.path.exists(os.path.join(d, "a.py")))
        self.assertFalse(os.path.exists(os.path.join(d, "campanhas")))  # a cópia não leva campanhas/
        self.assertNotEqual(sh(self.skill, "copia.sh", "f1").returncode, 0)  # não sobrescreve
        self.assertNotEqual(sh(self.skill, "copia.sh", "../x").returncode, 0)  # nome inválido

    def test_copia_e_portao_excluem_campanhas_local_e_dist(self):
        for rel in ("campanhas/c1/oraculo/test_x.py", "local/nota.md", "dist/pacote.txt"):
            os.makedirs(os.path.dirname(os.path.join(self.skill, rel)), exist_ok=True)
            escrever(os.path.join(self.skill, rel), "x\n", "w")
        subprocess.run(["git", "add", "-f", "skills/fake/campanhas", "skills/fake/local", "skills/fake/dist"],
                       cwd=self.raiz, check=True)
        subprocess.run(GIT + ["commit", "-q", "-m", "dados"], cwd=self.raiz, check=True)
        escrever(os.path.join(self.skill, "local", "solto.md"), "y\n", "w")  # não versionado
        sh(self.skill, "copia.sh", "x", "--com-untracked")
        d = os.path.join(self.ws, "work", "x")
        for top in ("campanhas", "local", "dist"):
            self.assertFalse(os.path.exists(os.path.join(d, top)), top)
        self.assertTrue(os.path.exists(os.path.join(d, "a.py")))
        self.edita_copia("x", "a.py", "def f():\n    return 8\n\n\ndef g():\n    return 2\n")
        self.assertEqual(self.portao("x", "--", "a.py").returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(self.ws, "portao-x", "limpa", "campanhas")))

    def test_copia_dry_run_nao_cria(self):
        r = sh(self.skill, "copia.sh", "f2", "--dry-run")
        self.assertEqual(r.returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(self.ws, "work", "f2")))

    def test_copia_com_untracked(self):
        escrever(os.path.join(self.skill, "novo.py"), "def n():\n    pass\n", "w")
        os.makedirs(os.path.join(self.skill, "__pycache__"))
        escrever(os.path.join(self.skill, "__pycache__", "x.pyc"), "x", "w")
        sh(self.skill, "copia.sh", "f3", "--com-untracked")
        self.assertTrue(os.path.exists(os.path.join(self.ws, "work", "f3", "novo.py")))
        self.assertTrue(os.path.exists(os.path.join(self.ws, "work", "f3.base", "novo.py")))
        self.assertFalse(os.path.exists(os.path.join(self.ws, "work", "f3", "__pycache__")))

    def portao(self, frente, *extra):
        return sh(self.skill, "portao.sh", frente, *extra)

    def test_portao_verde_roda_nos_dois_pythons_e_termina_em_FIM(self):
        sh(self.skill, "copia.sh", "v")
        self.edita_copia("v", "a.py", "def f():\n    return 10\n\n\ndef g():\n    return 2\n")
        r = self.portao("v", "--", "a.py")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("VERDE", r.stdout)
        self.assertIn("python3 tests/t1", r.stdout)
        self.assertIn("/usr/bin/python3 tests/t1", r.stdout)
        out = ler(os.path.join(self.ws, "portao-v", "portao.out"))
        self.assertTrue(out.rstrip().endswith("FIM"))
        j = json.loads(ler(os.path.join(self.ws, "portao-v", "portao.json")))
        self.assertEqual(j["veredito"], "VERDE")
        self.assertEqual(sum(1 for x in j["resultados"] if x["item"].startswith("suite:")), 2)
        # a cópia limpa tem a versão da frente
        self.assertIn("return 10", ler(os.path.join(self.ws, "portao-v", "limpa", "a.py")))

    def test_portao_vermelho_reporta_e_exit_1(self):
        sh(self.skill, "copia.sh", "r")
        self.edita_copia("r", "tests/t1/test_ok.py",
                         "import unittest\n\nclass T(unittest.TestCase):\n    def test_a(self):\n        self.fail('x')\n")
        r = self.portao("r", "--", "tests/t1/test_ok.py")
        self.assertEqual(r.returncode, 1)
        self.assertIn("VERMELHO", r.stdout)
        self.assertIn("rc=1", r.stdout)
        self.assertTrue(ler(os.path.join(self.ws, "portao-r", "portao.out")).rstrip().endswith("FIM"))

    def test_portao_detecta_def_removido(self):
        sh(self.skill, "copia.sh", "d")
        self.edita_copia("d", "a.py", "def f():\n    return 1\n")  # g sumiu
        r = self.portao("d", "--", "a.py")
        self.assertEqual(r.returncode, 1)
        self.assertIn("REMOVIDO a.py: g", r.stdout)

    def test_portao_so_inclui_arquivos_listados(self):
        sh(self.skill, "copia.sh", "s")
        self.edita_copia("s", "a.py", "def f():\n    return 5\n\n\ndef g():\n    return 2\n")
        self.edita_copia("s", "extra.py", "x = 1\n")  # não listado
        self.portao("s", "--", "a.py")
        self.assertFalse(os.path.exists(os.path.join(self.ws, "portao-s", "limpa", "extra.py")))

    def test_portao_recusa_entradas_ruins(self):
        sh(self.skill, "copia.sh", "e")
        for args in (["e"], ["e", "--"], ["e", "--", "../x"], ["e", "--", "/etc/passwd"], ["e", "--", "naoexiste.py"]):
            self.assertNotEqual(self.portao(*args).returncode, 0, args)
        self.assertNotEqual(self.portao("e", "--oraculo", "semdoispontos", "--", "a.py").returncode, 0)
        self.assertNotEqual(self.portao("e", "--src", "/nao/existe", "--", "a.py").returncode, 0)

    def test_portao_dry_run(self):
        sh(self.skill, "copia.sh", "p")
        r = self.portao("p", "--dry-run", "--", "a.py")
        self.assertEqual(r.returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(self.ws, "portao-p", "limpa")))

    def test_portao_oraculo_externo_usa_a_copia_limpa(self):
        sh(self.skill, "copia.sh", "o")
        self.edita_copia("o", "a.py", "def f():\n    return 77\n\n\ndef g():\n    return 2\n")
        orc = os.path.join(self.raiz, "orc"); os.makedirs(orc)
        escrever(os.path.join(orc, "test_orc.py"),
            "import os, unittest\n\nclass O(unittest.TestCase):\n    def test_home(self):\n"
            "        p = os.path.join(os.path.expanduser('~'), '.claude', 'skills', 'fake', 'a.py')\n"
            "        self.assertIn('return 77', open(p).read())\n"
            "        self.assertTrue(os.environ['CO_SKILL_DIR'].endswith(os.path.join('portao-o', 'limpa')))\n")
        r = self.portao("o", "--oraculo", orc + ":test_orc", "--", "a.py")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("oráculo python3 test_orc", r.stdout)
        self.assertIn("oráculo /usr/bin/python3 test_orc", r.stdout)

    def test_conferir_commit(self):
        sh(self.skill, "copia.sh", "c")
        self.edita_copia("c", "a.py", "def f():\n    return 3\n\n\ndef g():\n    return 2\n")
        self.assertEqual(self.portao("c", "--", "a.py").returncode, 0)
        self.assertEqual(sh(self.skill, "portar.sh", "c", "--", "a.py").returncode, 0)
        self.assertEqual(sh(self.skill, "conferir-commit.sh", "c", "--", "a.py").returncode, 0)
        escrever(os.path.join(self.skill, "a.py"), "# mudou depois do portão\n", "a")
        r = sh(self.skill, "conferir-commit.sh", "c", "--", "a.py")
        self.assertEqual(r.returncode, 1)
        self.assertIn("DIFERE", r.stdout)
        r = sh(self.skill, "conferir-commit.sh", "c", "--", "SKILL.md", "a.py")  # SKILL.md veio de HEAD: idêntico
        self.assertIn("ok: SKILL.md", r.stdout)
        self.assertNotEqual(sh(self.skill, "conferir-commit.sh", "nunca-rodou", "--", "a.py").returncode, 0)

    def test_portar_copia_quando_vivo_igual_a_head(self):
        sh(self.skill, "copia.sh", "p1")
        self.edita_copia("p1", "a.py", "def f():\n    return 9\n\n\ndef g():\n    return 2\n")
        r = sh(self.skill, "portar.sh", "p1", "--", "a.py")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("return 9", ler(os.path.join(self.skill, "a.py")))

    def test_portar_merge_limpo_e_conflito(self):
        base = "l1\nl2\nl3\nl4\nl5\nl6\nl7\nl8\nl9\n"
        escrever(os.path.join(self.skill, "m.txt"), base, "w")
        subprocess.run(["git", "add", "skills/fake/m.txt"], cwd=self.raiz, check=True)
        subprocess.run(GIT + ["commit", "-q", "-m", "m"], cwd=self.raiz, check=True)
        sh(self.skill, "copia.sh", "m")
        self.edita_copia("m", "m.txt", base.replace("l9", "L9-frente"))
        escrever(os.path.join(self.skill, "m.txt"), base.replace("l1\n", "L1-vivo\n"))  # outra sessão
        r = sh(self.skill, "portar.sh", "m", "--", "m.txt")
        self.assertEqual(r.returncode, 0, r.stdout)
        t = ler(os.path.join(self.skill, "m.txt"))
        self.assertIn("L1-vivo", t); self.assertIn("L9-frente", t)
        # conflito: mesma linha
        escrever(os.path.join(self.skill, "m.txt"), base)  # volta ao HEAD
        sh(self.skill, "copia.sh", "m2")
        self.edita_copia("m2", "m.txt", base.replace("l5", "L5-frente"))
        vivo = base.replace("l5", "L5-vivo")
        escrever(os.path.join(self.skill, "m.txt"), vivo, "w")
        r = sh(self.skill, "portar.sh", "m2", "--", "m.txt")
        self.assertEqual(r.returncode, 1)
        self.assertIn("CONFLITO", r.stdout)
        self.assertEqual(ler(os.path.join(self.skill, "m.txt")), vivo)  # vivo intocado
        self.assertIn("<<<<<<<", ler(os.path.join(self.ws, "work", "m2.conflitos", "m.txt")))

    def test_portar_dry_run_e_arquivo_ausente(self):
        sh(self.skill, "copia.sh", "q")
        self.edita_copia("q", "a.py", "def f():\n    return 4\n\n\ndef g():\n    return 2\n")
        r = sh(self.skill, "portar.sh", "q", "--dry-run", "--", "a.py")
        self.assertIn("[dry-run] copiar", r.stdout)
        self.assertIn("return 1", ler(os.path.join(self.skill, "a.py")))
        self.assertEqual(sh(self.skill, "portar.sh", "q", "--", "inexistente.py").returncode, 1)

    def test_portar_nao_versionado_usa_base_da_copia(self):
        escrever(os.path.join(self.skill, "u.py"), "a\nb\nc\nd\ne\nf\ng\nh\n", "w")
        sh(self.skill, "copia.sh", "u", "--com-untracked")
        self.edita_copia("u", "u.py", "a\nb\nc\nd\ne\nf\ng\nH-frente\n")
        escrever(os.path.join(self.skill, "u.py"), "A-vivo\nb\nc\nd\ne\nf\ng\nh\n", "w")
        self.assertEqual(sh(self.skill, "portar.sh", "u", "--", "u.py").returncode, 0)
        t = ler(os.path.join(self.skill, "u.py"))
        self.assertTrue(t.startswith("A-vivo") and "H-frente" in t)

    def test_carimbo_real_e_json(self):
        r = sh(self.skill, "carimbo.sh")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("branch master", r.stdout)
        j = json.loads(sh(self.skill, "carimbo.sh", "--json").stdout)
        self.assertEqual(j["branch"], "master")
        self.assertEqual(len(j["head"]), 7)
        b = sh(self.skill, "carimbo.sh", "--brief").stdout
        self.assertTrue(b.startswith("[harness-dev]"))

    def test_carimbo_write_resume(self):
        f = os.path.join(self.skill, ".claude", "state", "RESUME.md")
        escrever(f, "# R\n<!-- carimbo:begin -->\nvelho\n<!-- carimbo:end -->\ncorpo\n", "w")
        self.assertEqual(sh(self.skill, "carimbo.sh", "--write-resume").returncode, 0)
        t = ler(f)
        self.assertNotIn("velho", t); self.assertIn("branch master", t); self.assertTrue(t.endswith("corpo\n"))


if __name__ == "__main__":
    unittest.main()
