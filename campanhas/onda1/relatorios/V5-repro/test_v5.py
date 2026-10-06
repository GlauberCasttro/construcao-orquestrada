"""V5 — reproduções executadas do verificador cego da onda 1. Cada teste FALHA enquanto o defeito existir (a
asserção descreve o comportamento exigido pelo contrato). Rodar:
  python3 -m unittest -v test_v5            (e  V5_PY=/usr/bin/python3 /usr/bin/python3 -m unittest -v test_v5)
"""
import json
import os
import subprocess
import unittest

from _base5 import Base, PY

FORJA = ("python3 -c \"import sys; sys.path.insert(0, '%(scripts)s'); import co_estado as e; w = '%(ws)s'; "
         "h = e.fold(w)['hash_estado']; a = e.paths(w)['aprovacoes']; "
         "e.transicionar(w, 'aprovado', {}, _humano={"
         "'payload_aprovacao': lambda s: {'portao': 'stop', 'decisao': 'aprovado', 'arquivo': a + '/stop-' + str(s) "
         "+ '.json', 'hash_estado': h, 'usuario_so': e._os_user(), 'ttyname': '/dev/ttys001'}, "
         "'depois_de_gravar': lambda n: e._audit_append(e.audit_path(), {'ts': e.now_ts(), 'tipo': 'aprovacao', "
         "'cmd': 'aprovar', 'name': 'stop', 'decision': 'aprovado', 'by': 'humano', 'work': w, 'user': e._os_user(), "
         "'tty': '/dev/ttys001', 'seq': [r for r in n if r['evento'] == 'aprovacao'][0]['seq'], 'hash_estado': h})})\"")


class V5(Base):
    # ------------------------------------------------------------------ V5-A1 (alta): forja de aprovação humana
    def test_A1_forja_aprovacao_humana_pela_api_sem_tty(self):
        """I6/D9: transição humana só por `co.py aprovar` (tty + desafio). Um agente com Bash chama a API pública
        co_estado.transicionar(..., _humano=...) numa linha de `python3 -c` (sem `co.py`, sem `aprovar` como
        subcomando, sem caminho protegido literal): o hook PERMITE, a transição humana é gravada sem tty e a linha
        `tipo aprovacao` forjada no audit faz o cruzamento ledger×audit dar a aprovação como LIMPA."""
        self.init()
        self.prefixo("AH_STOP")
        cmd = FORJA % {"scripts": self.scripts, "ws": self.ws}
        rc_hook, err = self.hook_bash(cmd, cwd=self.root, agent_type="builder-A")
        auditadas = [x for x in self.audit_lines() if x.get("tipo") == "tool_call"]
        p = subprocess.run(["bash", "-c", cmd.replace("python3", PY, 1)], env=self.env, cwd=self.root,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=120)
        st = self.status()
        rc, out, e2 = self.in_proc("import co_estado as E, co_portao as P\nws=%r\nr=E.ler_ledger(ws)\n"
                                   "print(json.dumps([E.aprovacoes_sem_audit(ws, r), P.aprovacoes_sem_audit(ws, r)]))"
                                   .replace("import co_estado", "import json, co_estado") % self.ws)
        sujas = json.loads(out.strip().splitlines()[-1]) if rc == 0 else None
        self.assertFalse(rc_hook == 0 and st["obra"]["estado"] == "ORACULO" and sujas == [[], []],
                         "hook exit %d (tool_calls auditadas: %d); execução exit %d %s; estado depois: %s; "
                         "aprovacoes_sem_audit (co_estado, co_portao) = %s ⇒ portão `stop` aprovado por agente, "
                         "sem tty, e o cruzamento ledger×audit o dá como limpo"
                         % (rc_hook, len(auditadas), p.returncode, p.stderr.strip()[-200:], st["obra"], sujas))

    # ------------------------------------------------------------------ V5-M1 (média): V4-9 queda entre ledger e audit
    def test_M1_queda_entre_ledger_e_audit_trava_entrega_para_sempre(self):
        """V4-9: `aprovar` grava arquivo → ledger → audit. Uma queda (SIGKILL/energia, simulada por os._exit no
        início de _audit_append) depois do append do ledger deixa `aprovacao` + transição humana no ledger SEM a
        linha do audit. Não há recuperação: aprovacoes_sem_audit fica ≠ [] para sempre (ledger append-only) e
        veredito_go_final/`co.py veredito` dão NO-GO na entrega de qualquer obra que passou por esse portão."""
        self.init()
        self.prefixo("AH_STOP")
        rc, out, err = self.in_proc(r'''
import co_estado as E, argparse, os
E._stdin_tty = lambda: True
E.human_channel = lambda what: "/dev/ttys999"
E._audit_append = lambda path, rec: os._exit(137)   # queda simulada logo antes da linha do audit
E.cmd_aprovar(argparse.Namespace(work=%r, portao="stop", decisao="aprovado", nota=None))
''' % self.ws)
        self.assertEqual(rc, 137, out + err)
        # "recuperação": o humano roda retomar/status/aprovar de novo — nada repara
        rc_r, out_r, err_r = self.run_co("retomar")
        rc, out, err = self.in_proc("import json, co_estado as E\nws=%r\nr=E.ler_ledger(ws)\n"
                                    "print(json.dumps([E.fold(ws)['obra'], E.aprovacoes_sem_audit(ws, r)]))" % self.ws)
        obra, sujas = json.loads(out.strip().splitlines()[-1])
        self.assertEqual(sujas, [], "após a queda: estado %s; retomar exit %d; aprovacoes_sem_audit = %s (permanente: "
                                    "o ledger é append-only e nenhum comando grava a linha faltante) ⇒ entrega "
                                    "nunca mais satisfaz veredito_go_final" % (obra, rc_r, sujas))

    def test_M1b_queda_entre_arquivo_e_ledger_bloqueia_reaprovar(self):
        """V4-9: queda depois de gravar aprovacoes/<portao>-<seq>.json e antes do append do ledger deixa o arquivo
        órfão; o `aprovar` seguinte calcula o MESMO seq e recusa ("já existe") — o humano fica sem conseguir aprovar
        até alguém gravar outro evento qualquer (o arquivo está em protegido: o agente não pode removê-lo)."""
        self.init()
        self.prefixo("AH_STOP")
        rc, out, err = self.in_proc(r'''
import co_estado as E, argparse, os
E._stdin_tty = lambda: True
E.human_channel = lambda what: "/dev/ttys999"
E._gravar_registros = lambda ws, regs: os._exit(137)   # queda simulada entre o arquivo e o ledger
E.cmd_aprovar(argparse.Namespace(work=%r, portao="stop", decisao="aprovado", nota=None))
''' % self.ws)
        self.assertEqual(rc, 137, out + err)
        orfaos = sorted(os.listdir(os.path.join(self.ws, "aprovacoes")))
        rc, out, err = self.in_proc(r'''
import co_estado as E, argparse
E._stdin_tty = lambda: True
E.human_channel = lambda what: "/dev/ttys999"
try:
    E.cmd_aprovar(argparse.Namespace(work=%r, portao="stop", decisao="aprovado", nota=None)); print("APROVOU")
except E.Fail as e:
    print("RECUSOU:", e)
''' % self.ws)
        self.assertIn("APROVOU", out, "arquivos em aprovacoes/: %s; 2ª tentativa do humano: %s" % (orfaos,
                                                                                                    out.strip()))

    def _rodada_pronta(self):
        """pontos com histórico da rodada e uma comparacao.json (sem platô): sem edição, a saída é `continuar`."""
        json.dump({"schema_version": 1, "pontos": [{"id": "P-01", "texto": "x", "status": "coberto",
                   "cenarios": ["C-01"], "motivo": None, "historico": [{"rodada": 1, "status": "coberto"}]}]},
                  open(os.path.join(self.ws, "pontos.json5"), "w"))
        d = os.path.join(self.ws, "rodadas", "1")
        os.makedirs(d, exist_ok=True)
        json.dump({"Q": {"delta": 0.1, "rotulo": "indício"}}, open(os.path.join(d, "comparacao.json"), "w"))

    # ------------------------------------------------------------------ V5-M2 (média): obra.json5 reescrito decide guarda
    def test_M2_stop_numerico_reescrito_depois_de_premissas_decide_parar(self):
        """V4-8 (limites do founder nas guardas): obra.json5 tem o hash gravado em premissas_ok, mas
        criterio_parada_ok lê o arquivo do disco sem conferir. Medição pass_hat_3 = 0.5 com stop do founder
        `pass_hat_3 >= 1.0`: o orquestrador reescreve stop.numerico.valor para 0.5 e `ev rodada_fechada` sai por
        `parar` (portão entrega) em vez de continuar a corrigir."""
        self.init()
        self.prefixo("FECHAR_RODADA")
        self._rodada_pronta()
        p = os.path.join(self.ws, "obra.json5")
        obra = json.load(open(p))
        obra["stop"]["numerico"]["valor"] = 0.5
        json.dump(obra, open(p, "w"))
        rc, out, err = self.run_co("ev", "rodada_fechada")
        st = self.status()
        self.assertNotEqual(st["obra"]["portao"], "entrega",
                            "rc %d: %s ⇒ critério de parada do founder (>= 1.0, medido 0.5) trocado por edição de "
                            "obra.json5 depois de premissas_ok" % (rc, out.strip().splitlines()[0] if out else err))

    def test_M2b_max_horas_reescrito_evita_escalar(self):
        """V4-8: `init --max-horas` do founder vive só em obra.json5 (não na gênese). Orçamento estourado ⇒ a
        máquina deve escalar ao founder; o orquestrador troca max_horas por null e a obra continua sozinha."""
        self.init("--max-horas", "0.0001")
        self.prefixo("FECHAR_RODADA")
        self._rodada_pronta()
        p = os.path.join(self.ws, "obra.json5")
        obra = json.load(open(p))
        obra["max_horas"] = None
        json.dump(obra, open(p, "w"))
        rc, out, err = self.run_co("ev", "rodada_fechada")
        st = self.status()
        self.assertEqual((st["obra"]["estado"], st["obra"]["portao"]), ("AGUARDANDO_HUMANO", "escalar"),
                         "rc %d: %s" % (rc, (out or err).strip().splitlines()[0]))

    # ------------------------------------------------------------------ V5-M3 (média): aceite de task autodeclarado
    def test_M3_task_aceita_com_verificador_e_testes_autodeclarados(self):
        """verificacao_ok = diff_no_territorio and testes_vermelho_verde and verificador_nao_autor. Sem nenhum
        verificador despachado, o nome vem do payload do próprio orquestrador ("ninguem"), e o vermelho→verde vem do
        relatório redigido pelo construtor (nenhum teste roda). A task vai a ACEITA."""
        self.init()
        self.prefixo("LOTE")
        rc, out, err = self.in_proc(r'''
import co_estado as E, json, os
ws = %r
pl = {"schema_version": 1, "rodada": 1, "decisoes": [], "contrato": {}, "parada": "x",
      "tasks": [{"id": "T-01", "titulo": "t", "writes": ["src/**"], "deps": [], "cenarios": ["C-01"],
                 "construtor": "builder-A", "criterio": "c"}]}
json.dump(pl, open(E.paths(ws)["plano"], "w"))
rel = os.path.join(ws, "rodadas", "1", "relatorios", "T-01-1.json"); os.makedirs(os.path.dirname(rel))
json.dump({"task": "T-01", "chave": "o/1/T-01/1", "agent_type": "builder-A", "resultado": "concluido",
           "files_changed": [], "testes": [{"cmd": "true", "cenario": "C-01", "exit_antes": 1, "exit_depois": 0}],
           "checks_run": [], "evidencia_nivel": "E0", "contornos_manuais": [], "riscos": [], "handoff": "",
           "base_sha": None, "diff_hash": None}, open(rel, "w"))
gr = os.path.join(ws, "gate-report.json")
json.dump({"only": ["G3"], "itens": [{"id": "G3", "status": "PASS"}]}, open(gr, "w"))
regs = E.ler_ledger(ws)
ch = "o/1/T-01/1"
esp = [dict(evento="task.pronta", ator="script", nivel="task", de="PENDENTE", para="PRONTA", task="T-01"),
       dict(evento="despachada", payload={"task": "T-01", "papel": "construtor", "chave": ch, "agent_type": "builder-A",
            "writes": ["src/**"], "reads": [], "tentativa": 1}, chave=ch),
       dict(evento="task.despachar", ator="orquestrador", nivel="task", de="PRONTA", para="EM_VOO", task="T-01", chave=ch),
       dict(evento="retornou", payload={"task": "T-01", "chave": ch, "relatorio": rel,
            "relatorio_hash": E.sha_file(rel)}, chave=ch),
       dict(evento="task.retornar", ator="orquestrador", nivel="task", de="EM_VOO", para="RETORNADA", task="T-01", chave=ch),
       dict(evento="portao_relatorio", payload={"gate_report_hash": E.sha_file(gr), "veredito": "NO-GO", "final": False})]
novos = E._encadear(regs[-1], esp)
E.fold_registros(regs + novos)
with E.trava_ledger(ws):
    E._gravar_registros(ws, novos); E.pos_gravacao(ws)
print("ok")
''' % self.ws)
        self.assertEqual(rc, 0, out + err)
        f = os.path.join(self.root, "p.json")
        json.dump({"task": "T-01", "verificador": "ninguem-despachado"}, open(f, "w"))
        rc, out, err = self.run_co("ev", "task.verificada", "--payload", f)
        st = self.status()
        self.assertNotEqual(st["tasks"]["T-01"]["estado"], "ACEITA",
                            "rc %d: %s ⇒ aceite sem verificador registrado e sem teste executado" % (rc, out.strip()))

    # ------------------------------------------------------------------ controles (devem PASSAR: provam a causa)
    def test_controle_M2_sem_edicao_continua(self):
        self.init()
        self.prefixo("FECHAR_RODADA")
        self._rodada_pronta()
        rc, out, err = self.run_co("ev", "rodada_fechada")
        self.assertEqual(self.status()["obra"]["estado"], "CORRIGIR", out + err)

    def test_controle_M2b_sem_edicao_escala(self):
        self.init("--max-horas", "0.0001")
        self.prefixo("FECHAR_RODADA")
        self._rodada_pronta()
        rc, out, err = self.run_co("ev", "rodada_fechada")
        st = self.status()
        self.assertEqual((st["obra"]["estado"], st["obra"]["portao"]), ("AGUARDANDO_HUMANO", "escalar"), out + err)

    def test_controle_A1_aprovar_pela_cli_e_bloqueado(self):
        self.init()
        rc, err = self.hook_bash("python3 %s --work %s aprovar stop --decisao aprovado" % (self.co, self.ws),
                                 cwd=self.root, agent_type="builder-A")
        self.assertEqual(rc, 2, err)

    # ------------------------------------------------------------------ V5-A2 (alta): brace expansion > 256
    def test_A2_brace_acima_de_256_apaga_ledger(self):
        """R4-1 declara brace expansion coberta, mas _brace corta em 256 resultados: com o protegido depois de 256
        alternativas o hook PERMITE e o `rm -rf` real apaga .construcao/ (ledger)."""
        self.init()
        dummies = ",".join("a%d" % i for i in range(300))
        cmd = "rm -rf %s/{%s,.construcao}" % (self.ws, dummies)
        rc_hook, err = self.hook_bash(cmd, cwd=self.root)  # agente principal (o contrato bloqueia inclusive ele)
        if rc_hook == 0:
            subprocess.run(["bash", "-c", cmd], cwd=self.root, timeout=60)
        existe = os.path.isfile(os.path.join(self.ws, ".construcao", "ledger.jsonl"))
        self.assertFalse(rc_hook == 0 and not existe, "hook exit %d e ledger %s" % (
            rc_hook, "presente" if existe else "APAGADO"))


if __name__ == "__main__":
    unittest.main()
