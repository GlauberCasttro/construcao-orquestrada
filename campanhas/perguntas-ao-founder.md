# Perguntas ao founder — construcao-orquestrada

Só decisões que o código não pode tomar. Cada uma com a recomendação.

## 1. Como garantir que portão humano é humano?
Hoje o `ac.py gate --by ana` é só um comando: nada impede o agente de rodá-lo pelo Bash. O que segura é
disciplina + o `aprovar-*.sh` gerado que você roda.
**Recomendação:** manter o `aprovar-*.sh` E acrescentar um hook PreToolUse que bloqueia `ac.py gate|preauth` e
`co.py gate` vindos do Bash do agente (sem `--simulated`). Custo baixo, fecha a brecha.

## 2. Campanhas sobrepostas (L17): quantas ao mesmo tempo?
**Recomendação:** no máximo 2 campanhas ativas, teto global de 3 subagentes vivos somando tudo, integração
sempre serial com trava, e a segunda só entra em correção se `collide` provar arquivos disjuntos. Mais que isso
bate no 429 (L06) e no limite de 5h.

## 3. Baseline "sem o sistema" é obrigatório?
Em requisito novo (ferramenta CLI, feature) não existe tarefa comparável; nas campanhas 5–8 não houve baseline.
**Recomendação:** obrigatório quando o alvo é skill ou agente (skill-creator with/without), opcional com dispensa
registrada nos demais. Você confirma?

## 4. Ritmo frente ao limite de 5h
**Recomendação:** 1 rodada por janela; checkpoint e pergunta em ~50%; máx. 2 rodadas por obra antes de escalar;
evals uma por vez. Se preferir mais autonomia, a alternativa é pré-autorizar "continuar" até 80% com
`preauth continue` — mas aí você só vê o resultado no fim.

## 5. Onde mora o mecanismo e quem edita a auto-correcao
O desenho pede (a) um `co.py` novo e fino para o portfólio (obra, pontos, regressão, colisão, retomada) e
(b) gravar a lição L17 e o `collide`/trava de integração na própria `auto-correcao`.
**Recomendação:** `co.py` dentro da nova skill (não inchar o `ac.py`); L17 entra em
`auto-correcao/references/licoes.json5` como mudança aprovada por você, e a trava de integração fica no `co.py`
(a auto-correcao continua sabendo de uma campanha só). Primeira obra para provar a skill: o eval 2 (`jsonl-diff`),
que é barato e não toca repo seu.
