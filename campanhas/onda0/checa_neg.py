import importlib.util, os, sys, re, itertools, copy
_AQUI = os.path.dirname(os.path.abspath(__file__))
_PROJ = os.environ.get("CO_SKILL_DIR") or os.path.join(_AQUI, "..", "..")  # raiz do projeto (campanhas/onda0 -> ../..)
_ACS = [os.environ.get("CO_AC_PY", ""), os.path.expanduser("~/.claude/skills/auto-correcao/scripts/ac.py"),
        os.path.join(_PROJ, ".claude", "tools", "ac", "scripts", "ac.py")]  # motor embutido como último recurso
spec = importlib.util.spec_from_file_location("ac", next(p for p in _ACS if p and os.path.isfile(p)))
ac = importlib.util.module_from_spec(spec); spec.loader.exec_module(ac)
R = os.environ.get("CHECA_NEG_DIR", "")  # cópias NEGATIVAS das references (fixture local, fora do projeto)
if not R:
    print("PULADO: defina CHECA_NEG_DIR=<dir com cópias negativas de references/*.json5>"); sys.exit(0)
R = os.path.join(R, "")
docs = {}
for f in ["contrato.json5", "maquina.json5", "portoes.json5", "invariantes.json5", "ondas.json5"]:
    docs[f] = ac.json5_load(R + f); print("JSON5 ok:", f)
M = docs["maquina.json5"]; K = M["constantes"]; CONT = M["contadores"]
errs = []
KW = {"and", "or", "not", "true", "false", "True", "False"}

def atoms(g): return set(re.findall(r"[A-Za-z_]\w*", g)) - KW
def ev(g, env):
    g2 = re.sub(r"\btrue\b", "True", re.sub(r"\bfalse\b", "False", g))
    return eval(g2, {"__builtins__": {}}, env)

def nodes_graph(L, drop=()):
    T = L["transitions"]; init = (L["initial"], None, None)
    def succ(n):
        s, p, r = n
        for name, t in T.items():
            if s not in t["from"] or s in drop: continue
            req = t.get("requer", {})
            if "portao" in req and req["portao"] != p: continue
            to = t["to"]
            if to == "@retorno":
                if not r: errs.append("@retorno sem retorno em %s via %s" % (n, name)); continue
                to = r
            if to in drop: continue
            st = t.get("set", {})
            np = st.get("portao", p); nr = st.get("retorno", r)
            if nr == "@from": nr = s
            if to not in L.get("transversais", {}): np, nr = None, None
            elif to == "PAUSADO" and "portao" not in st: np = None
            yield name, t, (to, np, nr)
    seen = {init}; q = [init]; E = []
    while q:
        n = q.pop()
        for name, t, m in succ(n):
            E.append((n, name, t, m))
            if m not in seen: seen.add(m); q.append(m)
    return seen, E

def check_level(nome, L):
    S = set(L["states"]); T = L["transitions"]; term = set(L["terminal"]); targets = term | set(L.get("estaveis", []))
    # S1/S3
    for n, t in T.items():
        for x in t["from"] + [t["to"]]:
            if x != "@retorno" and x not in S: errs.append("%s: %s estado desconhecido %s" % (nome, n, x))
        if set(t["from"]) & term: errs.append("%s: %s sai de terminal" % (nome, n))
        for c in [t.get("incrementa")] + t.get("zera", []):
            if c and c not in CONT: errs.append("%s: contador %s" % (nome, c))
        if t["actor"] not in M["atores"]: errs.append("actor %s" % n)
    seen, E = nodes_graph(L)
    reach = {n[0] for n in seen}
    # I1
    if S - reach: errs.append("%s I1 inalcançáveis: %s" % (nome, S - reach))
    # I2
    for s in S - term:
        if not any(s in t["from"] for t in T.values()): errs.append("%s I2 sem saída: %s" % (nome, s))
    rev = {}
    for a, _, _, b in E: rev.setdefault(b, set()).add(a)
    good = {n for n in seen if n[0] in targets}; q = list(good)
    while q:
        n = q.pop()
        for a in rev.get(n, ()):
            if a not in good: good.add(a); q.append(a)
    bad = [n for n in seen if n not in good and n[0] not in term]
    if bad: errs.append("%s I2 nós presos: %s" % (nome, bad))
    for st, d in L.get("transversais", {}).items():
        evs = {t["evento"] for t in T.values() if st in t["from"]}
        if set(d["saidas_minimas"]) - evs: errs.append("%s I2 %s falta %s" % (nome, st, set(d["saidas_minimas"]) - evs))
    # I3
    for v in L.get("verificacao_obrigatoria", []):
        s2, _ = nodes_graph(L, drop=(v,))
        if L["sucesso"] in {n[0] for n in s2}: errs.append("%s I3 %s alcançável sem %s" % (nome, L["sucesso"], v))
    # I4
    adj = {}
    for a, name, t, b in E:
        if t["actor"] == "humano" or t.get("incrementa"): continue
        adj.setdefault(a, []).append(b)
    color = {}
    def dfs(u, path):
        color[u] = 1
        for w in adj.get(u, []):
            if color.get(w) == 1: errs.append("%s I4 ciclo sem contador: %s" % (nome, [p[0] for p in path[path.index(w):]] if w in path else w))
            elif not color.get(w): dfs(w, path + [w])
        color[u] = 2
    for n in seen:
        if not color.get(n): dfs(n, [n])
    # I5
    groups = {}
    for n, t in T.items():
        for s in t["from"]:
            groups.setdefault((s, t["evento"], t.get("requer", {}).get("portao")), []).append((n, t["guard"]))
    for k, lst in groups.items():
        for (n1, g1), (n2, g2) in itertools.combinations(lst, 2):
            ats = sorted(atoms(g1) | atoms(g2)); doms = []
            for a in ats:
                if a in K: doms.append([K[a]])
                elif a in CONT: doms.append(list(range(0, ac_teto(a) + 2)))
                else: doms.append([False, True])
            for vals in itertools.product(*doms):
                env = dict(zip(ats, vals))
                if ev(g1, env) and ev(g2, env):
                    errs.append("%s I5 %s∧%s em %s: %s" % (nome, n1, n2, k, env)); break
    # I6
    for n, t in T.items():
        h = t["actor"] == "humano"; ah = "AGUARDANDO_HUMANO" in t["from"]; g = "aprovacao_humana" in atoms(t["guard"])
        if h and not (ah and g and t["from"] == ["AGUARDANDO_HUMANO"]): errs.append("%s I6 %s" % (nome, n))
        if (g or ah) and not h: errs.append("%s I6 não-humano %s" % (nome, n))
    # I7
    for n, t in T.items():
        if set(t["from"]) & set(L.get("estaveis", [])) and not t.get("motivo_obrigatorio"): errs.append("%s I7 %s" % (nome, n))
        if t["to"] == "ORACULO" and not (t["from"] == ["AGUARDANDO_HUMANO"] and t.get("requer", {}).get("portao") in ("stop", "oraculo", "oraculo_mudar")):
            errs.append("%s I7 entrada ORACULO %s" % (nome, n))
    print("%s: %d estados, %d transições, %d nós (estado,portao,retorno), %d arestas, %d grupos (estado,evento,portao)" % (nome, len(S), len(T), len(seen), len(E), len(groups)))

def ac_teto(c):
    t = CONT[c]["teto"]; return K[t] if isinstance(t, str) else t

for nome, L in M["niveis"].items():
    check_level(nome, L)

# ondas: writes disjuntos por onda + autor do oráculo != construtor
for o in docs["ondas.json5"]["ondas"]:
    fr = o["frentes"]
    ws = [(f["id"], g) for f in fr for g in f["writes"] + f.get("oraculo_writes", [])]
    for (i1, a), (i2, b) in itertools.combinations(ws, 2):
        if i1 != i2 and ac.globs_overlap(a, b): errs.append("onda %s: %s~%s (%s ~ %s)" % (o["id"], i1, i2, a, b))
    for f in fr:
        if f.get("oraculo_por") and f["oraculo_por"].split()[0] == f["construtor"] and f["construtor"] != "orquestrador":
            errs.append("onda %s %s: autor do oráculo constrói" % (o["id"], f["id"]))
        if not f.get("papel") and any(g.split("/")[1:2] == ["tests"] for g in f["writes"]):
            errs.append("onda %s %s: construtor escreve tests" % (o["id"], f["id"]))
    print("onda %s: %d frentes, %d globs, disjunção ok=%s" % (o["id"], len(fr), len(ws), not any(e.startswith("onda %s:" % o["id"]) for e in errs)))

# coerência contrato <-> portões <-> maquina
C = docs["contrato.json5"]; P = docs["portoes.json5"]
if sorted(P["itens"]) != sorted(C["portoes_regressao"]): errs.append("G ids divergem")
sw = sorted(k for k, v in P["itens"].items() if v["waiver"] is False)
if sw != sorted(C["sem_waiver"]): errs.append("sem_waiver diverge %s vs %s" % (sw, C["sem_waiver"]))
ph = {t.get("set", {}).get("portao") for t in M["niveis"]["obra"]["transitions"].values()} - {None}
if ph != set(C["portoes_humanos"]): errs.append("portões humanos divergem %s" % (ph ^ set(C["portoes_humanos"])))
print("ERROS:" if errs else "TUDO OK", *errs, sep="\n  ")
sys.exit(1 if errs else 0)
