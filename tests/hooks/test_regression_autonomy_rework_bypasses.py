"""Regression tests: always-human bypasses QA found in re-test 1 (increment B).

QA-delegated-autonomy-B.md "Re-test 1", 2026-10-20, against 7309362. QA pinned
20 spellings that passed the guard. Amendment 1
(doc/specs/SPEC-delegated-autonomy-am1-guards-catch-accidents.md) declared 17
of them limits — the guards catch accidents, not every shell spelling — and
those pins were retired; the declared list is in that spec's §Declared limits
and in doc/framework/ADAPTERS.md. What stays here:

* Off switch, by shadowing (self-inflicted, so it stays closed): an
  agent-written `scripts/shlex.py` must not make the core fail to import and
  switch AH3 or the path guard off.
* Defect 7 (B-AC10): ordinary read-only tools naming an owner script are
  allowed in every project.

Run: `python3 -m pytest tests/hooks/test_regression_autonomy_rework_bypasses.py -q`
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GUARD_BASH = _REPO_ROOT / ".claude" / "hooks" / "guard_bash.py"

_EXIT_ALLOW = 0
_EXIT_BLOCK = 2
_MANDATE_KEY = "mandate-proj-first-2026-10-20"
_MANDATE = {
    "key": _MANDATE_KEY,
    "artifact": "doc/mandates/MANDATE-proj-first.md",
    "status": "Approved",
    "approved_by": "owner",
    "approved_at": "2026-10-20T09:00:00+07:00",
    "kind": "mandate",
    "expires": "2099-12-31",
}


def _hook(guard: Path, payload: dict, *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(guard)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        cwd=str(cwd),
        env=env,
    )


def _bash(command: str, *, cwd: Path, env: dict[str, str], guard: Path = _GUARD_BASH) -> subprocess.CompletedProcess[str]:
    return _hook(guard, {"tool_name": "Bash", "tool_input": {"command": command}}, cwd=cwd, env=env)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@example.test", "-c", "user.name=t", *args],
        cwd=repo,
        check=True,
        timeout=30,
        capture_output=True,
    )


def _project(base: Path, *, mandate: bool, commit_opt_in: bool) -> tuple[Path, dict[str, str]]:
    """A repo at `base/repo` with one plain commit (tagged `pre-opt-in`), then,
    when `mandate`, the opt-in files (committed if `commit_opt_in`), a mandate
    folder and a live mandate in the registry. HOME is `base`, so the default
    registry is `base/.jarvis/approvals/registry.jsonl`."""
    repo = base / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "feature/x"], cwd=repo, check=True, timeout=30)
    (repo / "tracked.txt").write_text("committed\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")
    _git(repo, "tag", "pre-opt-in")
    registry = base / ".jarvis" / "approvals" / "registry.jsonl"
    registry.parent.mkdir(parents=True)
    registry.write_text("", encoding="utf-8")
    if mandate:
        (repo / "scripts").mkdir()
        (repo / "scripts" / "autonomy.json").write_text(json.dumps({"project": "proj"}), encoding="utf-8")
        (repo / "doc" / "mandates").mkdir(parents=True)
        (repo / "doc" / "mandates" / "MANDATE-proj-first.md").write_text("mandate\n", encoding="utf-8")
        (repo / ".claude").mkdir()
        (repo / ".claude" / "settings.json").write_text('{"hooks": "on"}\n', encoding="utf-8")
        registry.write_text(json.dumps(_MANDATE) + "\n", encoding="utf-8")
        if commit_opt_in:
            _git(repo, "add", "-A")
            _git(repo, "commit", "-qm", "opt in")
    env = {**os.environ, "HOME": str(base), "APPROVAL_LOG": str(registry)}
    return repo, env


@pytest.fixture
def active(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    return _project(tmp_path.resolve(), mandate=True, commit_opt_in=True)


@pytest.fixture
def plain(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    return _project(tmp_path.resolve(), mandate=False, commit_opt_in=False)


# --------------------------------------------------------------------------- off switch: shadowing


def _install_guards(repo: Path) -> None:
    """The guards and the core inside the project, as a real install has them,
    so `scripts/` on the import path is this repo's `scripts/`."""
    shutil.copytree(_REPO_ROOT / ".claude" / "hooks", repo / ".claude" / "hooks")
    for name in ("autonomy.py", "verify_approvals.py"):
        shutil.copy(_REPO_ROOT / "scripts" / name, repo / "scripts" / name)


def test_regression_shadow_module_in_scripts_keeps_ah3_on(active: tuple[Path, dict[str, str]]) -> None:
    repo, env = active
    _install_guards(repo)
    (repo / "scripts" / "shlex.py").write_text("raise ImportError('shadow')\n", encoding="utf-8")

    result = _bash("git push origin main", cwd=repo, env=env, guard=repo / ".claude" / "hooks" / "guard_bash.py")

    assert result.returncode == _EXIT_BLOCK, "an unprotected scripts/shlex.py switched AH3 off under a mandate"


def test_regression_shadow_module_in_scripts_keeps_the_path_guard_on(active: tuple[Path, dict[str, str]]) -> None:
    repo, env = active
    _install_guards(repo)
    (repo / "scripts" / "shlex.py").write_text("raise ImportError('shadow')\n", encoding="utf-8")

    result = _hook(
        repo / ".claude" / "hooks" / "guard_autonomy_paths.py",
        {"tool_name": "Write", "tool_input": {"file_path": str(repo / ".claude" / "settings.json"), "content": "{}"}},
        cwd=repo,
        env=env,
    )

    assert result.returncode == _EXIT_BLOCK, (
        f"Write to .claude/settings.json under a mandate exited {result.returncode}: {result.stderr[-200:]}"
    )


# --------------------------------------------------------------------------- off switch: rewinding the tree


# Retired by SPEC-delegated-autonomy-am1-guards-catch-accidents: rewinding, stashing and restoring from another ref are declared limits (D-L4, D-L5).

# --------------------------------------------------------------------------- owner rule (every project)


# Retired by SPEC-delegated-autonomy-am1-guards-catch-accidents: an owner script run through git or awk, and a registry write through a same-command symlink or cd $HOME are declared limits (D-L1, D-L2, D-L3, D-L6, D-L9).


@pytest.mark.parametrize(
    "command",
    [
        "find . -name approve.sh",
        "ruff check scripts/approve.py",
        "scripts/approve.sh --help",
    ],
)
def test_regression_reading_an_owner_script_stays_allowed(plain: tuple[Path, dict[str, str]], command: str) -> None:
    repo, env = plain

    result = _bash(command, cwd=repo, env=env)

    assert result.returncode == _EXIT_ALLOW, f"{command!r} writes nothing, yet was refused: {result.stderr[:200]}"


# --------------------------------------------------------------------------- AH3 spellings

# Retired by SPEC-delegated-autonomy-am1-guards-catch-accidents: unlisted wrappers, a git alias and --repo= are declared limits (D-L1, D-L7, D-L8).
