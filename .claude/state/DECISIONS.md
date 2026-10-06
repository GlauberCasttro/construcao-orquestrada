# Decisões do founder — construcao-orquestrada

Fonte: `campanhas/DECISOES-FOUNDER.md` (2026-10-04/05), `PENDENTE.md`
(2026-10-05) e a especificação do harness-dev (2026-10-06). Formato: D-nn · data · decisão · porquê · onde vale.
Nova decisão entra aqui com data do sistema (`date`), nunca digitada de memória.

- **D-01** · 2026-10-04 · Hook GLOBAL de aprovação (`ac.py gate/preauth`, `co.py approve` só pelo terminal, desafio
  redigitado): SIM. Porquê: aprovação nunca pode vir da IA. Vale: toda campanha; nunca peça a senha no chat.
- **D-02** · 2026-10-04 · auto-correcao v0.3 (AC-01..04 + L17) ANTES do bootstrap da construcao-orquestrada: SIM.
- **D-03** · 2026-10-04 · Ritmo mais agressivo: até 5 subagentes vivos, rodadas sem pergunta intermediária (risco
  aceito: consumo e 429; recuar para 3 se houver 429). Vale: fan-out de campanhas e mutação.
- **D-04** · 2026-10-04 · Medição: baseline obrigatório para skill/agente, held-out oculto do construtor, pass^3 no
  aceite final. Vale: onda 2 em diante e toda obra de prova.
- **D-05** · 2026-10-04 · Obra 1 de prova = `jsonl-diff` (DESENHO-v2), depois `changelog-pt`.
- **D-06** · 2026-10-04 · Tudo que for mecânico vira script (estado com `--dry-run` JSON, pré-condição por `check`,
  leitura `--json`, corpo de skill curto). Skill que repete em prosa lógica de script = defeito no portão.
- **D-07** · 2026-10-04 · Comandos do harness são SKILLS: consulta invocável pelo modelo; criação mostra `--dry-run`
  antes; mudança de estado só pelo humano (`disable-model-invocation`).
- **D-08** · 2026-10-04 · Guia de uso atualizado a cada melhoria: frente de doc obrigatória em toda campanha que muda
  comportamento; doctests docs<->CLI cobrem o MODO-DE-USO.md.
- **D-09** · 2026-10-05 · Onda 1, rodada 1: testes GERADOS do contrato (728 linhas + concorrência), não escritos à
  mão; a estratégia anterior estacionou em ~72% de mutação e o oráculo não generalizava (1/10 nos ocultos).
  Vale: oráculo da onda 1 e seguintes.
- **D-10** · 2026-10-05 · O held-out fica fora do alcance do construtor; o oráculo só muda por mudança oficial feita
  pelo autor (`oracle change --why --evidence`). Quem testa não é quem constrói.
- **D-11** · 2026-10-05 · O custo da onda 1 é confirmado com o founder ANTES de cada rodada de mutação (a mais cara
  do projeto: é a fundação de segurança; rodadas levam horas).
- **D-12** · 2026-10-06 · Cada skill tem o seu harness de desenvolvimento em `<skill>/.claude/`; toda mudança no
  produto passa pelo fluxo dele (frente -> cópia -> portão -> portar -> conferir -> commit). Vale: aqui.
- **PENDENTE CO-1** · 2026-10-05 · O contrato não tem portão humano para aprovar a DISPENSA (waiver) de um item;
  `cmd_aprovar` não gera aprovação de waiver legítima. Proposta: portão `waiver` com `--item Gn` no contrato, na
  máquina e no hook (muda a onda 0). Decisão do founder: ABERTA (ver BACKLOG P0-2).
- **D-13** · 2026-10-06 · Cada skill vira um PROJETO completo (`<skill>/` com SKILL na raiz, harness em `.claude/`,
  oráculos em `campanhas/`, notas privadas em `local/` fora do git), com motor de campanhas EMBUTIDO em
  `.claude/tools/ac/` e guard de privacidade. Vale: este projeto; o harness não depende mais de
  `~/.claude/skills/auto-correcao`.
- **PROPOSTA P-01** · 2026-10-06 · A construcao-orquestrada passa a ser a skill que ENSINA e INSTALA o harness de
  desenvolvimento de uma skill; os 3 harnesses construídos hoje (codebase-specialists, auto-correcao, esta) viram
  modelos e testes de referência; a especificação comum (`campanhas/harness-dev/RESUMO.md`) é a base.
  Status: AGUARDA CONFIRMAÇÃO do founder (ver BACKLOG P0-3). Não executar antes da confirmação.
