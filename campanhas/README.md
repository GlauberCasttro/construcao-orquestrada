# campanhas/ — oráculos, relatórios e documentos de desenho

Tudo que a construção da skill produziu FORA do produto: oráculos (testes que o construtor não escreveu),
relatórios de mutação e de verificação cega, e os documentos de desenho e decisão do founder. O ledger/state de cada
campanha (`.auto-correcao/`) fica só na máquina de origem e não é versionado.

## Campanhas
| campanha | o quê | commit de entrega | decisão |
|---|---|---|---|
| `onda0/` | onda 0: contrato, máquina, portões, invariantes, ondas e formatos (`references/`). Checadores `checa.py` (estrutura, bijeção, disjunção) e `checa_neg.py` (casos negativos; precisa de `CHECA_NEG_DIR`) | `5e9e6f7` (repositório privado de origem) | GO |
| `onda1/` | onda 1: estado + ledger (`co_estado`), hook PreToolUse (`co_hook`), portões (`co_portao`), CLI (`co.py`). Oráculo O1 visível em `tests/onda1/` (incl. `gerado/`), held-out em `onda1/oraculo/heldout/`, base do vazio em `oraculo/base.txt` | nenhum ainda (no repositório de origem segue untracked; aqui entra no 1º commit como "em andamento") | PARCIAL — suítes verdes; prova independente pendente (ver abaixo) |
| `revisao-v4/` | verificador cego V4 da rodada 1: 18 testes (15 falhavam, 3 controles) que viraram oráculo da rodada 2 | integrado ao oráculo da onda 1 | 15 achados comprovados -> rodada 2 |
| `campanha-ac-v03/` | auto-correcao v0.3 (aprovação humana não forjável, remedição real, L02, campanhas sobrepostas), conduzida daqui no bootstrap | `5800ed2` (auto-correcao, repositório de origem) | GO (entregue) |
| `campanha-ac-v04/` | auto-correcao v0.4: aprovação por frase-senha do founder | `6e5dc67` (+ `797dc3d` v0.4.1) | GO (entregue) |

## Onda 1 — histórico de medição (relatórios em `onda1/`)
| rodada | mutação (G5) | generalização | veredito |
|---|---|---|---|
| r0 — M1 (`mutantes/`) | 51/79 = 64,6%; retorno constante 18/22 | — | NO-GO |
| r0 — M2 (`mutantes-r2/`) | 67/92 = 72,8%; retorno constante 28/33 | — | NO-GO |
| r0 — M3 (`mutantes-r3/`) | 109/152 = 71,7%; retorno constante 47/53 | 1/10 ocultos do M2 | NO-GO (oráculo não generalizava) |
| r1 — testes GERADOS do contrato | suítes verdes (186 visíveis + gerado + 64 ocultos) | — | NO-GO pelo verificador cego V4 (`revisao-v4/`) |
| r2 — M4 (`mutantes-r4/`) | INTERROMPIDO na pausa de 2026-10-05: parcial 219/335 = 65,4% (sem relatório final) | parcial 13/43 | sem veredito |
Medição de 2026-10-06 (no projeto, 2 Pythons): visível 188, gerado 15, held-out 64, revisao-v4 18 — todos OK.
Falta: agente de mutação NOVO (>= 100 mutantes próprios + sobreviventes do M3) e verificador cego NOVO.

## Documentos
- `DECISOES-FOUNDER.md` — decisões do founder de 2026-10-04/05 (e CO-1 aberta). O registro vivo é
  `.claude/state/DECISIONS.md`.
- `DESENHO.md`, `DESENHO-v2.md` — desenho da skill (v2 é a fonte da verdade, sobreposta pelas decisões).
- `perguntas-ao-founder.md`, `evals-propostos.json`, `pesquisa/` — insumos do desenho.
- `harness-dev/RESUMO.md` — resumo limpo da especificação comum do harness de desenvolvimento de uma skill e do
  layout de projeto (base da proposta P-01).

## Adaptações feitas ao trazer para o projeto (2026-10-06)
Só caminhos e privacidade; nenhuma asserção mudou:
- `tests/onda1/_comum.py`, `onda1/oraculo/heldout/*.py`, `revisao-v4/_base.py`, `onda0/checa*.py`: acham a skill
  por `CO_SKILL_DIR` ou pelo caminho relativo dentro do projeto, e a auto-correcao por `CO_AC_DIR`, pela instalada,
  pelo projeto irmão ou pelo motor embutido (`.claude/tools/ac/`). Antes: `~/.claude/skills/...` fixo.
- Scripts e relatórios de mutação: caminhos absolutos do usuário viraram `~`/`os.path.expanduser`; o caminho do
  workspace virou `campanhas/`. Os `oraculo_snapshot.sha256` registram os arquivos ORIGINAIS da época.
- Fora do projeto (ficam só na máquina de origem): ledgers `.auto-correcao/`, resultados brutos por mutante
  (`res/`), HOMEs de trabalho (`w*/`, `pristine_home/`), logs, scripts `aprovar-*.sh` com caminhos locais.
