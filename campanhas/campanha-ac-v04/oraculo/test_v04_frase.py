"""Oráculo de aceite da auto-correcao v0.4 — aprovação humana por FRASE-SENHA do founder.

Escrito por um agente SEPARADO de quem implementa (L15). Falha hoje; passa quando a v0.4 estiver pronta.
Interfaces fixadas: ESPEC.md ao lado. unittest puro, Python 3.9+, sem dependências.

Isolamento: cada teste roda com HOME, AC_FRASE_FILE e AC_AUDIT_LOG apontando para um temporário. O
`~/.claude/auto-correcao/` real nunca é lido nem escrito. Processos sem terminal rodam com `start_new_session=True`
(sem tty controlador). O caminho do humano é um pseudo-terminal real (`pty.fork`): o teste espera o prompt
`FRASE...:` aparecer (eco já desligado) e só então digita — exatamente o que um agente com Python faria; por isso a
única coisa que separa humano de agente aqui é CONHECER a frase.
"""
import functools
import hashlib
import hmac
import importlib.util
import json
import os
import pty
import re
import select
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unicodedata
import unittest

SKILL = os.path.expanduser("~/.claude/skills/auto-correcao")
SCRIPTS = os.environ.get("ORACULO_SCRIPTS") or os.path.join(SKILL, "scripts")  # override só p/ validar o oráculo
AC = os.path.join(SCRIPTS, "ac.py")
FRASE_PY = os.path.join(SCRIPTS, "frase.py")
HOOK = os.path.join(SCRIPTS, "hook_aprovacao.py")

FRASE = "lagoa serena de inverno"          # frase do "founder" de teste
SENHA = "Lagoa#2026xy"                     # modo senha: 12 caracteres, 4 classes, 10 distintos
# mudança oficial (2026-10-05, pedido do founder): aceitar SENHA além de frase. Força =
#   (frase: ≥3 palavras e ≥12 caracteres) OU (senha: ≥12 caracteres e ≥3 classes entre minúscula, maiúscula,
#   dígito, símbolo = não alfanumérico e não espaço) — e, nos DOIS modos, ≥6 caracteres distintos (anti-repetição).
FORTES = (FRASE, SENHA, "Senha.Forte2026", "lagoa9#serena", "PEDRA-antiga-77")
FRACAS = ("curta demais", "abc def ghi", "umapalavraenormesemespacos", "duas palavrasgrandes",
          "abcdefghijkl", "abcdef123456", "ABCDEF123456", "abcdef-ghijk", "aaaaaaaaaaaa", "Aa1!Aa1!Aa1!",
          "aaa aaa aaaaaa", "Ab1!xyz", "Ab1!", "Ab1!Ab1!Ab1!Ab1!", "abab abab abab")
OUTRA = "pedra antiga do farol norte"      # frase que um agente inventaria
PROMPT = re.compile(rb"FRASE[^\r\n:]*:")   # todo pedido de frase contém FRASE...: (maiúsculas), eco já desligado
OLD_CHALLENGE = re.compile(rb"DESAFIO:[^\r\n]*\r?\n")  # canal v0.3 (só para a base não travar)
BYPASS_ENV = ("AC_FRASE", "AC_FRASE_SENHA", "AC_PASSPHRASE", "AC_SENHA", "AC_SECRET", "FRASE", "PASSPHRASE",
              "AC_TEST", "AC_TEST_TTY", "AC_ALLOW_NONTTY", "AC_FORCE_TTY", "AC_HUMAN", "CI")


def ciclo():
    spec = importlib.util.spec_from_file_location("ac_oraculo_v04", AC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.ciclo()


def norm(frase):
    return unicodedata.normalize("NFC", frase.strip()).encode("utf-8")


ITER = 600000  # OWASP 2023 para PBKDF2-HMAC-SHA256; mínimo aceito, sem atalho por env


@functools.lru_cache(maxsize=None)
def _pbkdf2(nb, salt_hex, it):
    return hashlib.pbkdf2_hmac("sha256", nb, bytes.fromhex(salt_hex), it, dklen=32)


def kdf(frase, salt_hex, fj):
    """PBKDF2-HMAC-SHA256 (existe no Python 3.9/LibreSSL, ao contrário de hashlib.scrypt); cache no processo."""
    return _pbkdf2(norm(frase), salt_hex, fj["iter"])


def canonical(work, nome, decisao, seq, estado_hash):
    return json.dumps({"work": work, "nome": nome, "decisao": decisao, "seq": seq, "estado_hash": estado_hash},
                      sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha(b):
    return hashlib.sha256(b).hexdigest()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="ac-oraculo-v04-"))
        self.work = os.path.join(self.tmp, "camp")
        self.target = os.path.join(self.tmp, "alvo")
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(os.path.join(self.target, "src"))
        os.makedirs(self.home)
        self.frase_file = os.path.join(self.tmp, "segredo", "frase.json")
        self.audit = os.path.join(self.tmp, "auditoria", "audit.jsonl")
        self.env = {k: v for k, v in os.environ.items() if not (k.startswith("AC_") or k in BYPASS_ENV)}
        self.env.update(HOME=self.home, AC_FRASE_FILE=self.frase_file, AC_AUDIT_LOG=self.audit)
        self.outputs = []

    def tearDown(self):
        for out in self.outputs:  # nenhum comando, em nenhum caminho, vaza a frase ou um traceback
            self.assertNotIn(FRASE, out, "a frase apareceu na saída do terminal (eco ligado ou impressa)")
            self.assertNotIn("Traceback", out)
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---------------------------------------------------------------- processos
    def cli(self, *argv, input=None, env=None, work=None, leak_ok=False):
        """Como um agente via Bash: sem tty (stdin pipe/devnull, sem terminal controlador)."""
        p = subprocess.run([sys.executable, AC, "--work", work or self.work] + list(argv), input=input,
                           stdin=None if input is not None else subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, env=self.env if env is None else env, timeout=120,
                           universal_newlines=True, start_new_session=True)
        if not leak_ok:  # leak_ok: o próprio teste pôs a frase no argv (argparse a ecoa no erro)
            self.outputs.append(p.stdout)
        return p.returncode, p.stdout

    def tty(self, *argv, answers=(), env=None, work=None, stdin_data=None, timeout=90, argv0=None, leak_ok=False):
        """Roda ac.py num pty. A cada prompt FRASE...: digita a próxima resposta (esgotou → linha vazia).
        stdin_data: stdin vira um pipe com esse texto (o pty segue como /dev/tty). Retorna (exit, saída, nprompts)."""
        env = self.env if env is None else env
        rfd = None
        if stdin_data is not None:
            rfd, wfd = os.pipe()
            os.write(wfd, stdin_data.encode())
            os.close(wfd)
        cmd = argv0 or [sys.executable, AC, "--work", work or self.work]
        pid, fd = pty.fork()
        if pid == 0:
            try:
                if rfd is not None:
                    os.dup2(rfd, 0)
                os.execve(cmd[0], cmd + list(argv), env)
            finally:
                os._exit(127)
        if rfd is not None:
            os.close(rfd)
        answers, buf, seen, old, deadline = list(answers), b"", 0, 0, time.time() + timeout
        try:
            while True:
                if time.time() > deadline:
                    os.kill(pid, signal.SIGKILL)
                    self.fail("ac.py no tty não terminou em %ss; saída: %r" % (timeout, buf[-500:]))
                r, _, _ = select.select([fd], [], [], 0.1)
                if not r:
                    continue
                try:
                    data = os.read(fd, 4096)
                except OSError:
                    break
                if not data:
                    break
                buf += data
                n = len(PROMPT.findall(buf))
                while seen < n:
                    os.write(fd, ((answers[seen] if seen < len(answers) else "") + "\n").encode())
                    seen += 1
                k = len(OLD_CHALLENGE.findall(buf))
                while old < k:  # canal antigo: responde vazio (recusa rápida na base)
                    os.write(fd, b"\n")
                    old += 1
        finally:
            _, status = os.waitpid(pid, 0)
            os.close(fd)
        code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else 128 + os.WTERMSIG(status)
        out = buf.decode("utf-8", "replace")
        if not leak_ok:
            self.outputs.append(out)
        return code, out, seen

    # ---------------------------------------------------------------- fixtures
    def definir(self, frase=FRASE):
        code, out, n = self.tty("frase", "definir", answers=[frase, frase])
        self.assertEqual(code, 0, out)
        self.assertEqual(n, 2, "definir deve pedir a frase 2x (FRASE...: duas vezes)")

    def init(self, scope="src/**"):
        code, out = self.cli("init", "--target", self.target, "--scope", scope, "--problem", "p",
                             "--stop", "qualidade>=6/6", "--max-rounds", "3")
        self.assertEqual(code, 0, out)

    def gate(self, name, decision="approve", frase=FRASE):
        return self.tty("gate", name, "--by", "founder", "--decision", decision, answers=[frase])

    def conferir(self, frase=FRASE):
        return self.tty("frase", "conferir", answers=[frase])

    def pronto(self):
        """frase definida + campanha + portão stop aprovado pelo canal da frase."""
        self.definir()
        self.init()
        code, out, _ = self.gate("stop")
        self.assertEqual(code, 0, out)

    def p_state(self):
        return os.path.join(self.work, ".auto-correcao", "state.json")

    def p_ledger(self):
        return os.path.join(self.work, ".auto-correcao", "ledger.jsonl")

    def state(self):
        with open(self.p_state()) as fh:
            return json.load(fh)

    def save_state(self, st):
        with open(self.p_state(), "w") as fh:
            json.dump(st, fh, indent=1, sort_keys=True)

    def raw(self, p):
        if not os.path.isfile(p):
            return b""
        with open(p, "rb") as fh:
            return fh.read()

    def jl(self, p):
        return [json.loads(l) for l in self.raw(p).decode().splitlines() if l.strip()]

    def ledger(self):
        return self.jl(self.p_ledger())

    def audit_lines(self):
        return self.jl(self.audit)

    def snapshot(self):
        return (self.raw(self.p_state()), self.raw(self.p_ledger()), self.raw(self.audit))

    def fj(self, path=None):
        with open(path or self.frase_file) as fh:
            return json.load(fh)

    def tag(self, frase, nome, decisao, seq, estado_hash, fj=None):
        fj = fj or self.fj()
        k = kdf(frase, fj["salt_chave"], fj)
        return hmac.new(k, canonical(self.work, nome, decisao, seq, estado_hash), hashlib.sha256).hexdigest()

    def mark_done(self, *stages):
        st = self.state()
        cy = ciclo()
        for name in stages:
            for sub in cy["stages"][name]["substages"]:
                st["done"][sub["id"]] = "2020-01-01T00:00:00Z"
        self.save_state(st)

    def forge(self, nome, decisao="approve", tag=None, ledger=True, audit=True, state=True, event="gate"):
        """Grava à mão uma 'aprovação' como um agente sem a frase faria (estado, ledger e audit coerentes)."""
        eh = sha(self.raw(self.p_state()))
        seq = len(self.ledger()) + 1
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        rec = {"ts": ts, "event": event, "name": nome, "decision": decisao, "by": "founder", "simulated": False,
               "seq": seq, "estado_hash": eh}
        if tag:
            rec["tag"] = tag(seq, eh) if callable(tag) else tag
        if ledger:
            with open(self.p_ledger(), "a") as fh:
                fh.write(json.dumps(rec, sort_keys=True) + "\n")
        if audit:
            a = dict(rec, cmd=event, work=self.work, user="ana", tty="/dev/ttys003")
            a.pop("event")
            os.makedirs(os.path.dirname(self.audit), exist_ok=True)
            with open(self.audit, "a") as fh:
                fh.write(json.dumps(a, sort_keys=True) + "\n")
        if state and event == "gate":
            st = self.state()
            st.setdefault("gates", {})[nome] = {"by": "founder", "decision": decisao, "note": "", "at": ts,
                                                "simulated": False, "seq": seq, "tag": rec.get("tag")}
            self.save_state(st)
        return rec


# ====================================================================== 1. frase definir

class R1FraseDefinirTest(Base):
    def test_definir_stores_only_salt_and_pbkdf2_verifier_mode_0600(self):
        self.definir()
        mode = stat.S_IMODE(os.stat(self.frase_file).st_mode)
        self.assertEqual(mode, 0o600, "frase.json precisa de modo 0600 (tem %o)" % mode)
        text = self.raw(self.frase_file).decode()
        for leak in (FRASE, FRASE.replace(" ", ""), FRASE.encode().hex()):
            self.assertNotIn(leak, text, "frase.json contém a frase")
        fj = self.fj()
        self.assertEqual((fj.get("versao"), fj.get("kdf")), (1, "pbkdf2-sha256"))
        self.assertIsInstance(fj.get("iter"), int)
        self.assertGreaterEqual(fj["iter"], ITER, "PBKDF2 com menos de 600000 iterações")
        for k in ("salt_verificador", "salt_chave"):
            self.assertRegex(fj[k], r"^[0-9a-f]{32,}$", "%s: ≥16 bytes em hex" % k)
        self.assertNotEqual(fj["salt_verificador"], fj["salt_chave"], "chave HMAC e verificador com o mesmo salt")
        self.assertEqual(fj["verificador"], kdf(FRASE, fj["salt_verificador"], fj).hex())
        self.assertNotEqual(fj["verificador"], kdf(FRASE, fj["salt_chave"], fj).hex())

    def test_unknown_kdf_or_weak_iter_refused(self):
        """frase.json adulterado para kdf desconhecido ou iter < 600000 (verificador coerente): recusa, nada gravado."""
        self.definir()
        self.init()
        orig = self.fj()
        variantes = [dict(orig, kdf="scrypt"), dict(orig, kdf="pbkdf2-sha1"), dict(orig, iter=1000),
                     dict(orig, iter=ITER - 1), dict(orig, iter="600000")]
        for v in variantes:
            if isinstance(v["iter"], int) and v["iter"] > 0:
                v["verificador"] = _pbkdf2(norm(FRASE), v["salt_verificador"], v["iter"]).hex()
            with self.subTest(kdf=v["kdf"], iter=v["iter"]):
                with open(self.frase_file, "w") as fh:
                    json.dump(v, fh)
                os.chmod(self.frase_file, 0o600)
                snap = self.snapshot()
                code, out, n = self.gate("stop")
                self.assertNotEqual(code, 0, "aceitou frase.json com kdf/iter inválido: %r" % out)
                self.assertEqual(self.snapshot(), snap)
                self.assertNotEqual(self.conferir()[0], 0)
                self.assertEqual(self.snapshot(), snap)
        with open(self.frase_file, "w") as fh:  # controle: o original volta a aprovar
            json.dump(orig, fh)
        self.assertEqual(self.gate("stop")[0], 0)

    def test_default_path_is_home_dot_claude(self):
        env = dict(self.env)
        env.pop("AC_FRASE_FILE")
        code, out, n = self.tty("frase", "definir", answers=[FRASE, FRASE], env=env)
        self.assertEqual(code, 0, out)
        p = os.path.join(self.home, ".claude", "auto-correcao", "frase.json")
        self.assertTrue(os.path.isfile(p), "padrão deveria ser $HOME/.claude/auto-correcao/frase.json")
        self.assertEqual(stat.S_IMODE(os.stat(p).st_mode), 0o600)

    def test_confirmation_mismatch_refused(self):
        code, out, n = self.tty("frase", "definir", answers=[FRASE, FRASE + " x"])
        self.assertNotEqual(code, 0, out)
        self.assertFalse(os.path.exists(self.frase_file), "gravou com confirmação divergente")
        self.definir()  # controle: confirmação igual grava

    def test_password_mode_accepted_and_approves(self):
        """Modo senha: definir aceita SENHA e gate aprova com ela (e só com ela)."""
        code, out, n = self.tty("frase", "definir", answers=[SENHA, SENHA], leak_ok=True)
        self.assertEqual(code, 0, out)
        self.assertNotIn(SENHA, out, "senha ecoada no terminal")
        self.assertNotIn(SENHA, self.raw(self.frase_file).decode())
        self.init()
        self.assertNotEqual(self.gate("stop", frase=SENHA.lower())[0], 0, "senha é case-sensitive")
        code, out, n = self.gate("stop", frase=SENHA)
        self.assertEqual(code, 0, out)
        self.assertNotIn(SENHA, out)

    def test_weak_passwords_refused(self):
        for fraca in ("abcdefghijkl", "abcdef123456", "aaaaaaaaaaaa", "Aa1!Aa1!Aa1!", "Ab1!xyz"):
            with self.subTest(fraca=fraca):
                code, out, _ = self.tty("frase", "definir", answers=[fraca, fraca])
                self.assertNotEqual(code, 0, "aceitou senha fraca %r" % fraca)
                self.assertFalse(os.path.exists(self.frase_file))
        code, out, _ = self.tty("frase", "definir", answers=[SENHA, SENHA], leak_ok=True)  # controle
        self.assertEqual(code, 0, out)

    def test_definir_without_work(self):
        """A frase é do founder, não da campanha: `ac.py frase definir` dispensa --work; o resto continua exigindo."""
        code, out, n = self.tty("frase", "definir", answers=[FRASE, FRASE], argv0=[sys.executable, AC])
        self.assertEqual(code, 0, out)
        self.assertEqual(n, 2)
        self.assertTrue(os.path.isfile(self.frase_file))
        code, out, n = self.tty("frase", "conferir", answers=[FRASE], argv0=[sys.executable, AC])
        self.assertEqual(code, 2, "frase conferir sem --work deveria exigir --work: %s" % out)
        code, out, n = self.tty("gate", "stop", "--by", "f", "--decision", "approve", answers=[FRASE],
                                argv0=[sys.executable, AC])
        self.assertEqual(code, 2, out)
        p = subprocess.run([sys.executable, AC, "frase", "definir"], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, env=self.env, timeout=60, universal_newlines=True,
                           start_new_session=True)
        self.assertEqual(p.returncode, 2, "sem tty continua exit 2: %s" % p.stdout)

    def test_weak_phrases_refused(self):
        for fraca in ("curta demais", "abc def ghi", "umapalavraenormesemespacos", "duas palavrasgrandes"):
            with self.subTest(fraca=fraca):
                code, out, _ = self.tty("frase", "definir", answers=[fraca, fraca])
                self.assertNotEqual(code, 0, "aceitou frase fraca %r" % fraca)
                self.assertFalse(os.path.exists(self.frase_file))
        self.definir()  # controle: ≥12 caracteres e ≥3 palavras grava

    def test_definir_requires_tty(self):
        code, out = self.cli("frase", "definir")
        self.assertEqual(code, 2, out)
        code, out = self.cli("frase", "definir", input="%s\n%s\n" % (FRASE, FRASE))
        self.assertEqual(code, 2, out)
        self.assertFalse(os.path.exists(self.frase_file))
        self.definir()  # controle: no terminal grava

    def test_change_requires_old_phrase(self):
        self.definir()
        before = self.raw(self.frase_file)
        code, out, n = self.tty("frase", "definir", answers=["errada errada errada", OUTRA, OUTRA])
        self.assertNotEqual(code, 0, "trocou a frase sem a antiga")
        self.assertEqual(self.raw(self.frase_file), before, "arquivo mudou com frase antiga errada")
        code, out, n = self.tty("frase", "definir", answers=[FRASE, OUTRA, OUTRA])
        self.assertEqual(code, 0, out)
        self.assertEqual(n, 3, "troca: FRASE antiga, nova, nova de novo")
        fj = self.fj()
        self.assertEqual(fj["verificador"], kdf(OUTRA, fj["salt_verificador"], fj).hex())
        self.init()
        self.assertNotEqual(self.gate("stop", frase=FRASE)[0], 0, "frase antiga ainda aprova")
        self.assertEqual(self.gate("stop", frase=OUTRA)[0], 0)


# ====================================================================== 2. gate/preauth com a frase

class R2AprovacaoComFraseTest(Base):
    def test_gate_with_phrase_records_tag_in_state_ledger_and_audit(self):
        self.definir()
        self.init()
        before = self.raw(self.p_state())
        code, out, n = self.gate("stop")
        self.assertEqual(code, 0, out)
        self.assertEqual(n, 1, "gate pede a frase uma vez")
        self.assertNotIn("DESAFIO", out, "o desafio numérico deveria ter saído")
        evs = [(i + 1, x) for i, x in enumerate(self.ledger()) if x.get("event") == "gate"]
        self.assertEqual(len(evs), 1)
        seq, ev = evs[0]
        self.assertEqual(ev.get("seq"), seq, "seq = número (1-based) da linha do evento no ledger.jsonl")
        self.assertEqual(ev.get("estado_hash"), sha(before), "estado_hash = sha256 do state.json antes da aprovação")
        self.assertEqual(ev.get("tag"), self.tag(FRASE, "stop", "approve", seq, sha(before)),
                         "tag ≠ HMAC-SHA256(pbkdf2(frase, salt_chave), canonical)")
        au = [x for x in self.audit_lines() if x.get("cmd") == "gate"]
        self.assertEqual(len(au), 1)
        for k in ("name", "decision", "by", "user", "tty", "ts"):
            self.assertTrue(au[0].get(k), "audit sem %s" % k)
        self.assertEqual(os.path.realpath(au[0]["work"]), self.work)
        self.assertEqual((au[0].get("seq"), au[0].get("estado_hash"), au[0].get("tag")),
                         (seq, ev["estado_hash"], ev["tag"]))
        g = self.state()["gates"]["stop"]
        self.assertEqual((g.get("decision"), g.get("simulated"), g.get("seq"), g.get("tag")),
                         ("approve", False, seq, ev["tag"]))
        self.assertEqual(self.cli("check", "intake.3")[0], 0)

    def test_preauth_with_phrase_records_tag(self):
        self.definir()
        self.init()
        before = self.raw(self.p_state())
        code, out, n = self.tty("preauth", "commit", "--by", "founder", "--requires", "integracao.1",
                                "integracao.2", answers=[FRASE])
        self.assertEqual(code, 0, out)
        evs = [(i + 1, x) for i, x in enumerate(self.ledger()) if x.get("event") == "preauth"]
        self.assertEqual(len(evs), 1)
        seq, ev = evs[0]
        self.assertEqual(ev.get("tag"), self.tag(FRASE, "commit", "preauth:integracao.1,integracao.2", seq,
                                                 sha(before)))
        self.assertEqual(self.state()["preauth"]["commit"].get("tag"), ev["tag"])
        self.assertEqual([x.get("tag") for x in self.audit_lines() if x.get("cmd") == "preauth"], [ev["tag"]])

    def test_wrong_phrase_exit_nonzero_nothing_recorded(self):
        self.definir()
        self.init()
        snap = self.snapshot()
        code, out, n = self.gate("stop", frase="lagoa serena de verao")
        self.assertNotEqual(code, 0)
        self.assertEqual(self.snapshot(), snap, "frase errada gravou algo (state/ledger/audit)")
        code, out, n = self.tty("preauth", "commit", "--by", "f", "--requires", "integracao.1", answers=[OUTRA])
        self.assertNotEqual(code, 0)
        self.assertEqual(self.snapshot(), snap)

    def test_no_phrase_defined_refused_with_instruction(self):
        self.init()
        snap = self.snapshot()
        code, out, n = self.gate("stop")
        self.assertEqual(code, 2, out)
        self.assertEqual(n, 0, "sem frase definida não deve nem pedir a frase")
        self.assertIn("frase definir", out)
        self.assertEqual(self.snapshot(), snap)

    def test_reject_decision_also_tagged(self):
        self.definir()
        self.init()
        before = self.raw(self.p_state())
        self.assertEqual(self.gate("plan:DEC-1", decision="reject")[0], 0)
        seq, ev = [(i + 1, x) for i, x in enumerate(self.ledger()) if x.get("event") == "gate"][0]
        self.assertEqual(ev.get("tag"), self.tag(FRASE, "plan:DEC-1", "reject", seq, sha(before)))


# ====================================================================== 3. frase conferir (forja à mão pega)

class R3ConferirTest(Base):
    def test_legit_approvals_confer_and_record_frase_conferida(self):
        self.pronto()
        self.assertEqual(self.tty("preauth", "commit", "--by", "founder", "--requires", "integracao.1",
                                  answers=[FRASE])[0], 0)
        self.cli("gate", "ensaio", "--by", "bot", "--decision", "approve", "--simulated")  # simulado: ignorado
        before = self.raw(self.p_state())
        code, out, n = self.conferir()
        self.assertEqual(code, 0, out)
        led = self.ledger()
        evs = [(i + 1, x) for i, x in enumerate(led) if x.get("event") == "frase-conferida"]
        self.assertEqual(len(evs), 1, "conferir ok grava 1 evento frase-conferida no ledger")
        seq, ev = evs[0]
        self.assertEqual(ev.get("seq"), seq)
        self.assertEqual(ev.get("tag"), self.tag(FRASE, "frase-conferida", "ok", seq, sha(before)))
        self.assertEqual([x.get("tag") for x in self.audit_lines() if x.get("cmd") == "frase-conferida"],
                         [ev["tag"]])
        self.assertEqual(self.conferir()[0], 0, "frase-conferida anterior também tem de conferir")

    def _refused(self, *must_cite):
        snap_led = len(self.ledger())
        code, out, n = self.conferir()
        self.assertEqual(code, 1, "forja não detectada: %s" % out)
        for x in must_cite:
            self.assertIn(x, out, "conferir deve listar a aprovação problemática")
        self.assertFalse([x for x in self.ledger()[snap_led:] if x.get("event") == "frase-conferida"],
                         "conferir com problema não grava frase-conferida")
        return out

    def test_state_only_forged_gate_caught(self):
        self.pronto()
        st = self.state()
        st["gates"]["commit"] = {"by": "founder", "decision": "approve", "note": "", "at": "x", "simulated": False}
        self.save_state(st)
        self._refused("commit")

    def test_forged_without_tag_caught(self):
        self.pronto()
        self.forge("commit")
        self._refused("commit")

    def test_forged_random_tag_caught(self):
        self.pronto()
        self.forge("commit", tag="ab" * 32)
        self._refused("commit")

    def test_forged_tag_from_wrong_phrase_caught(self):
        self.pronto()
        self.forge("commit", tag=lambda seq, eh: self.tag(OUTRA, "commit", "approve", seq, eh))
        self._refused("commit")

    def test_replayed_valid_tag_caught(self):
        self.pronto()
        legit = [x for x in self.ledger() if x.get("event") == "gate"][0]["tag"]
        self.forge("commit", tag=legit)
        self._refused("commit")

    def _round_new_with_old_commit(self):
        self.pronto()
        self.assertEqual(self.gate("commit")[0], 0)  # aprovação legítima na rodada 0
        self.old_commit = dict(self.state()["gates"]["commit"])
        self.old_lines = [l for l in self.raw(self.p_ledger()).decode().splitlines(True) if '"commit"' in l]
        self.mark_done("intake", "oraculo", "base")
        code, out = self.cli("round", "new")
        self.assertEqual(code, 0, out)
        self.assertNotIn("commit", self.state()["gates"], "round new deveria zerar o portão commit")

    def test_replay_old_round_approval_in_state_caught(self):
        """Agente devolve ao state.json o commit aprovado na rodada anterior (mesmo seq/tag, válidos)."""
        self._round_new_with_old_commit()
        st = self.state()
        st["gates"]["commit"] = self.old_commit
        self.save_state(st)
        self._refused("commit")

    def test_replay_by_copying_ledger_line_caught(self):
        """...e ainda copia a linha antiga do ledger (e do audit) para depois do round-new."""
        self._round_new_with_old_commit()
        with open(self.p_ledger(), "a") as fh:
            fh.write("".join(self.old_lines))
        au = [l for l in self.raw(self.audit).decode().splitlines(True) if '"commit"' in l]
        with open(self.audit, "a") as fh:
            fh.write("".join(au))
        st = self.state()
        st["gates"]["commit"] = self.old_commit
        self.save_state(st)
        self._refused("commit")

    def test_forged_frase_conferida_caught(self):
        self.pronto()
        self.forge("frase-conferida", decisao="ok", tag="cd" * 32, event="frase-conferida", state=False)
        self._refused("frase-conferida")

    def test_audit_line_missing_caught(self):
        self.pronto()
        with open(self.audit, "w") as fh:
            fh.write("")
        self._refused("stop")

    def test_in_audit_but_missing_from_ledger_caught(self):
        self.pronto()
        self.assertEqual(self.gate("commit")[0], 0)
        lines = self.raw(self.p_ledger()).decode().splitlines(True)
        with open(self.p_ledger(), "w") as fh:  # agente trunca o ledger (some a aprovação do commit)
            fh.write("".join(l for l in lines if '"commit"' not in l))
        self._refused("commit")

    def test_wrong_phrase_at_conferir_refused_nothing_recorded(self):
        self.pronto()
        snap = self.snapshot()
        code, out, n = self.conferir(frase=OUTRA)
        self.assertNotEqual(code, 0)
        self.assertEqual(self.snapshot(), snap)

    def test_agent_replacing_frase_file_is_caught_by_founder(self):
        """Agente troca frase.json pela frase DELE e forja com a chave dele: a frase do founder não confere."""
        self.pronto()
        fj = self.fj()
        salt_v, salt_k = os.urandom(16).hex(), os.urandom(16).hex()
        novo = dict(fj, salt_verificador=salt_v, salt_chave=salt_k)
        novo["verificador"] = kdf(OUTRA, salt_v, novo).hex()
        with open(self.frase_file, "w") as fh:
            json.dump(novo, fh)
        os.chmod(self.frase_file, 0o600)
        self.forge("commit", tag=lambda seq, eh: self.tag(OUTRA, "commit", "approve", seq, eh, fj=novo))
        snap_led = len(self.ledger())
        code, out, n = self.conferir(frase=FRASE)
        self.assertNotEqual(code, 0, "frase do founder 'conferiu' contra um frase.json trocado")
        self.assertFalse([x for x in self.ledger()[snap_led:] if x.get("event") == "frase-conferida"])

    def test_conferir_requires_tty(self):
        self.pronto()
        self.assertEqual(self.cli("frase", "conferir")[0], 2)
        self.assertEqual(self.cli("frase", "conferir", input=FRASE + "\n")[0], 2)


# ====================================================================== 4. done decisao exige frase-conferida

class R4DoneDecisaoTest(Base):
    def _ate_decisao(self):
        self.pronto()
        self.mark_done(*[n for n in ciclo()["order"] if n != "decisao"])
        self.assertEqual(self.cli("set", "decision", "parar")[0], 0)
        self.assertEqual(self.cli("set", "report", "relatorio curto")[0], 0)

    def test_done_decisao_needs_frase_conferida(self):
        self._ate_decisao()
        code, out = self.cli("done", "decisao")
        self.assertEqual(code, 1, "done decisao fechou sem o founder conferir: %s" % out)
        self.assertIn("frase conferir", out)
        self.assertNotIn(self.state()["stage"], ("concluida", "concluída"))
        self.assertEqual(self.conferir()[0], 0)
        code, out = self.cli("done", "decisao")
        self.assertEqual(code, 0, out)
        self.assertIn(self.state()["stage"], ("concluida", "concluída"))

    def test_approval_after_conferida_requires_new_conferida(self):
        self._ate_decisao()
        self.assertEqual(self.conferir()[0], 0)
        self.assertEqual(self.gate("commit")[0], 0)
        self.assertEqual(self.cli("done", "decisao")[0], 1, "aprovação posterior à conferência não conferida")
        self.assertEqual(self.conferir()[0], 0)
        self.assertEqual(self.cli("done", "decisao")[0], 0)


# ====================================================================== 5. nenhum canal alternativo para a frase

class R5SemCanalAlternativoTest(Base):
    def test_frase_flag_refused(self):
        code, out = self.cli("frase", "definir", "--frase", FRASE, leak_ok=True)
        self.assertEqual(code, 2, out)
        self.assertFalse(os.path.exists(self.frase_file))
        self.definir()
        self.init()
        snap = self.snapshot()
        self.assertEqual(self.cli("gate", "stop", "--by", "f", "--decision", "approve", "--frase", FRASE,
                                  leak_ok=True)[0], 2)
        code, out, n = self.tty("gate", "stop", "--by", "f", "--decision", "approve", "--frase", FRASE,
                                leak_ok=True)
        self.assertEqual(code, 2, out)
        self.assertEqual(self.cli("frase", "conferir", "--frase", FRASE, leak_ok=True)[0], 2)
        self.assertEqual(self.snapshot(), snap)

    def test_env_vars_never_supply_phrase(self):
        self.definir()
        self.init()
        snap = self.snapshot()
        env = dict(self.env, **{k: FRASE for k in BYPASS_ENV})
        self.assertEqual(self.cli("gate", "stop", "--by", "f", "--decision", "approve", env=env)[0], 2)
        self.assertEqual(self.cli("frase", "conferir", env=env)[0], 2)
        code, out, n = self.tty("gate", "stop", "--by", "f", "--decision", "approve", env=env,
                                answers=["nao sei a frase"])
        self.assertNotEqual(code, 0, "variável de ambiente forneceu a frase")
        self.assertEqual(self.snapshot(), snap)

    def test_piped_stdin_refused_even_with_correct_phrase_and_tty(self):
        self.definir()
        self.init()
        snap = self.snapshot()
        self.assertEqual(self.cli("gate", "stop", "--by", "f", "--decision", "approve", input=FRASE + "\n")[0], 2)
        self.assertEqual(self.cli("preauth", "commit", "--by", "f", "--requires", "integracao.1",
                                  input=FRASE + "\n")[0], 2)
        code, out, n = self.tty("gate", "stop", "--by", "f", "--decision", "approve", stdin_data=FRASE + "\n",
                                answers=[FRASE])
        self.assertEqual(code, 2, "stdin em pipe precisa ser recusado (exit 2) mesmo com /dev/tty: %s" % out)
        self.assertEqual(self.snapshot(), snap)

    def test_phrase_never_written_anywhere(self):
        self.pronto()
        self.assertEqual(self.tty("preauth", "commit", "--by", "founder", "--requires", "integracao.1",
                                  answers=[FRASE])[0], 0)
        self.gate("x", frase="lagoa serena de verao")
        self.assertEqual(self.conferir()[0], 0)
        blobs = [self.raw(self.frase_file), self.raw(self.audit)]
        for root, _, files in os.walk(self.work):
            blobs += [self.raw(os.path.join(root, f)) for f in files]
        for b in blobs:
            self.assertNotIn(FRASE.encode(), b)
            self.assertNotIn(b"lagoa serena de verao", b, "frase ERRADA digitada também não pode ser gravada")


# ====================================================================== 6. forja por pty e por import

class R6ForjaTest(Base):
    def test_pty_agent_without_phrase_refused_with_phrase_accepted(self):
        self.definir()
        self.init()
        snap = self.snapshot()
        for chute in ("1234", "", FRASE.upper(), FRASE + " x", FRASE[:-1], "DESAFIO", " ".join(FRASE.split()[::-1])):
            with self.subTest(chute=chute):
                code, out, n = self.gate("stop", frase=chute)
                self.assertNotEqual(code, 0, "aceitou %r" % chute)
                self.assertEqual(self.snapshot(), snap)
        self.assertEqual(self.gate("stop", frase="  %s  " % FRASE)[0], 0, "espaços nas pontas são normalizados")

    def test_import_and_call_directly_refused(self):
        self.definir()
        self.init()
        snap = self.snapshot()
        code = ("import sys; sys.path.insert(0, %r); import ac; "
                "sys.exit(ac.main(['--work', %r, 'gate', 'stop', '--by', 'f', '--decision', 'approve']))"
                % (SCRIPTS, self.work))
        p = subprocess.run([sys.executable, "-c", code], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, env=self.env, timeout=120, universal_newlines=True,
                           start_new_session=True)
        self.outputs.append(p.stdout)
        self.assertEqual(p.returncode, 2, p.stdout)
        c, out, n = self.tty(answers=["nao sei a frase"],
                             argv0=[sys.executable, "-c", code])
        self.assertNotEqual(c, 0, out)
        self.assertEqual(self.snapshot(), snap)


# ====================================================================== 7. hook

def run_hook(cmd, agent):
    p = {"session_id": "s", "transcript_path": "/tmp/t.jsonl", "cwd": "/tmp", "hook_event_name": "PreToolUse",
         "tool_name": "Bash", "tool_input": {"command": cmd, "description": "x"}}
    if agent:
        p.update(agent_id="a-1", agent_type="general-purpose")
    r = subprocess.run([sys.executable, HOOK], input=json.dumps(p), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       timeout=30, universal_newlines=True)
    return r.returncode, r.stdout


def denies(code, out):
    if code == 2:
        return True
    try:
        j = json.loads(out) if out.strip() else {}
    except ValueError:
        return False
    return (j.get("hookSpecificOutput") or {}).get("permissionDecision") == "deny" or j.get("decision") == "block"


DENY_FRASE = [
    "python3 %s --work /tmp/c frase definir" % AC,
    "python3 ~/.claude/skills/auto-correcao/scripts/ac.py --work /tmp/c frase conferir",
    "python3 ac.py --work /tmp/c frase conferir",
    "cd /x && ./ac.py --work . frase definir",
    "PYTHONPATH=/x python3 -m ac --work /tmp/c frase conferir",
    "sh -c 'python3 ac.py --work /tmp/c frase definir'",
    "python3 $AC --work /tmp/c frase conferir",
    "echo x | python3 ac.py --work /tmp/c frase definir",
    "true; python3 '%s' '--work' /tmp/c 'frase' 'conferir'" % AC,
    "python3 -c 'import runpy,sys; sys.argv=[\"ac.py\",\"--work\",\"/tmp/c\",\"frase\",\"conferir\"]; "
    "runpy.run_path(\"%s\", run_name=\"__main__\")'" % AC,
]
ALLOW_FRASE = [
    "grep -n frase %s" % AC,
    "cat ~/.claude/skills/auto-correcao/scripts/frase.py",
    "echo frase",
    "python3 other.py frase definir",
    "python3 ac.py --work /tmp/c status",
]


class R7HookTest(unittest.TestCase):
    def test_hook_denies_frase_commands(self):
        for cmd in DENY_FRASE:
            for agent in (False, True):
                with self.subTest(cmd=cmd, agent=agent):
                    code, out = run_hook(cmd, agent)
                    self.assertTrue(denies(code, out), "hook não negou %r" % cmd)

    def test_hook_allows_reading_about_frase(self):
        for cmd in ALLOW_FRASE:
            with self.subTest(cmd=cmd):
                code, out = run_hook(cmd, True)
                self.assertEqual(code, 0)
                self.assertFalse(denies(code, out))


# ====================================================================== 7b. hook: controles de uso real (sem falso positivo)
# Regra (ESPEC): nega só quando o ac.py é EXECUTADO e seu 1º argumento posicional (depois das opções globais, ex.
# `--work W` / `--work=W`) é gate|preauth|frase. `oracle change` NÃO é aprovação humana (exige --why/--evidence e
# fica no ledger). Texto que não é executado (printf/echo para arquivo, mensagem de commit, grep) não conta.

ALLOW_USO_REAL = [
    "python3 %s --work /tmp/c front report frase --file /tmp/rel.md" % AC,
    "python3 ac.py --work /tmp/c front report gate --file /tmp/rel.md",
    "printf 'texto com frase e gate e preauth\\n' > /tmp/rel.md && python3 ac.py --work /tmp/c done correcao",
    "printf 'texto com frase e gate' > /tmp/x.md; python3 %s --work /tmp/c set integration.tests_green true" % AC,
    "echo 'ac.py gate stop e frase conferir' > /tmp/nota.md && python3 ac.py --work /tmp/c status",
    "git commit -F /tmp/msg.txt",
    "git commit -m 'ac.py: gate/preauth agora pedem a frase (frase conferir, frase definir)'",
    "grep -n frase ac.py",
    "grep -n 'frase conferir\\|gate' %s" % AC,
    "python3 ac.py --work /tmp/c oracle change --why x --evidence y",
]
DENY_MANTIDO = [
    "python3 ac.py --work /tmp/c frase definir",
    "python3 ac.py --work=/tmp/c frase conferir",
    "python3 %s --work /tmp/c gate stop --by f --decision approve" % AC,
    "python3 ac.py --work /tmp/c preauth commit --by f --requires integracao.1",
    "sh -c 'python3 ac.py --work /tmp/c gate stop --by f --decision approve'",
    "printf 'x' > /tmp/a.md && python3 ac.py --work /tmp/c gate stop --by f --decision approve",
    "bash -s <<'EOF'\npython3 ac.py --work /tmp/c gate stop --by f --decision approve\nEOF",
    "bash <<EOF\npython3 %s --work /tmp/c frase conferir\nEOF" % AC,
    "cat <<'EOF' | bash\npython3 ac.py --work /tmp/c preauth commit --by f --requires integracao.1\nEOF",
    "printf 'python3 ac.py --work /tmp/c gate stop --by f --decision approve' | sh",
]


class R7bHookUsoRealTest(unittest.TestCase):
    def test_legit_commands_allowed(self):
        for cmd in ALLOW_USO_REAL:
            for agent in (False, True):
                with self.subTest(cmd=cmd, agent=agent):
                    code, out = run_hook(cmd, agent)
                    self.assertFalse(denies(code, out), "falso positivo: hook negou comando legítimo %r" % cmd)
                    self.assertEqual(code, 0)

    def test_approvals_still_denied(self):
        for cmd in DENY_MANTIDO:
            for agent in (False, True):
                with self.subTest(cmd=cmd, agent=agent):
                    code, out = run_hook(cmd, agent)
                    self.assertTrue(denies(code, out), "hook deixou passar aprovação: %r" % cmd)


# ====================================================================== 8. AC-06 escopo com vírgula

class R8EscopoVirgulaTest(Base):
    def test_comma_glob_refused_or_split(self):
        for sc in ("a/**, b/**", "a/**,b/**"):
            with self.subTest(scope=sc):
                shutil.rmtree(self.work, ignore_errors=True)
                code, out = self.cli("init", "--target", self.target, "--scope", sc)
                if code == 0:
                    self.assertEqual(self.state().get("scope"), ["a/**", "b/**"], "dividiu errado")
                else:
                    self.assertEqual(code, 2, out)
                    self.assertTrue("vírgula" in out or "," in out, "recusa deve citar a vírgula: %s" % out)
                    st = self.state() if os.path.isfile(self.p_state()) else {}
                    self.assertFalse([g for g in st.get("scope") or [] if "," in g], "glob com vírgula gravado")


# ====================================================================== 9. rollout: aprovações legadas (v0.3, sem tag)

LEGADO_TS = "2026-09-30T12:00:00Z"  # anterior a qualquer frase.json criado pelo teste


class R9LegadoTest(Base):
    """Campanhas abertas sob a v0.3 têm aprovações SEM tag. Só as anteriores a frase.json.criada_em (e anteriores ao
    1º evento tagueado do ledger) são legadas; o founder as assina UMA vez com `frase conferir --assinar-legado`."""

    def legado(self, ts=LEGADO_TS, gates=("stop",), preauths=("commit",)):
        """Grava aprovações exatamente como a v0.3 gravava (state, ledger e audit, sem seq/estado_hash/tag)."""
        st = self.state()
        led, aud = [], []
        for g in gates:
            led.append({"ts": ts, "event": "gate", "name": g, "decision": "approve", "by": "founder",
                        "simulated": False})
            st.setdefault("gates", {})[g] = {"by": "founder", "decision": "approve", "note": "", "at": ts,
                                             "simulated": False}
            aud.append({"cmd": "gate", "name": g, "decision": "approve", "by": "founder", "work": self.work,
                        "user": "ana", "tty": "/dev/ttys001", "ts": ts})
        for pa in preauths:
            led.append({"ts": ts, "event": "preauth", "name": pa, "by": "founder", "requires": ["integracao.1"]})
            st.setdefault("preauth", {})[pa] = {"by": "founder", "requires": ["integracao.1"], "note": "", "at": ts}
            aud.append({"cmd": "preauth", "name": pa, "by": "founder", "requires": ["integracao.1"],
                        "work": self.work, "user": "ana", "tty": "/dev/ttys001", "ts": ts})
        self.save_state(st)
        with open(self.p_ledger(), "a") as fh:
            fh.write("".join(json.dumps(x, sort_keys=True) + "\n" for x in led))
        os.makedirs(os.path.dirname(self.audit), exist_ok=True)
        with open(self.audit, "a") as fh:
            fh.write("".join(json.dumps(x, sort_keys=True) + "\n" for x in aud))

    def campanha_v03(self):
        self.init()
        self.legado()
        self.definir()  # rollout: o founder define a frase DEPOIS das aprovações v0.3

    def assinar(self, frase=FRASE):
        return self.tty("frase", "conferir", "--assinar-legado", answers=[frase])

    def eventos(self, ev):
        return [(i + 1, x) for i, x in enumerate(self.ledger()) if x.get("event") == ev]

    def test_definir_records_criada_em(self):
        antes = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.definir()
        depois = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        c = self.fj().get("criada_em")
        self.assertRegex(c or "", r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$", "frase.json sem criada_em (UTC ISO)")
        self.assertTrue(antes <= c <= depois, "criada_em %r fora de [%s, %s]" % (c, antes, depois))

    def test_conferir_without_flag_lists_legacy_with_instruction(self):
        self.campanha_v03()
        snap = self.snapshot()
        code, out, n = self.conferir()
        self.assertEqual(code, 1, "aprovação legada sem tag passou no conferir: %s" % out)
        for x in ("stop", "commit", "--assinar-legado"):
            self.assertIn(x, out)
        self.assertEqual(self.snapshot(), snap, "conferir com legado pendente gravou algo")

    def test_assinar_legado_signs_each_then_conferir_passes(self):
        self.campanha_v03()
        legadas = [(i, x) for i, x in enumerate(self.ledger(), 1) if x.get("event") in ("gate", "preauth")]
        before = self.raw(self.p_state())
        code, out, n = self.assinar()
        self.assertEqual(code, 0, out)
        self.assertEqual(n, 1, "pede a frase uma vez")
        evs = self.eventos("legado-assinado")
        self.assertEqual(len(evs), 1, "um evento humano legado-assinado")
        seq, ev = evs[0]
        itens = ev.get("itens") or []
        self.assertEqual([it.get("linha") for it in itens], [i for i, _ in legadas], "itens = linhas legadas, em ordem")
        esperado = {"gate": lambda x: (x["name"], x["decision"]),
                    "preauth": lambda x: (x["name"], "preauth:" + ",".join(x["requires"]))}
        for (linha, rec), it in zip(legadas, itens):
            nome, decisao = esperado[rec["event"]](rec)
            self.assertEqual((it.get("nome"), it.get("decisao"), it.get("ts")), (nome, decisao, rec["ts"]))
            self.assertEqual(it.get("tag"), self.tag(FRASE, nome, decisao, linha, "legado:" + rec["ts"]),
                             "tag do item ≠ HMAC(K, canonical(work, nome, decisao, linha, 'legado:'+ts))")
        self.assertEqual(ev.get("seq"), seq)
        self.assertEqual(ev.get("estado_hash"), sha(before))
        self.assertEqual(ev.get("tag"), self.tag(FRASE, "legado-assinado",
                                                 "legado:" + ",".join(str(i) for i, _ in legadas), seq, sha(before)))
        au = [x for x in self.audit_lines() if x.get("cmd") == "legado-assinado"]
        self.assertEqual([(x.get("seq"), x.get("tag"), x.get("itens")) for x in au], [(seq, ev["tag"], itens)])
        code, out, n = self.conferir()
        self.assertEqual(code, 0, "depois de assinado, o legado confere: %s" % out)
        self.assertEqual(len(self.eventos("frase-conferida")), 1)

    def test_assinar_legado_wrong_phrase_nothing_recorded(self):
        self.campanha_v03()
        snap = self.snapshot()
        self.assertNotEqual(self.assinar(frase=OUTRA)[0], 0)
        self.assertEqual(self.snapshot(), snap)
        self.assertEqual(self.cli("frase", "conferir", "--assinar-legado")[0], 2, "sem tty → exit 2")
        self.assertEqual(self.snapshot(), snap)
        self.assertEqual(self.assinar()[0], 0)  # controle: com a frase assina

    def test_untagged_after_criada_em_is_forgery(self):
        self.definir()
        self.init()
        self.assertEqual(self.gate("stop")[0], 0)
        self.forge("commit")  # sem tag, ts de agora (≥ criada_em): forja, não legado
        snap = self.snapshot()
        code, out, n = self.conferir()
        self.assertEqual(code, 1, out)
        self.assertIn("commit", out)
        code, out, n = self.assinar()
        self.assertEqual(code, 1, "--assinar-legado assinou aprovação posterior a criada_em: %s" % out)
        self.assertIn("commit", out)
        self.assertEqual(self.snapshot(), snap)

    def test_mixed_legacy_and_forgery_signs_nothing(self):
        self.campanha_v03()
        self.forge("plan:DEC-9")  # sem tag, ts de agora, ainda antes de qualquer evento tagueado
        snap = self.snapshot()
        code, out, n = self.assinar()
        self.assertEqual(code, 1, out)
        self.assertIn("plan:DEC-9", out)
        self.assertEqual(self.snapshot(), snap, "com forja na lista, nem o legado legítimo é assinado")

    def test_backdated_untagged_after_first_tagged_event_refused(self):
        """Agente acrescenta, depois de eventos tagueados, uma aprovação sem tag com ts antigo (retroativo)."""
        self.campanha_v03()
        self.assertEqual(self.assinar()[0], 0)
        self.legado(gates=("plan:DEC-7",), preauths=())  # ts LEGADO_TS < criada_em, mas depois do 1º tagueado
        snap = self.snapshot()
        code, out, n = self.conferir()
        self.assertEqual(code, 1, out)
        self.assertIn("plan:DEC-7", out)
        code, out, n = self.assinar()
        self.assertEqual(code, 1, "assinou aprovação retroativa posterior ao 1º evento tagueado: %s" % out)
        self.assertIn("plan:DEC-7", out)
        self.assertEqual(self.snapshot(), snap)

    def test_forged_legado_assinado_caught(self):
        self.campanha_v03()
        legadas = [i for i, x in enumerate(self.ledger(), 1) if x.get("event") in ("gate", "preauth")]
        rec = self.forge("legado-assinado", decisao="legado:" + ",".join(map(str, legadas)), tag="ef" * 32,
                         event="legado-assinado", state=False)
        self.assertTrue(rec)
        code, out, n = self.conferir()
        self.assertEqual(code, 1, "legado-assinado forjado (tag sem a frase) passou: %s" % out)
        self.assertIn("legado-assinado", out, "conferir deve apontar o evento legado-assinado forjado")
        self.assertNotEqual(self.assinar()[0], 0, "com legado-assinado forjado no ledger, assinar recusa")


# ====================================================================== módulo compartilhado scripts/frase.py

class R0ModuloFraseTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue(os.path.isfile(FRASE_PY), "falta %s (módulo compartilhado ac.py/co_estado)" % FRASE_PY)
        spec = importlib.util.spec_from_file_location("frase_oraculo_v04", FRASE_PY)
        self.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.m)

    def test_canonical_and_tag(self):
        args = ("/w", "stop", "approve", 2, "ab" * 32)
        self.assertEqual(self.m.canonical(*args), canonical(*args))
        k = b"\x01" * 32
        self.assertEqual(self.m.tag(k, *args), hmac.new(k, canonical(*args), hashlib.sha256).hexdigest())

    def test_strength_and_normalization(self):
        for fraca in FRACAS:
            self.assertTrue(self.m.problemas_forca(fraca), "aceitou fraca %r" % fraca)
        for forte in FORTES:
            self.assertEqual(self.m.problemas_forca(forte), [], "recusou forte %r" % forte)
        self.assertEqual(self.m.normalizar("  %s \n" % FRASE), FRASE)


if __name__ == "__main__":
    unittest.main()
