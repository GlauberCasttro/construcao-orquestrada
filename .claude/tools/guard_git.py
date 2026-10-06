#!/usr/bin/env python3
"""guard_git.py — decide se um comando Bash do payload de hook PreToolUse é git destrutivo.

Uso (hook): python3 guard_git.py < payload.json   (via tools/guard-git.sh)
            python3 guard_git.py --check "git reset --hard"   (decisão em texto, exit 1 se negar)
Saída de negação: JSON hookSpecificOutput permissionDecision=deny. Permissão: sem saída, exit 0.
Limite honesto: analisa o TEXTO do comando (shlex, bash -c, eval, $(...)); não enxerga scripts que
chamam git por dentro, nem aliases. Texto de heredoc é lido como comando (falso positivo é aceito).
"""
import json
import os
import re
import shlex
import subprocess
import sys

SEPS = set(";&|()\n")
WRAPPERS = {"sudo", "env", "command", "time", "nohup", "exec", "builtin", "nice"}
GIT_OPTS_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix"}


def _repo_root(cwd):
    try:
        r = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=10)
        return os.path.realpath(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None
    except Exception:
        return None


def _tokens(cmd):
    lex = shlex.shlex(cmd.replace("\n", " ; "), posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    return list(lex)


def _segments(tokens):
    seg = []
    for t in tokens:
        if t and set(t) <= SEPS:
            if seg:
                yield seg
            seg = []
        else:
            seg.append(t)
    if seg:
        yield seg


def _short_has(arg, ch):
    return arg.startswith("-") and not arg.startswith("--") and ch in arg[1:]


def _analyse_git(args, cwd, repo):
    """args = tokens depois de 'git'. Retorna motivo de negação ou None."""
    eff = cwd
    i = 0
    while i < len(args) and args[i].startswith("-"):
        a = args[i]
        if a == "-C" and i + 1 < len(args):
            eff = os.path.realpath(os.path.join(eff, os.path.expanduser(args[i + 1]))); i += 2; continue
        if a in GIT_OPTS_ARG:
            i += 2; continue
        i += 1
    if i >= len(args):
        return None
    sub, rest = args[i], args[i + 1:]
    has = lambda *names: any(a in names for a in rest)
    if sub == "reset" and (has("--hard", "--merge") ):
        return "git reset --hard/--merge descarta trabalho (outras sessões podem ter trabalho no working tree)"
    if sub == "checkout" and (has("--", ".", "-f", "--force") or any(_short_has(a, "f") for a in rest)):
        return "git checkout -- / . / -f sobrescreve arquivos do working tree"
    if sub == "switch" and (has("--discard-changes", "--force", "-f")):
        return "git switch --force descarta alterações"
    if sub == "restore" and not (has("--staged") and not has("--worktree", "-W")):
        return "git restore sobrescreve o working tree (só 'restore --staged' é permitido)"
    if sub == "clean" and (has("--force") or any(_short_has(a, "f") for a in rest)):
        return "git clean -f apaga arquivos não versionados (trabalho em andamento pode estar untracked)"
    if sub == "stash" and not (rest and rest[0] in ("list", "show")):
        return "git stash esconde trabalho de outras sessões; use cópia de trabalho (tools/copia.sh)"
    if sub == "push":
        return "push é só do humano (nunca pela IA)"
    if sub == "add":
        if has("-A", "--all", "-u", "--update") or any(_short_has(a, "A") for a in rest):
            return "git add -A/--all/-u pega arquivo de outras frentes; liste os arquivos explicitamente"
        for a in rest:
            if a in (".", "*", ":/", ":/*") or (a.startswith("./") and a.strip("./") == ""):
                target = eff if a in (".", "*") or a.startswith("./") else repo
                if repo and os.path.realpath(target) == repo:
                    return "git add . / * na raiz do repo pega tudo (inclusive o que não é da frente); liste os arquivos"
    if sub == "commit":
        if has("--all", "--amend") or any(_short_has(a, "a") for a in rest if not a.startswith("-m")):
            return "git commit -a/--all/--amend: commite só os arquivos da frente (git add <lista> + commit -F arquivo)"
    if sub == "branch" and (has("-D", "--delete", "-d", "--force", "-f") or any(_short_has(a, "D") for a in rest)):
        return "apagar/forçar branch é decisão do humano"
    if sub in ("rebase", "filter-branch", "filter-repo", "replace"):
        return "git %s reescreve histórico" % sub
    if sub == "reflog" and has("expire", "delete"):
        return "reflog expire/delete apaga a rede de segurança"
    if sub == "gc" and any("prune" in a for a in rest):
        return "git gc --prune apaga objetos"
    return None


def analyse(cmd, cwd, repo, depth=0):
    if depth > 4:
        return None
    try:
        toks = _tokens(cmd)
    except ValueError:
        # aspas desbalanceadas: cai no regex conservador
        m = re.search(r"\bgit\b[^;&|\n]*\b(push|stash|reset\s+--hard|clean\s+-\w*f)", cmd)
        return "comando com aspas inválidas contendo git destrutivo" if m else None
    for tk in toks:  # $(...) e `...` dentro de tokens
        for inner in re.findall(r"\$\(([^()]*)\)|`([^`]*)`", tk) if ("$(" in tk or "`" in tk) else []:
            r = analyse(inner[0] or inner[1], cwd, repo, depth + 1)
            if r:
                return r
    cur = cwd
    for seg in _segments(toks):
        j = 0
        while j < len(seg) and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", seg[j]) or seg[j] in WRAPPERS):
            j += 1
        seg = seg[j:]
        if not seg:
            continue
        prog = os.path.basename(seg[0])
        if prog == "cd" and len(seg) > 1:
            cur = os.path.realpath(os.path.join(cur, os.path.expanduser(seg[1])))
        elif prog == "git":
            r = _analyse_git(seg[1:], cur, repo)
            if r:
                return r
        elif prog in ("sh", "bash", "zsh", "dash", "ksh") and "-c" in seg:
            k = seg.index("-c")
            if k + 1 < len(seg):
                r = analyse(seg[k + 1], cur, repo, depth + 1)
                if r:
                    return r
        elif prog == "eval":
            r = analyse(" ".join(seg[1:]), cur, repo, depth + 1)
            if r:
                return r
        elif prog == "xargs" and "git" in seg:
            r = _analyse_git(seg[seg.index("git") + 1:], cur, repo)
            if r:
                return r
    return None


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny",
        "permissionDecisionReason": "guard-git (harness-dev): " + reason +
        ". Veja .claude/CLAUDE.md (git e privacidade). Push e git destrutivo são só do humano."}}, ensure_ascii=False))


def main(argv):
    if len(argv) >= 2 and argv[1] in ("-h", "--help"):
        print(__doc__); return 0
    if len(argv) >= 3 and argv[1] == "--check":
        r = analyse(argv[2], os.getcwd(), _repo_root(os.getcwd()))
        print("NEGA: " + r if r else "permite"); return 1 if r else 0
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("payload não é objeto")
    except Exception as e:
        deny("payload do hook ilegível (%s); falha fechada" % e); return 0
    ti = payload.get("tool_input")
    cmd = ti.get("command") if isinstance(ti, dict) else None
    if cmd is None:
        return 0  # não é Bash
    if not isinstance(cmd, str):
        deny("tool_input.command não é texto"); return 0
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) and payload.get("cwd") else os.getcwd()
    r = analyse(cmd, os.path.realpath(cwd), _repo_root(cwd))
    if r:
        deny(r)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
