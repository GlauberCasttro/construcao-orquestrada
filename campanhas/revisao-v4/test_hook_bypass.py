"""Q3 — hook PreToolUse: variações de caminho/ferramenta que deveriam bloquear (exit 2) e passam (exit 0).
Cada teste afirma o comportamento do CONTRATO (bloquear); falha = achado."""
import json
import os
import subprocess
import unittest

from _base import Base

SUB = dict(agent_id="ag-1", agent_type="builder-A")  # construtor (não autor no MANIFEST)


class HookBypass(Base):
    def setUp(self):
        super().setUp()
        for d in (".construcao", "aprovacoes", "oraculo/dev", "oraculo/heldout/casos"):
            os.makedirs(os.path.join(self.ws, d))
        with open(os.path.join(self.ws, ".construcao", "ledger.jsonl"), "w") as fh:
            fh.write("")
        with open(os.path.join(self.ws, "oraculo", "heldout", "casos", "C-01.json"), "w") as fh:
            fh.write('{"id": "h-01"}')
        with open(os.path.join(self.ws, "oraculo", "MANIFEST.json5"), "w") as fh:
            json.dump({"schema_version": 1, "frentes": {"T-01": {"autores": ["oraculo-O1"], "dev": ["oraculo/dev/**"],
                                                                  "heldout": ["oraculo/heldout/**"]}}}, fh)
        self.H = os.path.join(self.ws, "oraculo", "heldout", "casos", "C-01.json")

    def bash(self, cmd, cwd=None, **who):
        return self.hook_payload("Bash", {"command": cmd}, cwd or self.root, **who)

    # sanidade: a forma literal é bloqueada
    def test_00_controle_literal_bloqueia(self):
        self.assertEqual(self.bash("cat %s" % self.H, **SUB)[0], 2)
        self.assertEqual(self.bash("rm -rf %s" % self.ws)[0], 2)

    # (c) leitura do held-out por construtor via brace expansion do shell
    def test_brace_le_heldout(self):
        cmd = "cat %s/oraculo/heldou{t,x}/casos/C-01.json" % self.ws
        self.assertEqual(self.bash(cmd, **SUB)[0], 2, "brace expansion lê o held-out sem bloqueio")

    # (b) escrita em protegido via brace expansion
    def test_brace_escreve_ledger(self):
        cmd = "echo forjado | tee -a %s/.{construcao,nada}/ledger.jsonl" % self.ws
        self.assertEqual(self.bash(cmd)[0], 2, "brace expansion escreve no ledger sem bloqueio")

    # (d) apagar o workspace via brace expansion (agente principal)
    def test_brace_rm_workspace(self):
        cmd = "rm -rf %s/{ws1,nada}" % os.path.dirname(self.ws)
        self.assertEqual(self.bash(cmd)[0], 2, "brace expansion apaga o ws sem bloqueio")

    # $HOME (variável de ambiente trivial) em vez de ~
    def test_var_home_rm_workspace(self):
        self.assertEqual(self.bash('rm -rf "$HOME/obras/ws1"')[0], 2, "$HOME/... apaga o ws sem bloqueio")

    def test_var_home_le_heldout(self):
        self.assertEqual(self.bash('cat "$HOME/obras/ws1/oraculo/heldout/casos/C-01.json"', **SUB)[0], 2,
                         "$HOME/... lê o held-out sem bloqueio")

    # cd cumulativo dentro de `sh -c` (o hook só acumula cd no nível de cima)
    def test_sh_c_cd_encadeado(self):
        cmd = "sh -c 'cd oraculo; cd heldout; cat casos/C-01.json'"
        self.assertEqual(self.bash(cmd, cwd=self.ws, **SUB)[0], 2, "sh -c com cd encadeado lê o held-out")

    # rsync --delete esvazia o workspace (inclui ledger/aprovacoes/oráculo)
    def test_rsync_delete_esvazia_ws(self):
        vazio = os.path.join(self.root, "vazio")
        os.makedirs(vazio)
        self.assertEqual(self.bash("rsync -a --delete %s/ %s/" % (vazio, self.ws))[0], 2,
                         "rsync --delete sobre o ws não é tratado como destrutivo")

    # tar extraindo dentro de .construcao (sobrescreve ledger)
    def test_tar_extrai_em_protegido(self):
        self.assertEqual(self.bash("tar -xf /tmp/forjado.tar -C %s/.construcao" % self.ws)[0], 2,
                         "tar -x -C <ws>/.construcao não é escrita em protegido")

    # git clean num repositório que contém o ws (git é 'leitor')
    def test_git_clean_apaga_ws(self):
        obras = os.path.dirname(self.ws)
        subprocess.run(["git", "init", "-q", obras], check=True)
        self.assertEqual(self.bash("git -C %s clean -fdx" % obras)[0], 2, "git clean -fdx apaga o ws sem bloqueio")


    # hardlink: realpath não resolve hardlink; criar o alias e depois escrever nele passa nos dois passos
    def test_hardlink_para_ledger(self):
        led = os.path.join(self.ws, ".construcao", "ledger.jsonl")
        alias = os.path.join(self.alvo, "notas.txt")
        r1 = self.bash("ln %s %s" % (led, alias), **SUB)[0]
        os.link(led, alias)  # o que o comando faria
        r2 = self.bash("echo forjado >> %s" % alias, **SUB)[0]
        self.assertIn(2, (r1, r2), "ln (exit %d) + escrita no alias (exit %d): ledger alterado por construtor" % (r1, r2))


if __name__ == "__main__":
    unittest.main()
