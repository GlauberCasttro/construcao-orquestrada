# Backlog — construcao-orquestrada

Prioridade P0..P2. Cada item: origem e critério de pronto. Fonte: `PENDENTE.md`, `campanhas/DECISOES-FOUNDER.md`,
`references/ondas.json5`, decisões de 2026-10-06. Ordem = ordem de execução, salvo decisão do founder.

## P0
1. **Onda 1: prova independente e fechamento (frente `onda1-retomada`)** — origem: PENDENTE.md (pausa por custo,
   2026-10-05) + medição de 2026-10-06. Estado: no projeto a onda 1 está versionada como "em andamento"; suítes
   VERDES nos 2 Pythons (visível 188, gerado 15, held-out 64, revisao-v4 18 — ver RESUME). No repositório privado
   de origem ela segue untracked. A frente A (`co_estado.py`) foi interrompida na pausa e a medição mostra tudo
   verde: confira o código contra a lista abaixo antes de dar a frente A por fechada (não presuma).
   Itens a conferir (oráculo `campanhas/revisao-v4/test_estado.py`): V4-1 decisão de transição do payload nunca
   vale; V4-8 `init --max-rodadas/--teto` respeitados nas guardas; V4-9 `aprovar` atômico/idempotente; integração
   da frente C (`problemas_waivers` com `item=`, `relatorio_satisfaz_entrega` ->
   `co_portao.problema_relatorio_obsoleto`); suspeitas: aceite de task com `verificador`/`testes` autodeclarados e
   `_task_valida` com `lstrip("./")`. Mutação M4: interrompida, sem relatório.
   Pronto quando: prova independente — agente de mutação NOVO (>= 100 mutantes próprios + sobreviventes do M3) e
   verificador cego NOVO com reprodução executada: >= 80% de mutação, todos os de retorno constante mortos, nenhum
   achado alto; então a frente fecha pelo fluxo (portão -> conferir -> commit).
   **Custo: confirmar com o founder antes de cada rodada de mutação.**
2. **Decidir CO-1 (portão humano para waiver)** — origem: `campanhas/DECISOES-FOUNDER.md`, CO-1. Só o founder
   decide; se SIM, é frente que muda a onda 0 (`contrato.json5`, `maquina.json5`, `portoes.json5`) + máquina + hook.
   Pronto quando: decisão em DECISIONS.md e, se SIM, contrato/máquina/hook com `waiver --item Gn` e testes.
3. **PROPOSTA (aguarda confirmação do founder) — a skill passa a ENSINAR e INSTALAR o harness de desenvolvimento
   de uma skill** — origem: decisão de 2026-10-06 (registrada como proposta P-01 em DECISIONS.md). A
   construcao-orquestrada ganha o papel de montar, para qualquer skill, o harness de desenvolvimento descrito em
   `campanhas/harness-dev/RESUMO.md` (state com carimbo, rituais load/save/new-front/close-front, guards de
   entrega e de git, cópia de trabalho -> portão em 2 Pythons -> portar -> conferir-commit, motor de campanhas
   embutido, guard de privacidade, layout de projeto). Os 3 harnesses construídos em 2026-10-06
   (codebase-specialists, auto-correcao e esta) viram MODELOS e TESTES DE REFERÊNCIA: o instalador tem de
   reproduzir cada um a partir da especificação comum, e as suítes deles (ex.: as 64 de `.claude/tools/tests/`
   daqui) rodam contra o que foi instalado. Questões para o founder: entra antes ou depois das ondas 2/3? vira
   uma onda nova em `ondas.json5` (mudança da onda 0, só por decisão)? o instalador é script (`co.py harness
   install --dry-run`) chamado por skill fina?
   Pronto quando (se confirmada): decisão em DECISIONS.md; onda/frente planejada com oráculo próprio escrito por
   agente separado; instalação em skill de exemplo reproduz os 3 modelos com as suítes deles verdes.

## P1
4. **Onda 2** — `co_medir` (medição pareada, IC por bootstrap, pass^3 na entrega), plano/lote/colisão/trava no
   `co.py`, `SKILL.md` e guia de uso. O autor do oráculo O2 escreve durante a onda 1. Pronto quando: fecha_quando da
   onda 2 em `ondas.json5` (G5 com mutantes de M, G12 docs<->CLI, G2 em 3.9 e 3.13).
5. **Onda 3** — integração: a skill passa pelo próprio portão G0..G14. Pronto: portão completo GO sem waiver nos [S],
   `maquina check`, pass^3 no aceite final.

## P2
6. **Obra de prova** — construir `jsonl-diff` com a skill e comparar contra execução sem ela (baseline); depois
   `changelog-pt`. Pronto: `ondas.json5#prova`.
7. **Migrar `PENDENTE.md` para o state** — quando a onda 1 fechar, `PENDENTE.md` perde a razão de existir
   (só por frente, via fluxo, pois o guard-entrega protege o produto).
8. **Atualizar o motor embutido** quando a auto-correcao mudar: recopiar `.claude/tools/ac/` e regravar
   `ORIGEM.txt` (o teste `test_origem_confere_sha256` acusa divergência local).
