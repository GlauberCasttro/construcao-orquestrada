#!/bin/sh
# 5 execuções da cópia SEM mutante (oráculo completo: heldout + tests/onda1 + gerado), em paralelo (carga similar à campanha)
M4=$(cd "$(dirname "$0")" && pwd)
for k in 1 2 3 4 5; do
  H=$M4/b$k; rm -rf $H; mkdir -p $H/.claude/skills
  cp -R $M4/pristine_home/.claude/skills/construcao-orquestrada $H/.claude/skills/
  ln -s ~/.claude/skills/auto-correcao $H/.claude/skills/auto-correcao
  (HOME=$H PYTHONDONTWRITEBYTECODE=1 python3 $M4/runner.py $M4/heldout $M4/base/base$k.json --tudo > $M4/base/base$k.log 2>&1) &
done
wait
HOME=$M4/b1 PYTHONDONTWRITEBYTECODE=1 python3 campanhas/onda1/oraculo/heldout/run_heldout.py --com-visiveis --json $M4/base/run_heldout_oficial.json > $M4/base/run_heldout_oficial.log 2>&1
echo "run_heldout exit $?" >> $M4/base/run_heldout_oficial.log
for k in 1 2 3 4 5; do rm -rf $M4/b$k; done
