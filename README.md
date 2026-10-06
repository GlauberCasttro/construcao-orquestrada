# construcao-orquestrada

Skill (Claude Code) para **construir software com uma equipe de agentes sob portões mecânicos**: contrato e
máquina de estado em JSON5, ledger encadeado por hash, hook que impede o agente de forjar aprovação humana,
portões G0..G14, oráculo escrito por quem não constrói e held-out fora do alcance do construtor.

Este repositório é o **projeto de desenvolvimento** da skill: tem a skill (na raiz), o harness que entrega a
evolução dela (`.claude/`), os oráculos e relatórios das campanhas (`campanhas/`) e o estado do trabalho
(`.claude/state/`).

## Estado (2026-10-06)
- **Onda 0** entregue: `references/` (contrato, máquina, portões, invariantes, ondas, formatos).
- **Onda 1 em andamento**: `scripts/co.py`, `co_estado.py`, `co_hook.py`, `co_portao.py`, `tests/onda1/**`,
  `references/hook-settings.json5`. Suítes verdes nos 2 Pythons; a prova independente (mutação >= 80% + verificador
  cego novos) está pendente. Detalhes e números: `.claude/state/RESUME.md`.
- Ainda não há `SKILL.md` (vem na onda 2). Decisões abertas do founder: `.claude/state/BACKLOG.md`.

## Layout
```
references/  scripts/  tests/onda1/   a skill (o produto)
PENDENTE.md                           nota da pausa de 2026-10-05 (a verdade de estado é .claude/state/)
.claude/                              harness de desenvolvimento: CLAUDE.md, settings.json (hooks), skills/
  tools/                              scripts do fluxo (carimbo, cópia, portão, portar, conferir, guards)
  tools/ac/                           motor de campanhas EMBUTIDO (cópia verbatim da auto-correcao; ORIGEM.txt)
  state/                              RESUME, WORKFLOW, BACKLOG, DECISIONS, logs/
campanhas/                            oráculos e relatórios das campanhas + documentos de desenho e decisão
local/                                (fora do git) notas privadas desta máquina
```

## Como desenvolver
1. Abra o Claude Code na raiz do projeto (`cd construcao-orquestrada && claude`). O hook `SessionStart` imprime o
   carimbo (branch, HEAD, campanha ativa, arquivos sujos).
2. Rode `/load-session` para retomar. Toda mudança no produto passa pelo fluxo `new-front` -> cópia de trabalho ->
   portão (2 Pythons) -> portar -> conferir-commit -> `close-front` (descrito em `.claude/CLAUDE.md`).
3. Aprovações humanas (gates, pré-autorizações, frase) são feitas por você, no seu terminal, com a sua frase-senha.

## Instalar a skill a partir do projeto
A skill se instala em `~/.claude/skills/construcao-orquestrada` (o produto usa esse caminho em comandos e no hook).
Faça um link para o projeto:
```
ln -s "$PWD" ~/.claude/skills/construcao-orquestrada
```
O produto reusa o leitor JSON5 do `ac.py` da skill `auto-correcao` (`~/.claude/skills/auto-correcao`). Os testes
acham a auto-correcao por `CO_AC_DIR`, pela instalada, por um projeto irmão `../auto-correcao` ou, em último caso,
pelo motor embutido em `.claude/tools/ac/`.

## Primeira vez numa máquina nova
- Python 3.9+ (as suítes rodam em `python3` e em `/usr/bin/python3`). Só stdlib.
- No SEU terminal (nunca pelo chat), defina a frase-senha das aprovações:
  `python3 .claude/tools/ac/ac.py frase definir`.
- Instale os hooks de privacidade do git: `bash .claude/tools/guard-privacidade.sh --install-hook`, e crie
  `local/termos-privados.txt` (um termo por linha; fora do git).
- Rode as suítes:
  ```
  python3 -m unittest discover -s tests/onda1
  python3 -m unittest discover -s tests/onda1/gerado
  (cd campanhas/revisao-v4 && python3 -m unittest test_estado test_hook_bypass test_portao)
  python3 campanhas/onda1/oraculo/heldout/run_heldout.py
  python3 -m unittest discover -s .claude/tools/tests
  ```
  `CO_SKILL_DIR=<dir>` faz os testes e oráculos testarem outra cópia da skill (é o que o portão usa).

## Limites
- Os ledgers das campanhas (`.auto-correcao/`) ficam só na máquina de origem; aqui vão oráculos e relatórios.
- Testes que dependeriam de recurso privado pulam com motivo (ex.: `campanhas/onda0/checa_neg.py` sem
  `CHECA_NEG_DIR`). Os scripts de mutação em `campanhas/onda1/mutantes-r*/` são históricos (rodaram na máquina de
  origem); os relatórios estão junto.
- Não há CI: o portão é local. Hooks são filtros sintáticos, não sandbox (veja "O que NÃO existe" em
  `.claude/CLAUDE.md`).

## Licença
MIT — veja `LICENSE`.
