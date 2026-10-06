"""Q1/Q4 — integridade do estado e máquina. O prefixo do ledger é montado com a API do motor
(co_estado._encadear, transições válidas da maquina.json5, fold aceita) só para chegar ao estado em que o defeito
aparece; o passo testado é sempre o comando público `co.py ...`."""
import json
import os
import unittest

from _base import Base

PREFIXO_FECHAR_RODADA = r'''
import co_estado as E, json, os
ws = %(ws)r
regs = E.ler_ledger(ws)
def t(ev, de, para, ator, payload=None):
    return dict(evento=ev, ator=ator, nivel="obra", de=de, para=para, payload=payload or {})
def op(ev, payload):
    return dict(evento=ev, payload=payload)
def ap(portao):
    return [op("aprovacao", {"portao": portao, "decisao": "aprovado"}),
            t("aprovado", "AGUARDANDO_HUMANO", None, "humano")]
esp = [t("iniciar", "INICIO", "PREMISSAS", "script"),
       t("premissas_ok", "PREMISSAS", "AGUARDANDO_HUMANO", "orquestrador")]
a = ap("stop"); a[1]["para"] = "ORACULO"; esp += a
esp += [t("oraculo_pronto", "ORACULO", "AGUARDANDO_HUMANO", "orquestrador")]
a = ap("oraculo"); a[1]["para"] = "BASELINE"; esp += a
esp += [t("dispensado", "BASELINE", "PLANO", "orquestrador", {"motivo": "cli"}),
        t("plano_ok", "PLANO", "LOTE", "orquestrador"),
        t("fronteira_vazia", "LOTE", "INTEGRAR", "script"),
        t("merge_ok", "INTEGRAR", "VERIFICAR", "script"),
        t("verde", "VERIFICAR", "MEDIR", "script"),
        op("medicao_registrada", {"config": "sistema", "k": 3, "final": True, "run_ids": [], "pass_at_k": 0.5,
                                  "pass_hat_k": 0.5, "simulated": False, "rotulo": "final"}),
        t("medido", "MEDIR", "FECHAR_RODADA", "script")]
for _ in range(%(voltas)d):
    esp += [t("rodada_fechada", "FECHAR_RODADA", "CORRIGIR", "script", {"saida": "continuar"}),
            t("campanhas_abertas", "CORRIGIR", "LOTE", "orquestrador"),
            t("fronteira_vazia", "LOTE", "INTEGRAR", "script"),
            t("merge_ok", "INTEGRAR", "VERIFICAR", "script"),
            t("verde", "VERIFICAR", "MEDIR", "script"),
            t("medido", "MEDIR", "FECHAR_RODADA", "script")]
novos = E._encadear(regs[-1], esp)
E.fold_registros(regs + novos)
with E.trava_ledger(ws):
    E._gravar_registros(ws, novos)
    E.pos_gravacao(ws)
for n in range(1, %(ncomp)d + 1):
    d = os.path.join(ws, "rodadas", str(n)); os.makedirs(d, exist_ok=True)
    json.dump({"Q": {"delta": %(delta)r, "rotulo": %(rotulo)r}}, open(os.path.join(d, "comparacao.json"), "w"))
st = E.fold(ws)
print(st["obra"], st["contadores"])
'''


class Estado(Base):
    def _status(self):
        rc, out, err = self.run_co("status", "--json")
        self.assertEqual(rc, 0, err)
        return json.loads(out)

    def _fechar_rodada(self, voltas=0, ncomp=2, delta=0.0, rotulo="sem efeito"):
        rc, out, err = self.in_proc(PREFIXO_FECHAR_RODADA % {"ws": self.ws, "voltas": voltas, "ncomp": ncomp,
                                                             "delta": delta, "rotulo": rotulo})
        self.assertEqual(rc, 0, out + err)
        self.assertIn("FECHAR_RODADA", out)

    def test_controle_escalar_sem_payload(self):
        self.init()
        self._fechar_rodada()
        rc, out, err = self.run_co("ev", "rodada_fechada")
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(self._status()["obra"]["portao"], "escalar")

    def test_payload_transicao_abre_portao_entrega(self):
        """O motor escolhe `escalar` (critério de parada falso, platô) mas `--payload {"transicao":"parar"}` faz o
        fold dobrar o registro como `parar` ⇒ portão `entrega` aberto por uma escalada (co_estado.py:710)."""
        self.init()
        self._fechar_rodada()
        f = os.path.join(self.root, "p.json")
        with open(f, "w") as fh:
            json.dump({"transicao": "parar"}, fh)
        rc, out, err = self.run_co("ev", "rodada_fechada", "--payload", f)
        st = self._status()
        self.assertEqual(st["obra"]["portao"], "escalar",
                         "co.py saiu %d (%s) e o fold abriu portão %r; payload gravado tem saida=escalar"
                         % (rc, out.strip().splitlines()[0] if out.strip() else err.strip(), st["obra"]["portao"]))


    def test_max_rodadas_do_founder_ignorado(self):
        """`init --max-rodadas 1` grava obra.max_rodadas=1, mas a guarda usa a constante MAX_RODADAS=3 da máquina:
        com rodada=1 e sem platô, a obra continua (CORRIGIR) em vez de escalar ao founder."""
        rc, out, err = self.run_co("init", "--alvo", self.alvo, "--tipo", "cli", "--pedido", "x", "--stop",
                                   "pass_hat_3 >= 1.0", "--max-rodadas", "1")
        self.assertEqual(rc, 0, out + err)
        self._fechar_rodada(voltas=1, ncomp=1, delta=0.1, rotulo="indício")
        rc, out, err = self.run_co("ev", "rodada_fechada")
        st = self._status()
        self.assertEqual((st["obra"]["estado"], st["obra"]["portao"]), ("AGUARDANDO_HUMANO", "escalar"),
                         "rodada 1 -> %s com --max-rodadas 1: %s" % (st["contadores"]["rodada"], out.strip()))


    def test_aprovar_falha_apos_audit_trava_obra(self):
        """cmd_aprovar grava a linha `aprovacao` no audit ANTES do arquivo e do ledger (co_estado.py:3469-3481).
        Se a escrita do arquivo falha (aprovacoes/ sem permissão), o audit fica com um seq que o ledger nunca terá
        e TODO comando seguinte reprova (problemas_fim_do_ledger) — "nada gravado em toda recusa" violado e obra
        travada sem caminho de recuperação. (tty simulado só para chegar à escrita; não é o vetor.)"""
        self.init()
        rc, out, err = self.in_proc(r'''
import co_estado as E, argparse, os
ws = %r
regs = E.ler_ledger(ws)
esp = [dict(evento="iniciar", ator="script", nivel="obra", de="INICIO", para="PREMISSAS", payload={}),
       dict(evento="premissas_ok", ator="orquestrador", nivel="obra", de="PREMISSAS", para="AGUARDANDO_HUMANO",
            payload={})]
novos = E._encadear(regs[-1], esp)
with E.trava_ledger(ws):
    E._gravar_registros(ws, novos); E.pos_gravacao(ws)
os.chmod(os.path.join(ws, "aprovacoes"), 0o500)
E._stdin_tty = lambda: True
E.human_channel = lambda what: "/dev/ttys999"
try:
    E.cmd_aprovar(argparse.Namespace(work=ws, portao="stop", decisao="aprovado", nota=None))
    print("APROVOU")
except BaseException as e:
    print("RECUSOU", type(e).__name__)
''' % self.ws)
        os.chmod(os.path.join(self.ws, "aprovacoes"), 0o700)
        self.assertIn("RECUSOU", out, out + err)
        aud = os.path.join(self.home, ".claude", "construcao-orquestrada", "audit.jsonl")
        linhas = open(aud).read().splitlines() if os.path.isfile(aud) else []
        rc, out, err = self.run_co("status")
        self.assertEqual((rc, [l for l in linhas if '"aprovacao"' in l]), (0, []),
                         "após recusa: status exit %d (%s)" % (rc, err.strip()[:160]))


if __name__ == "__main__":
    unittest.main()
