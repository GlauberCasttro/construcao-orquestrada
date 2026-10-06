#!/usr/bin/env bash
# _lib.sh — caminhos comuns dos tools do harness de desenvolvimento (sourced, não executado).
# Tudo é derivado da localização deste arquivo: <skill>/.claude/tools/_lib.sh.
# Projeto: a raiz É a skill; campanhas, cópias de trabalho (campanhas/work/) e portões (campanhas/portao-*/)
# ficam em <skill>/campanhas/ (work/ e portao-*/ no .gitignore). HARNESS_WORKSPACE (opcional) redireciona.
# Motor de campanhas: o EMBUTIDO em .claude/tools/ac/ (cópia verbatim da auto-correcao; ver ORIGEM.txt).
HD_TOOLS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SKILL_DIR="$(cd "$HD_TOOLS/../.." && pwd -P)"
SKILL_NAME="$(basename "$SKILL_DIR")"
REPO="$(git -C "$SKILL_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
if [ -n "$REPO" ] && [ "$REPO" != "$SKILL_DIR" ]; then SKILL_REL="${SKILL_DIR#"$REPO"/}"; else SKILL_REL=""; fi
WS="${HARNESS_WORKSPACE:-$SKILL_DIR/campanhas}"
STATE="$SKILL_DIR/.claude/state"
AC="$HD_TOOLS/ac/ac.py"
if [ -n "$SKILL_REL" ]; then HEAD_TREE="HEAD:$SKILL_REL"; else HEAD_TREE="HEAD"; fi

# o que NÃO entra numa cópia de trabalho/portão: dados de campanha, notas locais, pacote gerado
EXCLUIR=(':(exclude)campanhas' ':(exclude)local' ':(exclude)dist')
arquivar() { git -C "$REPO" archive "$HEAD_TREE" -- . "${EXCLUIR[@]}"; }  # git archive do HEAD da skill, sem EXCLUIR
fora_da_copia() { case "$1" in campanhas/*|local/*|dist/*|.claude/*|*__pycache__*|*.pyc|.DS_Store|*/.DS_Store) return 0;; esac; return 1; }

die() { echo "ERRO: $*" >&2; exit 2; }
need_repo() { [ -n "$REPO" ] || die "a skill não está dentro de um repositório git"; }
valid_frente() { case "$1" in ""|.*|*[!A-Za-z0-9._-]*) die "nome de frente inválido: '$1' (use letras, dígitos, . _ -)";; esac; }
# normaliza e valida um caminho relativo à skill: sem '..', sem absoluto
valid_rel() { case "$1" in ""|/*|../*|*/../*|*/..|..) die "caminho inválido (precisa ser relativo à skill, sem ..): '$1'";; esac; }
