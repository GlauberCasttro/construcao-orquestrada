"""Base das reproduções V5 (verificador cego). Mesmo isolamento de campanhas/revisao-v4/_base.py: cópia da skill sob
verificação num HOME temporário (.claude/skills/construcao-orquestrada = cópia; auto-correcao = link). Nada aqui toca
a skill real nem a cópia de trabalho. Skill: V5_SKILL_DIR (padrão: campanhas/work/onda1-prova-cego). Python: V5_PY."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.realpath(os.environ.get("V5_SKILL_DIR") or os.path.join(AQUI, "..", "..", "..", "work",
                                                                      "onda1-prova-cego"))
_ACS = [os.environ.get("CO_AC_DIR", ""), os.path.expanduser("~/.claude/skills/auto-correcao"),
        os.path.join(os.path.dirname(SRC), "auto-correcao")]
AC_DIR = os.path.realpath(next((d for d in _ACS if d and os.path.isfile(os.path.join(d, "scripts", "ac.py"))),
                               _ACS[1]))
PY = os.environ.get("V5_PY", sys.executable)

PREFIXO = r'''
import co_estado as E, json, os
ws = %(ws)r
regs = E.ler_ledger(ws)
def t(ev, de, para, ator, payload=None):
    return dict(evento=ev, ator=ator, nivel="obra", de=de, para=para, payload=payload or {})
def op(ev, payload):
    return dict(evento=ev, payload=payload)
def ap(portao, para):
    return [op("aprovacao", {"portao": portao, "decisao": "aprovado"}),
            t("aprovado", "AGUARDANDO_HUMANO", para, "humano")]
ate = %(ate)r
esp = [t("iniciar", "INICIO", "PREMISSAS", "script"),
       t("premissas_ok", "PREMISSAS", "AGUARDANDO_HUMANO", "orquestrador",
         {"obra_hash": E.sha_file(E.paths(ws)["obra"]), "pontos_hash": E.sha_file(E.paths(ws)["pontos"]),
          "pontos_ids": []})]
if ate != "AH_STOP":
    esp += ap("stop", "ORACULO")
    esp += [t("oraculo_pronto", "ORACULO", "AGUARDANDO_HUMANO", "orquestrador")]
    esp += ap("oraculo", "BASELINE")
    esp += [op("oraculo_congelado", {"hash": "f" * 64, "n_testes": 1, "n_assercoes": 1, "manifest_hash": "e" * 64}),
            t("dispensado", "BASELINE", "PLANO", "orquestrador", {"motivo": "cli"}),
            t("plano_ok", "PLANO", "LOTE", "orquestrador")]
if ate == "FECHAR_RODADA":
    esp += [t("fronteira_vazia", "LOTE", "INTEGRAR", "script"),
            t("merge_ok", "INTEGRAR", "VERIFICAR", "script"),
            t("verde", "VERIFICAR", "MEDIR", "script"),
            op("medicao_registrada", {"config": "sistema", "k": 3, "final": True, "run_ids": [], "pass_at_k": 0.5,
                                      "pass_hat_k": 0.5, "simulated": False, "rotulo": "final"}),
            t("medido", "MEDIR", "FECHAR_RODADA", "script")]
novos = E._encadear(regs[-1], esp)
E.fold_registros(regs + novos)
with E.trava_ledger(ws):
    E._gravar_registros(ws, novos)
    E.pos_gravacao(ws)
st = E.fold(ws)
print(st["obra"], st["contadores"])
'''


class Base(unittest.TestCase):
    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="v5-"))
        self.home = os.path.join(self.root, "home")
        sk = os.path.join(self.home, ".claude", "skills")
        os.makedirs(sk)
        self.skill = os.path.join(sk, "construcao-orquestrada")
        shutil.copytree(SRC, self.skill, ignore=shutil.ignore_patterns("__pycache__", "tests", ".git", "campanhas",
                                                                       "local", "dist"))
        os.symlink(AC_DIR, os.path.join(sk, "auto-correcao"))
        self.scripts = os.path.join(self.skill, "scripts")
        self.co = os.path.join(self.scripts, "co.py")
        self.hook = os.path.join(self.scripts, "co_hook.py")
        self.env = dict(os.environ, HOME=self.home, PYTHONDONTWRITEBYTECODE="1")
        self.alvo = os.path.join(self.home, "proj", "alvo")
        self.ws = os.path.join(self.home, "obras", "ws1")
        os.makedirs(self.alvo)
        with open(os.path.join(self.alvo, "core.py"), "w") as fh:
            fh.write("x = 1\n")
        os.makedirs(os.path.dirname(self.ws))
        self.audit = os.path.join(self.home, ".claude", "construcao-orquestrada", "audit.jsonl")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def run_co(self, *args):
        p = subprocess.run([PY, self.co, "--work", self.ws] + list(args), env=self.env, cwd=self.root,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=300)
        return p.returncode, p.stdout, p.stderr

    def init(self, *extra, stop="pass_hat_3 >= 1.0"):
        rc, out, err = self.run_co("init", "--alvo", self.alvo, "--tipo", "cli", "--pedido", "x", "--stop", stop,
                                   *extra)
        self.assertEqual(rc, 0, out + err)

    def in_proc(self, code, cwd=None):
        boot = "import sys; sys.path.insert(0, %r)\n" % self.scripts + code
        p = subprocess.run([PY, "-c", boot], env=self.env, cwd=cwd or self.root, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True, timeout=300)
        return p.returncode, p.stdout, p.stderr

    def prefixo(self, ate):
        rc, out, err = self.in_proc(PREFIXO % {"ws": self.ws, "ate": ate})
        self.assertEqual(rc, 0, out + err)
        return out

    def status(self):
        rc, out, err = self.run_co("status", "--json")
        self.assertEqual(rc, 0, out + err)
        return json.loads(out)

    def hook_bash(self, cmd, cwd, agent_type=None):
        p = {"session_id": "s", "cwd": cwd, "hook_event_name": "PreToolUse", "tool_name": "Bash",
             "tool_input": {"command": cmd}}
        if agent_type:
            p["agent_id"], p["agent_type"] = "ag-1", agent_type
        r = subprocess.run([PY, self.hook], input=json.dumps(p), env=self.env, cwd=cwd, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True, timeout=60)
        return r.returncode, r.stderr

    def audit_lines(self):
        if not os.path.isfile(self.audit):
            return []
        with open(self.audit, encoding="utf-8") as fh:
            return [json.loads(x) for x in fh if x.strip()]
