#!/usr/bin/env python3
"""Consolida res/*.final.json + explicacoes.json em relatorio.json."""
import glob, json, os, sys
from collections import Counter, defaultdict

M4 = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, M4)
import driver  # noqa: E402

exp = {}
pe = os.path.join(M4, "explicacoes.json")
if os.path.exists(pe):
    exp = json.load(open(pe))
res = {}
for f in glob.glob(os.path.join(M4, "res", "*.final.json")):
    d = json.load(open(f))
    res[d["id"]] = d
faltam = [x["id"] for x in driver.TODOS if x["id"] not in res]
muts = []
for x in driver.TODOS:
    d = dict(res.get(x["id"], {"id": x["id"], "pendente": True}))
    if x["id"] in exp:
        d.update({k: v for k, v in exp[x["id"]].items()})
    muts.append(d)
A = [d for d in muts if d.get("parte") == "A" and not d.get("pendente")]
B = [d for d in muts if d.get("parte") == "B" and not d.get("pendente")]
eq = sorted(d["id"] for d in A if not d["morto"] and d.get("equivalente"))
mA = sum(1 for d in A if d["morto"])
rcA = [d for d in A if d["tipo"] == "retorno_constante"]
por_arq, por_tipo, morto_em = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0]), Counter()
for d in A:
    por_arq[d["arquivo"]][0] += 1
    por_arq[d["arquivo"]][1] += int(d["morto"])
    por_tipo[d["tipo"]][0] += 1
    por_tipo[d["tipo"]][1] += int(d["morto"])
    morto_em[d.get("morto_em") or "vivo"] += 1
mB = sum(1 for d in B if d["morto"])
rel = {
    "parteA": {"total": len(A), "mortos": mA, "taxa": round(mA / len(A), 4) if A else None,
               "taxa_sem_equivalentes": round(mA / (len(A) - len(eq)), 4) if A else None,
               "retorno_constante": {"total": len(rcA), "mortos": sum(1 for d in rcA if d["morto"]),
                                     "sobreviventes": [d["id"] for d in rcA if not d["morto"]]},
               "equivalentes": eq,
               "sobreviventes": [d["id"] for d in A if not d["morto"]],
               "morto_em": dict(morto_em),
               "por_arquivo": {k: {"total": v[0], "mortos": v[1]} for k, v in sorted(por_arq.items())},
               "por_tipo": {k: {"total": v[0], "mortos": v[1]} for k, v in sorted(por_tipo.items())},
               "criterio": {"taxa_min": 0.80, "rc_todos_mortos": True,
                            "atende": bool(A) and mA / len(A) >= 0.80 and all(d["morto"] for d in rcA)}},
    "parteB": {"total": len(B), "mortos": mB, "taxa": round(mB / len(B), 4) if B else None,
               "adaptados": sorted(d["r3"] for d in B if d.get("adaptado")),
               "detalhes": [{k: d.get(k) for k in ("id", "r3", "arquivo", "tipo", "descricao", "adaptado", "r3_classe",
                                                   "morto", "morto_em", "morto_por", "classe_sobrevivente",
                                                   "explicacao", "equivalente")} for d in B]},
    "metodo": json.load(open(os.path.join(M4, "metodo.json"))) if os.path.exists(os.path.join(M4, "metodo.json")) else {},
    "pendentes": faltam,
    "mutantes": muts,
}
json.dump(rel, open(os.path.join(M4, "relatorio.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in rel["parteA"].items() if k not in ("sobreviventes",)}, ensure_ascii=False))
print("parteB", rel["parteB"]["total"], rel["parteB"]["mortos"], "pendentes", len(faltam))
print("vivos A:", rel["parteA"]["sobreviventes"])
print("vivos B:", [d["id"] for d in B if not d["morto"]])
