import concurrent.futures as cf, hashlib, json, os, shutil, subprocess, sys, time
M3 = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1]; sys.path.insert(0, OUT)
import mutantes_def as D
only = set(sys.argv[3].split(",")) if len(sys.argv) > 3 and sys.argv[3] else None
NW = int(sys.argv[2])
PRIS = os.path.join(M3, "pristine_home")
SC_REL = ".claude/skills/construcao-orquestrada/scripts"
ARQS = ["co.py", "co_estado.py", "co_hook.py", "co_portao.py"]
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
PSHA = {a: sha(os.path.join(PRIS, SC_REL, a)) for a in ARQS}
res_dir = os.path.join(M3, "res"); os.makedirs(res_dir, exist_ok=True)
import queue
homes = queue.Queue()
for k in range(NW):
    h = os.path.join(M3, "w%d" % k)
    if os.path.exists(h): shutil.rmtree(h)
    os.makedirs(os.path.join(h, ".claude", "skills"))
    shutil.copytree(os.path.join(PRIS, ".claude/skills/construcao-orquestrada"), os.path.join(h, ".claude/skills/construcao-orquestrada"), symlinks=True)
    os.symlink(os.path.expanduser("~/.claude/skills/auto-correcao"), os.path.join(h, ".claude/skills/auto-correcao"))
    homes.put(h)
def restore(h):
    for a in ARQS:
        shutil.copy2(os.path.join(PRIS, SC_REL, a), os.path.join(h, SC_REL, a))
        assert sha(os.path.join(h, SC_REL, a)) == PSHA[a]
    pc = os.path.join(h, SC_REL, "__pycache__")
    if os.path.exists(pc): shutil.rmtree(pc)
def run(x):
    h = homes.get()
    try:
        restore(h)
        f = os.path.join(h, SC_REL, x["arquivo"])
        src = open(f, encoding="utf-8").read()
        assert src.count(x["old"]) == x["n"]
        open(f, "w", encoding="utf-8").write(src.replace(x["old"], x["new"]))
        rj = os.path.join(res_dir, x["id"] + ".json")
        env = dict(os.environ, HOME=h, PYTHONDONTWRITEBYTECODE="1")
        t0 = time.time(); to = False
        try:
            p = subprocess.run([sys.executable, os.path.join(M3, "runner.py"), os.path.join(M3, "heldout"), rj, "--failfast"],
                               env=env, cwd=M3, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=1200)
            log = p.stdout.decode("utf-8", "replace")[-3000:]
        except subprocess.TimeoutExpired:
            to = True; log = "TIMEOUT"
        try: r = json.load(open(rj))
        except Exception: r = {"morto": True, "erro_runner": True}
        if to: r = {"morto": True, "timeout": True}
        fal = []
        for b in ("heldout", "visiveis"):
            if b in r: fal += r[b]["falharam"]
        out = dict({k: v for k, v in x.items() if k not in ("old", "new")}, morto=bool(r.get("morto")),
                   morto_por=fal[:3] or (["timeout"] if to else (["erro_runner"] if r.get("erro_runner") else [])),
                   blocos={b: {kk: r[b][kk] for kk in ("rodados", "falhas", "erros", "pulados", "s")} for b in ("heldout", "visiveis") if b in r},
                   segundos=round(time.time() - t0, 1))
        if r.get("erro_runner"): out["log"] = log
        json.dump(out, open(os.path.join(res_dir, x["id"] + ".final.json"), "w"), indent=1, ensure_ascii=False)
        print("%-8s %s %s" % (x["id"], "MORTO" if out["morto"] else "VIVO ", out["morto_por"][:1]), flush=True)
        return out
    finally:
        restore(h)
        homes.put(h)
todo = [x for x in D.MUTANTES if (only is None or x["id"] in only) and not os.path.exists(os.path.join(res_dir, x["id"] + ".final.json"))]
print("a rodar:", len(todo), flush=True)
with cf.ThreadPoolExecutor(NW) as ex:
    list(ex.map(run, todo))
print("FIM", flush=True)
