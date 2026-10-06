#!/usr/bin/env python3
"""co_estado.py — estado mecânico da construcao-orquestrada (frente A, onda 1). Python 3.9+, só stdlib.

Ledger append-only encadeado por hash (formatos.json5#arquivos.ledger), estado = fold do ledger (o ledger vence o
cache state.json), transições SÓ da references/maquina.json5 com guardas avaliadas em lógica de 3 valores (átomo
não computável ⇒ indeterminado ⇒ a guarda não passa: falha fechada), write-ahead de despacho (`despachada` é a única
fonte de vivos), retomada com detecção de task em voo perdida, RETOMAR.md e aprovar-<portao>.sh gerados, checador
dos invariantes (invariantes.json5) e o subcomando humano `aprovar` (tty + desafio + audit + transição humana, I6).

Exit: 0 passa · 1 guarda falsa / reprova (ledger inalterado byte a byte) · 2 entrada inválida (falha fechada).

API REUTILIZÁVEL (co_portao, co_medir e co.py importam daqui; `sys.path` = scripts/):
  Erros ............ Fail (exit 1), Bad (exit 2)
  Caminhos ......... RAIZ_SKILL, REFS, SCRIPTS, AC_PY, paths(ws) -> dict (ledger, estado_cache, obra, pontos, plano,
                     regressao, gate_report, baseline, retomar_md, aprovacoes, oraculo, manifest, campanha_mae),
                     audit_path() -> caminho real do audit (~/.claude/construcao-orquestrada/audit.jsonl)
  JSON/hash ........ json5_loads(txt), json5_load(path) (importados do ac.py), canon(obj), sha_obj(obj),
                     sha_file(path), now_ts(), escrever_json_atomico(path, obj)
  Referências ...... carregar_contrato(), carregar_maquina(nivel=None, path=None), carregar_portoes()
  Obra ............. ler_obra(ws), ler_pontos(ws), ws_real(ws)
  Ledger ........... ler_ledger(ws) -> list[dict], problemas_cadeia(registros) -> list[str],
                     verificar_cadeia(ws) -> bool, append_evento(ws, evento, ator, payload, nivel="operacional",
                     de=None, para=None, task=None, chave=None) -> seq, trava_ledger(ws) (context manager; NÃO
                     reentrante — append_evento já trava sozinho)
  Estado ........... fold(ws) -> dict (campos de formatos.estado_cache), fold_registros(regs) -> dict,
                     hash_estado(estado) -> sha256 (D8), ultimo_evento(ws, nome) -> registro|None
  Guardas .......... parse_guarda(expr) -> ast, avaliar_guarda(expr, ctx) -> bool (ctx: dict nome->valor ou
                     {"valores": {...}}), transicionar(ws, evento, payload, atomos=None) -> dict.
                     G-2: `atomos` (chamador Python confiável) só COMPLETA átomo de ATOMOS_INJETAVEIS cujo cálculo
                     deu None (artefato da onda 2–3 ainda ausente); nunca sobrepõe valor computado, contador,
                     constante, aprovacao_humana (só cmd_aprovar) nem perdida_na_retomada (só retomar).
  Átomos (G-8) ..... ATOMOS (nome -> fn(Contexto) -> True/False/None, recalculado do disco/ledger/audit),
                     ATOMOS_G8 (os 35 que antes eram só injeção), ATOMOS_SO_EVIDENCIA, ATOMOS_INJETAVEIS,
                     atomos_definidos() (maquina.*.atomos_definidos; verificacao_ok = diff_no_territorio and
                     testes_vermelho_verde and verificador_nao_autor — G-3),
                     valor_atomo(ws, nome, evento=None, payload=None, task=None) -> True/False/None (PARA A FRENTE
                     C: mesmo cálculo das guardas, sem injeção), hash_sistema(alvo) (formatos.hash_sistema),
                     hash_entradas_task(ws, st, tid). payload_do_motor(): rodada_fechada.saida/criterio_parada_ok/
                     plato_2/comparacao_hash, task.verificada.verificacao_ok/hash_entradas e task.reabrir.hash_*
                     são gravados pelo MOTOR (o payload do agente não decide).
  Fold (G-1) ....... registro com várias candidatas (rodada_fechada FECHAR_RODADA→AGUARDANDO_HUMANO: parar ×
                     escalar) é distinguido por payload.saida (SAIDA_PARA_TRANSICAO); sem `saida` coerente ⇒ Fail.
                     PARA A FRENTE C: estado.obra.portao == "entrega" só vem de `parar`; escalada nunca abre entrega.
  Pós-gravação ..... pos_gravacao(ws) (cache + RETOMAR.md + aprovar-<portao>.sh), gerar_retomar_md(ws)
  Máquina .......... checar_maquina(maquina, niveis=None) -> {"ok": bool, "violacoes": [...], "info": [...]}
  Retomada ......... retomar(ws) -> plano_retomada
  Integridade (A8) . problemas_fim_do_ledger(ws, regs, exigir_cache=True) -> list[str] (cache state.json e linhas
                     `aprovacao` do audit contra o fim do ledger; R3-3: ledger não vazio sem cache válido ⇒ problema), conferir_ledger(ws, regs) (cadeia + fim; Fail). fold(ws) e toda escrita
                     já chamam; co_portao deve usar fold()/append_evento() em vez de ler o ledger cru.
  Entrega (A1/A5) .. relatorio_satisfaz_entrega(rep) -> (bool, motivo): só run completo (only=null), final, veredito
                     "GO"|"GO (com waiver)" (nunca "GO (simulado)"), G0..G14 presentes, núcleo G0/G1/G3/G4 PASS.
                     Átomos veredito_go_final e portao_regressao_go usam isto.
                     aprovacoes_sem_audit(ws, regs) -> list[ref] (R3-10): `aprovacao` do ledger sem linha `tipo
                     aprovacao` no audit (ou feita por tool_call) — veredito_go_final exige lista vazia.
  Hashes (R3-5) .... hashes_do_disco(ws, evento, payload): premissas_ok/plano_ok gravam o hash do DISCO (transicionar
                     chama sob a trava; payload não escolhe hash).
                     PARA A FRENTE C: co_portao deve chamar relatorio_parcial_ajustado(rep) antes de gravar
                     gate-report.json (`only` ≠ null ⇒ final=false), para `portao run --only X --final` nunca
                     produzir relatório parcial com final=true e veredito GO.
  Oráculo (A9) ..... arquivos_do_oraculo(ws), contar_testes_assercoes(files), preparar_congelamento(ws),
                     congelar_oraculo(ws, prep, motivo): `aprovar oraculo --decisao aprovado` roda ac.py oracle
                     freeze na campanha-mãe e grava `oraculo_congelado` na mesma escrita da transição.
  Trava (A10/A11) .. transicionar reconfere o hash_estado do canal humano sob a trava; pos_gravacao roda sob a trava.
  Handlers CLI ..... cmd_init, cmd_ev, cmd_status, cmd_load (G-7a: refaz o fold; ledger corrompido ⇒ 1),
                     cmd_maquina, cmd_pontos, cmd_retomar,
                     cmd_oraculo_mudar, cmd_oraculo_manifest, cmd_aprovar (args do argparse de co.py -> int)
"""
import contextlib
import datetime
import fnmatch
import getpass
import hashlib
import importlib.util
import json
import os
import posixpath
import re
import secrets
import subprocess
import sys

try:
    import fcntl
except ImportError:  # pragma: no cover — só POSIX é suportado
    fcntl = None

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
RAIZ_SKILL = os.path.dirname(SCRIPTS)
REFS = os.path.join(RAIZ_SKILL, "references")
RAIZ_SKILL_TXT = "~/.claude/skills/construcao-orquestrada"
CO_TXT = "python3 %s/scripts/co.py" % RAIZ_SKILL_TXT
AC_PY = os.path.join(os.path.dirname(RAIZ_SKILL), "auto-correcao", "scripts", "ac.py")
AUDIT_TXT = os.path.join("~", ".claude", "construcao-orquestrada", "audit.jsonl")

CAMPOS_LEDGER = ["seq", "ts", "ator", "nivel", "evento", "de", "para", "task", "chave", "payload", "payload_hash",
                 "prev", "hash"]
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
CHAVES_HASH_ESTADO = ["obra", "contadores", "constantes", "teto_vigente", "tasks", "campanhas", "contrato_hash",
                      "oraculo"]
SECOES_RETOMAR = ["# Obra", "## Estado", "## Portões pendentes", "## Contrato e oráculo", "## Critério de parada",
                  "## Orçamento", "## Tasks em voo", "## Fora do escopo", "## Próximo comando"]
EVENTOS_VIA_EV = ("nota", "checkpoint_janela_50")  # operacionais que `ev` aceita; os demais têm comando próprio
JANELA_H, CHECKPOINT_H = 5.0, 2.5


class Fail(Exception):
    """Reprova / guarda falsa (exit 1)."""


class Bad(Exception):
    """Entrada inválida / ferramenta ausente (exit 2)."""


# ================================================================== JSON5 (reuso do ac.py), hash, tempo

_AC = None


def _ac():
    global _AC
    if _AC is None:
        alvo = AC_PY if os.path.isfile(AC_PY) else os.path.expanduser("~/.claude/skills/auto-correcao/scripts/ac.py")
        if not os.path.isfile(alvo):
            raise Bad("ac.py ausente (%s): necessário para json5_loads (contrato.reuso.ac_py)" % alvo)
        spec = importlib.util.spec_from_file_location("ac_reuso_co_estado", alvo)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _AC = mod
    return _AC


def json5_loads(text):
    return _ac().json5_loads(text)


def json5_load(path):
    with open(path, encoding="utf-8") as fh:
        return json5_loads(fh.read())


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha_obj(obj):
    return hashlib.sha256(canon(obj)).hexdigest()


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for bloco in iter(lambda: fh.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()


def now_ts(offset_s=0.0):
    t = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=offset_s)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(s):
    if not isinstance(s, str) or not TS_RE.match(s):
        return None
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)


def _ts_mais(ts, horas):
    d = parse_ts(ts)
    return None if d is None else (d + datetime.timedelta(hours=horas)).strftime("%Y-%m-%dT%H:%M:%SZ")


def escrever_atomico(path, texto, modo=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = "%s.tmp-%d" % (path, os.getpid())
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, modo if modo is not None else 0o644)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(texto)
            fh.flush()
            os.fsync(fh.fileno())
        if modo is not None:
            os.chmod(tmp, modo)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def escrever_json_atomico(path, obj, modo=None):
    escrever_atomico(path, json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n", modo)


# ================================================================== referências e caminhos

_CACHE_REFS = {}


def _ref(nome):
    p = os.path.join(REFS, nome)
    if p not in _CACHE_REFS:
        try:
            _CACHE_REFS[p] = json5_load(p)
        except (OSError, ValueError) as e:
            raise Bad("referência ilegível %s: %s" % (p, e))
    return _CACHE_REFS[p]


def carregar_contrato():
    return _ref("contrato.json5")


def carregar_portoes():
    return _ref("portoes.json5")


def carregar_maquina(nivel=None, path=None):
    """Máquina inteira (dict) ou só um nível (`obra`, `task`, `campanha`)."""
    if path:
        try:
            m = json5_load(path)
        except (OSError, ValueError) as e:
            raise Bad("máquina ilegível %s: %s" % (path, e))
    else:
        m = _ref("maquina.json5")
    if nivel is None:
        return m
    try:
        return m["niveis"][nivel]
    except (KeyError, TypeError):
        raise Bad("nível %r ausente na máquina" % nivel)


def ws_real(ws):
    return os.path.realpath(os.path.expanduser(ws))


def paths(ws):
    w = ws_real(ws)
    c = os.path.join(w, ".construcao")
    return {"ws": w, "dir": c, "ledger": os.path.join(c, "ledger.jsonl"), "estado_cache": os.path.join(c, "state.json"),
            "lock": os.path.join(c, "ledger.lock"), "trava_integracao": os.path.join(c, "integracao.lock"),
            "obra": os.path.join(w, "obra.json5"), "pontos": os.path.join(w, "pontos.json5"),
            "plano": os.path.join(w, "PLANO.json5"), "regressao": os.path.join(w, "regressao.json5"),
            "gate_report": os.path.join(w, "gate-report.json"), "baseline": os.path.join(w, "baseline.json"),
            "retomar_md": os.path.join(w, "RETOMAR.md"), "aprovacoes": os.path.join(w, "aprovacoes"),
            "oraculo": os.path.join(w, "oraculo"), "manifest": os.path.join(w, "oraculo", "MANIFEST.json5"),
            "campanha_mae": os.path.join(w, "campanhas", "construcao")}


def audit_path():
    return os.path.realpath(os.path.expanduser(AUDIT_TXT))


def ler_obra(ws):
    p = paths(ws)["obra"]
    try:
        return json5_load(p)
    except (OSError, ValueError):
        return None


def ler_pontos(ws):
    p = paths(ws)["pontos"]
    try:
        return json5_load(p)
    except (OSError, ValueError):
        return None


def _dentro(p, raiz):
    return p == raiz or p.startswith(raiz.rstrip(os.sep) + os.sep)


# ================================================================== ledger

@contextlib.contextmanager
def trava_ledger(ws):
    """Escrita em série no ledger (flock). Não reentrante."""
    p = paths(ws)
    os.makedirs(p["dir"], exist_ok=True)
    fd = os.open(p["lock"], os.O_RDWR | os.O_CREAT, 0o600)
    try:
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def ler_ledger(ws):
    """Registros do ledger. Linha ilegível ⇒ Fail (cadeia quebrada). Ausente ⇒ Bad (obra não inicializada)."""
    p = paths(ws)["ledger"]
    if not os.path.isfile(p):
        raise Bad("obra não inicializada em %s (sem %s); rode `co.py --work <ws> init ...`" % (paths(ws)["ws"], p))
    regs = []
    with open(p, encoding="utf-8") as fh:
        for i, linha in enumerate(fh, 1):
            if not linha.strip():
                continue
            try:
                r = json.loads(linha)
            except ValueError:
                raise Fail("ledger: linha %d não é JSON (cadeia quebrada)" % i)
            if not isinstance(r, dict):
                raise Fail("ledger: linha %d não é objeto (cadeia quebrada)" % i)
            regs.append(r)
    return regs


def hash_registro(rec):
    sem = {k: v for k, v in rec.items() if k != "hash"}
    return hashlib.sha256((str(rec.get("prev")) + canon(sem).decode("utf-8")).encode("utf-8")).hexdigest()


def problemas_cadeia(registros):
    """formatos.ledger.hash.verificar_cadeia. Lista vazia = cadeia íntegra."""
    probs, prev = [], "0"
    for i, r in enumerate(registros, 1):
        if sorted(r.keys()) != sorted(CAMPOS_LEDGER):
            probs.append("registro %d: campos %s" % (i, sorted(r.keys())))
            break
        if r["seq"] != i:
            probs.append("registro %d: seq %r (lacuna ou reordenação)" % (i, r["seq"]))
        if r["prev"] != prev:
            probs.append("seq %s: prev não encadeia no registro anterior" % r["seq"])
        if hash_registro(r) != r["hash"]:
            probs.append("seq %s: hash não confere (registro editado)" % r["seq"])
        if not isinstance(r["payload"], dict) or sha_obj(r["payload"]) != r["payload_hash"]:
            probs.append("seq %s: payload_hash não confere" % r["seq"])
        if not TS_RE.match(str(r["ts"])):
            probs.append("seq %s: ts fora do formato" % r["seq"])
        prev = r["hash"]
    if registros and registros[0].get("evento") != "genese":
        probs.append("seq 1 não é a gênese")
    return probs


def verificar_cadeia(ws):
    try:
        return not problemas_cadeia(ler_ledger(ws))
    except (Fail, Bad):
        return False


def _novo_registro(anterior, evento, ator, nivel, de, para, task, chave, payload):
    payload = {} if payload is None else payload
    r = {"seq": (anterior["seq"] + 1) if anterior else 1, "ts": now_ts(), "ator": ator, "nivel": nivel,
         "evento": evento, "de": de, "para": para, "task": task, "chave": chave, "payload": payload,
         "payload_hash": sha_obj(payload), "prev": anterior["hash"] if anterior else "0"}
    r["hash"] = hash_registro(r)
    return r


def _gravar_registros(ws, registros):
    """Append (uma escrita, fsync) — chamador já detém trava_ledger."""
    p = paths(ws)["ledger"]
    txt = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in registros)
    fd = os.open(p, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, txt.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


def _truncar_ledger(path, tam):
    """V4-9: desfaz um append ainda sob a trava (o ledger volta exatamente ao tamanho anterior)."""
    try:
        fd = os.open(path, os.O_WRONLY)
        try:
            os.ftruncate(fd, tam)
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


def _encadear(ultimo, especs):
    """especs: lista de dicts (evento, ator, nivel, de, para, task, chave, payload) -> registros encadeados."""
    out, ant = [], ultimo
    for e in especs:
        r = _novo_registro(ant, e["evento"], e.get("ator", "script"), e.get("nivel", "operacional"), e.get("de"),
                           e.get("para"), e.get("task"), e.get("chave"), e.get("payload"))
        out.append(r)
        ant = r
    return out


def append_evento(ws, evento, ator, payload, nivel="operacional", de=None, para=None, task=None, chave=None):
    """Grava UM registro (trava + confere a cadeia + fold coerente + pós-gravação). Retorna o seq."""
    with trava_ledger(ws):
        regs = ler_ledger(ws)
        conferir_ledger(ws, regs)
        novos = _encadear(regs[-1] if regs else None, [dict(evento=evento, ator=ator, nivel=nivel, de=de, para=para,
                                                             task=task, chave=chave, payload=payload)])
        fold_registros(regs + novos)  # o registro tem de ser coerente com a máquina antes de ir ao disco
        _gravar_registros(ws, novos)
        pos_gravacao(ws)  # A11: cache + RETOMAR.md sob a mesma trava do append
    return novos[-1]["seq"]


def ultimo_evento(ws, nome):
    for r in reversed(ler_ledger(ws)):
        if r.get("evento") == nome:
            return r
    return None


# ================================================================== guardas (expressões booleanas da máquina)

_TOK = re.compile(r"\s*(?:(\d+)|([A-Za-z_][A-Za-z0-9_]*)|(<=|>=|==|!=|<|>|\(|\)))")
_PALAVRAS = {"and", "or", "not", "true", "false"}


def _tokens(expr):
    toks, i, s = [], 0, expr or ""
    while i < len(s):
        if s[i:].strip() == "":
            break
        m = _TOK.match(s, i)
        if not m or m.end() == i:
            raise ValueError("token inválido em %r na posição %d" % (s, i))
        if m.group(1) is not None:
            toks.append(("num", int(m.group(1))))
        elif m.group(2) is not None:
            toks.append(("id", m.group(2)))
        else:
            toks.append(("op", m.group(3)))
        i = m.end()
    return toks


def parse_guarda(expr):
    """AST de uma guarda: ('or',[..]) ('and',[..]) ('not',x) ('cmp',op,a,b) ('id',n) ('num',n) ('bool',v)."""
    toks = _tokens(expr)
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else (None, None)

    def take():
        t = peek()
        pos[0] += 1
        return t

    def p_or():
        xs = [p_and()]
        while peek() == ("id", "or"):
            take()
            xs.append(p_and())
        return xs[0] if len(xs) == 1 else ("or", xs)

    def p_and():
        xs = [p_not()]
        while peek() == ("id", "and"):
            take()
            xs.append(p_not())
        return xs[0] if len(xs) == 1 else ("and", xs)

    def p_not():
        if peek() == ("id", "not"):
            take()
            return ("not", p_not())
        return p_cmp()

    def p_cmp():
        a = p_prim()
        k, v = peek()
        if k == "op" and v in ("<", "<=", ">", ">=", "==", "!="):
            take()
            return ("cmp", v, a, p_prim())
        return a

    def p_prim():
        k, v = take()
        if k == "op" and v == "(":
            e = p_or()
            if take() != ("op", ")"):
                raise ValueError("parêntese não fechado em %r" % expr)
            return e
        if k == "num":
            return ("num", v)
        if k == "id":
            if v in ("true", "false"):
                return ("bool", v == "true")
            if v in ("and", "or", "not"):
                raise ValueError("operador fora de lugar em %r" % expr)
            return ("id", v)
        raise ValueError("expressão incompleta: %r" % expr)

    if not toks:
        raise ValueError("guarda vazia")
    ast = p_or()
    if pos[0] != len(toks):
        raise ValueError("sobra na guarda %r" % expr)
    return ast


def ids_guarda(ast, acc=None):
    acc = set() if acc is None else acc
    k = ast[0]
    if k == "id":
        acc.add(ast[1])
    elif k in ("or", "and"):
        for x in ast[1]:
            ids_guarda(x, acc)
    elif k == "not":
        ids_guarda(ast[1], acc)
    elif k == "cmp":
        ids_guarda(ast[2], acc)
        ids_guarda(ast[3], acc)
    return acc


def avaliar_ast(ast, valor):
    """Lógica de Kleene: None = indeterminado. valor(nome) -> bool|int|None."""
    k = ast[0]
    if k == "bool":
        return ast[1]
    if k == "num":
        return ast[1]
    if k == "id":
        return valor(ast[1])
    if k == "not":
        v = avaliar_ast(ast[1], valor)
        return None if v is None else (not v)
    if k == "and":
        vs = [avaliar_ast(x, valor) for x in ast[1]]
        if any(v is False for v in vs):
            return False
        return None if any(v is None for v in vs) else True
    if k == "or":
        vs = [avaliar_ast(x, valor) for x in ast[1]]
        if any(v is True for v in vs):
            return True
        return None if any(v is None for v in vs) else False
    if k == "cmp":
        a, b = avaliar_ast(ast[2], valor), avaliar_ast(ast[3], valor)
        if a is None or b is None:
            return None
        op = ast[1]
        return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b, "==": a == b, "!=": a != b}[op]
    raise ValueError("nó desconhecido %r" % (k,))


def avaliar_guarda(nome, ctx):
    """contrato: avaliar_guarda(nome, ctx) -> bool. `nome` = expressão da guarda; ctx = {nome: valor} (ou
    {"valores": {...}}). Identificador ausente ⇒ indeterminado ⇒ False (falha fechada)."""
    valores = ctx.get("valores", ctx) if isinstance(ctx, dict) else {}
    return avaliar_ast(parse_guarda(nome), lambda n: valores.get(n)) is True


# ================================================================== fold (estado derivado)

def _contadores_nivel(maq, nivel):
    return [c for c, d in maq.get("contadores", {}).items() if nivel in (d.get("nivel") or [])]


def _incrementos(t):
    inc = t.get("incrementa")
    if inc is None:
        return []
    return [inc] if isinstance(inc, str) else list(inc)


def destino(niv, no, t):
    """Nó (estado, portao, retorno) de destino de t aplicada a `no` (None se @retorno vazio). Regra comum ao fold
    e ao checador (invariantes.json5#modelo de grafo)."""
    estado, portao, retorno = no
    to = t.get("to")
    if to == "@retorno":
        if not retorno:
            return None
        to = retorno
    transv = niv.get("transversais") or {}
    if to in transv:
        attrs = {"portao": portao, "retorno": retorno}
        for k, v in (t.get("set") or {}).items():
            attrs[k] = estado if v == "@from" else v
        keep = transv[to].get("atributos") or []
        return (to, attrs["portao"] if "portao" in keep else None, attrs["retorno"] if "retorno" in keep else None)
    return (to, None, None)


def aplicavel(t, no):
    if no[0] not in (t.get("from") or []):
        return False
    for k, v in (t.get("requer") or {}).items():
        if {"portao": no[1], "retorno": no[2]}.get(k) != v:
            return False
    return True


def _estado_inicial(maq):
    obra = maq["niveis"]["obra"]
    par = maq.get("paralelismo", {})
    return {"schema_version": 1, "ledger_seq": 0, "ledger_hash": "0" * 64,
            "obra": {"estado": obra["initial"], "portao": None, "retorno": None},
            "contadores": {c: 0 for c in _contadores_nivel(maq, "obra")},
            "constantes": dict(maq.get("constantes", {})), "teto_vigente": par.get("teto_padrao", 5), "vivos": [],
            "tasks": {}, "campanhas": {}, "contrato_hash": None, "oraculo": None, "janela": None,
            "retomar_apos": None, "trava": None, "simulado": False, "hash_estado": None}


def hash_estado(estado):
    """D8: sha256_de_objeto do subconjunto decisório do fold."""
    return sha_obj({k: estado.get(k) for k in CHAVES_HASH_ESTADO})


def _nivel_de_evento(evento):
    if evento.startswith("task."):
        return "task"
    if evento.startswith("campanha."):
        return "campanha"
    return "obra"


def _zerar(maq, st, tnome):
    for c, d in maq.get("contadores", {}).items():
        if tnome in (d.get("zera_em") or []) and c in st["contadores"]:
            st["contadores"][c] = 0


def fold_registros(regs, maq=None):
    """Replica a cadeia na máquina (guardas não são reavaliadas no replay — ESPEC 1). Registro incoerente ⇒ Fail."""
    maq = maq or carregar_maquina()
    st = _estado_inicial(maq)
    niveis = maq["niveis"]
    ops = set((carregar_contrato()["ledger"]["eventos_operacionais"] or {}).keys())
    anterior = None
    for r in regs:
        ev, nivel = r.get("evento"), r.get("nivel")
        if nivel == "operacional":
            if ev not in ops:
                raise Fail("seq %s: evento operacional desconhecido %r" % (r.get("seq"), ev))
            if r.get("ator") != "script" or r.get("de") is not None or r.get("para") is not None:
                raise Fail("seq %s: operacional %r com ator/de/para incoerentes" % (r.get("seq"), ev))
            _fold_operacional(st, r, maq)
        elif nivel in ("obra", "task", "campanha"):
            _fold_transicao(st, r, niveis[nivel], nivel, maq, anterior)
        else:
            raise Fail("seq %s: nível %r inválido" % (r.get("seq"), nivel))
        st["ledger_seq"], st["ledger_hash"] = r["seq"], r["hash"]
        anterior = r
    st["hash_estado"] = hash_estado(st)
    return st


def _fold_operacional(st, r, maq):
    ev, p = r["evento"], r.get("payload") or {}
    if ev == "genese":
        ini = r["ts"]
        st["janela"] = {"inicio": ini, "checkpoint_em": _ts_mais(ini, CHECKPOINT_H)}
        # V4-8: limites do founder (`init --max-rodadas/--teto`) gravados na gênese valem para as guardas;
        # ausentes ⇒ padrão da máquina.
        mr, tt = p.get("max_rodadas"), p.get("teto")
        if isinstance(mr, int) and not isinstance(mr, bool) and mr >= 1:
            st["constantes"]["MAX_RODADAS"] = mr
        if isinstance(tt, int) and not isinstance(tt, bool) and tt >= 1:
            st["teto_vigente"] = tt
    elif ev == "janela_inicio":
        ini = p.get("inicio") or r["ts"]
        st["janela"] = {"inicio": ini, "checkpoint_em": p.get("checkpoint_em") or _ts_mais(ini, CHECKPOINT_H)}
    elif ev == "despachada":
        ch = r.get("chave") or p.get("chave")
        if ch and ch not in st["vivos"]:
            st["vivos"].append(ch)
    elif ev in ("retornou", "perdida", "colhida"):
        ch = r.get("chave") or p.get("chave")
        if ch in st["vivos"]:
            st["vivos"].remove(ch)
    elif ev == "oraculo_congelado":
        st["oraculo"] = {"hash": p.get("hash"), "n_testes": p.get("n_testes"), "n_assercoes": p.get("n_assercoes"),
                         "seq": r["seq"]}
    elif ev == "contrato_hash":
        st["contrato_hash"] = p.get("contrato_hash")
        if isinstance(p.get("max_despachos"), int):
            st["constantes"]["MAX_DESPACHOS"] = p["max_despachos"]
    elif ev == "teto_recuado":
        try:
            st["teto_vigente"] = int(p.get("para", maq.get("paralelismo", {}).get("teto_recuo", 3)))
        except (TypeError, ValueError):
            st["teto_vigente"] = maq.get("paralelismo", {}).get("teto_recuo", 3)
    elif ev == "trava_adquirida":
        st["trava"] = {"dono": p.get("dono"), "seq": r["seq"]}
    elif ev == "trava_liberada":
        st["trava"] = None
    elif ev == "medicao_registrada":
        if p.get("simulated") is True:
            st["simulado"] = True


def _fold_transicao(st, r, niv, nivel, maq, anterior):
    seq, ev = r.get("seq"), r.get("evento")
    if nivel == "obra":
        no = (st["obra"]["estado"], st["obra"]["portao"], st["obra"]["retorno"])
    elif nivel == "task":
        tid = r.get("task")
        if not tid:
            raise Fail("seq %s: evento de task sem `task`" % seq)
        ent = st["tasks"].setdefault(tid, {"estado": niv["initial"], "tentativas": 0, "reaberturas": 0,
                                           "chave": None, "hash_entradas": None, "ultima_rejeicao": None})
        no = (ent["estado"], None, None)
    else:
        nome = r.get("task")
        if not nome:
            raise Fail("seq %s: evento de campanha sem nome (campo task)" % seq)
        ent = st["campanhas"].setdefault(nome, {"estado": niv["initial"], "reintegracoes": 0})
        no = (ent["estado"], None, None)
    if r.get("de") != no[0]:
        raise Fail("seq %s: %s parte de %r mas o estado dobrado é %r" % (seq, ev, r.get("de"), no[0]))
    cand = []
    for tn, t in (niv.get("transitions") or {}).items():
        if t.get("evento") == ev and aplicavel(t, no):
            d = destino(niv, no, t)
            if d is not None and d[0] == r.get("para"):
                cand.append((tn, t, d))
    cand_ator = [c for c in cand if c[1].get("actor") == r.get("ator")]
    if not cand_ator:
        raise Fail("seq %s: transição %s %s→%s (ator %s) não existe em maquina.json5"
                   % (seq, ev, r.get("de"), r.get("para"), r.get("ator")))
    p = r.get("payload") or {}
    if len(cand_ator) > 1:
        # G-1: mesmo (evento, de, para, ator) com portões distintos (rodada_fechada: parar ⇒ entrega, escalar ⇒
        # escalar). O fold distingue pelo que o motor gravou (payload.saida); sem isso o registro é ambíguo e é
        # recusado — nunca se escolhe a primeira candidata (uma escalada não pode abrir o portão de entrega).
        # V4-1: só `saida` (gravada pelo MOTOR) decide; `transicao` no payload é campo de decisão vindo de fora —
        # se aparecer e divergir de `saida`, o registro é incoerente.
        alvo = SAIDA_PARA_TRANSICAO.get(p.get("saida"))
        if "transicao" in p and p.get("transicao") != alvo:
            raise Fail("seq %s: registro %s com payload.transicao=%r divergente de payload.saida=%r (incoerente)"
                       % (seq, ev, p.get("transicao"), p.get("saida")))
        cand_ator = [c for c in cand_ator if c[0] == alvo]
        if len(cand_ator) != 1:
            raise Fail("seq %s: registro %s %s→%s ambíguo (payload.saida=%r não identifica a transição)"
                       % (seq, ev, r.get("de"), r.get("para"), p.get("saida")))
    tn, t, d = cand_ator[0]
    if t.get("actor") == "humano":
        ap = anterior.get("payload") if anterior and anterior.get("evento") == "aprovacao" else None
        if not ap or ap.get("portao") != no[1] or ap.get("decisao") != ev:
            raise Fail("seq %s: transição humana %s sem `aprovacao` imediatamente antes (I6/D9)" % (seq, ev))
    if nivel == "obra":
        st["obra"] = {"estado": d[0], "portao": d[1], "retorno": d[2]}
        for c in _incrementos(t):
            st["contadores"][c] = st["contadores"].get(c, 0) + 1
        for c in t.get("zera") or []:
            st["contadores"][c] = 0
        _zerar(maq, st, tn)
        if ev == "limite_uso":
            st["retomar_apos"] = p.get("retomar_apos")
        elif d[0] not in (niv.get("transversais") or {}):
            st["retomar_apos"] = None
    else:
        ent["estado"] = d[0]
        for c in _incrementos(t):
            ent[c] = ent.get(c, 0) + 1
        for c in t.get("zera") or []:
            ent[c] = 0
        if nivel == "task":
            if r.get("chave"):
                ent["chave"] = r["chave"]
            if ev == "task.verificada" and p.get("motivo_rejeicao"):
                ent["ultima_rejeicao"] = p["motivo_rejeicao"]
            if ev == "task.verificada" and d[0] == "ACEITA" and isinstance(p.get("hash_entradas"), str):
                ent["hash_entradas"] = p["hash_entradas"]  # entradas no aceite (base de hash_entradas_mudou)
            if ev == "task.reabrir" and p.get("hash_entradas_depois"):
                ent["hash_entradas"] = p["hash_entradas_depois"]


SAIDA_PARA_TRANSICAO = {"parar": "parar", "continuar": "continuar_rodada", "escalar": "escalar"}
TRANSICAO_PARA_SAIDA = {v: k for k, v in SAIDA_PARA_TRANSICAO.items()}


def problemas_fim_do_ledger(ws, regs, exigir_cache=True):
    """A8 — truncamento/reescrita do FIM do ledger (a cadeia de hash sozinha não acusa um prefixo íntegro).
    Testemunhas externas ao ledger: (1) cache state.json (`ledger_seq`/`ledger_hash` gravados sob a trava na última
    escrita): seq além do fim ou hash diferente do registro naquele seq ⇒ problema; (2) linhas `tipo aprovacao` do
    audit desta obra (work = ws, ts ≥ gênese): o `seq` tem de existir no ledger e ser um registro `aprovacao` do
    mesmo portão. Lista vazia = ok."""
    probs = []
    n = len(regs)
    cache = paths(ws)["estado_cache"]
    c = None
    if os.path.lexists(cache):
        try:
            with open(cache, encoding="utf-8") as fh:
                c = json.load(fh)
        except (OSError, ValueError):
            c = None
    if exigir_cache and n >= 1:
        # R3-3: ledger não vazio exige a testemunha. Cache ausente, ilegível, `{}` ou sem ledger_seq/ledger_hash
        # válidos ⇒ estado incoerente (apagar o cache não pode ser o jeito de calar a testemunha). Cache ATRASADO
        # (seq menor que o fim, hash conferindo naquele seq) continua legítimo: o fold refaz do ledger.
        cs0 = c.get("ledger_seq") if isinstance(c, dict) else None
        ch0 = c.get("ledger_hash") if isinstance(c, dict) else None
        if not isinstance(c, dict):
            probs.append("state.json (testemunha do fim do ledger) ausente ou ilegível com ledger não vazio "
                         "(%d registros) — estado incoerente" % n)
        elif not (isinstance(cs0, int) and not isinstance(cs0, bool) and cs0 >= 1 and isinstance(ch0, str)
                  and HEX64.match(ch0)):
            probs.append("state.json sem ledger_seq/ledger_hash válidos com ledger não vazio (%d registros) — "
                         "estado incoerente" % n)
    if isinstance(c, dict):
        cs, ch = c.get("ledger_seq"), c.get("ledger_hash")
        if isinstance(cs, int) and not isinstance(cs, bool) and cs > n:
            probs.append("state.json registra ledger_seq %d mas o ledger termina em %d (fim truncado)" % (cs, n))
        elif isinstance(cs, int) and not isinstance(cs, bool) and cs >= 1 and isinstance(ch, str) and \
                HEX64.match(ch) and regs[cs - 1].get("hash") != ch:
            probs.append("state.json registra ledger_hash %s no seq %d e o ledger tem outro (reescrito)"
                         % (ch[:12], cs))
    gen_ts = str(regs[0].get("ts", "")) if regs else ""
    w = ws_real(ws)
    for x in _audit_linhas():
        if not isinstance(x, dict) or x.get("tipo") != "aprovacao" or not x.get("work"):
            continue
        try:
            if ws_real(str(x["work"])) != w:
                continue
        except (TypeError, ValueError):
            continue
        if gen_ts and str(x.get("ts", "")) < gen_ts:
            continue  # obra anterior no mesmo caminho
        s = x.get("seq")
        if not isinstance(s, int) or isinstance(s, bool):
            continue
        r = regs[s - 1] if 1 <= s <= n else None
        if r is None or r.get("evento") != "aprovacao" or \
                (x.get("name") and (r.get("payload") or {}).get("portao") != x.get("name")):
            probs.append("audit registra aprovação %r no seq %s que o ledger não tem (fim truncado/reescrito)"
                         % (x.get("name"), s))
    return probs


def conferir_ledger(ws, regs):
    """Cadeia íntegra + fim não truncado (A8). Fail com a lista de problemas; nada é gravado."""
    probs = problemas_cadeia(regs)
    if probs:
        raise Fail("cadeia do ledger quebrada; nada gravado: " + "; ".join(probs[:5]))
    probs = problemas_fim_do_ledger(ws, regs)
    if probs:
        raise Fail("ledger divergente das testemunhas (state.json/audit); nada gravado: " + "; ".join(probs[:5]))


def ler_ledger_conferido(ws, tentativas=5):
    """Leitura SEM a trava (status, veredito, aprovar antes do desafio): um escritor concorrente pode anexar ao
    ledger e regravar o state.json entre a nossa leitura do ledger e a do cache ⇒ falso "fim truncado". Como toda
    escrita grava o ledger ANTES do cache/audit, reler o ledger depois de ler as testemunhas resolve a corrida;
    truncamento real persiste em todas as releituras e continua Fail."""
    ult = None
    for _ in range(max(1, tentativas)):
        regs = ler_ledger(ws)
        try:
            conferir_ledger(ws, regs)
            return regs
        except Fail as e:
            ult = e
    raise ult


def fold(ws):
    """Estado = fold do ledger. Cadeia quebrada, fim truncado (A8) ou registro incoerente ⇒ Fail."""
    return fold_registros(ler_ledger_conferido(ws))


# ================================================================== átomos das guardas (predicados nomeados)

def _audit_linhas():
    p = audit_path()
    out = []
    try:
        with open(p, encoding="utf-8") as fh:
            for x in fh:
                try:
                    out.append(json.loads(x))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


def hook_selftest_estatico():
    co_hook = os.path.join(SCRIPTS, "co_hook.py")
    if not os.path.isfile(co_hook):
        return False
    try:
        p = subprocess.run([sys.executable, co_hook, "--selftest"], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return False
    return p.returncode == 0


def hook_vivo_no_audit(ws, desde_ts):
    """Linha tool_call BLOQUEADA citando `aprovar __selftest__`, com ts ≥ gênese (ESPEC 4)."""
    for x in _audit_linhas():
        if x.get("tipo") != "tool_call" or x.get("decisao") != "bloqueado":
            continue
        alvo = " ".join(str(x.get("alvo", "")).replace("'", " ").replace('"', " ").split())
        if "aprovar __selftest__" not in alvo:
            continue
        if desde_ts and str(x.get("ts", "")) < desde_ts:
            continue
        return True
    return False


def _gate_report_valido(ws, regs):
    ult = None
    for r in reversed(regs):
        if r.get("evento") == "portao_relatorio":
            ult = r
            break
    p = paths(ws)["gate_report"]
    if ult is None or not os.path.isfile(p):
        return None
    if sha_file(p) != (ult.get("payload") or {}).get("gate_report_hash"):
        return None
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _item_gate(rep, gid):
    if not rep:
        return None
    for it in rep.get("itens") or []:
        if it.get("id") == gid:
            return it.get("status")
    return None


class Contexto(object):
    """Valores das guardas para uma escrita: constantes, contadores do nível e átomos RECALCULADOS da evidência
    (disco/ledger/audit). Ordem (G-2): constante/contador > atomos_definidos (expressão sobre outros átomos) >
    função de ATOMOS (evidência) > injeção. A injeção de um chamador Python confiável (`atomos=`) só completa um
    átomo INJETAVEL cujo cálculo deu indeterminado (None: o artefato que a onda 2–3 produz ainda não existe); nunca
    sobrepõe valor computado, contador, constante, aprovacao_humana (só o canal humano) nem perdida_na_retomada
    (só `retomar`)."""

    def __init__(self, ws, st, regs, payload, nivel="obra", entidade=None, atomos=None, ident=None, humano=False,
                 retomada=False):
        self.ws, self.st, self.regs, self.payload = ws, st, regs, payload or {}
        self.nivel, self.ent, self.atomos = nivel, entidade or {}, dict(atomos or {})
        self.ident = ident if ident is not None else (self.payload.get("task") if nivel == "task" else
                                                      (self.payload.get("campanha") or self.payload.get("task")
                                                       if nivel == "campanha" else None))
        self.humano, self.retomada = bool(humano), bool(retomada)
        self.cache = {}
        self.mem = {}  # cache de leituras de disco desta avaliação

    def valor(self, nome):
        if nome in self.st["constantes"]:
            return self.st["constantes"][nome]
        if self.nivel != "obra" and isinstance(self.ent.get(nome), int) and not isinstance(self.ent.get(nome), bool):
            return self.ent[nome]
        if nome in self.st["contadores"]:
            return self.st["contadores"][nome]
        if nome in ("reaberturas", "reintegracoes", "tentativas"):
            return self.ent.get(nome, 0)
        if nome not in self.cache:
            self.cache[nome] = None  # recursão em atomos_definidos ⇒ indeterminado
            self.cache[nome] = self._computar(nome)
        return self.cache[nome]

    def _computar(self, nome):
        if nome == "aprovacao_humana":
            return self.humano  # I6: só o canal humano (cmd_aprovar) liga
        if nome == "perdida_na_retomada":
            return self.retomada  # só retomar() (vaga aberta achada na retomada) liga
        definidos = atomos_definidos()
        if nome in definidos:
            try:
                return avaliar_ast(parse_guarda(definidos[nome]), self.valor)
            except ValueError:
                return None
        f = ATOMOS.get(nome)
        v = None
        if f is not None:
            try:
                v = f(self)
            except Exception:  # noqa: BLE001 — átomo que falha é indeterminado (falha fechada)
                v = None
            if v is not None:
                return bool(v)
        if nome in self.atomos and nome in ATOMOS_INJETAVEIS and isinstance(self.atomos[nome], bool):
            return self.atomos[nome]
        return None

    # ---- leituras de evidência (cacheadas por avaliação)
    def ler(self, chave, fn):
        if chave not in self.mem:
            try:
                self.mem[chave] = fn()
            except Exception:  # noqa: BLE001
                self.mem[chave] = None
        return self.mem[chave]

    def plano(self):
        return self.ler("plano", lambda: _json5_ou_none(paths(self.ws)["plano"]))

    def obra(self):
        return self.ler("obra", lambda: ler_obra(self.ws))


def _a_hook_vivo(c):
    gen = c.regs[0]["ts"] if c.regs else None
    return hook_vivo_no_audit(c.ws, gen) and hook_selftest_estatico()


def _a_ws_fora(c):
    o = ler_obra(c.ws)
    if not o or not o.get("alvo"):
        return None
    return not _dentro(ws_real(c.ws), os.path.realpath(o["alvo"]))


def _a_pontos_completos(c):
    p = ler_pontos(c.ws)
    if not p or not isinstance(p.get("pontos"), list):
        return False
    st_ok = ("aberto", "coberto", "atendido", "fora_do_escopo", "rejeitado")
    return bool(p["pontos"]) and all(isinstance(x, dict) and x.get("id") and x.get("texto") and
                                     x.get("status") in st_ok for x in p["pontos"])


def _a_stop_numerico(c):
    o = ler_obra(c.ws) or {}
    n = (o.get("stop") or {}).get("numerico")
    return isinstance(n, dict) and bool(n.get("metrica")) and n.get("op") in (">=", "<=", "==") and \
        isinstance(n.get("valor"), (int, float))


def _a_limite(c):
    return c.payload.get("causa") in ("rate_limit", "janela", "outro") and parse_ts(c.payload.get("retomar_apos")) \
        is not None


def _a_agora_apos(c):
    d = parse_ts(c.st.get("retomar_apos"))
    if d is None:
        return None
    return datetime.datetime.now(datetime.timezone.utc) >= d


def _a_tipo_baseline(c):
    o = ler_obra(c.ws) or {}
    if not o.get("tipo"):
        return None
    return o["tipo"] in carregar_contrato().get("tipos_exigem_baseline", [])


def _a_ha_decisoes(c):
    try:
        pl = json5_load(paths(c.ws)["plano"])
    except (OSError, ValueError):
        return None
    return bool(pl.get("decisoes"))


def _a_todas_ret(c):
    return all(t.get("estado") in ("RETORNADA", "ACEITA", "DESCARTADA") for t in c.st["tasks"].values())


def _a_retomar_md_valido(c):
    try:
        with open(paths(c.ws)["retomar_md"], encoding="utf-8") as fh:
            primeira = fh.readline()
    except OSError:
        return False
    m = re.search(r"ledger_hash=([0-9a-f]{64})", primeira)
    return bool(m) and m.group(1) == c.st["ledger_hash"]


def _a_pass3_final(c):
    for r in reversed(c.regs):
        if r.get("evento") == "medicao_registrada":
            p = r.get("payload") or {}
            if p.get("final") is True and isinstance(p.get("k"), int) and p["k"] >= 3 and not p.get("simulated"):
                return True
    return False


GATES_RUN_COMPLETO = ["G%d" % i for i in range(15)]  # G0..G14 (co_portao.CHECAGENS)
GATES_NUCLEO = ("G0", "G1", "G3", "G4")  # sempre aplicáveis, sem waiver (A2)
VEREDITOS_ENTREGA = ("GO", "GO (com waiver)")  # "GO (simulado)" NUNCA satisfaz entrega/regressão (A5)


def problemas_waivers(ws, regs, rep):
    """Itens WAIVED do relatório cuja aprovação não vale (mesma regra de co_portao.problema_waiver: JSON em
    <ws>/aprovacoes/ com decisao aprovado + seq, evento `aprovacao` nesse seq do mesmo portão e arquivo, linha de
    audit fora do ws). co_portao indisponível ⇒ todo WAIVED é recusado (falha fechada)."""
    out = []
    try:
        import co_portao
        fn = co_portao.problema_waiver
    except Exception:  # noqa: BLE001
        fn = None
    for i in (rep or {}).get("itens") or []:
        if isinstance(i, dict) and i.get("status") == "WAIVED":
            prob = fn(ws, i.get("aprovacao"), regs, item=i.get("id")) if fn else \
                "co_portao.problema_waiver indisponível"
            if prob:
                out.append("%s: %s" % (i.get("id"), prob))
    return out


def relatorio_satisfaz_entrega(rep, ws=None, regs=None):
    """(bool, motivo). Um gate-report só conta como regressão GO / entrega quando é de um run COMPLETO
    (`only` presente e null), `final` true, veredito exatamente "GO" ou "GO (com waiver)" (nunca "GO (simulado)"),
    sem item FAIL/ERRO, com G0..G14 todos presentes e o núcleo G0/G1/G3/G4 em PASS (A1/A5)."""
    if not isinstance(rep, dict):
        return False, "gate-report ausente ou ilegível"
    if "only" not in rep or rep.get("only") not in (None,):
        return False, "relatório parcial (portao run --only %s) não conta como regressão/entrega" % rep.get("only")
    if rep.get("final") is not True:
        return False, "relatório não final"
    if rep.get("simulado") is True or rep.get("simulated") is True:
        return False, "relatório simulado"
    if rep.get("veredito") not in VEREDITOS_ENTREGA:
        return False, "veredito %r não é GO real (%s)" % (rep.get("veredito"), " | ".join(VEREDITOS_ENTREGA))
    itens = {}
    for i in rep.get("itens") or []:
        if isinstance(i, dict):
            itens[i.get("id")] = i.get("status")
    ruins = sorted(g for g, s in itens.items() if s in ("FAIL", "ERRO"))
    if ruins:
        return False, "itens FAIL/ERRO: %s" % ", ".join(str(x) for x in ruins)
    faltam = [g for g in GATES_RUN_COMPLETO if g not in itens]
    if faltam:
        return False, "run incompleto: faltam %s" % ", ".join(faltam)
    nucleo = [g for g in GATES_NUCLEO if itens.get(g) != "PASS"]
    if nucleo:
        return False, "núcleo sem PASS: %s" % ", ".join(nucleo)
    if ws is not None:
        # V4-7: o alvo mudou depois do portão ⇒ o relatório é obsoleto e não entrega (mesma regra do veredito).
        try:
            import co_portao
            obs = co_portao.problema_relatorio_obsoleto(ws, rep)
        except Exception as e:  # noqa: BLE001 — falha fechada
            obs = "conferência de relatório obsoleto indisponível (%s)" % e
        if obs:
            return False, obs
    if any(s == "WAIVED" for s in itens.values()):
        if ws is None:
            return False, "WAIVED sem workspace para conferir a aprovação"
        probs = problemas_waivers(ws, regs or [], rep)
        if probs:
            return False, "waiver sem aprovação válida: %s" % "; ".join(probs)
    return True, "ok"


def relatorio_parcial_ajustado(rep):
    """Para co_portao (frente C) chamar ANTES de gravar gate-report.json: um relatório com `only` não nulo nunca
    sai com `final: true` (A1: `final` e `GO` não andam juntos num relatório parcial). Retorna o próprio dict."""
    if isinstance(rep, dict) and rep.get("only"):
        rep["final"] = False
    return rep


def aprovacoes_sem_audit(ws, regs):
    """R3-10 (mesma regra de co_portao.aprovacoes_sem_audit): cada `aprovacao` do ledger precisa da linha
    `tipo aprovacao` no audit (mesmo seq + work = ws) e de nenhuma tool_call permitida que a tenha feito.
    Retorna a lista de referências (arquivo ou "seq N") sujas; [] = limpo."""
    linhas = [x for x in _audit_linhas() if isinstance(x, dict)]
    w = ws_real(ws)

    def _mesmo_ws(x):
        try:
            return bool(x) and ws_real(str(x)) == w
        except (TypeError, ValueError):
            return False

    sujas = []
    for r in regs:
        if r.get("evento") != "aprovacao":
            continue
        pl = r.get("payload") or {}
        ref = pl.get("arquivo") or "seq %s" % r.get("seq")
        ok = any(a.get("tipo") == "aprovacao" and a.get("seq") == r.get("seq") and _mesmo_ws(a.get("work"))
                 for a in linhas)
        tool = any(a.get("tipo") == "tool_call" and a.get("decisao") == "permitido"
                   and "aprovar" in (a.get("tokens") or []) and w in str(a.get("alvo", ""))
                   and str(pl.get("portao", "\0")) in str(a.get("alvo", "")) for a in linhas)
        if not ok or tool:
            sujas.append(ref)
    return sujas


def _a_veredito_go_final(c):
    rep = _gate_report_valido(c.ws, c.regs)
    if not rep:
        return None
    if aprovacoes_sem_audit(c.ws, c.regs):
        return False  # R3-10: aprovação no ledger sem audit não satisfaz entrega
    return relatorio_satisfaz_entrega(rep, c.ws, c.regs)[0]


def _a_regressao_go(c):
    rep = _gate_report_valido(c.ws, c.regs)
    if not rep:
        return None
    return relatorio_satisfaz_entrega(rep, c.ws, c.regs)[0]


def _a_gate_falhou(gid):
    def f(c):
        s = _item_gate(_gate_report_valido(c.ws, c.regs), gid)
        return None if s is None else s in ("FAIL", "ERRO")
    return f


def _a_gate_passou(gid):
    def f(c):
        s = _item_gate(_gate_report_valido(c.ws, c.regs), gid)
        return None if s is None else s == "PASS"
    return f


# ------------------------------------------------------------------ G-8: átomos recalculados da EVIDÊNCIA
# Princípio do founder: o produto recalcula da evidência (arquivo em disco, cadeia do ledger, audit), não confia em
# payload/evento que um agente poderia gravar. Convenção tri-valorada: True/False quando a evidência existe;
# None (indeterminado) quando o artefato que a produz ainda não existe na obra (ex.: baseline.json, comparacao.json,
# campanha do ac.py, relatório da frente) — aí, e só aí, a injeção de chamador confiável completa (G-2).

PROTEGIDOS_REL = (".construcao", "aprovacoes", "oraculo")


def _json5_ou_none(path):
    try:
        return json5_load(path)
    except (OSError, ValueError):
        return None


def _json_ou_none(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _overlap(a, b):
    try:
        return bool(_ac().globs_overlap(a, b))
    except Exception:  # noqa: BLE001 — sem o ac.py, aproximação conservadora: sobrepõe
        return True


def _globs_sobrepoem(xs, ys):
    return any(_overlap(a, b) for a in xs for b in ys)


def _regs_evento(c, nome, desde=0):
    return [r for r in c.regs if r.get("evento") == nome and r.get("seq", 0) > desde]


def _ultimo_reg(c, nome, nivel=None):
    for r in reversed(c.regs):
        if r.get("evento") == nome and (nivel is None or r.get("nivel") == nivel):
            return r
    return None


def _seq_entrada(c, estado):
    """seq do último registro de transição de obra que ENTROU em `estado` (0 se nunca)."""
    for r in reversed(c.regs):
        if r.get("nivel") == "obra" and r.get("para") == estado:
            return r.get("seq", 0)
    return 0


def _tasks_plano(c):
    pl = c.plano()
    if not isinstance(pl, dict) or not isinstance(pl.get("tasks"), list):
        return None
    return {t.get("id"): t for t in pl["tasks"] if isinstance(t, dict) and t.get("id")}


def _lista_str(x, vazia_ok=True):
    return isinstance(x, list) and (vazia_ok or bool(x)) and all(isinstance(i, str) and i.strip() for i in x)


def _task_valida(t, ids):
    """formatos.plano: campos obrigatórios da task, deps existentes, writes fora dos protegidos."""
    if not isinstance(t, dict):
        return False
    for k in ("id", "titulo", "construtor", "criterio"):
        if not isinstance(t.get(k), str) or not t[k].strip():
            return False
    if not _lista_str(t.get("writes"), vazia_ok=False) or not _lista_str(t.get("cenarios"), vazia_ok=False):
        return False
    if not _lista_str(t.get("deps", []), vazia_ok=True) or any(d not in ids or d == t["id"] for d in t.get("deps", [])):
        return False
    for w in t["writes"]:
        if _write_toca_protegido(w):
            return False
    return True


def _write_toca_protegido(w):
    """True se o glob de escrita é absoluto, escapa da raiz (`..`) ou começa num protegido (.construcao,
    aprovacoes, oraculo) — com normalização real do caminho (`./`, `a/../`, `//`, `\\`) e sem diferença de caixa
    (APFS/NTFS). Glob no 1º componente que casa um protegido (ex.: `.constru*`) também conta; os amplos `*`/`**`
    ficam com a regra de writes amplos (portão humano do plano)."""
    s = w.replace("\\", "/").strip()
    if not s or s.startswith("/") or s.startswith("~") or re.match(r"^[A-Za-z]:", s):
        return True
    n = posixpath.normpath(s)
    if n == ".." or n.startswith("../"):
        return True
    raiz = n.split("/", 1)[0].lower()
    if raiz in PROTEGIDOS_REL:
        return True
    if raiz not in ("*", "**", ".") and any(ch in raiz for ch in "*?["):
        return any(fnmatch.fnmatchcase(p, raiz) for p in PROTEGIDOS_REL)
    return False


def _construtores(c, tid=None):
    """agent_types construtores (PLANO.task.construtor + `despachada` papel construtor) da task ou de todas."""
    out = set()
    tp = _tasks_plano(c) or {}
    for i, t in tp.items():
        if (tid is None or i == tid) and isinstance(t.get("construtor"), str):
            out.add(t["construtor"])
    for r in _regs_evento(c, "despachada"):
        p = r.get("payload") or {}
        if p.get("papel") == "construtor" and (tid is None or p.get("task") == tid) and p.get("agent_type"):
            out.add(p["agent_type"])
    return out


def _vivos_payloads(c, excluir_task=None):
    desp = {}
    for r in _regs_evento(c, "despachada"):
        desp[r.get("chave") or (r.get("payload") or {}).get("chave")] = r.get("payload") or {}
    out = []
    for ch in c.st.get("vivos") or []:
        p = desp.get(ch) or {}
        if excluir_task and p.get("task") == excluir_task:
            continue
        out.append(p)
    return out


def _lote(c):
    """Tasks PRONTA do fold (o lote que `lote_ok` despacharia). Vazio ⇒ None (não há lote a julgar)."""
    ids = sorted(tid for tid, t in c.st["tasks"].items() if t.get("estado") == "PRONTA")
    return ids or None


# ---- PLANO / brief / deps / disjunção

def _a_plano_valido(c):
    pl = c.plano()
    if pl is None:
        return None
    if not isinstance(pl, dict) or not isinstance(pl.get("tasks"), list) or not pl["tasks"]:
        return False
    if not isinstance(pl.get("decisoes", None), list) or not isinstance(pl.get("contrato", None), dict):
        return False
    for d in pl["decisoes"]:
        if not isinstance(d, dict) or not d.get("id") or not str(d.get("texto") or "").strip() or \
                not isinstance(d.get("opcoes"), list) or not d.get("recomendacao"):
            return False
    ids = [t.get("id") for t in pl["tasks"] if isinstance(t, dict)]
    if len(ids) != len(pl["tasks"]) or len(set(ids)) != len(ids):
        return False
    tasks = {t["id"]: t for t in pl["tasks"]}
    if not all(_task_valida(t, tasks) for t in pl["tasks"]):
        return False
    # DAG acíclico
    estado = {}

    def ciclo(n):
        if estado.get(n) == 1:
            return True
        if estado.get(n) == 2:
            return False
        estado[n] = 1
        if any(ciclo(d) for d in tasks[n].get("deps", [])):
            return True
        estado[n] = 2
        return False
    if any(ciclo(n) for n in tasks):
        return False
    # writes de tasks distintas disjuntos (ac.py globs_overlap)
    lst = list(tasks.values())
    for i in range(len(lst)):
        for j in range(i + 1, len(lst)):
            if _globs_sobrepoem(lst[i]["writes"], lst[j]["writes"]):
                return False
    man = _json5_ou_none(paths(c.ws)["manifest"])
    if isinstance(man, dict):
        autores = set()
        for f in (man.get("frentes") or {}).values():
            if isinstance(f, dict):
                autores |= set(x for x in (f.get("autores") or []) if isinstance(x, str))
        if any(t["construtor"] in autores for t in lst):
            return False
    return True


def _a_brief_valido(c):
    tp = _tasks_plano(c)
    if tp is None:
        return None
    t = tp.get(c.ident)
    return bool(t) and _task_valida(t, tp)


def _deps_ok(c, tid, tp):
    t = tp.get(tid)
    if not t:
        return False
    return all((c.st["tasks"].get(d) or {}).get("estado") == "ACEITA" for d in (t.get("deps") or []))


def _a_deps_aceitas(c):
    tp = _tasks_plano(c)
    if tp is None:
        return None
    if c.nivel == "task":
        return _deps_ok(c, c.ident, tp)
    lote = _lote(c)
    if lote is None:
        return None
    return all(_deps_ok(c, tid, tp) for tid in lote)


def _a_lote_disjunto(c):
    tp = _tasks_plano(c)
    lote = _lote(c)
    if tp is None or lote is None:
        return None
    if any(tid not in tp for tid in lote):
        return False
    vivos = []
    for p in _vivos_payloads(c):
        vivos += [x for x in (p.get("writes") or []) + (p.get("reads") or []) if isinstance(x, str)]
    for i, a in enumerate(lote):
        wa = tp[a].get("writes") or []
        if _globs_sobrepoem(wa, vivos):
            return False
        for b in lote[i + 1:]:
            if _globs_sobrepoem(wa, tp[b].get("writes") or []):
                return False
    return True


def _a_writes_disjuntos_dos_vivos(c):
    tp = _tasks_plano(c)
    if tp is None:
        return None
    t = tp.get(c.ident)
    if not t:
        return False
    outros = []
    for p in _vivos_payloads(c, excluir_task=c.ident):
        outros += [x for x in (p.get("writes") or []) + (p.get("reads") or []) if isinstance(x, str)]
    return not _globs_sobrepoem(t.get("writes") or [], outros)


def _a_obra_replanejou(c):
    if not _regs_evento(c, "novo_plano"):
        return False
    tp = _tasks_plano(c)
    if tp is None:
        return None
    return c.ident not in tp


def hash_entradas_task(ws, st, tid, plano=None):
    """sha256 das ENTRADAS de uma task: entrada do PLANO + hash do oráculo congelado + contrato_hash do fold.
    None se o PLANO ou a task não existem (indeterminado)."""
    pl = plano if plano is not None else _json5_ou_none(paths(ws)["plano"])
    if not isinstance(pl, dict):
        return None
    t = None
    for x in pl.get("tasks") or []:
        if isinstance(x, dict) and x.get("id") == tid:
            t = x
    if t is None:
        return None
    return sha_obj({"task": t, "oraculo": (st.get("oraculo") or {}).get("hash"), "contrato": st.get("contrato_hash")})


def _a_hash_entradas_mudou(c):
    antes = c.ent.get("hash_entradas")
    agora = hash_entradas_task(c.ws, c.st, c.ident, c.plano())
    if antes is None or agora is None:
        return None
    return agora != antes


# ---- orçamento / rejeições / comparações

def _horas_desde_genese(c):
    d = parse_ts(c.regs[0].get("ts")) if c.regs else None
    if d is None:
        return None
    return (datetime.datetime.now(datetime.timezone.utc) - d).total_seconds() / 3600.0


def _a_orcamento_esgotado(c):
    o = c.obra()
    if not isinstance(o, dict):
        return None
    esg = c.st["contadores"].get("despachos", 0) >= c.st["constantes"].get("MAX_DESPACHOS", 30)
    mh = o.get("max_horas")
    if isinstance(mh, (int, float)) and not isinstance(mh, bool):
        h = _horas_desde_genese(c)
        if h is None:
            return None
        esg = esg or h >= float(mh)
    return esg


def _a_orcamento_restante(c):
    v = _a_orcamento_esgotado(c)
    return None if v is None else (not v)


def _campanhas_ativas(c, excluir=None):
    return [n for n, e in c.st["campanhas"].items() if e.get("estado") in ("ATIVA", "PRONTA_INTEGRAR") and n != excluir]


def _a_campanhas_ativas_abaixo_de_2(c):
    teto = carregar_contrato().get("paralelismo", {}).get("max_campanhas_ativas", 2)
    return len(_campanhas_ativas(c, excluir=c.ident)) < teto


def _rejeicoes(c, tid):
    out = []
    for r in c.regs:
        if r.get("evento") == "task.verificada" and r.get("task") == tid and r.get("para") == "REJEITADA":
            out.append(" ".join(str((r.get("payload") or {}).get("motivo_rejeicao") or "").lower().split()))
    return out


def _mesma_2x(rs):
    return len(rs) >= 2 and bool(rs[-1]) and rs[-1] == rs[-2]


def _a_mesma_rejeicao_2x(c):
    if c.nivel == "task":
        return _mesma_2x(_rejeicoes(c, c.ident))
    return any(_mesma_2x(_rejeicoes(c, tid)) for tid in c.st["tasks"])


def _comparacoes(c):
    raiz = os.path.join(paths(c.ws)["ws"], "rodadas")
    out = []
    try:
        nomes = os.listdir(raiz)
    except OSError:
        return out
    for n in nomes:
        if not n.isdigit():
            continue
        d = _json_ou_none(os.path.join(raiz, n, "comparacao.json"))
        if isinstance(d, dict):
            out.append((int(n), d))
    return [d for _, d in sorted(out, key=lambda x: x[0])]


def _deltas(cs):
    out = []
    for d in cs:
        q = d.get("Q") or {}
        v = q.get("delta")
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return None
        out.append(float(v))
    return out


def _a_oscilacao(c):
    cs = _comparacoes(c)
    if not cs:
        return None
    ds = _deltas(cs)
    if ds is None:
        return False
    sinais = [1 if x > 0 else -1 for x in ds if x != 0]
    return len(sinais) >= 2 and sinais[-1] != sinais[-2]


def _a_plato_2(c):
    cs = _comparacoes(c)
    if not cs:
        return None
    if len(cs) < 2:
        return False
    for d in cs[-2:]:
        q = d.get("Q") or {}
        v = q.get("delta")
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return False
        if v > 0 and q.get("rotulo") not in ("sem efeito", "piora"):
            return False
    return True


# ---- medição

def _runs_dir(c):
    return os.path.join(paths(c.ws)["ws"], "rodadas")


def _run_json(c, rid):
    raiz = _runs_dir(c)
    try:
        rodadas = sorted(os.listdir(raiz))
    except OSError:
        return None
    for n in rodadas:
        d = _json_ou_none(os.path.join(raiz, n, "runs", str(rid), "run.json"))
        if isinstance(d, dict):
            return d
    return None


def _ultima_medicao(c, config="sistema"):
    for r in reversed(c.regs):
        if r.get("evento") == "medicao_registrada" and (r.get("payload") or {}).get("config") == config:
            return r
    return None


def _runs_da_medicao(c, rec):
    ids = (rec.get("payload") or {}).get("run_ids")
    if not isinstance(ids, list) or not ids:
        return None
    runs = [_run_json(c, i) for i in ids]
    return None if any(r is None for r in runs) else runs


def _a_copia_limpa(c):
    rec = _ultima_medicao(c)
    if rec is None:
        return None
    runs = _runs_da_medicao(c, rec)
    if runs is None:
        return False
    return all(r.get("copia_limpa") is True for r in runs)


def hash_sistema(alvo):
    """formatos.convencoes.hash_sistema: ac.py sha_files(arquivos do produto no alvo, sem .git)."""
    alvo = os.path.realpath(alvo)
    files = []
    for raiz, dirs, arqs in os.walk(alvo):
        dirs[:] = sorted(d for d in dirs if d not in (".git", "__pycache__"))
        files += [os.path.join(raiz, a) for a in arqs if not a.endswith(".pyc")]
    return _ac().sha_files(sorted(files))


def _a_sistema_congelado(c):
    rec = _ultima_medicao(c)
    if rec is None:
        return None
    p = rec.get("payload") or {}
    runs = _runs_da_medicao(c, rec)
    if runs is None:
        return False
    for r in runs:
        if r.get("sistema_hash_inicio") != r.get("sistema_hash_fim") or r.get("sistema_hash_inicio") != p.get(
                "sistema_hash"):
            return False
    o = c.obra() or {}
    if not o.get("alvo") or not os.path.isdir(o["alvo"]):
        return None
    return hash_sistema(o["alvo"]) == p.get("sistema_hash")


def _a_medicao_posterior_ao_merge(c):
    rec = _ultima_medicao(c)
    if rec is None:
        return None
    merges = [r for r in c.regs if r.get("evento") == "merge_ok" and r.get("nivel") == "obra"]
    ult = merges[-1]["seq"] if merges else None
    if ult is not None and rec["seq"] < ult:
        return False
    return (rec.get("payload") or {}).get("seq_ultimo_merge") == ult


def _a_baseline_reprodutivel(c):
    b = _json_ou_none(paths(c.ws)["baseline"])
    if b is None:
        return None
    if not isinstance(b, dict) or b.get("dispensado") is not False or not str(b.get("cmd") or "").strip():
        return False
    k, ids = b.get("k"), b.get("run_ids")
    if not isinstance(k, int) or isinstance(k, bool) or k < 1 or not isinstance(ids, list) or len(ids) != k:
        return False
    ora = c.st.get("oraculo") or {}
    if not ora.get("hash") or b.get("oraculo_hash") != ora.get("hash"):
        return False
    rec = _ultima_medicao(c, "baseline")
    if rec is None or sorted((rec.get("payload") or {}).get("run_ids") or []) != sorted(ids) or \
            (rec.get("payload") or {}).get("simulated"):
        return False
    runs = [_run_json(c, i) for i in ids]
    if any(r is None for r in runs):
        return False
    qs = set()
    for r in runs:
        if r.get("config") != "baseline" or r.get("sistema_hash_inicio") != r.get("sistema_hash_fim"):
            return False
        qs.add(json.dumps(r.get("quality"), sort_keys=True))
    return len(qs) == 1  # reprodutível: as k execuções dão o mesmo [Q]


def _metrica_medida(c, metrica):
    rec = None
    for r in reversed(c.regs):
        p = r.get("payload") or {}
        if r.get("evento") == "medicao_registrada" and p.get("config") == "sistema" and p.get("final") is True \
                and not p.get("simulated"):
            rec = r
            break
    if rec is None:
        return None
    p = rec["payload"]
    if metrica in p and isinstance(p[metrica], (int, float)):
        return float(p[metrica])
    m = re.match(r"^pass_(hat|at)_(\d+)$", metrica or "")
    if m:
        if not isinstance(p.get("k"), int) or p["k"] < int(m.group(2)):
            return None
        v = p.get("pass_%s_k" % m.group(1))
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None
    for d in reversed(_comparacoes(c)):
        if isinstance(d.get(metrica), (int, float)):
            return float(d[metrica])
    return None


def _a_criterio_parada_ok(c):
    o = c.obra() or {}
    n = (o.get("stop") or {}).get("numerico")
    if not isinstance(n, dict) or n.get("op") not in (">=", "<=", "==") or not isinstance(n.get("valor"), (int, float)):
        return None
    v = _metrica_medida(c, n.get("metrica"))
    if v is None:
        return None
    alvo = float(n["valor"])
    return {">=": v >= alvo, "<=": v <= alvo, "==": v == alvo}[n["op"]]


# ---- pontos

def _pontos_lista(c):
    p = ler_pontos(c.ws)
    if not isinstance(p, dict) or not isinstance(p.get("pontos"), list):
        return None
    return [x for x in p["pontos"] if isinstance(x, dict)]


def _a_pontos_atualizados(c):
    ps = _pontos_lista(c)
    if not ps:
        return None
    snap = _ultimo_reg(c, "premissas_ok", "obra")
    ids_antes = set(((snap or {}).get("payload") or {}).get("pontos_ids") or [])
    ids = set(x.get("id") for x in ps)
    if not ids_antes <= ids:
        return False  # G14: ponto que já apareceu sumiu
    rodada = c.st["contadores"].get("rodada", 0) + 1
    for x in ps:
        if x.get("status") not in ("aberto", "coberto", "atendido", "fora_do_escopo", "rejeitado"):
            return False
        hist = x.get("historico")
        if not isinstance(hist, list) or not any(isinstance(h, dict) and h.get("rodada") == rodada and
                                                 h.get("status") == x.get("status") for h in hist):
            return False
    return True


# ---- oráculo (MANIFEST + arquivos)

def _oraculo_arquivos(c):
    """(arquivos, manifest) do MANIFEST; None se o MANIFEST não existe."""
    def ler():
        if not os.path.isfile(paths(c.ws)["manifest"]):
            return None
        try:
            return arquivos_do_oraculo(c.ws)
        except Fail:
            return ([], _json5_ou_none(paths(c.ws)["manifest"]) or {})
    return c.ler("oraculo_arquivos", ler)


def _manifest_integro(c, man):
    ult = _ultimo_reg(c, "manifest_gravado")
    if ult is None or not isinstance(man, dict):
        return False
    doc = {"schema_version": 1, "frentes": man.get("frentes"), "construtores": man.get("construtores") or {},
           "congelado": man.get("congelado")}
    return sha_obj(doc) == (ult.get("payload") or {}).get("manifest_hash")


def _a_autor_fora_dos_construtores(c):
    r = _oraculo_arquivos(c)
    if r is None:
        return None
    _files, man = r
    if not _manifest_integro(c, man):
        return False  # MANIFEST que não é o gravado por `oraculo manifest` (D5)
    frentes = man.get("frentes") or {}
    if not frentes:
        return False
    for fid, f in frentes.items():
        autores = set(x for x in (f.get("autores") or []) if isinstance(x, str)) if isinstance(f, dict) else set()
        if not autores:
            return False
        cons = _construtores(c, fid)
        mc = (man.get("construtores") or {}).get(fid)
        if isinstance(mc, str):
            cons.add(mc)
        if cons & autores:
            return False
    return True


_CLASSE_RE = re.compile(r"#\s*cenario:\s*(C-\d+)\b.*?\bclasse:\s*([QS])\b")
_TESTE_RE = re.compile(r"^\s*def\s+test\w*\s*\(", re.M)


def _classificacoes(files):
    """(n_testes_py, n_classificados_py, cenarios_citados, casos_ok)"""
    nt = ncl = 0
    cen, casos_ok = set(), True
    for f in files:
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                src = fh.read()
        except OSError:
            casos_ok = False
            continue
        if f.endswith(".py"):
            nt += len(_TESTE_RE.findall(src))
            achados = _CLASSE_RE.findall(src)
            ncl += len(achados)
            cen |= set(x[0] for x in achados)
        elif f.endswith(".json"):
            try:
                d = json.loads(src)
            except ValueError:
                casos_ok = False
                continue
            if not isinstance(d, dict) or d.get("classe") not in ("Q", "S") or not re.match(r"^C-\d+$",
                                                                                        str(d.get("cenario"))):
                casos_ok = False
            else:
                cen.add(d["cenario"])
    return nt, ncl, cen, casos_ok


def _a_criterios_classificados(c):
    r = _oraculo_arquivos(c)
    if r is None:
        return None
    files, _man = r
    if not files:
        return False
    nt, ncl, cen, casos_ok = _classificacoes(files)
    return casos_ok and bool(cen) and ncl >= nt


def _a_pontos_cobertos(c):
    r = _oraculo_arquivos(c)
    if r is None:
        return None
    files, _man = r
    ps = _pontos_lista(c)
    if not files or not ps:
        return False
    _nt, _ncl, cen, _ok = _classificacoes(files)
    for x in ps:
        if x.get("status") in ("fora_do_escopo", "rejeitado"):
            continue
        cs = x.get("cenarios")
        if not isinstance(cs, list) or not cs or any(cc not in cen for cc in cs):
            return False
    return True


def _copia_alvo(alvo, destino, stub=False):
    for raiz, dirs, arqs in os.walk(alvo):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        rel = os.path.relpath(raiz, alvo)
        os.makedirs(os.path.join(destino, rel), exist_ok=True)
        for a in arqs:
            src, dst = os.path.join(raiz, a), os.path.join(destino, rel, a)
            eh_teste = a.startswith("test") or a == "conftest.py" or rel.split(os.sep)[0] in ("tests", "test")
            if stub and a.endswith(".py") and not eh_teste:
                with open(dst, "w", encoding="utf-8") as fh:
                    fh.write("")  # produto vazio: o stub
            elif not a.endswith(".pyc"):
                with open(src, "rb") as fi, open(dst, "wb") as fo:
                    fo.write(fi.read())


def _oraculo_vermelho_em(alvo, testes, stub):
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="co-vacuo-")
    try:
        copia = os.path.join(tmp, "alvo")
        _copia_alvo(alvo, copia, stub=stub)
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([copia, os.path.join(copia, "src")])
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        for t in testes:
            try:
                p = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", os.path.dirname(t), "-p",
                                    os.path.basename(t), "-t", os.path.dirname(t)], cwd=copia, env=env,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   timeout=120)
            except (OSError, subprocess.SubprocessError):
                return None
            if p.returncode == 0:
                return False  # o oráculo passa no baseline/stub: vácuo
        return True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _a_vermelho_baseline_e_stub(c):
    """O oráculo (testes .py do MANIFEST) tem de REPROVAR o alvo atual (baseline: nada foi construído ainda) e um
    stub (cópia limpa do alvo com o produto .py esvaziado). Passar em qualquer um ⇒ oráculo vácuo ⇒ False."""
    r = _oraculo_arquivos(c)
    if r is None:
        return None
    files, _man = r
    testes = [f for f in files if f.endswith(".py") and os.path.basename(f).startswith("test")]
    if not testes:
        return None if not files else False
    o = c.obra() or {}
    alvo = o.get("alvo")
    if not alvo or not os.path.isdir(alvo):
        return None
    base = _oraculo_vermelho_em(alvo, testes, stub=False)
    if base is not True:
        return base
    return _oraculo_vermelho_em(alvo, testes, stub=True)


# ---- integração (trava, merge, oráculo após merge)

def _travas_desde_integrar(c):
    s = _seq_entrada(c, "INTEGRAR")
    return [r for r in c.regs if r.get("evento") == "trava_adquirida" and r.get("seq", 0) > s]


def _a_merge_ordenado(c):
    ts = _travas_desde_integrar(c)
    if not ts:
        return None
    donos = [str((r.get("payload") or {}).get("dono") or "") for r in ts]
    return all(donos) and all(donos[i] < donos[i + 1] for i in range(len(donos) - 1))


def _a_oraculo_apos_cada_merge(c):
    ts = _travas_desde_integrar(c)
    if not ts:
        return None
    rels = [r.get("seq", 0) for r in c.regs if r.get("evento") == "portao_relatorio"]
    for i, t in enumerate(ts):
        fim = ts[i + 1]["seq"] if i + 1 < len(ts) else float("inf")
        if not any(t["seq"] < s < fim for s in rels):
            return False
    return True


# ---- task: relatório, verificação, worktree

def _retornou_da_task(c):
    ch = c.payload.get("chave") if isinstance(c.payload.get("chave"), str) else c.ent.get("chave")
    if not ch:
        return None
    for r in reversed(c.regs):
        if r.get("evento") == "retornou" and (r.get("chave") or (r.get("payload") or {}).get("chave")) == ch:
            return r
    return None


def _relatorio(c):
    """(ok_integro, dict|None): relatório da frente apontado por `retornou`, conferido pelo hash."""
    r = _retornou_da_task(c)
    if r is None:
        return None
    p = r.get("payload") or {}
    arq = p.get("relatorio")
    if not isinstance(arq, str) or not os.path.isfile(arq):
        return (None, None)
    if sha_file(arq) != p.get("relatorio_hash"):
        return (False, None)
    d = _json_ou_none(arq)
    if not isinstance(d, dict):
        return (False, None)
    return (True, d)


def _a_relatorio_presente(c):
    rel = _relatorio(c)
    if rel is None:
        return None
    ok, d = rel
    if not ok:
        return False
    return d.get("task") in (None, c.ident) and isinstance(d.get("files_changed"), list)


def _a_testes_vermelho_verde(c):
    rel = _relatorio(c)
    if rel is None or rel[0] is None:
        return None
    ok, d = rel
    if not ok:
        return False
    ts = d.get("testes")
    if not isinstance(ts, list) or not ts:
        return False
    # o relatório do construtor não se valida sozinho: tem de ser DESTA task/vaga (task e chave do `retornou`) e
    # cada teste tem de cobrir um cenário da task no PLANO, com comando declarado.
    ret = _retornou_da_task(c) or {}
    ch = ret.get("chave") or (ret.get("payload") or {}).get("chave")
    if d.get("task") not in (None, c.ident) or (d.get("chave") is not None and d.get("chave") != ch):
        return False
    tp = (_tasks_plano(c) or {}).get(c.ident) if c.ident else None
    cen = set(tp.get("cenarios") or []) if isinstance(tp, dict) and isinstance(tp.get("cenarios"), list) else None
    for t in ts:
        if not (isinstance(t, dict) and isinstance(t.get("exit_antes"), int) and not isinstance(t["exit_antes"], bool)
                and t["exit_antes"] != 0 and t.get("exit_depois") == 0 and not isinstance(t.get("exit_depois"), bool)
                and isinstance(t.get("cmd"), str) and t["cmd"].strip()):
            return False
        if cen is not None and t.get("cenario") not in cen:
            return False
    return True


def _a_verificador_nao_autor(c):
    if c.nivel == "task":
        # O nome do verificador vem do payload, mas é conferido contra a evidência registrada: falso se ele é
        # construtor da task (PLANO ou `despachada`), autor do relatório da frente, ou despachado no ledger com
        # outro papel; se o ledger registra verificador(es) despachado(s) para esta task depois do `retornou`, o
        # nome do payload tem de ser um deles (onda 1: sem registro, vale o payload — gerado/motor.py).
        v = c.payload.get("verificador")
        if not isinstance(v, str) or not v.strip():
            return None
        if v in _construtores(c, c.ident):
            return False
        rel = _relatorio(c)
        if rel and rel[0] and isinstance(rel[1], dict) and rel[1].get("agent_type") == v:
            return False
        registrados = set()
        ret = _retornou_da_task(c)
        desde = ret.get("seq", 0) if ret else 0
        for r in _regs_evento(c, "despachada"):
            p = r.get("payload") or {}
            if p.get("agent_type") == v and p.get("papel") != "verificador":
                return False
            if r.get("seq", 0) > desde and p.get("papel") == "verificador" and p.get("task") == c.ident \
                    and p.get("agent_type"):
                registrados.add(p["agent_type"])
        return not registrados or v in registrados
    s = max(_seq_entrada(c, "INTEGRAR"), _seq_entrada(c, "VERIFICAR") - 1)
    vs = set()
    for r in _regs_evento(c, "despachada", desde=s):
        p = r.get("payload") or {}
        if p.get("papel") == "verificador" and p.get("agent_type"):
            vs.add(p["agent_type"])
    if not vs:
        return None
    return not (vs & _construtores(c))


def _a_resultado_no_worktree(c):
    ch = c.payload.get("chave") if isinstance(c.payload.get("chave"), str) else c.ent.get("chave")
    desp = None
    for r in _regs_evento(c, "despachada"):
        if (r.get("chave") or (r.get("payload") or {}).get("chave")) == ch:
            desp = r
    if desp is None:
        return None
    if (desp.get("payload") or {}).get("isolation") != "worktree":
        return False  # sem worktree não há resultado em worktree
    for r in _regs_evento(c, "colhida"):
        if (r.get("chave") or (r.get("payload") or {}).get("chave")) == ch and (r.get("payload") or {}).get("diff_hash"):
            return True
    return None  # worktree declarado; inspeção do worktree é da onda 2 (`colhida`)


# ---- campanhas (ac.py, <ws>/campanhas/<nome>/.auto-correcao/)

def _camp_dir(c, nome):
    return os.path.join(paths(c.ws)["ws"], "campanhas", str(nome))


def _camp_state(c, nome):
    return c.ler("camp:" + str(nome), lambda: _json_ou_none(os.path.join(_camp_dir(c, nome), ".auto-correcao",
                                                                         "state.json")))


def _camp_rodada(c, nome, arq):
    st = _camp_state(c, nome)
    if not isinstance(st, dict):
        return None
    d = os.path.join(_camp_dir(c, nome), ".auto-correcao", "rounds", str(st.get("round", 0)), arq)
    if arq.endswith(".jsonl"):
        out = []
        try:
            with open(d, encoding="utf-8") as fh:
                for x in fh:
                    try:
                        out.append(json.loads(x))
                    except ValueError:
                        continue
        except OSError:
            return None
        return out
    return _json5_ou_none(d)


def _oraculo_campanha_ok(c, nome):
    st = _camp_state(c, nome)
    if not isinstance(st, dict):
        return None
    o = st.get("oracle") or {}
    files = o.get("files") or []
    if not o.get("hash") or not files or not all(isinstance(f, str) and os.path.isfile(f) for f in files):
        return False
    return _ac().sha_files(sorted(files)) == o["hash"]


def _a_oraculo_campanha_congelado(c):
    return _oraculo_campanha_ok(c, c.ident)


def _a_ac_decisao_parar(c):
    st = _camp_state(c, c.ident)
    if not isinstance(st, dict):
        return None
    dec = str(st.get("decision") or "").strip().lower()
    return dec.startswith("parar") and bool((st.get("done") or {}).get("decisao.1"))


def _a_oraculos_fechados_verdes(c):
    ok = _oraculo_campanha_ok(c, c.ident)
    if ok is not True:
        return ok
    runs = _camp_rodada(c, c.ident, "runs.jsonl")
    sis = [r for r in (runs or []) if isinstance(r, dict) and r.get("config") == "sistema" and not r.get("simulated")]
    if not sis:
        return False
    q = sis[-1].get("quality") or {}
    return isinstance(q.get("total"), int) and q["total"] > 0 and q.get("passed") == q["total"]


def _camp_escreve(c, nome):
    pl = _camp_rodada(c, nome, "PLANO.json5")
    if not isinstance(pl, dict):
        return None
    out = []
    for f in pl.get("frentes") or []:
        if isinstance(f, dict):
            out += [x for x in (f.get("escreve") or []) if isinstance(x, str)]
    return out


def _a_colisao_vazia(c):
    meus = _camp_escreve(c, c.ident)
    if meus is None:
        return None
    outros = []
    for n in _campanhas_ativas(c, excluir=c.ident):
        outros += _camp_escreve(c, n) or []
    for p in _vivos_payloads(c):
        outros += [x for x in (p.get("writes") or []) if isinstance(x, str)]
    return not _globs_sobrepoem(meus, outros)


def _campanhas_abertas(c):
    raiz = os.path.join(paths(c.ws)["ws"], "campanhas")
    try:
        nomes = sorted(n for n in os.listdir(raiz) if n != "construcao")
    except OSError:
        return []
    return [n for n in nomes if isinstance(_camp_state(c, n), dict)]


def _defeitos(c, nome):
    d = _camp_rodada(c, nome, "DEFEITOS.json5")
    return (d.get("defeitos") if isinstance(d, dict) and isinstance(d.get("defeitos"), list) else None)


def _a_defeitos_classificados(c):
    cs = _campanhas_abertas(c)
    if not cs:
        return None
    for n in cs:
        ds = _defeitos(c, n)
        if not ds:
            return False
        for d in ds:
            if not isinstance(d, dict) or not d.get("id") or d.get("classe") not in (
                    "sistema", "oraculo", "ambiente", "executor") or (d["classe"] == "sistema" and not d.get("frente")):
                return False
    return True


def _a_so_sistema_vira_task(c):
    cs = _campanhas_abertas(c)
    if not cs:
        return None
    for n in cs:
        ds = {d.get("id"): d for d in (_defeitos(c, n) or []) if isinstance(d, dict)}
        pl = _camp_rodada(c, n, "PLANO.json5")
        if not ds or not isinstance(pl, dict):
            return False
        for f in pl.get("frentes") or []:
            for did in (f.get("defeitos") or []) if isinstance(f, dict) else []:
                if (ds.get(did) or {}).get("classe") != "sistema":
                    return False
    return True


def _a_teste_falha_antes(c):
    cs = _campanhas_abertas(c)
    if not cs:
        return None
    for n in cs:
        ds = [d for d in (_defeitos(c, n) or []) if isinstance(d, dict) and d.get("classe") == "sistema"]
        if not ds or not all(d.get("reproduzido") is True and d.get("evidencia") for d in ds):
            return False
        runs = [r for r in (_camp_rodada(c, n, "runs.jsonl") or []) if isinstance(r, dict)]
        q = [(r.get("quality") or {}) for r in runs]
        if not any(isinstance(x.get("total"), int) and isinstance(x.get("passed"), int) and x["passed"] < x["total"]
                   for x in q):
            return False  # nenhuma execução registrada mostra o vermelho antes da correção
    return True


_ATOMOS_DEF = {}


def atomos_definidos(maq=None):
    """maquina.niveis.*.atomos_definidos (nome -> expressão sobre outros átomos), de todos os níveis."""
    if maq is None and _ATOMOS_DEF:
        return _ATOMOS_DEF
    out = {}
    for niv in (maq or carregar_maquina())["niveis"].values():
        out.update(niv.get("atomos_definidos") or {})
    if maq is None:
        _ATOMOS_DEF.update(out)
    return out


ATOMOS = {
    "aprovacao_humana": lambda c: c.humano,  # só `aprovar` (canal humano) liga — I6 (Contexto trata antes)
    "hook_vivo": _a_hook_vivo,
    "workspace_fora_do_alvo": _a_ws_fora,
    "pontos_completos": _a_pontos_completos,
    "stop_numerico": _a_stop_numerico,
    "motivo_registrado": lambda c: bool(str(c.payload.get("motivo") or "").strip()),
    "evidencia_registrada": lambda c: bool(str(c.payload.get("evidencia") or "").strip()),
    "limite_detectado": _a_limite,
    "agora_apos_retomar": _a_agora_apos,
    "sem_perdidas_pendentes": lambda c: not c.st["vivos"],
    "lote_cabe_no_teto": lambda c: len(c.st["vivos"]) < c.st["teto_vigente"],
    "vivos_abaixo_do_teto": lambda c: len(c.st["vivos"]) < c.st["teto_vigente"],
    "nenhuma_em_voo": lambda c: not any(t.get("estado") == "EM_VOO" for t in c.st["tasks"].values()),
    "todas_tasks_retornadas_ou_aceitas": _a_todas_ret,
    "trava_adquirida": lambda c: c.st.get("trava") is not None,
    "oraculo_congelado": lambda c: c.st.get("oraculo") is not None,
    "tipo_exige_baseline": _a_tipo_baseline,
    "ha_decisoes": _a_ha_decisoes,
    "retomar_md_valido": _a_retomar_md_valido,
    "pass3_final": _a_pass3_final,
    "veredito_go_final": _a_veredito_go_final,
    "portao_regressao_go": _a_regressao_go,
    "g3_reprovou": _a_gate_falhou("G3"),
    "g4_reprovou": _a_gate_falhou("G4"),
    "diff_no_territorio": _a_gate_passou("G3"),
    # G-8 — os 35 que antes só entravam por injeção, agora recalculados da evidência
    "ac_decisao_parar": _a_ac_decisao_parar,
    "autor_fora_dos_construtores": _a_autor_fora_dos_construtores,
    "baseline_reprodutivel": _a_baseline_reprodutivel,
    "brief_valido": _a_brief_valido,
    "campanhas_ativas_abaixo_de_2": _a_campanhas_ativas_abaixo_de_2,
    "colisao_vazia": _a_colisao_vazia,
    "copia_limpa": _a_copia_limpa,
    "criterio_parada_ok": _a_criterio_parada_ok,
    "criterios_classificados": _a_criterios_classificados,
    "defeitos_classificados": _a_defeitos_classificados,
    "deps_aceitas": _a_deps_aceitas,
    "hash_entradas_mudou": _a_hash_entradas_mudou,
    "lote_disjunto": _a_lote_disjunto,
    "medicao_posterior_ao_merge": _a_medicao_posterior_ao_merge,
    "merge_ordenado": _a_merge_ordenado,
    "mesma_rejeicao_2x": _a_mesma_rejeicao_2x,
    "obra_replanejou": _a_obra_replanejou,
    "oraculo_apos_cada_merge": _a_oraculo_apos_cada_merge,
    "oraculo_campanha_congelado": _a_oraculo_campanha_congelado,
    "oraculos_fechados_verdes": _a_oraculos_fechados_verdes,
    "orcamento_esgotado": _a_orcamento_esgotado,
    "orcamento_restante": _a_orcamento_restante,
    "oscilacao": _a_oscilacao,
    "plano_valido": _a_plano_valido,
    "plato_2": _a_plato_2,
    "pontos_atualizados": _a_pontos_atualizados,
    "pontos_cobertos": _a_pontos_cobertos,
    "relatorio_presente": _a_relatorio_presente,
    "resultado_no_worktree": _a_resultado_no_worktree,
    "sistema_congelado_na_medicao": _a_sistema_congelado,
    "so_sistema_vira_task": _a_so_sistema_vira_task,
    "teste_falha_antes": _a_teste_falha_antes,
    "verificador_nao_autor": _a_verificador_nao_autor,
    "vermelho_baseline_e_stub": _a_vermelho_baseline_e_stub,
    "writes_disjuntos_dos_vivos": _a_writes_disjuntos_dos_vivos,
    # componentes de atomos_definidos.verificacao_ok (G-3)
    "testes_vermelho_verde": _a_testes_vermelho_verde,
}
ATOMOS_G8 = ("ac_decisao_parar", "autor_fora_dos_construtores", "baseline_reprodutivel", "brief_valido",
             "campanhas_ativas_abaixo_de_2", "colisao_vazia", "copia_limpa", "criterio_parada_ok",
             "criterios_classificados", "defeitos_classificados", "deps_aceitas", "hash_entradas_mudou",
             "lote_disjunto", "medicao_posterior_ao_merge", "merge_ordenado", "mesma_rejeicao_2x", "obra_replanejou",
             "oraculo_apos_cada_merge", "oraculo_campanha_congelado", "oraculos_fechados_verdes", "orcamento_esgotado",
             "orcamento_restante", "oscilacao", "plano_valido", "plato_2", "pontos_atualizados", "pontos_cobertos",
             "relatorio_presente", "resultado_no_worktree", "sistema_congelado_na_medicao", "so_sistema_vira_task",
             "teste_falha_antes", "verificador_nao_autor", "vermelho_baseline_e_stub", "writes_disjuntos_dos_vivos")
# G-2: átomos que o motor declara NÃO computáveis no estado em que a evidência ainda não existe (o cálculo dá None
# porque o artefato da onda 2–3 — baseline.json, comparacao.json, relatório da frente, campanha do ac.py, MANIFEST,
# PLANO — não existe). Só eles aceitam injeção de chamador Python confiável, e só quando o cálculo deu None.
# Os átomos da cadeia/ledger e os "do disco" da onda 1 (hook_vivo, lote_cabe_no_teto, oraculo_congelado,
# retomar_md_valido, ...) NUNCA aceitam injeção; aprovacao_humana e perdida_na_retomada só pelos seus canais.
ATOMOS_SO_EVIDENCIA = ("hook_vivo", "workspace_fora_do_alvo", "pontos_completos", "stop_numerico",
                       "motivo_registrado", "evidencia_registrada", "limite_detectado", "agora_apos_retomar",
                       "sem_perdidas_pendentes", "lote_cabe_no_teto", "vivos_abaixo_do_teto", "nenhuma_em_voo",
                       "todas_tasks_retornadas_ou_aceitas", "trava_adquirida", "oraculo_congelado",
                       "tipo_exige_baseline", "ha_decisoes", "retomar_md_valido", "pass3_final", "veredito_go_final",
                       "portao_regressao_go", "g3_reprovou", "g4_reprovou", "diff_no_territorio", "aprovacao_humana",
                       "perdida_na_retomada", "verificacao_ok", "campanhas_ativas_abaixo_de_2", "mesma_rejeicao_2x",
                       "orcamento_esgotado", "orcamento_restante")
ATOMOS_INJETAVEIS = frozenset(a for a in tuple(ATOMOS_G8) + ("testes_vermelho_verde",)
                              if a not in ATOMOS_SO_EVIDENCIA)


def valor_atomo(ws, nome, evento=None, payload=None, task=None):
    """API para a frente C (e diagnóstico): valor tri-valorado (True/False/None) de um átomo RECALCULADO da evidência
    no estado atual (fold), sem injeção. `evento` escolhe o nível (task./campanha.), `task` o id da entidade."""
    payload = dict(payload or {})
    if task:
        payload.setdefault("task", task)
        payload.setdefault("campanha", task)
    regs = ler_ledger_conferido(ws)
    st = fold_registros(regs)
    nivel = _nivel_de_evento(evento or "")
    ident = payload.get("task") if nivel == "task" else (payload.get("campanha") if nivel == "campanha" else None)
    ent = (st["tasks"].get(ident) if nivel == "task" else st["campanhas"].get(ident) if nivel == "campanha"
           else None) or {}
    return Contexto(ws, st, regs, payload, nivel, ent, None, ident=ident).valor(nome)


# ================================================================== transição (escrita guardada)

def _eventos_conhecidos(maq):
    out = {}
    for nivel, niv in maq["niveis"].items():
        for tn, t in (niv.get("transitions") or {}).items():
            out.setdefault(t["evento"], []).append((nivel, tn, t))
    return out


def eventos_humanos(maq=None):
    maq = maq or carregar_maquina()
    return sorted({t["evento"] for niv in maq["niveis"].values() for t in (niv.get("transitions") or {}).values()
                   if t.get("actor") == "humano"})


def _candidatas(maq, st, evento, payload):
    nivel = _nivel_de_evento(evento)
    niv = maq["niveis"][nivel]
    if nivel == "obra":
        no, ent, ident = (st["obra"]["estado"], st["obra"]["portao"], st["obra"]["retorno"]), None, None
    elif nivel == "task":
        ident = payload.get("task")
        if not ident or not isinstance(ident, str):
            raise Bad("evento de task exige `task` no --payload (ex.: {\"task\": \"T-01\"})")
        ent = st["tasks"].get(ident) or {"estado": niv["initial"], "tentativas": 0, "reaberturas": 0}
        no = (ent["estado"], None, None)
    else:
        ident = payload.get("campanha") or payload.get("task")
        if not ident or not isinstance(ident, str):
            raise Bad("evento de campanha exige `campanha` no --payload")
        ent = st["campanhas"].get(ident) or {"estado": niv["initial"], "reintegracoes": 0}
        no = (ent["estado"], None, None)
    cands = []
    for tn, t in (niv.get("transitions") or {}).items():
        if t.get("evento") == evento and aplicavel(t, no):
            d = destino(niv, no, t)
            if d is not None:
                cands.append((tn, t, d))
    return nivel, niv, no, ent, ident, cands


def _efeitos(ws, st, nivel, tn, t, payload, reg_trans):
    """Registros operacionais que a mesma chamada grava após a transição (efeitos da máquina)."""
    out = []
    par = carregar_maquina().get("paralelismo", {})
    if t.get("evento") == "limite_uso" and payload.get("causa") == "rate_limit" and \
            st["teto_vigente"] > par.get("teto_recuo", 3):  # teto do founder ≤ recuo ⇒ nada a recuar
        out.append(dict(evento="teto_recuado", payload={"de": st["teto_vigente"], "para": par.get("teto_recuo", 3),
                                                        "seq_limite_uso": reg_trans["seq"]}))
    if t.get("evento") == "plano_ok":
        try:
            pl = json5_load(paths(ws)["plano"])
            n = len(pl.get("tasks") or [])
        except (OSError, ValueError):
            n = 0
        out.append(dict(evento="contrato_hash", payload={
            "contrato_hash": sha_file(os.path.join(REFS, "contrato.json5")),
            "plano_hash": sha_file(paths(ws)["plano"]) if os.path.isfile(paths(ws)["plano"]) else None,
            "max_despachos": st["constantes"].get("MAX_TENTATIVAS", 3) * max(n, 1)}))
    return out


def _janela_expirada(st):
    j = st.get("janela") or {}
    fim = _ts_mais(j.get("inicio"), JANELA_H) if j.get("inicio") else None
    return fim is not None and now_ts() >= fim


def _registro_janela():
    ini = now_ts()
    return dict(evento="janela_inicio", payload={"inicio": ini, "checkpoint_em": _ts_mais(ini, CHECKPOINT_H),
                                                 "fim": _ts_mais(ini, JANELA_H)})


def _explicar(ast_txt, ctx):
    try:
        nomes = sorted(ids_guarda(parse_guarda(ast_txt)))
    except ValueError:
        return ""
    partes = []
    for n in nomes:
        v = ctx.valor(n)
        partes.append("%s=%s" % (n, "indeterminado" if v is None else v))
    return ", ".join(partes)


def hashes_do_disco(ws, evento, payload):
    """R3-5: em `premissas_ok` (obra_hash, pontos_hash, pontos_ids) e `plano_ok` (plano_hash, regressao_hash) o
    MOTOR calcula os campos dos arquivos em disco no momento do evento; o que vier no payload é descartado
    (sobrescrito). Arquivo ausente ⇒ campo ausente (a guarda/G-check acusa). Muta e retorna `payload`."""
    p = paths(ws)
    if evento == "premissas_ok":
        campos = (("obra_hash", p["obra"]), ("pontos_hash", p["pontos"]))
    elif evento == "plano_ok":
        campos = (("plano_hash", p["plano"]), ("regressao_hash", p["regressao"]))
    else:
        return payload
    for campo, arq in campos:
        payload.pop(campo, None)
        if os.path.isfile(arq):
            payload[campo] = sha_file(arq)
    if evento == "premissas_ok":
        payload.pop("pontos_ids", None)
        pts = ler_pontos(ws)
        if isinstance(pts, dict) and isinstance(pts.get("pontos"), list):
            payload["pontos_ids"] = [x.get("id") for x in pts["pontos"] if isinstance(x, dict) and x.get("id")]
    return payload


def payload_do_motor(ws, st, evento, tn, payload, ctx):
    """Campos de payload que o MOTOR decide (não o agente): rodada_fechada.saida/criterio_parada_ok/plato_2/
    comparacao_hash (G-1: o fold distingue parar × escalar por `saida`), task.verificada.verificacao_ok e
    hash_entradas (no aceite), task.reabrir.hash_entradas_antes/depois. Muta e retorna `payload`."""
    if evento == "rodada_fechada" and tn in TRANSICAO_PARA_SAIDA:
        payload["saida"] = TRANSICAO_PARA_SAIDA[tn]
        payload["criterio_parada_ok"] = ctx.valor("criterio_parada_ok")
        payload["plato_2"] = ctx.valor("plato_2")
        comp = None
        raiz = os.path.join(paths(ws)["ws"], "rodadas")
        try:
            ns = sorted((int(n) for n in os.listdir(raiz) if n.isdigit()), reverse=True)
        except OSError:
            ns = []
        for n in ns:
            arq = os.path.join(raiz, str(n), "comparacao.json")
            if os.path.isfile(arq):
                comp = sha_file(arq)
                break
        payload["comparacao_hash"] = comp
    elif evento == "task.verificada":
        payload["verificacao_ok"] = tn == "aceitar"
        payload.pop("hash_entradas", None)
        if tn == "aceitar":
            he = hash_entradas_task(ws, st, ctx.ident, ctx.plano())
            if he:
                payload["hash_entradas"] = he
    elif evento == "task.reabrir":
        payload["hash_entradas_antes"] = ctx.ent.get("hash_entradas")
        payload["hash_entradas_depois"] = hash_entradas_task(ws, st, ctx.ident, ctx.plano())
    return payload


CAMPOS_DECISAO_MOTOR = ("transicao", "saida", "criterio_parada_ok", "plato_2", "comparacao_hash", "verificacao_ok",
                        "hash_entradas", "hash_entradas_antes", "hash_entradas_depois")


def transicionar(ws, evento, payload=None, atomos=None, _humano=None):
    """Aplica `evento` se exatamente uma guarda aplicável for verdadeira; grava transição + efeitos numa escrita.
    Guarda falsa ⇒ Fail (nada gravado). `_humano` = dict do canal humano (uso interno de cmd_aprovar)."""
    payload = dict(payload or {})
    for campo in CAMPOS_DECISAO_MOTOR:  # V4-1: a decisão é do motor; o que vier do agente é descartado
        payload.pop(campo, None)
    maq = carregar_maquina()
    with trava_ledger(ws):
        regs = ler_ledger(ws)
        conferir_ledger(ws, regs)
        st = fold_registros(regs, maq)
        hashes_do_disco(ws, evento, payload)  # R3-5: sob a trava, do disco; payload do agente não escolhe hash
        if _humano and _humano.get("hash_estado") and st["hash_estado"] != _humano["hash_estado"]:
            # A10: reconfere DENTRO da trava, depois do desafio — o estado aprovado tem de ser o estado gravado
            raise Fail("hash_estado mudou durante a aprovação (TOCTOU) — nada gravado; rode de novo")
        nivel, niv, no, ent, ident, cands = _candidatas(maq, st, evento, payload)
        if not cands:
            raise Fail("evento %r não sai do estado atual %s (portao=%s); nada gravado" % (evento, no[0], no[1]))
        ctx = Contexto(ws, st, regs, payload, nivel, ent, atomos, ident=ident, humano=bool(_humano))
        verdade, detalhes = [], []
        for tn, t, d in cands:
            if t.get("motivo_obrigatorio") and not str(payload.get("motivo") or "").strip():
                raise Bad("transição %s exige --motivo (motivo_obrigatorio)" % tn)
            try:
                v = avaliar_ast(parse_guarda(t.get("guard", "false")), ctx.valor)
            except ValueError as e:
                raise Bad("guarda ilegível em %s: %s" % (tn, e))
            detalhes.append("%s [%s] ⇒ %s (%s)" % (tn, t.get("guard"), "indeterminada" if v is None else v,
                                                   _explicar(t.get("guard"), ctx)))
            if v is True:
                verdade.append((tn, t, d))
        if not verdade:
            raise Fail("guarda falsa; ledger inalterado:\n  " + "\n  ".join(detalhes))
        if len(verdade) > 1:
            raise Bad("não determinismo (I5): %s" % ", ".join(x[0] for x in verdade))
        tn, t, d = verdade[0]
        if (t.get("actor") == "humano") != bool(_humano):
            raise Bad("transição humana só por `co.py aprovar` (I6/D9)")
        payload_do_motor(ws, st, evento, tn, payload, ctx)
        especs = []
        if _janela_expirada(st):
            especs.append(_registro_janela())
        if _humano:
            pap = _humano["payload_aprovacao"]
            if callable(pap):  # seq da aprovação calculado sob a trava
                pap = pap(regs[-1]["seq"] + 1 + len(especs))
            especs.append(dict(evento="aprovacao", payload=pap))
        chave = payload.get("chave") if isinstance(payload.get("chave"), str) else None
        especs.append(dict(evento=evento, ator=t.get("actor"), nivel=nivel, de=no[0], para=d[0],
                           task=ident, chave=chave, payload=payload))
        novos = _encadear(regs[-1], especs)
        st_depois = fold_registros(regs + novos, maq)
        extras = _efeitos(ws, st_depois, nivel, tn, t, payload, novos[-1])
        if extras:
            novos += _encadear(novos[-1], extras)
            st_depois = fold_registros(regs + novos, maq)
        if _humano and callable(_humano.get("efeito")):
            # efeito da transição humana (ex.: oraculo_aprovado ⇒ ac.py oracle freeze + oraculo_congelado, A9)
            mais = _humano["efeito"](tn, novos, st_depois) or []
            if mais:
                novos += _encadear(novos[-1], mais)
                st_depois = fold_registros(regs + novos, maq)
        desfazer = (_humano or {}).get("desfazer")
        if _humano and "antes_de_gravar" in _humano:
            _humano["antes_de_gravar"](novos)  # arquivo de aprovação (falha ⇒ nada no ledger, nada no audit)
        lp = paths(ws)["ledger"]
        tam = os.path.getsize(lp)
        try:
            _gravar_registros(ws, novos)
            if _humano and callable(_humano.get("depois_de_gravar")):
                _humano["depois_de_gravar"](novos)  # V4-9: audit por último; falha ⇒ ledger volta ao tamanho anterior
        except BaseException:
            _truncar_ledger(lp, tam)
            if callable(desfazer):
                desfazer()
            raise
        pos_gravacao(ws)  # A11
    return {"transicao": tn, "de": no[0], "para": d[0], "registros": novos, "estado": st_depois}


# ================================================================== pós-gravação: cache, RETOMAR.md, aprovar-*.sh

def pos_gravacao(ws):
    """Roda SÓ logo após uma escrita, sob a trava, cuja pré-condição já conferiu o ledger (conferir_ledger); por
    isso aqui o cache pode estar atrasado ou ainda não existir (gênese) — exigir_cache=False."""
    regs = ler_ledger(ws)
    probs = problemas_cadeia(regs) + problemas_fim_do_ledger(ws, regs, exigir_cache=False)
    if probs:
        raise Fail("ledger divergente após a escrita: " + "; ".join(probs[:5]))
    st = fold_registros(regs)
    p = paths(ws)
    escrever_json_atomico(p["estado_cache"], st)
    gerar_retomar_md(ws, st)
    if st["obra"]["estado"] == "AGUARDANDO_HUMANO" and st["obra"]["portao"]:
        gerar_aprovar_sh(ws, st)
    return st


def gerar_aprovar_sh(ws, st):
    w = ws_real(ws)
    portao = st["obra"]["portao"]
    linhas = ["#!/bin/sh",
              "# portão: %s | estado: AGUARDANDO_HUMANO | hash_estado: %s" % (portao, st["hash_estado"]),
              "# retorno: %s | ledger_seq: %s" % (st["obra"]["retorno"] or "—", st["ledger_seq"]),
              "# Rode no SEU terminal (o agente NUNCA executa este arquivo). Escolha UMA linha e redigite o desafio."]
    for dec in ("aprovado", "rejeitado", "abandonar"):
        linhas.append("# %s --work %s aprovar %s --decisao %s" % (CO_TXT, w, portao, dec))
    path = os.path.join(paths(ws)["aprovacoes"], "aprovar-%s.sh" % portao)
    escrever_atomico(path, "\n".join(linhas) + "\n", modo=0o600)
    return path


def proximo_comando(ws, st):
    w = ws_real(ws)
    e, portao = st["obra"]["estado"], st["obra"]["portao"]
    base = "%s --work %s " % (CO_TXT, w)
    tabela = {
        "INICIO": "ev iniciar", "PREMISSAS": "pontos check",
        "ORACULO": "oraculo manifest --manifest <arquivo-fora-de-protegidos>",
        "BASELINE": "medir --config baseline --k 3", "PLANO": "plano check --plano %s" % paths(ws)["plano"],
        "LOTE": "lote proximo", "DESPACHADO": "lote retornar <task> --relatorio <arquivo>",
        "INTEGRAR": "trava integracao acquire --dono <task>", "VERIFICAR": "portao run",
        "MEDIR": "medir --k 3", "CORRIGIR": "ev campanhas_abertas", "FECHAR_RODADA": "ev rodada_fechada",
        "REPLANEJAR": "plano check --plano %s" % paths(ws)["plano"], "PAUSADO": "ev retomar",
        "ENTREGUE": "status", "ABANDONADO": "status",
    }
    if st["vivos"] and e not in ("ENTREGUE", "ABANDONADO"):
        return base + "retomar"
    if e == "AGUARDANDO_HUMANO":
        return base + "aprovar %s --decisao aprovado" % (portao or "<portao>")
    if e == "INICIO" and not hook_vivo_no_audit(ws, None):
        return base + "hook selftest --vivo"
    return base + tabela.get(e, "status")


def gerar_retomar_md(ws, st=None):
    st = st or fold(ws)
    obra = ler_obra(ws) or {}
    pontos = ler_pontos(ws) or {}
    c, k = st["contadores"], st["constantes"]
    o = st["obra"]
    nome = os.path.basename(ws_real(ws))
    if o["estado"] == "AGUARDANDO_HUMANO":
        pend = "portão %s — aprovação SÓ no terminal do humano: %s" % (
            o["portao"], os.path.join(paths(ws)["aprovacoes"], "aprovar-%s.sh" % o["portao"]))
    elif o["estado"] == "PAUSADO":
        pend = "pausado até %s (retorno: %s)" % (st["retomar_apos"] or "—", o["retorno"] or "—")
    else:
        pend = "nenhum"
    ora = st["oraculo"]
    ora_txt = ("congelado %s (%s testes, %s asserções, seq %s)" % (ora["hash"], ora["n_testes"], ora["n_assercoes"],
                                                                  ora["seq"])) if ora else "não congelado"
    stop = obra.get("stop") or {}
    num = stop.get("numerico")
    parada = ("%s %s %s" % (num.get("metrica"), num.get("op"), num.get("valor"))) if isinstance(num, dict) \
        else (stop.get("texto") or "—")
    em_voo = [ch for ch in st["vivos"]]
    em_voo += ["%s (%s)" % (tid, t["estado"]) for tid, t in sorted(st["tasks"].items()) if t.get("estado") == "EM_VOO"]
    fora = [("%s: %s" % (p.get("id"), p.get("texto"))) for p in (pontos.get("pontos") or [])
            if isinstance(p, dict) and p.get("status") == "fora_do_escopo"]
    linhas = [
        "<!-- gerado por co.py; ledger_seq=%d ledger_hash=%s; NÃO EDITE -->" % (st["ledger_seq"], st["ledger_hash"]),
        "# Obra",
        "%s (%s) — alvo %s" % (nome, obra.get("tipo", "?"), obra.get("alvo", "?")),
        "pedido: %s" % (obra.get("pedido") or "—"),
        "## Estado",
        "%s (portao: %s, retorno: %s); hash_estado %s" % (o["estado"], o["portao"] or "—", o["retorno"] or "—",
                                                          st["hash_estado"]),
        "## Portões pendentes",
        pend,
        "## Contrato e oráculo",
        "contrato_hash: %s; oráculo: %s" % (st["contrato_hash"] or "—", ora_txt),
        "## Critério de parada",
        parada,
        "## Orçamento",
        "rodada %d/%d; tentativas %d/%d; despachos %d/%d; pausas %d/%d; replanejamentos %d/%d; teto %d; vivos %d" % (
            c.get("rodada", 0), k.get("MAX_RODADAS", 0), c.get("tentativas", 0), k.get("MAX_TENTATIVAS", 0),
            c.get("despachos", 0), k.get("MAX_DESPACHOS", 0), c.get("pausas", 0), k.get("MAX_PAUSAS", 0),
            c.get("replanejamentos", 0), k.get("MAX_REPLANEJAMENTOS", 0), st["teto_vigente"], len(st["vivos"])),
        "## Tasks em voo",
        "\n".join("- " + x for x in em_voo) if em_voo else "nenhuma",
        "## Fora do escopo",
        "\n".join("- " + x for x in fora) if fora else "—",
        "## Próximo comando",
        "```",
        proximo_comando(ws, st),
        "```",
    ]
    escrever_atomico(paths(ws)["retomar_md"], "\n".join(linhas) + "\n")
    return paths(ws)["retomar_md"]


# ================================================================== retomada

def retomar(ws):
    """Cadeia ok ⇒ fecha vagas perdidas (`perdida`; task EM_VOO ⇒ task.perdida) e grava `retomada`."""
    maq = carregar_maquina()
    with trava_ledger(ws):
        regs = ler_ledger(ws)
        conferir_ledger(ws, regs)
        st = fold_registros(regs, maq)
        desp = {}
        for r in regs:
            if r.get("evento") == "despachada":
                desp[r.get("chave") or (r.get("payload") or {}).get("chave")] = r
        novos, perdidas = [], []
        for ch in list(st["vivos"]):
            r = desp.get(ch) or {}
            p = r.get("payload") or {}
            tid = p.get("task") or r.get("task")
            ent = st["tasks"].get(tid) if tid else None
            tent = (ent or {}).get("tentativas", p.get("tentativa", 0) or 0)
            novos += _encadear(novos[-1] if novos else regs[-1], [dict(
                evento="perdida", task=tid, chave=ch,
                payload={"task": tid, "chave": ch, "tentativa_nova": int(tent) + 1})])
            perdidas.append(ch)
            st = fold_registros(regs + novos, maq)
            ent = st["tasks"].get(tid) if tid else None
            if ent and ent.get("estado") == "EM_VOO" and (ent.get("chave") in (None, ch)):
                niv = maq["niveis"]["task"]
                ctx = Contexto(ws, st, regs + novos, {"task": tid, "chave": ch}, "task", ent,
                               {"resultado_no_worktree": False}, ident=tid, retomada=True)
                for tn, t in niv["transitions"].items():
                    if t["evento"] == "task.perdida" and aplicavel(t, ("EM_VOO", None, None)) and \
                            avaliar_ast(parse_guarda(t["guard"]), ctx.valor) is True:
                        novos += _encadear(novos[-1], [dict(evento="task.perdida", ator=t["actor"], nivel="task",
                                                            de="EM_VOO", para=t["to"], task=tid, chave=ch,
                                                            payload={"task": tid, "chave": ch})])
                        st = fold_registros(regs + novos, maq)
                        break
        prox = proximo_comando(ws, st)
        if prox.endswith(" retomar"):
            prox = "%s --work %s status" % (CO_TXT, ws_real(ws))
        novos += _encadear(novos[-1] if novos else regs[-1], [dict(
            evento="retomada", payload={"cadeia_ok": True, "perdidas": perdidas, "colhidas": [],
                                        "proximo_comando": prox})])
        fold_registros(regs + novos, maq)
        _gravar_registros(ws, novos)
        st = pos_gravacao(ws)  # A11
    return {"cadeia_ok": True, "perdidas": perdidas, "colhidas": [], "proximo_comando": proximo_comando(ws, st),
            "estado": st}


# ================================================================== checador de máquina (invariantes.json5)

def _alvo_vivo(niv):
    return set(niv.get("terminal") or []) | set(niv.get("estaveis") or [])


def _grafo(niv):
    """BFS sobre nós (estado, portao, retorno) a partir de (initial, -, -). Retorna (nós, arestas)."""
    ini = (niv.get("initial"), None, None)
    nos, fila, arestas = {ini}, [ini], []
    trans = list((niv.get("transitions") or {}).items())
    while fila:
        n = fila.pop(0)
        for tn, t in trans:
            if aplicavel(t, n):
                d = destino(niv, n, t)
                if d is None:
                    continue
                arestas.append((n, d, tn, t))
                if d not in nos:
                    nos.add(d)
                    fila.append(d)
    return nos, arestas


def _alcanca(ini, arestas, excluir=None):
    excluir = excluir or set()
    if ini[0] in excluir:
        return set()
    adj = {}
    for a, b, _, _ in arestas:
        adj.setdefault(a, []).append(b)
    vis, fila = {ini}, [ini]
    while fila:
        n = fila.pop()
        for m in adj.get(n, []):
            if m[0] in excluir or m in vis:
                continue
            vis.add(m)
            fila.append(m)
    return vis


def _valor_constante(maq, teto):
    if isinstance(teto, int):
        return teto
    return (maq.get("constantes") or {}).get(teto)


def _sccs(nos, arestas):
    """Componentes fortemente conexas (lista de conjuntos) do grafo (nos, arestas[(a, b, ...)])."""
    adj = {}
    for e in arestas:
        adj.setdefault(e[0], set()).add(e[1])

    def alc(x):
        vist, fila = {x}, [x]
        while fila:
            n = fila.pop()
            for m in adj.get(n, ()):
                if m not in vist:
                    vist.add(m)
                    fila.append(m)
        return vist

    reach = {n: alc(n) for n in nos}
    out, feito = [], set()
    for n in sorted(nos, key=lambda z: tuple(str(x) for x in z) if isinstance(z, tuple) else (str(z),)):
        if n in feito:
            continue
        comp = {m for m in reach[n] if n in reach.get(m, ())}
        feito |= comp
        out.append(comp)
    return out


def _ciclo_sem_teto(arestas):
    """arestas: [(a, b, tn, t, incrementa:set, zera:set)]. Retorna os nós de uma SCC com ciclo sem contador
    limitante (I4), ou None."""
    pend = [arestas]
    while pend:
        ars = pend.pop()
        nos = set()
        for e in ars:
            nos.add(e[0])
            nos.add(e[1])
        for comp in _sccs(nos, ars):
            internas = [e for e in ars if e[0] in comp and e[1] in comp]
            if not internas:
                continue  # nó isolado sem laço
            inc = set().union(*[e[4] for e in internas])
            zer = set().union(*[e[5] for e in internas])
            limitam = inc - zer
            if not limitam:
                return comp
            resto = [e for e in internas if not (e[4] & limitam)]
            if resto:
                pend.append(resto)
    return None


def checar_maquina(maquina, niveis=None):
    """S1..S4 e I1..I7 de invariantes.json5 sobre a máquina dada (dict). Retorna relatório."""
    viol, info = [], []

    def v(cid, nivel, msg):
        viol.append({"id": cid, "nivel": nivel, "msg": msg})

    if not isinstance(maquina, dict) or not isinstance(maquina.get("niveis"), dict):
        raise Bad("máquina sem `niveis`")
    atores = set(maquina.get("atores") or [])
    constantes = maquina.get("constantes") or {}
    contadores = maquina.get("contadores") or {}
    sel = list(maquina["niveis"].keys()) if not niveis else list(niveis)
    for nivel in sel:
        niv = maquina["niveis"].get(nivel)
        if not isinstance(niv, dict):
            raise Bad("nível %r ausente na máquina" % nivel)
        states = list(niv.get("states") or [])
        sset = set(states)
        trans = niv.get("transitions") or {}
        terminal = set(niv.get("terminal") or [])
        estaveis = set(niv.get("estaveis") or [])
        transv = niv.get("transversais") or {}
        # ---- S1
        if niv.get("initial") not in sset:
            v("S1", nivel, "initial %r não é estado declarado" % niv.get("initial"))
        for x in sorted((terminal | estaveis | set(niv.get("verificacao_obrigatoria") or [])) - sset):
            v("S1", nivel, "estado %r referenciado mas não declarado" % x)
        for tn, t in trans.items():
            for f in t.get("from") or []:
                if f not in sset:
                    v("S1", nivel, "%s: from %r não declarado" % (tn, f))
            if t.get("to") != "@retorno" and t.get("to") not in sset:
                v("S1", nivel, "%s: to %r não declarado" % (tn, t.get("to")))
        # ---- S2
        for tn, t in trans.items():
            if t.get("actor") not in atores:
                v("S2", nivel, "%s: actor %r fora de atores" % (tn, t.get("actor")))
            for c in _incrementos(t) + list(t.get("zera") or []):
                d = contadores.get(c)
                if not d or _valor_constante(maquina, d.get("teto")) is None:
                    v("S2", nivel, "%s: contador %r sem declaração ou sem teto" % (tn, c))
        # ---- S3
        for tn, t in trans.items():
            for f in t.get("from") or []:
                if f in terminal:
                    v("S3", nivel, "%s: sai do terminal %s" % (tn, f))
        # ---- S4
        asts = {}
        for tn, t in trans.items():
            try:
                asts[tn] = parse_guarda(t.get("guard", ""))
            except ValueError as e:
                v("S4", nivel, "%s: guarda ilegível (%s)" % (tn, e))
        ini = (niv.get("initial"), None, None)
        nos, arestas = _grafo(niv)
        # ---- I1
        alc = {n[0] for n in nos}
        for s in states:
            if s not in alc:
                v("I1", nivel, "estado %s inalcançável a partir de %s" % (s, niv.get("initial")))
        # ---- I2
        alvos = _alvo_vivo(niv)
        rev = {}
        for a, b, _, _ in arestas:
            rev.setdefault(b, []).append(a)
        bons = {n for n in nos if n[0] in alvos}
        fila = list(bons)
        while fila:
            n = fila.pop()
            for m in rev.get(n, []):
                if m not in bons:
                    bons.add(m)
                    fila.append(m)
        presos = sorted({n[0] for n in nos if n not in bons and n[0] not in alvos})
        for s in presos:
            v("I2", nivel, "estado %s alcançável sem caminho a terminal/estável" % s)
        com_saida = {f for t in trans.values() for f in (t.get("from") or [])}
        for s in states:
            if s not in terminal and s not in com_saida:
                v("I2", nivel, "estado não terminal %s sem transição de saída" % s)
        for s, d in transv.items():
            if s in terminal:
                v("I2", nivel, "transversal %s não pode ser terminal" % s)
            evs = {t.get("evento") for t in trans.values() if s in (t.get("from") or [])}
            for ev in d.get("saidas_minimas") or []:
                if ev not in evs:
                    v("I2", nivel, "transversal %s sem saída mínima %r (L16)" % (s, ev))
        # ---- I3
        suc = niv.get("sucesso")
        for vv in niv.get("verificacao_obrigatoria") or []:
            r = _alcanca(ini, arestas, {vv})
            if suc and any(n[0] == suc for n in r):
                v("I3", nivel, "%s alcançável sem passar por %s (atalho)" % (suc, vv))
        # ---- I4 (R3-7: um contador só limita o ciclo se NÃO for zerado — `zera` da transição ou `zera_em` do
        # contador — dentro do próprio ciclo). Decomposição em SCCs: numa SCC não trivial (sem arestas humanas),
        # os contadores incrementados e não zerados por nenhuma aresta da SCC limitam as arestas que os
        # incrementam; essas arestas saem e as SCCs restantes são reexaminadas. SCC com ciclo e nenhum contador
        # limitante ⇒ violação (há um passeio fechado que percorre todas as arestas e zera tudo o que incrementa).
        def _zeros(tn, t):
            z = set(t.get("zera") or [])
            for cn, cd in contadores.items():
                if isinstance(cd, dict) and tn in (cd.get("zera_em") or []):
                    z.add(cn)
            return z

        ciclo = _ciclo_sem_teto([(a, b, tn, t, set(_incrementos(t)), _zeros(tn, t)) for a, b, tn, t in arestas
                                 if t.get("actor") != "humano"])
        if ciclo:
            v("I4", nivel, "ciclo sem humano e sem `incrementa` que não seja zerado no próprio ciclo: %s"
              % " → ".join(sorted({str(n[0]) for n in ciclo})))
        # ---- I5
        lista = [(tn, t) for tn, t in trans.items() if tn in asts]
        for i in range(len(lista)):
            for j in range(i + 1, len(lista)):
                (an, a), (bn, b) = lista[i], lista[j]
                if a.get("evento") != b.get("evento"):
                    continue
                comuns = set(a.get("from") or []) & set(b.get("from") or [])
                if not comuns:
                    continue
                ra, rb = (a.get("requer") or {}).get("portao"), (b.get("requer") or {}).get("portao")
                if ra is not None and rb is not None and ra != rb:
                    continue
                sobre = _sobreposicao(asts[an], asts[bn], maquina, contadores, constantes)
                if sobre is not None:
                    v("I5", nivel, "%s e %s (evento %s) não são mutuamente exclusivas: %s"
                      % (an, bn, a.get("evento"), sobre))
        # ---- I6
        AH = "AGUARDANDO_HUMANO"
        for tn, t in trans.items():
            hum = t.get("actor") == "humano"
            tem = tn in asts and "aprovacao_humana" in ids_guarda(asts[tn])
            frm = set(t.get("from") or [])
            if hum and (frm != {AH} or not tem):
                v("I6", nivel, "%s: transição humana fora de %s ou sem aprovacao_humana" % (tn, AH))
            if tem and not hum:
                v("I6", nivel, "%s: guarda com aprovacao_humana em transição não humana" % tn)
            if not hum and AH in frm:
                v("I6", nivel, "%s: transição não humana saindo de %s" % (tn, AH))
        # ---- I7
        for tn, t in trans.items():
            frm = set(t.get("from") or [])
            if frm & terminal:
                v("I7", nivel, "%s: saída de terminal" % tn)
            if frm & estaveis and not t.get("motivo_obrigatorio"):
                v("I7", nivel, "%s: saída de estável sem motivo_obrigatorio" % tn)
            if "ORACULO" in sset and t.get("to") == "ORACULO":
                pt = (t.get("requer") or {}).get("portao")
                if frm != {AH} or pt not in ("stop", "oraculo", "oraculo_mudar"):
                    v("I7", nivel, "%s: entrada em ORACULO fora de AGUARDANDO_HUMANO[stop|oraculo|oraculo_mudar]"
                      % tn)
        info.append({"nivel": nivel, "nos": len(nos), "arestas": len(arestas), "transicoes": len(trans)})
    return {"ok": not viol, "violacoes": viol, "info": info}


def _sobreposicao(a, b, maq, contadores, constantes):
    """Tabela-verdade: atribuição que satisfaz as duas guardas (ou None)."""
    nomes = sorted(ids_guarda(a) | ids_guarda(b))
    eixos = []
    for n in nomes:
        if n in constantes:
            continue
        if n in contadores:
            teto = _valor_constante(maq, contadores[n].get("teto"))
            eixos.append((n, list(range(0, (teto if isinstance(teto, int) else 3) + 2))))
        else:
            eixos.append((n, [False, True]))

    def rec(i, atual):
        if i == len(eixos):
            def val(x):
                return constantes[x] if x in constantes else atual.get(x)
            if avaliar_ast(a, val) is True and avaliar_ast(b, val) is True:
                return dict(atual)
            return None
        nome, dom = eixos[i]
        for x in dom:
            atual[nome] = x
            r = rec(i + 1, atual)
            if r is not None:
                return r
        atual.pop(nome, None)
        return None

    return rec(0, {})


def cobertura_eventos(maquina, niveis):
    """Matriz OK/RECUSA por aresta (invariantes.cobertura_g8) — `maquina check --events FILE`."""
    out = []
    for nivel in niveis:
        for tn, t in (maquina["niveis"][nivel].get("transitions") or {}).items():
            for caso in ("OK", "RECUSA"):
                out.append({"nivel": nivel, "transicao": tn, "evento": t.get("evento"), "from": t.get("from"),
                            "to": t.get("to"), "guarda": t.get("guard"), "caso": caso})
    return out


# ================================================================== handlers da CLI (args = namespace do argparse)

def _ler_payload(args):
    payload = {}
    if getattr(args, "payload", None):
        try:
            with open(args.payload, encoding="utf-8") as fh:
                payload = json.load(fh)
        except OSError as e:
            raise Bad("--payload ilegível: %s" % e)
        except ValueError as e:
            raise Bad("--payload não é JSON válido: %s" % e)
        if not isinstance(payload, dict):
            raise Bad("--payload precisa ser um objeto JSON")
    if getattr(args, "motivo", None):
        payload["motivo"] = args.motivo
    if getattr(args, "texto", None):
        payload["texto"] = args.texto
    return payload


_STOP_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*(>=|<=|==)\s*([0-9]+(?:\.[0-9]+)?)\s*$")


def cmd_init(args):
    w = ws_real(args.work)
    p = paths(w)
    contrato = carregar_contrato()
    if args.tipo not in contrato["tipos_alvo"]:
        raise Bad("--tipo %r inválido (%s)" % (args.tipo, ", ".join(contrato["tipos_alvo"])))
    alvo = os.path.realpath(os.path.expanduser(args.alvo))
    if not os.path.isdir(alvo):
        raise Bad("--alvo %s não é diretório existente" % alvo)
    if _dentro(w, alvo):
        raise Bad("workspace %s está dentro do alvo %s — o workspace fica SEMPRE fora do alvo; nada criado" % (w, alvo))
    if os.path.exists(p["ledger"]):
        raise Bad("já existe obra em %s (ledger presente); init não reescreve o ledger" % w)
    for nome in ("max_rodadas", "teto"):
        if getattr(args, nome) is not None and getattr(args, nome) < 1:
            raise Bad("--%s precisa ser ≥ 1" % nome.replace("_", "-"))
    c_hash = sha_file(os.path.join(REFS, "contrato.json5"))
    m_hash = sha_file(os.path.join(REFS, "maquina.json5"))
    m = _STOP_RE.match(args.stop or "")
    numerico = {"metrica": m.group(1), "op": m.group(2), "valor": float(m.group(3))} if m else None
    obra = {"schema_version": 1, "alvo": alvo, "workspace": w, "tipo": args.tipo, "pedido": args.pedido,
            "stop": {"texto": args.stop, "numerico": numerico},
            "max_rodadas": args.max_rodadas if args.max_rodadas is not None else 3,
            "max_horas": args.max_horas, "teto": args.teto if args.teto is not None else 5,
            "criado_em": now_ts(), "contrato_hash": c_hash, "maquina_hash": m_hash}
    if args.tipo in ("skill", "agente", "harness-maquina"):
        obra["runtimes"] = ["3.9", "3.13"]
    os.makedirs(p["dir"], exist_ok=True)
    with trava_ledger(w):
        if os.path.exists(p["ledger"]):
            raise Bad("já existe obra em %s" % w)
        escrever_json_atomico(p["obra"], obra)
        if not os.path.exists(p["pontos"]):
            escrever_json_atomico(p["pontos"], {"schema_version": 1, "pontos": []})
        gpl = {"alvo": alvo, "tipo": args.tipo, "contrato_hash": c_hash, "maquina_hash": m_hash}
        # V4-8: limite explícito do founder vai para a gênese (o ledger é a fonte das guardas); sem flag, padrão.
        if obra["max_rodadas"] != 3:
            gpl["max_rodadas"] = obra["max_rodadas"]
        if obra["teto"] != 5:
            gpl["teto"] = obra["teto"]
        gen = _encadear(None, [dict(evento="genese", payload=gpl)])
        _gravar_registros(w, gen)
        st = pos_gravacao(w)  # A11
    print("obra criada em %s (alvo %s, tipo %s); estado %s" % (w, alvo, args.tipo, st["obra"]["estado"]))
    print("próximo: %s" % proximo_comando(w, st))
    return 0


def cmd_ev(args):
    maq = carregar_maquina()
    evento = args.evento
    payload = _ler_payload(args)
    conhecidos = _eventos_conhecidos(maq)
    ops = set(carregar_contrato()["ledger"]["eventos_operacionais"].keys())
    if evento in eventos_humanos(maq):
        raise Bad("`%s` é transição humana: só `co.py aprovar` (no terminal do humano) a grava (I6/D9)" % evento)
    if evento in ops:
        if evento not in EVENTOS_VIA_EV:
            raise Bad("evento operacional `%s` é gravado pelo seu próprio comando, não por `ev`" % evento)
        if evento == "nota":
            if not str(payload.get("texto") or "").strip():
                raise Bad("`ev nota` exige --texto")
            payload = {"texto": payload["texto"]}
        else:
            md = paths(args.work)["retomar_md"]
            payload = {"retomar_md_hash": sha_file(md) if os.path.isfile(md) else sha_obj("")}
        seq = append_evento(args.work, evento, "script", payload)
        if evento == "checkpoint_janela_50":
            gerar_retomar_md(args.work)
        print("%s gravado (seq %d); estado inalterado" % (evento, seq))
        return 0
    if evento not in conhecidos:
        raise Bad("evento %r não existe em maquina.json5 nem em contrato.ledger.eventos_operacionais" % evento)
    r = transicionar(args.work, evento, payload)
    st = r["estado"]
    print("%s: %s → %s (seq %d)" % (r["transicao"], r["de"], r["para"], r["registros"][-1]["seq"]))
    print("próximo: %s" % proximo_comando(args.work, st))
    return 0


def cmd_status(args):
    st = fold(args.work)
    cache = paths(args.work)["estado_cache"]
    if os.path.isfile(cache):
        try:
            with open(cache, encoding="utf-8") as fh:
                c = json.load(fh)
        except (OSError, ValueError):
            c = None
        if c != st:
            sys.stderr.write("aviso: cache state.json diverge do fold do ledger — o ledger vence (mostrando o fold)\n")
    if getattr(args, "json", False):
        print(json.dumps(st, ensure_ascii=False, indent=1, sort_keys=True))
        return 0
    o = st["obra"]
    print("estado: %s (portao: %s, retorno: %s)" % (o["estado"], o["portao"] or "—", o["retorno"] or "—"))
    print("ledger: seq %d, hash %s" % (st["ledger_seq"], st["ledger_hash"]))
    print("hash_estado: %s" % st["hash_estado"])
    print("contadores: %s" % json.dumps(st["contadores"], sort_keys=True))
    print("teto: %d; vivos: %s" % (st["teto_vigente"], ", ".join(st["vivos"]) or "nenhum"))
    for tid, t in sorted(st["tasks"].items()):
        print("task %s: %s (tentativas %d)" % (tid, t["estado"], t.get("tentativas", 0)))
    print("próximo: %s" % proximo_comando(args.work, st))
    return 0


def cmd_load(args):
    fold(args.work)  # G-7a: ledger corrompido/truncado ⇒ Fail (exit 1) antes de montar o pacote
    maq = carregar_maquina()
    alvo = args.estado
    nivel = None
    for n, niv in maq["niveis"].items():
        if alvo in (niv.get("states") or []):
            nivel = n
            break
    if nivel is None:
        raise Bad("estado %r não existe em maquina.json5" % alvo)
    niv = maq["niveis"][nivel]
    partes = ["# load %s (nível %s)" % (alvo, nivel), "## Saídas (maquina.json5)"]
    for tn, t in (niv.get("transitions") or {}).items():
        if alvo in (t.get("from") or []):
            partes.append("- %s: `co.py ev %s` → %s [ator %s] guarda: %s%s" % (
                tn, t["evento"], t["to"], t["actor"], t.get("guard"),
                (" requer %s" % json.dumps(t["requer"], ensure_ascii=False)) if t.get("requer") else ""))
    md = paths(args.work)["retomar_md"]
    if os.path.isfile(md):
        with open(md, encoding="utf-8") as fh:
            partes += ["## RETOMAR.md", fh.read()]
    txt = "\n".join(partes)
    limite = carregar_contrato().get("load_max_chars", 6000)
    if len(txt) > limite:
        sys.stderr.write("pacote de %d chars > %d (load_max_chars)\n" % (len(txt), limite))
        return 1
    print(txt)
    return 0


def cmd_maquina(args):
    path = getattr(args, "machine", None)
    try:
        if path:
            with open(path, encoding="utf-8") as fh:
                maq = json5_loads(fh.read())
        else:
            maq = carregar_maquina()
    except OSError as e:
        raise Bad("máquina ilegível: %s" % e)
    except ValueError as e:
        raise Bad("máquina não é JSON/JSON5 válido: %s" % e)
    if not isinstance(maq, dict) or not isinstance(maq.get("niveis"), dict):
        raise Bad("máquina sem `niveis`")
    nivel = getattr(args, "nivel", None) or "todos"
    niveis = list(maq["niveis"].keys()) if nivel == "todos" else [nivel]
    rel = checar_maquina(maq, niveis)
    if getattr(args, "events", None):
        escrever_json_atomico(os.path.abspath(args.events), cobertura_eventos(maq, niveis))
    for i in rel["info"]:
        print("nível %s: %d nós, %d arestas, %d transições" % (i["nivel"], i["nos"], i["arestas"], i["transicoes"]))
    for x in rel["violacoes"]:
        print("FALHA %s [%s]: %s" % (x["id"], x["nivel"], x["msg"]))
    print("maquina check: %s (%s)" % ("OK" if rel["ok"] else "VIOLA " + ",".join(sorted({x["id"] for x in
                                                                                          rel["violacoes"]})),
                                     "S1..S4, I1..I7"))
    return 0 if rel["ok"] else 1


def cmd_pontos(args):
    p = ler_pontos(args.work)
    if p is None or not isinstance(p.get("pontos"), list):
        raise Bad("pontos.json5 ausente ou ilegível em %s" % paths(args.work)["pontos"])
    probs = []
    if not p["pontos"]:
        probs.append("nenhum ponto registrado")
    st_ok = ("aberto", "coberto", "atendido", "fora_do_escopo", "rejeitado")
    vistos = set()
    for i, x in enumerate(p["pontos"]):
        if not isinstance(x, dict):
            probs.append("ponto %d não é objeto" % i)
            continue
        pid = x.get("id") or "#%d" % i
        if pid in vistos:
            probs.append("%s duplicado" % pid)
        vistos.add(pid)
        if x.get("status") not in st_ok:
            probs.append("%s: status %r inválido" % (pid, x.get("status")))
        if not (isinstance(x.get("cenarios"), list) and x["cenarios"]) and not str(x.get("motivo") or "").strip():
            probs.append("%s: sem cenário e sem motivo" % pid)
    for pr in probs:
        print("FALHA: %s" % pr)
    print("pontos check: %s (%d pontos)" % ("OK" if not probs else "REPROVA", len(p["pontos"])))
    return 0 if not probs else 1


def cmd_retomar(args):
    r = retomar(args.work)
    print("cadeia ok; perdidas: %s" % (", ".join(r["perdidas"]) or "nenhuma"))
    print("estado: %s" % r["estado"]["obra"]["estado"])
    print("próximo: %s" % r["proximo_comando"])
    return 0


def cmd_oraculo_mudar(args):
    if not str(getattr(args, "motivo", None) or "").strip() or not str(getattr(args, "evidencia", None) or "").strip():
        raise Bad("oraculo mudar exige --motivo e --evidencia")
    r = transicionar(args.work, "oraculo_mudar", {"motivo": args.motivo, "evidencia": args.evidencia})
    print("oraculo_mudar: %s → %s[oraculo_mudar] (aprovação humana no terminal)" % (r["de"], r["para"]))
    return 0


def cmd_oraculo_manifest(args):
    if not getattr(args, "manifest", None):
        raise Bad("oraculo manifest exige --manifest FILE")
    try:
        man = json5_load(args.manifest)
    except OSError as e:
        raise Bad("--manifest ilegível: %s" % e)
    except ValueError as e:
        raise Bad("--manifest não é JSON5 válido: %s" % e)
    if not isinstance(man, dict) or not isinstance(man.get("frentes"), dict) or \
            not isinstance(man.get("construtores", {}), dict):
        raise Bad("MANIFEST precisa de `frentes` (map) e `construtores` (map)")
    autores = set()
    for fid, f in man["frentes"].items():
        if not isinstance(f, dict) or not isinstance(f.get("autores"), list) or not f["autores"]:
            raise Bad("frente %s sem `autores`" % fid)
        for k in ("dev", "heldout"):
            if not isinstance(f.get(k, []), list):
                raise Bad("frente %s: `%s` precisa ser lista" % (fid, k))
        autores |= set(f["autores"])
        cons = (man.get("construtores") or {}).get(fid)
        if cons and cons in f["autores"]:
            raise Fail("frente %s: autor do oráculo = construtor (%s) — D5" % (fid, cons))
    w = ws_real(args.work)
    with trava_ledger(w):
        regs = ler_ledger(w)
        conferir_ledger(w, regs)
        st = fold_registros(regs)
        if st["obra"]["estado"] != "ORACULO":
            raise Fail("oraculo manifest só em ORACULO (estado atual %s)" % st["obra"]["estado"])
        doc = {"schema_version": 1, "frentes": man["frentes"], "construtores": man.get("construtores") or {},
               "congelado": man.get("congelado")}
        mh = sha_obj(doc)
        novos = _encadear(regs[-1], [dict(evento="manifest_gravado",
                                          payload={"manifest_hash": mh, "autores": sorted(autores)})])
        escrever_json_atomico(paths(w)["manifest"], doc)
        _gravar_registros(w, novos)
        pos_gravacao(w)  # A11
    print("MANIFEST gravado (%s); autores: %s" % (mh, ", ".join(sorted(autores))))
    return 0


# ================================================================== aprovar (canal humano, modelo AC-04 do ac.py)

def make_challenge(n=4):
    """Desafio numérico aleatório de n dígitos (ac.py v0.3), exibido com espaços entre os dígitos."""
    return "%0*d" % (n, secrets.randbelow(10 ** n))


def _stdin_tty():
    try:
        return sys.stdin is not None and sys.stdin.isatty()
    except (ValueError, OSError):
        return False


def human_channel(what):
    """Exige humano no terminal: stdin tty E /dev/tty; mostra `DESAFIO: d d d d` e só aceita a redigitação exata
    (espaços ignorados). Nenhuma variável de ambiente dispensa. Sem tty ⇒ Bad; desafio errado ⇒ Fail."""
    if not _stdin_tty():
        raise Bad("aprovação humana exige terminal interativo (stdin tty); nada gravado. Um agente não aprova "
                  "portões — o humano roda este comando no terminal dele.")
    try:
        fd = os.open("/dev/tty", os.O_RDWR | getattr(os, "O_NOCTTY", 0))
    except OSError:
        raise Bad("aprovação humana exige /dev/tty (terminal controlador); nada gravado.")
    try:
        name = os.ttyname(sys.stdin.fileno())
    except OSError:
        name = "/dev/tty"
    ch = make_challenge()
    try:
        os.write(fd, ("Você vai %s.\nDESAFIO: %s\nDigite o número %s e aperte Enter: " % (what, ch, ch)).encode())
        buf = b""
        while not buf.endswith(b"\n") and len(buf) < 4096:
            chunk = os.read(fd, 1)
            if not chunk:
                break
            buf += chunk
    finally:
        os.close(fd)
    if "".join(buf.decode("utf-8", "replace").split()) != ch:
        raise Fail("desafio não confere — nada gravado")
    return name


def _os_user():
    try:
        import pwd
        return pwd.getpwuid(os.getuid()).pw_name
    except Exception:  # noqa: BLE001
        try:
            return getpass.getuser()
        except Exception:  # noqa: BLE001
            return str(os.getuid())


def _audit_append(path, rec):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            os.write(fd, (json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as e:
        raise Bad("não consegui gravar o audit em %s (%s); nada gravado" % (path, e))


# ------------------------------------------------------------------ A9: efeito de oraculo_aprovado (congelamento)

_IGNORAR_ARQ = ("__pycache__",)


def arquivos_do_oraculo(ws):
    """Arquivos (realpath, ordenados) casados pelos globs `MANIFEST.frentes[*].dev|heldout` (relativos ao ws ou
    absolutos). `**`/`*` casam qualquer coisa, inclusive `/` (fnmatch). __pycache__/*.pyc ficam fora."""
    import fnmatch
    w = ws_real(ws)
    try:
        man = json5_load(paths(w)["manifest"])
    except OSError:
        raise Fail("aprovar oraculo: %s ausente — rode `oraculo manifest` antes; nada gravado" % paths(w)["manifest"])
    except ValueError as e:
        raise Fail("aprovar oraculo: MANIFEST ilegível (%s); nada gravado" % e)
    globs = []
    for f in (man.get("frentes") or {}).values() if isinstance(man, dict) else []:
        if isinstance(f, dict):
            for k in ("dev", "heldout"):
                globs += [g for g in (f.get(k) or []) if isinstance(g, str) and g.strip()]
    if not globs:
        raise Fail("aprovar oraculo: MANIFEST sem globs dev/heldout; nada a congelar; nada gravado")
    pats = [os.path.normpath(g if os.path.isabs(g) else os.path.join(w, g)) for g in globs]
    pulados = {paths(w)["dir"], paths(w)["aprovacoes"], os.path.join(w, "campanhas")}
    achados = set()
    for raiz, dirs, arqs in os.walk(w):
        dirs[:] = sorted(d for d in dirs if d not in _IGNORAR_ARQ and os.path.join(raiz, d) not in pulados)
        for a in arqs:
            if a.endswith(".pyc"):
                continue
            full = os.path.join(raiz, a)
            if full == paths(w)["manifest"]:
                continue
            if any(fnmatch.fnmatchcase(full, pt) for pt in pats):
                achados.add(os.path.realpath(full))
    return sorted(achados), man


def contar_testes_assercoes(files):
    """Mesma contagem do G0 (co_portao.contar_oraculo); cópia local só se co_portao não carregar."""
    try:
        import co_portao
        return co_portao.contar_oraculo(files)
    except Exception:  # noqa: BLE001 — fallback determinístico idêntico
        pass
    import ast as _ast
    nt = na = 0
    for f in files:
        with open(f, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        c = None
        if f.endswith(".py"):
            try:
                tree = _ast.parse(src)
                a = b = 0
                for n in _ast.walk(tree):
                    if isinstance(n, (_ast.FunctionDef, _ast.AsyncFunctionDef)) and n.name.startswith("test"):
                        a += 1
                    elif isinstance(n, _ast.Assert):
                        b += 1
                    elif isinstance(n, _ast.Call):
                        fn = n.func
                        nm = fn.attr if isinstance(fn, _ast.Attribute) else fn.id if isinstance(fn, _ast.Name) else ""
                        if nm.startswith("assert") or nm.startswith("fail") or nm == "expect":
                            b += 1
                c = (a, b)
            except SyntaxError:
                c = None
        if c is None:
            c = (len(re.findall(r"\b(?:def\s+test\w*|it\(|test\()", src)),
                 len(re.findall(r"\bassert\w*|\bexpect\(|\"esperado\"", src)))
        nt, na = nt + c[0], na + c[1]
    return nt, na


def preparar_congelamento(ws):
    """Pré-condições do congelamento, SEM escrever nada: campanha-mãe inicializada, arquivos do MANIFEST, contagem
    ≥ 1 teste e ≥ 1 asserção. Fail ⇒ a aprovação nem pede o desafio."""
    camp = paths(ws)["campanha_mae"]
    st_ac = os.path.join(camp, ".auto-correcao", "state.json")
    if not os.path.isfile(st_ac):
        raise Fail("aprovar oraculo: campanha-mãe não inicializada (%s ausente; `ac.py --work %s init ...`); nada "
                   "gravado" % (st_ac, camp))
    if not os.path.isfile(AC_PY):
        raise Bad("ac.py ausente (%s): necessário para `oracle freeze`" % AC_PY)
    files, man = arquivos_do_oraculo(ws)
    if not files:
        raise Fail("aprovar oraculo: nenhum arquivo casa os globs dev/heldout do MANIFEST; nada gravado")
    nt, na = contar_testes_assercoes(files)
    if nt < 1 or na < 1:
        raise Fail("aprovar oraculo: oráculo vazio (%d testes, %d asserções); nada gravado" % (nt, na))
    doc = {"schema_version": 1, "frentes": man.get("frentes"), "construtores": man.get("construtores") or {},
           "congelado": man.get("congelado")}
    return {"camp": camp, "state": st_ac, "files": files, "n_testes": nt, "n_assercoes": na,
            "manifest_hash": sha_obj(doc)}


def congelar_oraculo(ws, prep, motivo):
    """Roda `ac.py --work <campanha-mãe> oracle freeze --file ...` (ou `oracle change` se a campanha já tem outro
    hash congelado; nada se o hash já é o dos mesmos arquivos) e devolve o espec do evento `oraculo_congelado`."""
    def ac_state():
        with open(prep["state"], encoding="utf-8") as fh:
            return json.load(fh).get("oracle") or {}
    try:
        o = ac_state()
    except (OSError, ValueError) as e:
        raise Fail("state da campanha-mãe ilegível (%s); nada gravado" % e)
    atual = _ac().sha_files(prep["files"])
    cmd = None
    if not o.get("hash"):
        cmd = ["oracle", "freeze"]
    elif o.get("hash") != atual or sorted(o.get("files") or []) != prep["files"]:
        cmd = ["oracle", "change", "--why", motivo, "--evidence", "aprovação humana do portão oraculo (co.py aprovar)"]
    if cmd:
        argv = [sys.executable, AC_PY, "--work", prep["camp"]] + cmd
        for f in prep["files"]:
            argv += ["--file", f]
        try:
            p = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               universal_newlines=True, timeout=120)
        except (OSError, subprocess.SubprocessError) as e:
            raise Fail("ac.py oracle %s não rodou (%s); nada gravado" % (cmd[1], e))
        if p.returncode != 0:
            raise Fail("ac.py oracle %s falhou (exit %d): %s; nada gravado" % (cmd[1], p.returncode,
                                                                              p.stdout.strip()[-400:]))
    try:
        h = ac_state().get("hash")
    except (OSError, ValueError) as e:
        raise Fail("state da campanha-mãe ilegível após o freeze (%s); nada gravado" % e)
    if not isinstance(h, str) or not HEX64.match(h) or h != atual:
        raise Fail("ac.py não registrou o hash esperado do oráculo (%s); nada gravado" % h)
    return dict(evento="oraculo_congelado", payload={"hash": h, "n_testes": prep["n_testes"],
                                                     "n_assercoes": prep["n_assercoes"],
                                                     "manifest_hash": prep["manifest_hash"]})


def cmd_aprovar(args):
    """tty + desafio + hash_estado ⇒ (audit, aprovacoes/<portao>-<seq>.json, `aprovacao`, transição humana e seus
    efeitos) na MESMA chamada, sob a trava do ledger. Toda recusa: nada gravado.
    A9: `aprovar oraculo --decisao aprovado` congela o oráculo (ac.py oracle freeze) e grava `oraculo_congelado`.
    A10: hash_estado é reconferido DENTRO da trava, depois do desafio."""
    portao, decisao = args.portao, args.decisao
    if decisao not in ("aprovado", "rejeitado", "abandonar"):
        raise Bad("--decisao aprovado|rejeitado|abandonar")
    if not _stdin_tty():
        raise Bad("aprovação humana exige terminal interativo (stdin tty); nada gravado. Um agente não aprova "
                  "portões — o humano roda este comando no terminal dele.")
    w = ws_real(args.work)
    aud = audit_path()
    if _dentro(aud, w):
        raise Fail("audit (%s) resolve para dentro do workspace %s — precisa ficar fora; nada gravado" % (aud, w))
    st = fold(w)
    o = st["obra"]
    if o["estado"] != "AGUARDANDO_HUMANO" or o["portao"] != portao:
        raise Fail("nada a aprovar no portão %r: estado %s (portao %s)" % (portao, o["estado"], o["portao"]))
    h_antes = st["hash_estado"]
    prep = preparar_congelamento(w) if (portao == "oraculo" and decisao == "aprovado") else None
    tty = human_channel("decidir '%s' no portão '%s' (obra %s, hash_estado %s)" % (decisao, portao, w, h_antes[:12]))
    st2 = fold(w)
    if st2["hash_estado"] != h_antes or st2["obra"] != o:
        raise Fail("hash_estado mudou durante a aprovação (TOCTOU) — nada gravado; rode de novo")
    user, ts = _os_user(), now_ts()
    ctx = {}

    def payload_ap(seq_ap):
        return {"portao": portao, "decisao": decisao,
                "arquivo": os.path.join(paths(w)["aprovacoes"], "%s-%d.json" % (portao, seq_ap)),
                "hash_estado": h_antes, "usuario_so": user, "ttyname": tty}

    def efeito(tn, novos, st_depois):
        if prep is None or tn != "oraculo_aprovado":
            return []
        ap = [r for r in novos if r["evento"] == "aprovacao"][0]
        return [congelar_oraculo(w, prep, "aprovação do oráculo (portão oraculo, seq %d)" % ap["seq"])]

    def antes_de_gravar(novos):
        ap = [r for r in novos if r["evento"] == "aprovacao"][0]
        tr = novos[novos.index(ap) + 1]
        arquivo = os.path.join(paths(w)["aprovacoes"], "%s-%d.json" % (portao, ap["seq"]))
        if ap["payload"]["arquivo"] != arquivo:
            raise Fail("seq da aprovação divergiu — nada gravado")
        if os.path.lexists(arquivo):
            raise Fail("arquivo de aprovação %s já existe — nada gravado" % arquivo)
        # V4-9: ordem segura — arquivo (atômico) → ledger → audit; falha em qualquer passo desfaz os anteriores.
        try:
            escrever_json_atomico(arquivo, {
                "schema_version": 1, "portao": portao, "decisao": decisao, "nota": getattr(args, "nota", None),
                "seq": ap["seq"], "usuario_so": user, "uid": os.getuid(), "ttyname": tty, "ts": ts,
                "hash_estado": h_antes, "estado": dict(o), "desafio_ok": True, "transicao_seq": tr["seq"]},
                modo=0o600)
        except OSError as e:
            raise Bad("não consegui gravar o arquivo de aprovação %s (%s); nada gravado" % (arquivo, e))
        ctx["arquivo"], ctx["seq"] = arquivo, ap["seq"]

    def depois_de_gravar(novos):
        _audit_append(aud, {"ts": ts, "tipo": "aprovacao", "cmd": "aprovar", "name": portao, "decision": decisao,
                            "by": "humano", "work": w, "user": user, "tty": tty, "seq": ctx["seq"],
                            "hash_estado": h_antes})

    def desfazer():
        arq = ctx.get("arquivo")
        if arq and os.path.lexists(arq):
            try:
                os.unlink(arq)
            except OSError:
                pass

    evento = "abandonar" if decisao == "abandonar" else decisao
    payload_tr = {"nota": args.nota} if getattr(args, "nota", None) else {}
    r = transicionar(w, evento, payload_tr, _humano={"payload_aprovacao": payload_ap, "hash_estado": h_antes,
                                                      "efeito": efeito, "antes_de_gravar": antes_de_gravar,
                                                      "depois_de_gravar": depois_de_gravar, "desfazer": desfazer})
    sh = os.path.join(paths(w)["aprovacoes"], "aprovar-%s.sh" % portao)
    if os.path.isfile(sh) and not (r["estado"]["obra"]["estado"] == "AGUARDANDO_HUMANO"
                                   and r["estado"]["obra"]["portao"] == portao):
        os.unlink(sh)
    cong = [x for x in r["registros"] if x["evento"] == "oraculo_congelado"]
    print("portão %s: %s por %s (%s) — %s → %s; aprovação %s%s" % (
        portao, decisao, user, tty, r["de"], r["para"], ctx.get("arquivo"),
        ("; oráculo congelado %s (%d testes, %d asserções)" % (cong[-1]["payload"]["hash"][:12],
                                                               cong[-1]["payload"]["n_testes"],
                                                               cong[-1]["payload"]["n_assercoes"])) if cong else ""))
    return 0
