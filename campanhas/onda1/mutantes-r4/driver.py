#!/usr/bin/env python3
"""Driver M4. Uso: driver.py validar | driver.py rodar NWORKERS [ids,separados] | driver.py lista
Fase 1 (rápida): heldout + tests/onda1 (sem gerado), failfast. Fase 2 (só sobreviventes da 1): tests/onda1/gerado."""
import ast, concurrent.futures as cf, hashlib, json, os, queue, shutil, subprocess, sys, time

M4 = os.path.dirname(os.path.abspath(__file__))
R3 = os.path.join(os.path.dirname(M4), "mutantes-r3")
sys.path.insert(0, M4)
import mutantes_def as D  # noqa: E402

PRIS = os.path.join(M4, "pristine_home")
SC_REL = ".claude/skills/construcao-orquestrada/scripts"
ARQS = ["co.py", "co_estado.py", "co_hook.py", "co_portao.py"]
RES = os.path.join(M4, "res")
os.makedirs(RES, exist_ok=True)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


PSHA = {a: sha(os.path.join(PRIS, SC_REL, a)) for a in ARQS}
PSRC = {a: open(os.path.join(PRIS, SC_REL, a), encoding="utf-8").read() for a in ARQS}


def parte_b():
    r3 = json.load(open(os.path.join(R3, "relatorio.json")))
    vivos = [x for x in r3["mutantes"] if not x.get("morto")]
    import importlib.util
    spec = importlib.util.spec_from_file_location("mutantes_def_r3", os.path.join(R3, "mutantes_def.py"))
    d3 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(d3)
    defs = {x["id"]: x for x in d3.MUTANTES}
    out = []
    for v in vivos:
        x = defs[v["id"]]
        if v["id"] in D.B_ADAPT:
            a = D.B_ADAPT[v["id"]]
            out.append(dict(id="B4-" + v["id"], parte="B", r3=v["id"], arquivo=a["arquivo"], tipo=a["tipo"],
                            descricao=a["descricao"], subs=a["subs"], adaptado=True,
                            r3_classe=v.get("classe_sobrevivente")))
        else:
            out.append(dict(id="B4-" + v["id"], parte="B", r3=v["id"], arquivo=x["arquivo"], tipo=x["tipo"],
                            descricao=x["descricao"], subs=[(x["old"], x["new"], x.get("n", 1))], adaptado=False,
                            r3_classe=v.get("classe_sobrevivente")))
    return out


TODOS = D.MUTANTES + parte_b()


def _acha(tree, qual):
    nos = [tree]
    for parte in qual.split("."):
        achado = None
        for n in nos:
            for f in ast.walk(n) if n is tree else n.body:
                if isinstance(f, (ast.FunctionDef, ast.ClassDef)) and f.name == parte and (
                        n is not tree or f in tree.body or isinstance(f, ast.FunctionDef)):
                    achado = f
                    break
            if achado:
                break
        if achado is None:
            raise KeyError(qual)
        nos = [achado]
    return nos[0]


def aplicar(x, src):
    if "rc" in x:
        qual, expr = x["rc"]
        tree = ast.parse(src)
        # resolve qualname só por nós de topo / filhos diretos
        alvo = None
        partes = qual.split(".")
        corpo = tree.body
        for i, p in enumerate(partes):
            alvo = next((n for n in corpo if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == p), None)
            if alvo is None:
                raise KeyError(qual)
            corpo = alvo.body
        body = alvo.body
        st = body[0]
        if isinstance(st, ast.Expr) and isinstance(getattr(st, "value", None), ast.Constant) and \
                isinstance(st.value.value, str) and len(body) > 1:
            st = body[1]
        linhas = src.splitlines(True)
        ind = " " * st.col_offset
        linhas.insert(st.lineno - 1, "%sreturn %s\n" % (ind, expr))
        return "".join(linhas)
    for old, new, n in x["subs"]:
        c = src.count(old)
        if c != n:
            raise ValueError("%s: old aparece %d vezes (esperado %d): %r" % (x["id"], c, n, old[:80]))
        src = src.replace(old, new)
    return src


def validar():
    ruins = 0
    ids = set()
    for x in TODOS:
        if x["id"] in ids:
            print("ID DUPLICADO", x["id"]); ruins += 1
        ids.add(x["id"])
        try:
            novo = aplicar(x, PSRC[x["arquivo"]])
            compile(novo, x["arquivo"], "exec")
            if novo == PSRC[x["arquivo"]]:
                raise ValueError("mutante idêntico")
        except Exception as e:  # noqa: BLE001
            ruins += 1
            print("RUIM", x["id"], type(e).__name__, str(e)[:200])
    pa = [x for x in TODOS if x["parte"] == "A"]
    print("total=%d A=%d B=%d ruins=%d" % (len(TODOS), len(pa), len(TODOS) - len(pa), ruins))
    from collections import Counter
    print(Counter(x["arquivo"] for x in pa), Counter(x["tipo"] for x in pa))
    return ruins


def novo_home(k):
    h = os.path.join(M4, "w%d" % k)
    if os.path.exists(h):
        shutil.rmtree(h)
    os.makedirs(os.path.join(h, ".claude", "skills"))
    shutil.copytree(os.path.join(PRIS, ".claude/skills/construcao-orquestrada"),
                    os.path.join(h, ".claude/skills/construcao-orquestrada"), symlinks=True)
    os.symlink(os.path.expanduser("~/.claude/skills/auto-correcao"), os.path.join(h, ".claude/skills/auto-correcao"))
    return h


def restore(h):
    for a in ARQS:
        shutil.copy2(os.path.join(PRIS, SC_REL, a), os.path.join(h, SC_REL, a))
        assert sha(os.path.join(h, SC_REL, a)) == PSHA[a]
    pc = os.path.join(h, SC_REL, "__pycache__")
    if os.path.exists(pc):
        shutil.rmtree(pc)
    # o .claude/construcao-orquestrada (audit) do HOME do worker não deve vazar entre mutantes
    au = os.path.join(h, ".claude", "construcao-orquestrada")
    if os.path.exists(au):
        shutil.rmtree(au)


def roda_fase(h, x, modo, timeout):
    rj = os.path.join(RES, "%s.%s.json" % (x["id"], modo.strip("-")))
    env = dict(os.environ, HOME=h, PYTHONDONTWRITEBYTECODE="1")
    to = False
    try:
        p = subprocess.run([sys.executable, os.path.join(M4, "runner.py"), os.path.join(M4, "heldout"), rj,
                            "--failfast", modo], env=env, cwd=M4, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=timeout)
        log = p.stdout.decode("utf-8", "replace")[-3000:]
    except subprocess.TimeoutExpired:
        to, log = True, "TIMEOUT"
    try:
        r = json.load(open(rj))
    except Exception:  # noqa: BLE001
        r = {"morto": True, "erro_runner": True}
    if to:
        r = {"morto": True, "timeout": True}
    r["_log"] = log if r.get("erro_runner") else ""
    return r


def run(x, homes):
    h = homes.get()
    try:
        restore(h)
        f = os.path.join(h, SC_REL, x["arquivo"])
        open(f, "w", encoding="utf-8").write(aplicar(x, PSRC[x["arquivo"]]))
        t0 = time.time()
        r1 = roda_fase(h, x, "--rapido", 1500)
        fases = {"rapido": r1}
        morto = bool(r1.get("morto"))
        if not morto:
            restore(h)
            open(f, "w", encoding="utf-8").write(aplicar(x, PSRC[x["arquivo"]]))
            r2 = roda_fase(h, x, "--gerado", 2400)
            fases["gerado"] = r2
            morto = bool(r2.get("morto"))
        fal, blocos = [], {}
        for fn, r in fases.items():
            for b in ("heldout", "visiveis", "gerado"):
                if b in r:
                    fal += r[b]["falharam"]
                    blocos[b] = {kk: r[b][kk] for kk in ("rodados", "falhas", "erros", "pulados", "s")}
            if r.get("timeout"):
                fal.append("timeout(%s)" % fn)
            if r.get("erro_runner"):
                fal.append("erro_runner(%s)" % fn)
        morto_em = None
        if morto:
            for b in ("heldout", "visiveis", "gerado"):
                if b in blocos and (blocos[b]["falhas"] or blocos[b]["erros"] or blocos[b]["pulados"]):
                    morto_em = b
                    break
            morto_em = morto_em or ("timeout" if any("timeout" in f for f in fal) else "erro_runner")
        out = {k: v for k, v in x.items() if k not in ("subs",)}
        out.update(morto=morto, morto_em=morto_em, morto_por=fal[:3], blocos=blocos,
                   segundos=round(time.time() - t0, 1))
        if "subs" in x:
            out["antes"] = [s[0] for s in x["subs"]]
            out["depois"] = [s[1] for s in x["subs"]]
        logs = [r.get("_log") for r in fases.values() if r.get("_log")]
        if logs:
            out["log"] = logs[-1]
        json.dump(out, open(os.path.join(RES, x["id"] + ".final.json"), "w"), indent=1, ensure_ascii=False)
        print("%-10s %s %s %s" % (x["id"], "MORTO" if morto else "VIVO ", morto_em or "", (fal[:1] or [""])[0][:90]),
              flush=True)
        return out
    finally:
        restore(h)
        homes.put(h)


def rodar(nw, only=None):
    homes = queue.Queue()
    for k in range(nw):
        homes.put(novo_home(k))
    todo = [x for x in TODOS if (only is None or x["id"] in only)
            and not os.path.exists(os.path.join(RES, x["id"] + ".final.json"))]
    print("a rodar:", len(todo), flush=True)
    with cf.ThreadPoolExecutor(nw) as ex:
        list(ex.map(lambda x: run(x, homes), todo))
    print("FIM", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "validar":
        sys.exit(1 if validar() else 0)
    if sys.argv[1] == "rodar":
        only = set(sys.argv[3].split(",")) if len(sys.argv) > 3 and sys.argv[3] else None
        rodar(int(sys.argv[2]), only)
