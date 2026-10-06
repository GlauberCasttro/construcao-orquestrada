#!/usr/bin/env python3
"""co_portao — portão de regressão da construcao-orquestrada (frente C, onda 1). Python 3.9+, só stdlib.

Contrato (references/contrato.json5#modulos.co_portao): gerar_regressao(ws, tipo), rodar(ws, only, final),
selftest(), veredito(ws), g0..g14, cmd_portao, cmd_veredito, cmd_diff. `co.py` (frente A) despacha os
subcomandos `portao run|selftest`, `veredito` e `diff` para cá chamando `main(argv)` (argv com ou sem o
`--work <ws>` global) ou os `cmd_*(args)` com o Namespace dele. Exit: 0 passa/GO*, 1 reprova/NO-GO, 2 entrada
inválida/ferramenta ausente (falha fechada).

Núcleo da onda 1: G0 (oráculo intacto por hash + contagens), G1 (suítes registradas; só conta teste executado
com relatório estruturado do próprio runner — R3-6; 0 executados, runner desconhecido ou ferramenta ausente reprova), G3 (território: diff desde a base incluindo staged/untracked/modo/rename/deleção), G4 (gaming no diff),
veredito com precedência NO-GO > GO (simulado) > GO (com waiver) > GO; G0/G1/G3/G4 sem waiver. Os demais gates
saem ERRO ("não implementado na onda 1") quando aplicáveis — falha fechada, nunca PASS por vácuo.
"""
import argparse
import ast
import fnmatch
import hashlib
import importlib.util
import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time

AQUI = os.path.dirname(os.path.realpath(__file__))
SKILL = os.path.dirname(AQUI)
REFS = os.path.join(SKILL, "references")
PORTOES = os.path.join(REFS, "portoes.json5")
CONTRATO = os.path.join(REFS, "contrato.json5")
GIDS = ["G%d" % n for n in range(15)]
PRECEDENCIA = ["NO-GO", "GO (simulado)", "GO (com waiver)", "GO"]
SEM_WAIVER_NUCLEO = ("G0", "G1", "G3", "G4")


class Erro(Exception):
    """Entrada inválida / ferramenta ausente ⇒ exit 2."""


# ------------------------------------------------------------------ reuso do ac.py (importlib, nunca copiar)

_AC = None


def ac_path():
    for p in (os.path.join(os.path.dirname(SKILL), "auto-correcao", "scripts", "ac.py"),
              os.path.expanduser("~/.claude/skills/auto-correcao/scripts/ac.py")):
        if os.path.isfile(p):
            return p
    raise Erro("ac.py (auto-correcao) não encontrado")


def acmod():
    global _AC
    if _AC is None:
        spec = importlib.util.spec_from_file_location("ac_para_co_portao", ac_path())
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _AC = m
    return _AC


def json5_load(path):
    with open(path, encoding="utf-8") as fh:
        return acmod().json5_loads(fh.read())


def sha_files(paths):
    return acmod().sha_files(paths)


# ------------------------------------------------------------------ hash / io (formatos.json5#convencoes)

def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha_obj(obj):
    return hashlib.sha256(canon(obj)).hexdigest()


def sha_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def now_ts():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def grava_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    os.replace(tmp, path)


# ------------------------------------------------------------------ ledger (API da frente A: co_estado)

if AQUI not in sys.path:
    sys.path.insert(0, AQUI)
import co_estado  # noqa: E402  (ler_ledger, problemas_cadeia, append_evento — docstring de co_estado)


def ledger_path(ws):
    return co_estado.paths(ws)["ledger"]


def ler_ledger(ws):
    try:
        return co_estado.ler_ledger(ws)
    except (co_estado.Bad, co_estado.Fail) as e:
        raise Erro(str(e))


def cadeia_ok(recs):
    return not co_estado.problemas_cadeia(recs)


def problemas_ledger(ws, recs):
    """Cadeia de hash (problemas_cadeia) + fim não truncado/reescrito (co_estado.conferir_ledger: testemunhas
    state.json/audit). Lista vazia = ledger íntegro."""
    probs = list(co_estado.problemas_cadeia(recs))
    if probs:
        return ["cadeia quebrada: " + "; ".join(probs[:3])]
    try:
        co_estado.conferir_ledger(ws, recs)
    except (co_estado.Fail, co_estado.Bad) as e:
        return [str(e)]
    return []


def ler_ledger_conferido(ws):
    """Ledger legível E íntegro (cadeia + fim), senão Erro (falha fechada, exit 2)."""
    recs = ler_ledger(ws)
    probs = problemas_ledger(ws, recs)
    if probs:
        raise Erro("ledger ilegível/adulterado: %s" % "; ".join(probs))
    return recs


def append_ledger(ws, evento, payload, ator="script"):
    try:
        return co_estado.append_evento(ws, evento, ator, payload)
    except (co_estado.Bad, co_estado.Fail) as e:
        raise Erro("nada gravado no ledger: %s" % e)


# ------------------------------------------------------------------ registrado no ledger (A2/A4)
# obra.json5, PLANO.json5 e regressao.json5 são reescrevíveis; o que vale é o hash gravado em premissas_ok/plano_ok.

def _payload_ultimo(recs, evento):
    for r in reversed(recs):
        if r.get("evento") == evento:
            return r
    return None


_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def hash_do_motor(rec, campo):
    """R3-5: o hash que vale é o que o MOTOR (co_estado) calculou do disco no momento do evento e gravou no registro
    encadeado — nunca um valor de `--payload` do agente nem algo recalculado agora. Se co_estado exporta um acessor
    (`hash_do_motor`/`hash_registrado`), ele decide; senão o campo do registro, só se for um sha256 bem formado
    (ausente/malformado ⇒ None ⇒ divergência, falha fechada)."""
    for nome in ("hash_do_motor", "hash_registrado"):
        f = getattr(co_estado, nome, None)
        if callable(f):
            v = f(rec, campo)
            return v if isinstance(v, str) and _HEX64.match(v) else None
    pl = rec.get("payload") if isinstance(rec, dict) else None
    motor = pl.get("motor") if isinstance(pl, dict) and isinstance(pl.get("motor"), dict) else None
    v = motor.get(campo) if motor is not None else (pl.get(campo) if isinstance(pl, dict) else None)
    return v if isinstance(v, str) and _HEX64.match(v) else None


def divergencias_registradas(ws, recs):
    """{"obra"|"plano"|"regressao": motivo} para cada arquivo que diverge do hash gravado no ledger. Antes do
    evento que grava o hash não há comparação."""
    out = {}
    alvos = (("obra", "premissas_ok", "obra_hash", "obra.json5"),
             ("plano", "plano_ok", "plano_hash", "PLANO.json5"),
             ("regressao", "plano_ok", "regressao_hash", "regressao.json5"))
    for chave, evento, campo, arq in alvos:
        r = _payload_ultimo(recs, evento)
        if r is None:
            continue
        gravado = hash_do_motor(r, campo)
        p = os.path.join(ws, arq)
        atual = sha_file(p) if os.path.isfile(p) else None
        if not gravado or atual != gravado:
            out[chave] = "%s (%s) ≠ %s.%s gravado no ledger (seq %s)" % (
                arq, (atual or "ausente")[:12], evento, campo, r.get("seq"))
    return out


_SONDAS_AMPLO = ("zq-sonda-amplo-7731.zqx", "zq-sonda-1/zq-sonda-2/zq-sonda-amplo-7731.zqx")


def writes_amplos(writes):
    """Globs que cobrem a raiz inteira (`**`, `*`, `**/*`, `./**`, ...): casam um arquivo arbitrário na raiz ou
    em profundidade."""
    return [g for g in writes if not str(g).strip() or any(glob_re(str(g)).match(s) for s in _SONDAS_AMPLO)]


def plano_aprovado(ws, recs):
    """Portão humano `plano` aprovado depois do último plano_ok, com linha limpa no audit."""
    ult = _payload_ultimo(recs, "plano_ok")
    desde = ult.get("seq", 0) if ult else 0
    sujas = set(aprovacoes_sem_audit(ws, recs))
    for r in recs:
        pl = r.get("payload") or {}
        if r.get("evento") == "aprovacao" and r.get("seq", 0) > desde and pl.get("portao") == "plano" \
                and pl.get("decisao") == "aprovado" and (pl.get("arquivo") or "seq %s" % r.get("seq")) not in sujas:
            return True
    return False


def problemas_territorio_registrado(ws, recs, writes):
    """Motivos que reprovam G3 independentemente do diff: obra/PLANO reescritos e writes amplos não aprovados."""
    div = divergencias_registradas(ws, recs)
    probs = [div[k] for k in ("obra", "plano") if k in div]
    amplos = writes_amplos(writes)
    if amplos and not plano_aprovado(ws, recs):
        probs.append("writes amplos %s sem portão humano `plano` aprovado" % amplos)
    return probs


def _reprova_g3(r3, probs):
    if not probs:
        return r3
    ev = "; ".join(probs) + ("" if r3["status"] == "PASS" else " | " + r3["evidencia"])
    return _res("G3", "FAIL", 1, r3.get("cmd") or "diff", ev, "território não é o registrado")


def ler_obra(ws):
    p = os.path.join(ws, "obra.json5")
    if not os.path.isfile(p):
        raise Erro("obra.json5 ausente em %s" % ws)
    return json5_load(p)


# ------------------------------------------------------------------ regressao.json5

def _na_motivo(txt):
    m = re.search(r"motivo:\s*([^)]*)\)", txt)
    return (m.group(1).strip() if m else txt[3:].strip(" ()")) or "não aplicável"


def aplicabilidade_contrato(tipo):
    """V4-2: {gid: {"aplica", "waiver", "na_motivo", "por_tipo"}} derivado SÓ do contrato (portoes.json5 por tipo de
    alvo + contrato.sem_waiver), nunca do regressao.json5 editável. Tipo desconhecido ⇒ Erro."""
    contrato = json5_load(CONTRATO)
    port = json5_load(PORTOES)
    coluna = contrato["tipo_coluna_portao"].get(tipo) if isinstance(tipo, str) else None
    if coluna is None:
        raise Erro("tipo inválido: %r" % (tipo,))
    sem_waiver = set(contrato["sem_waiver"])
    out = {}
    for gid in GIDS:
        g = port["itens"][gid]
        pt = g["por_tipo"].get(coluna, "aplica")
        aplica, na, waiver = True, None, bool(g.get("waiver"))
        if isinstance(pt, dict):
            aplica = bool(pt.get("aplica", True))
            waiver = bool(pt.get("waiver", waiver))
            na = None if aplica else (pt.get("motivo") or "não aplicável")
        elif isinstance(pt, str) and pt.strip().upper().startswith("N/A"):
            aplica, na = False, _na_motivo(pt.strip())
        if gid in sem_waiver:
            waiver = False
        out[gid] = {"aplica": aplica, "waiver": waiver, "na_motivo": na, "por_tipo": pt}
    return out


def sem_waiver_contrato():
    try:
        return set(json5_load(CONTRATO)["sem_waiver"]) | set(SEM_WAIVER_NUCLEO)
    except (OSError, ValueError, KeyError, TypeError, Erro):
        return set(SEM_WAIVER_NUCLEO)


def tipo_da_obra(ws):
    """Tipo do alvo vindo de obra.json5 (cujo hash é conferido contra premissas_ok); None se ilegível."""
    if not ws:
        return None
    try:
        t = ler_obra(ws).get("tipo")
    except (Erro, OSError, ValueError, AttributeError):
        return None
    return t if isinstance(t, str) else None


def regressao_efetiva(reg, tipo):
    """V4-2: itens efetivos = contrato ∪ exigência extra do regressao.json5. O arquivo só ACRESCENTA exigência:
    aplica = contrato.aplica OR reg.aplica; waiver = contrato.waiver AND reg.waiver; itens sem waiver do contrato
    (G0/G1/G3/G4/G5/G7/G13, G8 em harness-maquina) nunca viram NA nem WAIVED por edição. Tipo desconhecido ⇒ todo
    item sem_waiver do contrato forçado aplicável, sem waiver (falha fechada)."""
    regi = {i["id"]: dict(i) for i in (reg or {}).get("itens") or [] if isinstance(i, dict) and "id" in i}
    try:
        cont = aplicabilidade_contrato(tipo)
    except (Erro, OSError, ValueError, KeyError, TypeError):
        cont = None
    if cont is None:
        for gid in sem_waiver_contrato():
            regi[gid] = dict(regi.get(gid) or {"id": gid}, aplica=True, waiver=False)
        return regi
    for gid, c in cont.items():
        r = regi.get(gid) or {"id": gid, "nome": gid, "cmd": "", "na_motivo": c["na_motivo"]}
        aplica = bool(c["aplica"]) or r.get("aplica") is True
        waiver = bool(c["waiver"]) and r.get("waiver") is not False
        regi[gid] = dict(r, aplica=aplica, waiver=waiver, na_motivo=None if aplica else
                         (c["na_motivo"] or r.get("na_motivo") or "não aplicável"))
    for gid in SEM_WAIVER_NUCLEO:
        regi[gid] = dict(regi[gid], aplica=True, waiver=False)
    return regi


def gerar_regressao(ws, tipo=None):
    """Grava <ws>/regressao.json5 com G0..G14 (os 15 sempre presentes; N/A com motivo)."""
    ws = os.path.realpath(ws)
    obra = {}
    if os.path.isfile(os.path.join(ws, "obra.json5")):
        obra = ler_obra(ws)
    tipo = tipo or obra.get("tipo")
    port = json5_load(PORTOES)
    cont = aplicabilidade_contrato(tipo)
    subst = {"{ws}": ws, "{alvo}": obra.get("alvo") or "{alvo}", "{base}": obra.get("base") or "{base}"}
    itens = []
    for gid in GIDS:
        g = port["itens"][gid]
        c = cont[gid]
        aplica, pt = c["aplica"], c["por_tipo"]
        cmd = g.get("cmd", "") if aplica else ""
        for k, v in subst.items():
            cmd = cmd.replace(k, v)
        itens.append({"id": gid, "nome": g["nome"], "aplica": aplica, "na_motivo": c["na_motivo"], "cmd": cmd,
                      "limiar": g.get("limiar"), "falha_fechado": True, "waiver": c["waiver"],
                      "por_tipo": pt if isinstance(pt, str) else None})
    reg = {"schema_version": 1, "tipo": tipo, "portoes_hash": sha_file(PORTOES), "itens": itens}
    grava_json(os.path.join(ws, "regressao.json5"), reg)
    return reg


def ler_regressao(ws):
    p = os.path.join(ws, "regressao.json5")
    if not os.path.isfile(p):
        return gerar_regressao(ws)
    return json5_load(p)


# ------------------------------------------------------------------ G0 oráculo intacto

def _conta_py(src):
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    nt = na = 0
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test"):
            nt += 1
        elif isinstance(n, ast.Assert):
            na += 1
        elif isinstance(n, ast.Call):
            f = n.func
            nome = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
            if nome.startswith("assert") or nome.startswith("fail") or nome == "expect":
                na += 1
    return nt, na


def contar_oraculo(files):
    nt = na = 0
    for f in files:
        with open(f, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        c = _conta_py(src) if f.endswith(".py") else None
        if c is None:
            c = (len(re.findall(r"\b(?:def\s+test\w*|it\(|test\()", src)),
                 len(re.findall(r"\bassert\w*|\bexpect\(|\"esperado\"", src)))
        nt, na = nt + c[0], na + c[1]
    return nt, na


def manifest_hashes(path):
    """Hashes aceitos do MANIFEST atual: o do documento normalizado que co_estado grava/congela
    ({schema_version: 1, frentes, construtores, congelado} — sha_obj) e o sha256 dos bytes. None se ausente;
    {} (vazio) se ilegível (nunca confere)."""
    if not os.path.isfile(path):
        return None
    hs = {sha_file(path)}
    try:
        man = json5_load(path)
    except Exception:  # noqa: BLE001 — ilegível ⇒ só o hash dos bytes, que não confere com o congelado
        return set()
    if isinstance(man, dict):
        hs.add(sha_obj({"schema_version": 1, "frentes": man.get("frentes"),
                        "construtores": man.get("construtores") or {}, "congelado": man.get("congelado")}))
    return hs


def problema_manifest(ws, recs, cong):
    """G-6: `oraculo_congelado.manifest_hash` × MANIFEST.json5 atual. Alterado ⇒ motivo; ausente com
    oraculo_congelado gravado ⇒ motivo; ilegível ⇒ motivo. None = confere."""
    p = os.path.join(ws, "oraculo", "MANIFEST.json5")
    gravado = cong.get("manifest_hash")
    atuais = manifest_hashes(p)
    if atuais is None:  # oraculo_congelado gravado ⇒ o MANIFEST tem de existir (falha fechada)
        return "MANIFEST.json5 ausente com oraculo_congelado gravado (manifest_hash %s)" % str(gravado)[:12]
    if not isinstance(gravado, str) or not _HEX64.match(gravado) or gravado not in atuais:
        return "MANIFEST.json5 alterado depois do congelamento: atual ≠ oraculo_congelado.manifest_hash %s" % (
            str(gravado)[:12])
    return None


def g0_oraculo_intacto(ws, recs=None):
    cmd = "ac.py --work %s oracle verify" % os.path.join(ws, "campanhas", "construcao")
    camp = os.path.join(ws, "campanhas", "construcao")
    st_path = os.path.join(camp, ".auto-correcao", "state.json")
    if not os.path.isfile(st_path):
        return _res("G0", "ERRO", None, cmd, "campanha mãe ausente: %s" % st_path, "campanha ausente")
    try:
        p = subprocess.run([sys.executable, ac_path(), "--work", camp, "oracle", "verify"], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True, timeout=120)
    except (OSError, subprocess.SubprocessError, Erro) as e:
        return _res("G0", "ERRO", None, cmd, str(e), "ac.py não rodou")
    if p.returncode != 0:
        return _res("G0", "FAIL" if p.returncode == 1 else "ERRO", p.returncode, cmd, p.stdout.strip()[-800:],
                    "oracle verify reprovou")
    with open(st_path, encoding="utf-8") as fh:
        o = (json.load(fh).get("oracle") or {})
    recs = ler_ledger(ws) if recs is None else recs
    cong = [r["payload"] for r in recs if r.get("evento") == "oraculo_congelado"]
    if not cong:
        return _res("G0", "FAIL", 0, cmd, "ledger sem oraculo_congelado", "oráculo nunca congelado na obra")
    c = cong[-1]
    if c.get("hash") != o.get("hash"):
        return _res("G0", "FAIL", 0, cmd, "hash do ledger %s ≠ campanha %s" % (str(c.get("hash"))[:12],
                    str(o.get("hash"))[:12]), "oráculo da campanha não é o congelado na obra")
    prob_man = problema_manifest(ws, recs, c)
    if prob_man:
        return _res("G0", "FAIL", 0, cmd, prob_man, "MANIFEST do oráculo não é o congelado")
    nt, na = contar_oraculo(o.get("files") or [])
    ev = "hash ok; %d testes (congelado %s), %d asserções (congelado %s)" % (nt, c.get("n_testes"), na,
                                                                              c.get("n_assercoes"))
    if nt < int(c.get("n_testes") or 0) or na < int(c.get("n_assercoes") or 0) or nt < 1 or na < 1:
        return _res("G0", "FAIL", 0, cmd, ev, "contagem abaixo do congelado")
    return _res("G0", "PASS", 0, cmd, ev, None)


# ------------------------------------------------------------------ G1 suítes (falha fechada)

# R3-6: só conta teste EXECUTADO, provado por eventos por teste que o runner (wrapper unittest / plugin pytest)
# emite num pipe herdado; o relatório estruturado é escrito e validado pelo G1, em OUTRO processo, num diretório
# privado e com nonce que o processo testado nunca vê. Texto impresso ("Ran N tests", "N passed", "ok") não conta.
# A suíte registrada é decomposta em passos (`cd DIR`, `K=V ... <runner>`, ligados por `&&`/`;`); cada runner
# precisa ser conhecido (unittest via `python -m unittest`, pytest via `pytest`/`python -m pytest`). Qualquer
# outro comando, pipe, redireção, subshell ou `||` ⇒ FAIL (runner sem relatório estruturado; falha fechada).

_PY_BIN = re.compile(r"^python(?:\d+(?:\.\d+)*)?$")
_PY_FLAGS_SOLTAS = {"-B", "-u", "-E", "-s", "-I", "-O", "-OO", "-q", "-b", "-bb", "-P"}
_ENV_ATRIB = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_SEPARADORES = ("&&", ";")

_WRAPPER_UNITTEST = r'''
import json, os, sys, unittest
_fd = int(sys.argv[1])
del sys.argv[1:2]
sys.argv[0] = "python -m unittest"
sys.path[0] = os.getcwd()
os.set_inheritable(_fd, False)
_canal = os.fdopen(_fd, "w", buffering=1)


def _emit(d):
    try:
        _canal.write(json.dumps(d) + "\n")
        _canal.flush()
    except (OSError, ValueError):
        pass


class _Res(unittest.TextTestResult):
    def startTest(self, test):
        _emit({"ev": "inicio", "t": test.id()})
        super(_Res, self).startTest(test)

    def addSuccess(self, test):
        super(_Res, self).addSuccess(test)
        _emit({"ev": "res", "t": test.id(), "r": "ok"})

    def addFailure(self, test, err):
        super(_Res, self).addFailure(test, err)
        _emit({"ev": "res", "t": test.id(), "r": "fail"})

    def addError(self, test, err):
        super(_Res, self).addError(test, err)
        _emit({"ev": "res", "t": str(getattr(test, "id", lambda: test)()), "r": "error"})

    def addSkip(self, test, reason):
        super(_Res, self).addSkip(test, reason)
        _emit({"ev": "res", "t": test.id(), "r": "skip"})

    def addExpectedFailure(self, test, err):
        super(_Res, self).addExpectedFailure(test, err)
        _emit({"ev": "res", "t": test.id(), "r": "xfail"})

    def addUnexpectedSuccess(self, test):
        super(_Res, self).addUnexpectedSuccess(test)
        _emit({"ev": "res", "t": test.id(), "r": "xpass"})

    def addSubTest(self, test, subtest, err):
        super(_Res, self).addSubTest(test, subtest, err)
        if err is not None:
            _emit({"ev": "res", "t": test.id(), "r": "fail"})


class _Runner(unittest.TextTestRunner):
    resultclass = _Res
    resultado = None

    def run(self, test):
        r = super(_Runner, self).run(test)
        _Runner.resultado = r
        return r


unittest.main(module=None, testRunner=_Runner, exit=False)
r = _Runner.resultado
if r is not None:
    _emit({"ev": "fim", "run": r.testsRun})
_canal.close()
sys.exit(0 if r is not None and r.wasSuccessful() and r.testsRun > len(r.skipped) else 1)
'''

_PLUGIN_PYTEST = r'''
import json, os
_fd = int(os.environ.pop("CO_G1_CANAL"))
os.set_inheritable(_fd, False)
_canal = os.fdopen(_fd, "w", buffering=1)


def _emit(d):
    try:
        _canal.write(json.dumps(d) + "\n")
        _canal.flush()
    except (OSError, ValueError):
        pass


def pytest_runtest_logreport(report):
    xf = hasattr(report, "wasxfail")
    if report.when == "call":
        r = ("xpass" if xf else "ok") if report.passed else ("xfail" if xf else "skip") if report.skipped else "fail"
    elif report.when == "setup" and not report.passed:
        r = ("xfail" if xf else "skip") if report.skipped else "error"
    elif report.when == "teardown" and report.failed:
        r = "error"
    else:
        return
    _emit({"ev": "res", "t": report.nodeid, "r": r})


def pytest_runtest_logstart(nodeid, location):
    _emit({"ev": "inicio", "t": nodeid})


def pytest_sessionfinish(session, exitstatus):
    _emit({"ev": "fim", "run": None, "exit": int(exitstatus)})
'''


class SuiteNaoEstruturada(Exception):
    """Suíte registrada sem runner conhecido capaz de gravar relatório estruturado ⇒ FAIL."""


def _tokens_suite(cmd):
    lx = shlex.shlex(cmd, posix=True, punctuation_chars=True)
    lx.whitespace_split = True
    try:
        toks = list(lx)
    except ValueError as e:
        raise SuiteNaoEstruturada("comando ilegível: %s" % e)
    passos, atual = [], []
    for t in toks:
        if t in _SEPARADORES:
            if atual:
                passos.append(atual)
            atual = []
        elif t and all(c in "();<>|&" for c in t):
            raise SuiteNaoEstruturada("operador de shell %r não suportado (pipe/redireção/subshell)" % t)
        else:
            atual.append(t)
    if atual:
        passos.append(atual)
    return passos


def _runner_python(toks):
    """(interp, flags, modulo, args) para `python [flags] -m unittest|pytest args`, ou None."""
    if not toks or not (_PY_BIN.match(os.path.basename(toks[0])) or toks[0] == sys.executable):
        return None
    i, flags = 1, []
    while i < len(toks) and toks[i] != "-m":
        t = toks[i]
        if t in _PY_FLAGS_SOLTAS or re.match(r"^-[WX].+", t):
            flags.append(t)
            i += 1
        elif t in ("-W", "-X") and i + 1 < len(toks):
            flags += [t, toks[i + 1]]
            i += 2
        else:
            return None
    if i + 1 >= len(toks) or toks[i + 1] not in ("unittest", "pytest"):
        return None
    return toks[0], flags, toks[i + 1], toks[i + 2:]


def plano_suite(cmd):
    """Lista de passos: ("cd", dir) | ("unittest"|"pytest", env_extra, prefixo_argv, args). Levanta
    SuiteNaoEstruturada se algum passo não for `cd` nem um runner conhecido, ou se não houver runner."""
    passos = []
    for toks in _tokens_suite(cmd or ""):
        if toks[0] == "cd":
            if len(toks) != 2:
                raise SuiteNaoEstruturada("`cd` com argumentos inesperados: %r" % " ".join(toks))
            passos.append(("cd", os.path.expanduser(os.path.expandvars(toks[1]))))
            continue
        env_extra = {}
        while toks and _ENV_ATRIB.match(toks[0]):
            k, v = toks[0].split("=", 1)
            env_extra[k] = v
            toks = toks[1:]
        py = _runner_python(toks)
        if py:
            interp, flags, mod, args = py
            passos.append((mod, env_extra, [interp] + flags, args))
        elif toks and os.path.basename(toks[0]) in ("pytest", "py.test"):
            passos.append(("pytest", env_extra, [toks[0]], toks[1:]))
        else:
            raise SuiteNaoEstruturada("runner desconhecido %r: sem relatório estruturado (junit/json) gerado pelo "
                                      "próprio runner, saída impressa não conta" % " ".join(toks)[:120])
    if not any(p[0] != "cd" for p in passos):
        raise SuiteNaoEstruturada("nenhum runner de teste no comando")
    return passos


def _ler_canal(fd, linhas):
    with os.fdopen(fd, "rb") as fh:
        for ln in fh:
            linhas.append(ln)


def _eventos_do_canal(linhas, mod):
    """Agrega os eventos do canal do processo testado. O processo testado só emite fatos por teste; quem conta,
    decide e grava o relatório (com o nonce) é o G1, em outro processo. (tot, erro)."""
    inicios, res, fim = [], [], []
    for b in linhas:
        try:
            e = json.loads(b.decode("utf-8"))
        except ValueError:
            return None, "canal do runner com linha inválida"
        if not isinstance(e, dict) or e.get("ev") not in ("inicio", "res", "fim"):
            return None, "canal do runner com evento inválido"
        if e["ev"] == "fim":
            fim.append(e)
        elif not isinstance(e.get("t"), str):
            return None, "canal do runner com evento sem id de teste"
        elif e["ev"] == "inicio":
            inicios.append(e["t"])
        elif e.get("r") in ("ok", "fail", "error", "skip", "xfail", "xpass"):
            res.append((e["t"], e["r"]))
        else:
            return None, "canal do runner com resultado inválido"
    if not fim:
        return None, "execução incompleta: o runner não sinalizou o fim (saída prematura/os._exit?)"
    if len(fim) > 1 or [x for x in linhas[-1:] if json.loads(x.decode("utf-8")).get("ev") != "fim"]:
        return None, "canal do runner com fim duplicado ou fora de ordem"
    com_res = set(t for t, _r in res)
    sem_res = [t for t in inicios if t not in com_res]
    if sem_res:
        return None, "teste iniciado sem resultado: %s" % ", ".join(sem_res[:5])
    n = len(set(inicios) | com_res)
    if mod == "unittest":
        if fim[0].get("run") != len(inicios):
            return None, "contagem do runner (%r) ≠ testes iniciados no canal (%d)" % (fim[0].get("run"), len(inicios))
        n = len(inicios)
    cont = {}
    for _t, r in res:
        cont[r] = cont.get(r, 0) + 1
    return {"run": n, "failures": cont.get("fail", 0), "errors": cont.get("error", 0),
            "skipped": cont.get("skip", 0), "expected_failures": cont.get("xfail", 0),
            "unexpected_successes": cont.get("xpass", 0)}, None


def _executa_runner(passo, cwd, env, tmpdir, idx):
    """Roda UM passo da suíte num processo filho que só emite eventos por teste num pipe herdado. O relatório
    estruturado é escrito e validado por ESTE processo, num diretório que o filho desconhece, com um nonce que o
    filho nunca vê (o código sob teste não consegue reescrever o relatório)."""
    mod, env_extra, prefixo, args = passo
    env2 = dict(env, **env_extra)
    r_fd, w_fd = os.pipe()
    if mod == "unittest":
        wrapper = os.path.join(tmpdir, "co_g1_unittest_%d.py" % idx)
        with open(wrapper, "w", encoding="utf-8") as fh:
            fh.write(_WRAPPER_UNITTEST)
        argv = prefixo + [wrapper, str(w_fd)] + args
    else:
        plug_dir = os.path.join(tmpdir, "plugin-%d" % idx)
        os.makedirs(plug_dir)
        nome = "co_g1_canal_%s" % secrets.token_hex(4)
        with open(os.path.join(plug_dir, nome + ".py"), "w", encoding="utf-8") as fh:
            fh.write(_PLUGIN_PYTEST)
        env2["PYTHONPATH"] = plug_dir + (os.pathsep + env2["PYTHONPATH"] if env2.get("PYTHONPATH") else "")
        env2["CO_G1_CANAL"] = str(w_fd)
        argv = prefixo + ["-p", nome] + args
    linhas = []
    saida = tempfile.TemporaryFile()
    try:
        try:
            proc = subprocess.Popen(argv, cwd=cwd, env=env2, stdin=subprocess.DEVNULL, stdout=saida,
                                    stderr=subprocess.STDOUT, pass_fds=(w_fd,))
        except BaseException:
            os.close(r_fd)
            raise
        finally:
            os.close(w_fd)
        leitor = threading.Thread(target=_ler_canal, args=(r_fd, linhas))
        leitor.daemon = True
        leitor.start()
        try:
            rc = proc.wait(timeout=1800)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            raise
        leitor.join(15)
        saida.seek(0)
        out = saida.read().decode("utf-8", "replace")
    finally:
        saida.close()
    if leitor.is_alive():
        return None, rc, out, "%s: canal do runner não fechou (processo filho preso)" % mod
    tot, erro = _eventos_do_canal(linhas, mod)
    if erro:
        return None, rc, out, "%s: %s" % (mod, erro)
    # relatório estruturado: escrito e validado só por este processo (dir privado + nonce)
    privado = tempfile.mkdtemp(prefix="co-g1-rel-")
    try:
        nonce = secrets.token_hex(16)
        rel = os.path.join(privado, "relatorio-%d.json" % idx)
        grava_json(rel, dict(tot, nonce=nonce, runner=mod, completo=True, exit=rc))
        with open(rel, encoding="utf-8") as fh:
            d = json.load(fh)
        if d.get("nonce") != nonce or d.get("runner") != mod or not d.get("completo"):
            return None, rc, out, "%s: relatório estruturado inválido (nonce)" % mod
    finally:
        shutil.rmtree(privado, ignore_errors=True)
    return d, rc, out, None


def _uma_suite(nome, cmd, cwd):
    try:
        passos = plano_suite(cmd)
    except SuiteNaoEstruturada as e:
        return "FAIL", None, "%s: %s" % (nome, e)
    # bytecode isolado: um .pyc velho (mesmo mtime/tamanho) não pode mascarar a fonte atual
    tmpdir = tempfile.mkdtemp(prefix="co-g1-")
    cache = os.path.join(tmpdir, "pyc")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPYCACHEPREFIX=cache)
    cur = cwd if cwd and os.path.isdir(cwd) else os.getcwd()
    tot = {"run": 0, "failures": 0, "errors": 0, "skipped": 0, "unexpected_successes": 0}
    try:
        for i, passo in enumerate(passos):
            if passo[0] == "cd":
                alvo = passo[1] if os.path.isabs(passo[1]) else os.path.join(cur, passo[1])
                if not os.path.isdir(alvo):
                    return "ERRO", 1, "%s: cd %s: diretório inexistente" % (nome, passo[1])
                cur = alvo
                continue
            try:
                d, rc, out, erro = _executa_runner(passo, cur, env, tmpdir, i)
            except subprocess.TimeoutExpired:
                return "ERRO", None, "%s: timeout" % nome
            except OSError as e:
                return "ERRO", 127, "%s: ferramenta ausente: %s" % (nome, e)
            cauda = out.strip()[-400:]
            if erro:
                if rc in (126, 127) or re.search(r"No module named (?:'?pytest'?|'?unittest'?)", out):
                    return "ERRO", rc, "%s: ferramenta ausente (exit %s): %s" % (nome, rc, cauda)
                return "FAIL", rc if rc else 1, "%s: %s (exit %s): %s" % (nome, erro, rc, cauda)
            for k in tot:
                tot[k] += int(d.get(k) or 0)
            if rc != 0:
                return "FAIL", rc, "%s: exit %s; relatório: %s: %s" % (nome, rc, _fmt_tot(d), cauda)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    executados = tot["run"] - tot["skipped"]
    if tot["failures"] or tot["errors"] or tot["unexpected_successes"]:
        return "FAIL", 1, "%s: relatório estruturado com falha: %s" % (nome, _fmt_tot(tot))
    if executados < 1:
        return "FAIL", 0, "%s: exit 0 sem nenhum teste executado (relatório estruturado: %s)" % (nome, _fmt_tot(tot))
    return "PASS", 0, "%s: relatório estruturado do runner: %d teste(s) executado(s), %s, exit 0" % (
        nome, executados, _fmt_tot(tot))


def _fmt_tot(d):
    return "run=%s failures=%s errors=%s skipped=%s" % (d.get("run"), d.get("failures"), d.get("errors"),
                                                       d.get("skipped"))


def g1_suites(ws, obra=None, obra_divergente=None):
    obra = ler_obra(ws) if obra is None else obra
    if obra_divergente:  # A4: a suíte só vale se for a registrada (obra.json5 conferida contra premissas_ok)
        cmd = "; ".join(s.get("cmd", "") for s in obra.get("suites") or [])
        return _res("G1", "FAIL", 1, cmd, obra_divergente, "suíte não é a registrada em premissas_ok")
    alvo = obra.get("alvo")
    suites = obra.get("suites") or []
    if not suites and obra.get("tipo") in ("skill", "agente", "harness-maquina") and alvo:
        suites = [{"nome": "unit", "cmd": "python3 -m unittest discover -s %s/tests" % alvo}]
    cmd = "; ".join(s.get("cmd", "") for s in suites)
    if not suites:
        return _res("G1", "FAIL", None, cmd, "nenhuma suíte declarada em obra.json5", "sem suíte (falha fechada)")
    piores, evs, exit_ = [], [], 0
    for s in suites:
        st, ex, ev = _uma_suite(s.get("nome", "?"), s.get("cmd", ""), alvo)
        piores.append(st)
        evs.append(ev)
        if st != "PASS":
            exit_ = ex
    st = "ERRO" if "ERRO" in piores else "FAIL" if "FAIL" in piores else "PASS"
    return _res("G1", st, exit_ if st != "PASS" else 0, cmd, " | ".join(evs), None if st == "PASS" else "suíte reprovou")


# ------------------------------------------------------------------ G3/G4 via diff

class Diff:
    def __init__(self, paths, adicionadas):
        self.paths = paths            # list[str] relativos ao repo (old e new de rename, deleções, modo)
        self.adicionadas = adicionadas  # list[(path, linha)]


def _git(repo, *args):
    p = subprocess.run(["git", "-C", repo, "-c", "core.quotepath=off", "-c", "core.fileMode=true"] + list(args),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def coletar_diff(repo, base):
    if shutil.which("git") is None:
        raise Erro("git ausente")
    code, top, _ = _git(repo, "rev-parse", "--show-toplevel")
    if code != 0:
        raise Erro("--repo não é repositório git: %s" % repo)
    code, sha, _ = _git(repo, "rev-parse", "--verify", "--quiet", "%s^{commit}" % base)
    if code != 0 or not sha.strip():
        raise Erro("base inválida: %s" % base)
    base = sha.strip()
    paths = set()
    for extra in ([], ["--cached"]):
        code, out, err = _git(repo, "diff", "--no-ext-diff", "--name-status", "-z", "-M", "--find-copies",
                              *extra, base, "--")
        if code != 0:
            raise Erro("git diff falhou: %s" % err.strip())
        toks = out.split("\0")
        i = 0
        while i < len(toks) and toks[i]:
            st = toks[i]
            if st[:1] in ("R", "C"):
                paths.update(toks[i + 1:i + 3])
                i += 3
            else:
                paths.add(toks[i + 1])
                i += 2
    code, out, _ = _git(repo, "ls-files", "-z", "--others", "--exclude-standard")
    novos = [p for p in out.split("\0") if p]
    paths.update(novos)
    adic = []
    for extra in ([], ["--cached"]):
        code, out, _ = _git(repo, "diff", "--no-ext-diff", "--no-color", "-U0", "-M", *extra, base, "--")
        cur = None
        for ln in out.splitlines():
            if ln.startswith("+++ "):
                cur = None if ln[4:] == "/dev/null" else ln[6:] if ln.startswith("+++ b/") else ln[4:]
            elif ln.startswith("+") and cur is not None:
                adic.append((cur, ln[1:]))
    for p in novos:
        full = os.path.join(repo, p)
        try:
            if os.path.isfile(full) and os.path.getsize(full) <= 2 * 1024 * 1024:
                with open(full, "rb") as fh:
                    data = fh.read()
                if b"\0" not in data[:8192]:
                    adic.extend((p, x) for x in data.decode("utf-8", "replace").splitlines())
        except OSError:
            pass
    return Diff(sorted(paths), adic)


def glob_re(g):
    g = g.strip()
    while g.startswith("./"):
        g = g[2:]
    out, i = "", 0
    while i < len(g):
        c = g[i]
        if g.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif g.startswith("**", i):
            out += ".*"
            i += 2
        elif c == "*":
            out += "[^/]*"
            i += 1
        elif c == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(c)
            i += 1
    if g.endswith("/"):
        out += ".*"
    return re.compile("^" + out + "$")


def casa(path, globs):
    return any(glob_re(g).match(path) for g in globs)


def _protegidos_rel(repo, ws):
    """Caminhos protegidos (<ws>/.construcao, aprovacoes, oraculo) relativos ao repo, se ws estiver dentro dele."""
    if not ws:
        return []
    r, w = os.path.realpath(repo), os.path.realpath(ws)
    if w == r or w.startswith(r + os.sep):
        rel = os.path.relpath(w, r)
        pre = "" if rel == "." else rel + "/"
        return [pre + ".construcao/**", pre + "aprovacoes/**", pre + "oraculo/**"]
    return []


def g3_territorio(diff, writes, protegidos=()):
    fora = [p for p in diff.paths if not casa(p, writes)]
    prot = [p for p in diff.paths if protegidos and casa(p, protegidos)]
    if fora or prot:
        ev = []
        if fora:
            ev.append("fora de writes %s: %s" % (writes, ", ".join(fora[:20])))
        if prot:
            ev.append("em protegido: %s" % ", ".join(prot[:20]))
        return _res("G3", "FAIL", 1, "diff", "; ".join(ev), "território violado")
    return _res("G3", "PASS", 0, "diff", "%d caminho(s) no diff, todos em %s" % (len(diff.paths), writes), None)


_TESTE_PATHS = ["tests/**", "test/**", "**/tests/**", "**/test/**", "**/test_*.py", "**/*_test.py", "test_*.py",
                "*_test.py", "**/conftest.py", "conftest.py", "pytest.ini", "**/pytest.ini", "tox.ini", ".coveragerc",
                "noxfile.py", "**/__tests__/**", "**/*.test.*", "**/*.spec.*", "*.test.*", "*.spec.*"]
_CFG_TESTE = re.compile(r"\[(?:tool[:.])?pytest|\[tool\.coverage|\[coverage:|testpaths|addopts")

_GAMING = [
    ("skip/xfail", re.compile(r"\bpytest\.(?:skip|xfail|importorskip)\s*\(|@pytest\.mark\.(?:skip|skipif|xfail)\b|"
                              r"@unittest\.(?:skip|skipIf|skipUnless|expectedFailure)\b|\bunittest\.skip\w*\s*\(|"
                              r"\.skipTest\s*\(|raise\s+(?:unittest\.)?SkipTest\b|\b(?:it|describe|test)\.skip\s*\(|"
                              r"(?<![\w.])xit\s*\(")),
    ("sys.exit(0)", re.compile(r"(?:\bsys\.|(?<![\w.]))(?:exit|quit)\s*\(\s*(?:0|None|False|0x0)?\s*\)|"
                               r"\braise\s+SystemExit\s*(?:\(\s*(?:0|None)?\s*\))?\s*(?:#.*)?$|"
                               r"\bprocess\.exit\s*\(\s*0?\s*\)")),
    ("os._exit", re.compile(r"\bos\._exit\s*\(")),
    ("assert True", re.compile(r"^\s*assert\s+(?:True|1|not\s+False|not\s+None|\(\s*True\s*\))\s*(?:,.*)?(?:#.*)?$")),
    ("except: pass", re.compile(r"^\s*except\b[^:]*:\s*(?:pass|\.\.\.)\s*(?:#.*)?$")),
    ("__eq__ novo", re.compile(r"\bdef\s+__(?:eq|ne)__\s*\(|\b__(?:eq|ne)__\s*=")),
    ("monkeypatch de avaliador", re.compile(r"\b(?:unittest\.)?TestCase\.\w+\s*=|setattr\(\s*(?:unittest|pytest|builtins|"
                                            r"TestCase|sys\.modules)|sys\.modules\[\s*['\"](?:unittest|pytest|_pytest)|"
                                            r"\bbuiltins\.\w+\s*=")),
]
_GAMING += [
    # R3-8: saída/skip por getattr/__import__, skip importado (com ou sem alias), asserção tautológica em TestCase
    ("exit por getattr", re.compile(r"\bgetattr\s*\(\s*[\w.]+\s*,\s*['\"](?:exit|_exit|quit|abort|kill|skip\w*|xfail|"
                                    r"importorskip|SkipTest)['\"]|\b__import__\s*\(\s*['\"](?:os|sys)['\"]\s*\)\s*\."
                                    r"(?:_?exit|abort)\b|\bimportlib\.import_module\s*\(\s*['\"](?:os|sys)['\"]\s*\)"
                                    r"\s*\.(?:_?exit|abort)\b")),
    ("skip importado", re.compile(r"^\s*from\s+(?:pytest|_pytest(?:\.\w+)*|unittest(?:\.\w+)*)\s+import\b.*\b(?:skip\w*|"
                                  r"xfail|importorskip|SkipTest|expectedFailure)\b")),
    ("exit importado", re.compile(r"^\s*from\s+(?:os|sys|builtins)\s+import\b.*\b(?:_exit|exit|quit|abort)\b\s+as\b|"
                                  r"^\s*from\s+os\s+import\b.*\b(?:_exit|abort)\b")),
    ("skip por atributo", re.compile(r"\.\s*(?:skipIf|skipUnless|expectedFailure|importorskip|xfail|SkipTest)\b")),
    ("assert tautológico", re.compile(r"\bassert(?:True|_)?\s*\(\s*(?:True|1|not\s+(?:False|None|0))\s*[,)]|"
                                      r"\bassertFalse\s*\(\s*(?:False|None|0)\s*[,)]|"
                                      r"\bassert(?:Is)?None\s*\(\s*None\s*[,)]|"
                                      r"^\s*assert\s+(?:True|1|not\s+(?:False|None|0)|\(\s*(?:True|1)\s*\))\s*(?:[,;].*)?(?:#.*)?$")),
]
_IMPORT_ALIAS = re.compile(r"^\s*from\s+(pytest|_pytest(?:\.\w+)*|unittest(?:\.\w+)*|os|sys|builtins)\s+import\s+"
                           r"\(?\s*(.+?)\s*\)?\s*(?:#.*)?$")
_IMPORT_MOD_ALIAS = re.compile(r"^\s*import\s+(.+?)\s*(?:#.*)?$")
_NOMES_GAMING = {"skip", "skipIf", "skipUnless", "expectedFailure", "xfail", "importorskip", "SkipTest", "exit", "_exit",
                 "quit", "abort"}
_MODS_GAMING = {"pytest", "unittest", "os", "sys", "builtins", "_pytest"}


def _aliases_gaming(linhas):
    """(nomes, modulos): nomes locais ligados a skip/exit importados (`from pytest import skip as s`) e aliases de
    módulos de teste/saída (`import unittest as u`, `import sys as s`)."""
    nomes, mods = set(), set()
    for ln in linhas:
        m = _IMPORT_ALIAS.match(ln)
        if m:
            for parte in m.group(2).split(","):
                ps = parte.strip().split()
                if ps and ps[0] in _NOMES_GAMING:
                    nomes.add(ps[2] if len(ps) == 3 and ps[1] == "as" else ps[0])
            continue
        m = _IMPORT_MOD_ALIAS.match(ln)
        if m:
            for parte in m.group(1).split(","):
                ps = parte.strip().split()
                if ps and ps[0].split(".")[0] in _MODS_GAMING and len(ps) == 3 and ps[1] == "as":
                    mods.add(ps[2])
    return nomes, mods


_ARG_SAIDA_OK = r"\s*\(\s*(?:0|None|False|0x0)?\s*\)"


def _gaming_por_alias(ln, nomes, mods):
    """Uso de nome/módulo importado por alias. Saída só conta com código de sucesso (`exit(0)`/`exit()`), para não
    acusar `exit(main())`; `_exit`/`abort` e skip contam sempre."""
    for n in nomes:
        q = re.escape(n)
        if re.search(r"(?<![\w.])%s\s*\(" % q, ln) and n not in ("exit", "quit") or \
                re.search(r"(?<![\w.])%s%s" % (q, _ARG_SAIDA_OK), ln) or re.search(r"@\s*%s\b" % q, ln):
            return "chamada de %s importado" % n
    for m in mods:
        q = re.escape(m)
        if re.search(r"(?<![\w.])%s\s*\.\s*(?:skip\w*|xfail|importorskip|SkipTest|expectedFailure|_exit|abort)\b" % q, ln) \
                or re.search(r"(?<![\w.])%s\s*\.\s*(?:exit|quit)%s" % (q, _ARG_SAIDA_OK), ln):
            return "skip/exit via alias %s" % m
    return None


_EXCEPT = re.compile(r"^\s*except\b[^:]*:\s*(?:#.*)?$")
_PASS = re.compile(r"^\s*(?:pass|\.\.\.)\s*(?:#.*)?$")


def literais_heldout(ws, minimo=6):
    lits = set()
    base = os.path.join(ws, "oraculo", "heldout") if ws else None
    if not base or not os.path.isdir(base):
        return lits

    def walk(o):
        if isinstance(o, str):
            if len(o.strip()) >= minimo:
                lits.add(o)
        elif isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    for raiz, _dirs, files in os.walk(base):
        for f in files:
            if f.endswith((".json", ".json5")):
                try:
                    walk(json5_load(os.path.join(raiz, f)))
                except Exception:
                    continue
    return lits


def g4_gaming(diff, literais=()):
    achados = []
    for p in diff.paths:
        if casa(p, _TESTE_PATHS):
            achados.append("toque em teste/config de teste: %s" % p)
        if casa(p, ["oraculo/**", "**/oraculo/**"]):
            achados.append("toque no oráculo: %s" % p)
    cfg = {"setup.cfg", "pyproject.toml", "package.json"}
    prev = {}
    por_arquivo = {}
    for path, ln in diff.adicionadas:
        por_arquivo.setdefault(path, []).append(ln)
    aliases = {p: _aliases_gaming(lns) for p, lns in por_arquivo.items()}
    for path, ln in diff.adicionadas:
        s = ln.strip()
        for lit in literais:
            if lit in ln:
                achados.append("literal do held-out em %s: %r" % (path, s[:120]))
                break
        if os.path.basename(path) in cfg and _CFG_TESTE.search(ln):
            achados.append("config de teste alterada em %s: %r" % (path, s[:120]))
        if not s or s.startswith(("#", "//")):
            continue
        for nome, rx in _GAMING:
            if rx.search(ln):
                achados.append("%s em %s: %r" % (nome, path, s[:120]))
        via = _gaming_por_alias(ln, *aliases[path])
        if via:
            achados.append("%s em %s: %r" % (via, path, s[:120]))
        if _PASS.match(ln) and _EXCEPT.match(prev.get(path, "")):
            achados.append("except: pass em %s" % path)
        prev[path] = ln
    if achados:
        return _res("G4", "FAIL", 1, "diff", "; ".join(achados[:30]), "gaming no diff")
    return _res("G4", "PASS", 0, "diff", "%d linha(s) adicionada(s) sem padrão de gaming" % len(diff.adicionadas), None)


def avaliar_diff(repo, base, writes, ws=None):
    d = coletar_diff(repo, base)
    return [g3_territorio(d, writes, _protegidos_rel(repo, ws)), g4_gaming(d, literais_heldout(ws))]


# ------------------------------------------------------------------ demais gates (fora do núcleo da onda 1)

def _nao_implementado(gid):
    def f(*_a, **_k):
        return _res(gid, "ERRO", None, "", "checagem %s não implementada na onda 1" % gid, "falha fechada")
    f.__name__ = "g_" + gid
    return f


g2_runtimes = _nao_implementado("G2")
g5_forca_oraculo = _nao_implementado("G5")
g6_superficie = _nao_implementado("G6")


def g7_checks_provam_efeito(ws=None, *_a, **_k):
    """G-5: G7 = `portao selftest` (portoes.json5#G7.cmd): cada check de gate tem par negativo plantado (stub que
    sai 0 sem efeito ⇒ o check reprova). Roda em processo separado a partir DESTE arquivo (uma cópia sabotada roda
    o próprio selftest sabotado e reprova). Exit 0 ⇒ PASS; 1 ⇒ FAIL; outro/ausente/timeout ⇒ ERRO."""
    script = os.path.realpath(__file__)
    cmd = "co.py%s portao selftest" % (" --work %s" % ws if ws else "")
    try:
        # importa o módulo inteiro (como co.py faz) em vez de rodá-lo como __main__: o que vier depois do bloco
        # `if __name__ == "__main__"` também vale para o selftest
        boot = ("import sys; sys.path.insert(0, %r); sys.dont_write_bytecode = True; import co_portao; "
                "sys.exit(co_portao.main(['portao', 'selftest']))" % os.path.dirname(script))
        p = subprocess.run([sys.executable, "-c", boot], stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=900)
    except subprocess.TimeoutExpired:
        return _res("G7", "ERRO", None, cmd, "portao selftest: timeout", "falha fechada")
    except OSError as e:
        return _res("G7", "ERRO", 127, cmd, "portao selftest não rodou: %s" % e, "falha fechada")
    out = (p.stdout or "").strip()
    falhou = [ln for ln in out.splitlines() if ln.startswith("FALHOU")]
    ok_lin = [ln for ln in out.splitlines() if ln.startswith("ok  ")]
    if p.returncode == 0 and not falhou and ok_lin and out.endswith("portao selftest: ok"):
        return _res("G7", "PASS", 0, cmd, "portao selftest: %d check(s) com par negativo, todos ok" % len(ok_lin),
                    None)
    if p.returncode in (0, 1):
        ev = "; ".join(falhou[:10]) or out[-600:]
        return _res("G7", "FAIL", 1, cmd, "portao selftest reprovou (exit %d): %s" % (p.returncode, ev),
                    "check que aceita stub sem efeito")
    return _res("G7", "ERRO", p.returncode, cmd, out[-600:], "falha fechada")
g8_maquina = _nao_implementado("G8")
g9_e2e = _nao_implementado("G9")
g10_instalacao_limpa = _nao_implementado("G10")
g11_upgrade_legado = _nao_implementado("G11")
g12_docs_cli = _nao_implementado("G12")
g13_medicao = _nao_implementado("G13")
g14_pontos = _nao_implementado("G14")


def _res(gid, status, exit_, cmd, evidencia, motivo, aprovacao=None):
    return {"id": gid, "status": status, "exit": exit_, "cmd": cmd, "evidencia": evidencia or "(vazio)",
            "motivo": motivo, "aprovacao": aprovacao}


# ------------------------------------------------------------------ rodar / gate-report

def sistema_hash(alvo):
    """formatos.convencoes.hash_sistema — MESMO cálculo de co_estado.hash_sistema (V4-7: o relatório e o veredito
    comparam o mesmo hash). Sem alvo ⇒ hash da lista vazia."""
    f = getattr(co_estado, "hash_sistema", None)
    if callable(f) and alvo and os.path.isdir(alvo):
        return f(alvo)
    files = []
    if alvo and os.path.isdir(alvo):
        for raiz, dirs, fs in os.walk(alvo):
            dirs[:] = sorted(d for d in dirs if d not in (".git", "__pycache__"))
            files.extend(os.path.join(raiz, f) for f in fs if not f.endswith((".pyc", ".pyo")))
    return sha_files(files)


def _g_diff_portao(ws, obra, gid, recs):
    div = divergencias_registradas(ws, recs)
    if "obra" in div:  # base/alvo vêm da obra: reescrita ⇒ o diff não é o registrado
        return _res(gid, "FAIL", 1, "diff", div["obra"], "obra.json5 não é a registrada (falha fechada)")
    base = obra.get("base")
    plano_p = os.path.join(ws, "PLANO.json5")
    if not base or not os.path.isfile(plano_p):
        return _res(gid, "ERRO", None, "co.py --work %s diff <task> --base <sha>" % ws,
                    "sem base/PLANO no portão: rode `co.py diff <task> --base <sha>` por task", "falha fechada")
    writes = []
    for t in json5_load(plano_p).get("tasks") or []:
        writes.extend(t.get("writes") or [])
    try:
        r3, r4 = avaliar_diff(obra.get("alvo"), base, writes, ws)
    except Erro as e:
        return _res(gid, "ERRO", 2, "diff", str(e), "falha fechada")
    return _reprova_g3(r3, problemas_territorio_registrado(ws, recs, writes)) if gid == "G3" else r4


def _nomes_waiver(gid):
    """Nomes de portão humano que dispensam o item `gid` (a aprovação tem de ser DESTE item)."""
    return (gid, "waiver-" + gid, "waiver:" + gid)


def waiver_aprovado(ws, gid, recs, sujas=None):
    """Arquivo da aprovação válida (problema_waiver None) que dispensa o PRÓPRIO item `gid`, ou None. A mais recente
    vence; aprovação de outro portão (entrega, plano, outro G) nunca vale."""
    for r in reversed(recs or []):
        pl = r.get("payload") or {}
        if r.get("evento") != "aprovacao" or pl.get("portao") not in _nomes_waiver(gid) or \
                pl.get("decisao") != "aprovado" or not isinstance(pl.get("arquivo"), str):
            continue
        if problema_waiver(ws, pl["arquivo"], recs, sujas, item=gid) is None:
            return pl["arquivo"]
    return None


def rodar(ws, only=None, final=False):
    ws = os.path.realpath(ws)
    obra = ler_obra(ws)
    reg = ler_regressao(ws)
    recs = ler_ledger(ws)
    # V4-2: aplicabilidade/waiver vêm do contrato por tipo; regressao.json5 só acrescenta exigência
    por_id = regressao_efetiva(reg, obra.get("tipo"))
    if only:
        ids = list(only)
    else:  # A2: o núcleo é sempre avaliado, ainda que desligado ou removido de regressao.json5
        presentes = set(por_id) | set(SEM_WAIVER_NUCLEO)
        ids = [g for g in GIDS if g in presentes] + sorted(g for g in por_id if g not in GIDS)
    div = divergencias_registradas(ws, recs)
    itens = []
    for gid in ids:
        it = por_id.get(gid)
        t0 = time.time()
        if gid == "G0":
            r = g0_oraculo_intacto(ws, recs)
        elif gid == "G1":
            r = g1_suites(ws, obra, div.get("obra"))
        elif gid in ("G3", "G4"):
            r = _g_diff_portao(ws, obra, gid, recs)
        elif it is None:
            r = _res(gid, "ERRO", None, "", "item ausente de regressao.json5", "falha fechada")
        elif not it.get("aplica"):
            r = _res(gid, "NA", None, it.get("cmd", ""), "N/A", it.get("na_motivo") or "não aplicável")
        elif gid not in CHECAGENS:
            r = _res(gid, "ERRO", None, it.get("cmd", ""), "item sem checagem conhecida", "falha fechada")
        else:
            r = globals()[CHECAGENS[gid]](ws)
        if r.get("status") not in ("PASS", "NA") and it is not None and it.get("waiver") \
                and gid not in sem_waiver_contrato():
            ap = waiver_aprovado(ws, gid, recs)  # WAIVED só com aprovação válida do PRÓPRIO item
            if ap:
                r = _res(gid, "WAIVED", r.get("exit"), r.get("cmd", ""), "%s | dispensado por aprovação %s"
                         % (r.get("evidencia"), os.path.basename(ap)), "waiver aprovado", aprovacao=ap)
        r["duracao_s"] = round(time.time() - t0, 3)
        itens.append(r)
    simulado = _simulado(recs)
    v, motivo, _f, _w = calcular_veredito(itens, reg, simulado, exigir_todos=not only, ws=ws, recs=recs,
                                          tipo=obra.get("tipo"))
    extra = [div[k] for k in ("regressao", "obra", "plano") if k in div]
    extra += ["ledger: %s" % p for p in problemas_ledger(ws, recs)]
    if extra:
        v, motivo = "NO-GO", "; ".join(([motivo] if v == "NO-GO" else []) + extra)
    rep = {"schema_version": 1, "ts": now_ts(), "seq_ledger": recs[-1]["seq"] if recs else 0,
           "final": bool(final) and not only, "only": list(only) if only else None,
           "sistema_hash": sistema_hash(obra.get("alvo")),
           "regressao_hash": sha_file(os.path.join(ws, "regressao.json5")), "itens": itens, "veredito": v,
           "motivo": motivo}
    if only:  # A1: relatório parcial nunca vale como regressão nem entrega (final=false, veredito NO-GO)
        rep.update(parcial=True, final_pedido=bool(final), veredito_parcial=v, veredito="NO-GO",
                   motivo="relatório parcial (--only %s) não vale como regressão/entrega; nos itens rodados: %s"
                   % (",".join(only), v))
    grava_json(os.path.join(ws, "gate-report.json"), rep)
    return rep


CHECAGENS = {"G0": "g0_oraculo_intacto", "G1": "g1_suites", "G2": "g2_runtimes", "G3": "g3_territorio",
             "G4": "g4_gaming", "G5": "g5_forca_oraculo", "G6": "g6_superficie", "G7": "g7_checks_provam_efeito",
             "G8": "g8_maquina", "G9": "g9_e2e", "G10": "g10_instalacao_limpa", "G11": "g11_upgrade_legado",
             "G12": "g12_docs_cli", "G13": "g13_medicao", "G14": "g14_pontos"}


# ------------------------------------------------------------------ veredito

def _simulado(recs):
    return any(r.get("evento") == "medicao_registrada" and (r.get("payload") or {}).get("simulated") is True
               for r in recs)


def problema_waiver(ws, ap, recs=None, sujas=None, item=None):
    """Motivo pelo qual `ap` NÃO vale como aprovação de waiver DO ITEM `item`, ou None. `item` (G-id dispensado) é
    obrigatório: o `portao` da aprovação (arquivo e evento) tem de ser o próprio item (`Gn`, `waiver-Gn` ou
    `waiver:Gn`) — aprovação de outro portão humano (entrega, plano, outro G) nunca dispensa item; item que o
    contrato marca sem waiver nunca é dispensado. Exige ainda: caminho .json dentro de
    <ws>/aprovacoes/ (realpath; nunca o aprovar-<portao>.sh, nunca symlink para fora), JSON objeto no formato
    formatos.aprovacao com `portao`, `decisao` = "aprovado" e `seq` inteiro; o ledger tem, nesse seq, o evento
    `aprovacao` do mesmo portão, decisão aprovado e `arquivo` = este arquivo; e a linha `tipo aprovacao` desse seq
    está no audit, que fica FORA do ws (`sujas` = aprovacoes_sem_audit, injetável só pelo selftest)."""
    if not isinstance(ap, str) or not ap.strip():
        return "sem arquivo de aprovação"
    if ws is None:
        return "sem workspace para conferir a aprovação"
    wsr = os.path.realpath(ws)
    raiz = os.path.join(wsr, "aprovacoes") + os.sep
    real = os.path.realpath(ap if os.path.isabs(ap) else os.path.join(ws, ap))
    if not real.startswith(raiz):
        return "aprovação fora de <ws>/aprovacoes/: %s" % ap
    if not real.endswith(".json") or os.path.basename(real).startswith("aprovar-"):
        return "aprovação não é um <portao>-<seq>.json (o .sh gerado nunca vale): %s" % ap
    if not os.path.isfile(real):
        return "arquivo de aprovação ausente: %s" % ap
    try:
        with open(real, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as e:
        return "aprovação ilegível (%s): %s" % (type(e).__name__, ap)
    if not isinstance(doc, dict) or not isinstance(doc.get("portao"), str) or not doc["portao"].strip():
        return "aprovação sem `portao`: %s" % ap
    if doc.get("decisao") != "aprovado":
        return "aprovação com decisão %r (≠ aprovado): %s" % (doc.get("decisao"), ap)
    if not isinstance(item, str) or item not in GIDS:
        return "item dispensado não informado/inválido (%r): a aprovação tem de ser do próprio item" % (item,)
    if item in sem_waiver_contrato():
        return "%s não admite waiver (contrato.sem_waiver)" % item
    if doc["portao"] not in _nomes_waiver(item):
        return "aprovação do portão %r não dispensa %s (exige portão %s): %s" % (doc["portao"], item, item, ap)
    sq = doc.get("seq")
    if not isinstance(sq, int) or isinstance(sq, bool):
        return "aprovação sem `seq` (não ancorada no ledger): %s" % ap
    regs = recs or []
    r = regs[sq - 1] if 1 <= sq <= len(regs) else None
    pl = (r or {}).get("payload") or {}
    if r is None or r.get("seq") != sq or r.get("evento") != "aprovacao" or pl.get("portao") != doc["portao"] or \
            pl.get("decisao") != "aprovado":
        return "aprovação seq %s sem evento `aprovacao` aprovado do portão %s no ledger: %s" % (sq, doc["portao"], ap)
    arq = pl.get("arquivo")
    if not isinstance(arq, str) or os.path.realpath(arq) != real:
        return "evento `aprovacao` seq %s cita outro arquivo (%s): %s" % (sq, arq, ap)
    if sujas is None:
        aud = os.path.realpath(audit_path())
        if aud == wsr or aud.startswith(wsr + os.sep):
            return "audit dentro do ws (%s): não vale como testemunha" % aud
        sujas = aprovacoes_sem_audit(ws, regs)
    if arq in set(sujas) or "seq %s" % sq in set(sujas):
        return "aprovação seq %s sem linha limpa no audit: %s" % (sq, ap)
    return None


def calcular_veredito(itens, reg, simulado, exigir_todos=True, ws=None, recs=None, _sujas=None, tipo=None):
    """(veredito, motivo, falhas, waivers). Recalcula sempre; nunca confia no `veredito` gravado. V4-2: a
    aplicabilidade vem do contrato pelo tipo do alvo (`tipo` ou obra.json5 do ws), não de regressao.json5."""
    if tipo is None:
        tipo = tipo_da_obra(ws)
    regi = regressao_efetiva(reg, tipo)
    sem_waiver_c = sem_waiver_contrato()
    falhas, waivers, motivos = [], [], []
    vistos = {}
    for r in itens:
        gid = r.get("id")
        if gid in vistos:
            falhas.append(gid)
            motivos.append("%s duplicado no relatório" % gid)
            continue
        vistos[gid] = r
        it = regi.get(gid)
        st = r.get("status")
        if it is None:
            falhas.append(gid)
            motivos.append("%s fora da regressão" % gid)
            continue
        sem_waiver = (not it.get("waiver")) or gid in sem_waiver_c
        if st == "PASS":
            continue
        if st == "NA":
            if it.get("aplica"):
                falhas.append(gid)
                motivos.append("%s NA mas aplica" % gid)
            continue
        if st == "WAIVED":
            prob_ap = problema_waiver(ws, r.get("aprovacao"), recs, _sujas, item=gid)
            if sem_waiver:
                falhas.append(gid)
                motivos.append("%s não admite waiver" % gid)
            elif prob_ap:
                falhas.append(gid)
                motivos.append("%s WAIVED sem aprovação válida (%s)" % (gid, prob_ap))
            else:
                waivers.append(gid)
            continue
        falhas.append(gid)
        motivos.append("%s %s" % (gid, st))
    if exigir_todos:
        for gid in regi:
            if gid not in vistos:
                falhas.append(gid)
                motivos.append("%s ausente do relatório" % gid)
    if falhas:
        return "NO-GO", "; ".join(motivos), falhas, waivers
    if simulado:
        return "GO (simulado)", "medição simulada no ledger (D10)", falhas, waivers
    if waivers:
        return "GO (com waiver)", "%s dispensado(s) por aprovação" % ", ".join(waivers), falhas, waivers
    return "GO", "todo item aplicável PASS, nenhum waiver", falhas, waivers


def audit_path():
    return os.path.expanduser("~/.claude/construcao-orquestrada/audit.jsonl")


def aprovacoes_sem_audit(ws, recs):
    """Cada `aprovacao` do ledger precisa da linha tipo aprovacao no audit (seq + work) e de nenhuma tool_call
    permitida que a tenha feito (formatos.audit.uso)."""
    linhas = []
    p = audit_path()
    if os.path.isfile(p):
        with open(p, encoding="utf-8", errors="replace") as fh:
            for x in fh:
                try:
                    linhas.append(json.loads(x))
                except ValueError:
                    continue
    w = os.path.realpath(ws)
    sujas = []
    for r in recs:
        if r.get("evento") != "aprovacao":
            continue
        pl = r.get("payload") or {}
        ref = pl.get("arquivo") or "seq %s" % r.get("seq")
        ok = any(a.get("tipo") == "aprovacao" and a.get("seq") == r.get("seq") and a.get("work")
                 and os.path.realpath(a["work"]) == w for a in linhas)
        tool = any(a.get("tipo") == "tool_call" and a.get("decisao") == "permitido"
                   and "aprovar" in (a.get("tokens") or []) and w in str(a.get("alvo", ""))
                   and str(pl.get("portao", "\0")) in str(a.get("alvo", "")) for a in linhas)
        if not ok or tool:
            sujas.append(ref)
    return sujas


def problema_relatorio_obsoleto(ws, rep):
    """V4-7: motivo se o `sistema_hash` do relatório ≠ hash atual do alvo (co_estado.hash_sistema) — o produto
    mudou depois do portão ⇒ "relatório obsoleto" (NO-GO); None se confere. Obra/alvo ilegível ⇒ motivo (falha
    fechada). Para a entrega (co_estado.relatorio_satisfaz_entrega) chamar o mesmo."""
    try:
        alvo = ler_obra(ws).get("alvo")
    except (Erro, OSError, ValueError, AttributeError) as e:
        return "relatório obsoleto: obra.json5 ilegível (%s)" % e
    if not isinstance(alvo, str) or not os.path.isdir(alvo):
        return "relatório obsoleto: alvo ausente (%r)" % (alvo,)
    gravado = rep.get("sistema_hash") if isinstance(rep, dict) else None
    try:
        atual = sistema_hash(alvo)
    except Exception as e:  # noqa: BLE001 — falha fechada
        return "relatório obsoleto: hash do alvo não calculável (%s)" % e
    if gravado != atual:
        return "relatório obsoleto: sistema_hash do gate-report (%s) ≠ hash atual do alvo (%s) — o alvo mudou " \
               "depois do portão; rode `portao run` de novo" % (str(gravado)[:12], atual[:12])
    return None


def veredito_detalhado(ws):
    ws = os.path.realpath(ws)
    rep_p = os.path.join(ws, "gate-report.json")
    reg_p = os.path.join(ws, "regressao.json5")
    if not os.path.isfile(rep_p):
        raise Erro("gate-report.json ausente: rode `co.py portao run`")
    if not os.path.isfile(reg_p):
        raise Erro("regressao.json5 ausente")
    with open(rep_p, "rb") as fh:
        bruto = fh.read()  # um só read: o hash conferido é o dos bytes avaliados (sem TOCTOU)
    h_rep = hashlib.sha256(bruto).hexdigest()
    try:
        rep = json.loads(bruto.decode("utf-8"))
    except ValueError as e:
        raise Erro("gate-report.json ilegível: %s" % e)
    if not isinstance(rep, dict):
        raise Erro("gate-report.json não é objeto")
    reg = json5_load(reg_p)
    recs = ler_ledger(ws)
    simulado = _simulado(recs)
    v, motivo, falhas, waivers = calcular_veredito(rep.get("itens") or [], reg, simulado, exigir_todos=True, ws=ws,
                                                   recs=recs)
    extra = []
    obs = problema_relatorio_obsoleto(ws, rep)  # V4-7
    if obs:
        extra.append(obs)
    # G-4: o relatório só vale se for o registrado — sha256 = gate_report_hash do ÚLTIMO portao_relatorio
    ult = _payload_ultimo(recs, "portao_relatorio")
    if ult is None:
        extra.append("gate-report.json sem evento portao_relatorio no ledger (relatório não ancorado)")
    else:
        gravado = (ult.get("payload") or {}).get("gate_report_hash")
        if gravado != h_rep:
            extra.append("gate-report.json (%s) ≠ gate_report_hash do último portao_relatorio (seq %s: %s) — "
                         "relatório reescrito depois do evento" % (h_rep[:12], ult.get("seq"), str(gravado)[:12]))
    if rep.get("regressao_hash") != sha_file(reg_p):
        extra.append("regressao_hash do relatório ≠ regressao.json5 atual")
    if rep.get("only") or rep.get("parcial"):
        extra.append("relatório parcial (only=%s): não vale como regressão" % (rep.get("only"),))
    div = divergencias_registradas(ws, recs)
    extra.extend(div[k] for k in ("regressao", "obra", "plano") if k in div)
    if not cadeia_ok(recs):
        extra.append("ledger com cadeia quebrada")
    else:
        extra.extend("ledger: %s" % p for p in problemas_ledger(ws, recs))
    sujas = aprovacoes_sem_audit(ws, recs)
    if sujas:
        extra.append("aprovação no ledger sem linha limpa no audit: %s" % ", ".join(sujas))
    if extra:
        v = "NO-GO"
        motivo = "; ".join(([motivo] if falhas else []) + extra)
    return {"veredito": v, "motivo": motivo, "falhas": falhas, "waivers": waivers, "simulado": simulado,
            "gate_report_hash": h_rep, "sintese": None, "aprovacoes_sem_audit_limpo": sujas}


def veredito(ws):
    return veredito_detalhado(ws)["veredito"]


# ------------------------------------------------------------------ selftest (L03: cada check reprova seu negativo)

def selftest(verbose=False):
    ok, linhas = True, []

    def chk(nome, cond):
        nonlocal ok
        ok = ok and bool(cond)
        linhas.append("%s %s" % ("ok  " if cond else "FALHOU", nome))

    tmp = tempfile.mkdtemp(prefix="co-portao-selftest-")
    env = dict(os.environ, GIT_AUTHOR_NAME="st", GIT_AUTHOR_EMAIL="st@st", GIT_COMMITTER_NAME="st",
               GIT_COMMITTER_EMAIL="st@st", GIT_CONFIG_NOSYSTEM="1")
    try:
        repo = os.path.join(tmp, "repo")

        def w(rel, txt):
            p = os.path.join(repo, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as fh:
                fh.write(txt)

        def g(*a):
            subprocess.run(["git", "-C", repo] + list(a), env=env, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=True)
        w("src/core.py", "def soma(a, b):\n    return a + b\n")
        w("tests/test_core.py", "import unittest\nimport sys\nsys.path.insert(0, 'src')\nfrom core import soma\n\n\n"
          "class T(unittest.TestCase):\n    def test_soma(self):\n        self.assertEqual(soma(1, 2), 3)\n")
        w("README.md", "# r\n")
        g("init", "-q")
        g("add", "-A")
        g("commit", "-q", "-m", "base")
        base = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], stdout=subprocess.PIPE,
                              universal_newlines=True, env=env).stdout.strip()

        def caso(muda, desfaz, literais=()):
            muda()
            d = coletar_diff(repo, base)
            r = (g3_territorio(d, ["src/**"])["status"], g4_gaming(d, literais)["status"])
            desfaz()
            return r

        def reset():
            g("reset", "-q", "--hard", base)
            g("clean", "-qfdx")
        chk("G3/G4 controle: diff vazio passa", caso(lambda: None, reset) == ("PASS", "PASS"))
        chk("G3 controle: edição dentro passa", caso(lambda: w("src/novo.py", "X = 1\n"), reset)[0] == "PASS")
        chk("G3 negativo: untracked fora reprova", caso(lambda: w("fora.txt", "x\n"), reset)[0] == "FAIL")
        chk("G3 negativo: staged fora reprova", caso(lambda: (w("README.md", "y\n"), g("add", "-A")), reset)[0] == "FAIL")
        chk("G3 negativo: rename fora→dentro reprova", caso(lambda: g("mv", "README.md", "src/README.md"), reset)[0] == "FAIL")
        chk("G3 negativo: modo alterado fora reprova",
            caso(lambda: os.chmod(os.path.join(repo, "README.md"), 0o755), reset)[0] == "FAIL")
        for nome, src in (("pytest.skip", "import pytest\npytest.skip('x')\n"), ("sys.exit(0)", "import sys\nsys.exit(0)\n"),
                          ("os._exit", "import os\nos._exit(0)\n"), ("assert True", "assert True\n"),
                          ("__eq__", "class A:\n    def __eq__(self, o):\n        return True\n"),
                          ("except pass", "try:\n    x = 1\nexcept Exception:\n    pass\n"),
                          ("R3-8 from pytest import skip", "from pytest import skip\n\n\ndef f():\n    skip()\n"),
                          ("R3-8 getattr(sys,'exit')", "import sys\n\n\ndef f():\n    getattr(sys, 'exit')(0)\n"),
                          ("R3-8 getattr(os,'_exit')", "import os\ngetattr(os, '_exit')(0)\n"),
                          ("R3-8 assertTrue(True)", "def f(self):\n    self.assertTrue(True)\n"),
                          ("R3-8 assert 1", "assert 1\n"),
                          ("R3-8 unittest.skip por alias", "from unittest import skip as pula\n\n\n@pula('x')\n"
                                                           "def f():\n    return 1\n"),
                          ("R3-8 from sys import exit; exit(0)", "from sys import exit\nexit(0)\n")):
            chk("G4 negativo: %s reprova" % nome, caso(lambda s=src: w("src/core.py", s), reset)[1] == "FAIL")
        chk("G4 negativo: teste editado reprova",
            caso(lambda: w("tests/test_core.py", "import unittest\n"), reset)[1] == "FAIL")
        chk("G4 negativo: literal do held-out reprova",
            caso(lambda: w("src/core.py", "K = 'segredo-heldout-42'\n"), reset, {"segredo-heldout-42"})[1] == "FAIL")
        chk("G4 controle: sys.exit(main()) passa",
            caso(lambda: w("src/cli.py", "import sys\n\n\ndef main():\n    return 0\n\n\nif __name__ == '__main__':\n"
                                         "    sys.exit(main())\n"), reset)[1] == "PASS")
        try:
            coletar_diff(repo, "0" * 40)
            chk("diff: base inválida ⇒ Erro", False)
        except Erro:
            chk("diff: base inválida ⇒ Erro", True)
        # G1
        py = sys.executable
        chk("G1 controle: suíte verde passa", _uma_suite("u", "%s -m unittest discover -s tests" % py, repo)[0] == "PASS")
        chk("G1 negativo: 0 coletados reprova", _uma_suite("u", "%s -c pass" % py, repo)[0] != "PASS")
        chk("G1 negativo: ferramenta ausente reprova", _uma_suite("u", "runner-inexistente-zz9 --x", repo)[0] != "PASS")
        for falsa in ("echo ok fake", "echo 'Ran 7 tests'", "printf '3 passed\\n'", "true && echo 'Ran 1 test'",
                      "%s -m unittest discover -s tests | cat" % py, "%s -c \"print('Ran 5 tests')\"" % py):
            chk("G1 R3-6 negativo: suíte que só imprime reprova (%s)" % falsa, _uma_suite("u", falsa, repo)[0] != "PASS")
        chk("G1 R3-6 negativo: unittest sem teste executado reprova",
            _uma_suite("u", "%s -m unittest discover -s src" % py, repo)[0] != "PASS")
        chk("G1 R3-6 controle: cd + unittest com relatório estruturado passa",
            _uma_suite("u", "cd %s && %s -m unittest discover -s tests -v" % (repo, py), tmp)[0] == "PASS")
        w("src/core.py", "def soma(a, b):\n    return a - b\n")
        chk("G1 negativo: teste falhando reprova",
            _uma_suite("u", "%s -m unittest discover -s tests" % py, repo)[0] == "FAIL")
        reset()
        # G0 (contagens; o hash é do ac.py oracle verify)
        o = os.path.join(tmp, "o.py")
        with open(o, "w") as fh:
            fh.write("import unittest\n\n\nclass O(unittest.TestCase):\n    def test_a(self):\n"
                     "        self.assertEqual(1, 1)\n        self.assertTrue(1)\n")
        chk("G0 contagem: 1 teste, 2 asserções", contar_oraculo([o]) == (1, 2))
        # veredito (V4-2: aplicabilidade do contrato por tipo; regressao.json5 só acrescenta exigência)
        cont = aplicabilidade_contrato("cli")
        reg = {"tipo": "cli", "itens": [{"id": gi, "aplica": c["aplica"], "waiver": c["waiver"]}
                                        for gi, c in cont.items()]}
        ws = os.path.join(tmp, "ws")
        ap = os.path.join(ws, "aprovacoes", "G2-2.json")
        grava_json(ap, {"portao": "G2", "decisao": "aprovado", "seq": 2})
        ap_ent = os.path.join(ws, "aprovacoes", "entrega-3.json")
        grava_json(ap_ent, {"portao": "entrega", "decisao": "aprovado", "seq": 3})
        recs_ap = [{"seq": 1, "evento": "genese", "payload": {}},
                   {"seq": 2, "evento": "aprovacao", "payload": {"portao": "G2", "decisao": "aprovado", "arquivo": ap}},
                   {"seq": 3, "evento": "aprovacao", "payload": {"portao": "entrega", "decisao": "aprovado",
                                                                  "arquivo": ap_ent}}]

        def it(gid, st, **k):
            d = {"id": gid, "status": st, "aprovacao": None}
            d.update(k)
            return d
        base_ok = [it(gi, "PASS" if c["aplica"] else "NA") for gi, c in cont.items()]

        def troca(gid, st, **k):
            return [it(gid, st, **k) if x["id"] == gid else x for x in base_ok]

        def sem(*gids):
            return [x for x in base_ok if x["id"] not in gids]

        def v(itens, rg=None, simul=False, **k):
            return calcular_veredito(itens, rg or reg, simul, ws=ws, tipo="cli", **k)[0]
        chk("veredito: tudo PASS ⇒ GO", v(base_ok) == "GO")
        chk("veredito: FAIL ⇒ NO-GO", v(troca("G0", "FAIL")) == "NO-GO")
        chk("veredito: item ausente ⇒ NO-GO", v(sem("G14")) == "NO-GO")
        chk("veredito A2: núcleo fora da regressão e ausente do relatório ⇒ NO-GO",
            v(sem("G1"), {"itens": [i for i in reg["itens"] if i["id"] != "G1"]}) == "NO-GO")
        reg_na = {"itens": [dict(i, aplica=False, waiver=True) if i["id"] in ("G1", "G5", "G7", "G13") else i
                            for i in reg["itens"]]}
        chk("veredito A2: núcleo NA mesmo com aplica=false ⇒ NO-GO", v(troca("G1", "NA"), reg_na) == "NO-GO")
        for gi in ("G5", "G7", "G13"):
            chk("veredito V4-2: %s NA por edição de regressao.json5 (contrato: aplica) ⇒ NO-GO" % gi,
                v(troca(gi, "NA"), reg_na) == "NO-GO")
        chk("veredito V4-2: tipo desconhecido ⇒ sem_waiver forçado aplicável ⇒ NO-GO",
            calcular_veredito(troca("G13", "NA"), reg_na, False, ws=ws, tipo="??")[0] == "NO-GO")
        reg_mais = {"itens": [dict(i, aplica=True) if i["id"] == "G8" else i for i in reg["itens"]]}
        chk("veredito V4-2: regressao.json5 pode ACRESCENTAR exigência (G8 aplica ⇒ NA reprova)",
            v(base_ok, reg_mais) == "NO-GO")
        reg_g2 = {"itens": [dict(i, waiver=False) if i["id"] == "G2" else i for i in reg["itens"]]}
        wv = troca("G2", "WAIVED", aprovacao=ap)
        chk("veredito V4-2: regressao.json5 pode tirar waiver (G2 waiver:false ⇒ WAIVED reprova)",
            v(wv, reg_g2, recs=recs_ap, _sujas=[]) == "NO-GO")
        chk("A4: writes amplos detectados", writes_amplos(["**", "*", "**/*", "./**", "src/**", "*.md"]) ==
            ["**", "*", "**/*", "./**"])
        chk("veredito: NA em item aplicável ⇒ NO-GO", v(troca("G0", "NA")) == "NO-GO")
        chk("veredito: waiver do próprio item (seq + evento + audit) ⇒ GO (com waiver)",
            v(wv, recs=recs_ap, _sujas=[]) == "GO (com waiver)")
        chk("veredito negativo: waiver com aprovação de OUTRO portão (entrega) ⇒ NO-GO",
            v(troca("G2", "WAIVED", aprovacao=ap_ent), recs=recs_ap, _sujas=[]) == "NO-GO")
        chk("problema_waiver: aprovação de G2 não dispensa G6", problema_waiver(ws, ap, recs_ap, [], item="G6"))
        chk("problema_waiver: sem item informado ⇒ recusa", problema_waiver(ws, ap, recs_ap, []))
        chk("waiver_aprovado: acha a do próprio item e não a de outro portão",
            waiver_aprovado(ws, "G2", recs_ap, []) == ap and waiver_aprovado(ws, "G6", recs_ap, []) is None)
        chk("veredito negativo: waiver sem linha no audit ⇒ NO-GO", v(wv, recs=recs_ap, _sujas=[ap]) == "NO-GO")
        chk("veredito negativo: waiver cujo seq não está no ledger ⇒ NO-GO",
            v(wv, recs=recs_ap[:1], _sujas=[]) == "NO-GO")
        chk("veredito: waiver sem arquivo ⇒ NO-GO", v(troca("G2", "WAIVED", aprovacao=ap + ".x")) == "NO-GO")
        ap_g13 = os.path.join(ws, "aprovacoes", "G13-4.json")
        grava_json(ap_g13, {"portao": "G13", "decisao": "aprovado", "seq": 4})
        recs_13 = recs_ap + [{"seq": 4, "evento": "aprovacao", "payload": {"portao": "G13", "decisao": "aprovado",
                                                                           "arquivo": ap_g13}}]
        chk("veredito: waiver em G0 ⇒ NO-GO", v(troca("G0", "WAIVED", aprovacao=ap)) == "NO-GO")
        chk("veredito V4-2: waiver em G13 (sem_waiver do contrato) mesmo com aprovação do item ⇒ NO-GO",
            v(troca("G13", "WAIVED", aprovacao=ap_g13), reg_na, recs=recs_13, _sujas=[]) == "NO-GO")
        chk("veredito: simulado vence waiver", v(wv, simul=True, recs=recs_ap, _sujas=[]) == "GO (simulado)")
        chk("veredito: NO-GO vence simulado", v(troca("G0", "ERRO"), simul=True) == "NO-GO")
        # V4-7: relatório cujo sistema_hash ≠ hash atual do alvo é obsoleto
        alvo_st = os.path.join(tmp, "alvo-v47")
        os.makedirs(alvo_st)
        with open(os.path.join(alvo_st, "m.py"), "w") as fh:
            fh.write("print(1)\n")
        grava_json(os.path.join(ws, "obra.json5"), {"alvo": alvo_st, "tipo": "cli"})
        rep_st = {"sistema_hash": sistema_hash(alvo_st)}
        chk("V4-7 controle: alvo intacto ⇒ relatório atual", problema_relatorio_obsoleto(ws, rep_st) is None)
        with open(os.path.join(alvo_st, "m.py"), "w") as fh:
            fh.write("raise SystemExit(1)\n")
        chk("V4-7 negativo: alvo mudou depois do portão ⇒ relatório obsoleto",
            problema_relatorio_obsoleto(ws, rep_st) is not None)
        os.remove(os.path.join(ws, "obra.json5"))
        # waiver só com aprovação JSON válida em <ws>/aprovacoes/ (nunca o .sh, nunca decisão ≠ aprovado)
        sh = os.path.join(ws, "aprovacoes", "aprovar-G2.sh")
        with open(sh, "w") as fh:
            fh.write("#!/bin/sh\n")
        rej = os.path.join(ws, "aprovacoes", "G2-10.json")
        grava_json(rej, {"portao": "G2", "decisao": "rejeitado"})
        ruim = os.path.join(ws, "aprovacoes", "G2-11.json")
        with open(ruim, "w") as fh:
            fh.write("{nao e json")
        fora = os.path.join(tmp, "G2-12.json")
        grava_json(fora, {"portao": "G2", "decisao": "aprovado"})
        orfa = os.path.join(ws, "aprovacoes", "G2-13.json")
        grava_json(orfa, {"portao": "G2", "decisao": "aprovado", "seq": 13})
        sem_seq = os.path.join(ws, "aprovacoes", "G2-14.json")
        grava_json(sem_seq, {"portao": "G2", "decisao": "aprovado"})
        for nome, arq in (("aprovar-<portao>.sh", sh), ("decisão rejeitado", rej), ("JSON ilegível", ruim),
                          ("fora de aprovacoes/", fora), ("seq sem evento no ledger", orfa), ("sem seq", sem_seq)):
            chk("veredito negativo: waiver com %s ⇒ NO-GO" % nome,
                v(troca("G2", "WAIVED", aprovacao=arq), recs=recs_ap, _sujas=[]) == "NO-GO")
        # G0 / G-6: MANIFEST conferido contra oraculo_congelado.manifest_hash
        man = os.path.join(ws, "oraculo", "MANIFEST.json5")
        doc = {"schema_version": 1, "frentes": {"T-01": {"autores": ["o1"]}}, "construtores": {}, "congelado": None}
        grava_json(man, doc)
        cong = {"manifest_hash": sha_obj(doc)}
        chk("G0 controle: MANIFEST intacto confere", problema_manifest(ws, [], cong) is None)
        doc["frentes"]["T-01"]["autores"] = ["builder-A"]
        grava_json(man, doc)
        chk("G0 negativo: MANIFEST alterado ⇒ FAIL", problema_manifest(ws, [], cong) is not None)
        os.remove(man)
        chk("G0 negativo: MANIFEST ausente com oraculo_congelado ⇒ FAIL", problema_manifest(ws, [], cong) is not None)
        # G1 (wrapper): o processo testado não fecha o relatório — saída prematura ⇒ FAIL
        w("tests/test_saida.py", "import os\nimport unittest\n\n\nclass S(unittest.TestCase):\n"
          "    def test_s(self):\n        os._exit(0)\n")
        chk("G1 negativo: os._exit(0) dentro do teste (sem fim no canal) reprova",
            _uma_suite("u", "%s -m unittest discover -s tests" % py, repo)[0] == "FAIL")
        w("tests/test_saida.py", "import __main__\nimport sys\nimport unittest\n\n\nclass S(unittest.TestCase):\n"
          "    def test_s(self):\n        self.assertFalse(hasattr(__main__, '_nonce'))\n"
          "        self.assertFalse(any('co-g1-rel-' in a for a in sys.argv))\n")
        chk("G1 controle: o processo testado não conhece nonce nem caminho do relatório",
            _uma_suite("u", "%s -m unittest discover -s tests" % py, repo)[0] == "PASS")
        reset()
    except Exception as e:  # selftest que não roda reprova
        chk("selftest executou sem exceção (%s: %s)" % (type(e).__name__, e), False)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if verbose:
        print("\n".join(linhas))
    return ok


# ------------------------------------------------------------------ CLI (chamado por co.py)

def _ga(args, *nomes, default=None):
    for n in nomes:
        v = getattr(args, n, None)
        if v is not None:
            return v
    return default


def _ws(args):
    ws = _ga(args, "work", "ws")
    if not ws:
        raise Erro("--work obrigatório")
    return os.path.realpath(ws)


def _parse_only(only):
    if not only:
        return None
    if isinstance(only, (list, tuple)):
        only = ",".join(only)
    ids = [x.strip().upper() for x in only.split(",") if x.strip()]
    bad = [x for x in ids if x not in GIDS]
    if bad or not ids:
        raise Erro("--only inválido: %s (use G0..G14)" % ",".join(bad or [only]))
    return ids


def cmd_portao(args):
    acao = _ga(args, "acao", "action", "acao_portao", "subacao")
    if acao == "selftest":
        ok = selftest(verbose=True)
        print("portao selftest: %s" % ("ok" if ok else "REPROVOU"))
        return 0 if ok else 1
    if acao != "run":
        raise Erro("ação de portao inválida: %r (run|selftest)" % acao)
    ws = _ws(args)
    final = bool(_ga(args, "final", default=False))
    rep = rodar(ws, _parse_only(_ga(args, "only")), final)
    h = sha_file(os.path.join(ws, "gate-report.json"))
    append_ledger(ws, "portao_relatorio", {"gate_report_hash": h, "veredito": rep["veredito"], "final": rep["final"]})
    for i in rep["itens"]:
        ev = i["evidencia"].replace("Traceback (most recent call last)", "[pilha da suíte]")
        print("%s %s: %s" % (i["id"], i["status"], ev[-300:]))
    if rep.get("parcial"):
        print("veredito: %s — %s (gate-report %s)" % (rep["veredito"], rep["motivo"], h[:12]))
        return 1 if rep["veredito_parcial"] == "NO-GO" else 0
    print("veredito: %s (gate-report %s)" % (rep["veredito"], h[:12]))
    return 1 if rep["veredito"] == "NO-GO" else 0


def cmd_veredito(args):
    v = veredito_detalhado(_ws(args))
    if _ga(args, "json", default=False):
        print(json.dumps(v, ensure_ascii=False, indent=1))
    else:
        print("%s — %s" % (v["veredito"], v["motivo"]))
    return 1 if v["veredito"] == "NO-GO" else 0


def cmd_diff(args):
    ws = _ws(args)
    task = _ga(args, "task")
    base = _ga(args, "base")
    if not task or not base:
        raise Erro("uso: diff <task> --base SHA [--repo PATH]")
    repo = _ga(args, "repo")
    if not repo:
        repo = ler_obra(ws).get("alvo")
    if not repo or not os.path.isdir(repo):
        raise Erro("--repo inválido: %s" % repo)
    plano_p = os.path.join(ws, "PLANO.json5")
    if not os.path.isfile(plano_p):
        raise Erro("PLANO.json5 ausente em %s" % ws)
    tasks = {t.get("id"): t for t in json5_load(plano_p).get("tasks") or []}
    if task not in tasks:
        raise Erro("task desconhecida: %s" % task)
    writes = tasks[task].get("writes") or []
    # G-7b: ledger ilegível/adulterado ⇒ Erro (exit 2, falha fechada); nunca "sem ledger = nada registrado"
    recs = ler_ledger_conferido(ws)
    r3, r4 = avaliar_diff(os.path.realpath(repo), base, writes, ws)
    r3 = _reprova_g3(r3, problemas_territorio_registrado(ws, recs, writes))
    for r in (r3, r4):
        print("%s %s: %s" % (r["id"], r["status"], r["evidencia"]))
    return 0 if r3["status"] == r4["status"] == "PASS" else 1


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write("%s: erro: %s\n" % (self.prog, message))
        raise SystemExit(2)


def build_parser():
    p = _Parser(prog="co_portao.py", description="portão de regressão (G0..G14), veredito e diff de território")
    p.add_argument("--work", help="workspace da obra (fora do alvo)")
    sub = p.add_subparsers(dest="cmd")
    s = sub.add_parser("portao", help="run|selftest")
    s.add_argument("acao", choices=["run", "selftest"])
    s.add_argument("--only", help="G<n>[,G<n>]")
    s.add_argument("--final", action="store_true")
    s.add_argument("--work", dest="work_sub", default=None)
    s = sub.add_parser("veredito", help="GO | GO (com waiver) | GO (simulado) | NO-GO")
    s.add_argument("--json", action="store_true")
    s.add_argument("--work", dest="work_sub", default=None)
    s = sub.add_parser("diff", help="G3 território + G4 gaming de uma task desde a base")
    s.add_argument("task")
    s.add_argument("--base", required=True)
    s.add_argument("--repo")
    s.add_argument("--work", dest="work_sub", default=None)
    return p


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and os.path.basename(argv[0]) in ("co.py", "co_portao.py"):
        argv = argv[1:]
    try:
        a = build_parser().parse_args(argv)
    except SystemExit as e:
        return 0 if e.code in (0, None) else 2
    a.work = a.work or getattr(a, "work_sub", None)
    try:
        if a.cmd == "portao":
            if a.acao == "run" and not a.work:
                raise Erro("--work obrigatório")
            return cmd_portao(a)
        if a.cmd == "veredito":
            return cmd_veredito(a)
        if a.cmd == "diff":
            return cmd_diff(a)
        build_parser().print_usage(sys.stderr)
        return 2
    except Erro as e:
        sys.stderr.write("erro: %s\n" % e)
        return 2
    except Exception as e:  # falha fechada, sem traceback
        sys.stderr.write("erro interno (%s): %s\n" % (type(e).__name__, e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
