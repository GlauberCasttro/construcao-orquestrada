#!/usr/bin/env python3
"""gerar.py — gera MECANICAMENTE a tabela do oráculo da onda 1 a partir dos references (contrato, maquina, portoes,
invariantes, formatos .json5) e grava `tabela.json` + `COBERTURA.md` ao lado. Oráculo O1-gerado.

Categorias (uma linha = um caso; nome legível = item + caso):
  a  átomo de guarda      V e F por evidência real (arquivo/evento/audit/payload); átomo sem evidência na onda 1
                          (não computado pelo produto) ⇒ V/F por injeção de chamador confiável + omitido ⇒ recusa;
                          átomo do disco ⇒ injeção contrária não sobrepõe o disco
  b  transição            evento certo no estado certo grava; estado errado recusa sem gravar; ator errado ⇒ fold recusa
  c  contador com teto    abaixo/no teto (guarda); zera_em/zera
  d  campo do ledger      cada campo de formatos.arquivos.ledger × tipo de registro, adulterado (cadeia recalculada)
  e  hash conferido       arquivo alterado depois do evento ⇒ NO-GO/recusa (com controle)
  f  portão G0..G14       PASS e FAIL por efeito real (núcleo da onda 1), não-PASS por vácuo (fora da onda 1),
                          relatório adulterado ⇒ NO-GO
  g  subcomando           entrada inválida ⇒ 2 sem traceback; erro interno ⇒ ≠ 0
  h  evento operacional   `ev <op>` que não seja nota/checkpoint ⇒ recusa
  i  entrega              só run completo, final, GO real, pass^3 e aprovações com audit; cada falta ⇒ não entrega

Uso: python3 gerar.py [--check]   (sai ≠ 0 se algum item do contrato ficar sem caso — falha do próprio gerador)
"""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)

import motor as m  # noqa: E402

FALHAS = []  # itens do contrato sem caso (o gerador sai ≠ 0)


def falta(msg):
    FALHAS.append(msg)


# ====================================================================== previsão (máquina + avaliador próprio)

def prever(nivel, no, evento, valores):
    """valores: nome -> bool/int (ausente = indeterminado). Retorna (tn, t, destino) ou None."""
    def val(n):
        if n in valores:
            return valores[n]
        return m.CONST.get(n)
    verd = [(tn, t, d) for tn, t, d in m.grupo(nivel, evento, no) if m.ev3(m.parse(t["guard"]), val) is True]
    return verd[0] if len(verd) == 1 else None


def no_de(nivel, spec):
    return m.no_obra(spec) if nivel == "obra" else (spec, None, None)


def spec_from(nivel, t, f):
    if nivel != "obra":
        return f
    if f == "AGUARDANDO_HUMANO":
        p = (t.get("requer") or {}).get("portao", "stop")
        return "AH:%s" % p + ("@LOTE" if p in ("oraculo_mudar", "continuar") else "")
    if f == "PAUSADO":
        return "PAUSADO@LOTE"
    return f


def simular_rota(nivel, spec, cont):
    try:
        passos = m.rota(nivel, spec, cont)
        st = m.simular(passos)
    except KeyError as e:
        return None, str(e)
    for c, v in (cont or {}).items():
        if m.contadores_no(st, nivel).get(c) != v:
            return None, "contador %s=%s pedido, rota dá %s" % (c, v, m.contadores_no(st, nivel).get(c))
    return st, None


def humano(grp):
    return any(t["actor"] == "humano" for _tn, t, _d in grp)


def montar_caso(nivel, spec, cont, evento, assign, modo_forcado=None, injetar_tambem=None, omitir=(),
                contra_injecao=None):
    """Transforma uma atribuição de átomos em (modo, evid, injeta, esperado). assign: átomo -> bool."""
    st, err = simular_rota(nivel, spec, cont)
    if st is None:
        raise ValueError(err)
    no = m.no_atual(st, nivel)
    grp = m.grupo(nivel, evento, no)
    hum = humano(grp)
    evid, inj = {}, dict(injetar_tambem or {})
    retomar_modo = False
    if evento == "task.perdida" and assign.get("perdida_na_retomada") is True and \
            assign.get("resultado_no_worktree") is False and modo_forcado in (None, "retomar"):
        retomar_modo = True
    for a, v in assign.items():
        if a in omitir:
            continue
        if a == "aprovacao_humana":
            continue
        if retomar_modo and a in ("perdida_na_retomada", "resultado_no_worktree"):
            continue
        if a in m.EVID and m.EVID[a]["fase"] not in ("canal", "retomar") and (a not in inj):
            evid[a] = v
            for k2, v2 in m.DEFINIDO_INJETA.get(a, {}).items():
                inj.setdefault(k2, v2)
        else:
            inj.setdefault(a, v)
    for a, v in (contra_injecao or {}).items():
        inj[a] = v
    if hum:
        modo = "aprovar"
    elif retomar_modo:
        modo = "retomar"
    elif modo_forcado:
        modo = modo_forcado
    else:
        modo = "api" if inj else "ev"
    valores = dict(m.contadores_no(st, nivel))
    valores.update({a: v for a, v in m.efetivos(assign).items() if a not in omitir})
    if hum:
        valores["aprovacao_humana"] = True
    for a, v in inj.items():
        valores[a] = v
    # evidência vence injeção contrária (ESPEC: computados do disco continuam valendo)
    for a, v in m.efetivos(evid).items():
        valores[a] = v
    for x in m.TRAVA_DEP:
        if evid.get("trava_adquirida") is False:
            valores.pop(x, None)
    r = prever(nivel, no, evento, valores)
    esp = {"grava": r is not None}
    if r is not None:
        tn, t, d = r
        st2 = json.loads(json.dumps(st))
        st2["obra"] = tuple(st2["obra"])
        m.aplicar(st2, nivel, evento, no[0], d[0], t["actor"], m.TASK_ID if nivel == "task" else m.CAMP_ID,
                  {}, portao=d[1])
        esp.update(transicao=tn, ator=t["actor"], de=no[0], no_depois=list(m.no_atual(st2, nivel)),
                   contadores_depois=m.contadores_no(st2, nivel))
    payload = m.payload_base(nivel, evento, (r[1] if r else (grp[0][1] if grp else {})))
    for a in ("motivo_registrado", "evidencia_registrada", "limite_detectado"):
        if a in evid:
            v = evid[a]
            if a == "motivo_registrado":
                payload.pop("motivo", None)
                if v:
                    payload["motivo"] = "motivo registrado"
            elif a == "evidencia_registrada":
                payload.pop("evidencia", None)
                if v:
                    payload["evidencia"] = "evidência registrada"
            else:
                payload.update(causa="outro" if v else "nao-sei", retomar_apos=m.PASSADO, mensagem="parede")
    if evento == "limite_uso" and "limite_detectado" not in evid:
        payload.update(causa="outro", retomar_apos=m.PASSADO, mensagem="parede")
    return {"nivel": nivel, "no": spec, "cont": cont or {}, "evento": evento, "modo": modo, "evid": evid,
            "injeta": inj, "payload": payload, "esperado": esp, "contadores_antes": m.contadores_no(st, nivel),
            "no_antes": list(no)}


def vars_grupo(grp):
    s = set()
    for _tn, t, _d in grp:
        s |= set(m.atomos_de(t["guard"]))
    return s


def ok_evid(assign, nivel, no, vc=None):
    for a, v in assign.items():
        if a not in m.EVID:
            return False  # átomo sem evidência montável: nenhuma injeção é aceita como substituto
        if m.EVID[a]["fase"] not in ("canal", "retomar", "definido") and not m.viavel(a, v, nivel, no, vc):
            return False
    return m.spec_relatorio(assign) is not None


def variantes_cont(t, nivel, spec):
    out = [{}]
    for c, _op, K in m.comparacoes(t["guard"]):
        out.append({c: m.CONST[K]})
        out.append({c: 1})
    if spec in ("AH:continuar@LOTE",):
        out = [{}]
    return out


# ====================================================================== (b) transições + (c) contadores

def linhas_transicoes(L):
    for nivel in m.NIVEIS:
        for tn, t in m.transicoes(nivel).items():
            for f in t["from"]:
                spec = spec_from(nivel, t, f)
                item = "%s.%s [%s]" % (nivel, tn, spec)
                feito = False
                for cont in variantes_cont(t, nivel, spec):
                    st, err = simular_rota(nivel, spec, cont)
                    if st is None:
                        continue
                    no = m.no_atual(st, nivel)
                    grp = m.grupo(nivel, t["evento"], no)
                    if tn not in [g[0] for g in grp]:
                        continue
                    hum = humano(grp)
                    vs = vars_grupo(grp) - {"aprovacao_humana"}
                    valores_c = m.contadores_no(st, nivel)
                    vc_ev = valores_c

                    def pred(a):
                        if not ok_evid(a, nivel, no, vc_ev):
                            return False
                        vv = dict(valores_c, **m.efetivos(a))
                        if hum:
                            vv["aprovacao_humana"] = True
                        r = prever(nivel, no, t["evento"], vv)
                        return r is not None and r[0] == tn
                    a = m.escolher(vs, pred)
                    if a is None:
                        continue
                    caso = montar_caso(nivel, spec, cont, t["evento"], a)
                    if not caso["esperado"]["grava"] or caso["esperado"]["transicao"] != tn:
                        continue
                    L.append(dict(caso, cat="b", tipo="certo", item=item,
                                  caso="evento certo no estado certo grava%s" % (
                                      " (%s)" % ",".join("%s=%s" % kv for kv in sorted(cont.items())) if cont else ""),
                                  portao=no[1], decisao=("abandonar" if t["evento"] == "abandonar" else t["evento"])))
                    feito = True
                    break
                if not feito and nivel == "task" and tn == "colher":
                    # ESPEC interp. 8: `colhida` (worktree) fica fora da onda 1; perdida_na_retomada só pela retomada,
                    # que na onda 1 não colhe. Caso real: fora da retomada o evento é recusado (falha fechada).
                    L.append({"cat": "b", "tipo": "fora_onda1", "item": item, "nivel": nivel, "no": spec, "cont": {},
                              "caso": "fora da onda 1 (colhida é onda 2): `ev task.colher` fora da retomada recusa",
                              "evento": t["evento"], "modo": "ev", "evid": {}, "injeta": {},
                              "payload": m.payload_base(nivel, t["evento"], t), "esperado": {"grava": False}})
                    feito = True
                if not feito:
                    falta("b: %s sem caso 'certo' (nenhuma rota/atribuição o dispara)" % item)
                # estado errado
                cands = m.NOS_OBRA if nivel == "obra" else (m.MAQ["niveis"][nivel]["states"])
                errado = None
                k = sum(map(ord, tn)) % len(cands)
                for w in cands[k:] + cands[:k]:
                    if nivel == "obra" and humano([(tn, t, None)]) and w.startswith("AH:"):
                        continue
                    wno = no_de(nivel, w)
                    if w == spec or m.grupo(nivel, t["evento"], wno):
                        continue
                    if simular_rota(nivel, w, {})[0] is None:
                        continue
                    errado = w
                    break
                if errado is None:
                    falta("b: %s sem estado errado montável" % item)
                else:
                    hum = t["actor"] == "humano"
                    L.append({"cat": "b", "tipo": "estado_errado", "item": item,
                              "caso": "evento no estado errado %s recusa sem gravar" % errado, "nivel": nivel,
                              "no": errado, "cont": {}, "evento": t["evento"], "modo": "aprovar" if hum else "ev",
                              "portao": (t.get("requer") or {}).get("portao", "stop"),
                              "decisao": "abandonar" if t["evento"] == "abandonar" else t["evento"],
                              "evid": {}, "injeta": {}, "payload": m.payload_base(nivel, t["evento"], t),
                              "esperado": {"grava": False}})
                # ator errado (fold)
                st, err = simular_rota(nivel, spec, {})
                if st is None:
                    falta("b: %s sem rota para o ator errado: %s" % (item, err))
                    continue
                no = m.no_atual(st, nivel)
                d = m.destino(nivel, t, no)
                ruim = None
                for a in m.ATORES:
                    if a == t["actor"]:
                        continue
                    if any(t2["evento"] == t["evento"] and m.aplicavel(t2, no) and t2["actor"] == a and
                           m.destino(nivel, t2, no) is not None and m.destino(nivel, t2, no)[0] == d[0]
                           for t2 in m.transicoes(nivel).values()):
                        continue
                    ruim = a
                    break
                if ruim is None or d is None:
                    falta("b: %s sem ator errado possível" % item)
                else:
                    L.append({"cat": "b", "tipo": "ator_errado", "item": item,
                              "caso": "registro com ator %s (≠ %s) ⇒ fold recusa" % (ruim, t["actor"]),
                              "nivel": nivel, "no": spec, "cont": {}, "evento": t["evento"], "modo": "forja",
                              "forja": {"evento": t["evento"], "de": no[0], "para": d[0], "ator": ruim,
                                        "nivel": nivel, "task": None if nivel == "obra" else
                                        (m.TASK_ID if nivel == "task" else m.CAMP_ID)},
                              "evid": {}, "injeta": {}, "payload": {}, "esperado": {"grava": False}})


def linhas_contadores(L):
    feitos = set()
    for nivel in m.NIVEIS:
        for tn, t in m.transicoes(nivel).items():
            for c, op, K in m.comparacoes(t["guard"]):
                teto = m.CONST[K]
                f = t["from"][0]
                spec = spec_from(nivel, t, f)
                passa_em = teto - 1 if op in ("<", "<=") else teto
                for v in (teto - 1, teto):
                    item = "%s %s %s (%s.%s)" % (c, op, K, nivel, tn)
                    st, err = simular_rota(nivel, spec, {c: v} if v else {})
                    if st is None:
                        falta("c: %s v=%d sem rota: %s" % (item, v, err))
                        continue
                    no = m.no_atual(st, nivel)
                    grp = m.grupo(nivel, t["evento"], no)
                    hum = humano(grp)
                    vs = vars_grupo(grp) - {"aprovacao_humana"}
                    vc_ev = m.contadores_no(st, nivel)
                    # atribuição em que T dispara quando o contador está do lado que passa
                    st_p, _ = simular_rota(nivel, spec, {c: passa_em} if passa_em else {})
                    vc_p = m.contadores_no(st_p, nivel)

                    outro = teto if passa_em != teto else teto - 1
                    st_o, _ = simular_rota(nivel, spec, {c: outro} if outro else {})
                    vc_o = m.contadores_no(st_o, nivel)

                    def pred(a):
                        if not ok_evid(a, nivel, no, vc_ev):
                            return False
                        res = []
                        for vc_x in (vc_p, vc_o):
                            vv = dict(vc_x, **m.efetivos(a))
                            if hum:
                                vv["aprovacao_humana"] = True
                            r = prever(nivel, no, t["evento"], vv)
                            res.append(r is not None and r[0] == tn)
                        return res == [True, False]
                    a = m.escolher(vs, pred)
                    if a is None:
                        falta("c: %s sem atribuição que dispare %s" % (item, tn))
                        continue
                    caso = montar_caso(nivel, spec, {c: v} if v else {}, t["evento"], a)
                    dispara = caso["esperado"]["grava"] and caso["esperado"]["transicao"] == tn
                    deve = (v == passa_em)
                    if dispara != deve:
                        falta("c: %s v=%d previsão incoerente" % (item, v))
                    rot = "no teto (%s=%d)" % (c, v) if v == teto else "abaixo do teto (%s=%d)" % (c, v)
                    L.append(dict(caso, cat="c", tipo="teto", item=item, alvo_tn=tn,
                                  caso="%s ⇒ %s" % (rot, "%s grava" % tn if deve else "%s recusa%s" % (
                                      tn, " (vai %s)" % caso["esperado"]["transicao"] if caso["esperado"]["grava"] else "")),
                                  portao=no[1], decisao=t["evento"]))
                    feitos.add((c, tn))
            # zera / zera_em
            for c in m.zera(tn, t):
                item = "zera %s em %s.%s" % (c, nivel, tn)
                spec = spec_from(nivel, t, t["from"][0])
                ok = False
                for cont in ({c: 1}, {c: 2, "tentativas": 3} if c != "tentativas" else {c: 3}, {}):
                    st, err = simular_rota(nivel, spec, cont)
                    if st is None or m.contadores_no(st, nivel).get(c, 0) < 1:
                        continue
                    no = m.no_atual(st, nivel)
                    grp = m.grupo(nivel, t["evento"], no)
                    hum = humano(grp)
                    vc = m.contadores_no(st, nivel)
                    vc_ev = vc

                    def pred(a):
                        if not ok_evid(a, nivel, no, vc_ev):
                            return False
                        vv = dict(vc, **m.efetivos(a))
                        if hum:
                            vv["aprovacao_humana"] = True
                        r = prever(nivel, no, t["evento"], vv)
                        return r is not None and r[0] == tn
                    a = m.escolher(vars_grupo(grp) - {"aprovacao_humana"}, pred)
                    if a is None:
                        continue
                    caso = montar_caso(nivel, spec, cont, t["evento"], a)
                    if caso["esperado"].get("contadores_depois", {}).get(c) != 0:
                        continue
                    L.append(dict(caso, cat="c", tipo="zera", item=item, alvo_tn=tn,
                                  caso="%s=%d antes ⇒ 0 depois de %s" % (c, vc[c], tn), portao=no[1],
                                  decisao=t["evento"]))
                    ok = True
                    break
                if not ok:
                    falta("c: %s sem caso" % item)
    for c in m.CONTADORES:
        if not any(k[0] == c for k in feitos):
            falta("c: contador %s sem caso de teto" % c)


# ====================================================================== (a) átomos

def cenarios_do_atomo(A):
    out = []
    for hum_ok in (False, True):
        for nivel in m.NIVEIS:
            for tn, t in m.transicoes(nivel).items():
                if A not in m.atomos_de(t["guard"]):
                    continue
                if (t["actor"] == "humano") != hum_ok:
                    continue
                for f in t["from"]:
                    out.append((nivel, tn, t, spec_from(nivel, t, f)))
    return out


def linhas_atomos(L):
    todos = set()
    for nivel in m.NIVEIS:
        for t in m.transicoes(nivel).values():
            todos |= set(m.atomos_de(t["guard"]))
    for A in sorted(todos):
        if A == "aprovacao_humana":
            L.append({"cat": "a", "tipo": "canal", "item": "átomo %s" % A, "caso": "V: `aprovar stop` no pty grava",
                      "atomo": A, "valor": True, "nivel": "obra", "no": "AH:stop", "cont": {}, "evento": "aprovado",
                      "modo": "aprovar", "portao": "stop", "decisao": "aprovado", "evid": {}, "injeta": {},
                      "payload": {}, "esperado": {"grava": True, "transicao": "stop_aprovado", "ator": "humano",
                                                  "de": "AGUARDANDO_HUMANO", "no_depois": ["ORACULO", None, None],
                                                  "contadores_depois": m.contadores_no(m.simular(m.rota_obra("ORACULO")), "obra")}})
            L.append({"cat": "a", "tipo": "canal", "item": "átomo %s" % A,
                      "caso": "F: sem canal humano (ev e API com átomo forjado) recusa", "atomo": A, "valor": False,
                      "nivel": "obra", "no": "AH:stop", "cont": {}, "evento": "aprovado", "modo": "sem_canal",
                      "evid": {}, "injeta": {"aprovacao_humana": True}, "payload": {}, "esperado": {"grava": False}})
            continue
        if A == "perdida_na_retomada":
            L.append({"cat": "a", "tipo": "retomar", "item": "átomo %s" % A,
                      "caso": "V: `retomar` com T-01 EM_VOO e vaga aberta grava task.perdida", "atomo": A,
                      "valor": True, "nivel": "task", "no": "EM_VOO", "cont": {}, "evento": "task.perdida",
                      "modo": "retomar", "evid": {}, "injeta": {}, "payload": {},
                      "esperado": {"grava": True, "transicao": "perdida", "ator": "script", "de": "EM_VOO",
                                   "no_depois": ["PRONTA", None, None]}})
            L.append({"cat": "a", "tipo": "retomar", "item": "átomo %s" % A,
                      "caso": "F: `ev task.perdida` fora da retomada recusa", "atomo": A, "valor": False,
                      "nivel": "task", "no": "EM_VOO", "cont": {}, "evento": "task.perdida", "modo": "ev",
                      "evid": {}, "injeta": {}, "payload": {"task": m.TASK_ID}, "esperado": {"grava": False}})
            continue
        if A in m.EVID and m.EVID[A]["fase"] == "valor":
            for x in (True, False):
                L.append({"cat": "a", "tipo": "valor", "item": "átomo %s" % A, "atomo": A, "valor": x,
                          "caso": "%s por evidência (valor_atomo, sem injeção): %s" % (
                              "V" if x else "F", m.EVID[A]["como"].split(";")[0 if x else 1].strip()),
                          "nivel": "task", "no": "EM_VOO", "cont": {}, "evento": "task.perdida", "modo": "valor",
                          "evid": {A: x}, "injeta": {}, "payload": {"task": m.TASK_ID},
                          "esperado": {"grava": None, "valor": x}})
            continue
        if A not in m.EVID:
            falta("a: átomo %s sem evidência montável (injeção não é caso)" % A)
            continue
        com_evid = True
        achou = None
        for nivel, tn, t, spec in cenarios_do_atomo(A):
            for cont in variantes_cont(t, nivel, spec):
                st, err = simular_rota(nivel, spec, cont)
                if st is None:
                    continue
                no = m.no_atual(st, nivel)
                grp = m.grupo(nivel, t["evento"], no)
                if tn not in [g[0] for g in grp]:
                    continue
                hum = humano(grp)
                if com_evid and not (m.viavel(A, True, nivel, no) and m.viavel(A, False, nivel, no)) and \
                        m.EVID[A]["fase"] != "definido":
                    continue
                vs = vars_grupo(grp) - {"aprovacao_humana", A}
                vc = m.contadores_no(st, nivel)
                vc_ev = vc

                def out(a, x):
                    aa = dict(a)
                    aa[A] = x
                    vv = dict(vc, **m.efetivos(aa))
                    if hum:
                        vv["aprovacao_humana"] = True
                    r = prever(nivel, no, t["evento"], vv)
                    return r[0] if r else None

                def pred(a):
                    for x in (True, False):
                        aa = dict(a)
                        aa[A] = x
                        if not ok_evid(aa, nivel, no, vc_ev):
                            return False
                    return out(a, True) != out(a, False)
                a = m.escolher(vs, pred)
                if a is not None:
                    achou = (nivel, tn, t, spec, cont, a, out)
                    break
            if achou:
                break
        if not achou:
            falta("a: átomo %s sem cenário sensível" % A)
            continue
        nivel, tn, t, spec, cont, a, out = achou
        item = "átomo %s" % A
        onde = "%s.%s [%s]" % (nivel, tn, spec)
        if com_evid:
            for x in (True, False):
                aa = dict(a)
                aa[A] = x
                caso = montar_caso(nivel, spec, cont, t["evento"], aa)
                L.append(dict(caso, cat="a", tipo="evidencia", item=item, atomo=A, valor=x, cenario=onde,
                              caso="%s por evidência em %s ⇒ %s" % ("V" if x else "F", onde,
                                                                    caso["esperado"].get("transicao") or "recusa"),
                              portao=caso["no_antes"][1], decisao=t["evento"]))
            if A in m.DISCO:
                x = False if out(a, False) is None else (True if out(a, True) is None else False)
                aa = dict(a)
                aa[A] = x
                caso = montar_caso(nivel, spec, cont, t["evento"], aa, modo_forcado="api",
                                   contra_injecao={A: (not x)})
                caso["modo"] = "api"
                L.append(dict(caso, cat="a", tipo="disco_vence", item=item, atomo=A, valor=x, cenario=onde,
                              caso="disco %s + injeção %s em %s ⇒ o disco vence (%s)" % (
                                  "V" if x else "F", "V" if not x else "F", onde,
                                  caso["esperado"].get("transicao") or "recusa"),
                              portao=caso["no_antes"][1], decisao=t["evento"]))
        else:
            for x in (True, False):
                aa = dict(a)
                aa[A] = x
                caso = montar_caso(nivel, spec, cont, t["evento"], aa, modo_forcado="api")
                caso["modo"] = "api"
                L.append(dict(caso, cat="a", tipo="injecao", item=item, atomo=A, valor=x, cenario=onde,
                              caso="%s por injeção (sem evidência computável na onda 1) em %s ⇒ %s" % (
                                  "V" if x else "F", onde, caso["esperado"].get("transicao") or "recusa"),
                              portao=caso["no_antes"][1], decisao=t["evento"]))
            caso = montar_caso(nivel, spec, cont, t["evento"], dict(a, **{A: True}), modo_forcado="api",
                               omitir=(A,))
            caso["modo"] = "api"
            L.append(dict(caso, cat="a", tipo="omitido", item=item, atomo=A, valor=None, cenario=onde,
                          caso="omitido ⇒ indeterminado ⇒ %s em %s" % (
                              caso["esperado"].get("transicao") or "recusa (falha fechada)", onde),
                          portao=caso["no_antes"][1], decisao=t["evento"]))


# ====================================================================== (d) campos do ledger

TIPOS_REG = {
    "genese": "gênese (op)", "nota": "operacional nota", "despachada": "operacional despachada",
    "oraculo_congelado": "operacional oraculo_congelado", "iniciar": "transição obra",
    "aprovacao": "operacional aprovacao", "humano": "transição humana", "task.despachar": "transição task",
}


def adulteracoes(campo, tipo):
    """(rotulo, operação, detecção) ou None quando a regra de formatos não fixa incoerência para o par."""
    if campo == "seq":
        return ("seq com lacuna (+1)", {"op": "seq_mais1"}, "duro")
    if campo == "ts":
        return ("ts fora do formato ISO-8601 Z", {"op": "set", "valor": "2026-10-04 12:00:00"}, "duro")
    if campo == "ator":
        alvo = {"genese": "orquestrador", "nota": "orquestrador", "despachada": "humano",
                "oraculo_congelado": "orquestrador", "aprovacao": "humano", "iniciar": "orquestrador",
                "humano": "orquestrador", "task.despachar": "script"}[tipo]
        return ("ator %s" % alvo, {"op": "set", "valor": alvo}, "duro")
    if campo == "nivel":
        alvo = {"genese": "obra", "nota": "xpto", "despachada": "task", "oraculo_congelado": "obra",
                "aprovacao": "obra", "iniciar": "task", "humano": "task", "task.despachar": "obra"}[tipo]
        return ("nivel %s" % alvo, {"op": "set", "valor": alvo}, "duro")
    if campo == "evento":
        alvo = "task.inexistente_zz" if tipo == "task.despachar" else "evento_inexistente_zz"
        return ("evento %s" % alvo, {"op": "set", "valor": alvo}, "duro")
    if campo == "de":
        alvo = {"iniciar": "LOTE", "humano": "LOTE", "task.despachar": "RETORNADA"}.get(tipo, "LOTE")
        return ("de %s" % alvo, {"op": "set", "valor": alvo}, "duro")
    if campo == "para":
        alvo = {"iniciar": "ORACULO", "humano": "ENTREGUE", "task.despachar": "ACEITA"}.get(tipo, "LOTE")
        return ("para %s" % alvo, {"op": "set", "valor": alvo}, "duro")
    if campo == "task":
        if tipo == "task.despachar":
            return ("task null num evento de task", {"op": "set", "valor": None}, "duro")
        return None
    if campo == "chave":
        if tipo in ("task.despachar", "despachada"):
            return ("chave trocada (cadeia recalculada)", {"op": "set", "valor": "obra/9/T-01/9"}, "cache")
        return None
    if campo == "payload":
        return ("payload trocado com payload_hash velho", {"op": "payload_velho"}, "duro")
    if campo == "payload_hash":
        return ("payload_hash trocado", {"op": "set", "valor": "0" * 64}, "duro")
    if campo == "prev":
        if tipo == "genese":
            return ("prev da gênese ≠ '0'", {"op": "set", "valor": "1" * 64}, "duro")
        return ("prev quebrado", {"op": "set", "valor": "2" * 64}, "duro")
    if campo == "hash":
        return ("hash trocado", {"op": "set", "valor": "3" * 64}, "duro")
    return None


def linhas_ledger(L):
    campos = list(m.FMT["arquivos"]["ledger"]["campos"].keys())
    if campos != list(m.CON["ledger"]["campos"]):
        falta("d: formatos.ledger.campos ≠ contrato.ledger.campos")
    for campo in campos:
        n = 0
        for tipo in TIPOS_REG:
            ad = adulteracoes(campo, tipo)
            if ad is None:
                continue
            rot, op, det = ad
            L.append({"cat": "d", "item": "ledger.%s" % campo, "caso": "%s em %s ⇒ %s" % (
                rot, TIPOS_REG[tipo], "status/retomar/ev/veredito ≠ 0, nada gravado" if det == "duro"
                else "status avisa cache ≠ fold"), "campo": campo, "registro": tipo, "adulteracao": op,
                "deteccao": det})
            n += 1
        if n == 0:
            falta("d: campo %s sem adulteração" % campo)
    # payload recalculado (coerente) num registro que muda o estado ⇒ a testemunha cache acusa
    L.append({"cat": "d", "item": "ledger.payload", "caso": "payload de oraculo_congelado trocado com cadeia "
              "recalculada ⇒ status avisa cache ≠ fold", "campo": "payload", "registro": "oraculo_congelado",
              "adulteracao": {"op": "payload_recalc", "valor": {"n_testes": 99}}, "deteccao": "cache"})
    L.append({"cat": "d", "item": "ledger (controle)", "caso": "forja sem adulteração é aceita (controle)",
              "campo": None, "registro": "nota", "adulteracao": {"op": "nada"}, "deteccao": "nenhuma"})


# ====================================================================== (e) hashes conferidos

HASHES = [
    ("obra", "premissas_ok.obra_hash", "obra.json5 alterado depois de premissas_ok ⇒ G1 e G3 FAIL/ERRO; veredito NO-GO"),
    ("plano", "plano_ok.plano_hash", "PLANO.json5 alterado depois de plano_ok ⇒ G3 (diff) reprova"),
    ("regressao", "plano_ok.regressao_hash", "regressao.json5 alterado depois de plano_ok ⇒ veredito NO-GO"),
    ("gate_report", "portao_relatorio.gate_report_hash", "gate-report.json alterado depois do evento ⇒ veredito NO-GO e entrega recusada"),
    ("oraculo", "oraculo_congelado.hash", "arquivo do oráculo alterado depois do congelamento ⇒ G0 FAIL"),
    ("ac_py", "estado da campanha-mãe do ac.py (oracle.hash)", "oráculo alterado E recongelado só no ac.py ⇒ G0 FAIL (hash ≠ oraculo_congelado do ledger)"),
    ("manifest", "oraculo_congelado.manifest_hash", "MANIFEST.json5 alterado depois do congelamento ⇒ G0 FAIL"),
]
PEDIDOS_HASH = ["obra", "plano", "regressao", "gate_report", "oraculo", "ac_py", "manifest"]


def linhas_hashes(L):
    feitos = set()
    for chave, campo, desc in HASHES:
        L.append({"cat": "e", "item": "hash %s (%s)" % (chave, campo), "caso": "controle: intacto ⇒ PASS/GO",
                  "hash": chave, "adulterar": False})
        L.append({"cat": "e", "item": "hash %s (%s)" % (chave, campo), "caso": desc, "hash": chave,
                  "adulterar": True})
        feitos.add(chave)
    for k in PEDIDOS_HASH:
        if k not in feitos:
            falta("e: hash %s sem caso" % k)
    # sha256 dos payloads sem conferência na onda 1 (listados na COBERTURA, não são falha)
    return [(ev, c) for ev, d in m.FMT["payloads"].items() for c, t in (d.get("campos") or {}).items()
            if "sha256" in str(t)]


# ====================================================================== (f) portões

NUCLEO_ONDA1 = ["G0", "G1", "G3", "G4", "G7"]  # ondas.json5 frente C


def linhas_portoes(L):
    L.append({"cat": "f", "item": "veredito (sistema_hash)", "caso": "relatório obsoleto (alvo mudou depois do run) "
              "⇒ veredito NO-GO", "gid": "G0", "caso_id": "obsoleto"})
    for gid, it in m.POR["itens"].items():
        item = "portão %s (%s)" % (gid, it["nome"])
        if gid in NUCLEO_ONDA1:
            L.append({"cat": "f", "item": item, "caso": "PASS por efeito real", "gid": gid, "caso_id": "pass"})
            L.append({"cat": "f", "item": item, "caso": "FAIL por efeito real (%s)" % it["negativo"], "gid": gid,
                      "caso_id": "fail"})
        else:
            col = it["por_tipo"].get("cli")
            aplica = not (isinstance(col, str) and col.startswith("N/A"))
            L.append({"cat": "f", "item": item, "caso": "fora da onda 1: `portao run --only %s` (cli) ⇒ %s" % (
                gid, "nunca PASS por vácuo" if aplica else "NA com motivo"), "gid": gid,
                "caso_id": "vacuo" if aplica else "na"})
        if gid == "G2":
            L.append({"cat": "f", "item": item, "caso": "waiver de G2 com aprovação do portão G6 (outro item) ⇒ "
                      "veredito NO-GO", "gid": gid, "caso_id": "waiver_outro"})
        L.append({"cat": "f", "item": item, "caso": "relatório registrado adulterado (%s FAIL→PASS, veredito→GO) ⇒ "
                  "veredito NO-GO" % gid, "gid": gid, "caso_id": "adulterado"})


# ====================================================================== (g) subcomandos

INVALIDOS = {
    "init": [["init", "--alvo", "{alvo}", "--tipo", "nao-e-tipo", "--pedido", "p", "--stop", "s"]],
    "ev": [["ev", "evento_que_nao_existe_zz"], ["ev", "nota", "--payload", "{payload_ruim}"]],
    "status": [["status", "--formato-zz"]],
    "load": [["load"]],
    "maquina": [["maquina", "check", "--machine", "{payload_ruim}"], ["maquina", "acao_zz"]],
    "pontos": [["pontos", "acao_zz"]],
    "oraculo": [["oraculo", "mudar", "--motivo", "m"], ["oraculo", "acao_zz"]],
    "plano": [["plano", "acao_zz"]],
    "lote": [["lote", "acao_zz"]],
    "diff": [["diff", "T-99", "--base", "{base}", "--repo", "{alvo}"], ["diff"]],
    "colisao": [["colisao"]],
    "trava": [["trava", "integracao", "acao_zz"]],
    "medir": [["medir", "--config", "zz"]],
    "comparar": [["comparar", "--rodada", "nao-int"]],
    "portao": [["portao", "acao_zz"], ["portao", "run", "--only", "G99"]],
    "veredito": [["veredito", "--formato-zz"]],
    "aprovar": [["aprovar", "stop", "--decisao", "aprovado"], ["aprovar", "stop", "--decisao", "talvez"]],
    "hook": [["hook", "acao_zz"]],
    "retomar": [["retomar", "--flag-zz"]],
    "reabrir": [["reabrir", "T-01"]],
}
INTERNOS = {sub: "ledger_corrompido" for sub in INVALIDOS}
INTERNOS.update(init="work_e_arquivo", hook="stdin_tipo_errado", maquina="maquina_tipo_errado",
                aprovar="ledger_corrompido")


def linhas_subcomandos(L):
    for sub in m.CON["cli"]["subcomandos"]:
        if sub not in INVALIDOS:
            falta("g: subcomando %s sem entrada inválida" % sub)
            continue
        L.append({"cat": "g", "item": "co.py %s" % sub, "caso": "flag desconhecida ⇒ 2 sem traceback", "sub": sub,
                  "argv": [sub] + (["check"] if sub in ("maquina", "pontos") else []) + ["--flag-inexistente-zz"],
                  "esperado_exit": [2]})
        for argv in INVALIDOS[sub]:
            L.append({"cat": "g", "item": "co.py %s" % sub, "caso": "entrada inválida `%s` ⇒ 2 sem traceback" %
                      " ".join(argv), "sub": sub, "argv": argv, "esperado_exit": [2]})
        L.append({"cat": "g", "item": "co.py %s" % sub, "caso": "erro interno (%s) ⇒ ≠ 0 sem traceback" % INTERNOS[sub],
                  "sub": sub, "interno": INTERNOS[sub], "argv": None, "esperado_exit": "nao_zero"})
    L.append({"cat": "g", "item": "co.py (global)", "caso": "sem --work ⇒ 2", "sub": "status",
              "argv": ["status"], "sem_work": True, "esperado_exit": [2]})


# ====================================================================== (h) operacionais via ev

def linhas_operacionais(L):
    for op in m.CON["ledger"]["eventos_operacionais"]:
        if op in ("nota", "checkpoint_janela_50"):
            L.append({"cat": "h", "item": "ev %s" % op, "caso": "controle: aceito, estado e hash_estado inalterados",
                      "op": op, "aceito": True})
        else:
            L.append({"cat": "h", "item": "ev %s" % op, "caso": "operacional fora de nota/checkpoint ⇒ recusa sem gravar",
                      "op": op, "aceito": False})


# ====================================================================== (i) entrega

def linhas_entrega(L):
    L.append({"cat": "i", "item": "entrega", "caso": "controle: run completo, final, GO, pass^3, aprovações com audit ⇒ ENTREGUE",
              "falta": None, "grava": True})
    L.append({"cat": "i", "item": "entrega", "caso": "controle: GO (com waiver) em G2 com aprovação ⇒ ENTREGUE",
              "falta": "waiver_g2", "grava": True})
    faltas = [("parcial", "relatório parcial (only=[G0..G4])"), ("nao_final", "relatório final=false"),
              ("simulado", "GO (simulado) com medição simulada"), ("nogo", "veredito NO-GO"),
              ("item_fail", "item G9 FAIL com veredito GO gravado"), ("item_erro", "item G12 ERRO com veredito GO"),
              ("sem_pass3", "medição final com k=1"), ("pass3_simulado", "medição k=3 simulada"),
              ("sem_medicao", "medição final com k=0 (nenhuma execução)"), ("relatorio_alterado", "gate-report alterado após o evento"),
              ("sem_portao_relatorio", "gate-report sem evento portao_relatorio"),
              ("tool_call_aprovou", "aprovação feita por tool_call permitida no audit")]
    for g in m.CON["portoes_regressao"]:
        faltas.append(("sem_" + g, "relatório sem o item %s" % g))
    for g in ("G0", "G1", "G3", "G4"):
        faltas.append(("waiver_" + g, "núcleo %s WAIVED (com aprovação completa)" % g))
    # waiver de G2 só vale com aprovação de verdade (evento `aprovacao` + arquivo com decisão aprovado e seq + audit
    # fora do ws); cada peça faltando ⇒ não entrega
    faltas += [("waiver_g2_sem_seq", "waiver G2 com arquivo de aprovação sem seq"),
               ("waiver_g2_sem_audit", "waiver G2 sem linha tipo aprovacao no audit"),
               ("waiver_g2_rejeitado", "waiver G2 com aprovação de decisão rejeitado"),
               ("waiver_g2_arquivo_solto", "waiver G2 apontando arquivo solto sem evento nem audit"),
               ("waiver_outro_item", "waiver G2 com aprovação do portão G6 (outro item)"),
               ("obsoleto", "relatório obsoleto (alvo mudou depois do run)")]
    for p in ("stop", "oraculo"):
        faltas.append(("sem_audit_" + p, "aprovação %s sem linha tipo aprovacao no audit" % p))
    for k, desc in faltas:
        L.append({"cat": "i", "item": "entrega", "caso": "%s ⇒ não entrega (nada gravado)" % desc, "falta": k,
                  "grava": False})


# ====================================================================== montagem

def construir():
    del FALHAS[:]
    L = []
    linhas_atomos(L)
    linhas_transicoes(L)
    linhas_contadores(L)
    linhas_ledger(L)
    nao_conferidos = linhas_hashes(L)
    linhas_portoes(L)
    linhas_subcomandos(L)
    linhas_operacionais(L)
    linhas_entrega(L)
    vistos = {}
    for i, r in enumerate(L, 1):
        r["id"] = "%s-%04d" % (r["cat"].upper(), i)
        r["nome"] = "%s — %s" % (r["item"], r["caso"])
        vistos[r["nome"]] = vistos.get(r["nome"], 0) + 1
    for r in L:
        if vistos[r["nome"]] > 1:
            r["nome"] += " [%s]" % r["id"]
    return L, list(FALHAS), nao_conferidos


CATS = [("a", "átomos de guarda"), ("b", "transições"), ("c", "contadores com teto"), ("d", "campos do ledger"),
        ("e", "hashes conferidos"), ("f", "portões G0..G14"), ("g", "subcomandos"), ("h", "operacionais via ev"),
        ("i", "entrega")]


def cobertura_md(L, falhas, nao_conferidos):
    out = ["# COBERTURA — oráculo gerado da onda 1", "",
           "Gerado por `gerar.py` a partir de `references/*.json5` (não edite à mão). "
           "Rodar: `python3 -m unittest discover -s tests/onda1/gerado -t tests/onda1/gerado`.", ""]
    out += ["## Totais", "", "| categoria | itens | linhas |", "|---|---:|---:|"]
    for c, nome in CATS:
        rs = [r for r in L if r["cat"] == c]
        out.append("| %s — %s | %d | %d |" % (c, nome, len({r["item"] for r in rs}), len(rs)))
    out.append("| **total** | %d | %d |" % (len({r["item"] for r in L}), len(L)))
    out.append("")
    todos = set()
    for nivel in m.NIVEIS:
        for t in m.transicoes(nivel).values():
            todos |= set(m.atomos_de(t["guard"]))
    com = sorted(a for a in todos if a in m.EVID)
    sem = sorted(a for a in todos if a not in m.EVID)
    ntr = sum(len(t["from"]) for n in m.NIVEIS for t in m.transicoes(n).values())
    out += ["## Contagem do contrato", "",
            "- átomos distintos nas guardas: %d (com evidência na onda 1: %d; sem — só injeção: %d)" % (
                len(todos), len(com), len(sem)),
            "- transições: %d (pares transição × estado de origem: %d)" % (
                sum(len(m.transicoes(n)) for n in m.NIVEIS), ntr),
            "- contadores: %d; constantes: %d" % (len(m.CONTADORES), len(m.CONST)),
            "- campos do ledger: %d" % len(m.FMT["arquivos"]["ledger"]["campos"]),
            "- hashes conferidos: %d" % len(HASHES),
            "- portões: %d (núcleo da onda 1: %s)" % (len(m.POR["itens"]), ", ".join(NUCLEO_ONDA1)),
            "- subcomandos: %d" % len(m.CON["cli"]["subcomandos"]),
            "- eventos operacionais: %d" % len(m.CON["ledger"]["eventos_operacionais"]), "",
            "Átomos sem evidência computável na onda 1 (o produto os trata como indeterminados até as ondas 2–3; "
            "cobertos por injeção V/F + omitido ⇒ recusa): " + ", ".join(sem), "",
            "sha256 de payload SEM conferência na onda 1 (não listados como `conferidos`): " +
            ", ".join("%s.%s" % x for x in nao_conferidos if "%s.%s" % x not in
                      ("premissas_ok.obra_hash", "plano_ok.plano_hash", "plano_ok.regressao_hash",
                       "portao_relatorio.gate_report_hash", "oraculo_congelado.hash",
                       "oraculo_congelado.manifest_hash")), ""]
    out += ["## Item × caso", ""]
    for c, nome in CATS:
        out += ["### %s — %s" % (c, nome), "", "| id | item | caso |", "|---|---|---|"]
        for r in L:
            if r["cat"] == c:
                out.append("| %s | %s | %s |" % (r["id"], r["item"].replace("|", "/"), r["caso"].replace("|", "/")))
        out.append("")
    out += ["## Itens sem caso (falha do gerador)", ""]
    out += ["- " + f for f in falhas] if falhas else ["nenhum"]
    return "\n".join(out) + "\n"


def main(argv=None):
    L, falhas, nc = construir()
    with open(os.path.join(AQUI, "tabela.json"), "w", encoding="utf-8") as fh:
        json.dump(L, fh, ensure_ascii=False, indent=1, sort_keys=True)
    with open(os.path.join(AQUI, "COBERTURA.md"), "w", encoding="utf-8") as fh:
        fh.write(cobertura_md(L, falhas, nc))
    for c, nome in CATS:
        print("%s %-22s %4d linhas" % (c, nome, sum(1 for r in L if r["cat"] == c)))
    print("total %d linhas" % len(L))
    if falhas:
        sys.stderr.write("ITENS SEM CASO (%d):\n  %s\n" % (len(falhas), "\n  ".join(falhas)))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
