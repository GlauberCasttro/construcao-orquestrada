# Harness de desenvolvimento de uma skill — resumo da especificação comum (2026-10-06)

Resumo limpo das duas especificações internas usadas em 2026-10-06 para montar os harnesses de desenvolvimento de
três skills (codebase-specialists, auto-correcao e construcao-orquestrada) e transformá-las em projetos. É a base da
proposta P-01 (BACKLOG P0-3): a construcao-orquestrada ensinar e instalar este harness em qualquer skill.

## Princípios
- Cada skill tem o SEU harness em `<skill>/.claude/`; toda mudança no produto passa pelo fluxo dele.
- Tudo que é mecânico vira script em `.claude/tools/` (`--dry-run`, `check`, `--json` quando couber); as skills do
  harness são finas e só chamam scripts. Markdown explica, script decide.
- Nunca fabricar aprovação, execução, contagem ou data. Aprovação humana só no terminal do humano, com a senha dele.
- Comandos em inglês (verbo-objeto), prosa em português.

## Layout do harness
| arquivo | papel |
|---|---|
| `CLAUDE.md` (<= ~90 linhas) | método, fluxo de entrega, git e privacidade, lições, rituais, o que NÃO existe |
| `settings.json` | PreToolUse Bash -> guard-git (+ hook de aprovação do motor); Edit/Write -> guard-entrega; SessionStart -> carimbo |
| `skills/load-session`, `save-session`, `new-front`, `close-front` | rituais finos (os que mudam estado: só o humano invoca) |
| `tools/carimbo.sh` | âncora real: branch, HEAD, versão, campanha ativa, arquivos sujos, data (`--brief`, `--json`, `--write-resume`) |
| `tools/guard-git.sh` | nega git destrutivo (reset --hard, checkout --, clean -f, stash, push, add -A/., commit -a/--amend, rebase...) |
| `tools/guard-entrega.py` | nega Edit/Write no produto; zonas livres: `.claude/state/`, `campanhas/`, `local/`; falha fechada |
| `tools/copia.sh` | cópia de trabalho (`git archive HEAD`, sem `campanhas/`/`local/`/`dist/`) em `campanhas/work/<frente>/` |
| `tools/portao.sh` | cópia limpa = HEAD + só os arquivos da frente; suítes nos 2 Pythons; oráculos externos; nenhum def removido |
| `tools/portar.sh` | cópia -> produto vivo, com merge de 3 vias se o vivo mudou; para em conflito |
| `tools/conferir-commit.sh` | cada arquivo do commit é idêntico ao que o portão testou |
| `tools/frente.py`, `tools/log-sessao.py` | registro das frentes (uma ativa por vez) e log append-only |
| `tools/guard-privacidade.sh` | termos privados (lista fora do git) + padrões genéricos; pre-commit e commit-msg |
| `tools/ac/` | motor de campanhas EMBUTIDO (auto-correcao verbatim + `ORIGEM.txt` com sha256) |
| `state/` | RESUME (com carimbo), WORKFLOW (frentes), BACKLOG (P0..P2), DECISIONS (D-nn), `logs/sessoes.jsonl` |

## Fluxo de entrega
1. `new-front`: campanha no motor (um `--scope` por glob) + registro da frente.
2. Oráculo por agente SEPARADO, congelado; mudança só oficial (`oracle change --why --evidence`, passando TODOS os
   arquivos do oráculo).
3. Aprovação humana por script que o founder roda no terminal (gates, pré-autorização de commit, frase conferir).
4. Corretor só na cópia de trabalho -> portão -> portar -> conferir-commit -> commit só dos arquivos da frente
   (mensagem em arquivo) -> fechar a campanha.

## Projeto da skill
`<skill>/` com a skill na raiz, `.claude/` (harness), `campanhas/<nome>/` (oráculos, relatórios; sem ledgers),
`local/` (fora do git), `README.md`, `LICENSE` (MIT), `.gitignore`. Testes e oráculos acham a skill por variável de
ambiente ou caminho relativo; o que depende de recurso privado pula com motivo. Nada é empurrado sem revisão humana.

## Verificação de cada harness
`bash -n`/`py_compile` e `--help` de cada tool; guards com payloads simulados (inclusive inválido => nega);
carimbo real; suítes da skill verdes nos 2 Pythons; testes do próprio harness (`.claude/tools/tests/`); grep de
termos privados vazio na árvore e no histórico; simulação de máquina nova (HOME temporário, cópia em outro caminho).
