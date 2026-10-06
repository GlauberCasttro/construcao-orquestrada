"""Definição dos mutantes M3 (onda 1, rodada 3). Cada mutante: substituição exata (old -> new) num arquivo.
`n` = número de ocorrências esperadas de `old` (padrão 1; todas são trocadas). Parte A = próprios; parte B =
reaplicação dos 10 ocultos de mutantes-ocultos-r2.json (adaptados ao código atual)."""

RC = "retorno_constante"
FR = "feature_removida"
CI = "condicao_invertida"
LD = "limite_deslocado"
PT = "precedencia_trocada"
HC = "campo_omitido_do_hash"
LK = "lock_removido"
G1T = "g1_texto_impresso"
CS = "normalizacao_caixa_desligada"
HD = "hash_disco_trocado_por_payload"

A = []


def m(id_, arq, tipo, desc, old, new, n=1, parte="A"):
    A.append(dict(id=id_, parte=parte, arquivo=arq, tipo=tipo, descricao=desc, old=old, new=new, n=n))


CO, ES, HK, PO = "co.py", "co_estado.py", "co_hook.py", "co_portao.py"

# ============================================================ co.py
m("C01", CO, RC, "_rc devolve 0 sempre (código de saída constante)",
  '    if v is None or isinstance(v, bool) or not isinstance(v, int):\n        return 2\n    return v\n',
  '    return 0\n')
m("C02", CO, RC, "_main: erro do argparse sai 0",
  '        args = parser.parse_args(argv)\n    except SystemExit as e:\n        return 0 if e.code in (0, None) else 2',
  '        args = parser.parse_args(argv)\n    except SystemExit as e:\n        return 0')
m("C03", CO, CI, "_main: Fail (guarda falsa/reprova) sai 0 em vez de 1",
  '        sys.stderr.write("NÃO: %s\\n" % e)\n        return 1',
  '        sys.stderr.write("NÃO: %s\\n" % e)\n        return 0')
m("C04", CO, FR, "_despachar: veredito deixa de ir para co_portao",
  'if sub in ("diff", "portao", "veredito"):', 'if sub in ("diff", "portao"):')
m("C05", CO, RC, "main: exceção inesperada sai 0",
  '            pass\n        return 2\n\n\ndef _main', '            pass\n        return 0\n\n\ndef _main')

# ============================================================ co_estado.py — retorno constante
m("E-RC01", ES, RC, "problemas_cadeia devolve [] (cadeia sempre ok)",
  '    """formatos.ledger.hash.verificar_cadeia. Lista vazia = cadeia íntegra."""\n',
  '    """formatos.ledger.hash.verificar_cadeia. Lista vazia = cadeia íntegra."""\n    return []\n')
m("E-RC02", ES, RC, "verificar_cadeia devolve True",
  '    try:\n        return not problemas_cadeia(ler_ledger(ws))', '    try:\n        return True')
m("E-RC03", ES, RC, "relatorio_satisfaz_entrega devolve (True, ok) sempre",
  '    if not isinstance(rep, dict):\n        return False, "gate-report ausente ou ilegível"',
  '    return True, "ok"\n    if not isinstance(rep, dict):\n        return False, "gate-report ausente ou ilegível"')
m("E-RC04", ES, RC, "avaliar_guarda devolve True (gate passa)",
  '    valores = ctx.get("valores", ctx) if isinstance(ctx, dict) else {}\n',
  '    return True\n')
m("E-RC05", ES, RC, "_a_veredito_go_final devolve True (veredito GO)",
  'def _a_veredito_go_final(c):\n', 'def _a_veredito_go_final(c):\n    return True\n')
m("E-RC06", ES, RC, "_a_regressao_go devolve True",
  'def _a_regressao_go(c):\n', 'def _a_regressao_go(c):\n    return True\n')
m("E-RC07", ES, RC, "problemas_fim_do_ledger devolve [] (A8 desligado)",
  '    mesmo portão. Lista vazia = ok."""\n', '    mesmo portão. Lista vazia = ok."""\n    return []\n')
m("E-RC08", ES, RC, "aprovacoes_sem_audit (co_estado) devolve []",
  '    linhas = [x for x in _audit_linhas() if isinstance(x, dict)]\n',
  '    return []\n')
m("E-RC09", ES, RC, "_a_hook_vivo devolve True",
  'def _a_hook_vivo(c):\n', 'def _a_hook_vivo(c):\n    return True\n')
m("E-RC10", ES, RC, "hook_vivo_no_audit devolve True",
  '    """Linha tool_call BLOQUEADA citando `aprovar __selftest__`, com ts ≥ gênese (ESPEC 4)."""\n',
  '    """Linha tool_call BLOQUEADA citando `aprovar __selftest__`, com ts ≥ gênese (ESPEC 4)."""\n    return True\n')
m("E-RC11", ES, RC, "checar_maquina: ok constante, sem violações",
  '    return {"ok": not viol, "violacoes": viol, "info": info}',
  '    return {"ok": True, "violacoes": [], "info": info}')
m("E-RC12", ES, RC, "human_channel devolve tty sem desafio",
  '    (espaços ignorados). Nenhuma variável de ambiente dispensa. Sem tty ⇒ Bad; desafio errado ⇒ Fail."""\n',
  '    (espaços ignorados). Nenhuma variável de ambiente dispensa. Sem tty ⇒ Bad; desafio errado ⇒ Fail."""\n'
  '    return "/dev/tty"\n')
m("E-RC13", ES, RC, "conferir_ledger não confere nada (no-op)",
  '    """Cadeia íntegra + fim não truncado (A8). Fail com a lista de problemas; nada é gravado."""\n',
  '    """Cadeia íntegra + fim não truncado (A8). Fail com a lista de problemas; nada é gravado."""\n    return\n')
m("E-RC14", ES, RC, "_a_pass3_final devolve True",
  'def _a_pass3_final(c):\n', 'def _a_pass3_final(c):\n    return True\n')
m("E-RC15", ES, RC, "_a_ws_fora devolve True",
  'def _a_ws_fora(c):\n', 'def _a_ws_fora(c):\n    return True\n')
m("E-RC16", ES, RC, "_a_pontos_completos devolve True",
  'def _a_pontos_completos(c):\n', 'def _a_pontos_completos(c):\n    return True\n')
m("E-RC17", ES, RC, "_a_retomar_md_valido devolve True",
  'def _a_retomar_md_valido(c):\n', 'def _a_retomar_md_valido(c):\n    return True\n')
m("E-RC18", ES, RC, "_a_limite devolve True",
  'def _a_limite(c):\n', 'def _a_limite(c):\n    return True\n')
m("E-RC19", ES, RC, "_stdin_tty devolve True",
  'def _stdin_tty():\n', 'def _stdin_tty():\n    return True\n')
m("E-RC20", ES, HD, "hashes_do_disco devolve o payload intacto (hash do agente vale)",
  '    p = paths(ws)\n    if evento == "premissas_ok":\n        campos',
  '    return payload\n    p = paths(ws)\n    if evento == "premissas_ok":\n        campos')
m("E-RC21", ES, RC, "_a_stop_numerico devolve True",
  'def _a_stop_numerico(c):\n', 'def _a_stop_numerico(c):\n    return True\n')

# ============================================================ co_estado.py — demais
m("E01", ES, FR, "problemas_cadeia não confere seq (lacuna/reordenação)",
  '        if r["seq"] != i:\n', '        if False:\n')
m("E02", ES, FR, "problemas_cadeia não confere prev",
  '        if r["prev"] != prev:\n', '        if False:\n')
m("E03", ES, FR, "problemas_cadeia não confere payload_hash",
  '        if not isinstance(r["payload"], dict) or sha_obj(r["payload"]) != r["payload_hash"]:\n',
  '        if not isinstance(r["payload"], dict):\n')
m("E04", ES, FR, "problemas_cadeia não exige gênese no seq 1",
  '    if registros and registros[0].get("evento") != "genese":\n', '    if False:\n')
m("E05", ES, HC, "hash_registro omite o campo `ator`",
  '    sem = {k: v for k, v in rec.items() if k != "hash"}', '    sem = {k: v for k, v in rec.items() if k not in ("hash", "ator")}')
m("E06", ES, HC, "hash_registro omite o campo `payload_hash`",
  '    sem = {k: v for k, v in rec.items() if k != "hash"}',
  '    sem = {k: v for k, v in rec.items() if k not in ("hash", "payload_hash")}')
m("E07", ES, HC, "hash_estado omite `oraculo`",
  'CHAVES_HASH_ESTADO = ["obra", "contadores", "constantes", "teto_vigente", "tasks", "campanhas", "contrato_hash",\n                      "oraculo"]',
  'CHAVES_HASH_ESTADO = ["obra", "contadores", "constantes", "teto_vigente", "tasks", "campanhas", "contrato_hash"]')
m("E08", ES, HC, "hash_estado omite `contadores`",
  'CHAVES_HASH_ESTADO = ["obra", "contadores", "constantes",', 'CHAVES_HASH_ESTADO = ["obra", "constantes",')
m("E09", ES, LK, "transicionar sem trava_ledger",
  '    maq = carregar_maquina()\n    with trava_ledger(ws):\n        regs = ler_ledger(ws)\n        conferir_ledger(ws, regs)\n        st = fold_registros(regs, maq)\n        hashes_do_disco',
  '    maq = carregar_maquina()\n    with contextlib.nullcontext():\n        regs = ler_ledger(ws)\n        conferir_ledger(ws, regs)\n        st = fold_registros(regs, maq)\n        hashes_do_disco')
m("E10", ES, LK, "append_evento sem trava_ledger",
  '    """Grava UM registro (trava + confere a cadeia + fold coerente + pós-gravação). Retorna o seq."""\n    with trava_ledger(ws):',
  '    """Grava UM registro (trava + confere a cadeia + fold coerente + pós-gravação). Retorna o seq."""\n    with contextlib.nullcontext():')
m("E11", ES, FR, "transicionar não reconfere hash_estado do canal humano sob a trava (TOCTOU)",
  '        if _humano and _humano.get("hash_estado") and st["hash_estado"] != _humano["hash_estado"]:',
  '        if False:')
m("E12", ES, LD, "transicionar: não determinismo só com >2 guardas verdadeiras",
  '        if len(verdade) > 1:', '        if len(verdade) > 2:')
m("E13", ES, FR, "transicionar não confere ator humano x canal",
  '        if (t.get("actor") == "humano") != bool(_humano):', '        if False:')
m("E14", ES, FR, "transicionar ignora motivo_obrigatorio",
  '            if t.get("motivo_obrigatorio") and not str(payload.get("motivo") or "").strip():',
  '            if False:')
m("E15", ES, FR, "fold: transição humana sem aprovacao imediatamente antes é aceita",
  '        if not ap or ap.get("portao") != no[1] or ap.get("decisao") != ev:', '        if False:')
m("E16", ES, FR, "fold: operacional com ator/de/para incoerente aceito",
  '            if r.get("ator") != "script" or r.get("de") is not None or r.get("para") is not None:',
  '            if False:')
m("E17", ES, FR, "fold: `de` do registro não confere com estado dobrado",
  '    if r.get("de") != no[0]:\n', '    if False:\n')
m("E18", ES, CI, "_a_limite: retomar_apos inválido aceito (is not None → is None)",
  'parse_ts(c.payload.get("retomar_apos")) \\\n        is not None', 'parse_ts(c.payload.get("retomar_apos")) \\\n        is None')
m("E19", ES, LD, "lote_cabe_no_teto: < → <=",
  '    "lote_cabe_no_teto": lambda c: len(c.st["vivos"]) < c.st["teto_vigente"],',
  '    "lote_cabe_no_teto": lambda c: len(c.st["vivos"]) <= c.st["teto_vigente"],')
m("E20", ES, CI, "_a_agora_apos: >= → <",
  '    return datetime.datetime.now(datetime.timezone.utc) >= d', '    return datetime.datetime.now(datetime.timezone.utc) < d')
m("E21", ES, FR, "relatorio_satisfaz_entrega: relatório sem chave `only` aceito",
  '    if "only" not in rep or rep.get("only") not in (None,):', '    if rep.get("only") not in (None,):')
m("E22", ES, FR, "relatorio_satisfaz_entrega: não exige final",
  '    if rep.get("final") is not True:\n        return False, "relatório não final"', '    if False:\n        return False, "relatório não final"')
m("E23", ES, FR, "VEREDITOS_ENTREGA aceita GO (simulado)",
  'VEREDITOS_ENTREGA = ("GO", "GO (com waiver)")', 'VEREDITOS_ENTREGA = ("GO", "GO (com waiver)", "GO (simulado)")')
m("E24", ES, FR, "relatorio_satisfaz_entrega: run incompleto aceito",
  '    if faltam:\n        return False, "run incompleto', '    if False:\n        return False, "run incompleto')
m("E25", ES, FR, "GATES_NUCLEO sem G4",
  'GATES_NUCLEO = ("G0", "G1", "G3", "G4")', 'GATES_NUCLEO = ("G0", "G1", "G3")')
m("E26", ES, FR, "relatorio_satisfaz_entrega: item FAIL/ERRO aceito",
  '    if ruins:\n', '    if False:\n')
m("E27", ES, LD, "problemas_fim_do_ledger: seq do cache além do fim tolerado em 1",
  '        if isinstance(cs, int) and not isinstance(cs, bool) and cs > n:',
  '        if isinstance(cs, int) and not isinstance(cs, bool) and cs > n + 1:')
m("E28", ES, FR, "problemas_fim_do_ledger: cache ausente com ledger não vazio tolerado (R3-3)",
  '    if exigir_cache and n >= 1:', '    if False:')
m("E29", ES, FR, "problemas_fim_do_ledger: audit não é testemunha",
  '        if gen_ts and str(x.get("ts", "")) < gen_ts:\n            continue',
  '        if True:\n            continue')
m("E30", ES, FR, "aprovacoes_sem_audit (co_estado): tool_call que aprovou não suja",
  '        if not ok or tool:\n            sujas.append(ref)\n    return sujas\n\n\ndef _a_veredito_go_final',
  '        if not ok:\n            sujas.append(ref)\n    return sujas\n\n\ndef _a_veredito_go_final')
m("E31", ES, FR, "_a_veredito_go_final não cruza ledger x audit",
  '    if aprovacoes_sem_audit(c.ws, c.regs):\n        return False', '    if False:\n        return False')
m("E32", ES, FR, "cmd_ev aceita evento humano",
  '    if evento in eventos_humanos(maq):\n', '    if False:\n')
m("E33", ES, FR, "cmd_ev aceita qualquer operacional",
  '        if evento not in EVENTOS_VIA_EV:\n', '        if False:\n')
m("E34", ES, FR, "cmd_init aceita workspace dentro do alvo",
  '    if _dentro(w, alvo):\n', '    if False:\n')
m("E35", ES, LD, "cmd_init aceita --teto/--max-rodadas 0",
  '        if getattr(args, nome) is not None and getattr(args, nome) < 1:',
  '        if getattr(args, nome) is not None and getattr(args, nome) < 0:')
m("E36", ES, FR, "cmd_aprovar aceita audit dentro do workspace",
  '    if _dentro(aud, w):\n        raise Fail("audit', '    if False:\n        raise Fail("audit')
m("E37", ES, CI, "human_channel compara só o 1º dígito do desafio",
  '    if "".join(buf.decode("utf-8", "replace").split()) != ch:',
  '    if "".join(buf.decode("utf-8", "replace").split())[:1] != ch[:1]:')
m("E38", ES, FR, "congelar_oraculo nunca roda `oracle change` (hash diferente)",
  '        cmd = ["oracle", "change", "--why", motivo,', '        cmd = None and ["oracle", "change", "--why", motivo,')
m("E39", ES, FR, "preparar_congelamento não exige campanha-mãe",
  '    if not os.path.isfile(st_ac):\n        raise Fail', '    if False:\n        raise Fail')
m("E40", ES, CI, "avaliar_ast and: indeterminado vira True (Kleene quebrado)",
  '        return None if any(v is None for v in vs) else True\n', '        return True\n')
m("E41", ES, CI, "avaliar_guarda: indeterminado satisfaz (is True → is not False)",
  '    return avaliar_ast(parse_guarda(nome), lambda n: valores.get(n)) is True',
  '    return avaliar_ast(parse_guarda(nome), lambda n: valores.get(n)) is not False')
m("E42", ES, PT, "parse_guarda: `and` passa a ligar mais fraco que `or`",
  '        while peek() == ("id", "or"):', '        while peek() == ("id", "and"):')
m("E43", ES, PT, "avaliar_ast or: indeterminado tem precedência sobre True",
  '        if any(v is True for v in vs):\n            return True\n        return None if any(v is None for v in vs) else False',
  '        if any(v is None for v in vs):\n            return None\n        return True if any(v is True for v in vs) else False')
m("E44", ES, FR, "cmd_oraculo_manifest aceita autor = construtor (D5)",
  '        if cons and cons in f["autores"]:', '        if False:')
m("E45", ES, FR, "cmd_oraculo_manifest fora de ORACULO",
  '        if st["obra"]["estado"] != "ORACULO":', '        if False:')
m("E46", ES, FR, "cmd_pontos não acusa ponto duplicado",
  '        if pid in vistos:\n', '        if False:\n')
m("E47", ES, FR, "problemas_cadeia não confere formato de ts",
  '        if not TS_RE.match(str(r["ts"])):\n', '        if False:\n')
m("E48", ES, FR, "gerar_aprovar_sh grava com modo 0o755",
  '    escrever_atomico(path, "\\n".join(linhas) + "\\n", modo=0o600)', '    escrever_atomico(path, "\\n".join(linhas) + "\\n", modo=0o755)')
m("E49", ES, CI, "_a_todas_ret aceita task EM_VOO",
  '("RETORNADA", "ACEITA", "DESCARTADA")', '("RETORNADA", "ACEITA", "DESCARTADA", "EM_VOO")')
m("E50", ES, FR, "cmd_load sem limite load_max_chars",
  '    if len(txt) > limite:\n', '    if False:\n')

# ============================================================ co_hook.py — retorno constante
m("H-RC01", HK, RC, "classificar: hook permite sempre",
  '    why, meta = _analisar(payload)\n    _ULTIMA = meta\n',
  '    why, meta = None, {"tokens": [], "toca": False, "alvo": ""}\n    _ULTIMA = meta\n')
m("H-RC02", HK, RC, "check_aprovacao devolve (None, [])",
  '    """(motivo, tokens) se o comando executa aprovação humana; senão (None, [])."""\n',
  '    """(motivo, tokens) se o comando executa aprovação humana; senão (None, [])."""\n    return None, []\n')
m("H-RC03", HK, RC, "_decide_leitura devolve None",
  '    """itens = [(path, marca)]. Bloqueia leitura/listagem do held-out por construtor."""\n',
  '    """itens = [(path, marca)]. Bloqueia leitura/listagem do held-out por construtor."""\n    return None\n')
m("H-RC04", HK, RC, "_decide_escrita devolve None",
  'def _decide_escrita(paths, sub, agent_type, destrutivo=False):\n',
  'def _decide_escrita(paths, sub, agent_type, destrutivo=False):\n    return None\n')
m("H-RC05", HK, CS, "_k identidade (normalização de caixa/NFC desligada)",
  '    if not isinstance(p, str):\n        return p\n    return unicodedata.normalize("NFC", unicodedata.normalize("NFC", p).casefold())',
  '    return p')
m("H-RC06", HK, RC, "run_raw: payload inválido nunca falha fechado",
  '        if RAW_FAILCLOSED_RE.search(raw or ""):\n            motivo = "erro ao analisar',
  '        if False:\n            motivo = "erro ao analisar')
m("H-RC07", HK, RC, "anexar_audit devolve True sem gravar",
  '    """Anexa uma linha ao audit. Recusa (False) se o audit resolver para dentro de um workspace."""\n',
  '    """Anexa uma linha ao audit. Recusa (False) se o audit resolver para dentro de um workspace."""\n    return True\n')
m("H-RC08", HK, RC, "_e_construtor devolve False",
  '    """Construtor = subagente cujo agent_type não é autor no MANIFEST (sem agent_type ⇒ construtor)."""\n',
  '    """Construtor = subagente cujo agent_type não é autor no MANIFEST (sem agent_type ⇒ construtor)."""\n    return False\n')
m("H-RC09", HK, RC, "_rel_heldout devolve False",
  'def _rel_heldout(ws, rel):\n', 'def _rel_heldout(ws, rel):\n    return False\n')
m("H-RC10", HK, RC, "embedded_text_hit devolve False",
  'def embedded_text_hit(text):\n', 'def embedded_text_hit(text):\n    return False\n')
m("H-RC11", HK, RC, "_find_destroi devolve False",
  '    (os parênteses/`!` do find quebram o segmento, por isso a varredura é sobre todos os tokens)."""\n',
  '    (os parênteses/`!` do find quebram o segmento, por isso a varredura é sobre todos os tokens)."""\n    return False\n')
m("H-RC12", HK, RC, "selftest devolve 0 sem rodar",
  'def selftest(saida=None):\n', 'def selftest(saida=None):\n    return 0\n')
m("H-RC13", HK, RC, "selftest_vivo devolve 0 sem conferir audit",
  '    com ts ≥ gênese do ledger (quando --work tem gênese)."""\n',
  '    com ts ≥ gênese do ledger (quando --work tem gênese)."""\n    return 0\n')
m("H-RC14", HK, RC, "_pode_escrever devolve True",
  'def _pode_escrever(sub, agent_type, ws, rel):\n', 'def _pode_escrever(sub, agent_type, ws, rel):\n    return True\n')

# ============================================================ co_hook.py — demais
m("H01", HK, FR, "approval_hit: exceção --decisao vale para co/ac (não só var)",
  '            if kind == "var" and j > 0 and rest[j - 1] in ("--decision", "--decisao"):',
  '            if j > 0 and rest[j - 1] in ("--decision", "--decisao"):')
m("H02", HK, FR, "WORDS co sem `approve`",
  'WORDS = {"co": ({"aprovar", "approve"}, [("oraculo", "mudar")]),', 'WORDS = {"co": ({"aprovar"}, [("oraculo", "mudar")]),')
m("H03", HK, FR, "_embutidos ignora git -c",
  '            if t == "-c" and nxt is not None:\n                val = nxt',
  '            if False:\n                val = nxt')
m("H04", HK, FR, "strip_prefix: `env` deixa de ser wrapper",
  'WRAPPERS = {"env", "nohup",', 'WRAPPERS = {"nohup",')
m("H05", HK, FR, "script_kind ignora `-m co|ac`",
  '    if prev in ("-m", "runpy", "-mrunpy") and tok in ("ac", "co"):', '    if False:')
m("H06", HK, FR, "_pode_escrever: autor pode escrever MANIFEST.json5",
  '    if rel == "oraculo/manifest.json5":\n        return False', '    if False:\n        return False')
m("H07", HK, FR, "_decide_escrita: subagente escreve regressao.json5/gate-report.json",
  '            if sub and L.rel in SO_SCRIPT_SUBAGENTE:', '            if False:')
m("H08", HK, CI, "_decide_leitura: condição de subagente invertida",
  '    if not sub:\n        return None\n    for p, marca in itens:', '    if sub:\n        return None\n    for p, marca in itens:')
m("H09", HK, FR, "_glob_vs_heldout: `**` não conta como dentro",
  '            if s == "**":\n                return "dentro"', '            if False:\n                return "dentro"')
m("H10", HK, FR, "_git_alvos: -C não é cumulativo",
  '            if opt == "-C":\n                g = d', '            if False:\n                g = d')
m("H11", HK, FR, "RECURSIVE_FLAG_RE só aceita --recursive",
  'RECURSIVE_FLAG_RE = re.compile(r"^(-[A-Za-z]*[rR][A-Za-z]*|--recursive|--dereference-recursive)$")',
  'RECURSIVE_FLAG_RE = re.compile(r"^(--recursive|--dereference-recursive)$")')
m("H12", HK, FR, "_classificar_bash: `cd` encadeado não acumula",
  '                atual = _real(d if os.path.isabs(d) else os.path.join(atual, d))\n                bases.append(atual)',
  '                pass')
m("H13", HK, FR, "código embutido destrutivo não vira alvo destrutivo",
  '        if DESTROY_IN_CODE_RE.search(code):  # remover/mover/truncar', '        if False:  # remover/mover/truncar')
m("H14", HK, CS, "_k sem casefold (só NFC)",
  '    return unicodedata.normalize("NFC", unicodedata.normalize("NFC", p).casefold())',
  '    return unicodedata.normalize("NFC", p)')
m("H15", HK, FR, "run_raw não audita bloqueios (só toques)",
  '            if bloqueia or meta.get("toca") or CITES_SCRIPT_RE.search(texto):', '            if meta.get("toca"):')
m("H16", HK, FR, "Glob: padrão ignorado",
  '            items = expandir(base, [cwd]) + (expandir(alvo, [cwd]) if pat else [])', '            items = expandir(base, [cwd])')
m("H17", HK, FR, "Grep não é recursivo",
  '                items += expandir(os.path.join(alvo, g) if not os.path.isabs(g) else g, [cwd])\n            recursivo = True',
  '                items += expandir(os.path.join(alvo, g) if not os.path.isabs(g) else g, [cwd])\n            recursivo = False')
m("H18", HK, FR, "execução de aprovar-*.sh liberada",
  '            if APROVAR_SH_RE.search(t):\n                return "execução', '            if False:\n                return "execução')
m("H19", HK, FR, "interpretador carregando co/ac como módulo liberado",
  '            if any(MODULE_REF_RE.search(t) for t in codigo) and APPROVAL_IN_TEXT_RE.search(" ".join(body[1:])):',
  '            if False:')
m("H20", HK, FR, "find -delete não é destrutivo",
  '        if t == "-delete":\n            return True', '        if False:\n            return True')
m("H21", HK, FR, "_decide_escrita: audit dir não protegido",
  '        if _dentro(p, aud):\n            return "escrita no audit', '        if False:\n            return "escrita no audit')

# ============================================================ co_portao.py — retorno constante
m("P-RC01", PO, RC, "calcular_veredito devolve GO sempre",
  '    """(veredito, motivo, falhas, waivers). Recalcula sempre; nunca confia no `veredito` gravado."""\n',
  '    """(veredito, motivo, falhas, waivers). Recalcula sempre; nunca confia no `veredito` gravado."""\n'
  '    return "GO", "todo item aplicável PASS, nenhum waiver", [], []\n')
m("P-RC02", PO, RC, "g0_oraculo_intacto PASS constante",
  'def g0_oraculo_intacto(ws, recs=None):\n',
  'def g0_oraculo_intacto(ws, recs=None):\n    return _res("G0", "PASS", 0, "ac.py oracle verify", "hash ok", None)\n')
m("P-RC03", PO, RC, "g1_suites PASS constante",
  'def g1_suites(ws, obra=None, obra_divergente=None):\n',
  'def g1_suites(ws, obra=None, obra_divergente=None):\n    return _res("G1", "PASS", 0, "suites", "ok", None)\n')
m("P-RC04", PO, RC, "g3_territorio PASS constante",
  'def g3_territorio(diff, writes, protegidos=()):\n',
  'def g3_territorio(diff, writes, protegidos=()):\n    return _res("G3", "PASS", 0, "diff", "ok", None)\n')
m("P-RC05", PO, RC, "g4_gaming PASS constante",
  'def g4_gaming(diff, literais=()):\n',
  'def g4_gaming(diff, literais=()):\n    return _res("G4", "PASS", 0, "diff", "ok", None)\n')
m("P-RC06", PO, RC, "cadeia_ok devolve True",
  '    return not co_estado.problemas_cadeia(recs)', '    return True')
m("P-RC07", PO, RC, "divergencias_registradas devolve {}",
  '    evento que grava o hash não há comparação."""\n', '    evento que grava o hash não há comparação."""\n    return {}\n')
m("P-RC08", PO, RC, "aprovacoes_sem_audit (co_portao) devolve []",
  '    permitida que a tenha feito (formatos.audit.uso)."""\n', '    permitida que a tenha feito (formatos.audit.uso)."""\n    return []\n')
m("P-RC09", PO, RC, "plano_aprovado devolve True",
  '    """Portão humano `plano` aprovado depois do último plano_ok, com linha limpa no audit."""\n',
  '    """Portão humano `plano` aprovado depois do último plano_ok, com linha limpa no audit."""\n    return True\n')
m("P-RC10", PO, RC, "_simulado devolve False",
  'def _simulado(recs):\n', 'def _simulado(recs):\n    return False\n')
m("P-RC11", PO, RC, "writes_amplos devolve []",
  '    em profundidade."""\n    return [g for g in writes', '    em profundidade."""\n    return []\n    return [g for g in writes')
m("P-RC12", PO, RC, "literais_heldout devolve set()",
  'def literais_heldout(ws, minimo=6):\n', 'def literais_heldout(ws, minimo=6):\n    return set()\n')
m("P-RC13", PO, RC, "veredito_detalhado: veredito GO constante",
  '    return {"veredito": v, "motivo": motivo, "falhas": falhas,', '    return {"veredito": "GO", "motivo": motivo, "falhas": falhas,')
m("P-RC14", PO, RC, "_uma_suite PASS constante",
  'def _uma_suite(nome, cmd, cwd):\n', 'def _uma_suite(nome, cmd, cwd):\n    return "PASS", 0, "%s: ok" % nome\n')

# ============================================================ co_portao.py — demais
m("P01", PO, G1T, "G1 aceita texto impresso `Ran N tests` quando o runner não grava relatório",
  '    if not os.path.isfile(rel) or os.path.getmtime(rel) < t0 - 1:\n        return None, p.returncode, out,',
  '    if not os.path.isfile(rel) or os.path.getmtime(rel) < t0 - 1:\n'
  '        _m = re.search(r"Ran (\\d+) tests?", out)\n'
  '        if _m and p.returncode == 0:\n'
  '            return {"run": int(_m.group(1))}, 0, out, None\n'
  '        return None, p.returncode, out,')
m("P02", PO, FR, "G1 não confere nonce do relatório",
  '            if d.get("nonce") != nonce or d.get("runner") != "unittest" or not d.get("completo"):',
  '            if d.get("runner") != "unittest" or not d.get("completo"):')
m("P03", PO, LD, "G1: zero teste executado passa (< 1 → < 0)",
  '    if executados < 1:\n', '    if executados < 0:\n')
m("P04", PO, FR, "G1: pulados contam como executados",
  '    executados = tot["run"] - tot["skipped"]', '    executados = tot["run"]')
m("P05", PO, FR, "G1: pipe/redireção permitido na suíte",
  '        elif t and all(c in "();<>|&" for c in t):\n            raise', '        elif False:\n            raise')
m("P06", PO, PT, "calcular_veredito: simulado tem precedência sobre falhas",
  '    if falhas:\n        return "NO-GO", "; ".join(motivos), falhas, waivers\n    if simulado:\n        return "GO (simulado)", "medição simulada no ledger (D10)", falhas, waivers',
  '    if simulado:\n        return "GO (simulado)", "medição simulada no ledger (D10)", falhas, waivers\n    if falhas:\n        return "NO-GO", "; ".join(motivos), falhas, waivers')
m("P07", PO, PT, "calcular_veredito: waiver tem precedência sobre simulado",
  '    if simulado:\n        return "GO (simulado)", "medição simulada no ledger (D10)", falhas, waivers\n    if waivers:\n        return "GO (com waiver)", "%s dispensado(s) por aprovação" % ", ".join(waivers), falhas, waivers',
  '    if waivers:\n        return "GO (com waiver)", "%s dispensado(s) por aprovação" % ", ".join(waivers), falhas, waivers\n    if simulado:\n        return "GO (simulado)", "medição simulada no ledger (D10)", falhas, waivers')
m("P08", PO, FR, "calcular_veredito: waiver aceita aprovação fora de <ws>/aprovacoes",
  '                ws is None or os.path.realpath(ap)', '                True or os.path.realpath(ap)')
m("P09", PO, FR, "calcular_veredito: item ausente do relatório não reprova",
  '    if exigir_todos:\n        for gid in regi:', '    if False:\n        for gid in regi:')
m("P10", PO, FR, "calcular_veredito: id duplicado não reprova",
  '        if gid in vistos:\n            falhas.append(gid)', '        if False:\n            falhas.append(gid)')
m("P11", PO, FR, "calcular_veredito: NA em item que aplica aceito",
  '            if it.get("aplica"):\n                falhas.append(gid)\n                motivos.append("%s NA mas aplica" % gid)',
  '            if False:\n                falhas.append(gid)\n                motivos.append("%s NA mas aplica" % gid)')
m("P12", PO, FR, "rodar: núcleo removido de regressao.json5 não é avaliado (A2)",
  '        presentes = set(por_id) | set(SEM_WAIVER_NUCLEO)', '        presentes = set(por_id)')
m("P13", PO, FR, "rodar: --only com --final sai final=true",
  '"final": bool(final) and not only,', '"final": bool(final),')
m("P14", PO, FR, "rodar: divergência registrada não força NO-GO",
  '    extra = [div[k] for k in ("regressao", "obra", "plano") if k in div]\n    if extra:\n        v, motivo = "NO-GO"',
  '    extra = []\n    if extra:\n        v, motivo = "NO-GO"')
m("P15", PO, FR, "G0 não confere contagem contra o congelado",
  '    if nt < int(c.get("n_testes") or 0) or na < int(c.get("n_assercoes") or 0) or nt < 1 or na < 1:',
  '    if nt < 1 or na < 1:')
m("P16", PO, FR, "G0 não confere hash ledger x campanha",
  '    if c.get("hash") != o.get("hash"):\n', '    if False:\n')
m("P17", PO, FR, "G3 ignora caminhos protegidos",
  '    prot = [p for p in diff.paths if protegidos and casa(p, protegidos)]', '    prot = []')
m("P18", PO, FR, "G4 ignora toque em teste/config de teste",
  '        if casa(p, _TESTE_PATHS):\n', '        if False:\n')
m("P19", PO, FR, "G4 ignora skip/exit por alias",
  '        via = _gaming_por_alias(ln, *aliases[path])', '        via = None')
m("P20", PO, LD, "glob_re: `**/` exige ao menos um diretório",
  '            out += "(?:.*/)?"', '            out += "(?:.*/)"')
m("P21", PO, FR, "veredito_detalhado não confere regressao_hash",
  '    if rep.get("regressao_hash") != sha_file(reg_p):\n', '    if False:\n')
m("P22", PO, FR, "veredito_detalhado não cruza aprovações com audit",
  '    sujas = aprovacoes_sem_audit(ws, recs)\n    if sujas:', '    sujas = []\n    if sujas:')
m("P23", PO, FR, "G1 ignora obra divergente (A4)",
  '    if obra_divergente:  # A4', '    if False:  # A4')
m("P24", PO, FR, "G3 não reprova PLANO reescrito",
  '    probs = [div[k] for k in ("obra", "plano") if k in div]', '    probs = [div[k] for k in ("obra",) if k in div]')
m("P25", PO, FR, "coletar_diff ignora arquivos não rastreados",
  '    paths.update(novos)\n', '')
m("P26", PO, FR, "_ler_junit não soma failures",
  '        tot["failures"] += int(s.get("failures", 0))\n', '')
m("P27", PO, FR, "veredito_detalhado: relatório parcial vale",
  '    if rep.get("only") or rep.get("parcial"):\n', '    if False:\n')

# ============================================================ PARTE B — ocultos r2 (reaplicados)
m("B-E36", ES, "conferencia_hash_desligada", "_gate_report_valido não confere gate_report_hash do ledger",
  '    if sha_file(p) != (ult.get("payload") or {}).get("gate_report_hash"):\n        return None',
  '    if False:\n        return None', parte="B")
m("B-P10", PO, "conferencia_hash_desligada", "divergencias_registradas não confere plano_hash",
  '        if not gravado or atual != gravado:\n',
  '        if chave != "plano" and (not gravado or atual != gravado):\n', parte="B")
m("B-E37", ES, "conferencia_hash_desligada", "congelar_oraculo não confere hash registrado pelo ac.py",
  '    if not isinstance(h, str) or not HEX64.match(h) or h != atual:\n        raise Fail("ac.py não registrou',
  '    if False:\n        raise Fail("ac.py não registrou', parte="B")
m("B-E14", ES, "bypass_lock", "trava_ledger não adquire flock",
  '        if fcntl is not None:\n            fcntl.flock(fd, fcntl.LOCK_EX)\n',
  '        if False:\n            fcntl.flock(fd, fcntl.LOCK_EX)\n', parte="B")
m("B-H24", HK, "feature_removida", "anexar_audit aceita audit dentro de workspace",
  '    if _ws_acima(d):\n        return False\n', '', parte="B")
m("B-E31", ES, "condicao_invertida", "checar_maquina I6 não exige aprovacao_humana na guarda",
  '            if hum and (frm != {AH} or not tem):', '            if hum and frm != {AH}:', parte="B")
m("B-E38", ES, "condicao_invertida", "preparar_congelamento: or→and (oráculo sem asserções passa)",
  '    if nt < 1 or na < 1:\n        raise Fail("aprovar oraculo: oráculo vazio',
  '    if nt < 1 and na < 1:\n        raise Fail("aprovar oraculo: oráculo vazio', parte="B")
m("B-E34", ES, "feature_removida", "relatorio_satisfaz_entrega aceita relatório simulado",
  '    if rep.get("simulado") is True or rep.get("simulated") is True:\n', '    if False:\n', parte="B")
m("B-E10", ES, "conferencia_hash_desligada", "problemas_cadeia não confere hash do registro",
  '        if hash_registro(r) != r["hash"]:\n', '        if False:\n', parte="B")
m("B-E18", ES, "precedencia_trocada", "transicionar: atomos do chamador sobrepõem aprovacao_humana",
  '        ats = dict(atomos or {})\n        ats["aprovacao_humana"] = bool(_humano)',
  '        ats = {"aprovacao_humana": bool(_humano)}\n        ats.update(atomos or {})', parte="B")

MUTANTES = A
