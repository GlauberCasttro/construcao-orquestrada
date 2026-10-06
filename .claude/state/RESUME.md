# RESUME — construcao-orquestrada (desenvolvimento da skill)

<!-- carimbo:begin -->
```
carimbo construcao-orquestrada · 2026-10-06T12:52:22-0300
branch main @ 3fbc46c (repo construcao-orquestrada) · último commit da skill: 3fbc46c construcao-orquestrada onda 0 + onda 1 em andamento — projeto completo de desenvolvimento
versão: sem arquivo VERSION
campanha ativa: nenhuma  · frentes pausadas: onda1
arquivos sujos na skill: 3 modificados, 0 não versionados
 M .claude/state/RESUME.md
 M .claude/tools/carimbo.sh
 M tests/onda1/_comum.py
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

## Próximos passos
1. O founder decide: prova independente da onda 1 (confirmar o CUSTO da rodada de mutação antes), CO-1 e P-01.
2. Se seguir a onda 1: `new-front onda1-retomada` (campanha nova no motor embutido; os ledgers antigos ficaram
   na máquina de origem) -> mutação + verificador cego novos -> portão -> fechamento pelo fluxo.
3. Em máquina nova: `guard-privacidade.sh --install-hook`, criar `local/termos-privados.txt`, definir a frase-senha
   no terminal (`python3 .claude/tools/ac/ac.py frase definir`).
4. Push, remoto e o link `~/.claude/skills/construcao-orquestrada` -> projeto: só depois da revisão do founder.
