"""HELD-OUT da rodada 2 / G5 (onda 1) — oráculo O1. Variações de bypass/segurança dos mutantes sobreviventes:
H22 (destruir o ws por outra rota), H18 (escrita por código embutido), H14 (xargs que monta o subcomando),
E17 (aprovação não adjacente à transição humana). Não visível ao construtor."""
import os
import sys
import unittest

VIS = os.path.realpath(os.path.expanduser("~/.claude/skills/construcao-orquestrada/tests/onda1"))
sys.path.insert(0, VIS)
from _comum import CO, HookBase, bash, sub  # noqa: E402
from test_a_estado import EstadoBase  # noqa: E402


class HeldoutR2bHook(HookBase):
    def test_H22_destruir_ws_por_outras_rotas(self):
        for c in ["python3 -c \"import shutil; shutil.rmtree('%s')\"" % self.ws, "rm -r -f %s/" % self.ws,
                  "cd %s && rm -rf ." % self.ws]:
            with self.subTest(cmd=c):
                self.assertBloqueia(sub(bash(c)))

    def test_H18_escrita_por_codigo_embutido_variacoes(self):
        ap = os.path.join(self.ws, "aprovacoes", "stop-7.json")
        for c in ["python3 -c \"import pathlib; pathlib.Path('%s').write_text('{}')\"" % ap,
                  "python3 -c \"import json; json.dump({}, open('%s', 'w'))\"" % ap]:
            with self.subTest(cmd=c):
                self.assertBloqueia(sub(bash(c)))

    def test_H14_xargs_montando_o_subcomando(self):
        self.assertBloqueia(sub(bash("echo aprovar entrega | xargs -n2 python3 %s --work %s" % (CO, self.ws))))


class HeldoutR2bFold(EstadoBase):
    def test_E17_aprovacao_nao_adjacente(self):
        L = self.init()
        L.ate_ah_stop()
        L.append("aprovacao", payload={"portao": "stop", "decisao": "aprovado", "arquivo": "/x",
                                       "hash_estado": "1" * 64, "usuario_so": "t", "ttyname": "/dev/ttys0"})
        L.append("nota", payload={"texto": "entre a aprovação e a transição"})
        L.t("aprovado", "AGUARDANDO_HUMANO", "ORACULO", "humano")
        self.assertEqual(self.co("status", "--json")[0], 1)


if __name__ == "__main__":
    unittest.main()
