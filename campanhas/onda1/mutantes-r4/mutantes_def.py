"""Mutantes M4 (onda 1, rodada 4). Parte A = próprios e novos (não repetem nenhum mutante de M3); parte B =
reaplicação dos sobreviventes de M3 (mutantes-r3/relatorio.json, partes A e B) adaptados ao código atual.

Formatos:
  * substituição: subs=[(old, new, n)] (n = ocorrências esperadas de old; todas trocadas)
  * retorno constante: rc=(qualname, expr) — insere `return <expr>` como 1ª instrução do corpo (depois da docstring)
"""

RC = "retorno_constante"
FR = "feature_removida"
CI = "condicao_invertida"
LD = "limite_deslocado"
PT = "precedencia_trocada"
HC = "campo_omitido_do_hash"
LK = "lock_removido"
HD = "conferencia_hash_desligada"
WV = "validacao_waiver_desligada"
G1T = "g1_texto_impresso"

CO, ES, HK, PO = "co.py", "co_estado.py", "co_hook.py", "co_portao.py"
MUTANTES = []


def m(id_, arq, tipo, desc, old, new, n=1, parte="A", **kw):
    MUTANTES.append(dict(id=id_, parte=parte, arquivo=arq, tipo=tipo, descricao=desc, subs=[(old, new, n)], **kw))


def ms(id_, arq, tipo, desc, subs, parte="A", **kw):
    MUTANTES.append(dict(id=id_, parte=parte, arquivo=arq, tipo=tipo, descricao=desc,
                         subs=[s if len(s) == 3 else (s[0], s[1], 1) for s in subs], **kw))


def rc(id_, arq, qual, expr, desc=None, tipo=RC, parte="A", **kw):
    MUTANTES.append(dict(id=id_, parte=parte, arquivo=arq, tipo=tipo,
                         descricao=desc or "%s devolve %s" % (qual, expr), rc=(qual, expr), **kw))


NULO = "contextlib.nullcontext()"

# ============================================================================================ co.py (7)
rc("C4-01", CO, "_despachar", "0", "_despachar devolve 0 sem despachar nada")
rc("C4-02", CO, "_pendente", "0", "subcomando pendente sai 0 (finge sucesso)")
rc("C4-03", CO, "_modulo", "None", "_modulo: todo módulo 'ausente' (hook/portao indisponíveis)")
m("C4-04", CO, CI, "_main: Bad (entrada inválida) do handler sai 0",
  '    except co_estado.Bad as e:\n        sys.stderr.write("erro: %s\\n" % e)\n        return 2\n    except SystemExit as e:\n        # handler',
  '    except co_estado.Bad as e:\n        sys.stderr.write("erro: %s\\n" % e)\n        return 0\n    except SystemExit as e:\n        # handler')
m("C4-05", CO, CI, "_main: sys.exit(None/str) do handler vira 0",
  "rc = e.code if isinstance(e.code, int) and not isinstance(e.code, bool) else 2",
  "rc = e.code if isinstance(e.code, int) and not isinstance(e.code, bool) else 0")
m("C4-06", CO, CI, "_main: exceção inesperada do handler sai 0",
  '        sys.stderr.write("erro interno (%s): %s\\n" % (type(e).__name__, e))\n        return 2\n    return _rc(rc)',
  '        sys.stderr.write("erro interno (%s): %s\\n" % (type(e).__name__, e))\n        return 0\n    return _rc(rc)')
m("C4-07", CO, CI, "_despachar: co_hook ausente sai 0",
  '        if m is None:\n            return 2\n        if hasattr(m, "cmd_hook")', '        if m is None:\n            return 0\n        if hasattr(m, "cmd_hook")')

# ============================================================================================ co_estado.py
# ---- retorno constante: átomos (funções)
for i, (fn, v) in enumerate([
        ("_a_ac_decisao_parar", "True"), ("_a_autor_fora_dos_construtores", "True"), ("_a_baseline_reprodutivel", "True"),
        ("_a_brief_valido", "True"), ("_a_campanhas_ativas_abaixo_de_2", "True"), ("_a_colisao_vazia", "True"),
        ("_a_copia_limpa", "True"), ("_a_criterio_parada_ok", "True"), ("_a_criterios_classificados", "True"),
        ("_a_defeitos_classificados", "True"), ("_a_deps_aceitas", "True"), ("_a_hash_entradas_mudou", "True"),
        ("_a_lote_disjunto", "True"), ("_a_medicao_posterior_ao_merge", "True"), ("_a_merge_ordenado", "True"),
        ("_a_mesma_rejeicao_2x", "False"), ("_a_obra_replanejou", "True"), ("_a_oraculo_apos_cada_merge", "True"),
        ("_a_oraculo_campanha_congelado", "True"), ("_a_oraculos_fechados_verdes", "True"),
        ("_a_orcamento_esgotado", "False"), ("_a_orcamento_restante", "True"), ("_a_oscilacao", "False"),
        ("_a_plano_valido", "True"), ("_a_plato_2", "True"), ("_a_pontos_atualizados", "True"),
        ("_a_pontos_cobertos", "True"), ("_a_relatorio_presente", "True"), ("_a_resultado_no_worktree", "True"),
        ("_a_sistema_congelado", "True"), ("_a_so_sistema_vira_task", "True"), ("_a_teste_falha_antes", "True"),
        ("_a_verificador_nao_autor", "True"), ("_a_vermelho_baseline_e_stub", "True"),
        ("_a_writes_disjuntos_dos_vivos", "True"), ("_a_testes_vermelho_verde", "True"), ("_a_agora_apos", "True"),
        ("_a_tipo_baseline", "False"), ("_a_ha_decisoes", "False"), ("_a_todas_ret", "True"),
        ("_a_gate_falhou.f", "False"), ("_a_gate_passou.f", "True")], 1):
    rc("E4-A%02d" % i, ES, fn, v, "átomo %s devolve %s" % (fn, v), atomo=True)

# ---- retorno constante: átomos lambda do dict ATOMOS
for i, (nome, corpo) in enumerate([
        ("motivo_registrado", 'bool(str(c.payload.get("motivo") or "").strip())'),
        ("evidencia_registrada", 'bool(str(c.payload.get("evidencia") or "").strip())'),
        ("sem_perdidas_pendentes", 'not c.st["vivos"]'),
        ("lote_cabe_no_teto", 'len(c.st["vivos"]) < c.st["teto_vigente"]'),
        ("vivos_abaixo_do_teto", 'len(c.st["vivos"]) < c.st["teto_vigente"]'),
        ("nenhuma_em_voo", 'not any(t.get("estado") == "EM_VOO" for t in c.st["tasks"].values())'),
        ("trava_adquirida", 'c.st.get("trava") is not None'),
        ("oraculo_congelado", 'c.st.get("oraculo") is not None')], 1):
    m("E4-L%02d" % i, ES, RC, "átomo %s (lambda) devolve True" % nome,
      '    "%s": lambda c: %s,' % (nome, corpo), '    "%s": lambda c: True,' % nome, atomo=True)

# ---- retorno constante: guardas, conferências, funções públicas/handlers
for i, (fn, v, d) in enumerate([
        ("problemas_waivers", "[]", "conferência de waivers sempre limpa"),
        ("relatorio_parcial_ajustado", "rep", "relatório parcial mantém final=true"),
        ("_gate_report_valido", "None", "gate-report nunca válido"),
        ("hash_entradas_task", "None", "hash de entradas indeterminado"),
        ("valor_atomo", "True", "API valor_atomo devolve True"),
        ("Contexto.valor", "True", "todo valor de guarda é True"),
        ("_audit_linhas", "[]", "audit nunca lido (testemunha some)"),
        ("hook_selftest_estatico", "True", "selftest estático do hook sempre ok"),
        ("_manifest_integro", "True", "MANIFEST sempre íntegro"),
        ("_oraculo_campanha_ok", "True", "oráculo da campanha sempre ok"),
        ("_task_valida", "True", "toda task do PLANO válida"),
        ("_deps_ok", "True", "deps sempre aceitas"),
        ("_janela_expirada", "False", "janela nunca expira"),
        ("eventos_humanos", "[]", "nenhum evento é humano (cmd_ev)"),
        ("payload_do_motor", "payload", "motor não grava campos (agente decide)"),
        ("_sobreposicao", "None", "I5 nunca acusa sobreposição"),
        ("_ciclo_sem_teto", "None", "I4 nunca acusa ciclo sem teto"),
        ("contar_testes_assercoes", "(1, 1)", "contagem do oráculo constante"),
        ("cmd_pontos", "0", "pontos check sempre OK"),
        ("cmd_maquina", "0", "maquina check sempre OK"),
        ("cmd_load", "0", "load sempre 0 sem pacote"),
        ("make_challenge", '"0000"', "desafio humano constante"),
        ("pos_gravacao", "None", "pós-gravação (cache/RETOMAR/aprovar.sh) desligada"),
        ("hash_estado", '"0" * 64', "hash_estado constante (TOCTOU nunca detectado)"),
        ("cmd_aprovar", "0", "aprovar sai 0 sem gravar"),
        ("cmd_init", "0", "init sai 0 sem criar a obra"),
        ("cmd_ev", "0", "ev sai 0 sem gravar"),
        ("aplicavel", "True", "toda transição aplicável de qualquer estado"),
        ("_vivos_payloads", "[]", "vivos ignorados na disjunção"),
        ("_construtores", "set()", "nenhum construtor conhecido"),
        ("_metrica_medida", "1e9", "métrica medida constante (critério sempre atingido)"),
        ("_comparacoes", "[]", "nenhuma comparação lida"),
        ("_lote", "None", "lote nunca julgado"),
        ("_rejeicoes", "[]", "nenhuma rejeição contada"),
        ("_relatorio", "(True, {})", "relatório da frente sempre íntegro e vazio"),
        ("ler_obra", "{}", "obra.json5 lida como vazia"),
        ("_dentro", "False", "_dentro (estado) sempre False")], 1):
    rc("E4-R%02d" % i, ES, fn, v, "%s devolve %s — %s" % (fn, v, d))

# ---- campo omitido do hash
m("E4-H01", ES, HC, "hash_registro omite `evento`",
  '    sem = {k: v for k, v in rec.items() if k != "hash"}', '    sem = {k: v for k, v in rec.items() if k not in ("hash", "evento")}')
m("E4-H02", ES, HC, "hash_registro omite `para`",
  '    sem = {k: v for k, v in rec.items() if k != "hash"}', '    sem = {k: v for k, v in rec.items() if k not in ("hash", "para")}')
m("E4-H03", ES, HC, "hash_estado omite `obra`",
  'CHAVES_HASH_ESTADO = ["obra", "contadores",', 'CHAVES_HASH_ESTADO = ["contadores",')
m("E4-H04", ES, HC, "hash_estado omite `tasks`",
  '"teto_vigente", "tasks", "campanhas"', '"teto_vigente", "campanhas"')
m("E4-H05", ES, HC, "hash_estado omite `contrato_hash`",
  '"campanhas", "contrato_hash",\n', '"campanhas",\n')
m("E4-H06", ES, HC, "hash_entradas_task omite o hash do oráculo",
  'return sha_obj({"task": t, "oraculo": (st.get("oraculo") or {}).get("hash"), "contrato": st.get("contrato_hash")})',
  'return sha_obj({"task": t, "contrato": st.get("contrato_hash")})')
m("E4-H07", ES, HC, "hash_entradas_task omite a entrada da task",
  'return sha_obj({"task": t, "oraculo": (st.get("oraculo") or {}).get("hash"), "contrato": st.get("contrato_hash")})',
  'return sha_obj({"oraculo": (st.get("oraculo") or {}).get("hash"), "contrato": st.get("contrato_hash")})')
ms("E4-H08", ES, HC, "manifest_hash (gravado e conferido) omite `construtores`", [
    ('        doc = {"schema_version": 1, "frentes": man["frentes"], "construtores": man.get("construtores") or {},',
     '        doc = {"schema_version": 1, "frentes": man["frentes"],'),
    ('    doc = {"schema_version": 1, "frentes": man.get("frentes"), "construtores": man.get("construtores") or {},\n           "congelado": man.get("congelado")}\n    return sha_obj(doc) ==',
     '    doc = {"schema_version": 1, "frentes": man.get("frentes"),\n           "congelado": man.get("congelado")}\n    return sha_obj(doc) ==')])

# ---- lock removido
m("E4-K01", ES, LK, "retomar sem trava_ledger",
  '    with trava_ledger(ws):\n        regs = ler_ledger(ws)\n        conferir_ledger(ws, regs)\n        st = fold_registros(regs, maq)\n        desp = {}',
  '    with %s:\n        regs = ler_ledger(ws)\n        conferir_ledger(ws, regs)\n        st = fold_registros(regs, maq)\n        desp = {}' % NULO)
m("E4-K02", ES, LK, "cmd_oraculo_manifest sem trava_ledger",
  '    with trava_ledger(w):\n        regs = ler_ledger(w)\n        conferir_ledger(w, regs)\n        st = fold_registros(regs)\n        if st["obra"]["estado"] != "ORACULO":',
  '    with %s:\n        regs = ler_ledger(w)\n        conferir_ledger(w, regs)\n        st = fold_registros(regs)\n        if st["obra"]["estado"] != "ORACULO":' % NULO)
m("E4-K03", ES, LK, "cmd_init sem trava_ledger",
  '    with trava_ledger(w):\n        if os.path.exists(p["ledger"]):', '    with %s:\n        if os.path.exists(p["ledger"]):' % NULO)
m("E4-K04", ES, LK, "trava_ledger com LOCK_SH (compartilhada)", 'fcntl.flock(fd, fcntl.LOCK_EX)', 'fcntl.flock(fd, fcntl.LOCK_SH)')
m("E4-K05", ES, LK, "trava_ledger trava arquivo por processo (sem exclusão mútua)",
  'fd = os.open(p["lock"], os.O_RDWR | os.O_CREAT, 0o600)', 'fd = os.open(p["lock"] + str(os.getpid()), os.O_RDWR | os.O_CREAT, 0o600)')

# ---- conferência de hash desligada
m("E4-D01", ES, HD, "_relatorio não confere relatorio_hash", '    if sha_file(arq) != p.get("relatorio_hash"):', '    if False:')
m("E4-D02", ES, HD, "A8: hash do cache no seq não conferido (só o seq)",
  'HEX64.match(ch) and regs[cs - 1].get("hash") != ch:', 'HEX64.match(ch) and False:')
m("E4-D03", ES, HD, "cmd_aprovar não reconfere hash_estado depois do desafio",
  '    if st2["hash_estado"] != h_antes or st2["obra"] != o:', '    if False:')
m("E4-D04", ES, HD, "_a_sistema_congelado não confere hash_sistema do alvo",
  '    return hash_sistema(o["alvo"]) == p.get("sistema_hash")', '    return True')
m("E4-D05", ES, HD, "_a_baseline_reprodutivel não confere oraculo_hash",
  '    if not ora.get("hash") or b.get("oraculo_hash") != ora.get("hash"):', '    if not ora.get("hash"):')
m("E4-D06", ES, HD, "_a_retomar_md_valido aceita qualquer ledger_hash bem formado",
  '    return bool(m) and m.group(1) == c.st["ledger_hash"]', '    return bool(m)')

# ---- waiver
m("E4-W01", ES, WV, "relatorio_satisfaz_entrega não confere aprovação de WAIVED",
  '    if any(s == "WAIVED" for s in itens.values()):', '    if False:')
m("E4-W02", ES, WV, "relatorio_satisfaz_entrega: WAIVED sem ws aceito",
  '            return False, "WAIVED sem workspace para conferir a aprovação"', '            return True, "ok"')

# ---- condição invertida / limite deslocado
m("E4-C01", ES, CI, "_mesma_2x: == → !=", 'bool(rs[-1]) and rs[-1] == rs[-2]', 'bool(rs[-1]) and rs[-1] != rs[-2]')
m("E4-C02", ES, LD, "orçamento: despachos >= MAX → >", '>= c.st["constantes"].get("MAX_DESPACHOS", 30)', '> c.st["constantes"].get("MAX_DESPACHOS", 30)')
m("E4-C03", ES, LD, "campanhas ativas < teto → <=", '    return len(_campanhas_ativas(c, excluir=c.ident)) < teto', '    return len(_campanhas_ativas(c, excluir=c.ident)) <= teto')
m("E4-C04", ES, CI, "oscilação: sinais[-1] != sinais[-2] → ==", 'sinais[-1] != sinais[-2]', 'sinais[-1] == sinais[-2]')
m("E4-C05", ES, LD, "platô com 1 comparação (len < 2 → < 1)", '    if len(cs) < 2:\n        return False\n    for d in cs[-2:]:', '    if len(cs) < 1:\n        return False\n    for d in cs[-2:]:')
m("E4-C06", ES, LD, "pass3_final aceita k=2", 'p["k"] >= 3 and not p.get("simulated")', 'p["k"] >= 2 and not p.get("simulated")')
m("E4-C07", ES, LD, "merge_ordenado aceita dono repetido (< → <=)", 'donos[i] < donos[i + 1]', 'donos[i] <= donos[i + 1]')
m("E4-C08", ES, FR, "oraculo_apos_cada_merge ignora o limite da trava seguinte",
  'if not any(t["seq"] < s < fim for s in rels):', 'if not any(t["seq"] < s for s in rels):')
m("E4-C09", ES, FR, "testes_vermelho_verde não exige vermelho antes",
  'isinstance(t.get("exit_antes"), int) and t["exit_antes"] != 0 and', 'isinstance(t.get("exit_antes"), int) and')
m("E4-C10", ES, CI, "copia_limpa: all → any", 'return all(r.get("copia_limpa") is True for r in runs)', 'return any(r.get("copia_limpa") is True for r in runs)')
m("E4-C11", ES, FR, "defeito `sistema` sem frente aceito",
  ' or (d["classe"] == "sistema" and not d.get("frente")):', ':')
m("E4-C12", ES, FR, "verificador_nao_autor (obra) não cruza com construtores",
  '    return not (vs & _construtores(c))', '    return bool(vs)')
m("E4-C13", ES, FR, "_task_valida aceita writes em protegidos", '        if raiz in PROTEGIDOS_REL:', '        if raiz in ():')
m("E4-C14", ES, FR, "_task_valida aceita dep em si mesma", 'any(d not in ids or d == t["id"] for d', 'any(d not in ids for d')
m("E4-C15", ES, FR, "plano_valido não detecta ciclo", '    if any(ciclo(n) for n in tasks):\n        return False', '    if False:\n        return False')
m("E4-C16", ES, FR, "plano_valido não exige writes disjuntos",
  '            if _globs_sobrepoem(lst[i]["writes"], lst[j]["writes"]):\n                return False', '            if False:\n                return False')
m("E4-C17", ES, FR, "plano_valido aceita construtor = autor do oráculo",
  '        if any(t["construtor"] in autores for t in lst):', '        if False:')
m("E4-C18", ES, PT, "Contexto: injeção vence a evidência computada (G-2 invertido)",
  '        f = ATOMOS.get(nome)\n        v = None\n',
  '        if nome in self.atomos and nome in ATOMOS_INJETAVEIS and isinstance(self.atomos[nome], bool):\n            return self.atomos[nome]\n        f = ATOMOS.get(nome)\n        v = None\n')
m("E4-C19", ES, FR, "Contexto: qualquer átomo aceita injeção (não só INJETAVEIS)",
  '        if nome in self.atomos and nome in ATOMOS_INJETAVEIS and isinstance', '        if nome in self.atomos and isinstance')
m("E4-C20", ES, PT, "_a_limite: and → or (causa OU retomar_apos)",
  'in ("rate_limit", "janela", "outro") and parse_ts(c.payload.get("retomar_apos"))', 'in ("rate_limit", "janela", "outro") or parse_ts(c.payload.get("retomar_apos"))')
m("E4-C21", ES, PT, "A8 audit: (r None or não-aprovacao) passa a exigir portão divergente (or → and)",
  '        if r is None or r.get("evento") != "aprovacao" or \\\n', '        if (r is None or r.get("evento") != "aprovacao") and \\\n')
m("E4-C22", ES, FR, "fold G-1: registro ambíguo escolhe a 1ª candidata", '        if len(cand_ator) != 1:', '        if not cand_ator:')
m("E4-C23", ES, FR, "fold: aprovação de OUTRO portão vale para a transição humana",
  '        if not ap or ap.get("portao") != no[1] or ap.get("decisao") != ev:', '        if not ap or ap.get("decisao") != ev:')
m("E4-C24", ES, FR, "fold aceita operacional desconhecido",
  '            if ev not in ops:\n                raise Fail', '            if False:\n                raise Fail')
m("E4-C25", ES, FR, "fold ignora medição simulada", '        if p.get("simulated") is True:\n            st["simulado"] = True', '        if False:\n            st["simulado"] = True')
m("E4-C26", ES, FR, "fold ignora max_despachos do contrato_hash", '        if isinstance(p.get("max_despachos"), int):', '        if False:')
m("E4-C27", ES, FR, "fold ignora zera_em dos contadores", '        _zerar(maq, st, tn)\n', '        pass\n')
m("E4-C28", ES, FR, "fold não incrementa contadores da obra",
  '        for c in _incrementos(t):\n            st["contadores"][c] = st["contadores"].get(c, 0) + 1',
  '        for c in []:\n            st["contadores"][c] = st["contadores"].get(c, 0) + 1')
m("E4-C29", ES, FR, "aprovacoes_sem_audit: linha de audit de outro workspace vale",
  'a.get("seq") == r.get("seq") and _mesmo_ws(a.get("work"))', 'a.get("seq") == r.get("seq")')
m("E4-C30", ES, PT, "_a_hook_vivo: and → or (audit OU selftest)",
  '    return hook_vivo_no_audit(c.ws, gen) and hook_selftest_estatico()', '    return hook_vivo_no_audit(c.ws, gen) or hook_selftest_estatico()')
m("E4-C31", ES, FR, "hook_vivo_no_audit aceita linha permitida",
  '        if x.get("tipo") != "tool_call" or x.get("decisao") != "bloqueado":', '        if x.get("tipo") != "tool_call":')
m("E4-C32", ES, FR, "hook_vivo_no_audit aceita linha anterior à gênese",
  '        if desde_ts and str(x.get("ts", "")) < desde_ts:\n            continue\n        return True', '        if False:\n            continue\n        return True')
m("E4-C33", ES, FR, "cmd_load não refaz o fold (G-7a)", '    fold(args.work)  # G-7a', '    pass  # G-7a')
m("E4-C34", ES, FR, "transicionar não chama payload_do_motor", '        payload_do_motor(ws, st, evento, tn, payload, ctx)\n', '        pass\n')
m("E4-C35", ES, CI, "task.verificada: verificacao_ok sempre True", '        payload["verificacao_ok"] = tn == "aceitar"', '        payload["verificacao_ok"] = True')
m("E4-C36", ES, FR, "checar_maquina sem I3", '            if suc and any(n[0] == suc for n in r):', '            if False:')
m("E4-C37", ES, FR, "checar_maquina sem S3", '                if f in terminal:\n                    v("S3"', '                if False:\n                    v("S3"')
m("E4-C38", ES, FR, "checar_maquina sem I7 (estável sem motivo)", '            if frm & estaveis and not t.get("motivo_obrigatorio"):', '            if False:')
m("E4-C39", ES, FR, "I4: contador zerado no ciclo ainda limita (R3-7 desligado)", '            limitam = inc - zer', '            limitam = inc')
m("E4-C40", ES, FR, "checar_maquina sem I2 (estado preso)", '        for s in presos:\n            v("I2"', '        for s in []:\n            v("I2"')
m("E4-C41", ES, FR, "checar_maquina sem I5", '                if sobre is not None:', '                if False:')
m("E4-C42", ES, FR, "lote_disjunto ignora os vivos", '        if _globs_sobrepoem(wa, vivos):\n            return False', '        if False:\n            return False')
m("E4-C43", ES, FR, "resultado_no_worktree sem exigir isolation=worktree",
  '    if (desp.get("payload") or {}).get("isolation") != "worktree":\n        return False', '    if False:\n        return False')
m("E4-C44", ES, FR, "relatorio_presente aceita relatório de outra task",
  '    return d.get("task") in (None, c.ident) and isinstance', '    return isinstance')
m("E4-C45", ES, CI, "deps aceitas com dep RETORNADA", '.get("estado") == "ACEITA" for d in (t.get("deps") or [])', '.get("estado") in ("ACEITA", "RETORNADA") for d in (t.get("deps") or [])')
m("E4-C46", ES, FR, "ac_decisao_parar não exige done.decisao.1",
  '    return dec.startswith("parar") and bool((st.get("done") or {}).get("decisao.1"))', '    return dec.startswith("parar")')
m("E4-C47", ES, CI, "oraculos_fechados_verdes: passed == total → passed > 0",
  'q["total"] > 0 and q.get("passed") == q["total"]', 'q["total"] > 0 and (q.get("passed") or 0) > 0')
m("E4-C48", ES, LD, "teste_falha_antes aceita run verde (< → <=)", 'x["passed"] < x["total"]', 'x["passed"] <= x["total"]')
m("E4-C49", ES, FR, "pontos_atualizados aceita ponto sumido (G14)", '    if not ids_antes <= ids:', '    if False:')
m("E4-C50", ES, FR, "pontos_atualizados não exige histórico da rodada", 'h.get("rodada") == rodada and\n', '\n')
m("E4-C51", ES, FR, "autor_fora: construtor = autor aceito", '        if cons & autores:\n            return False', '        if False:\n            return False')
m("E4-C52", ES, FR, "autor_fora: MANIFEST não gravado aceito", '    if not _manifest_integro(c, man):', '    if False:')
m("E4-C53", ES, LD, "criterios_classificados: ncl >= nt → >= 0", '    return casos_ok and bool(cen) and ncl >= nt', '    return casos_ok and bool(cen) and ncl >= 0')
m("E4-C54", ES, FR, "pontos_cobertos não confere cenários citados",
  'if not isinstance(cs, list) or not cs or any(cc not in cen for cc in cs):', 'if not isinstance(cs, list) or not cs:')
m("E4-C55", ES, FR, "vermelho_baseline_e_stub só testa o stub",
  '    base = _oraculo_vermelho_em(alvo, testes, stub=False)\n', '    base = True\n')
m("E4-C56", ES, CI, "_oraculo_vermelho_em: returncode == 0 → != 0", '            if p.returncode == 0:\n                return False  # o oráculo passa', '            if p.returncode != 0:\n                return False  # o oráculo passa')
m("E4-C57", ES, FR, "cmd_aprovar aprova portão diferente do pendente",
  '    if o["estado"] != "AGUARDANDO_HUMANO" or o["portao"] != portao:', '    if o["estado"] != "AGUARDANDO_HUMANO":')
m("E4-C58", ES, FR, "ev nota grava o payload inteiro do agente", '            payload = {"texto": payload["texto"]}', '            pass')
m("E4-C59", ES, FR, "init aceita --alvo inexistente", '    if not os.path.isdir(alvo):\n        raise Bad("--alvo', '    if False:\n        raise Bad("--alvo')
ms("E4-C60", ES, FR, "init reescreve ledger existente", [
    ('    if os.path.exists(p["ledger"]):\n        raise Bad("já existe obra em %s (ledger presente)', '    if False:\n        raise Bad("já existe obra em %s (ledger presente)'),
    ('        if os.path.exists(p["ledger"]):\n            raise Bad("já existe obra em %s" % w)', '        if False:\n            raise Bad("já existe obra em %s" % w)')])
m("E4-C61", ES, FR, "limite_uso rate_limit não recua o teto", 'payload.get("causa") == "rate_limit" and', 'payload.get("causa") == "__nunca__" and')
m("E4-C62", ES, LD, "MAX_DESPACHOS ignora nº de tasks", '"max_despachos": st["constantes"].get("MAX_TENTATIVAS", 3) * max(n, 1)}', '"max_despachos": st["constantes"].get("MAX_TENTATIVAS", 3) * 100}')
m("E4-C63", ES, CI, "Kleene: not de indeterminado vira True", '        return None if v is None else (not v)', '        return not v')
m("E4-C64", ES, FR, "problemas_cadeia aceita campo extra no registro",
  '        if sorted(r.keys()) != sorted(CAMPOS_LEDGER):', '        if not set(CAMPOS_LEDGER) <= set(r.keys()):')
m("E4-C65", ES, FR, "métrica: medição simulada conta para o critério de parada",
  'p.get("final") is True \\\n                and not p.get("simulated"):', 'p.get("final") is True:')
m("E4-C66", ES, LD, "pass_at_k aceita k menor que o pedido", 'p["k"] < int(m.group(2)):', 'p["k"] < int(m.group(2)) - 1:')
m("E4-C67", ES, FR, "medição anterior ao último merge aceita", '    if ult is not None and rec["seq"] < ult:\n        return False', '    if False:\n        return False')
m("E4-C68", ES, FR, "baseline não reprodutível aceito (len(qs) == 1 → >= 1)", '    return len(qs) == 1  # reprodutível', '    return len(qs) >= 1  # reprodutível')
m("E4-C69", ES, FR, "baseline simulado aceito", '            (rec.get("payload") or {}).get("simulated"):', '            False:')
m("E4-C70", ES, FR, "pontos_completos aceita lista vazia", '    return bool(p["pontos"]) and all(', '    return all(')

# ============================================================================================ co_hook.py
for i, (fn, v) in enumerate([
        ("tokenize", "[]"), ("normalizar_comando", "[]"), ("segments", "iter(())"), ("strip_prefix", "seg"),
        ("script_kind", "None"), ("approval_hit", "[]"), ("_tokens_texto", "[]"), ("_embutidos", "[]"),
        ("_ws_acima", "None"), ("_ws_abaixo", "[]"), ("_ws_fundo", "[]"), ("_ws_conhecidos", "[]"),
        ("_manifest", "{}"), ("_autores", "set()"), ("_heldout_globs", "[]"), ("_rel_protegido_escrita", "False"),
        ("_dentro", "False"), ("localizar", "[]"), ("_glob_vs_heldout", "None"), ("expandir", "[]"),
        ("_quem", "(False, None)"), ("_toca", "False"), ("_executa_destrutivo", "False"),
        ("_git_alvos", "([atual], [], [atual], [], [])"),
        ("_classificar_bash", '(None, {"tokens": [], "toca": False, "alvo": cmd})'),
        ("_analisar", '(None, {"tokens": [], "toca": False, "alvo": ""})'), ("registrar_audit", "True"),
        ("cmd_hook", "0"), ("main", "0"), ("_find_partidas", "[]"), ("payloads_selftest", "[]"), ("_real", "p")], 1):
    rc("H4-R%02d" % i, HK, fn, v)

m("H4-01", HK, FR, "WRAPPERS sem exec/command/sudo",
  'WRAPPERS = {"env", "nohup", "exec", "command", "builtin", "sudo", "doas",', 'WRAPPERS = {"env", "nohup", "builtin", "doas",')
m("H4-02", HK, FR, "sh/bash viram leitores isentos", '"cmp", "ls", "file",', '"cmp", "ls", "sh", "bash", "file",')
m("H4-03", HK, FR, "less/more/man deixam de executar +cmd", ', "less": "less", "more": "less", "man": "less"}', '}')
m("H4-04", HK, FR, "aprovar-*.sh só casa com ./ (caminho absoluto escapa)", 'APROVAR_SH_RE = re.compile(r"(^|/)aprovar-', 'APROVAR_SH_RE = re.compile(r"(^|\\./)aprovar-')
m("H4-05", HK, FR, "falha fechada sensível a caixa", 'held[-_ ]out", re.IGNORECASE)', 'held[-_ ]out")')
m("H4-06", HK, FR, "runpy deixa de contar como carga de co/ac", r'''|\brunpy\b|"''' + "\n", '''|"''' + "\n")
m("H4-07", HK, CI, "aninhamento profundo vira permitido (falha aberta)",
  '        return "aninhamento de shell profundo demais para analisar (falha fechada)", []', '        return None, []')
m("H4-08", HK, CI, "código embutido só analisado em leitor (not is_reader → is_reader)",
  '                if not is_reader:\n                    why, toks = check_aprovacao(t, depth + 1)', '                if is_reader:\n                    why, toks = check_aprovacao(t, depth + 1)')
m("H4-09", HK, FR, "xargs/parallel/source com co.py aprovar liberado", '            if refs and APPROVAL_IN_TEXT_RE.search(cmd):', '            if False:')
m("H4-10", HK, FR, "eval de texto com aprovação liberado", '            if exe == "eval" and embedded_text_hit', '            if False and embedded_text_hit')
m("H4-11", HK, FR, "vim -c/--cmd/-S ignorado", '            if t in ("-c", "--cmd", "-S") and nxt is not None:', '            if False:')
m("H4-12", HK, FR, "system() embutido não extraído", '        m = re.search(r"system\\s*\\(\\s*[\'\\"](.*)[\'\\"]\\s*\\)", v)', '        m = None')
m("H4-13", HK, FR, "_ws_fundo ignora workspaces do audit", '        for w in _ws_conhecidos():', '        for w in []:')
m("H4-14", HK, FR, "globs heldout do MANIFEST ignorados", '                gl.extend(g for g in f["heldout"] if isinstance(g, str))', '                pass')
m("H4-15", HK, FR, "aprovacoes/ deixa de ser protegido", '    return top in (".construcao", "aprovacoes", "oraculo")', '    return top in (".construcao", "oraculo")')
m("H4-16", HK, LD, "_dentro sem fronteira de componente", '    return p == d or p.startswith(d.rstrip("/") + "/")', '    return p.startswith(d.rstrip("/"))')
m("H4-17", HK, FR, "autor do MANIFEST escreve .construcao/aprovacoes", '    if top != "oraculo":\n        return False', '    if False:\n        return False')
m("H4-18", HK, FR, "rm -rf do próprio workspace liberado", '            if L.rel == "" and destrutivo:', '            if False:')
m("H4-19", HK, FR, "destruição de ancestral do workspace liberada", '                if destrutivo:\n                    return "operação destrutiva sobre ancestral', '                if False:\n                    return "operação destrutiva sobre ancestral')
m("H4-20", HK, CI, "leitura recursiva de ancestral: recursivo → not recursivo", '            if ancestral and recursivo:', '            if ancestral and not recursivo:')
m("H4-21", HK, FR, "glob que casa o held-out liberado", '            if marca == "glob_dentro" or (', '            if (')
m("H4-22", HK, FR, "_toca ignora regressao.json5/gate-report.json", ' or L.rel in SO_SCRIPT_SUBAGENTE):\n                return True', '):\n                return True')
m("H4-23", HK, LD, "-exec: comando executado pula o 1º token", '_executa_destrutivo(ts[i + 1:i + 12])', '_executa_destrutivo(ts[i + 2:i + 12])')
m("H4-24", HK, FR, "git --git-dir ignorado", '            for o in ("--git-dir", "--work-tree"):', '            for o in ("--work-tree",):')
m("H4-25", HK, FR, "git <rev>:<caminho> ignorado", '            revs.append(t.split(":", 1)[1])', '            pass')
m("H4-26", HK, FR, "git archive/grep sem apontador não é recursivo",
  '    if subcmd in GIT_DESPEJA_ARVORE or (apont and subcmd in GIT_CONTEUDO):', '    if apont and subcmd in GIT_CONTEUDO:')
m("H4-27", HK, FR, "dd of= não é escrita", '            escritas.extend(a[3:] for a in args if a.startswith("of="))', '            pass')
m("H4-28", HK, FR, "sed -i não é escrita", '        elif exe in INPLACE and any(', '        elif False and any(')
m("H4-29", HK, FR, "cp/ln/rsync destino não é escrita", '        elif exe in WRITERS_DEST and nflag:', '        elif False:')
m("H4-30", HK, FR, "redireção > não é escrita", '            if kind == ">":\n                escritas.append(alvo)', '            if False:\n                escritas.append(alvo)')
m("H4-31", HK, FR, "código embutido com walk/glob não é recursivo", '                    if RECURSIVE_CODE_RE.search(a):\n                        recursivo = True', '                    if False:\n                        recursivo = True')
m("H4-32", HK, FR, "MultiEdit/NotebookEdit não analisados", '    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):', '    if tool in ("Write", "Edit"):')
m("H4-33", HK, FR, "Grep: glob ignorado", '            if isinstance(g, str) and g:\n                items += expandir(', '            if False:\n                items += expandir(')
m("H4-34", HK, FR, "audit não registra toque em protegido permitido",
  '            if bloqueia or meta.get("toca") or CITES_SCRIPT_RE.search(texto):', '            if bloqueia or CITES_SCRIPT_RE.search(texto):')
m("H4-35", HK, FR, "audit grava tokens vazios", '"tokens": list(tokens or []), "decisao": decisao,', '"tokens": [], "decisao": decisao,')
m("H4-36", HK, CI, "erro interno do hook nunca bloqueia", '        code = 2 if RAW_FAILCLOSED_RE.search(raw or "") else 0', '        code = 0')
m("H4-37", HK, FR, "_k sem NFC (só casefold)", '    return unicodedata.normalize("NFC", unicodedata.normalize("NFC", p).casefold())', '    return p.casefold()')
m("H4-38", HK, LD, "_ws_abaixo olha só o 1º filho", '            for n in sorted(os.listdir(p))[:500]:', '            for n in sorted(os.listdir(p))[:1]:')
m("H4-39", HK, FR, "interpretador python* fora de INTERPRETERS (só pelo nome exato)", '        if exe in INTERPRETERS or exe.startswith("python"):\n            # `python3 -c', '        if exe in INTERPRETERS:\n            # `python3 -c')
m("H4-40", HK, FR, "find -delete não é destrutivo (via _find_destroi)", '        if t == "-delete":\n            return True', '        if False:\n            return True')

# ============================================================================================ co_portao.py
for i, (fn, v) in enumerate([
        ("problemas_ledger", "[]"), ("ler_ledger_conferido", "ler_ledger(ws)"), ("hash_do_motor", "None"),
        ("problemas_territorio_registrado", "[]"), ("_reprova_g3", "r3"), ("problema_manifest", "None"),
        ("contar_oraculo", "(999, 999)"), ("_conta_py", "(1, 1)"), ("problema_waiver", "None"),
        ("g7_checks_provam_efeito", '_res("G7", "PASS", 0, "", "ok", None)'),
        ("_nao_implementado.f", '_res(gid, "PASS", 0, "", "ok", None)'),
        ("_eventos_do_canal", '({"run": 1, "failures": 0, "errors": 0, "skipped": 0, "expected_failures": 0, '
                              '"unexpected_successes": 0}, None)'),
        ("plano_suite", "[]"), ("_runner_python", "None"), ("_tokens_suite", "[]"), ("coletar_diff", "Diff([], [])"),
        ("glob_re", 're.compile(".*")'), ("casa", "True"), ("_protegidos_rel", "[]"), ("_gaming_por_alias", "None"),
        ("_aliases_gaming", "(set(), set())"),
        ("avaliar_diff", '[_res("G3", "PASS", 0, "diff", "ok", None), _res("G4", "PASS", 0, "diff", "ok", None)]'),
        ("_g_diff_portao", '_res(gid, "PASS", 0, "diff", "ok", None)'), ("cmd_portao", "0"), ("cmd_veredito", "0"),
        ("cmd_diff", "0"), ("selftest", "True"), ("main", "0"), ("veredito", '"GO"'), ("_parse_only", "None"),
        ("sistema_hash", '"0" * 64'), ("ler_regressao", '{"schema_version": 1, "itens": []}')], 1):
    rc("P4-R%02d" % i, PO, fn, v)

m("P4-01", PO, G1T, "G1 aceita '<N> passed' impresso quando o canal falha",
  '    tot, erro = _eventos_do_canal(linhas, mod)\n',
  '    tot, erro = _eventos_do_canal(linhas, mod)\n    _m = re.search(r"(\\d+) passed", out)\n    if erro and _m and rc == 0:\n'
  '        tot, erro = {"run": int(_m.group(1)), "failures": 0, "errors": 0, "skipped": 0}, None\n')
m("P4-02", PO, G1T, "G1: runner desconhecido passa se imprimir 'Ran N tests'/'N passed'",
  '    except SuiteNaoEstruturada as e:\n        return "FAIL", None, "%s: %s" % (nome, e)',
  '    except SuiteNaoEstruturada as e:\n        _p = subprocess.run(cmd, shell=True, cwd=cwd if cwd and os.path.isdir(cwd) else None, '
  'stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)\n'
  '        if _p.returncode == 0 and re.search(r"Ran [1-9]\\d* tests?|[1-9]\\d* passed", _p.stdout):\n'
  '            return "PASS", 0, "%s: texto impresso" % nome\n        return "FAIL", None, "%s: %s" % (nome, e)')
m("P4-03", PO, G1T, "G1: canal incompleto aceito se a saída termina em OK",
  '    if erro:\n        return None, rc, out, "%s: %s" % (mod, erro)\n',
  '    if erro and rc == 0 and re.search(r"(?m)^OK\\b", out):\n        tot, erro = {"run": 1, "failures": 0, "errors": 0, "skipped": 0}, None\n'
  '    if erro:\n        return None, rc, out, "%s: %s" % (mod, erro)\n')
m("P4-04", PO, FR, "canal: fim duplicado/fora de ordem aceito",
  '    if len(fim) > 1 or [x for x in linhas[-1:] if json.loads(x.decode("utf-8")).get("ev") != "fim"]:', '    if False:')
m("P4-05", PO, FR, "canal: teste iniciado sem resultado aceito", '    if sem_res:\n        return None, "teste iniciado', '    if False:\n        return None, "teste iniciado')
m("P4-06", PO, FR, "canal: contagem do runner ≠ iniciados aceita", '        if fim[0].get("run") != len(inicios):', '        if False:')
m("P4-07", PO, CI, "canal: skip não conta como pulado", '"skipped": cont.get("skip", 0),', '"skipped": 0,')
m("P4-08", PO, FR, "_uma_suite ignora exit ≠ 0 do runner", '            if rc != 0:\n                return "FAIL", rc, "%s: exit %s; relatório', '            if False:\n                return "FAIL", rc, "%s: exit %s; relatório')
m("P4-09", PO, FR, "_uma_suite ignora errors/xpass", '    if tot["failures"] or tot["errors"] or tot["unexpected_successes"]:', '    if tot["failures"]:')
m("P4-10", PO, FR, "suíte aceita `||` como separador", '_SEPARADORES = ("&&", ";")', '_SEPARADORES = ("&&", ";", "||")')
m("P4-11", PO, LD, "`cd` com argumentos extras aceito", '            if len(toks) != 2:', '            if len(toks) < 2:')
m("P4-12", PO, PT, "G1 agrega por PASS (uma suíte verde basta)",
  '    st = "ERRO" if "ERRO" in piores else "FAIL" if "FAIL" in piores else "PASS"',
  '    st = "PASS" if "PASS" in piores else "ERRO" if "ERRO" in piores else "FAIL"')
m("P4-13", PO, CI, "G1 sem suíte declarada passa", '        return _res("G1", "FAIL", None, cmd, "nenhuma suíte declarada', '        return _res("G1", "PASS", 0, cmd, "nenhuma suíte declarada')
m("P4-14", PO, FR, "G0 não confere o MANIFEST", '    prob_man = problema_manifest(ws, recs, c)', '    prob_man = None')
m("P4-15", PO, FR, "G0 aceita 0 testes/asserções se o congelado também é 0", ' or nt < 1 or na < 1:\n        return _res("G0", "FAIL"', ':\n        return _res("G0", "FAIL"')
m("P4-16", PO, CI, "G0: oracle verify exit 1 passa", '    if p.returncode != 0:\n        return _res("G0"', '    if p.returncode not in (0, 1):\n        return _res("G0"')
m("P4-17", PO, CI, "problema_manifest: gravado not in → in", ' or gravado not in atuais:', ' or gravado in atuais:')
m("P4-18", PO, FR, "G3 ignora caminhos fora de writes", '    fora = [p for p in diff.paths if not casa(p, writes)]', '    fora = []')
m("P4-19", PO, FR, "plano_aprovado aceita aprovação anterior ao plano_ok", ' and r.get("seq", 0) > desde and pl.get("portao") == "plano"', ' and r.get("seq", 0) > 0 and pl.get("portao") == "plano"')
m("P4-20", PO, FR, "plano_aprovado aceita aprovação sem audit", ' and (pl.get("arquivo") or "seq %s" % r.get("seq")) not in sujas:', ':')
m("P4-21", PO, FR, "divergencias_registradas não confere obra.json5", '    alvos = (("obra", "premissas_ok", "obra_hash", "obra.json5"),\n             ', '    alvos = (')
m("P4-22", PO, HD, "hash_do_motor aceita valor malformado",
  '    return v if isinstance(v, str) and _HEX64.match(v) else None\n\n\ndef divergencias_registradas', '    return v\n\n\ndef divergencias_registradas')
m("P4-23", PO, LD, "glob_re: * atravessa diretórios", '            out += "[^/]*"', '            out += ".*"')
m("P4-24", PO, FR, "G4 sem literais do held-out", '        for lit in literais:', '        for lit in ():')
m("P4-25", PO, FR, "G4 sem config de teste em setup.cfg/pyproject", '        if os.path.basename(path) in cfg and _CFG_TESTE.search(ln):', '        if False:')
m("P4-26", PO, FR, "G4 sem except:/pass em duas linhas", '        if _PASS.match(ln) and _EXCEPT.match(prev.get(path, "")):', '        if False:')
m("P4-27", PO, FR, "G4 sem toque no oráculo", '        if casa(p, ["oraculo/**", "**/oraculo/**"]):', '        if False:')
m("P4-28", PO, FR, "G4 sem __eq__", '    ("__eq__ novo", re.compile(r"\\bdef\\s+__(?:eq|ne)__\\s*\\(|\\b__(?:eq|ne)__\\s*=")),\n', '')
m("P4-29", PO, FR, "G4 sem monkeypatch de avaliador", '    ("monkeypatch de avaliador", re.compile(', '    ("monkeypatch de avaliador", (lambda *a: re.compile("(?!x)x"))(')
m("P4-30", PO, FR, "G4: test_*.py/ *_test.py fora de tests/ não é teste", '"**/test_*.py", "**/*_test.py", ', '')
m("P4-31", PO, FR, "rodar não acusa ledger adulterado", '    extra += ["ledger: %s" % p for p in problemas_ledger(ws, recs)]', '    pass')
m("P4-32", PO, FR, "rodar ignora medição simulada (GO em vez de GO (simulado))", '    simulado = _simulado(recs)\n    v, motivo, _f, _w = calcular_veredito(itens', '    simulado = False\n    v, motivo, _f, _w = calcular_veredito(itens')
m("P4-33", PO, WV, "waiver aceito em item cujo regressao.json5 não admite waiver",
  '        sem_waiver = (not it.get("waiver")) or gid in SEM_WAIVER_NUCLEO', '        sem_waiver = gid in SEM_WAIVER_NUCLEO')
m("P4-34", PO, WV, "waiver: portão do evento não conferido", ' or pl.get("portao") != doc["portao"] or \\\n', ' or \\\n')
m("P4-35", PO, WV, "waiver: decisão ≠ aprovado aceita", '    if doc.get("decisao") != "aprovado":\n        return "aprovação com decisão', '    if False:\n        return "aprovação com decisão')
m("P4-36", PO, WV, "waiver: evento cita outro arquivo aceito", '    if not isinstance(arq, str) or os.path.realpath(arq) != real:', '    if False:')
m("P4-37", PO, WV, "waiver: linha de audit não exigida", '    if arq in set(sujas) or "seq %s" % sq in set(sujas):', '    if False:')
m("P4-38", PO, WV, "waiver: aprovar-<portao>.* aceito", ' or os.path.basename(real).startswith("aprovar-"):', ':')
m("P4-39", PO, HD, "veredito não confere gate_report_hash", '        if gravado != h_rep:', '        if False:')
m("P4-40", PO, FR, "veredito aceita relatório sem portao_relatorio", '    if ult is None:\n        extra.append(', '    if False:\n        extra.append(')
m("P4-41", PO, PT, "calcular_veredito: PASS vence 'fora da regressão'",
  '        st = r.get("status")\n        if it is None:', '        st = r.get("status")\n        if st == "PASS":\n            continue\n        if it is None:')
m("P4-42", PO, CI, "portao run --only sai 0 mesmo com NO-GO parcial", '        return 1 if rep["veredito_parcial"] == "NO-GO" else 0', '        return 0')
m("P4-43", PO, FR, "writes amplos: glob vazio não conta", '    return [g for g in writes if not str(g).strip() or any(', '    return [g for g in writes if any(')
m("P4-44", PO, FR, "protegidos: ws na raiz do repo não protegido", '    if w == r or w.startswith(r + os.sep):', '    if w.startswith(r + os.sep):')
m("P4-45", PO, FR, "diff ignora o índice (--cached) nos caminhos",
  '    for extra in ([], ["--cached"]):\n        code, out, err = _git(repo, "diff", "--no-ext-diff", "--name-status"',
  '    for extra in ([],):\n        code, out, err = _git(repo, "diff", "--no-ext-diff", "--name-status"')
m("P4-46", PO, FR, "rename: caminho de origem esquecido", '                paths.update(toks[i + 1:i + 3])', '                paths.add(toks[i + 2])')
m("P4-47", PO, FR, "untracked: linhas adicionadas não entram no G4", '                    adic.extend((p, x) for x in data.decode("utf-8", "replace").splitlines())', '                    pass')

# ============================================================================================ PARTE B
# Sobreviventes de M3 (A e B). `r3` = id original; texto old/new do r3 quando ainda aplica, senão adaptado.
B_ADAPT = {
    "P01": dict(arquivo=PO, tipo=G1T, descricao="G1 aceita texto impresso `Ran N tests` quando o runner não grava relatório "
                "(adaptado: canal de eventos com erro + 'Ran N tests' e exit 0 ⇒ conta)",
                subs=[('    tot, erro = _eventos_do_canal(linhas, mod)\n',
                       '    tot, erro = _eventos_do_canal(linhas, mod)\n    _m = re.search(r"Ran (\\d+) tests?", out)\n'
                       '    if erro and _m and rc == 0:\n        tot, erro = {"run": int(_m.group(1)), "failures": 0, "errors": 0, '
                       '"skipped": 0}, None\n', 1)]),
    "P02": dict(arquivo=PO, tipo="feature_removida", descricao="G1 não confere nonce do relatório (adaptado ao relatório privado)",
                subs=[('        if d.get("nonce") != nonce or d.get("runner") != mod or not d.get("completo"):',
                       '        if d.get("runner") != mod or not d.get("completo"):', 1)]),
    "P08": dict(arquivo=PO, tipo=WV, descricao="waiver aceita aprovação fora de <ws>/aprovacoes (adaptado: problema_waiver)",
                subs=[('    if not real.startswith(raiz):\n        return "aprovação fora', '    if False:\n        return "aprovação fora', 1)]),
    "P14": dict(arquivo=PO, tipo="feature_removida", descricao="rodar: divergência registrada não força NO-GO (adaptado)",
                subs=[('    extra = [div[k] for k in ("regressao", "obra", "plano") if k in div]\n    extra += ["ledger',
                       '    extra = []\n    extra += ["ledger', 1)]),
    "P26": dict(arquivo=PO, tipo="feature_removida", descricao="G1 não soma failures (adaptado: _ler_junit não existe mais; "
                "_eventos_do_canal zera failures)",
                subs=[('"failures": cont.get("fail", 0),', '"failures": 0,', 1)]),
    "B-E18": dict(arquivo=ES, tipo=PT, descricao="atomos do chamador sobrepõem aprovacao_humana (adaptado: Contexto._computar)",
                  subs=[('        if nome == "aprovacao_humana":\n            return self.humano',
                         '        if nome == "aprovacao_humana":\n            return bool(self.atomos.get("aprovacao_humana", self.humano))', 1)]),
}
