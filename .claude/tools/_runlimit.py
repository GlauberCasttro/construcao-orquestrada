#!/usr/bin/env python3
"""_runlimit.py <segundos> -- <comando...>  executa com limite de tempo (macOS não tem `timeout`).
Exit 124 se estourou o limite; senão o exit do comando. 0 segundos = sem limite."""
import subprocess
import sys

if len(sys.argv) < 4 or sys.argv[2] != "--":
    print(__doc__); sys.exit(0 if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help") else 2)
lim = int(sys.argv[1])
try:
    p = subprocess.run(sys.argv[3:], timeout=lim or None)
    sys.exit(p.returncode)
except subprocess.TimeoutExpired:
    print("TIMEOUT após %ss: %s" % (lim, " ".join(sys.argv[3:]))); sys.exit(124)
