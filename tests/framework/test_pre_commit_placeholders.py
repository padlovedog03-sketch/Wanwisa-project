"""`.githooks/pre-commit` runs CI gate 3's placeholder scan over what is being committed.

SPEC-verify-tiers-merge-gate-am3-commit-on-red, AM3-AC14 to AM3-AC19 and AM3-AC21.

WHY THIS FILE EXISTS. Both incidents in doc/memory/gate-exit-code-before-commit.md
were an upper-case placeholder in angle brackets committed into a file CI gate 3
scans, and CI went red on the branch afterwards. The hook now runs the same scan
(pattern, roots, four exclusions) over the index being committed and refuses on
a hit. In a template that has not been bootstrapped (the staged AGENTS.md still
holds the PROJECT placeholder) the five tokens bootstrap fills are allowed.

Every test commits for real through the hook in a throwaway repo. Tokens are
built by concatenation so this file never reads like a leftover placeholder.

Run: `python3 -m pytest tests/framework/test_pre_commit_placeholders.py -q`
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BOOTSTRAP_TOKENS = ("PROJECT", "PACKAGE", "BACKEND_REPO_PATH", "FRONTEND_REPO_PATH",
                     "FRONTEND_REPO")
_FAIL = "FAIL placeholder scan"


def _tok(name: str) -> str:
    return "<" + name + ">"


_HIT = _tok("ABC_DEF")


def _env(tmp_path: Path) -> dict:
    """Parent env minus VERIFY_*/GIT_* and the checks' directory overrides;
    HOME is scratch so nothing reaches the owner's real registry."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("VERIFY_", "GIT_"))}
    for var in ("MEMORY_DIR", "NEUTRALITY_ROOT", "SCAR_DIR", "XDG_CONFIG_HOME"):
        env.pop(var, None)
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env.update({
        "HOME": str(home),
        "APPROVAL_LOG": str(tmp_path / "registry.jsonl"),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
    })
    return env


def _git(repo: Path, *args: str, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True,
                          env=env, check=False)


def _build(root: Path, mode: str) -> Path:
    """The `test_pre_commit.py::_clone_template` shape, `.verify/` and agent
    worktrees git-ignored. Project mode fills the five bootstrap tokens the
    way `scripts/bootstrap.sh` does, so the copy starts with zero scan hits."""
    repo = root / "repo"
    repo.mkdir()
    ignore = shutil.ignore_patterns("__pycache__", "*.local.txt")
    for rel in (".githooks", ".agents", "scripts", "doc/memory", "doc/scars", "doc/templates"):
        if (_REPO_ROOT / rel).is_dir():
            shutil.copytree(_REPO_ROOT / rel, repo / rel, ignore=ignore)
    (repo / ".gitignore").write_text(".verify/\n.claude/worktrees/\n", encoding="utf-8")
    title = _tok("PROJECT") if mode == "template" else "Acme"
    (repo / "AGENTS.md").write_text("# AGENTS.md — %s\nrules\n" % title, encoding="utf-8")
    if mode == "project":
        for path in repo.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".py", ".json", ".yaml", ".yml"}:
                text = path.read_text(encoding="utf-8")
                new = text
                for name in _BOOTSTRAP_TOKENS:
                    new = new.replace(_tok(name), "acme")
                if new != text:
                    path.write_text(new, encoding="utf-8")
    env = _env(root)
    _git(repo, "init", "-q", env=env)
    _git(repo, "config", "core.hooksPath", ".githooks", env=env)
    _git(repo, "add", "-A", env=env)
    first = _git(repo, "commit", "-q", "--no-verify", "-m", "base", env=env)
    assert first.returncode == 0, first.stderr
    return repo


@pytest.fixture(scope="module")
def _bases(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return {mode: _build(tmp_path_factory.mktemp(mode), mode)
            for mode in ("template", "project")}


def _copy(bases: dict, tmp_path: Path, mode: str) -> tuple:
    repo = tmp_path / "repo"
    shutil.copytree(bases[mode], repo, symlinks=True)
    return repo, _env(tmp_path)


@pytest.fixture()
def project(_bases: dict, tmp_path: Path) -> tuple:
    return _copy(_bases, tmp_path, "project")


@pytest.fixture()
def template(_bases: dict, tmp_path: Path) -> tuple:
    return _copy(_bases, tmp_path, "template")


def _write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _head(repo: Path, env: dict) -> Optional[str]:
    return _git(repo, "rev-parse", "-q", "--verify", "HEAD", env=env).stdout.strip() or None


def _commit(repo: Path, env: dict, *args: str, add: bool = True) -> tuple:
    if add:
        _git(repo, "add", "-A", env=env)
    before = _head(repo, env)
    result = _git(repo, "commit", "-q", "-m", "c", *args, env=env)
    return result, result.stdout + result.stderr, _head(repo, env) != before


def _refused(outcome: tuple) -> str:
    result, out, moved = outcome
    assert result.returncode != 0 and not moved, out
    assert _FAIL in out, out
    return out


def _passed(outcome: tuple) -> str:
    result, out, moved = outcome
    assert result.returncode == 0 and moved, out
    assert _FAIL not in out, out
    return out


# --------------------------------------------------------------------------- AM3-AC14
@pytest.mark.parametrize("mode", ["project", "template"])
def test_ac14_a_non_bootstrap_token_in_doc_qa_is_refused_and_named(
        _bases: dict, tmp_path: Path, mode: str) -> None:
    repo, env = _copy(_bases, tmp_path, mode)
    _write(repo, "doc/qa/QA-x.md", "leftover %s\n" % _HIT)
    out = _refused(_commit(repo, env))
    assert "doc/qa/QA-x.md:1:" in out


# --------------------------------------------------------------------------- AM3-AC15
@pytest.mark.parametrize(("rel", "line"), [
    ("doc/framework/x.md", _HIT),
    ("doc/templates/x.md", _HIT),
    ("scripts/bootstrap.sh", "# " + _HIT),
    ("doc/x.md", _HIT + " see doc/framework/"),
    ("src/x.py", "# " + _HIT),
    ("tests/x.py", "# " + _HIT),
    ("ci-examples/x.yml", "# " + _HIT),
])
def test_ac15_exclusions_and_roots_equal_cis_pass(project: tuple, rel: str, line: str) -> None:
    repo, env = project
    path = repo / rel
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    _write(repo, rel, old + line + "\n")
    _passed(_commit(repo, env))


def test_ac15_a_force_added_agent_worktree_passes(project: tuple) -> None:
    repo, env = project
    _write(repo, ".claude/worktrees/a/x.md", _HIT + "\n")
    _git(repo, "add", "-f", ".claude/worktrees/a/x.md", env=env)
    _passed(_commit(repo, env, add=False))


@pytest.mark.parametrize("rel", ["doc/worktrees-notes.md", ".claude/worktreesX/x.md",
                                 "doc/.claude/worktrees/x.md", "README.md", "AGENTS.md"])
def test_ac15_paths_next_to_the_exclusions_are_refused(project: tuple, rel: str) -> None:
    repo, env = project
    path = repo / rel
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    _write(repo, rel, old + _HIT + "\n")
    _git(repo, "add", "-f", rel, env=env)
    out = _refused(_commit(repo, env))
    assert rel + ":" in out


# --------------------------------------------------------------------------- AM3-AC16
@pytest.mark.parametrize("tokens", [("PROJECT", "PACKAGE"), ("BACKEND_REPO_PATH",),
                                    ("FRONTEND_REPO_PATH",), ("FRONTEND_REPO",)])
def test_ac16a_template_mode_allows_the_five_bootstrap_tokens(
        template: tuple, tokens: tuple) -> None:
    repo, env = template
    _write(repo, ".claude/agents/x.md", " ".join(_tok(t) for t in tokens) + "\n")
    _passed(_commit(repo, env))


def test_ac16b_a_bootstrap_token_never_shelters_another_on_its_line(template: tuple) -> None:
    repo, env = template
    _write(repo, ".claude/agents/x.md", _tok("PROJECT") + " and " + _HIT + "\n")
    out = _refused(_commit(repo, env))
    assert ".claude/agents/x.md:1:" + _tok("PROJECT") + " and " + _HIT in out


def test_ac16c_project_mode_refuses_a_bootstrap_token(project: tuple) -> None:
    repo, env = project
    _write(repo, "scripts/x.py", "# " + _tok("PROJECT") + "\n")
    out = _refused(_commit(repo, env))
    assert "scripts/x.py:1:" in out


def test_ac16d_the_index_not_the_working_tree_decides_template_mode(project: tuple) -> None:
    repo, env = project
    _write(repo, "scripts/x.py", "# " + _tok("PROJECT") + "\n")
    _git(repo, "add", "scripts/x.py", env=env)
    _write(repo, "AGENTS.md", "# AGENTS.md — " + _tok("PROJECT") + "\n")  # not staged
    out = _refused(_commit(repo, env, add=False))
    assert "scripts/x.py:1:" in out


def test_ac16d_agents_md_absent_from_the_index_is_project_mode(project: tuple) -> None:
    repo, env = project
    _git(repo, "rm", "-q", "AGENTS.md", env=env)
    _write(repo, "scripts/x.py", "# " + _tok("PROJECT") + "\n")
    out = _refused(_commit(repo, env))
    assert "scripts/x.py:1:" in out


def test_ac16d_a_project_token_elsewhere_never_switches_template_mode_on(
        project: tuple) -> None:
    repo, env = project
    _write(repo, "doc/AGENTS.md", "# AGENTS.md — " + _tok("PROJECT") + "\n")
    out = _refused(_commit(repo, env))
    assert "doc/AGENTS.md:1:" in out


@pytest.mark.parametrize("name", ["PROJECTS", "FRONTEND_REPO_PATHS", "XPROJECT"])
def test_ac16e_a_near_miss_of_a_bootstrap_token_is_refused_in_template_mode(
        template: tuple, name: str) -> None:
    repo, env = template
    _write(repo, ".claude/agents/x.md", _tok(name) + "\n")
    out = _refused(_commit(repo, env))
    assert ".claude/agents/x.md:1:" in out


# --------------------------------------------------------------------------- AM3-AC17
def test_ac17a_a_token_only_in_an_untracked_file_passes(project: tuple) -> None:
    repo, env = project
    _write(repo, "doc/u.md", _HIT + "\n")
    _write(repo, "notes.txt", "work\n")
    _git(repo, "add", "notes.txt", env=env)
    _passed(_commit(repo, env, add=False))


def test_ac17b_a_token_only_in_an_unstaged_edit_passes_a_plain_commit(project: tuple) -> None:
    repo, env = project
    with (repo / "doc" / "memory" / "README.md").open("a") as handle:
        handle.write(_HIT + "\n")
    _write(repo, "notes.txt", "work\n")
    _git(repo, "add", "notes.txt", env=env)
    _passed(_commit(repo, env, add=False))


def test_ac17c_the_same_edit_under_commit_a_is_refused(project: tuple) -> None:
    repo, env = project
    with (repo / "doc" / "memory" / "README.md").open("a") as handle:
        handle.write(_HIT + "\n")
    out = _refused(_commit(repo, env, "-a", add=False))
    assert "doc/memory/README.md:" in out


def test_ac17d_a_staged_deletion_of_the_only_hit_passes(project: tuple) -> None:
    repo, env = project
    _write(repo, "doc/bad.md", _HIT + "\n")
    _git(repo, "add", "doc/bad.md", env=env)
    assert _git(repo, "commit", "-q", "--no-verify", "-m", "bad", env=env).returncode == 0
    _git(repo, "rm", "-q", "doc/bad.md", env=env)
    _passed(_commit(repo, env, add=False))


def test_ac17e_commit_path_leaves_out_a_token_staged_elsewhere(project: tuple) -> None:
    repo, env = project
    _write(repo, "doc/f.md", "f\n")
    _write(repo, "doc/g.md", "g\n")
    _git(repo, "add", "doc/f.md", "doc/g.md", env=env)
    assert _git(repo, "commit", "-q", "--no-verify", "-m", "fg", env=env).returncode == 0
    _write(repo, "doc/f.md", "f edited\n")
    _write(repo, "doc/g.md", "g " + _HIT + "\n")
    _git(repo, "add", "doc/f.md", "doc/g.md", env=env)
    _passed(_commit(repo, env, "--", "doc/f.md", add=False))


# --------------------------------------------------------------------------- AM3-AC18
@pytest.mark.parametrize("text", [_tok("AB"), _tok("abc_def"), _tok("ABC-DEF"),
                                  "<\u00c0BC_DEF>", "<AB\u00c9CD>"])
def test_ac18_shapes_neither_tool_matches_pass(project: tuple, text: str) -> None:
    repo, env = project
    _write(repo, "doc/x.md", text + "\n")
    out = _passed(_commit(repo, env))
    assert "Traceback" not in out


def test_ac18_a_binary_file_holding_a_token_passes(project: tuple) -> None:
    repo, env = project
    (repo / "doc" / "x.bin").write_bytes(b"\x00\x01" + _HIT.encode() + b"\n")
    _passed(_commit(repo, env))


def test_ac18_a_newline_in_a_file_name_prints_gits_quoted_path_on_one_line(
        project: tuple) -> None:
    repo, env = project
    _write(repo, "doc/a\nb.md", _HIT + "\n")
    out = _refused(_commit(repo, env))
    assert '"doc/a\\nb.md":1:' + _HIT in out


def test_ac18_more_than_twenty_hits_print_twenty_then_the_true_rest(project: tuple) -> None:
    repo, env = project
    _write(repo, "doc/many.md", "".join("%d %s\n" % (i, _HIT) for i in range(1, 26)))
    out = _refused(_commit(repo, env))
    assert "25 line(s)" in out
    shown = re.findall(r"doc/many\.md:(\d+):", out)
    assert shown == [str(i) for i in range(1, 21)], out
    assert "… and 5 more" in out


# --------------------------------------------------------------------------- AM3-AC19
def _real_git() -> str:
    exec_path = subprocess.run(["git", "--exec-path"], capture_output=True, text=True,
                               check=True).stdout.strip()
    candidate = Path(exec_path) / "git"
    return str(candidate) if candidate.is_file() else shutil.which("git") or "git"


def test_ac19_a_scan_that_cannot_run_refuses(project: tuple, tmp_path: Path) -> None:
    """A `git` shim whose `grep` exits 2. Git puts its own exec-path first on a
    hook's PATH (measured 2026-10-22: the hook's PATH began with
    `.../libexec/git-core`, which holds a real `git`), so a shim that is only
    on PATH is never reached. The shim is therefore also the exec-path of the
    outer `git commit`; for everything but `grep` it delegates to the real git."""
    repo, env = project
    real = _real_git()
    shim_dir = tmp_path / "shim"
    shim_dir.mkdir()
    shim = shim_dir / "git"
    shim.write_text('#!/bin/sh\nif [ "$1" = grep ]; then exit 2; fi\n'
                    'unset GIT_EXEC_PATH\nexec "%s" "$@"\n' % real, encoding="utf-8")
    shim.chmod(0o755)
    _write(repo, "notes.txt", "work\n")
    _git(repo, "add", "-A", env=env)
    shimmed = {**env, "GIT_EXEC_PATH": str(shim_dir),
               "PATH": str(shim_dir) + os.pathsep + env["PATH"]}
    before = _head(repo, env)
    result = subprocess.run([real, "commit", "-q", "-m", "c"], cwd=repo, capture_output=True,
                            text=True, env=shimmed, check=False)
    out = result.stdout + result.stderr
    assert result.returncode != 0 and _head(repo, env) == before, out
    assert "FAIL placeholder scan — the scan could not run (git grep exit 2)" in out


# --------------------------------------------------------------------------- AM3-AC21
@pytest.mark.parametrize(("commit", "rel"), [
    ("7661338", "doc/qa/QA-bugfix-gate3-worktree.md"),
    ("e6b4daa", "doc/specs/SPEC-jarvis-coordinator.md"),
])
def test_ac21_both_real_incidents_are_refused(template: tuple, commit: str, rel: str) -> None:
    shown = subprocess.run(["git", "show", "%s:%s" % (commit, rel)], cwd=_REPO_ROOT,
                           capture_output=True, check=False)
    if shown.returncode != 0:
        pytest.skip("incident commit %s is not reachable here (shallow clone?): %s"
                    % (commit, shown.stderr.decode("utf-8", "replace").strip()))
    repo, env = template
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(shown.stdout)
    out = _refused(_commit(repo, env))
    assert re.search(r"^    %s:\d+:" % re.escape(rel), out, re.MULTILINE), out
