"""Runner de mutantes do M2 (r2). Uso: rodar_mutantes.py SANDBOX_ROOT N_WORKERS [ids...]
SANDBOX_ROOT/pristine = cópia limpa da skill; cada worker usa SANDBOX_ROOT/wK/home (HOME temporário) com
.claude/skills/construcao-orquestrada (cópia restaurada a cada mutante) + link para auto-correcao.
Mutante MORTO se o held-out ou a suíte visível (tests/onda1) falhar. Resultados em SANDBOX_ROOT/resultados.jsonl."""
import concurrent.futures as cf
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from mutantes_spec import MUTANTES  # noqa: E402

REAL_SKILLS = os.path.expanduser("~/.claude/skills")
HELDOUT = os.environ.get("M2_HELDOUT") or os.path.join(AQUI, "..", "oraculo", "heldout", "run_heldout.py")
ARQS = ["co.py", "co_estado.py", "co_hook.py", "co_portao.py"]
FAIL_RE = re.compile(r"^(FAIL|ERROR): (\S+) \(([^)]+)\)", re.M)


def aplicar(src, pares):
    for old, new in pares:
        n = src.count(old)
        if n != 1:
            raise ValueError("âncora ocorre %d vezes: %r" % (n, old[:80]))
        src = src.replace(old, new)
    return src


def linha(src, pares):
    return src[:src.index(pares[0][0])].count("\n") + 1


def preparar_worker(root, k):
    home = os.path.join(root, "w%d" % k, "home")
    sk = os.path.join(home, ".claude", "skills")
    if not os.path.isdir(os.path.join(sk, "construcao-orquestrada")):
        os.makedirs(sk, exist_ok=True)
        shutil.copytree(os.path.join(root, "pristine"), os.path.join(sk, "construcao-orquestrada"))
        os.symlink(os.path.join(REAL_SKILLS, "auto-correcao"), os.path.join(sk, "auto-correcao"))
    return home


def restaurar(root, home):
    for a in ARQS:
        shutil.copyfile(os.path.join(root, "pristine", "scripts", a),
                        os.path.join(home, ".claude", "skills", "construcao-orquestrada", "scripts", a))
    pc = os.path.join(home, ".claude", "skills", "construcao-orquestrada", "scripts", "__pycache__")
    shutil.rmtree(pc, ignore_errors=True)


def rodar(cmd, home, timeout=900):
    env = dict(os.environ, HOME=home, PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTHONPYCACHEPREFIX", None)
    try:
        p = subprocess.run(cmd, env=env, cwd=home, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           universal_newlines=True, timeout=timeout)
        return p.returncode, p.stdout
    except subprocess.TimeoutExpired as e:
        return "timeout", (e.stdout or "") if isinstance(e.stdout, str) else ""


def avaliar(root, home, mid, arquivo, pares):
    restaurar(root, home)
    if pares:
        path = os.path.join(home, ".claude", "skills", "construcao-orquestrada", "scripts", arquivo)
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(aplicar(src, pares))
    t0 = time.time()
    res = {"id": mid}
    falhas = set()
    rc, out = rodar([sys.executable, HELDOUT], home)
    if rc == "timeout":
        falhas.add(("heldout", "timeout", ""))
    falhas |= {("heldout", a + " " + b, c) for a, b, c in FAIL_RE.findall(out)}
    vis = os.path.join(home, ".claude", "skills", "construcao-orquestrada", "tests", "onda1")
    rc2, out2 = rodar([sys.executable, "-m", "unittest", "discover", "-s", vis, "-p", "test_*.py"], home)
    if rc2 == "timeout":
        falhas.add(("visivel", "timeout", ""))
    falhas |= {("visivel", a + " " + b, c) for a, b, c in FAIL_RE.findall(out2)}
    res["falhas_todas"] = sorted("%s: %s (%s)" % f for f in falhas)
    base = set()
    bp = os.path.join(root, "baseline_falhas.json")
    if os.path.isfile(bp):
        with open(bp) as fh:
            base = set(json.load(fh))
    novas = [f for f in res["falhas_todas"] if f not in base]
    res.update(morto=bool(novas), morto_por="; ".join(novas[:3]) if novas else None)
    res["dur_s"] = round(time.time() - t0, 1)
    restaurar(root, home)
    return res


def main():
    root, nw = sys.argv[1], int(sys.argv[2])
    ids = set(sys.argv[3:])
    alvo = [m for m in MUTANTES if not ids or m[0] in ids or ("BASE" in ids and False)]
    # validação: toda âncora única e o mutante compila
    for mid, arq, _t, _d, pares in MUTANTES:
        with open(os.path.join(root, "pristine", "scripts", arq), encoding="utf-8") as fh:
            src = fh.read()
        compile(aplicar(src, pares), arq, "exec")
    homes = queue.Queue()
    for k in range(nw):
        homes.put(preparar_worker(root, k))
    saida = os.path.join(root, "resultados.jsonl")

    def job(m):
        home = homes.get()
        try:
            mid, arq, tipo, desc, pares = m
            r = avaliar(root, home, mid, arq, pares)
            with open(os.path.join(root, "pristine", "scripts", arq), encoding="utf-8") as fh:
                src = fh.read()
            r.update(arquivo=arq, tipo=tipo, descricao=desc, linha=linha(src, pares) if pares else None)
            return r
        finally:
            homes.put(home)

    if "BASE" in ids:
        alvo = [("BASE%d" % k, "co.py", "baseline", "sem mutante", []) for k in range(nw)]
    with cf.ThreadPoolExecutor(nw) as ex:
        for r in ex.map(job, alvo):
            print(json.dumps(r, ensure_ascii=False), flush=True)
            with open(saida, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
