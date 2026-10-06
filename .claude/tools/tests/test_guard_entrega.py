import json
import os
import shutil
import tempfile
import unittest

from _util import SKILL, TOOLS, decisao, run

G = os.path.join(TOOLS, "guard-entrega.py")


def chamar(payload, raw=None):
    r = run(["python3", G], stdin=raw if raw is not None else json.dumps(payload))
    assert r.returncode == 0, r.stderr
    return decisao(r.stdout), r.stdout


class GuardEntrega(unittest.TestCase):
    def test_edit_em_produto_nega(self):
        for rel in ("SKILL.md", "scripts/co.py", "references/contrato.json5", "PENDENTE.md", ".claude/CLAUDE.md",
                    ".claude/tools/guard-entrega.py", ".claude/settings.json", "tests/onda1/x.py"):
            d, out = chamar({"tool_name": "Edit", "tool_input": {"file_path": os.path.join(SKILL, rel)}})
            self.assertEqual(d, "deny", rel)
        self.assertIn("tools/copia.sh", out)  # a mensagem explica o fluxo

    def test_write_e_notebook_em_produto_nega(self):
        self.assertEqual(chamar({"tool_input": {"file_path": os.path.join(SKILL, "novo.py")}})[0], "deny")
        self.assertEqual(chamar({"tool_input": {"notebook_path": os.path.join(SKILL, "n.ipynb")}})[0], "deny")

    def test_state_permite(self):
        for rel in (".claude/state/RESUME.md", ".claude/state/logs/sessoes.jsonl", ".claude/state/novo/x.md"):
            self.assertEqual(chamar({"tool_input": {"file_path": os.path.join(SKILL, rel)}})[0], "allow", rel)

    def test_zonas_livres_do_projeto_permitem(self):  # campanhas/ (oráculos, cópias, portões) e local/
        for rel in ("campanhas/work/f/scripts/co.py", "campanhas/onda1/oraculo/x.py", "local/notas.md"):
            self.assertEqual(chamar({"tool_input": {"file_path": os.path.join(SKILL, rel)}})[0], "allow", rel)
        p = os.path.join(SKILL, "campanhas", "..", "scripts", "co.py")
        self.assertEqual(chamar({"tool_input": {"file_path": p}})[0], "deny")

    def test_traversal_fora_do_state_nega(self):
        p = os.path.join(SKILL, ".claude", "state", "..", "tools", "x.py")
        self.assertEqual(chamar({"tool_input": {"file_path": p}})[0], "deny")

    def test_fora_da_skill_permite(self):
        home = os.path.expanduser("~")
        for p in (os.path.join(home, ".claude/skills/auto-correcao/x.py"), "/tmp/qualquer.txt"):
            self.assertEqual(chamar({"tool_input": {"file_path": p}})[0], "allow", p)

    def test_prefixo_parecido_nao_confunde(self):  # campanhas não é construcao-orquestrada/
        p = SKILL + "-workspace/work/x.py"
        self.assertEqual(chamar({"tool_input": {"file_path": p}})[0], "allow")

    def test_relativo_resolve_pelo_cwd_do_payload(self):
        self.assertEqual(chamar({"cwd": SKILL, "tool_input": {"file_path": "scripts/co.py"}})[0], "deny")
        self.assertEqual(chamar({"cwd": SKILL, "tool_input": {"file_path": ".claude/state/RESUME.md"}})[0], "allow")
        self.assertEqual(chamar({"cwd": "/tmp", "tool_input": {"file_path": "x.py"}})[0], "allow")

    def test_symlink_para_dentro_nega(self):
        d = tempfile.mkdtemp()
        try:
            os.symlink(os.path.join(SKILL, "SKILL.md"), os.path.join(d, "elo.md"))
            self.assertEqual(chamar({"tool_input": {"file_path": os.path.join(d, "elo.md")}})[0], "deny")
        finally:
            shutil.rmtree(d)

    def test_payload_invalido_nega_com_motivo(self):
        for raw in ("", "não é json", "[]", "null", '{"tool_input": 3}', '{"tool_input": {}}',
                    '{"tool_input": {"file_path": ""}}', '{"tool_input": {"file_path": 7}}'):
            d, out = chamar(None, raw=raw)
            self.assertEqual(d, "deny", raw)
            self.assertIn("guard-entrega", out)

    def test_copia_de_trabalho_permite(self):
        for pai in ("campanhas", "x-workspace"):
            self._copia_de_trabalho_permite(pai)

    def _copia_de_trabalho_permite(self, pai):
        raiz = tempfile.mkdtemp()
        try:
            copia = os.path.join(raiz, pai, "work", "frente")
            os.makedirs(os.path.join(copia, ".claude", "tools"))
            shutil.copy2(G, os.path.join(copia, ".claude", "tools", "guard-entrega.py"))
            r = run(["python3", os.path.join(copia, ".claude", "tools", "guard-entrega.py")],
                    stdin=json.dumps({"tool_input": {"file_path": os.path.join(copia, "scripts", "co.py")}}))
            self.assertEqual(decisao(r.stdout), "allow")
        finally:
            shutil.rmtree(raiz)

    def test_help(self):
        r = run(["python3", G, "--help"])
        self.assertEqual(r.returncode, 0)
        self.assertIn("guard-entrega", r.stdout)


if __name__ == "__main__":
    unittest.main()
