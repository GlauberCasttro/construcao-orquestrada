# Decisões do founder — 2026-10-04
1. Hook GLOBAL de aprovação (ac.py gate/preauth, co.py approve só pelo terminal, desafio redigitado): SIM.
2. auto-correcao v0.3 (AC-01..04 + L17) ANTES do bootstrap da construcao-orquestrada: SIM.
3. Ritmo: MAIS AGRESSIVO que o recomendado — até 5 subagentes vivos, rodadas sem pergunta intermediária
   (risco aceito: consumo e 429; recuar para 3 se houver 429).
4. Medição: baseline obrigatório p/ skill/agente, held-out oculto do construtor, pass^3 no aceite final: SIM.
5. (não perguntado em separado) obra 1 = jsonl-diff, conforme DESENHO-v2.
6. (2026-10-04) Tudo que uma skill fizer de mecânico vira script: estado com --dry-run JSON, pré-condição/DoR por comando check, leitura --json, corpo da skill curto. Vale para as skills emitidas pelo codebase-specialists e para a própria construcao-orquestrada (portão: skill que repete em prosa lógica que um script faz = defeito).
7. (2026-10-04) Comandos do harness são SKILLS (não comandos simples): consulta invocável pelo modelo; criação invocável mas mostra --dry-run antes; mudança de estado só pelo humano (disable-model-invocation).
8. (2026-10-04) Guia de uso atualizado a cada melhoria: frente de doc obrigatória em toda campanha que muda comportamento (iter9, iter10: MODO-DE-USO.md + SKILL.md); doctests docs<->CLI estendidos ao MODO-DE-USO.md — campanha não fecha se o guia citar comando inexistente.
- CO-1 (onda1 r2): contrato não tem portão humano para aprovar dispensa (waiver) de um item; cmd_aprovar não consegue gerar aprovação de waiver legítima. Decidir na próxima rodada/onda: portão 'waiver' com --item Gn no contrato + máquina + hook.
