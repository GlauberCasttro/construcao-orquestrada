"""motor.py — peças do oráculo GERADO da onda 1 (usadas por gerar.py e test_gerado.py). Oráculo O1-gerado.

Nada aqui implementa o produto. Contém, todas derivadas dos references (contrato/maquina/portoes/invariantes/
formatos .json5) e do ESPEC.md:
  * um avaliador de guarda PRÓPRIO (lógica de Kleene, para prever o resultado de cada linha da tabela);
  * a semântica de destino de invariantes.json5 (nó = (estado, portao, retorno));
  * ROTAS: listas de passos (registros do ledger) que levam a obra/task/campanha a qualquer nó, com contadores
    bombeados por ciclos legítimos da máquina — `simular()` re-dobra os passos pela máquina e acusa rota
    incoerente (falha do próprio gerador, nunca do produto);
  * EVIDÊNCIAS: para cada átomo computável na onda 1, como torná-lo verdadeiro/falso por efeito real (arquivo,
    registro no ledger, audit, payload), nunca por injeção do próprio átomo.
Python 3.9+, só stdlib.
"""
import itertools
import json
import os
import re
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
ONDA1 = os.path.dirname(AQUI)
if ONDA1 not in sys.path:
    sys.path.insert(0, ONDA1)

from _comum import REFS, json5_load  # noqa: E402

MAQ = json5_load(os.path.join(REFS, "maquina.json5"))
CON = json5_load(os.path.join(REFS, "contrato.json5"))
FMT = json5_load(os.path.join(REFS, "formatos.json5"))
POR = json5_load(os.path.join(REFS, "portoes.json5"))
INV = json5_load(os.path.join(REFS, "invariantes.json5"))

CONST = dict(MAQ["constantes"])
CONTADORES = dict(MAQ["contadores"])
ATORES = list(MAQ["atores"])
NIVEIS = ["obra", "task", "campanha"]
TASK_ID = "T-01"
CAMP_ID = "C-01"
PASSADO = "2020-01-01T00:00:00Z"
FUTURO = "2099-01-01T00:00:00Z"


# ====================================================================== guardas (avaliador próprio, Kleene)

def parse(expr):
    toks = re.findall(r"\d+|[A-Za-z_]\w*|<=|>=|==|!=|<|>|\(|\)", expr)
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def take():
        t = toks[pos[0]]
        pos[0] += 1
        return t

    def p_or():
        a = p_and()
        while peek() == "or":
            take()
            a = ("or", a, p_and())
        return a

    def p_and():
        a = p_not()
        while peek() == "and":
            take()
            a = ("and", a, p_not())
        return a

    def p_not():
        if peek() == "not":
            take()
            return ("not", p_not())
        return p_cmp()

    def p_cmp():
        a = p_prim()
        if peek() in ("<", "<=", ">", ">=", "==", "!="):
            op = take()
            return ("cmp", op, a, p_prim())
        return a

    def p_prim():
        t = take()
        if t == "(":
            a = p_or()
            if take() != ")":
                raise ValueError("parêntese")
            return a
        if t.isdigit():
            return ("num", int(t))
        if t in ("true", "false"):
            return ("const", t == "true")
        return ("id", t)

    ast = p_or()
    if pos[0] != len(toks):
        raise ValueError("sobra em %r" % expr)
    return ast


def ids(ast, acc=None):
    acc = set() if acc is None else acc
    if ast[0] == "id":
        acc.add(ast[1])
    for x in ast[1:]:
        if isinstance(x, tuple):
            ids(x, acc)
    return acc


def ev3(ast, val):
    k = ast[0]
    if k in ("const", "num"):
        return ast[1]
    if k == "id":
        return val(ast[1])
    if k == "not":
        v = ev3(ast[1], val)
        return None if v is None else (not v)
    if k in ("and", "or"):
        a, b = ev3(ast[1], val), ev3(ast[2], val)
        dom = False if k == "and" else True
        if a is dom or b is dom:
            return dom
        if a is None or b is None:
            return None
        return not dom
    if k == "cmp":
        a, b = ev3(ast[2], val), ev3(ast[3], val)
        if a is None or b is None:
            return None
        return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b, "==": a == b, "!=": a != b}[ast[1]]
    raise ValueError(k)


def atomos_de(guard):
    return sorted(i for i in ids(parse(guard)) if i not in CONST and i not in CONTADORES)


def comparacoes(guard):
    """[(contador, op, constante)] das comparações contador × constante da guarda."""
    out = []

    def rec(a):
        if a[0] == "cmp" and a[2][0] == "id" and a[3][0] == "id" and a[2][1] in CONTADORES and a[3][1] in CONST:
            out.append((a[2][1], a[1], a[3][1]))
        for x in a[1:]:
            if isinstance(x, tuple):
                rec(x)
    rec(parse(guard))
    return out


# ====================================================================== máquina: nós, aplicabilidade, destino

def transicoes(nivel):
    return MAQ["niveis"][nivel]["transitions"]


def aplicavel(t, no):
    if no[0] not in (t.get("from") or []):
        return False
    attrs = {"portao": no[1], "retorno": no[2]}
    return all(attrs.get(k) == v for k, v in (t.get("requer") or {}).items())


def destino(nivel, t, no):
    """invariantes.json5#modelo: @retorno ⇒ retorno do nó; set grava portao/retorno ('@from' = origem); atributos
    não setados preservados só no transversal que os declara; estado comum limpa portao/retorno."""
    to = t["to"]
    if to == "@retorno":
        if not no[2]:
            return None
        to = no[2]
    trv = MAQ["niveis"][nivel].get("transversais") or {}
    if to not in trv:
        return (to, None, None)
    attrs = {"portao": no[1], "retorno": no[2]}
    for k, v in (t.get("set") or {}).items():
        attrs[k] = no[0] if v == "@from" else v
    keep = trv[to].get("atributos") or []
    return (to, attrs["portao"] if "portao" in keep else None, attrs["retorno"] if "retorno" in keep else None)


def incrementos(t):
    inc = t.get("incrementa")
    return [] if inc is None else ([inc] if isinstance(inc, str) else list(inc))


def zera(tn, t):
    out = list(t.get("zera") or [])
    for c, d in CONTADORES.items():
        if tn in (d.get("zera_em") or []) and c not in out:
            out.append(c)
    return out


def nivel_do_evento(ev):
    return "task" if ev.startswith("task.") else "campanha" if ev.startswith("campanha.") else "obra"


def grupo(nivel, evento, no):
    """Transições (nome, t, destino) do mesmo evento aplicáveis ao nó — as candidatas de uma escrita."""
    out = []
    for tn, t in transicoes(nivel).items():
        if t["evento"] == evento and aplicavel(t, no):
            d = destino(nivel, t, no)
            if d is not None:
                out.append((tn, t, d))
    return out


# ====================================================================== rotas (passos do ledger)
# passo: {"k": "t"|"op"|"h", ...}. "h" = aprovação humana gravada à mão (registro `aprovacao` + transição humana
# + linha `tipo aprovacao` no audit, para o fixture ficar coerente com A8/R3-10).

def T(ev, de, para, ator, payload=None, nivel="obra", task=None, chave=None, portao=None):
    return {"k": "t", "evento": ev, "de": de, "para": para, "ator": ator, "payload": payload or {}, "nivel": nivel,
            "task": task, "chave": chave, "portao": portao}


def OP(ev, payload=None, chave=None):
    return {"k": "op", "evento": ev, "payload": payload or {}, "chave": chave}


def H(portao, ev, para):
    return {"k": "h", "portao": portao, "evento": ev, "para": para}


def no_obra(spec):
    """'LOTE' | 'AH:stop' | 'AH:oraculo_mudar@LOTE' | 'PAUSADO@LOTE' | 'AH:continuar@LOTE' -> (estado, portao, ret)."""
    ret = None
    if "@" in spec:
        spec, ret = spec.split("@", 1)
    if spec.startswith("AH:"):
        return ("AGUARDANDO_HUMANO", spec[3:], ret)
    return (spec, None, ret)


NOS_OBRA = ["INICIO", "PREMISSAS", "AH:stop", "ORACULO", "AH:oraculo", "BASELINE", "PLANO", "AH:plano", "LOTE",
            "DESPACHADO", "INTEGRAR", "CORRIGIR", "VERIFICAR", "MEDIR", "FECHAR_RODADA", "AH:entrega", "AH:escalar",
            "REPLANEJAR", "AH:abandonar", "AH:oraculo_mudar@LOTE", "PAUSADO@LOTE", "AH:continuar@LOTE", "ENTREGUE",
            "ABANDONADO"]


def spec_de_no(no):
    est, portao, ret = no
    if est == "AGUARDANDO_HUMANO":
        return "AH:%s" % portao + ("@%s" % ret if ret else "")
    return est + ("@%s" % ret if ret else "")


def _limite(R, retomar_apos):
    return T("limite_uso", R, "PAUSADO", "script",
             {"causa": "outro", "retomar_apos": retomar_apos or PASSADO, "mensagem": "parede"})


def rota_obra(spec, cont=None, retomar_apos=None):
    cont = dict(cont or {})
    usado = {}

    def pega(c, default=0):
        v = cont.pop(c, default)
        usado[c] = v
        return v

    def ate(s):
        est, portao, ret = no_obra(s)
        if s == "INICIO":
            return []
        if s == "PREMISSAS":
            return [T("iniciar", "INICIO", "PREMISSAS", "script")]
        if s == "AH:stop":
            return ate("PREMISSAS") + [T("premissas_ok", "PREMISSAS", "AGUARDANDO_HUMANO", "orquestrador",
                                         {"obra_hash": "a" * 64, "pontos_hash": "b" * 64, "pontos_ids": []})]
        if s == "ORACULO":
            return ate("AH:stop") + [H("stop", "aprovado", "ORACULO")]
        if s == "AH:oraculo":
            return ate("ORACULO") + [T("oraculo_pronto", "ORACULO", "AGUARDANDO_HUMANO", "orquestrador")]
        if s == "BASELINE":
            return ate("AH:oraculo") + [H("oraculo", "aprovado", "BASELINE")]
        if s == "PLANO":
            return ate("BASELINE") + [OP("oraculo_congelado", {"hash": "f" * 64, "n_testes": 1, "n_assercoes": 1,
                                                               "manifest_hash": "e" * 64}),
                                      T("dispensado", "BASELINE", "PLANO", "orquestrador", {"motivo": "cli"})]
        if s == "AH:plano":
            return ate("PLANO") + [T("plano_ok", "PLANO", "AGUARDANDO_HUMANO", "orquestrador",
                                     {"plano_hash": "c" * 64, "regressao_hash": "d" * 64, "ha_decisoes": True}),
                                   OP("contrato_hash", {"contrato_hash": "a" * 64, "plano_hash": "c" * 64,
                                                        "max_despachos": CONST["MAX_DESPACHOS"]})]
        if s == "LOTE":
            p = ate("PLANO") + [T("plano_ok", "PLANO", "LOTE", "orquestrador",
                                  {"plano_hash": "c" * 64, "regressao_hash": "d" * 64, "ha_decisoes": False}),
                                OP("contrato_hash", {"contrato_hash": "a" * 64, "plano_hash": "c" * 64,
                                                     "max_despachos": CONST["MAX_DESPACHOS"]})]
            for _ in range(pega("tentativas")):
                p += [T("fronteira_vazia", "LOTE", "INTEGRAR", "script"), T("violou", "INTEGRAR", "CORRIGIR", "script"),
                      T("campanhas_abertas", "CORRIGIR", "LOTE", "orquestrador")]
            for _ in range(pega("despachos")):
                p += [T("lote_ok", "LOTE", "DESPACHADO", "orquestrador"),
                      T("todos_retornaram", "DESPACHADO", "LOTE", "script")]
            return p
        if s == "DESPACHADO":
            return ate("LOTE") + [T("lote_ok", "LOTE", "DESPACHADO", "orquestrador")]
        if s == "INTEGRAR":
            return ate("LOTE") + [T("fronteira_vazia", "LOTE", "INTEGRAR", "script")]
        if s == "CORRIGIR":
            return ate("INTEGRAR") + [T("violou", "INTEGRAR", "CORRIGIR", "script")]
        if s == "VERIFICAR":
            return ate("INTEGRAR") + [T("merge_ok", "INTEGRAR", "VERIFICAR", "script")]
        if s == "MEDIR":
            return ate("VERIFICAR") + [T("verde", "VERIFICAR", "MEDIR", "script")]
        if s == "FECHAR_RODADA":
            p = ate("MEDIR") + [T("medido", "MEDIR", "FECHAR_RODADA", "script")]
            for _ in range(pega("rodada")):
                p += [T("rodada_fechada", "FECHAR_RODADA", "CORRIGIR", "script",
                        {"saida": "continuar", "criterio_parada_ok": False, "plato_2": False, "comparacao_hash": None}),
                      T("campanhas_abertas", "CORRIGIR", "LOTE", "orquestrador"),
                      T("fronteira_vazia", "LOTE", "INTEGRAR", "script"), T("merge_ok", "INTEGRAR", "VERIFICAR", "script"),
                      T("verde", "VERIFICAR", "MEDIR", "script"), T("medido", "MEDIR", "FECHAR_RODADA", "script")]
            return p
        if s == "AH:entrega":
            return ate("FECHAR_RODADA") + [T("rodada_fechada", "FECHAR_RODADA", "AGUARDANDO_HUMANO", "script",
                                             {"saida": "parar", "criterio_parada_ok": True, "plato_2": False,
                                              "comparacao_hash": None}, portao="entrega")]
        if s == "AH:escalar":
            return ate("FECHAR_RODADA") + [T("rodada_fechada", "FECHAR_RODADA", "AGUARDANDO_HUMANO", "script",
                                             {"saida": "escalar", "criterio_parada_ok": False, "plato_2": True,
                                              "comparacao_hash": None}, portao="escalar")]
        if s == "REPLANEJAR":
            if cont.get("tentativas", 0) >= CONST["MAX_TENTATIVAS"]:
                p = ate("CORRIGIR") + [T("campanhas_abertas", "CORRIGIR", "REPLANEJAR", "script")]
            else:
                p = ate("AH:plano") + [H("plano", "rejeitado", "REPLANEJAR")]
            for _ in range(pega("replanejamentos")):
                p += [T("novo_plano", "REPLANEJAR", "PLANO", "orquestrador"),
                      T("plano_ok", "PLANO", "AGUARDANDO_HUMANO", "orquestrador",
                        {"plano_hash": "c" * 64, "regressao_hash": "d" * 64, "ha_decisoes": True}),
                      OP("contrato_hash", {"contrato_hash": "a" * 64, "plano_hash": "c" * 64,
                                           "max_despachos": CONST["MAX_DESPACHOS"]}),
                      H("plano", "rejeitado", "REPLANEJAR")]
            return p
        if s == "AH:abandonar":
            return ate("REPLANEJAR") + [T("desistir", "REPLANEJAR", "AGUARDANDO_HUMANO", "orquestrador")]
        if s == "ENTREGUE":
            return ate("AH:entrega") + [H("entrega", "aprovado", "ENTREGUE")]
        if s == "ABANDONADO":
            return ate("AH:abandonar") + [H("abandonar", "aprovado", "ABANDONADO")]
        if est == "AGUARDANDO_HUMANO" and portao == "oraculo_mudar":
            return ate(ret) + [T("oraculo_mudar", ret, "AGUARDANDO_HUMANO", "orquestrador",
                                 {"motivo": "requisito novo", "evidencia": "pedido do founder"})]
        if est == "PAUSADO":
            n = pega("pausas", 1)
            p = ate(ret)
            for _ in range(max(n - 1, 0)):
                p += [_limite(ret, PASSADO), T("retomar", "PAUSADO", ret, "orquestrador")]
            return p + [_limite(ret, retomar_apos)]
        if est == "AGUARDANDO_HUMANO" and portao == "continuar":
            cont["pausas"] = CONST["MAX_PAUSAS"]
            return ate("PAUSADO@%s" % ret) + [T("retomar", "PAUSADO", "AGUARDANDO_HUMANO", "script")]
        raise KeyError("rota desconhecida: %s" % s)

    passos = ate(spec)
    sobra = {c: v for c, v in cont.items() if v}
    if sobra:
        raise KeyError("contador sem âncora na rota %s: %s" % (spec, sobra))
    return passos


def _ch(n):
    return "obra/1/%s/%d" % (TASK_ID, n)


def _desp(ch, task=TASK_ID, tent=1, isolation=None):
    return OP("despachada", {"task": task, "papel": "construtor", "chave": ch, "agent_type": "builder-A",
                             "writes": ["src/**"] if task == TASK_ID else ["docs/%s/**" % task], "reads": [],
                             "tentativa": tent, "brief_hash": "9" * 64,
                             "isolation": isolation, "teto_vigente": 5, "vivos_antes": 0}, chave=ch)


def _ret(ch, task=TASK_ID):
    return OP("retornou", {"task": task, "chave": ch, "relatorio": "/x/rel.json", "relatorio_hash": "8" * 64}, chave=ch)


def tt(ev, de, para, ator, payload=None, chave=None, task=TASK_ID):
    p = dict(payload or {})
    return T(ev, de, para, ator, p, nivel="task", task=task, chave=chave)


def ciclo_task(n, task=TASK_ID, fim="RETORNADA"):
    """PRONTA → EM_VOO → RETORNADA (com despachada/retornou, D3)."""
    ch = "obra/1/%s/%d" % (task, n)
    p = [_desp(ch, task), tt("task.despachar", "PRONTA", "EM_VOO", "orquestrador", {"chave": ch}, ch, task)]
    if fim == "EM_VOO":
        return p
    return p + [_ret(ch, task), tt("task.retornar", "EM_VOO", "RETORNADA", "orquestrador", {"chave": ch}, ch, task)]


def _verif(ok, task=TASK_ID, motivo="r"):
    return tt("task.verificada", "RETORNADA", "ACEITA" if ok else "REJEITADA", "script",
              {"verificacao_ok": ok, "verificador": "verificador-V", "motivo_rejeicao": None if ok else motivo,
               "diff_hash": "7" * 64}, task=task)


def rota_task(est, cont=None, task=TASK_ID, base="LOTE", rej_igual=False):
    """rej_igual: todas as rejeições com o MESMO motivo (evidência de mesma_rejeicao_2x); senão motivos distintos.
    base: nó da obra antes dos registros da task ("REPLANEJAR+" = obra que já replanejou: há `novo_plano`)."""
    cont = dict(cont or {})
    n = [0]
    nrej = [0]

    def rej():
        nrej[0] += 1
        return _verif(False, task, "mesmo motivo" if rej_igual else "motivo %d" % nrej[0])

    def nxt():
        n[0] += 1
        return n[0]

    def ate(s):
        if s == "PENDENTE":
            return []
        if s == "PRONTA":
            p = [tt("task.pronta", "PENDENTE", "PRONTA", "script", task=task)]
            for _ in range(cont.pop("tentativas", 0)):
                p += ciclo_task(nxt(), task) + [rej(),
                                                tt("task.retentar", "REJEITADA", "PRONTA", "orquestrador", task=task)]
            return p
        if s == "EM_VOO":
            return ate("PRONTA") + ciclo_task(nxt(), task, fim="EM_VOO")
        if s == "RETORNADA":
            return ate("PRONTA") + ciclo_task(nxt(), task)
        if s == "ACEITA":
            p = ate("RETORNADA") + [_verif(True, task)]
            for _ in range(cont.pop("reaberturas", 0)):
                p += [tt("task.reabrir", "ACEITA", "PRONTA", "orquestrador",
                         {"motivo": "entradas mudaram", "hash_entradas_antes": "1" * 64,
                          "hash_entradas_depois": "2" * 64}, task=task)]
                p += ciclo_task(nxt(), task) + [_verif(True, task)]
            return p
        if s == "REJEITADA":
            return ate("RETORNADA") + [rej()]
        if s == "DESCARTADA":
            return ate("PRONTA") + [tt("task.descartar", "PRONTA", "DESCARTADA", "script", {"motivo": "replanejou"},
                                       task=task)]
        raise KeyError(s)

    p = (rota_obra("REPLANEJAR", {"replanejamentos": 1}) if base == "REPLANEJAR+" else rota_obra(base)) + ate(est)
    if any(cont.values()):
        raise KeyError("contador de task sem âncora: %s" % cont)
    return p


def tc(ev, de, para, ator, payload=None):
    return T(ev, de, para, ator, payload, nivel="campanha", task=CAMP_ID)


def rota_campanha(est, cont=None):
    cont = dict(cont or {})

    def ate(s):
        if s == "RASCUNHO":
            return []
        if s == "ATIVA":
            return [tc("campanha.ativar", "RASCUNHO", "ATIVA", "script")]
        if s == "PRONTA_INTEGRAR":
            p = ate("ATIVA") + [tc("campanha.pronta", "ATIVA", "PRONTA_INTEGRAR", "script")]
            for _ in range(cont.pop("reintegracoes", 0)):
                p += [tc("campanha.integrar", "PRONTA_INTEGRAR", "ATIVA", "script"),
                      tc("campanha.pronta", "ATIVA", "PRONTA_INTEGRAR", "script")]
            return p
        if s == "INTEGRADA":
            return ate("PRONTA_INTEGRAR") + [tc("campanha.integrar", "PRONTA_INTEGRAR", "INTEGRADA", "script")]
        if s == "ABANDONADA":
            return [tc("campanha.abandonar", "RASCUNHO", "ABANDONADA", "orquestrador", {"motivo": "fora"})]
        raise KeyError(s)

    p = rota_obra("CORRIGIR") + ate(est)
    if any(cont.values()):
        raise KeyError("contador de campanha sem âncora: %s" % cont)
    return p


def rota(nivel, no, cont=None, retomar_apos=None, base_task="LOTE", rej_igual=False):
    if nivel == "obra":
        return rota_obra(no, cont, retomar_apos)
    if nivel == "task":
        return rota_task(no, cont, base=base_task, rej_igual=rej_igual)
    return rota_campanha(no, cont)


# ====================================================================== simulação (fold próprio sobre os passos)

def estado_inicial():
    return {"obra": ("INICIO", None, None), "contadores": {c: 0 for c, d in CONTADORES.items()
                                                          if "obra" in (d.get("nivel") or [])},
            "tasks": {}, "campanhas": {}, "vivos": [], "teto": MAQ["paralelismo"]["teto_padrao"]}


def aplicar(st, nivel, evento, de, para, ator, task=None, payload=None, portao=None):
    """Aplica uma transição ao estado simulado; KeyError se ela não existe na máquina (rota incoerente)."""
    if nivel == "obra":
        no = st["obra"]
    elif nivel == "task":
        e = st["tasks"].setdefault(task, {"estado": "PENDENTE", "tentativas": 0, "reaberturas": 0})
        no = (e["estado"], None, None)
    else:
        e = st["campanhas"].setdefault(task, {"estado": "RASCUNHO", "reintegracoes": 0})
        no = (e["estado"], None, None)
    if no[0] != de:
        raise KeyError("passo %s parte de %s mas o estado é %s" % (evento, de, no[0]))
    cand = [(tn, t, d) for tn, t, d in grupo(nivel, evento, no) if d[0] == para and t["actor"] == ator
            and (portao is None or d[1] == portao)]
    if not cand:
        raise KeyError("transição %s %s→%s (%s) inexistente em %s" % (evento, de, para, ator, no))
    tn, t, d = cand[0]
    if nivel == "obra":
        st["obra"] = d
        for c in incrementos(t):
            st["contadores"][c] += 1
        for c in zera(tn, t):
            st["contadores"][c] = 0
    else:
        e["estado"] = d[0]
        for c in incrementos(t):
            e[c] = e.get(c, 0) + 1
        for c in t.get("zera") or []:
            e[c] = 0
    return tn


def simular(passos, st=None):
    st = st or estado_inicial()
    for p in passos:
        if p["k"] == "op":
            ch = p.get("chave")
            if p["evento"] == "despachada" and ch not in st["vivos"]:
                st["vivos"].append(ch)
            elif p["evento"] in ("retornou", "perdida", "colhida") and ch in st["vivos"]:
                st["vivos"].remove(ch)
            elif p["evento"] == "teto_recuado":
                st["teto"] = p["payload"].get("para", 3)
        elif p["k"] == "h":
            aplicar(st, "obra", p["evento"], "AGUARDANDO_HUMANO", p["para"], "humano")
        else:
            aplicar(st, p["nivel"], p["evento"], p["de"], p["para"], p["ator"], p.get("task"), p.get("payload"),
                    p.get("portao"))
    return st


def no_atual(st, nivel):
    if nivel == "obra":
        return st["obra"]
    if nivel == "task":
        return (st["tasks"].get(TASK_ID, {}).get("estado", "PENDENTE"), None, None)
    return (st["campanhas"].get(CAMP_ID, {}).get("estado", "RASCUNHO"), None, None)


def contadores_no(st, nivel):
    if nivel == "obra":
        return dict(st["contadores"])
    ent = st["tasks"].get(TASK_ID) if nivel == "task" else st["campanhas"].get(CAMP_ID)
    ent = ent or {}
    base = dict(st["contadores"])
    for c in ("tentativas", "reaberturas", "reintegracoes"):
        if c in ent or nivel != "obra":
            base[c] = ent.get(c, 0)
    return base


# ====================================================================== evidências (átomos computáveis na onda 1)
# fase "pre" = antes de escrever a rota (arquivos da obra); "pos" = depois (registros/arquivos); "payload" = conteúdo
# do evento; "rel" = gate-report + portao_relatorio; "ultimo" = depois de tudo (RETOMAR.md). `nos` restringe onde o
# valor é montável (None = qualquer nó). Os átomos FORA desta tabela não são computados pelo produto na onda 1
# (co_estado: "indeterminados até as ondas 2–3") e só entram por injeção de chamador confiável.

EVID = {
    "hook_vivo": {"fase": "pos", "como": "V: linha tool_call bloqueada `aprovar __selftest__` no audit (+ selftest real); F: sem a linha"},
    "workspace_fora_do_alvo": {"fase": "pre", "como": "V: obra.alvo como criado; F: obra.alvo reescrito para um ancestral do ws"},
    "pontos_completos": {"fase": "pre", "como": "V: pontos.json5 com P-01 válido; F: pontos.json5 vazio"},
    "stop_numerico": {"fase": "pre", "como": "V: stop numérico do init; F: obra.stop.numerico = null"},
    "motivo_registrado": {"fase": "payload", "como": "V: --payload com motivo; F: sem motivo"},
    "evidencia_registrada": {"fase": "payload", "como": "V: --payload com evidencia; F: sem evidencia"},
    "limite_detectado": {"fase": "payload", "como": "V: payload {causa: outro, retomar_apos ts}; F: causa inválida"},
    "agora_apos_retomar": {"fase": "pre", "como": "V: limite_uso com retomar_apos no passado; F: no futuro"},
    "sem_perdidas_pendentes": {"fase": "pos", "como": "V: nenhum despachada aberto; F: despachada sem retornou"},
    "lote_cabe_no_teto": {"fase": "pos", "como": "V: vivos = teto-1; F: vivos = teto (despachada sem retornou)"},
    "vivos_abaixo_do_teto": {"fase": "pos", "como": "V: vivos = teto-1; F: vivos = teto"},
    "nenhuma_em_voo": {"fase": "pos", "como": "V: nenhuma task EM_VOO; F: task T-09 despachada (EM_VOO)"},
    "todas_tasks_retornadas_ou_aceitas": {"fase": "pos", "como": "V: T-09 RETORNADA; F: T-09 PRONTA"},
    "trava_adquirida": {"fase": "pos", "como": "V: evento trava_adquirida; F: sem trava"},
    "oraculo_congelado": {"fase": "pos", "como": "V: evento oraculo_congelado; F: sem ele",
                          "nos": ["BASELINE"]},
    "tipo_exige_baseline": {"fase": "pre", "como": "V: obra.tipo = skill; F: cli"},
    "ha_decisoes": {"fase": "pre", "como": "V: PLANO.json5 com decisoes [DEC-1]; F: decisoes []"},
    "retomar_md_valido": {"fase": "ultimo", "como": "V: RETOMAR.md regenerado por `ev nota` no último registro; F: um registro depois dele"},
    "pass3_final": {"fase": "pos", "como": "V: medicao_registrada final k=3 não simulada; F: k=1 não final"},
    "veredito_go_final": {"fase": "rel", "como": "V: gate-report completo final GO + portao_relatorio + audit das aprovações; F: G2 FAIL/NO-GO"},
    "portao_regressao_go": {"fase": "rel", "como": "V: gate-report completo final GO; F: G2 FAIL/NO-GO"},
    "g3_reprovou": {"fase": "rel", "como": "V: G3 FAIL no gate-report registrado; F: G3 PASS"},
    "g4_reprovou": {"fase": "rel", "como": "V: G4 FAIL no gate-report registrado; F: G4 PASS"},
    "diff_no_territorio": {"fase": "rel", "como": "V: G3 PASS no gate-report registrado; F: G3 FAIL"},
    "aprovacao_humana": {"fase": "canal", "como": "V: `co.py aprovar` num pty com o desafio redigitado; F: sem canal humano"},
    "perdida_na_retomada": {"fase": "retomar", "como": "V: `co.py retomar` com a task EM_VOO e a vaga aberta; F: `ev task.perdida` direto"},
    "verificacao_ok": {"fase": "definido", "como": "maquina.atomos_definidos: diff_no_territorio (G3 no gate-report) and testes_vermelho_verde (relatório da frente real, vermelho→verde) and verificador_nao_autor (payload.verificador fora dos construtores)"},
    # ---- G-8: os 35 que o produto passou a recalcular da evidência (antes só por injeção)
    "plano_valido": {"fase": "pre", "como": "V: PLANO.json5 com T-01 src/** e T-02 docs/** (disjuntos); F: T-02 escreve src/** (sobrepõe)"},
    "brief_valido": {"fase": "pre", "como": "V: T-01 completa no PLANO; F: T-01 sem `criterio`"},
    "deps_aceitas": {"fase": "pre", "como": "V: T-01 deps []; F: T-01 deps [T-02] com T-02 não ACEITA (obra: T-01 PRONTA no lote)"},
    "lote_disjunto": {"fase": "pos", "como": "V: lote T-01 sem vivo sobreposto; F: vivo (despachada) escrevendo src/**"},
    "writes_disjuntos_dos_vivos": {"fase": "pos", "como": "V: nenhum vivo de outra task; F: vivo de T-09 escrevendo src/**"},
    "obra_replanejou": {"fase": "pre", "como": "V: obra com `novo_plano` e PLANO sem T-01; F: obra sem `novo_plano`"},
    "hash_entradas_mudou": {"fase": "pos", "como": "V: PLANO.T-01 alterado depois do aceite (hash_entradas gravado no aceite); F: inalterado"},
    "orcamento_esgotado": {"fase": "pre", "como": "V: obra.max_horas já vencido desde a gênese; F: max_horas null e despachos < MAX"},
    "orcamento_restante": {"fase": "pre", "como": "V: orçamento aberto; F: obra.max_horas já vencido"},
    "campanhas_ativas_abaixo_de_2": {"fase": "pos", "como": "V: nenhuma outra campanha ativa; F: C-02 e C-03 ATIVA no ledger"},
    "mesma_rejeicao_2x": {"fase": "pre", "como": "V: duas últimas rejeições (task.verificada) com o mesmo motivo; F: motivos distintos/nenhuma"},
    "oscilacao": {"fase": "pos", "como": "V: rodadas/1,2/comparacao.json com Q.delta +0.2 e -0.1; F: +0.2 e +0.1"},
    "plato_2": {"fase": "pos", "como": "V: duas comparações com delta 0 'sem efeito'; F: delta +0.3 'melhora'"},
    "copia_limpa": {"fase": "pos", "como": "V: run.json copia_limpa true na medição; F: false"},
    "sistema_congelado_na_medicao": {"fase": "pos", "como": "V: run.json hash início = fim = hash_sistema(alvo); F: hash fim diferente do início"},
    "medicao_posterior_ao_merge": {"fase": "pos", "como": "V: medicao_registrada após o merge com seq_ultimo_merge certo; F: seq_ultimo_merge errado"},
    "baseline_reprodutivel": {"fase": "pos", "como": "V: baseline.json + medição baseline + 2 runs com o mesmo [Q]; F: [Q] diferentes"},
    "criterio_parada_ok": {"fase": "pos", "como": "V: medição final k=3 pass_hat_k 1.0 (stop pass_hat_3 >= 1.0); F: pass_hat_k 0.5"},
    "pontos_atualizados": {"fase": "pre", "como": "V: P-01 com historico da rodada corrente; F: sem historico"},
    "autor_fora_dos_construtores": {"fase": "pos", "como": "V: MANIFEST autores fora dos construtores do PLANO (+ manifest_gravado); F: autor = builder-A"},
    "criterios_classificados": {"fase": "pos", "como": "V: teste do oráculo com '# cenario: C-01 ... classe: Q'; F: sem a classificação"},
    "pontos_cobertos": {"fase": "pos", "como": "V: P-01 cenarios [C-01] presente no oráculo; F: [C-99]"},
    "vermelho_baseline_e_stub": {"fase": "pos", "como": "V: teste do oráculo reprova o alvo e o stub; F: teste que passa (vácuo)"},
    "merge_ordenado": {"fase": "pos", "como": "V: trava_adquirida T-01 depois T-02; F: T-02 depois T-01"},
    "oraculo_apos_cada_merge": {"fase": "pos", "como": "V: portao_relatorio depois de cada trava; F: só depois da última"},
    "relatorio_presente": {"fase": "pos", "como": "V: `retornou` com relatório da frente real e hash certo; F: hash do relatório não confere"},
    "verificador_nao_autor": {"fase": "pos", "como": "V: despachada papel verificador agent_type verificador-V; F: agent_type builder-A (construtor)"},
    "resultado_no_worktree": {"fase": "valor", "como": "V: despachada isolation worktree + colhida com diff_hash; F: isolation null (valor_atomo; colhida é onda 2)"},
    "oraculo_campanha_congelado": {"fase": "pos", "como": "V: campanha C-01 com `oracle freeze` íntegro; F: arquivo alterado depois do freeze"},
    "ac_decisao_parar": {"fase": "pos", "como": "V: state.json da campanha decision 'parar' + done.decisao.1; F: decision 'continuar'"},
    "oraculos_fechados_verdes": {"fase": "pos", "como": "V: runs.jsonl da rodada com [Q] total passou; F: 1/2"},
    "colisao_vazia": {"fase": "pos", "como": "V: PLANO da campanha escreve docs/**, nada vivo sobreposto; F: vivo escrevendo docs/**"},
    "defeitos_classificados": {"fase": "pos", "como": "V: DEFEITOS.json5 com classes válidas; F: um defeito classe 'xpto'"},
    "so_sistema_vira_task": {"fase": "pos", "como": "V: frentes só com defeitos classe sistema; F: frente com defeito classe oraculo"},
    "teste_falha_antes": {"fase": "pos", "como": "V: defeito sistema reproduzido + run vermelho registrado; F: reproduzido false"},
}
# átomos cujo valor vem do DISCO (arquivo/ledger/audit), não do payload: injeção não pode sobrepor (ESPEC, R2
# "Interpretações novas": "Os computados do disco ... continuam valendo").
DISCO = ["hook_vivo", "workspace_fora_do_alvo", "pontos_completos", "stop_numerico", "agora_apos_retomar",
         "sem_perdidas_pendentes", "lote_cabe_no_teto", "vivos_abaixo_do_teto", "nenhuma_em_voo",
         "todas_tasks_retornadas_ou_aceitas", "trava_adquirida", "oraculo_congelado", "tipo_exige_baseline",
         "ha_decisoes", "retomar_md_valido", "portao_regressao_go", "g3_reprovou", "g4_reprovou",
         "diff_no_territorio",
         # G-8 (computados; injeção só completa None): o disco também vence
         "plano_valido", "brief_valido", "deps_aceitas", "lote_disjunto", "writes_disjuntos_dos_vivos",
         "obra_replanejou", "hash_entradas_mudou", "orcamento_esgotado", "orcamento_restante",
         "campanhas_ativas_abaixo_de_2", "mesma_rejeicao_2x", "oscilacao", "plato_2", "copia_limpa",
         "sistema_congelado_na_medicao", "medicao_posterior_ao_merge", "baseline_reprodutivel", "criterio_parada_ok",
         "pontos_atualizados", "autor_fora_dos_construtores", "criterios_classificados", "pontos_cobertos",
         "vermelho_baseline_e_stub", "merge_ordenado", "oraculo_apos_cada_merge", "relatorio_presente",
         "verificador_nao_autor", "oraculo_campanha_congelado", "ac_decisao_parar", "oraculos_fechados_verdes",
         "colisao_vazia", "defeitos_classificados", "so_sistema_vira_task", "teste_falha_antes"]
TRAVA_DEP = ("merge_ordenado", "oraculo_apos_cada_merge")  # sem trava_adquirida: indeterminados


def efetivos(assign):
    """Valores que o produto VERÁ: sem trava não há o que ordenar (merge_ordenado/oraculo_apos indeterminados)."""
    a = dict(assign)
    if a.get("trava_adquirida") is False:
        for x in TRAVA_DEP:
            a.pop(x, None)
    return a

REL_ATOMOS = ("veredito_go_final", "portao_regressao_go", "g3_reprovou", "g4_reprovou", "diff_no_territorio",
              "verificacao_ok")
DEFINIDO_INJETA = {}  # componentes de verificacao_ok montados por evidência (relatório + payload.verificador)


def spec_relatorio(assign):
    """Restrições de gate-report impostas pelos átomos de relatório; None se contraditórias."""
    itens, go = {}, None
    for a in REL_ATOMOS:
        if a not in assign:
            continue
        v = assign[a]
        if a in ("veredito_go_final", "portao_regressao_go"):
            if v:
                go = True if go in (None, True) else "x"
            else:
                itens.setdefault("G2", "FAIL")
                go = False if go in (None, False) else "x"
        else:
            g = "G3" if a in ("g3_reprovou", "diff_no_territorio", "verificacao_ok") else "G4"
            st = ("PASS" if v else "FAIL") if a in ("diff_no_territorio", "verificacao_ok") else \
                ("FAIL" if v else "PASS")
            if itens.get(g, st) != st:
                return None
            itens[g] = st
    if go == "x":
        return None
    if go is True and any(s == "FAIL" for s in itens.values()):
        return None
    if go is None and not itens:
        return {}
    return {"itens": itens, "go": go}


def viavel(atomo, valor, nivel, no, cont=None):
    m = EVID.get(atomo)
    if not m:
        return False
    if m["fase"] == "valor":
        return valor is False  # V só por valor_atomo (linha dedicada); F = isolation null (padrão da rota)
    if atomo == "mesma_rejeicao_2x" and valor is True and nivel == "task" and (cont or {}).get("tentativas", 0) < 1:
        return False  # duas rejeições exigem uma retentativa na rota
    if atomo == "hash_entradas_mudou" and no[0] != "ACEITA":
        return False
    if m.get("nos") and spec_de_no(no) not in m["nos"]:
        return False
    if atomo == "oraculo_congelado" and valor is True and spec_de_no(no) != "BASELINE":
        return False
    return True


# ====================================================================== payload base por evento

def payload_base(nivel, evento, t):
    p = {}
    if nivel == "task":
        p["task"] = TASK_ID
    elif nivel == "campanha":
        p["campanha"] = CAMP_ID
    if t.get("motivo_obrigatorio"):
        p["motivo"] = "motivo registrado"
    if evento == "task.reabrir":
        p.update(hash_entradas_antes="1" * 64, hash_entradas_depois="3" * 64)
    if evento == "rodada_fechada":
        p.update(saida="x", criterio_parada_ok=False, plato_2=False, comparacao_hash=None)
    if evento == "task.verificada":
        p.update(verificador="verificador-V", motivo_rejeicao=None, diff_hash="7" * 64)
    return p


def ts_agora():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def escolher(variaveis, pred, preferir=None):
    """Primeira atribuição booleana (ordem determinística) que satisfaz pred; preferir: {var: valor}."""
    variaveis = sorted(variaveis)
    ordem = []
    for v in variaveis:
        pv = (preferir or {}).get(v)
        ordem.append([pv, not pv] if pv is not None else [True, False])
    for combo in itertools.product(*ordem):
        a = dict(zip(variaveis, combo))
        if pred(a):
            return a
    return None


def dumps(o):
    return json.dumps(o, ensure_ascii=False, sort_keys=True)
