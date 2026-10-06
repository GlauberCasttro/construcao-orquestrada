# Mutantes r2 (M2, independente) — construcao-orquestrada onda 1

**Veredito: critério NÃO atingido.** Taxa 67/92 = **72,8%** (< 80%), e **5 de 33** mutantes de retorno constante sobreviveram (E19, E33, E40, P07, C04).

## Método
- 95 mutantes próprios (co_estado 40, co_hook 25, co_portao 25, co.py 5, proporcional ao tamanho). Spec: `mutantes_spec.py`. Runner: `rodar_mutantes.py`. Saída bruta: `resultados_brutos.jsonl`.
- Cada mutante roda numa cópia da skill sob HOME temporário (`.claude/skills/construcao-orquestrada` copiado + link para `auto-correcao`), com 5 workers. Os 4 scripts são restaurados da cópia limpa antes e depois de cada mutante. `PYTHONDONTWRITEBYTECODE=1`.
- MORTO = algum teste falha na suíte visível `tests/onda1` ou no held-out (`run_heldout.py`). As duas suítes rodam completas.
- **Exclusão r3.** Durante a 1ª rodada entraram `tests/onda1/test_r3_achados.py` e `heldout/test_heldout_r3.py`, testes da rodada 3 que falham no código atual. A pedido do integrador, as duas suítes foram congeladas num snapshot (15:35, hashes em `oraculo_snapshot.sha256`), esses dois arquivos foram removidos do snapshot e os 95 mutantes foram medidos de novo. A cópia sem mutante passou 100% em 5/5 execuções paralelas. Na 1ª rodada, os mutantes de E01 a P12 tinham dado o mesmo resultado; de P13 em diante foram invalidados porque o r3 os "matava".
- Ressalva: o snapshot traz `test_r2_achados.py` e `test_heldout_a.py` já na versão editada por terceiros durante a medição. Não é a versão exata do início.

## Por arquivo
| arquivo | mortos/total |
|---|---|
| co_estado.py | 22/40 |
| co_hook.py | 22/25 |
| co_portao.py | 20/25 |
| co.py | 3/5 (C05 equivalente) |

## Equivalentes (fora do denominador)
- **C05** (co.py: `rc None` vira 0): nenhum handler despachado devolve None. Verifiquei por AST que todos terminam em `return int`, e SystemExit é convertido em int antes. O ramo é inalcançável.
- **E25** (cmd_aprovar sem reconferir hash_estado depois do desafio): `transicionar` refaz a mesma comparação sob a trava, antes de gravar, com o mesmo Fail e a mesma mensagem. `obra` faz parte do hash.
- **E26** (transicionar tolera 2 guardas verdadeiras): a máquina embarcada passa I5 (`checar_maquina` ok, 0 violações I5), então duas guardas verdadeiras são inalcançáveis. Ressalva: a prova enumera os contadores até teto+1.

## Sobreviventes (25)
Retorno constante (os que violam o critério):
- **E19** `aprovacao_humana` sempre True em transicionar. A barreira `(actor==humano) != bool(_humano)` impede a gravação, mas o erro muda de Fail para Bad (exit 1 para 2) via API. Nenhum teste chama `transicionar` com evento humano sem o canal humano.
- **E33** `_a_retomar_md_valido` sempre True. Nenhum teste edita o RETOMAR.md à mão antes de `rodada_fechada`/entrega.
- **E40** `hook_selftest_estatico` sempre True. Nenhum teste quebra o selftest estático e espera `iniciar` recusado.
- **P07** `veredito(ws)` sempre "GO". A função é pública no contrato (`veredito(ws) -> str`), mas nenhum teste a chama: só `cmd_veredito`/`veredito_detalhado` são exercitados.
- **C04** co.py, erro interno sai com 0. Nenhum teste provoca exceção não tratada pelo co.py para checar exit 2.

Conferência de hash desligada:
- **E09/E10/E11**: cada um desliga uma das três checagens de `problemas_cadeia` (payload_hash, hash, prev) e as outras duas cobrem os testes existentes. Falta um teste de adulteração que só uma delas pegue, por exemplo campo não-payload editado sem recomputar o hash (E10), ou registro trocado por outro autoconsistente com `prev` errado (E11).
- **E36**: gate-report.json editado depois do `portao_relatorio` não é testado contra os átomos `veredito_go_final`/`portao_regressao_go`.
- **E37**: o hash devolvido pelo ac.py depois do freeze não é conferido.
- **P10**: PLANO.json5 reescrito depois de `plano_ok` (o G3 usa `divergencias['plano']`). Falta teste.
- **P12**: regressao.json5 alterada depois do `portao run` não é exercitada no `veredito`.

Bypass do lock:
- **E14**: o flock nunca é testado com escritas concorrentes.

Precedência:
- **E17**: and/or trocados no parser. As guardas da máquina embarcada não misturam and/or sem parênteses, e nenhum teste de `avaliar_guarda` usa `a or b and c`.
- **E18**: `atomos` do chamador sobrepõem `aprovacao_humana`. Só é alcançável via API.

Feature removida, condição ou limite:
- **E24**: TOCTOU sob a trava. A janela entre `st2` e a trava não é testada.
- **E27**: fold aceita registro operacional com ator/de/para incoerentes. Falta teste.
- **E31**: I6 sem exigir `aprovacao_humana` na guarda humana. Falta máquina-fixture para isso.
- **E34**: relatório `simulado:true` com veredito "GO". Falta teste.
- **E38**: oráculo com testes e 0 asserções congela. Falta teste.
- **H12**: escrita no audit por ferramenta Write/Bash não é bloqueada. Falta teste.
- **H14**: `rm` sobre ancestral de workspace. Falta teste.
- **H24**: audit resolvendo para dentro de workspace (anexar_audit). Falta teste.
- **P19**: `--only` com `--final` grava `final:true` no gate-report. O veredito continua NO-GO, mas o campo `final` não é conferido.
- **P21**: G3 ignora protegidos. Só é alcançável com `diff --repo` contendo o ws, e não há teste.

## Integridade
`scripts/` e `references/` da skill original estão byte a byte iguais ao início, conferidos por sha256. Mudaram só `tests/onda1/ESPEC.md`, `test_r2_achados.py` e o novo `test_r3_achados.py`, editados por terceiros (o oráculo r3), não por M2.
