#!/usr/bin/env python3
"""Lançador do motor de campanhas EMBUTIDO (auto-correcao): executa scripts/<este nome>, cópia verbatim
registrada em ORIGEM.txt. O verbatim fica em scripts/ porque o ac.py acha references/ por ../references a partir
do próprio arquivo. Uso: python3 .claude/tools/ac/<nome>.py --help (mesmos argumentos do original)."""
import os
import runpy
import sys

_ALVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", os.path.basename(__file__))

if __name__ == "__main__":
    sys.argv[0] = _ALVO
    runpy.run_path(_ALVO, run_name="__main__")
else:  # importado (importlib): expõe as funções do original
    globals().update({k: v for k, v in runpy.run_path(_ALVO, run_name="ac_embutido").items()
                      if not k.startswith("__")})
