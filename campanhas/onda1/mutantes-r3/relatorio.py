import json, glob, os, sys
M3, OUT = sys.argv[1], sys.argv[2]
sys.path.insert(0, OUT)
import mutantes_def as D
exp = json.load(open(os.path.join(OUT, "explicacoes.json")))
res = {}
for f in glob.glob(os.path.join(M3, "res", "*.final.json")):
    d = json.load(open(f))
    res[d["id"]] = d
ms = []
for x in D.MUTANTES:
    r = res[x["id"]]
    e = exp.get(x["id"])
    viva = not r["morto"]
    ms.append(dict(id=x["id"], parte=x["parte"], arquivo=x["arquivo"], tipo=x["tipo"], descricao=x["descricao"],
                   antes=x["old"], depois=x["new"], morto=r["morto"], morto_por=r["morto_por"],
                   equivalente=bool(viva and e and e[0] == "equivalente"),
                   classe_sobrevivente=e[0] if (e and viva) else None,
                   explicacao=e[1] if (e and viva) else None, segundos=r["segundos"]))
RCT = ("retorno_constante", "normalizacao_caixa_desligada", "hash_disco_trocado_por_payload")
A = [m for m in ms if m["parte"] == "A"]
B = [m for m in ms if m["parte"] == "B"]
eqA = [m["id"] for m in A if m["equivalente"]]
mortosA = sum(m["morto"] for m in A)
naoeq = [m for m in A if not m["equivalente"]]
rc = [m for m in A if m["tipo"] in RCT]
por_arq, por_tipo = {}, {}
for m in A:
    for dic, k in ((por_arq, m["arquivo"]), (por_tipo, m["tipo"])):
        p = dic.setdefault(k, {"total": 0, "mortos": 0})
        p["total"] += 1
        p["mortos"] += m["morto"]
rel = {"parteA": {"total": len(A), "mortos": mortosA, "taxa": round(mortosA / len(A), 4),
                  "taxa_sem_equivalentes": round(mortosA / len(naoeq), 4),
                  "retorno_constante": {"total": len(rc), "mortos": sum(m["morto"] for m in rc),
                                        "sobreviventes": [m["id"] for m in rc if not m["morto"]]},
                  "equivalentes": eqA, "por_arquivo": por_arq, "por_tipo": por_tipo,
                  "sobreviventes": [m["id"] for m in A if not m["morto"]],
                  "criterio": {"taxa_ge_80": mortosA / len(naoeq) >= 0.8,
                               "todos_retorno_constante_mortos": all(m["morto"] for m in rc),
                               "atendido": mortosA / len(naoeq) >= 0.8 and all(m["morto"] for m in rc)}},
       "parteB": {"total": len(B), "mortos": sum(m["morto"] for m in B),
                  "detalhes": [{k: m[k] for k in ("id", "arquivo", "tipo", "descricao", "antes", "depois", "morto",
                                                  "morto_por", "classe_sobrevivente", "explicacao")} for m in B]},
       "metodo": {"oraculo": "tests/onda1 (180 testes) + heldout (64 testes), snapshot congelado no início (oraculo_snapshot.sha256)",
                  "base_sem_mutante": "5/5 execuções verdes (244 testes, 0 falhas, 0 pulados) + 1 run_heldout.py --com-visiveis verde",
                  "execucao": "HOME temporário por worker (6) com cópia da skill + link para auto-correcao; um mutante por vez por worker; scripts restaurados e conferidos por sha256 antes e depois; PYTHONDONTWRITEBYTECODE=1; runner.py com failfast (heldout, depois visíveis); sobrevivente = 244 testes verdes sem pulados"},
       "mutantes": ms}
json.dump(rel, open(os.path.join(OUT, "relatorio.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in rel["parteA"].items() if k != "por_tipo"}, ensure_ascii=False))
print("B", rel["parteB"]["total"], rel["parteB"]["mortos"])
print(json.dumps(por_tipo, ensure_ascii=False))
