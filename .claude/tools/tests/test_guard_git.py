import json
import os
import shutil
import subprocess
import tempfile
import unittest

from _util import SKILL, TOOLS, decisao, run

SH = os.path.join(TOOLS, "guard-git.sh")


def cmd(c, cwd=None):
    r = run(["bash", SH], stdin=json.dumps({"tool_name": "Bash", "cwd": cwd or SKILL, "tool_input": {"command": c}}))
    assert r.returncode == 0, r.stderr
    return decisao(r.stdout)


NEGA = [
    "git reset --hard", "git reset --hard HEAD~1", "git -C /x reset --hard", "git reset --merge",
    "git checkout -- scripts/co.py", "git checkout .", "git checkout -f main", "git switch --discard-changes x",
    "git restore scripts/co.py", "git restore --worktree x", "git restore .",
    "git clean -fd", "git clean -f", "git clean -xfd", "git clean --force",
    "git stash", "git stash pop", "git stash push -m x", "git stash drop",
    "git push", "git push origin master", "git push --force",
    "git add -A", "git add --all", "git add -u", "git add -Av",
    "git commit -a -m x", "git commit -am x", "git commit --all -m x", "git commit --amend",
    "git branch -D x", "git branch --delete --force x", "git rebase master", "git filter-branch x",
    "git reflog expire --all", "git gc --prune=now",
    "echo ok; git reset --hard", "true && git push", "git status | git push",
    "bash -c 'git reset --hard'", "sh -c \"git push origin\"", "eval git stash", "FOO=1 git push",
    "sudo git clean -fd", "echo $(git reset --hard)", "xargs git push",
]
PERMITE = [
    "git status", "git status --short", "git diff", "git log --oneline -5", "git show HEAD:SKILL.md",
    "git add scripts/co.py tests/onda1/x.py", "git add .claude/state/RESUME.md", "git commit -F msg.txt",
    "git commit -m 'feat: x'", "git restore --staged scripts/co.py", "git stash list", "git clean -n", "git clean -nd",
    "git checkout master", "git checkout -b nova", "git branch -a", "git reset HEAD scripts/co.py", "git reset --soft HEAD~1",
    "git merge-file a b c", "git archive HEAD | tar -x", "echo 'git push é só do humano'", "ls -la", "python3 -m unittest",
    "git diff --stat -- scripts", "grep -n 'git reset --hard' CLAUDE.md",
]


class GuardGit(unittest.TestCase):
    def test_nega(self):
        for c in NEGA:
            self.assertEqual(cmd(c), "deny", c)

    def test_permite(self):
        for c in PERMITE:
            self.assertEqual(cmd(c), "allow", c)

    def test_add_ponto_so_nega_na_raiz_do_repo(self):
        # repo temporário próprio: o teste não depende de onde a skill está (projeto, cópia de portão, outra máquina)
        raiz = os.path.realpath(tempfile.mkdtemp(prefix="gg-"))
        try:
            sub = os.path.join(raiz, "scripts")
            os.makedirs(sub)
            subprocess.run(["git", "init", "-q"], cwd=raiz, check=True)
            self.assertEqual(cmd("git add .", cwd=raiz), "deny")
            self.assertEqual(cmd("git add *", cwd=raiz), "deny")
            self.assertEqual(cmd("git add .", cwd=sub), "allow")
            self.assertEqual(cmd("git -C .. add .", cwd=sub), "deny")
            self.assertEqual(cmd("cd .. && git add .", cwd=sub), "deny")
            self.assertEqual(cmd("cd %s && git add ." % raiz, cwd=sub), "deny")
            self.assertEqual(cmd("git -C %s add ." % raiz, cwd=sub), "deny")
        finally:
            shutil.rmtree(raiz, ignore_errors=True)

    def test_nao_bash_ou_sem_comando_permite(self):
        r = run(["bash", SH], stdin=json.dumps({"tool_name": "Read", "tool_input": {"file_path": "/x"}}))
        self.assertEqual(decisao(r.stdout), "allow")

    def test_payload_invalido_nega(self):
        for raw in ("", "x", "[]", "null"):
            r = run(["bash", SH], stdin=raw)
            self.assertEqual(decisao(r.stdout), "deny", raw)
        r = run(["bash", SH], stdin=json.dumps({"tool_input": {"command": 5}}))
        self.assertEqual(decisao(r.stdout), "deny")

    def test_aspas_desbalanceadas_com_git_destrutivo_nega(self):
        self.assertEqual(cmd("echo 'x; git push"), "deny")

    def test_help_e_check(self):
        self.assertEqual(run(["bash", SH, "--help"]).returncode, 0)
        r = run(["python3", os.path.join(TOOLS, "guard_git.py"), "--check", "git push"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("NEGA", r.stdout)


if __name__ == "__main__":
    unittest.main()
