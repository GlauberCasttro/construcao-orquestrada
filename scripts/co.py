#!/usr/bin/env python3
"""co.py — CLI única da construcao-orquestrada (frente A, onda 1). Python 3.9+, só stdlib.

O parser é GERADO da tabela `cli.subcomandos` de references/contrato.json5 (nomes à letra: flags, ações,
posicionais, escolhas e padrões). co.py é o ÚNICO dispatcher:
  co_estado  init, ev, status, load, maquina, pontos, retomar, aprovar, oraculo mudar|manifest
             (handlers co_estado.cmd_*(args) -> int)
  co_hook    hook  — co_hook.cmd_hook(Namespace) (ou co_hook.main([acao, --vivo, --work ws]))
  co_portao  diff, portao, veredito — co_portao.main(argv) com argv = sys.argv[1:] (inclui --work <ws>)
  co_medir   medir, comparar, oraculo vacuo|forca — onda 2 (ausente ⇒ "pendente: <sub>", exit 2)
  co (aqui)  plano, lote, colisao, trava, reabrir — frente E, onda 2 ⇒ "pendente: <sub>", exit 2
Import lazy: módulo de outra frente ausente ⇒ exit 2 com mensagem clara (sem traceback).

Exit: 0 passa/GO/transição aplicada · 1 reprova/NO-GO/guarda falsa · 2 entrada inválida, ferramenta ausente ou
subcomando pendente (falha fechada).
"""
import argparse
import importlib
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)

OBRIGATORIAS = {("init", "--alvo"), ("init", "--tipo"), ("init", "--pedido"), ("init", "--stop"),
                ("aprovar", "--decisao"), ("reabrir", "--motivo")}
PENDENTES_ONDA2 = {"plano", "lote", "colisao", "trava", "reabrir", "medir", "comparar"}


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write("%s: erro: %s\n" % (self.prog, message))
        raise SystemExit(2)


def _contrato():
    import co_estado
    return co_estado.carregar_contrato()


def _add_flag(sp, sub, spec):
    partes = spec.split(None, 1)
    nome = partes[0]
    resto = partes[1] if len(partes) > 1 else ""
    kw = {"help": resto or None}
    if (sub, nome) in OBRIGATORIAS:
        kw["required"] = True
    m = re.match(r"^\{(.+)\}$", resto)
    if not resto:
        kw["action"] = "store_true"
    elif m:
        kw["choices"] = [x.strip() for x in m.group(1).split(",")]
        kw["metavar"] = "{%s}" % m.group(1)
    else:
        mt = re.match(r"^(INT|FLOAT)(?:=(.+))?$", resto)
        if mt:
            kw["type"] = int if mt.group(1) == "INT" else float
            if mt.group(2) is not None:
                kw["default"] = kw["type"](mt.group(2))
        kw["metavar"] = resto.split("=")[0]
    sp.add_argument(nome, **kw)


def _add_pos(sp, spec, opcional=False):
    nome, _, padrao = spec.partition("=")
    kw = {}
    m = re.match(r"^\{(.+)\}$", padrao or "")
    if m:
        kw["choices"] = [x.strip() for x in m.group(1).split(",")]
    elif padrao:
        kw["nargs"] = "?"
        kw["default"] = padrao
    if opcional:
        kw["nargs"] = "?"
    sp.add_argument(nome, **kw)


def build_parser():
    cli = _contrato()["cli"]
    p = _Parser(prog=cli.get("prog", "co.py"),
                description="construcao-orquestrada — CLI única (gerada de references/contrato.json5#cli)")
    for fg in cli.get("flags_globais", []):
        p.add_argument(fg["flag"], required=bool(fg.get("obrigatoria")), help=fg.get("help"))
    subs = p.add_subparsers(dest="sub", metavar="{%s}" % ",".join(cli["subcomandos"].keys()))
    subs.required = True
    for nome, spec in cli["subcomandos"].items():
        sp = subs.add_parser(nome, help="%s — %s" % (spec.get("handler", ""), spec.get("negativo", "")),
                             description="handler: %s. negativo: %s" % (spec.get("handler"), spec.get("negativo")))
        acoes = [a for a in spec.get("acoes", []) if not a.startswith("(")]
        if acoes:
            stdin_ok = any(a.startswith("(") for a in spec.get("acoes", []))
            sp.add_argument("acao", choices=acoes, nargs="?" if stdin_ok else None,
                            help="ação: %s%s" % (", ".join(acoes), " (sem ação: payload no stdin)" if stdin_ok else ""))
        for pos in spec.get("pos", []):
            _add_pos(sp, pos)
        for pos in spec.get("pos_opcional", []):
            _add_pos(sp, pos, opcional=True)
        for fl in spec.get("flags", []):
            _add_flag(sp, nome, fl)
    return p


def _modulo(nome, sub):
    try:
        return importlib.import_module(nome)
    except ImportError as e:
        if getattr(e, "name", None) == nome:
            sys.stderr.write("erro: módulo %s.py ausente em %s — subcomando `%s` indisponível nesta instalação\n"
                             % (nome, AQUI, sub))
            return None
        raise


def _pendente(sub):
    sys.stderr.write("pendente: %s\n" % sub)
    return 2


def cmd_plano(args):
    return _pendente("plano")


def cmd_lote(args):
    return _pendente("lote")


def cmd_colisao(args):
    return _pendente("colisao")


def cmd_trava(args):
    return _pendente("trava")


def cmd_reabrir(args):
    return _pendente("reabrir")


def _despachar(args, argv):
    sub = args.sub
    if sub in ("hook",):
        m = _modulo("co_hook", sub)
        if m is None:
            return 2
        if hasattr(m, "cmd_hook"):
            return m.cmd_hook(args)
        lst = ([args.acao] if args.acao else []) + (["--vivo"] if getattr(args, "vivo", False) else [])
        return m.main(lst + ["--work", args.work])
    if sub in ("diff", "portao", "veredito"):
        m = _modulo("co_portao", sub)
        return 2 if m is None else m.main(list(argv))
    if sub in ("medir", "comparar") or (sub == "oraculo" and args.acao in ("vacuo", "forca")):
        try:
            m = importlib.import_module("co_medir")
        except ImportError:
            return _pendente(sub)
        fn = getattr(m, {"medir": "cmd_medir", "comparar": "cmd_comparar"}.get(sub, "cmd_oraculo"), None)
        return _pendente(sub) if fn is None else fn(args)
    local = {"plano": cmd_plano, "lote": cmd_lote, "colisao": cmd_colisao, "trava": cmd_trava,
             "reabrir": cmd_reabrir}
    if sub in local:
        return local[sub](args)
    import co_estado
    if sub == "oraculo":
        return co_estado.cmd_oraculo_mudar(args) if args.acao == "mudar" else co_estado.cmd_oraculo_manifest(args)
    tabela = {"init": co_estado.cmd_init, "ev": co_estado.cmd_ev, "status": co_estado.cmd_status,
              "load": co_estado.cmd_load, "maquina": co_estado.cmd_maquina, "pontos": co_estado.cmd_pontos,
              "retomar": co_estado.cmd_retomar, "aprovar": co_estado.cmd_aprovar}
    return tabela[sub](args)


def _rc(v):
    """Código de saída normalizado: int (não bool) passa; None ⇒ 2; qualquer outra coisa ⇒ 2 (falha fechada)."""
    if v is None or isinstance(v, bool) or not isinstance(v, int):
        return 2
    return v


def main(argv=None):
    """Nunca devolve 0 por erro interno: toda exceção não prevista ⇒ 2."""
    try:
        return _main(argv)
    except SystemExit as e:
        # SystemExit que escapou de _main é inesperado: nunca vira 0
        return e.code if isinstance(e.code, int) and not isinstance(e.code, bool) and e.code != 0 else 2
    except KeyboardInterrupt:
        sys.stderr.write("interrompido; nada gravado além do que o ledger mostra\n")
        return 2
    except BaseException as e:  # noqa: BLE001 — falha fechada, sem traceback
        try:
            sys.stderr.write("erro interno (%s): %s\n" % (type(e).__name__, e))
        except Exception:  # noqa: BLE001
            pass
        return 2


def _main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        import co_estado
    except ImportError as e:
        sys.stderr.write("erro: co_estado.py indisponível (%s)\n" % e)
        return 2
    try:
        parser = build_parser()
    except co_estado.Bad as e:
        sys.stderr.write("erro: %s\n" % e)
        return 2
    except Exception as e:  # noqa: BLE001 — contrato ilegível etc.
        sys.stderr.write("erro interno ao montar a CLI (%s): %s\n" % (type(e).__name__, e))
        return 2
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code in (0, None) else 2
    try:
        rc = _despachar(args, argv)
    except co_estado.Fail as e:
        sys.stderr.write("NÃO: %s\n" % e)
        return 1
    except co_estado.Bad as e:
        sys.stderr.write("erro: %s\n" % e)
        return 2
    except SystemExit as e:
        # handler que chama sys.exit: só int explícito vale; None/str/bool ⇒ 2 (falha fechada)
        rc = e.code if isinstance(e.code, int) and not isinstance(e.code, bool) else 2
    except KeyboardInterrupt:
        sys.stderr.write("interrompido; nada gravado além do que o ledger mostra\n")
        return 2
    except Exception as e:  # noqa: BLE001 — falha fechada, sem traceback
        sys.stderr.write("erro interno (%s): %s\n" % (type(e).__name__, e))
        return 2
    return _rc(rc)


if __name__ == "__main__":
    sys.exit(main())
