# RESUME — construcao-orquestrada (desenvolvimento da skill)

<!-- carimbo:begin -->
```
carimbo construcao-orquestrada · 2026-10-06T13:27:33-0300
branch main @ 54afc00 (repo construcao-orquestrada) · último commit da skill: 54afc00 construcao-orquestrada onda 0 + onda 1 em andamento — projeto completo de desenvolvimento
versão: sem arquivo VERSION
campanha ativa: campanhas/onda1  · frentes pausadas: nenhuma
arquivos sujos na skill: 3 modificados, 1 não versionados
 M .claude/state/CAMPANHA_ATIVA
 M .claude/state/RESUME.md
 M .claude/state/WORKFLOW.md
?? campanhas/onda1/mutantes-r5/
```
<!-- carimbo:end -->

O bloco acima é a âncora REAL (script `tools/carimbo.sh --write-resume`). Se diverge do texto abaixo, o abaixo está
velho.

## Onde paramos (2026-10-06)
- Este é o PROJETO da skill: skill na raiz, harness em `.claude/`, oráculos em `campanhas/`, notas privadas em
  `local/` (fora do git). Primeiro commit: onda 0 + onda 1 em andamento + harness + campanhas.
- **Onda 0** entregue (`references/`; no repositório privado de origem: `5e9e6f7`).
- **Onda 1 em andamento**, VERDE nas suítes (ver abaixo). No repositório de origem segue untracked.
  Falta a **prova independente**: agente de mutação NOVO (>= 100 mutantes próprios + sobreviventes do M3,
  critério >= 80% e todos os de retorno constante mortos) e verificador cego NOVO com reprodução executada.
  A mutação M4 foi interrompida na pausa (parcial 219/335 = 65,4%, sem relatório final). Antes de dar a frente A
  por fechada, confira `co_estado.py` contra a lista do BACKLOG P0-1 (não presuma pelo verde).
- **CO-1** (portão humano para waiver) continua ABERTA: só o founder decide (BACKLOG P0-2).
- **Proposta P-01** (2026-10-06): a skill passa a ENSINAR e INSTALAR o harness de desenvolvimento de uma skill;
  os 3 harnesses de hoje viram modelos e testes de referência. AGUARDA CONFIRMAÇÃO do founder (BACKLOG P0-3).

## Estado das suítes (medido em 2026-10-06, no projeto, sem consertar nada)
| suíte | python3 (3.13) | /usr/bin/python3 (3.9) |
|---|---|---|
| `tests/onda1` (visível) | 188 OK | 188 OK |
| `tests/onda1/gerado` | 15 OK | 15 OK |
| held-out `campanhas/onda1/oraculo/heldout/run_heldout.py` | 64 OK | 64 OK |
| `campanhas/revisao-v4` (test_estado, test_hook_bypass, test_portao) | 18 OK | 18 OK |
| harness `.claude/tools/tests` | 64 OK | 64 OK |
| `campanhas/onda0/checa.py` | TUDO OK | TUDO OK |
Os testes acham a skill por `CO_SKILL_DIR` ou pelo caminho relativo no projeto, e a auto-correcao pela instalada,
pelo projeto irmão ou pelo motor embutido (`.claude/tools/ac/`). Simulação de máquina nova (HOME temporário,
clone em outro caminho, sem auto-correcao instalada): carimbo e motor respondem; visível 188 OK (3.13), gerado 15
OK (3.9), held-out 64 OK, revisao-v4 18 OK, harness 64 OK nos 2 Pythons; `checa_neg.py` pula (sem `CHECA_NEG_DIR`).

## Atualização (2026-10-06, tarde)
- **Publicado** (push autorizado pelo founder): `https://github.com/GlauberCasttro/construcao-orquestrada`
  (branch `main`). Na máquina de origem, `~/.claude/skills/construcao-orquestrada` é LINK para este projeto.
  Ainda sem `SKILL.md` (chega na onda 2): instalada, mas não aparece como skill.
- **Frente `onda1` RETOMADA** (founder: "siga com o que falta", confirmando o custo da prova): prova independente
  em andamento com 2 agentes NOVOS, só leitura do produto, cada um numa cópia em `campanhas/work/`:
  - mutação: `campanhas/work/onda1-prova-mut/` → relatório em `campanhas/onda1/mutantes-r5/relatorio.{md,json}`
    (≥ 100 mutantes próprios + sobreviventes do M3; critério ≥ 80% e todos os de retorno constante mortos);
  - verificador cego: `campanhas/work/onda1-prova-cego/` → `campanhas/onda1/relatorios/V5.md` + `V5-repro/`
    (contra o contrato da onda 0; achado só com reprodução executada).
  Se a sessão cair antes dos relatórios: os agentes não deixam estado no produto; recomece pelos mesmos passos.
- **Recomendações da IA ao founder (NÃO são decisões; aguardam a resposta dele):** CO-1 = SIM (dispensa de item
  exige a senha do founder, como os demais portões humanos); P-01 = SIM e ANTES da onda 2.

## Próximos passos
1. Ler `mutantes-r5/relatorio.md` e `relatorios/V5.md`. Critério atingido e nenhum achado alto ⇒ fechar a frente
   onda1 pelo fluxo (portão → conferir-commit → commit → `frente.py close onda1 --commit <hash>`).
   Não atingido ⇒ frente de correção: oráculo novo por agente separado (sobreviventes/achados) → aprovação do
   founder com senha → corretor na cópia → portão.
2. Founder decide CO-1 e P-01 (recomendações acima); registrar em DECISIONS.md como D-nn com data do sistema.
3. Em máquina nova: abrir o Claude no projeto e `/load-session`; senha (`frase definir`) só quando uma aprovação
   pedir, digitada pelo founder no terminal dele.
