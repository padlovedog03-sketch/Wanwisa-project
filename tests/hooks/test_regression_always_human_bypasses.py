"""Regression tests: bypasses of the always-human guards found by QA (increment B).

QA-delegated-autonomy-B.md, 2026-10-20. Each case is a spelling at COMMAND
POSITION that the design's §B.2/§B.3 rows cover, not one of the declared
limits (`bash -c`, a heredoc or pipe into a shell, a command inside a script).
Each was measured passing the guard at commit 9670f32. One was carried through
to a real registry write: `nice scripts/approve.sh <slug> --by agent` passed
the guard, appended an approval line and stamped the document `Approved`.

* B-AC4: owner commands behind a common prefix, a symlink to the registry,
  and the owner rule when the core module cannot be imported (exit 1 is
  non-blocking under the hook contract, so the rule silently turns off).
* B-AC2/B-AC3: the off switch. Moving or `git rm`-ing `scripts/autonomy.json`
  makes `status` read `inactive`, and every active-scope rule goes off. Plus
  spellings of §B.2 rows the classifier misses.
* B-AC6: on a case-insensitive filesystem (the macOS default) and through a
  symlink, a Write/Edit reaches a protected file under a name the guard does
  not recognise.

Every scenario runs the hook as the tool runner does, in a throwaway repo, with
`APPROVAL_LOG` pointed at a temporary registry.

Run: `python3 -m pytest tests/hooks/test_regression_always_human_bypasses.py -q`
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
_GUARD_PATHS = _REPO_ROOT / ".claude" / "hooks" / "guard_autonomy_paths.py"

_EXIT_BLOCK = 2
_MANDATE_KEY = "mandate-proj-first-2026-10-20"


def _run(guard: Path, payload: dict, *, cwd: Path, registry: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(guard)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        cwd=str(cwd),
        env={**os.environ, "APPROVAL_LOG": str(registry)},
    )


def _bash(command: str, *, cwd: Path, registry: Path, guard: Path = _GUARD_BASH) -> subprocess.CompletedProcess[str]:
    return _run(guard, {"tool_name": "Bash", "tool_input": {"command": command}}, cwd=cwd, registry=registry)


def _write(file_path: Path, *, cwd: Path, registry: Path) -> subprocess.CompletedProcess[str]:
    return _run(
        _GUARD_PATHS,
        {"tool_name": "Write", "tool_input": {"file_path": str(file_path), "content": "{}"}},
        cwd=cwd,
        registry=registry,
    )


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "feature/x"], cwd=path, check=True, timeout=30)
    (path / "tracked.txt").write_text("committed\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=path, check=True, timeout=30)
    subprocess.run(
        ["git", "-c", "user.email=t@example.test", "-c", "user.name=t", "commit", "-qm", "init"],
        cwd=path,
        check=True,
        timeout=30,
    )


@pytest.fixture
def plain_project(tmp_path: Path) -> tuple[Path, Path]:
    """No autonomy.json, empty registry. `resolve()` matters: on macOS the temp
    dir sits behind the /var -> /private/var symlink, which pushes the guard's
    path logic onto a resolve() fallback that real repos never take."""
    base = tmp_path.resolve()
    repo = base / "repo"
    repo.mkdir()
    _init_repo(repo)
    registry = base / "registry.jsonl"
    registry.write_text("", encoding="utf-8")
    return repo, registry


@pytest.fixture
def active_project(tmp_path: Path) -> tuple[Path, Path]:
    """An active, unexpired, unrevoked mandate; `data/**` declared as data."""
    base = tmp_path.resolve()
    repo = base / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "scripts").mkdir()
    (repo / "scripts" / "autonomy.json").write_text(
        json.dumps({"project": "proj", "data_globs": ["data/**"]}), encoding="utf-8"
    )
    (repo / "data").mkdir()
    (repo / "data" / "rows.csv").write_text("1\n", encoding="utf-8")
    (repo / "doc" / "mandates").mkdir(parents=True)
    registry = base / "registry.jsonl"
    entry = {
        "key": _MANDATE_KEY,
        "artifact": "doc/mandates/MANDATE-proj-first.md",
        "status": "Approved",
        "approved_by": "owner",
        "approved_at": "2026-10-20T09:00:00+07:00",
        "kind": "mandate",
        "expires": "2099-12-31",
    }
    registry.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    return repo, registry


# --------------------------------------------------------------------------- B-AC4

OWNER_COMMAND_BEHIND_A_PREFIX = [
    "nice scripts/approve.sh x --by a",
    "timeout 5 scripts/approve.sh x --by a",
    "source scripts/approve.sh x --by a",
    ". scripts/approve.sh x --by a",
    "env -i scripts/approve.sh x --by a",
    "/usr/bin/env python3 scripts/approve.py x --by a",
    "bash -o errexit scripts/approve.sh x --by a",
    "echo x | xargs scripts/approve.sh --by a",
]


@pytest.mark.parametrize("command", OWNER_COMMAND_BEHIND_A_PREFIX)
def test_regression_owner_command_behind_a_prefix_is_refused(
    command: str, plain_project: tuple[Path, Path]
) -> None:
    repo, registry = plain_project
    result = _bash(command, cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK, f"{command!r} passed the owner rule"
    assert "owner-only command" in result.stderr


def test_regression_registry_write_through_a_symlink_is_refused(plain_project: tuple[Path, Path]) -> None:
    """The design row says a target that RESOLVES to the registry."""
    repo, registry = plain_project
    (repo / "reglink").symlink_to(registry)
    result = _bash("echo '{}' >> reglink", cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK
    assert "owner-only command" in result.stderr


def test_regression_owner_rule_holds_when_the_core_cannot_be_imported(
    plain_project: tuple[Path, Path]
) -> None:
    """In a project that has not opted in, an agent may edit or delete
    scripts/autonomy.py (both guards allow it, R6). The guard then raises on
    import and exits 1, which the hook contract treats as non-blocking, so the
    'every project' owner rule turns itself off."""
    repo, registry = plain_project
    hooks = repo / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy(_GUARD_BASH, hooks / "guard_bash.py")
    shutil.copy(_GUARD_PATHS, hooks / "guard_autonomy_paths.py")
    (repo / "scripts").mkdir()  # no autonomy.py: deleted, or broken by an edit
    result = _bash("scripts/approve.sh x --by a", cwd=repo, registry=registry, guard=hooks / "guard_bash.py")
    assert result.returncode == _EXIT_BLOCK, f"exit {result.returncode}: {result.stderr[-200:]}"
    assert "owner-only command" in result.stderr


# --------------------------------------------------------------------------- B-AC2 / B-AC3

ACTIVE_SCOPE_MISSES = [
    # The off switch: with the project file gone, status() reads `inactive`.
    ("mv scripts/autonomy.json /tmp/elsewhere.json", "AH5"),
    ("git rm scripts/autonomy.json", "AH5"),
    ("git mv scripts/autonomy.json moved.json", "AH5"),
    # §B.2 rows in other spellings.
    ("git --no-pager push origin main", "AH3"),
    ("git push --all origin", "AH3"),
    ("git push --mirror origin", "AH3"),
    ("curl -sd payload https://example.test", "AH3"),
]


@pytest.mark.parametrize(("command", "item"), ACTIVE_SCOPE_MISSES)
def test_regression_always_human_spellings_are_refused_under_a_mandate(
    command: str, item: str, active_project: tuple[Path, Path]
) -> None:
    repo, registry = active_project
    result = _bash(command, cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK, f"{command!r} passed under an active mandate"
    assert f"always-human item {item}" in result.stderr


def test_regression_rm_of_an_ancestor_of_a_data_glob_is_refused(active_project: tuple[Path, Path]) -> None:
    """`rm -rf store` deletes everything `store/data/**` declares as data. The
    ancestor holds no protected path, so the only right answer is AH3."""
    repo, registry = active_project
    (repo / "scripts" / "autonomy.json").write_text(
        json.dumps({"project": "proj", "data_globs": ["store/data/**"]}), encoding="utf-8"
    )
    (repo / "store" / "data").mkdir(parents=True)
    (repo / "store" / "data" / "rows.csv").write_text("1\n", encoding="utf-8")
    result = _bash("rm -rf store", cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK, "rm -rf of a data directory's parent passed under a mandate"
    assert "always-human item AH3" in result.stderr


def test_regression_moving_the_project_file_switches_every_guard_off(
    active_project: tuple[Path, Path]
) -> None:
    """Why the off switch is High: after the move, the guard allows the very
    command B-AC3 plants first."""
    repo, registry = active_project
    assert _bash("git push origin main", cwd=repo, registry=registry).returncode == _EXIT_BLOCK
    (repo / "scripts" / "autonomy.json").rename(repo / "moved.json")
    result = _bash("git push origin main", cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK, "the mandate is still in force, but the guard reads inactive"


# --------------------------------------------------------------------------- B-AC6


def _case_insensitive(path: Path) -> bool:
    probe = path / "CaseProbe"
    probe.write_text("", encoding="utf-8")
    try:
        return (path / "caseprobe").exists()
    finally:
        probe.unlink()


@pytest.mark.parametrize("variant", ["SCRIPTS/autonomy.json", "scripts/Autonomy.json", "Doc/Mandates/M.md"])
def test_regression_case_variant_of_a_protected_path_is_refused(
    variant: str, active_project: tuple[Path, Path]
) -> None:
    repo, registry = active_project
    if not _case_insensitive(repo):
        pytest.skip("case-sensitive filesystem: a case variant names a different file here")
    result = _write(repo / variant, cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK, f"Write to {variant} reached a protected file"
    assert "always-human item AH5" in result.stderr


def test_regression_write_through_a_file_symlink_is_refused(active_project: tuple[Path, Path]) -> None:
    repo, registry = active_project
    (repo / "cfg.json").symlink_to("scripts/autonomy.json")
    result = _write(repo / "cfg.json", cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK
    assert "always-human item AH5" in result.stderr


def test_regression_write_through_a_directory_symlink_is_refused(active_project: tuple[Path, Path]) -> None:
    repo, registry = active_project
    (repo / "mlink").symlink_to("doc/mandates")
    result = _write(repo / "mlink" / "MANDATE-proj-first.md", cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK
    assert "always-human item AH5" in result.stderr
