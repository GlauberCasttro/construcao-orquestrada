#!/usr/bin/env python3
"""frente.py — registro mecânico das frentes (= campanhas auto-correcao) em state/WORKFLOW.md.

O estado fica num bloco JSON entre <!-- frentes:begin --> e <!-- frentes:end -->; a tabela legível entre
<!-- tabela:begin --> e <!-- tabela:end --> é regenerada. Regra: UMA frente ativa por vez, salvo frentes
declaradas --paralela (o declarante afirma que os escopos não colidem; confira com `ac.py overlap`).

  frente.py status [--json]
  frente.py check                       valida o bloco (exit 1 se violar)
  frente.py render                      regenera a tabela e CAMPANHA_ATIVA a partir do bloco JSON
  frente.py open <nome> --campanha DIR [--objetivo TXT] [--paralela] [--dry-run]
  frente.py pause <nome> [--dry-run]    ativa -> pausada
  frente.py resume <nome> [--dry-run]   pausada -> ativa (respeita a regra de uma ativa)
  frente.py close <nome> --commit HASH [--dry-run]   ativa/pausada -> entregas (com data)
Mantém state/CAMPANHA_ATIVA (usado pelo carimbo) = campanha da primeira frente ativa, ou 'nenhuma'.
Datas vêm do relógio do sistema; nunca digitadas.
"""
import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
STATE = os.environ.get("HARNESS_STATE") or os.path.join(HERE, "..", "state")
WF = os.path.join(STATE, "WORKFLOW.md")
CA = os.path.join(STATE, "CAMPANHA_ATIVA")
B, E = "<!-- frentes:begin -->", "<!-- frentes:end -->"
TB, TE = "<!-- tabela:begin -->", "<!-- tabela:end -->"
NOME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def agora():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def carregar():
    t = open(WF, encoding="utf-8").read()
    if B not in t or E not in t:
        sys.exit("WORKFLOW.md sem o bloco <!-- frentes:begin/end -->")
    corpo = t.split(B, 1)[1].split(E, 1)[0]
    m = re.search(r"```json\s*(.*?)```", corpo, re.S)
    if not m:
        sys.exit("bloco de frentes sem ```json")
    try:
        d = json.loads(m.group(1))
    except ValueError as e:
        sys.exit("JSON de frentes inválido: %s" % e)
    for k in ("ativas", "pausadas", "entregas"):
        d.setdefault(k, [])
    return t, d


def tabela(d):
    L = ["| estado | frente | campanha | desde / entrega | objetivo |", "|---|---|---|---|---|"]
    for k, rot in (("ativas", "ativa"), ("pausadas", "pausada")):
        for f in d[k]:
            L.append("| %s%s | %s | %s | %s | %s |" % (rot, " (paralela)" if f.get("paralela") else "", f["nome"],
                     f.get("campanha", "-"), f.get("desde", "-"), f.get("objetivo", "")))
    for f in d["entregas"][-8:]:
        L.append("| entregue | %s | %s | %s · commit %s | %s |" % (f["nome"], f.get("campanha", "-"),
                 f.get("em", "-"), f.get("commit", "-"), f.get("objetivo", "")))
    if len(L) == 2:
        L.append("| - | (nenhuma frente registrada) | | | |")
    return "\n".join(L)


def gravar(t, d):
    bloco = B + "\n```json\n" + json.dumps(d, ensure_ascii=False, indent=1) + "\n```\n" + E
    t = re.sub(re.escape(B) + r".*?" + re.escape(E), lambda m: bloco, t, flags=re.S)
    if TB in t and TE in t:
        t = re.sub(re.escape(TB) + r".*?" + re.escape(TE), lambda m: TB + "\n" + tabela(d) + "\n" + TE, t, flags=re.S)
    open(WF, "w", encoding="utf-8").write(t)
    ativa = d["ativas"][0].get("campanha", "nenhuma") if d["ativas"] else "nenhuma"
    open(CA, "w", encoding="utf-8").write(ativa + "\n")


def validar(d):
    erros = []
    nomes = [f.get("nome") for k in ("ativas", "pausadas") for f in d[k]]
    for n in nomes:
        if not isinstance(n, str) or not NOME.match(n):
            erros.append("nome inválido: %r" % (n,))
    if len(nomes) != len(set(nomes)):
        erros.append("nome de frente duplicado entre ativas/pausadas")
    if len(d["ativas"]) > 1 and not all(f.get("paralela") for f in d["ativas"]):
        erros.append("mais de uma frente ativa sem todas declaradas paralela")
    for f in d["ativas"]:
        c = f.get("campanha")
        if not c:
            erros.append("frente ativa '%s' sem campanha" % f.get("nome"))
        elif not os.path.isdir(os.path.expanduser(c)):
            erros.append("campanha da frente '%s' não existe: %s" % (f.get("nome"), c))
    return erros


def achar(d, nome, de):
    for f in d[de]:
        if f["nome"] == nome:
            return f
    sys.exit("frente '%s' não está em %s" % (nome, de))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("status"); s.add_argument("--json", action="store_true")
    sp.add_parser("check")
    sp.add_parser("render")
    o = sp.add_parser("open"); o.add_argument("nome"); o.add_argument("--campanha", required=True)
    o.add_argument("--objetivo", default=""); o.add_argument("--paralela", action="store_true")
    for c in ("pause", "resume"):
        sp.add_parser(c).add_argument("nome")
    c = sp.add_parser("close"); c.add_argument("nome"); c.add_argument("--commit", required=True)
    for p in (o, c) + tuple(sp.choices[x] for x in ("pause", "resume")):
        p.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    t, d = carregar()
    if a.cmd == "status":
        if a.json:
            print(json.dumps(d, ensure_ascii=False))
        else:
            print(tabela(d))
        return 0
    if a.cmd == "check":
        erros = validar(d)
        for e in erros:
            print("VIOLAÇÃO: " + e)
        print("frentes: ok" if not erros else "frentes: %d violação(ões)" % len(erros))
        return 1 if erros else 0
    if a.cmd == "render":
        gravar(t, d); print(tabela(d)); return 0
    if a.cmd == "open":
        if not NOME.match(a.nome):
            sys.exit("nome de frente inválido")
        if any(f["nome"] == a.nome for k in ("ativas", "pausadas") for f in d[k]):
            sys.exit("já existe frente com esse nome")
        if not os.path.isdir(os.path.expanduser(a.campanha)):
            sys.exit("campanha não existe (rode ac.py init antes): " + a.campanha)
        if d["ativas"] and not (a.paralela and all(f.get("paralela") for f in d["ativas"])):
            sys.exit("já há frente ativa (%s). Uma por vez: pause/feche, ou declare TODAS --paralela "
                     "(escopos sem colisão, conferidos com ac.py overlap)." % d["ativas"][0]["nome"])
        d["ativas"].append({"nome": a.nome, "campanha": a.campanha, "objetivo": a.objetivo,
                            "desde": agora(), **({"paralela": True} if a.paralela else {})})
    elif a.cmd == "pause":
        f = achar(d, a.nome, "ativas"); d["ativas"].remove(f); d["pausadas"].append(f)
    elif a.cmd == "resume":
        f = achar(d, a.nome, "pausadas")
        if d["ativas"] and not (f.get("paralela") and all(x.get("paralela") for x in d["ativas"])):
            sys.exit("já há frente ativa; pause-a antes")
        d["pausadas"].remove(f); d["ativas"].append(f)
    elif a.cmd == "close":
        de = "ativas" if any(f["nome"] == a.nome for f in d["ativas"]) else "pausadas"
        f = achar(d, a.nome, de); d[de].remove(f)
        f = dict(f, commit=a.commit, em=agora()); d["entregas"].append(f)
    if a.dry_run:
        print("[dry-run] resultado:\n" + tabela(d)); return 0
    gravar(t, d)
    print(tabela(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
