"""test_gerado.py — runner unittest do oráculo GERADO da onda 1. Carrega a tabela de gerar.py (gerada em tempo de
execução a partir dos references) e cria um subTest por linha (nome legível: item — caso), cada linha num
workspace temporário novo. Oráculo O1-gerado; só stdlib; Python 3.9+.

Rodar: python3 -m unittest discover -s tests/onda1/gerado -t tests/onda1/gerado
Filtrar: GERADO_CATS=ab (categorias) e/ou GERADO_IDS=A-0001,B-0190 (ids). GERADO_RESULTADOS=<arquivo.json> grava
o resultado por linha (id, nome, ok, erro).
"""
import atexit
import json
import os
import shutil
import subprocess
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
ONDA1 = os.path.dirname(AQUI)
for _p in (AQUI, ONDA1):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import gerar  # noqa: E402
import motor as m  # noqa: E402
from _comum import (AC, CABECALHO_RETOMAR, CO, REAL_SKILLS, SKILL, Ledger, acmod, git, json5_load, now_ts,  # noqa: E402
                    py_call, rec_hash, run_tty, sha_file, sha_obj)
from test_c_portao import sistema_hash_real, waiver_aprovado  # noqa: E402
from test_r2_achados import R2Base  # noqa: E402

TABELA, FALHAS_GERADOR, _NC = gerar.construir()
_CATS = os.environ.get("GERADO_CATS")
_IDS = set(x for x in os.environ.get("GERADO_IDS", "").split(",") if x)
RESULTADOS = []


def _gravar_resultados():
    dst = os.environ.get("GERADO_RESULTADOS")
    if dst:
        with open(dst, "w", encoding="utf-8") as fh:
            json.dump(RESULTADOS, fh, ensure_ascii=False, indent=1)


atexit.register(_gravar_resultados)


def linhas(cat):
    out = [r for r in TABELA if r["cat"] == cat]
    if _CATS and cat not in _CATS:
        return []
    if _IDS:
        out = [r for r in out if r["id"] in _IDS]
    return out


# ====================================================================== base

PLANO_BASE = {
    "schema_version": 1, "rodada": 1, "decisoes": [], "contrato": {}, "parada": "pass^3",
    "tasks": [
        {"id": "T-01", "titulo": "núcleo", "writes": ["src/**"], "deps": [], "cenarios": ["C-01"],
         "construtor": "builder-A", "criterio": "C-01 vermelho→verde"},
        {"id": "T-02", "titulo": "docs", "writes": ["docs/**"], "deps": [], "cenarios": ["C-01"],
         "construtor": "builder-B", "criterio": "C-01 vermelho→verde"}]}


class GBase(R2Base):
    """Workspace novo por linha: alvo git (src/, tests/, README), obra cli via init, caso held-out (de
    PortaoBase/R2Base) e PLANO VÁLIDO: T-01 (src/**) e T-02 (docs/**) disjuntos — a fixture antiga tinha T-02 com
    `**`, que sobrepõe T-01 e torna plano_valido falso por construção."""

    def setUp(self):
        super().setUp()
        self.write_json(os.path.join(self.ws, "PLANO.json5"), json.loads(json.dumps(PLANO_BASE)))
        self.base_task, self.rej_igual, self.rel_vermelho_verde = "LOTE", False, True

    def fresh(self):
        self.tearDown()
        self.setUp()

    def rodar_tabela(self, cat, fn):
        rows = linhas(cat)
        for r in rows:
            with self.subTest(msg="%s %s" % (r["id"], r["nome"])):
                self.fresh()
                try:
                    fn(r)
                except BaseException as e:  # noqa: BLE001
                    RESULTADOS.append({"id": r["id"], "nome": r["nome"], "ok": False,
                                       "erro": ("%s: %s" % (type(e).__name__, e))[:1500]})
                    raise
                RESULTADOS.append({"id": r["id"], "nome": r["nome"], "ok": True})

    # ------------------------------------------------------------ util
    def sem_traceback(self, *txts):
        for t in txts:
            self.assertNotIn("Traceback", t or "", (t or "")[-1500:])

    def payload_file(self, payload):
        p = os.path.join(self.tmp, "payload-%d.json" % len(os.listdir(self.tmp)))
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        return p

    def st_json(self):
        code, out, err = self.co("status", "--json")
        self.sem_traceback(out, err)
        self.assertEqual(code, 0, "status falhou: " + out[-500:] + err[-800:])
        return json.loads(out)

    def audit_raw(self):
        if not os.path.isfile(self.audit):
            return b""
        with open(self.audit, "rb") as fh:
            return fh.read()

    def aprovacoes_ls(self):
        d = os.path.join(self.ws, "aprovacoes")
        return sorted(os.listdir(d)) if os.path.isdir(d) else []

    def audit_aprovacao(self, rec):
        os.makedirs(os.path.dirname(self.audit), exist_ok=True)
        pl = rec["payload"]
        with open(self.audit, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": rec["ts"], "tipo": "aprovacao", "cmd": "aprovar", "name": pl["portao"],
                                 "decision": pl["decisao"], "by": "humano", "work": self.ws, "user": "teste",
                                 "tty": "/dev/ttys000", "seq": rec["seq"], "hash_estado": pl["hash_estado"]}) + "\n")

    def relatorio_frente(self, task, chave, vermelho_verde=True):
        """Relatório da frente REAL (formatos.relatorio_frente), gravado em rodadas/<N>/relatorios/<task>-<n>.json."""
        n = chave.rsplit("/", 1)[-1]
        rel = {"task": task, "chave": chave, "agent_type": "builder-A", "resultado": "concluido",
               "files_changed": ["src/core.py"],
               "testes": [{"cmd": "python3 -m unittest", "cenario": "C-01", "exit_antes": 1 if vermelho_verde else 0,
                           "exit_depois": 0}],
               "checks_run": [{"cmd": "python3 -m unittest", "exit": 0}], "evidencia_nivel": "E2",
               "contornos_manuais": [], "riscos": [], "handoff": "ok", "base_sha": None, "diff_hash": None}
        return self.write_json(os.path.join(self.ws, "rodadas", "1", "relatorios", "%s-%s.json" % (task, n)), rel)

    def hash_entradas(self, tid):
        code, out, err = py_call(self.env, "import co_estado\nprint(co_estado.hash_entradas_task(%r, "
                                           "co_estado.fold(%r), %r))" % (self.ws, self.ws, tid))
        self.assertEqual(code, 0, out + err)
        return out.strip().splitlines()[-1]

    def escrever_passos(self, passos):
        L = self.L
        for p in passos:
            if p["k"] == "op" and p["evento"] == "retornou":
                pl = dict(p["payload"])
                arq = self.relatorio_frente(pl["task"], p["chave"], self.rel_vermelho_verde)
                pl.update(relatorio=arq, relatorio_hash=sha_file(arq))
                L.append("retornou", payload=pl, chave=p.get("chave"))
            elif p["k"] == "op":
                L.append(p["evento"], payload=p["payload"], chave=p.get("chave"))
            elif p["k"] == "h":
                L.humano(p["portao"], p["evento"], p["para"])
                ap = [x for x in L.records() if x["evento"] == "aprovacao"][-1]
                self.audit_aprovacao(ap)
            else:
                pl = p["payload"]
                if p["evento"] == "task.verificada" and p["para"] == "ACEITA" and p.get("task") == m.TASK_ID:
                    pl = dict(pl, hash_entradas=self.hash_entradas(m.TASK_ID))  # o motor grava no aceite
                L.append(p["evento"], ator=p["ator"], nivel=p["nivel"], de=p["de"], para=p["para"],
                         task=p.get("task"), chave=p.get("chave"), payload=pl)

    def despachar_vago(self, n0, n):
        for i in range(n0, n):
            ch = "obra/1/-/V%d" % i
            self.L.append("despachada", chave=ch, payload={
                "task": None, "papel": "verificador", "chave": ch, "agent_type": "verificador-V", "writes": [],
                "reads": [], "tentativa": 1, "brief_hash": "9" * 64, "isolation": None, "teto_vigente": 5,
                "vivos_antes": i})

    def task_extra(self, ate):
        tid = "T-09"
        self.escrever_passos([m.tt("task.pronta", "PENDENTE", "PRONTA", "script", task=tid)])
        if ate in ("EM_VOO", "RETORNADA"):
            self.escrever_passos(m.ciclo_task(1, tid, fim=ate))

    def relatorio(self, veredito="GO", final=True, only=None, mudancas=None, tirar=(), evento=True):
        if not os.path.isfile(os.path.join(self.ws, "regressao.json5")):
            self.gerar_regressao()
        reg = json5_load(os.path.join(self.ws, "regressao.json5"))
        itens = []
        for it in reg["itens"]:
            if it["id"] in tirar or (only and it["id"] not in only):
                continue
            st = "PASS" if it["aplica"] else "NA"
            r = {"id": it["id"], "status": st, "exit": 0 if st == "PASS" else None, "cmd": it["cmd"],
                 "evidencia": "ok", "motivo": None if st == "PASS" else it["na_motivo"], "aprovacao": None}
            r.update((mudancas or {}).get(it["id"], {}))
            itens.append(r)
        rep = {"schema_version": 1, "ts": now_ts(), "seq_ledger": self.L.last()["seq"], "final": final,
               "only": only, "sistema_hash": sistema_hash_real(self),  # rodada 2: veredito confere com o alvo
               "regressao_hash": sha_file(os.path.join(self.ws, "regressao.json5")), "itens": itens,
               "veredito": veredito}
        p = self.write_json(os.path.join(self.ws, "gate-report.json"), rep)
        if evento:
            self.L.append("portao_relatorio", payload={"gate_report_hash": sha_file(p), "veredito": veredito,
                                                        "final": final})
        return p

    def medicao(self, k=3, final=True, simulated=False, pass_hat=1.0):
        self.L.append("medicao_registrada", payload={
            "config": "sistema", "k": k, "final": final, "run_ids": ["sistema-r1-%d" % i for i in range(1, k + 1)],
            # sistema_hash da medição NÃO entra no veredito (só no átomo de medição): fica fictício de propósito
            "sistema_hash": "d" * 64, "seq_ultimo_merge": None, "pass_at_k": 1.0, "pass_hat_k": pass_hat,
            "rotulo": "final" if final else "indício", "simulated": simulated})

    def preparar_freeze(self):
        """Pré-condições reais de `aprovar oraculo` (A9): MANIFEST, arquivo de oráculo, campanha-mãe do ac.py."""
        dev = os.path.join(self.ws, "oraculo", "dev")
        os.makedirs(dev, exist_ok=True)
        self.oraculo_arq = os.path.join(dev, "test_o.py")
        with open(self.oraculo_arq, "w") as fh:
            fh.write("import unittest\n\n\nclass O(unittest.TestCase):\n    def test_a(self):\n"
                     "        self.assertEqual(1, 1)\n        self.assertTrue(1)\n\n    def test_b(self):\n"
                     "        self.assertIn(1, [1])\n")
        self.write_json(os.path.join(self.ws, "oraculo", "MANIFEST.json5"), {
            "schema_version": 1, "frentes": {"T-01": {"autores": ["oraculo-O1"], "dev": ["oraculo/dev/**"],
                                                      "heldout": ["oraculo/heldout/**"]}},
            "construtores": {}, "congelado": None})
        camp = os.path.join(self.ws, "campanhas", "construcao")
        p = subprocess.run([sys.executable, AC, "--work", camp, "init", "--target", self.alvo, "--scope", "src/**",
                            "--problem", "p", "--stop", "s", "--max-rounds", "3"], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True, env=self.env, timeout=60)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.camp = camp

    def congelar_real(self):
        """Obra real até AH[oraculo] e `aprovar oraculo` no pty ⇒ oraculo_congelado gravado pelo produto."""
        self.escrever_passos(m.rota_obra("AH:oraculo"))
        self.preparar_freeze()
        self.assertEqual(self.co("ev", "nota", "--texto", "sync")[0], 0)
        code, out, ch = run_tty(["--work", self.ws, "aprovar", "oraculo", "--decisao", "aprovado"], self.env)
        self.assertEqual(code, 0, out[-1500:])
        self.assertIn("oraculo_congelado", [r["evento"] for r in self.L.records()])
        self.gerar_regressao()

    def portao_item(self, gid, *extra):
        code, out, err = self.co("portao", "run", "--only", gid, *extra)
        self.sem_traceback(out, err)
        with open(os.path.join(self.ws, "gate-report.json")) as fh:
            rep = json.load(fh)
        return code, {i["id"]: i for i in rep["itens"]}.get(gid, {}), out + err

    def veredito_cli(self):
        code, out, err = self.co("veredito", "--json")
        self.sem_traceback(out, err)
        try:
            v = json.loads(out)
        except ValueError:
            v = {"veredito": None, "raw": out + err}
        return code, v


# ====================================================================== (a)(b)(c) máquina

class MaquinaBase(GBase):
    # ------------------------------------------------------------ evidências (V/F por artefato real; nunca injeção)
    def editar_plano(self, fn):
        p = os.path.join(self.ws, "PLANO.json5")
        pl = json5_load(p)
        fn(pl)
        self.write_json(p, pl)

    def aplicar_pre(self, r):
        ev = r["evid"]
        obra_p = os.path.join(self.ws, "obra.json5")
        if ev.get("workspace_fora_do_alvo") is False:
            self.set_obra(alvo=self.tmp)
        if ev.get("stop_numerico") is False:
            o = json5_load(obra_p)
            self.set_obra(stop={"texto": o["stop"]["texto"], "numerico": None})
        if ev.get("tipo_exige_baseline") is True:
            self.set_obra(tipo="skill")
        if ev.get("orcamento_esgotado") is True or ev.get("orcamento_restante") is False:
            self.set_obra(max_horas=1e-9)
        if ev.get("pontos_completos") is True:
            self.write_json(os.path.join(self.ws, "pontos.json5"), {"schema_version": 1, "pontos": [
                {"id": "P-01", "texto": "soma dois inteiros", "origem": "pedido", "status": "aberto",
                 "cenarios": [], "motivo": "a cobrir"}]})
        elif ev.get("pontos_completos") is False:
            self.write_json(os.path.join(self.ws, "pontos.json5"), {"schema_version": 1, "pontos": []})
        if "pontos_atualizados" in ev or "pontos_cobertos" in ev:
            rodada = (r.get("contadores_antes") or {}).get("rodada", 0) + 1
            pt = {"id": "P-01", "texto": "soma dois inteiros", "origem": "pedido", "status": "aberto",
                  "cenarios": ["C-01"] if ev.get("pontos_cobertos", True) else ["C-99"], "motivo": None}
            if ev.get("pontos_atualizados", True):
                pt["historico"] = [{"rodada": rodada, "status": "aberto", "motivo": None}]
            self.write_json(os.path.join(self.ws, "pontos.json5"), {"schema_version": 1, "pontos": [pt]})

        def plano(pl):
            t1 = [t for t in pl["tasks"] if t["id"] == "T-01"][0]
            t2 = [t for t in pl["tasks"] if t["id"] == "T-02"][0]
            if "ha_decisoes" in ev:
                pl["decisoes"] = [{"id": "DEC-1", "texto": "formato", "opcoes": ["a", "b"], "recomendacao": "a"}] \
                    if ev["ha_decisoes"] else []
            if ev.get("plano_valido") is False:
                t2["writes"] = ["src/**"]
            if ev.get("brief_valido") is False:
                del t1["criterio"]
            if ev.get("deps_aceitas") is False:
                t1["deps"] = ["T-02"]
            if ev.get("obra_replanejou") is True:
                pl["tasks"] = [t2]
        self.editar_plano(plano)
        if ev.get("obra_replanejou") is True:
            self.base_task = "REPLANEJAR+"
        if ev.get("mesma_rejeicao_2x") is True and r["nivel"] == "task":
            self.rej_igual = True

    def vivo_de(self, task, writes, papel="construtor", agent="builder-Z", isolation=None, chave=None):
        ch = chave or "obra/1/%s/v%d" % (task or "-", len(self.L.records()))
        self.L.append("despachada", chave=ch, payload={
            "task": task, "papel": papel, "chave": ch, "agent_type": agent, "writes": writes, "reads": [],
            "tentativa": 1, "brief_hash": "9" * 64, "isolation": isolation, "teto_vigente": 5, "vivos_antes": 0})
        return ch

    def hash_alvo(self):
        files = []
        for raiz, dirs, arqs in os.walk(self.alvo):
            dirs[:] = sorted(d for d in dirs if d not in (".git", "__pycache__"))
            files += [os.path.join(raiz, a) for a in arqs if not a.endswith(".pyc")]
        return acmod().sha_files(sorted(files))

    def run_json(self, rid, cfg, **campos):
        d = {"schema_version": 1, "id": rid, "rodada": 1, "config": cfg, "i": 1, "final": False, "simulated": False,
             "sistema_hash_inicio": "d" * 64, "sistema_hash_fim": "d" * 64, "oraculo_hash": "f" * 64,
             "seq_ultimo_merge": None, "seq_registro": 1, "copia_limpa": True, "itens": [],
             "quality": {"passed": 1, "total": 2}, "structure": {"passed": 0, "total": 0}, "tokens": None,
             "minutos": 0.1, "ts": now_ts()}
        d.update(campos)
        self.write_json(os.path.join(self.ws, "rodadas", "1", "runs", rid, "run.json"), d)

    def campanha(self, nome="C-01", congelar=True):
        d = os.path.join(self.ws, "campanhas", nome)
        p = subprocess.run([sys.executable, AC, "--work", d, "init", "--target", self.alvo, "--scope", "docs/**",
                            "--problem", "p", "--stop", "s", "--max-rounds", "3"], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True, env=self.env, timeout=60)
        self.assertEqual(p.returncode, 0, p.stdout)
        arq = os.path.join(self.tmp, "oraculo-%s" % nome, "test_c.py")
        os.makedirs(os.path.dirname(arq), exist_ok=True)
        with open(arq, "w") as fh:
            fh.write("import unittest\n\n\nclass C(unittest.TestCase):\n    def test_c(self):\n"
                     "        self.assertEqual(1, 1)\n")
        if congelar:
            p = subprocess.run([sys.executable, AC, "--work", d, "oracle", "freeze", "--file", arq],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
                               env=self.env, timeout=60)
            self.assertEqual(p.returncode, 0, p.stdout)
        stp = os.path.join(d, ".auto-correcao", "state.json")
        with open(stp) as fh:
            st = json.load(fh)
        rdir = os.path.join(d, ".auto-correcao", "rounds", str(st.get("round", 0)))
        os.makedirs(rdir, exist_ok=True)
        return stp, rdir, arq

    def aplicar_pos(self, r):
        ev, nivel, L = r["evid"], r["nivel"], self.L
        if ev.get("hook_vivo") is True:
            self.grava_hook_vivo()
        if r["evento"] == "lote_ok":
            self.escrever_passos([m.tt("task.pronta", "PENDENTE", "PRONTA", "script")])  # o lote a julgar
        if ev.get("lote_disjunto") is False or ev.get("writes_disjuntos_dos_vivos") is False:
            self.vivo_de("T-09", ["src/**"])
        if ev.get("colisao_vazia") is False:
            self.vivo_de(None, ["docs/**"], papel="campanha")
        if ev.get("sem_perdidas_pendentes") is False:
            self.despachar_vago(0, 1)
        if ev.get("resultado_no_worktree") is True:
            ch = self.st_json()["tasks"][m.TASK_ID]["chave"]
            self.vivo_de(m.TASK_ID, ["src/**"], agent="builder-A", isolation="worktree", chave=ch)
            L.append("colhida", chave=ch, payload={"task": m.TASK_ID, "chave": ch, "worktree": self.tmp,
                                                   "diff_hash": "6" * 64})
        for a in ("lote_cabe_no_teto", "vivos_abaixo_do_teto"):
            if a in ev:
                st = self.st_json()
                alvo = st["teto_vigente"] - (1 if ev[a] else 0)
                self.despachar_vago(len(st["vivos"]), alvo)
        if ev.get("nenhuma_em_voo") is False:
            self.task_extra("EM_VOO")
        if "todas_tasks_retornadas_ou_aceitas" in ev:
            self.task_extra("RETORNADA" if ev["todas_tasks_retornadas_ou_aceitas"] else "PRONTA")
        if ev.get("mesma_rejeicao_2x") is True and nivel == "obra":
            tid = "T-09"
            passos = [m.tt("task.pronta", "PENDENTE", "PRONTA", "script", task=tid)]
            for n in (1, 2):
                passos += m.ciclo_task(n, tid) + [m._verif(False, tid, "mesmo motivo")]
                if n == 1:
                    passos.append(m.tt("task.retentar", "REJEITADA", "PRONTA", "orquestrador", task=tid))
            self.escrever_passos(passos)
        if ev.get("campanhas_ativas_abaixo_de_2") is False:
            self.escrever_passos([m.T("campanha.ativar", "RASCUNHO", "ATIVA", "script", nivel="campanha", task=c)
                                  for c in ("C-02", "C-03")])
        # gate-report (arquivo) + eventos: integração (travas) e/ou portao_relatorio
        spec = m.spec_relatorio({a: v for a, v in ev.items() if a in m.REL_ATOMOS})
        integra = any(a in ev for a in ("merge_ordenado", "oraculo_apos_cada_merge")) or \
            (r["evento"] == "merge_ok" and "trava_adquirida" in ev)
        rel_p = None
        if spec or integra:
            sp = spec or {"itens": {}}
            mud = {g: {"status": s, "exit": 0 if s == "PASS" else 1} for g, s in sp["itens"].items()}
            ruim = any(s == "FAIL" for s in sp["itens"].values())
            rel_p = self.relatorio(veredito="NO-GO" if ruim else "GO", mudancas=mud, evento=False)

        def ev_rel():
            with open(rel_p, encoding="utf-8") as fh:
                rep = json.load(fh)
            L.append("portao_relatorio", payload={"gate_report_hash": sha_file(rel_p), "veredito": rep["veredito"],
                                                  "final": rep["final"]})
        if integra:
            if ev.get("trava_adquirida") is not False:
                donos = ["T-01", "T-02"] if ev.get("merge_ordenado", True) else ["T-02", "T-01"]
                for i, dono in enumerate(donos):
                    L.append("trava_adquirida", payload={"nome": "integracao", "dono": dono})
                    if ev.get("oraculo_apos_cada_merge", True) or i == len(donos) - 1:
                        ev_rel()
                    if i < len(donos) - 1:
                        L.append("trava_liberada", payload={"nome": "integracao", "dono": dono})
            else:
                ev_rel()
        else:
            if ev.get("trava_adquirida") is True:
                L.append("trava_adquirida", payload={"nome": "integracao", "dono": "T-01"})
            if rel_p:
                ev_rel()
        if ev.get("oraculo_congelado") is True:
            L.append("oraculo_congelado", payload={"hash": "f" * 64, "n_testes": 1, "n_assercoes": 1,
                                                   "manifest_hash": "e" * 64})
        if "baseline_reprodutivel" in ev:
            ids = ["baseline-r1-1", "baseline-r1-2"]
            for i, rid in enumerate(ids):
                q = {"passed": 1, "total": 2} if (ev["baseline_reprodutivel"] or i == 0) else {"passed": 2, "total": 2}
                self.run_json(rid, "baseline", i=i + 1, quality=q)
            self.write_json(os.path.join(self.ws, "baseline.json"), {
                "schema_version": 1, "dispensado": False, "motivo": None, "cmd": "python3 -m unittest", "alvo_hash": None,
                "oraculo_hash": "f" * 64, "k": 2, "run_ids": ids, "pass_at_k": 0.5, "pass_hat_k": 0.5,
                "seq_ledger": L.last()["seq"], "ts": now_ts()})
            L.append("medicao_registrada", payload={"config": "baseline", "k": 2, "final": False, "run_ids": ids,
                                                    "sistema_hash": "d" * 64, "seq_ultimo_merge": None,
                                                    "pass_at_k": 0.5, "pass_hat_k": 0.5, "rotulo": "indício",
                                                    "simulated": False})
        if "pass3_final" in ev:
            self.medicao(k=3, final=True) if ev["pass3_final"] else self.medicao(k=1, final=False)
        if "criterio_parada_ok" in ev:
            self.medicao(k=3, final=True, pass_hat=1.0 if ev["criterio_parada_ok"] else 0.5)
        if any(a in ev for a in ("copia_limpa", "sistema_congelado_na_medicao", "medicao_posterior_ao_merge")):
            h = self.hash_alvo()
            self.run_json("sistema-r1-1", "sistema", copia_limpa=ev.get("copia_limpa", True),
                          sistema_hash_inicio=h,
                          sistema_hash_fim=h if ev.get("sistema_congelado_na_medicao", True) else "0" * 64)
            merges = [x["seq"] for x in L.records() if x["evento"] == "merge_ok" and x["nivel"] == "obra"]
            ult = merges[-1] if merges else None
            L.append("medicao_registrada", payload={
                "config": "sistema", "k": 1, "final": False, "run_ids": ["sistema-r1-1"], "sistema_hash": h,
                "seq_ultimo_merge": ult if ev.get("medicao_posterior_ao_merge", True) else (ult or 1) - 1,
                "pass_at_k": 1.0, "pass_hat_k": 1.0, "rotulo": "indício", "simulated": False})
        if "oscilacao" in ev or "plato_2" in ev:
            if "oscilacao" in ev:
                qs = [(0.2, "indício"), (-0.1 if ev["oscilacao"] else 0.1, "indício")]
            else:
                qs = [(0.0, "sem efeito"), (0.0, "sem efeito")] if ev["plato_2"] else [(0.3, "melhora"), (0.3, "melhora")]
            for n, (d, rot) in enumerate(qs, 1):
                self.write_json(os.path.join(self.ws, "rodadas", str(n), "comparacao.json"), {
                    "schema_version": 1, "rodada": n, "base": "baseline", "com": "sistema", "base_runs": [],
                    "com_runs": [], "k": 1, "final": False, "oraculo_hash": "f" * 64,
                    "Q": {"n_itens": 10, "total_base": 10, "total_com": 10, "taxa_base": 0.2, "taxa_com": 0.2 + d,
                          "delta": d, "ic95": [d - 0.1, d + 0.1], "faixa": "x", "rotulo": rot},
                    "S": {"n_itens": 0, "total_base": 0, "total_com": 0, "taxa_base": 0.0, "taxa_com": 0.0,
                          "delta": 0.0, "ic95": [0.0, 0.0], "faixa": None, "rotulo": "sem efeito"},
                    "bootstrap": {"reamostras": 100, "semente": 7, "cluster": "cenario"}, "pass_hat_3": None,
                    "custo": {"base": {"tokens": None, "minutos": 1.0}, "com": {"tokens": None, "minutos": 1.0}}})
        camp = [a for a in ("oraculo_campanha_congelado", "ac_decisao_parar", "oraculos_fechados_verdes",
                            "colisao_vazia", "defeitos_classificados", "so_sistema_vira_task", "teste_falha_antes")
                if a in ev]
        if camp:
            stp, rdir, arq = self.campanha()
            if ev.get("oraculo_campanha_congelado") is False:
                with open(arq, "a") as fh:
                    fh.write("# alterado depois do freeze\n")
            if "ac_decisao_parar" in ev:
                with open(stp) as fh:
                    sac = json.load(fh)
                sac["decision"] = "parar: critério atingido" if ev["ac_decisao_parar"] else "continuar"
                sac["done"] = dict(sac.get("done") or {}, **{"decisao.1": True})
                with open(stp, "w") as fh:
                    json.dump(sac, fh, indent=1)
            runs = []
            if "oraculos_fechados_verdes" in ev:
                runs.append({"config": "sistema", "simulated": False,
                             "quality": {"passed": 2 if ev["oraculos_fechados_verdes"] else 1, "total": 2}})
            if any(a in ev for a in ("defeitos_classificados", "so_sistema_vira_task", "teste_falha_antes")):
                defeitos = [{"id": "D-1-01", "classe": "sistema", "frente": "F1",
                             "reproduzido": ev.get("teste_falha_antes", True), "evidencia": "C-01 vermelho"},
                            {"id": "D-1-02", "classe": "oraculo", "frente": None, "reproduzido": True,
                             "evidencia": "x"}]
                if ev.get("defeitos_classificados") is False:
                    defeitos.append({"id": "D-1-09", "classe": "xpto", "frente": None})
                self.write_json(os.path.join(rdir, "DEFEITOS.json5"), {"schema_version": 1, "defeitos": defeitos})
                runs.append({"config": "sistema", "simulated": False, "quality": {"passed": 1, "total": 2}})
            frente = {"nome": "F1", "escreve": ["docs/**"], "criterio": "C-01",
                      "defeitos": ["D-1-01"] + (["D-1-02"] if ev.get("so_sistema_vira_task") is False else [])}
            self.write_json(os.path.join(rdir, "PLANO.json5"), {"schema_version": 1, "frentes": [frente]})
            with open(os.path.join(rdir, "runs.jsonl"), "w") as fh:
                for x in runs:
                    fh.write(json.dumps(x) + "\n")
        orac = [a for a in ("autor_fora_dos_construtores", "criterios_classificados", "pontos_cobertos",
                            "vermelho_baseline_e_stub") if a in ev]
        if orac:
            dev = os.path.join(self.ws, "oraculo", "dev")
            os.makedirs(dev, exist_ok=True)
            corpo = "        import core\n        self.assertTrue(hasattr(core, 'multiplica'))\n" \
                if ev.get("vermelho_baseline_e_stub", True) else "        self.assertEqual(1, 1)\n"
            cls = "    # cenario: C-01 ponto: P-01 classe: Q\n" if ev.get("criterios_classificados", True) else ""
            with open(os.path.join(dev, "test_o.py"), "w") as fh:
                fh.write("import unittest\n\n\nclass O(unittest.TestCase):\n%s    def test_c01(self):\n%s"
                         % (cls, corpo))
            autores = ["oraculo-O1"] if ev.get("autor_fora_dos_construtores", True) else ["builder-A"]
            doc = {"schema_version": 1, "frentes": {"T-01": {"autores": autores, "dev": ["oraculo/dev/**"],
                                                             "heldout": ["oraculo/heldout/**"]}},
                   "construtores": {}, "congelado": None}
            self.write_json(os.path.join(self.ws, "oraculo", "MANIFEST.json5"), doc)
            L.append("manifest_gravado", payload={"manifest_hash": sha_obj(doc), "autores": autores})
        if "relatorio_presente" in ev:
            ch = self.st_json()["tasks"][m.TASK_ID]["chave"]
            arq = self.relatorio_frente(m.TASK_ID, ch)
            L.append("retornou", chave=ch, payload={"task": m.TASK_ID, "chave": ch, "relatorio": arq,
                                                     "relatorio_hash": sha_file(arq) if ev["relatorio_presente"]
                                                     else "0" * 64})
        if "verificador_nao_autor" in ev and nivel == "obra":
            self.vivo_de(None, [], papel="verificador",
                         agent="verificador-V" if ev["verificador_nao_autor"] else "builder-A")
        if ev.get("hash_entradas_mudou") is True:
            self.editar_plano(lambda pl: pl["tasks"][0].__setitem__("criterio", "critério novo depois do aceite"))
        if "retomar_md_valido" in ev:
            code, out, err = self.co("ev", "nota", "--texto", "regera RETOMAR.md")
            self.assertEqual(code, 0, out + err)
            if ev["retomar_md_valido"] is False:
                L.append("nota", payload={"texto": "depois do RETOMAR.md"})

    def ler_no(self, st, nivel):
        if nivel == "obra":
            o = st["obra"]
            return [o["estado"], o["portao"], o["retorno"]]
        if nivel == "task":
            return [(st["tasks"].get(m.TASK_ID) or {}).get("estado", "PENDENTE"), None, None]
        return [(st["campanhas"].get(m.CAMP_ID) or {}).get("estado", "RASCUNHO"), None, None]

    def ler_cont(self, st, nivel, esperado):
        if nivel == "obra":
            return {c: st["contadores"].get(c) for c in esperado if c in st["contadores"]}, \
                {c: v for c, v in esperado.items() if c in st["contadores"]}
        ent = (st["tasks"].get(m.TASK_ID) if nivel == "task" else st["campanhas"].get(m.CAMP_ID)) or {}
        ks = ("tentativas", "reaberturas") if nivel == "task" else ("reintegracoes",)
        return {c: ent.get(c, 0) for c in ks}, {c: esperado.get(c, 0) for c in ks}

    def api(self, evento, payload, atomos):
        code, out, err = py_call(self.env, (
            "import co_estado, json\n"
            "try:\n"
            "    r = co_estado.transicionar(%r, %r, json.loads(%r), atomos=json.loads(%r))\n"
            "    print('GRAVOU', r['transicao'])\n"
            "except co_estado.Fail as e:\n"
            "    print('RECUSOU Fail', e)\n"
            "except co_estado.Bad as e:\n"
            "    print('RECUSOU Bad', e)\n") % (self.ws, evento, json.dumps(payload), json.dumps(atomos)))
        self.sem_traceback(out, err)
        return out + err

    def executar(self, r):
        nivel = r["nivel"]
        ret_apos = None
        if r["evid"].get("agora_apos_retomar") is False:
            ret_apos = m.FUTURO
        self.aplicar_pre(r)
        if r.get("modo") == "aprovar" and r.get("portao") == "oraculo" and r.get("decisao") == "aprovado" and \
                r["esperado"].get("grava"):
            self.preparar_freeze()
        self.escrever_passos(m.rota(nivel, r["no"], r.get("cont"), ret_apos, self.base_task, self.rej_igual))
        self.aplicar_pos(r)
        if "no_antes" in r:
            st0 = self.st_json()
            self.assertEqual(self.ler_no(st0, nivel), r["no_antes"],
                             "fold do ledger legítimo diverge da máquina (nó antes)")
            got, exp = self.ler_cont(st0, nivel, r.get("contadores_antes") or {})
            self.assertEqual(got, exp, "fold do ledger legítimo diverge (contadores antes)")
        L = self.L
        antes, n_antes = L.raw(), len(L.records())
        aud0, ap0 = self.audit_raw(), self.aprovacoes_ls()
        modo, esp = r["modo"], r["esperado"]
        if modo == "ev":
            code, out, err = self.co("ev", r["evento"], "--payload", self.payload_file(r["payload"]))
            self.sem_traceback(out, err)
            ok, saida = code == 0, "exit %d: %s" % (code, (out + err)[-1500:])
            if not ok:
                self.assertIn(code, (1, 2), saida)
        elif modo == "api":
            saida = self.api(r["evento"], r["payload"], r["injeta"])
            ok = "GRAVOU" in saida
            self.assertTrue(ok or "RECUSOU" in saida, saida)
        elif modo == "aprovar":
            code, out, ch = run_tty(["--work", self.ws, "aprovar", r["portao"] or "stop", "--decisao",
                                     r["decisao"]], self.env)
            self.sem_traceback(out)
            ok, saida = code == 0, "exit %d: %s" % (code, out[-1500:])
        elif modo == "retomar":
            code, out, err = self.co("retomar")
            self.sem_traceback(out, err)
            ok, saida = code == 0, out + err
        elif modo == "valor":
            code, out, err = py_call(self.env, "import co_estado\nprint('VALOR', co_estado.valor_atomo(%r, %r, "
                                               "evento=%r, task=%r))" % (self.ws, r["atomo"], r["evento"], m.TASK_ID))
            self.sem_traceback(out, err)
            self.assertIn("VALOR %s" % esp["valor"], out, "valor_atomo(%s): %s" % (r["atomo"], out + err))
            return
        elif modo == "sem_canal":
            code, out, err = self.co("ev", r["evento"])
            self.sem_traceback(out, err)
            self.assertEqual(code, 2, "ev %s deveria sair 2 (D9): %s" % (r["evento"], out + err))
            saida = self.api(r["evento"], {}, r["injeta"])
            ok = "GRAVOU" in saida
        else:
            raise AssertionError("modo %s" % modo)
        if not esp["grava"]:
            self.assertFalse(ok, "deveria RECUSAR e gravou: " + saida)
            self.assertEqual(L.raw(), antes, "recusa gravou no ledger")
            if modo == "aprovar":
                self.assertEqual(self.audit_raw(), aud0, "recusa gravou no audit")
                self.assertEqual(self.aprovacoes_ls(), ap0, "recusa gravou arquivo de aprovação")
            return
        self.assertTrue(ok, "deveria GRAVAR %s e recusou: %s" % (esp.get("transicao"), saida))
        novos = L.records()[n_antes:]
        trs = [x for x in novos if x["evento"] == r["evento"] and x["nivel"] != "operacional"]
        self.assertTrue(trs, "nenhum registro %s gravado: %s" % (r["evento"], [x["evento"] for x in novos]))
        tr = trs[-1]
        self.assertEqual((tr["de"], tr["para"], tr["ator"]), (esp["de"], esp["no_depois"][0], esp["ator"]),
                         "registro gravado não é a transição %s" % esp.get("transicao"))
        st = self.st_json()
        self.assertEqual(self.ler_no(st, nivel), esp["no_depois"], "nó depois")
        if esp.get("contadores_depois") is not None:
            got, exp = self.ler_cont(st, nivel, esp["contadores_depois"])
            self.assertEqual(got, exp, "contadores depois")
        with open(os.path.join(self.ws, "RETOMAR.md"), encoding="utf-8") as fh:
            mm = CABECALHO_RETOMAR.search(fh.readline())
        last = L.last()
        self.assertTrue(mm and int(mm.group(1)) == last["seq"] and mm.group(2) == last["hash"],
                        "RETOMAR.md não regenerado no último registro (L03)")
        if modo == "aprovar":
            aps = [x for x in novos if x["evento"] == "aprovacao"]
            self.assertTrue(aps, "aprovar sem registro aprovacao")
            arq = os.path.join(self.ws, "aprovacoes", "%s-%d.json" % (r["portao"], aps[-1]["seq"]))
            self.assertTrue(os.path.isfile(arq), "arquivo de aprovação ausente")
            linhas_aud = [json.loads(x) for x in self.audit_raw().decode().splitlines() if x.strip()]
            self.assertTrue(any(x.get("tipo") == "aprovacao" and x.get("seq") == aps[-1]["seq"]
                                for x in linhas_aud), "audit sem a linha tipo aprovacao")

    def forja(self, r):
        self.escrever_passos(m.rota(r["nivel"], r["no"], {}))
        self.assertEqual(self.co("ev", "nota", "--texto", "sync")[0], 0, "controle: rota legítima aceita")
        f = r["forja"]
        self.L.append(f["evento"], ator=f["ator"], nivel=f["nivel"], de=f["de"], para=f["para"], task=f["task"],
                      payload=m.payload_base(f["nivel"], f["evento"], {}))
        antes = self.L.raw()
        for argv in (("status", "--json"), ("retomar",), ("ev", "nota", "--texto", "x")):
            code, out, err = self.co(*argv)
            self.sem_traceback(out, err)
            self.assertNotEqual(code, 0, "registro com ator errado aceito por %s: %s" % (argv[0], (out + err)[-400:]))
        self.assertEqual(self.L.raw(), antes)


class TestA_Atomos(MaquinaBase):
    def test_atomos(self):
        self.rodar_tabela("a", self.executar)


class TestB_Transicoes(MaquinaBase):
    def test_transicoes(self):
        self.rodar_tabela("b", lambda r: self.forja(r) if r["modo"] == "forja" else self.executar(r))


class TestC_Contadores(MaquinaBase):
    def test_contadores(self):
        self.rodar_tabela("c", self.executar)


# ====================================================================== (d) ledger

def forjar(ws, fn):
    """Adultera com fn(recs) e re-encadeia tudo (seq, payload_hash, prev, hash) exceto `_manter`; alinha o
    ledger_seq/ledger_hash do cache ao novo fim (o adversário cala as testemunhas que pode)."""
    L = Ledger(ws)
    recs = L.records()
    fn(recs)
    prev = "0"
    for i, r in enumerate(recs, 1):
        manter = set(r.pop("_manter", ()))
        if "seq" not in manter:
            r["seq"] = i
        if "payload_hash" not in manter:
            r["payload_hash"] = sha_obj(r["payload"])
        if "prev" not in manter:
            r["prev"] = prev
        if "hash" not in manter:
            r["hash"] = rec_hash(r)
        prev = r["hash"]
    with open(L.path, "w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    cache = os.path.join(ws, ".construcao", "state.json")
    with open(cache) as fh:
        c = json.load(fh)
    c["ledger_seq"], c["ledger_hash"] = recs[-1]["seq"], recs[-1]["hash"]
    with open(cache, "w") as fh:
        json.dump(c, fh, indent=1, sort_keys=True, ensure_ascii=False)


class TestD_Ledger(GBase):
    def achar(self, recs, tipo):
        for i, r in enumerate(recs):
            if tipo == "genese" and r["evento"] == "genese":
                return i
            if tipo == "humano" and r["ator"] == "humano":
                return i
            if tipo == "nota" and r["evento"] == "nota":
                idx = i
            if tipo not in ("genese", "humano", "nota") and r["evento"] == tipo:
                return i
        return idx

    def linha(self, r):
        self.escrever_passos(m.rota_task("EM_VOO"))
        self.assertEqual(self.co("ev", "nota", "--texto", "sync")[0], 0)
        code, out, err = self.co("status", "--json")
        self.assertEqual(code, 0)
        self.assertNotIn("diverg", (out + err).lower(), "controle: cache sincronizado")
        op = r["adulteracao"]

        def fn(recs):
            i = self.achar(recs, r["registro"])
            x = recs[i]
            if op["op"] == "seq_mais1":
                x["seq"] += 1
                x["_manter"] = ["seq"]
            elif op["op"] == "set":
                x[r["campo"]] = op["valor"]
                x["_manter"] = [r["campo"]]
            elif op["op"] == "payload_velho":
                x["payload"] = dict(x["payload"], adulterado=True)
                x["_manter"] = ["payload_hash"]
            elif op["op"] == "payload_recalc":
                x["payload"] = dict(x["payload"], **op["valor"])
        forjar(self.ws, fn)
        antes = self.L.raw()
        if r["deteccao"] == "duro":
            for argv in (("status", "--json"), ("retomar",), ("ev", "nota", "--texto", "x"), ("veredito", "--json")):
                code, out, err = self.co(*argv)
                self.sem_traceback(out, err)
                self.assertNotEqual(code, 0, "%s adulterado aceito por `%s`: %s" % (
                    r["campo"], argv[0], (out + err)[-300:]))
            self.assertEqual(self.L.raw(), antes, "gravou sobre ledger adulterado")
        elif r["deteccao"] == "cache":
            code, out, err = self.co("status", "--json")
            self.sem_traceback(out, err)
            self.assertTrue(code != 0 or "cache" in (out + err).lower() or "diverg" in (out + err).lower(),
                            "adulteração coerente sem aviso de cache ≠ fold: " + err[-300:])
        else:
            code, out, err = self.co("status", "--json")
            self.assertEqual(code, 0, out + err)
            self.assertNotIn("diverg", (out + err).lower())
            self.assertEqual(self.co("retomar")[0], 0)

    def test_ledger(self):
        self.rodar_tabela("d", self.linha)


# ====================================================================== (e) hashes

class TestE_Hashes(GBase):
    def linha(self, r):
        k, adult = r["hash"], r["adulterar"]
        if k == "obra":
            self.ledger_coerente(so_t01=True)
            if adult:
                self.set_obra(pedido="pedido trocado depois de premissas_ok")
            c1, g1, o1 = self.portao_item("G1")
            c3, g3, o3 = self.portao_item("G3")
            if adult:
                self.assertIn(g1.get("status"), ("FAIL", "ERRO"), o1)
                self.assertIn(g3.get("status"), ("FAIL", "ERRO"), o3)
            else:
                self.assertEqual(g1.get("status"), "PASS", o1)
                self.assertEqual(g3.get("status"), "PASS", o3)
        elif k == "plano":
            self.ledger_coerente(so_t01=True)
            if adult:
                p = os.path.join(self.ws, "PLANO.json5")
                pl = json5_load(p)
                pl["tasks"][0]["writes"] = ["**"]
                self.write_json(p, pl)
                self.wfile("README.md", "# fora do território original\n")
                self.commit()
            code, out = self.diff("T-01")
            self.assertEqual(code, 1 if adult else 0, out)
        elif k in ("regressao", "gate_report"):
            self.ledger_coerente(ate="ENTREGA" if k == "gate_report" else "LOTE")
            self.relatorio()
            if adult and k == "regressao":
                p = os.path.join(self.ws, "regressao.json5")
                reg = json5_load(p)
                for it in reg["itens"]:
                    if it["id"] == "G2":
                        it["cmd"] = "true"
                self.write_json(p, reg)
                self.relatorio()
            if adult and k == "gate_report":
                p = os.path.join(self.ws, "gate-report.json")
                with open(p) as fh:
                    rep = json.load(fh)
                rep["itens"][0]["evidencia"] = "trocada depois do evento"
                self.write_json(p, rep)
            code, v = self.veredito_cli()
            self.assertEqual((code, v.get("veredito")), (1, "NO-GO") if adult else (0, "GO"), v)
            if k == "gate_report":
                antes = self.L.raw()
                code, out, _ch = run_tty(["--work", self.ws, "aprovar", "entrega", "--decisao", "aprovado"],
                                         self.env)
                if adult:
                    self.assertNotEqual(code, 0, out[-800:])
                    self.assertEqual(self.L.raw(), antes)
                else:
                    self.assertEqual(code, 0, out[-800:])
        else:
            self.congelar_real()
            if adult:
                if k == "oraculo":
                    with open(self.oraculo_arq) as fh:
                        txt = fh.read()
                    with open(self.oraculo_arq, "w") as fh:
                        fh.write(txt.replace("        self.assertTrue(1)\n", ""))
                elif k == "ac_py":
                    with open(self.oraculo_arq, "a") as fh:
                        fh.write("\n# trocado e recongelado só no ac.py\n")
                    stp = os.path.join(self.camp, ".auto-correcao", "state.json")
                    with open(stp) as fh:
                        sac = json.load(fh)
                    files = sac["oracle"].get("files") or [self.oraculo_arq]
                    sac["oracle"]["hash"] = acmod().sha_files(sorted(files))
                    with open(stp, "w") as fh:
                        json.dump(sac, fh, indent=1)
                    p = subprocess.run([sys.executable, AC, "--work", self.camp, "oracle", "verify"],
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
                                       env=self.env, timeout=60)
                    self.assertEqual(p.returncode, 0, "fixture: ac.py deveria aceitar o recongelamento: " + p.stdout)
                elif k == "manifest":
                    p = os.path.join(self.ws, "oraculo", "MANIFEST.json5")
                    man = json5_load(p)
                    man["frentes"]["T-01"]["autores"] = ["builder-A"]
                    self.write_json(p, man)
            code, g0, out = self.portao_item("G0")
            if adult:
                self.assertIn(g0.get("status"), ("FAIL", "ERRO"), out)
            else:
                self.assertEqual(g0.get("status"), "PASS", out)

    def test_hashes(self):
        self.rodar_tabela("e", self.linha)


# ====================================================================== (f) portões

SABOTA_G4 = "\n\ndef g4_gaming(diff, literais=()):\n    return _res('G4', 'PASS', 0, '', 'sabotado', None)\n"


class TestF_Portoes(GBase):
    def copia_sabotada(self):
        home = os.path.join(self.tmp, "home2")
        sk = os.path.join(home, ".claude", "skills")
        os.makedirs(sk)
        dst = os.path.join(sk, "construcao-orquestrada")
        shutil.copytree(SKILL, dst, ignore=shutil.ignore_patterns("__pycache__", "tests"))
        os.symlink(os.path.join(REAL_SKILLS, "auto-correcao"), os.path.join(sk, "auto-correcao"))
        with open(os.path.join(dst, "scripts", "co_portao.py"), "a", encoding="utf-8") as fh:
            fh.write(SABOTA_G4)
        env = self.make_env(home)
        return os.path.join(dst, "scripts", "co.py"), env

    def linha(self, r):
        gid, caso = r["gid"], r["caso_id"]
        if caso in ("obsoleto", "waiver_outro"):
            self.ledger_coerente()
            self.relatorio()
            code, v = self.veredito_cli()
            self.assertEqual((code, v.get("veredito")), (0, "GO"), "controle: relatório íntegro é GO: %s" % v)
            if caso == "obsoleto":
                self.wfile("src/core.py", "def soma(a, b):\n    return a + b  # mudou depois do relatório\n")
            else:
                self.relatorio(veredito="GO (com waiver)", mudancas=waiver_aprovado(self, gid, portao="G6"))
            code, v = self.veredito_cli()
            self.assertEqual((code, v.get("veredito")), (1, "NO-GO"), v)
            return
        if caso == "adulterado":
            self.ledger_coerente()
            self.relatorio()
            code, v = self.veredito_cli()
            self.assertEqual((code, v.get("veredito")), (0, "GO"), "controle: relatório íntegro é GO: %s" % v)
            p = self.relatorio(veredito="NO-GO", mudancas={gid: {"status": "FAIL", "exit": 1}})
            with open(p) as fh:
                rep = json.load(fh)
            for it in rep["itens"]:
                if it["id"] == gid:
                    it["status"], it["exit"] = "PASS", 0
            rep["veredito"] = "GO"
            self.write_json(p, rep)
            code, v = self.veredito_cli()
            self.assertEqual((code, v.get("veredito")), (1, "NO-GO"), v)
            return
        if gid == "G0":
            self.congelar_real()
            if caso == "fail":
                with open(self.oraculo_arq) as fh:
                    txt = fh.read()
                with open(self.oraculo_arq, "w") as fh:
                    fh.write(txt.replace("        self.assertTrue(1)\n", ""))
            code, it, out = self.portao_item("G0")
            if caso == "pass":
                self.assertEqual(it.get("status"), "PASS", out)
            else:
                self.assertIn(it.get("status"), ("FAIL", "ERRO"), out)
                self.assertEqual(code, 1, out)
            return
        if gid == "G7":
            self.ledger_coerente()
            if caso == "pass":
                code, out, err = self.co("portao", "selftest")
                self.assertEqual(code, 0, out + err)
                c2, it, o2 = self.portao_item("G7")
                self.assertEqual(it.get("status"), "PASS", "G7 no portao run: " + o2[-600:])
            else:
                co2, env2 = self.copia_sabotada()
                code, out, err = self.co("portao", "selftest", env=env2, script=co2)
                self.sem_traceback(out, err)
                self.assertEqual(code, 1, "selftest aceitou G4 sabotado: " + (out + err)[-600:])
                code, out, err = self.co("portao", "run", "--only", "G7", env=env2, script=co2)
                with open(os.path.join(self.ws, "gate-report.json")) as fh:
                    it = {i["id"]: i for i in json.load(fh)["itens"]}.get("G7", {})
                self.assertIn(it.get("status"), ("FAIL", "ERRO"), out + err)
            return
        if gid in ("G1", "G3", "G4"):
            self.ledger_coerente(so_t01=True)
            if caso == "pass" and gid != "G1":
                self.wfile("src/novo.py", "X = 1\n")
                self.commit()
            if caso == "fail":
                if gid == "G1":
                    self.wfile("src/core.py", "def soma(a, b):\n    return a - b\n")
                elif gid == "G3":
                    self.wfile("README.md", "# editado fora do território\n")
                    self.commit()
                else:
                    self.wfile("src/core.py", "import pytest\n\n\ndef soma(a, b):\n    pytest.skip('depois')\n"
                               "    return a + b\n")
                    self.commit()
            code, it, out = self.portao_item(gid)
            if caso == "pass":
                self.assertEqual(it.get("status"), "PASS", out)
            else:
                self.assertIn(it.get("status"), ("FAIL", "ERRO"), out)
                self.assertEqual(code, 1, out)
            return
        self.ledger_coerente()
        code, it, out = self.portao_item(gid)
        if caso == "vacuo":
            self.assertTrue(it, "item %s ausente do relatório" % gid)
            self.assertNotEqual(it.get("status"), "PASS", "%s PASS por vácuo na onda 1: %s" % (gid, out))
        else:
            self.assertEqual(it.get("status"), "NA", out)
            self.assertTrue(it.get("motivo"), "NA sem motivo")

    def test_portoes(self):
        self.rodar_tabela("f", self.linha)


# ====================================================================== (g) subcomandos

REPRESENTATIVO = {
    "ev": ["ev", "nota", "--texto", "x"], "status": ["status", "--json"], "load": ["load", "LOTE"],
    "pontos": ["pontos", "check"], "oraculo": ["oraculo", "mudar", "--motivo", "m", "--evidencia", "e"],
    "plano": ["plano", "check"], "lote": ["lote", "proximo"], "colisao": ["colisao", "T-01", "T-02"],
    "trava": ["trava", "integracao", "acquire", "--dono", "x"], "medir": ["medir"], "comparar": ["comparar"],
    "portao": ["portao", "run", "--only", "G0"], "veredito": ["veredito", "--json"], "retomar": ["retomar"],
    "reabrir": ["reabrir", "T-01", "--motivo", "m"], "diff": ["diff", "T-01", "--base", "{base}", "--repo", "{alvo}"],
}


class TestG_Subcomandos(GBase):
    def fmt(self, argv):
        ruim = os.path.join(self.tmp, "ruim.json")
        with open(ruim, "w") as fh:
            fh.write("{nao e json")
        return [a.format(alvo=self.alvo, base=self.base, payload_ruim=ruim) for a in argv]

    def linha(self, r):
        if r.get("interno"):
            k = r["interno"]
            if k == "ledger_corrompido":
                with open(os.path.join(self.ws, ".construcao", "ledger.jsonl"), "a") as fh:
                    fh.write("{quebrado\n")
                if r["sub"] == "aprovar":
                    self.escrever_passos([])
                    code, out, _ = run_tty(["--work", self.ws, "aprovar", "stop", "--decisao", "aprovado"], self.env)
                    err = ""
                elif r["sub"] == "hook":
                    code, out, err = self.co("hook", "selftest", "--vivo")
                else:
                    code, out, err = self.co(*self.fmt(REPRESENTATIVO[r["sub"]]))
            elif k == "work_e_arquivo":
                arq = os.path.join(self.tmp, "arquivo-comum")
                with open(arq, "w") as fh:
                    fh.write("x")
                code, out, err = self.co("init", "--alvo", self.alvo, "--tipo", "cli", "--pedido", "p", "--stop",
                                         "s", work=arq)
            elif k == "stdin_tipo_errado":
                code, out, err = self.co("hook", input=json.dumps({"tool_name": "Bash", "tool_input": [
                    "co.py aprovar stop"], "session_id": 3}))
            elif k == "maquina_tipo_errado":
                p = os.path.join(self.tmp, "maq.json")
                with open(p, "w") as fh:
                    json.dump({"schema_version": 1, "niveis": 5, "atores": "x"}, fh)
                code, out, err = self.co("maquina", "check", "--machine", p)
            self.sem_traceback(out, err)
            self.assertNotEqual(code, 0, "erro interno saiu 0: " + (out + err)[-400:])
            return
        argv = self.fmt(r["argv"])
        code, out, err = self.co(*argv, work=False if r.get("sem_work") else None)
        self.sem_traceback(out, err)
        self.assertIn(code, r["esperado_exit"], "`%s` saiu %d: %s" % (" ".join(argv), code, (out + err)[-400:]))

    def test_subcomandos(self):
        self.rodar_tabela("g", self.linha)


# ====================================================================== (h) operacionais

class TestH_Operacionais(GBase):
    def linha(self, r):
        self.escrever_passos(m.rota_obra("LOTE"))
        self.assertEqual(self.co("ev", "nota", "--texto", "sync")[0], 0)
        st0 = self.st_json()
        antes = self.L.raw()
        argv = ["ev", r["op"]] + (["--texto", "narrativa"] if r["op"] == "nota" else [])
        code, out, err = self.co(*argv, "--payload", self.payload_file({"texto": "t"}))
        self.sem_traceback(out, err)
        if r["aceito"]:
            self.assertEqual(code, 0, out + err)
            st = self.st_json()
            self.assertEqual(st["hash_estado"], st0["hash_estado"])
            self.assertEqual(st["obra"], st0["obra"])
            self.assertEqual(self.L.last()["evento"], r["op"])
        else:
            self.assertNotEqual(code, 0, "`ev %s` aceito: %s" % (r["op"], out + err))
            self.assertEqual(self.L.raw(), antes)

    def test_operacionais(self):
        self.rodar_tabela("h", self.linha)


# ====================================================================== (i) entrega

class TestI_Entrega(GBase):
    def linha(self, r):
        f = r["falta"] or ""
        kf = 0 if f == "sem_medicao" else (1 if f in ("sem_pass3", "pass3_simulado") else 3)
        self.ledger_coerente(ate="ENTREGA", k_final=kf)
        if f == "pass3_simulado":
            self.medicao(k=3, final=True, simulated=True)
        if f == "simulado":
            self.medicao(k=1, final=False, simulated=True)
        kw = {}
        if f == "parcial":
            kw = dict(only=["G0", "G1", "G3", "G4"])
        elif f == "nao_final":
            kw = dict(final=False)
        elif f == "simulado":
            kw = dict(veredito="GO (simulado)")
        elif f == "nogo":
            kw = dict(veredito="NO-GO")
        elif f == "item_fail":
            kw = dict(mudancas={"G9": {"status": "FAIL", "exit": 1}})
        elif f == "item_erro":
            kw = dict(mudancas={"G12": {"status": "ERRO", "exit": 2}})
        elif f.startswith("sem_G"):
            kw = dict(tirar=(f[4:],))
        elif f == "waiver_g2_arquivo_solto":
            arq = self.write_json(os.path.join(self.ws, "aprovacoes", "G2-90.json"), {"portao": "G2"})
            kw = dict(mudancas={"G2": {"status": "WAIVED", "motivo": "dispensa", "aprovacao": arq, "exit": None}},
                      veredito="GO (com waiver)")
        elif f == "waiver_outro_item":
            kw = dict(mudancas=waiver_aprovado(self, "G2", portao="G6"), veredito="GO (com waiver)")
        elif f.startswith("waiver_"):
            g = "G2" if f.startswith("waiver_g2") else f[7:]
            mud = waiver_aprovado(self, g, decisao="rejeitado" if f.endswith("_rejeitado") else "aprovado",
                                  com_seq=not f.endswith("_sem_seq"), com_audit=not f.endswith("_sem_audit"))
            kw = dict(mudancas=mud, veredito="GO (com waiver)")
        elif f == "sem_portao_relatorio":
            kw = dict(evento=False)
        p = self.relatorio(**kw)
        if f == "obsoleto":
            self.wfile("src/core.py", "def soma(a, b):\n    return a + b  # mudou depois do relatório\n")
        if f == "relatorio_alterado":
            with open(p) as fh:
                rep = json.load(fh)
            rep["itens"][0]["evidencia"] = "trocada"
            self.write_json(p, rep)
        if f.startswith("sem_audit_"):
            portao = f[len("sem_audit_"):]
            linhas_aud = [json.loads(x) for x in self.audit_raw().decode().splitlines() if x.strip()]
            with open(self.audit, "w") as fh:
                for x in linhas_aud:
                    if not (x.get("tipo") == "aprovacao" and x.get("name") == portao):
                        fh.write(json.dumps(x) + "\n")
        if f == "tool_call_aprovou":
            with open(self.audit, "a") as fh:
                fh.write(json.dumps({"ts": now_ts(), "tipo": "tool_call", "session_id": "s", "agent_id": None,
                                     "agent_type": None, "tool": "Bash",
                                     "alvo": "python3 %s --work %s aprovar stop --decisao aprovado" % (CO, self.ws),
                                     "tokens": ["co.py", "aprovar"], "decisao": "permitido", "motivo": "x",
                                     "exit": 0, "cwd": self.tmp, "payload_hash": "2" * 64}) + "\n")
        antes, aud0, ap0 = self.L.raw(), self.audit_raw(), self.aprovacoes_ls()
        code, out, _ch = run_tty(["--work", self.ws, "aprovar", "entrega", "--decisao", "aprovado"], self.env)
        self.sem_traceback(out)
        if r["grava"]:
            self.assertEqual(code, 0, out[-1200:])
            self.assertEqual(self.st_json()["obra"]["estado"], "ENTREGUE")
        else:
            self.assertNotEqual(code, 0, "entregou sem %s: %s" % (f, out[-600:]))
            self.assertEqual(self.L.raw(), antes, "recusa gravou no ledger")
            self.assertEqual(self.audit_raw(), aud0, "recusa gravou no audit")
            self.assertEqual(self.aprovacoes_ls(), ap0, "recusa gravou aprovação")

    def test_entrega(self):
        self.rodar_tabela("i", self.linha)


# ====================================================================== gerador e resultados

class TestZ_Gerador(unittest.TestCase):
    def test_gerador_cobre_todo_item(self):
        self.assertEqual(FALHAS_GERADOR, [], "itens do contrato sem caso: %s" % FALHAS_GERADOR)

    def test_gerar_sai_zero(self):
        p = subprocess.run([sys.executable, os.path.join(AQUI, "gerar.py")], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True, timeout=300)
        self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == "__main__":
    unittest.main()
