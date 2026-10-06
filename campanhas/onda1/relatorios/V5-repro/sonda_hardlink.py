#!/usr/bin/env python3
"""V5 — hardlink criado com `link` (não listado) e escrito depois: o hook acha o inode protegido? Executa de verdade
num HOME temporário (o link e a escrita), consultando o hook antes de cada passo."""
import os, sys, subprocess, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sonda_hook as S
hl = os.path.join(S.root, "hl-ledger")
for cwd in (S.ws, S.root, "/tmp"):
    cmd1 = "link %s/.construcao/ledger.jsonl %s" % (S.ws, hl)
    rc1, _ = S.hook(cmd1, cwd=cwd)
    if rc1 == 0 and not os.path.exists(hl):
        subprocess.run(["bash", "-c", cmd1], check=True)
    cmd2 = "echo forjado >> %s" % hl
    rc2, err2 = S.hook(cmd2, cwd=cwd)
    print("cwd=%-60s link: %s | escrita via hardlink: %s %s" % (cwd, "PERMITE" if rc1 == 0 else "BLOQUEIA",
          "PERMITE" if rc2 == 0 else "BLOQUEIA", err2[:90]))
print("st_nlink do ledger:", os.stat(os.path.join(S.ws, ".construcao", "ledger.jsonl")).st_nlink)
import shutil; shutil.rmtree(S.root, ignore_errors=True)
