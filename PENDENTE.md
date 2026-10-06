# construcao-orquestrada — o que falta (atualizado em 2026-10-05, pausa por custo)

Publicado: só a **onda 0** (`5e9e6f7`): `references/` com contrato, máquina, portões, invariantes, ondas e formatos.
Campanhas e oráculos: `campanhas/`. Decisões do founder: `campanhas/DECISOES-FOUNDER.md`.

## Onda 1 — estado, hook e portões (campanhas/onda1) · NÃO commitada
Untracked nesta pasta: `scripts/co.py`, `scripts/co_estado.py`, `scripts/co_hook.py`, `scripts/co_portao.py`, `tests/onda1/**` (incluindo `gerado/`) e `references/hook-settings.json5`.

**Histórico:**
- **Rodada 0** (3 sub-rodadas): NO-GO. A mutação estacionou em ~72% e o oráculo não generalizava (1/10 nos mutantes ocultos).
- **Rodada 1** (estratégia nova, decisão do founder: testes GERADOS do contrato, com 728 linhas + concorrência): tudo verde (186 visíveis + gerado + 64 ocultos nos 2 Pythons). NO-GO pelo verificador cego V4: 15 problemas comprovados com testes.
- **Rodada 2** (em andamento quando pausou):
  - ✅ frente C (`co_portao.py`): aplicabilidade vem do contrato; relatório obsoleto ⇒ NO-GO; waiver só do próprio item.
  - ✅ frente B (`co_hook.py`): `{a,b}`, `$HOME`, rsync/git clean/tar/unzip, hardlink, cd em `sh -c`. O limite honesto está documentado.
  - ⚠️ **frente A (`co_estado.py`) INTERROMPIDA no meio.** O arquivo pode estar inconsistente: rode `python3 -m unittest discover -s tests/onda1` antes de qualquer coisa.
  - ⚠️ mutação M4 interrompida, sem relatório.

**Falta na frente A** (oráculo: `campanhas/revisao-v4/test_estado.py`):
- V4-1: a decisão de transição vinda do payload (`transicao`/`saida`) nunca vale; a saída é sempre a calculada pelo motor.
- V4-8: `init --max-rodadas`/`--teto` do founder têm de ser respeitados nas guardas.
- V4-9: `aprovar` não pode travar a obra quando falha no meio (gravar de forma atômica, ou recuperar de forma idempotente).
- integrar a frente C: `problemas_waivers` passa `item=`; `relatorio_satisfaz_entrega` chama `co_portao.problema_relatorio_obsoleto`.
- suspeitas: aceite de task usando `verificador`/`testes` autodeclarados; `_task_valida` com `lstrip("./")`.

**Decisão pendente CO-1:** o contrato não tem portão humano para aprovar a dispensa (waiver) de um item. Proposta: portão `waiver` com `--item Gn` no contrato, na máquina e no hook. Isso muda a onda 0 e o founder decide.

**Depois da frente A:**
1. Integração: visível + gerado + held-out + revisao-v4 nos 2 Pythons.
2. Prova independente: um agente de mutação NOVO (≥100 mutantes próprios + os sobreviventes do M3) e um verificador cego NOVO com reprodução executada.
3. Critério: ≥80% de mutação, todos os de retorno constante mortos e nenhum achado alto. Se convergir, commit da onda 1.

**Custo:** a onda 1 é a mais cara de todo o projeto, porque é a fundação de segurança. Confirme o orçamento com o founder antes de cada rodada de mutação, que leva horas.

## Ondas seguintes (`references/ondas.json5`)
- **Onda 2:** `co_medir` (medição pareada com IC por bootstrap, pass^3 na entrega), plano/lote/colisão/trava no `co.py`, `SKILL.md` e guia de uso. O autor do oráculo O2 escreve durante a onda 1.
- **Onda 3:** integração. A skill passa pelo próprio portão G0..G14.
- **Obra de prova:** construir `jsonl-diff` com a skill e comparar contra uma execução sem ela (baseline). Depois `changelog-pt`.

## Princípios que não mudam
- Quem testa não é quem constrói. O held-out fica fora do alcance do construtor. O oráculo só muda por mudança oficial, feita pelo autor.
- Portão humano só com a senha do founder.
- Tudo que é mecânico vai para script; a skill só chama o script.
- No máximo 5 subagentes ao mesmo tempo (3 se der 429).
