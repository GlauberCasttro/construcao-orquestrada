"""Utilitários compartilhados do oráculo da onda 1 (construcao-orquestrada). Escrito pelo agente-oráculo O1.

Nada aqui implementa o produto: só monta fixtures (workspace, ledger encadeado à mão segundo formatos.json5,
repositório git do alvo, payloads PreToolUse) e roda os scripts como processo (CLI) ou num pty (aprovação humana).

Isolamento: cada teste roda em tempfile; HOME é trocado por um diretório temporário cujo `.claude/skills` é um
link simbólico para as skills (REAL_SKILLS: a skill deste projeto + a auto-correcao; ver abaixo) — assim `~/.claude/skills/...` continua resolvendo e o audit
(`~/.claude/construcao-orquestrada/audit.jsonl`, contrato.arquivos.audit) cai dentro do temporário.
Python 3.9+, só stdlib.
"""
import hashlib
import importlib.util
import json
import os
import pty
import re
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

# Onde está a skill (projeto): CO_SKILL_DIR, senão a raiz relativa a este arquivo (tests/onda1/ -> ../..).
# Onde está a auto-correcao (o produto reusa o json5 do ac.py): CO_AC_DIR (pasta com scripts/ac.py), senão a
# instalada em ~/.claude/skills/auto-correcao, senão o projeto irmão, senão o motor EMBUTIDO em .claude/tools/ac/.
# REAL_SKILLS = uma pasta "skills" com as duas: a real (~/.claude/skills) quando ela já aponta para este projeto;
# senão uma pasta temporária com dois links (apagada no fim do processo). Os testes trocam HOME e ligam
# ~/.claude/skills -> REAL_SKILLS, como antes.
_PROJ = os.path.realpath(os.environ.get("CO_SKILL_DIR")
                         or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def _tem_ac(d):
    return bool(d) and os.path.isfile(os.path.join(d, "scripts", "ac.py"))


def _raiz_skills():
    import atexit
    cands = [os.environ.get("CO_AC_DIR", ""), os.path.expanduser("~/.claude/skills/auto-correcao"),
             os.path.join(os.path.dirname(_PROJ), "auto-correcao"), os.path.join(_PROJ, ".claude", "tools", "ac")]
    ac_dir = os.path.realpath(next((c for c in cands if _tem_ac(c)), cands[1]))
    real = os.path.realpath(os.path.expanduser("~/.claude/skills"))
    if (os.path.realpath(os.path.join(real, "construcao-orquestrada")) == _PROJ
            and os.path.realpath(os.path.join(real, "auto-correcao")) == ac_dir):
        return real
    raiz = os.path.realpath(tempfile.mkdtemp(prefix="co-skills-"))
    atexit.register(shutil.rmtree, raiz, True)
    os.symlink(_PROJ, os.path.join(raiz, "construcao-orquestrada"))
    os.symlink(ac_dir, os.path.join(raiz, "auto-correcao"))
    return raiz


REAL_SKILLS = _raiz_skills()
# a skill é chamada PELO caminho dentro de REAL_SKILLS (não pelo realpath): o produto acha a auto-correcao como
# irmã (scripts/../../auto-correcao), exatamente como quando instalado em ~/.claude/skills.
SKILL = os.path.join(REAL_SKILLS, "construcao-orquestrada")
SCRIPTS = os.path.join(SKILL, "scripts")
REFS = os.path.join(SKILL, "references")
CO = os.path.join(SCRIPTS, "co.py")
CO_ESTADO = os.path.join(SCRIPTS, "co_estado.py")
CO_HOOK = os.path.join(SCRIPTS, "co_hook.py")
CO_PORTAO = os.path.join(SCRIPTS, "co_portao.py")
HOOK_SETTINGS = os.path.join(REFS, "hook-settings.json5")
AC = os.path.join(REAL_SKILLS, "auto-correcao", "scripts", "ac.py")

HEX64 = re.compile(r"^[0-9a-f]{64}$")
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
CAMPOS_LEDGER = ["seq", "ts", "ator", "nivel", "evento", "de", "para", "task", "chave", "payload", "payload_hash",
                 "prev", "hash"]
SECOES_RETOMAR = ["# Obra", "## Estado", "## Portões pendentes", "## Contrato e oráculo", "## Critério de parada",
                  "## Orçamento", "## Tasks em voo", "## Fora do escopo", "## Próximo comando"]
CABECALHO_RETOMAR = re.compile(r"<!-- gerado por co\.py; ledger_seq=(\d+) ledger_hash=([0-9a-f]{64}); NÃO EDITE -->")
CHALLENGE = re.compile(rb"DESAFIO:[ \t]*([^\r\n]+)\r?\n")

_AC_MOD = None


def acmod():
    global _AC_MOD
    if _AC_MOD is None:
        spec = importlib.util.spec_from_file_location("ac_para_oraculo_onda1", AC)
        _AC_MOD = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_AC_MOD)
    return _AC_MOD


def json5_load(path):
    with open(path, encoding="utf-8") as fh:
        return acmod().json5_loads(fh.read())


def contrato():
    return json5_load(os.path.join(REFS, "contrato.json5"))


def maquina():
    return json5_load(os.path.join(REFS, "maquina.json5"))


# ------------------------------------------------------------------ hash (formatos.json5#convencoes, ledger.hash)

def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha_obj(obj):
    return hashlib.sha256(canon(obj)).hexdigest()


def sha_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def rec_hash(rec):
    sem = {k: v for k, v in rec.items() if k != "hash"}
    return hashlib.sha256((rec["prev"] + canon(sem).decode("utf-8")).encode("utf-8")).hexdigest()


def hash_estado_de(st):
    """D8: sha256_de_objeto do subconjunto decisório do fold."""
    keys = ["obra", "contadores", "constantes", "teto_vigente", "tasks", "campanhas", "contrato_hash", "oraculo"]
    return sha_obj({k: st[k] for k in keys})


def now_ts(offset=0.0):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + offset))


def cadeia_problemas(records):
    """Confere a cadeia exatamente como formatos.ledger.hash.verificar_cadeia. Lista de problemas (vazia = ok)."""
    probs = []
    prev = "0"
    for i, r in enumerate(records, 1):
        if sorted(r.keys()) != sorted(CAMPOS_LEDGER):
            probs.append("seq %s: campos %s" % (r.get("seq"), sorted(r.keys())))
            continue
        if r["seq"] != i:
            probs.append("seq %s na posição %d" % (r["seq"], i))
        if r["prev"] != prev:
            probs.append("seq %s: prev não encadeia" % r["seq"])
        if rec_hash(r) != r["hash"]:
            probs.append("seq %s: hash não confere" % r["seq"])
        if sha_obj(r["payload"]) != r["payload_hash"]:
            probs.append("seq %s: payload_hash não confere" % r["seq"])
        if not TS_RE.match(str(r["ts"])):
            probs.append("seq %s: ts fora do formato" % r["seq"])
        prev = r["hash"]
    return probs


class Ledger:
    """Leitura do ledger e extensão À MÃO, encadeada pela regra de formatos.json5 (o ledger é a fonte da verdade:
    um registro válido gravado por fora deve ser dobrado pelo fold como qualquer outro)."""

    def __init__(self, ws):
        self.ws = ws
        self.path = os.path.join(ws, ".construcao", "ledger.jsonl")

    def raw(self):
        with open(self.path, "rb") as fh:
            return fh.read()

    def records(self):
        with open(self.path, encoding="utf-8") as fh:
            return [json.loads(x) for x in fh if x.strip()]

    def last(self):
        return self.records()[-1]

    def eventos(self):
        return [r["evento"] for r in self.records()]

    def append(self, evento, ator="script", nivel="operacional", de=None, para=None, task=None, chave=None,
               payload=None):
        payload = {} if payload is None else payload
        last = self.last()
        r = {"seq": last["seq"] + 1, "ts": now_ts(), "ator": ator, "nivel": nivel, "evento": evento, "de": de,
             "para": para, "task": task, "chave": chave, "payload": payload, "payload_hash": sha_obj(payload),
             "prev": last["hash"]}
        r["hash"] = rec_hash(r)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
        return r

    # transições da obra
    def t(self, evento, de, para, ator, payload=None):
        return self.append(evento, ator=ator, nivel="obra", de=de, para=para, payload=payload)

    def tt(self, task, evento, de, para, ator, chave=None, payload=None):
        return self.append(evento, ator=ator, nivel="task", de=de, para=para, task=task, chave=chave,
                           payload=payload)

    def humano(self, portao, evento, para, decisao=None):
        seq = self.last()["seq"] + 1
        self.append("aprovacao", payload={
            "portao": portao, "decisao": decisao or evento,
            "arquivo": os.path.join(self.ws, "aprovacoes", "%s-%d.json" % (portao, seq)),
            "hash_estado": "1" * 64, "usuario_so": "teste", "ttyname": "/dev/ttys000"})
        return self.t(evento, "AGUARDANDO_HUMANO", para, "humano")

    # ----- caminhos prontos (cada um parte de onde o anterior parou)
    def ate_premissas(self):
        self.t("iniciar", "INICIO", "PREMISSAS", "script")

    def ate_ah_stop(self):
        self.ate_premissas()
        self.t("premissas_ok", "PREMISSAS", "AGUARDANDO_HUMANO", "orquestrador",
               payload={"obra_hash": "a" * 64, "pontos_hash": "b" * 64, "pontos_ids": []})

    def ate_oraculo(self):
        self.ate_ah_stop()
        self.humano("stop", "aprovado", "ORACULO")

    def ate_plano(self, oraculo_hash="f" * 64, n_testes=1, n_assercoes=1):
        self.ate_oraculo()
        self.t("oraculo_pronto", "ORACULO", "AGUARDANDO_HUMANO", "orquestrador")
        self.humano("oraculo", "aprovado", "BASELINE")
        self.append("oraculo_congelado", payload={"hash": oraculo_hash, "n_testes": n_testes,
                                                   "n_assercoes": n_assercoes, "manifest_hash": "e" * 64})
        self.t("dispensado", "BASELINE", "PLANO", "orquestrador", payload={"motivo": "cli com requisito novo"})

    def plano_ok(self):
        self.t("plano_ok", "PLANO", "LOTE", "orquestrador",
               payload={"plano_hash": "c" * 64, "regressao_hash": "d" * 64, "ha_decisoes": False})
        self.append("contrato_hash", payload={"contrato_hash": "a" * 64, "plano_hash": "c" * 64, "max_despachos": 30})

    def ate_lote(self):
        self.ate_plano()
        self.plano_ok()

    def _volta_corrigir_lote(self):
        self.t("fronteira_vazia", "LOTE", "INTEGRAR", "script")
        self.t("violou", "INTEGRAR", "CORRIGIR", "script")
        self.t("campanhas_abertas", "CORRIGIR", "LOTE", "orquestrador")  # incrementa tentativas

    def lote_ate_corrigir_tent3(self):
        for _ in range(3):
            self._volta_corrigir_lote()
        self.t("fronteira_vazia", "LOTE", "INTEGRAR", "script")
        self.t("violou", "INTEGRAR", "CORRIGIR", "script")

    def lote_ate_verificar_tent3(self):
        for _ in range(3):
            self._volta_corrigir_lote()
        self.t("fronteira_vazia", "LOTE", "INTEGRAR", "script")
        self.t("merge_ok", "INTEGRAR", "VERIFICAR", "script")

    def lote_ate_replanejar(self):
        self.lote_ate_corrigir_tent3()
        self.t("campanhas_abertas", "CORRIGIR", "REPLANEJAR", "script")

    def ate_replanejar(self, replanejamentos=0):
        self.ate_lote()
        self.lote_ate_replanejar()
        for _ in range(replanejamentos):
            self.t("novo_plano", "REPLANEJAR", "PLANO", "orquestrador")
            self.plano_ok()
            self.lote_ate_replanejar()


# ------------------------------------------------------------------ base dos testes

class Base(unittest.TestCase):
    exige = (CO,)  # scripts que precisam existir (sem eles o teste ERRA limpo, nunca passa por vácuo)

    def setUp(self):
        for s in self.exige:
            self.assertTrue(os.path.isfile(s), "script ausente: %s" % s)
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="co-onda1-"))
        self.alvo = os.path.join(self.tmp, "alvo")
        self.ws = os.path.join(self.tmp, "obra")
        os.makedirs(os.path.join(self.alvo, "src"))
        with open(os.path.join(self.alvo, "src", "core.py"), "w") as fh:
            fh.write("def soma(a, b):\n    return a + b\n")
        self.home = os.path.join(self.tmp, "home")
        self.env = self.make_env(self.home)
        self.audit = os.path.join(self.home, ".claude", "construcao-orquestrada", "audit.jsonl")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @staticmethod
    def make_env(home):
        os.makedirs(os.path.join(home, ".claude"), exist_ok=True)
        link = os.path.join(home, ".claude", "skills")
        if not os.path.lexists(link):
            os.symlink(REAL_SKILLS, link)
        env = {k: v for k, v in os.environ.items() if not (k.startswith("CO_") or k.startswith("AC_"))}
        env.update(HOME=home, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                   GIT_COMMITTER_EMAIL="t@t", GIT_CONFIG_NOSYSTEM="1", PYTHONDONTWRITEBYTECODE="1")
        return env

    # --- CLI sem terminal (como um agente chamando via Bash)
    def co(self, *argv, work=None, input=None, env=None, script=None):
        cmd = [sys.executable, script or CO]
        if work is not False:
            cmd += ["--work", work or self.ws]
        p = subprocess.run(cmd + list(argv), input=input,
                           stdin=None if input is not None else subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env or self.env, timeout=120,
                           universal_newlines=True, cwd=self.tmp)
        return p.returncode, p.stdout, p.stderr

    def assertLimpo(self, out, err=""):
        """O script rodou de verdade: sem traceback, sem 'pendente:' (handler da onda 1 implementado)."""
        txt = out + err
        self.assertNotIn("Traceback", txt, txt[-2000:])
        self.assertNotIn("can't open file", txt, txt[-500:])
        self.assertNotIn("pendente:", txt, txt[-500:])

    def init(self, tipo="cli", ws=None, alvo=None):
        code, out, err = self.co("init", "--alvo", alvo or self.alvo, "--tipo", tipo, "--pedido", "CLI que soma",
                                 "--stop", "pass_hat_3 >= 1.0", work=ws or self.ws)
        self.assertEqual(code, 0, out + err)
        self.assertLimpo(out, err)
        return Ledger(ws or self.ws)

    def status(self):
        code, out, err = self.co("status", "--json")
        self.assertEqual(code, 0, out + err)
        self.assertLimpo(out, err)
        return json.loads(out)

    def write_json(self, path, obj):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=1)
        return path

    def audit_lines(self):
        if not os.path.isfile(self.audit):
            return []
        with open(self.audit, encoding="utf-8") as fh:
            return [json.loads(x) for x in fh if x.strip()]

    def grava_hook_vivo(self):
        """Linha de audit equivalente ao bloqueio do selftest vivo (formatos.audit, tipo tool_call)."""
        os.makedirs(os.path.dirname(self.audit), exist_ok=True)
        rec = {"ts": now_ts(), "tipo": "tool_call", "session_id": "s-vivo", "agent_id": "a-vivo",
               "agent_type": "general-purpose", "tool": "Bash",
               "alvo": "python3 %s --work %s aprovar __selftest__" % (CO, self.ws), "tokens": ["co.py", "aprovar"],
               "decisao": "bloqueado", "motivo": "aprovação só pelo terminal do founder", "exit": 2,
               "cwd": self.tmp, "payload_hash": "2" * 64}
        with open(self.audit, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------ hook (PreToolUse)

def payload(tool, tool_input, agent_type=None, agent_id=None, cwd="/tmp", session="s1"):
    p = {"session_id": session, "transcript_path": "/tmp/t.jsonl", "cwd": cwd, "hook_event_name": "PreToolUse",
         "tool_name": tool, "tool_input": tool_input}
    if agent_id is not None:
        p["agent_id"] = agent_id
    if agent_type is not None:
        p["agent_type"] = agent_type
    return p


def bash(cmd, **kw):
    return payload("Bash", {"command": cmd}, **kw)


def sub(p, agent_type="builder-A", agent_id="ag-1"):
    """Mesma chamada, vinda de subagente."""
    q = dict(p)
    q["agent_id"] = agent_id
    if agent_type is not None:
        q["agent_type"] = agent_type
    return q


class HookBase(Base):
    exige = (CO_HOOK,)

    def setUp(self):
        super().setUp()
        # workspace reconhecível: tem .construcao/ (ledger), aprovacoes/, oraculo/{dev,heldout}, MANIFEST
        os.makedirs(os.path.join(self.ws, ".construcao"))
        with open(os.path.join(self.ws, ".construcao", "ledger.jsonl"), "w") as fh:
            fh.write("")
        os.makedirs(os.path.join(self.ws, "aprovacoes"))
        os.makedirs(os.path.join(self.ws, "oraculo", "dev"))
        os.makedirs(os.path.join(self.ws, "oraculo", "heldout", "casos"))
        self.heldout_caso = self.write_json(os.path.join(self.ws, "oraculo", "heldout", "casos", "C-01.json"),
                                            {"id": "h-01", "cenario": "C-01", "classe": "Q",
                                             "entrada": {"a": "zq-heldout-7731-sentinela"}, "esperado": {"exit": 0}})
        with open(os.path.join(self.ws, "oraculo", "dev", "test_dev.py"), "w") as fh:
            fh.write("import unittest\n")
        self.write_json(os.path.join(self.ws, "oraculo", "MANIFEST.json5"),
                        {"schema_version": 1,
                         "frentes": {"T-01": {"autores": ["oraculo-O1"], "dev": ["oraculo/dev/**"],
                                              "heldout": ["oraculo/heldout/**"]}},
                         "construtores": {"T-01": "builder-A"}, "congelado": None})

    def hook(self, p, script=None, argv=()):
        raw = p if isinstance(p, str) else json.dumps(p)
        proc = subprocess.run([sys.executable, script or CO_HOOK] + list(argv), input=raw, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=self.env, timeout=60, universal_newlines=True,
                              cwd=self.tmp)
        self.assertNotIn("Traceback", proc.stderr, proc.stderr[-1500:])
        return proc.returncode, proc.stdout + proc.stderr

    def assertBloqueia(self, p, msg=""):
        code, out = self.hook(p)
        self.assertEqual(code, 2, "deveria BLOQUEAR (exit 2): %s %s -> %s" % (msg, json.dumps(p)[:400], out))
        self.assertTrue(out.strip(), "bloqueio sem motivo no stderr")

    def assertPermite(self, p, msg=""):
        code, out = self.hook(p)
        self.assertEqual(code, 0, "deveria PERMITIR (exit 0): %s %s -> %s" % (msg, json.dumps(p)[:400], out))


# ------------------------------------------------------------------ pty (caminho do humano; modelo _pty_helper.py)

def run_tty(argv, env, answer="echo", timeout=60, script=CO):
    """Roda `python3 <script> <argv>` num pseudo-terminal real e redigita o desafio.
    answer='echo' redigita exatamente o desafio; 'numero_errado' redigita um número de mesmo tamanho ≠ desafio
    (AC-07: desafio numérico); outra str redigita esse texto. Retorna (exit, saída, desafio|None)."""
    pid, fd = pty.fork()
    if pid == 0:
        try:
            os.execve(sys.executable, [sys.executable, script] + list(argv), env)
        finally:
            os._exit(127)
    buf, challenge, deadline = b"", None, time.time() + timeout
    try:
        while True:
            if time.time() > deadline:
                os.kill(pid, signal.SIGKILL)
                raise AssertionError("processo no tty não terminou em %ss; saída: %r" % (timeout, buf[-500:]))
            r, _, _ = select.select([fd], [], [], 0.2)
            if not r:
                continue
            try:
                data = os.read(fd, 4096)
            except OSError:
                break
            if not data:
                break
            buf += data
            if challenge is None:
                m = CHALLENGE.search(buf)
                if m:
                    challenge = m.group(1).decode().strip()
                    if answer == "echo":
                        resp = challenge
                    elif answer == "numero_errado":
                        resp = "".join(str((int(d) + 1) % 10) if d.isdigit() else "1" for d in challenge) or "0000"
                    else:
                        resp = answer
                    os.write(fd, (resp + "\n").encode())
    finally:
        _, status = os.waitpid(pid, 0)
        os.close(fd)
    code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else 128 + os.WTERMSIG(status)
    return code, buf.decode("utf-8", "replace"), challenge


# ------------------------------------------------------------------ git do alvo (portão)

def git(repo, *args, env=None):
    p = subprocess.run(["git", "-C", repo] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True, env=env, timeout=60)
    if p.returncode != 0:
        raise AssertionError("git %s falhou: %s" % (args, p.stderr))
    return p.stdout.strip()


def py_call(env, code, cwd=None):
    """Roda código Python com scripts/ no sys.path (chamada de função do módulo, nomes de contrato.modulos)."""
    pre = "import sys; sys.path.insert(0, %r)\n" % SCRIPTS
    p = subprocess.run([sys.executable, "-c", pre + code], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True, env=env, timeout=120, cwd=cwd)
    return p.returncode, p.stdout, p.stderr
