# Workflow — construcao-orquestrada

Uma frente ativa por vez (ou todas declaradas `--paralela`). Frente = campanha auto-correcao. O bloco JSON é
mantido por `python3 .claude/tools/frente.py` (open/pause/resume/close); a tabela é regenerada.

<!-- frentes:begin -->
```json
{
 "ativas": [],
 "pausadas": [
  {
   "nome": "onda1",
   "campanha": "campanhas/onda1",
   "objetivo": "Onda 1: estado, hook e portões (co_estado/co_hook/co_portao). Pausada em 2026-10-05 por custo; rodada 2, etapa correcao, frente A interrompida.",
   "desde": "2026-10-04"
  }
 ],
 "entregas": [
  {
   "nome": "onda0",
   "campanha": "campanhas/onda0",
   "objetivo": "Onda 0: contrato, máquina, portões, invariantes, ondas e formatos (references/)",
   "commit": "5e9e6f7",
   "em": "2026-10-04"
  }
 ]
}
```
<!-- frentes:end -->

<!-- tabela:begin -->
| estado | frente | campanha | desde / entrega | objetivo |
|---|---|---|---|---|
| pausada | onda1 | campanhas/onda1 | 2026-10-04 | Onda 1: estado, hook e portões (co_estado/co_hook/co_portao). Pausada em 2026-10-05 por custo; rodada 2, etapa correcao, frente A interrompida. |
| entregue | onda0 | campanhas/onda0 | 2026-10-04 · commit 5e9e6f7 | Onda 0: contrato, máquina, portões, invariantes, ondas e formatos (references/) |
<!-- tabela:end -->

## Fila
1. Onda 1: prova independente e fechamento (BACKLOG P0-1) — antes, o founder confirma o custo da rodada de mutação.
2. Decisão CO-1 (BACKLOG P0-2) — só o founder.
3. Proposta P-01: a skill ensina e instala o harness de desenvolvimento de uma skill (BACKLOG P0-3) — aguarda o founder.
4. Onda 2, onda 3, obra de prova (BACKLOG P1/P2).

## Campanhas neste projeto
As campanhas vivem em `campanhas/<nome>/` (oráculo, relatórios, mutantes). O ledger/state da auto-correcao
(`.auto-correcao/`) de cada campanha fica SÓ na máquina de origem (não versionado): ao retomar a onda 1 aqui, abra
uma campanha nova (`new-front onda1-retomada`) apontando para o oráculo de `campanhas/onda1/oraculo/` e
`campanhas/revisao-v4/`. Tabela campanha -> commit -> decisão: `campanhas/README.md`.

## Últimas entregas no git
No repositório privado de origem: `5e9e6f7` onda 0 (contrato, máquina, portões, invariantes, ondas, formatos) e
`7ac0666` PENDENTE.md. Neste projeto, o primeiro commit traz a onda 0 + a onda 1 em andamento + harness + campanhas
(veja `git log` — o hash não é digitado aqui).
