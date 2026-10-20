"""A stdlib name written into `scripts/` must not change what the autonomy
guards or the commit-msg check decide (SPEC-delegated-autonomy B-AC4, B-AC6, B-AC7).

QA-delegated-autonomy-B.md re-test 1, defect 1: the guards and the commit-msg
CLI put `scripts/` ahead of the standard library on the import path, so an
agent-written `scripts/<stdlib name>.py` replaced the module the core imports.
QA pinned `shlex` and `argparse` with a shadow that raises ImportError. These
cases use other names and a harsher shadow, `raise SystemExit(0)`: it is not an
`Exception`, so the guards' fallback cannot catch it, and exit 0 means "allow"
to a hook and "pass" to commit-msg.

Run: `python3 -m pytest tests/hooks/test_autonomy_stdlib_shadowing.py -q`
"""

from __future__ import annotations

import json
import os
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXIT_BLOCK = 2
_SHADOW = "raise SystemExit(0)\n"
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
_GIT_ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.test",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.test",
}


def _git(repo: Path, *args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, env=env, timeout=30, check=False
    )


def _project(base: Path) -> tuple[Path, dict[str, str]]:
    """A repo under a live mandate, with the guards, the core and commit-msg
    installed in it the way a real project has them."""
    repo = base / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / "doc" / "mandates").mkdir(parents=True)
    shutil.copytree(_REPO_ROOT / ".claude" / "hooks", repo / ".claude" / "hooks")
    (repo / ".claude" / "settings.json").write_text('{"hooks": "on"}\n', encoding="utf-8")
    (repo / ".githooks").mkdir()
    shutil.copy(_REPO_ROOT / ".githooks" / "commit-msg", repo / ".githooks" / "commit-msg")
    for name in ("autonomy.py", "verify_approvals.py", "check_fix_has_test.py"):
        shutil.copy(_REPO_ROOT / "scripts" / name, repo / "scripts" / name)
    (repo / "scripts" / "autonomy.json").write_text('{"project": "proj"}\n', encoding="utf-8")
    (repo / "doc" / "mandates" / "MANDATE-proj-first.md").write_text("mandate\n", encoding="utf-8")
    registry = base / "registry.jsonl"
    registry.write_text("", encoding="utf-8")
    env = {**os.environ, **_GIT_ENV, "HOME": str(base), "APPROVAL_LOG": str(registry)}
    assert _git(repo, "init", "-q", "-b", "feature/x", env=env).returncode == 0
    _git(repo, "config", "core.hooksPath", ".githooks", env=env)
    _git(repo, "add", "-A", env=env)
    opted = _git(repo, "commit", "-q", "-m", "chore: opt in", env=env)
    assert opted.returncode == 0, opted.stderr
    registry.write_text(json.dumps(_MANDATE) + "\n", encoding="utf-8")
    return repo, env


def _hook(repo: Path, guard: str, payload: dict, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(repo / ".claude" / "hooks" / guard)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        cwd=str(repo),
        env=env,
    )


# The names a guard has not already imported by the time it loads the core;
# a name the guard imported first (json, re) cannot be shadowed through it.
_GUARD_NAMES = ("dataclasses", "datetime")
# commit-msg starts a fresh interpreter on the core, so every import counts.
_COMMIT_NAMES = ("json", "subprocess")


@pytest.fixture
def project(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    return _project(tmp_path.resolve())


def test_without_a_shadow_the_cases_below_are_refused(project: tuple[Path, dict[str, str]]) -> None:
    """Control: the same three actions are refused when `scripts/` holds no shadow."""
    repo, env = project

    push = _hook(repo, "guard_bash.py", {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}}, env)
    write = _hook(
        repo,
        "guard_autonomy_paths.py",
        {"tool_name": "Write", "tool_input": {"file_path": str(repo / ".claude" / "settings.json"), "content": "{}"}},
        env,
    )
    (repo / "doc" / "mandates" / "MANDATE-proj-first.md").write_text("widened\n", encoding="utf-8")
    _git(repo, "add", "-A", env=env)
    commit = _git(repo, "commit", "-q", "-m", "chore: tidy", env=env)

    assert push.returncode == _EXIT_BLOCK, push.stderr
    assert write.returncode == _EXIT_BLOCK, write.stderr
    assert commit.returncode != 0 and "AH5" in commit.stderr, commit.stderr


@pytest.mark.parametrize("name", _GUARD_NAMES)
def test_a_stdlib_shadow_in_scripts_keeps_ah3_on(project: tuple[Path, dict[str, str]], name: str) -> None:
    repo, env = project
    (repo / "scripts" / f"{name}.py").write_text(_SHADOW, encoding="utf-8")

    result = _hook(repo, "guard_bash.py", {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}}, env)

    assert result.returncode == _EXIT_BLOCK, f"scripts/{name}.py switched AH3 off: exit {result.returncode}"
    assert "AH3" in result.stderr, result.stderr


@pytest.mark.parametrize("name", _GUARD_NAMES)
def test_a_stdlib_shadow_in_scripts_keeps_the_path_guard_on(project: tuple[Path, dict[str, str]], name: str) -> None:
    repo, env = project
    (repo / "scripts" / f"{name}.py").write_text(_SHADOW, encoding="utf-8")

    result = _hook(
        repo,
        "guard_autonomy_paths.py",
        {"tool_name": "Write", "tool_input": {"file_path": str(repo / ".claude" / "settings.json"), "content": "{}"}},
        env,
    )

    assert result.returncode == _EXIT_BLOCK, f"scripts/{name}.py switched the path guard off: exit {result.returncode}"


@pytest.mark.parametrize("name", _COMMIT_NAMES)
def test_a_stdlib_shadow_in_scripts_keeps_the_commit_check_on(project: tuple[Path, dict[str, str]], name: str) -> None:
    repo, env = project
    (repo / "doc" / "mandates" / "MANDATE-proj-first.md").write_text("widened\n", encoding="utf-8")
    (repo / "scripts" / f"{name}.py").write_text(_SHADOW, encoding="utf-8")
    _git(repo, "add", "-A", env=env)

    result = _git(repo, "commit", "-q", "-m", "chore: tidy", env=env)

    assert result.returncode != 0, f"a mandate edit with no trailer passed commit-msg behind scripts/{name}.py"
    assert "AH5" in result.stderr, result.stderr


def test_pythonpath_cannot_shadow_the_commit_check(project: tuple[Path, dict[str, str]], tmp_path: Path) -> None:
    """The commit-msg CLI runs isolated, so a PYTHONPATH in the committer's
    environment cannot put a shadow ahead of the stdlib either."""
    repo, env = project
    shadow_dir = tmp_path / "shadow"
    shadow_dir.mkdir()
    (shadow_dir / "argparse.py").write_text(_SHADOW, encoding="utf-8")
    (repo / "doc" / "mandates" / "MANDATE-proj-first.md").write_text("widened\n", encoding="utf-8")
    _git(repo, "add", "-A", env=env)

    result = _git(repo, "commit", "-q", "-m", "chore: tidy", env={**env, "PYTHONPATH": str(shadow_dir)})

    assert result.returncode != 0, "a mandate edit with no trailer passed commit-msg behind PYTHONPATH"
    assert "AH5" in result.stderr, result.stderr


# --------------------------------------------------------------------------- the core itself, by name


def _plant_package(repo: Path, module: str) -> None:
    """A package directory beats a module file in the same path entry."""
    (repo / "scripts" / module).mkdir()
    (repo / "scripts" / module / "__init__.py").write_text(_SHADOW, encoding="utf-8")


def _plant_pyc(repo: Path, module: str, mode: str) -> None:
    """A forged bytecode cache for `scripts/<module>.py`: an unchecked-hash pyc
    is never compared with its source, and a timestamp pyc only by the mtime
    and size in its header, which are copied from the real source."""
    source = repo / "scripts" / f"{module}.py"
    evil = repo / "scripts" / "_evil.py"
    evil.write_text(_SHADOW, encoding="utf-8")
    cache = repo / "scripts" / "__pycache__" / f"{module}.{sys.implementation.cache_tag}.pyc"
    cache.parent.mkdir(exist_ok=True)
    invalidation = (
        py_compile.PycInvalidationMode.UNCHECKED_HASH if mode == "unchecked" else py_compile.PycInvalidationMode.TIMESTAMP
    )
    py_compile.compile(str(evil), cfile=str(cache), invalidation_mode=invalidation, doraise=True)
    evil.unlink()
    if mode == "timestamp":
        stat = source.stat()
        header = bytearray(cache.read_bytes())
        header[8:12] = (int(stat.st_mtime) & 0xFFFFFFFF).to_bytes(4, "little")
        header[12:16] = (stat.st_size & 0xFFFFFFFF).to_bytes(4, "little")
        cache.write_bytes(bytes(header))


_PLANTS = {
    "package-autonomy": lambda repo: _plant_package(repo, "autonomy"),
    "package-verify_approvals": lambda repo: _plant_package(repo, "verify_approvals"),
    "pyc-unchecked-autonomy": lambda repo: _plant_pyc(repo, "autonomy", "unchecked"),
    "pyc-timestamp-autonomy": lambda repo: _plant_pyc(repo, "autonomy", "timestamp"),
    "pyc-unchecked-verify_approvals": lambda repo: _plant_pyc(repo, "verify_approvals", "unchecked"),
    "pyc-timestamp-verify_approvals": lambda repo: _plant_pyc(repo, "verify_approvals", "timestamp"),
    # Control: scripts/ is a path entry, not a package, so this is never run.
    "scripts-init": lambda repo: (repo / "scripts" / "__init__.py").write_text(_SHADOW, encoding="utf-8"),
}


@pytest.mark.parametrize("plant", sorted(_PLANTS))
def test_a_planted_copy_of_the_core_does_not_replace_it(project: tuple[Path, dict[str, str]], plant: str) -> None:
    """The guards and commit-msg load the core from its source file, so a
    package directory or a bytecode cache under `scripts/` cannot stand in for it."""
    repo, env = project
    _PLANTS[plant](repo)

    push = _hook(repo, "guard_bash.py", {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}}, env)
    write = _hook(
        repo,
        "guard_autonomy_paths.py",
        {"tool_name": "Write", "tool_input": {"file_path": str(repo / ".claude" / "settings.json"), "content": "{}"}},
        env,
    )
    (repo / "doc" / "mandates" / "MANDATE-proj-first.md").write_text("widened\n", encoding="utf-8")
    _git(repo, "add", "doc", env=env)
    commit = _git(repo, "commit", "-q", "-m", "chore: tidy", env=env)

    assert (push.returncode, write.returncode, commit.returncode != 0) == (_EXIT_BLOCK, _EXIT_BLOCK, True), (
        f"{plant}: guard_bash={push.returncode} path_guard={write.returncode} commit_msg={commit.returncode}"
    )
