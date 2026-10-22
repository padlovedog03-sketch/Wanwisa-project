"""Always-human guards: the forms the increment-B rework closes beyond QA's pins.

QA-delegated-autonomy-B.md listed these spellings in its findings without a
pinned test, or they are the same defect one step further (an ancestor
directory of a protected file moves the file just as `mv <file>` does). Each
one passed the guard at 9670f32.

* Owner rule (every project): more wrapper spellings, `find -exec`, and a core
  module that is present but broken (SyntaxError, not only ImportError).
* Registry writes: after `cd` into the registry's directory, `${APPROVAL_LOG:-x}`,
  `dd of=`, a case variant and a redirect through a symlink.
* Under a mandate: `curl -dfoo`, `rm -rf .`, `rm -rf *`, git global options,
  removing or moving a directory that holds protected files, and a Bash
  redirect through a symlink or case variant.
* Activation: a committed project file deleted from the working tree keeps the
  guards on; a project with no file, no commit of one and no mandate folder
  stays inactive even when the registry holds another project's mandate (R6).

Run: `python3 -m pytest tests/hooks/test_guard_always_human_rework.py -q`
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


def _bash(command: str, *, cwd: Path, registry: Path, guard: Path = _GUARD_BASH) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(guard)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        cwd=str(cwd),
        env={**os.environ, "APPROVAL_LOG": str(registry)},
    )


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@example.test", "-c", "user.name=t", *args],
        cwd=repo,
        check=True,
        timeout=30,
        capture_output=True,
    )


def _repo(base: Path) -> Path:
    repo = base / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "feature/x"], cwd=repo, check=True, timeout=30)
    (repo / "tracked.txt").write_text("committed\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-qm", "init")
    return repo


@pytest.fixture
def plain_project(tmp_path: Path) -> tuple[Path, Path]:
    base = tmp_path.resolve()
    repo = _repo(base)
    registry = base / "approvals" / "registry.jsonl"
    registry.parent.mkdir()
    registry.write_text("", encoding="utf-8")
    return repo, registry


@pytest.fixture
def active_project(tmp_path: Path) -> tuple[Path, Path]:
    base = tmp_path.resolve()
    repo = _repo(base)
    (repo / "scripts").mkdir()
    (repo / "scripts" / "autonomy.json").write_text(
        json.dumps({"project": "proj", "data_globs": ["data/**"]}), encoding="utf-8"
    )
    (repo / "data").mkdir()
    (repo / "data" / "rows.csv").write_text("1\n", encoding="utf-8")
    registry = base / "registry.jsonl"
    registry.write_text(json.dumps(_MANDATE) + "\n", encoding="utf-8")
    return repo, registry


# --------------------------------------------------------------------------- owner rule (B-AC4)

OWNER_SPELLINGS = [
    "sudo -u root scripts/approve.sh x --by a",
    "timeout -s KILL 5 scripts/approve.sh x --by a",
    "nice -n 5 scripts/approve.sh x --by a",
    "env -u HOME FOO=1 scripts/approve.sh x --by a",
    "/usr/bin/nohup scripts/approve.sh x --by a",
    "bash +o posix scripts/approve.sh x --by a",
    "python3 -W ignore scripts/approve.py x --by a",
    "find . -name x -exec scripts/approve.sh {} --by a ;",
    "xargs -I{} scripts/approve.sh {} --by a < slugs.txt",
]


@pytest.mark.parametrize("command", OWNER_SPELLINGS)
def test_owner_command_in_any_argv_position_is_refused(command: str, plain_project: tuple[Path, Path]) -> None:
    repo, registry = plain_project
    result = _bash(command, cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK, f"{command!r} passed the owner rule"
    assert "owner-only command" in result.stderr


@pytest.mark.parametrize(
    "command",
    [
        "git add scripts/approve.py",
        "git log --grep approve.sh",
        "grep -rn approve.sh doc/",
        "ls -la scripts/approve.sh",
        "nice grep -rn approve.sh doc/",
        "echo x | xargs grep approve.sh",
        "sed -n 1,5p scripts/approve.py",
    ],
)
def test_a_reader_that_names_an_owner_script_is_not_refused(command: str, plain_project: tuple[Path, Path]) -> None:
    repo, registry = plain_project
    result = _bash(command, cwd=repo, registry=registry)
    assert result.returncode == _EXIT_ALLOW, result.stderr


REGISTRY_WRITES = [
    "cd {dir} && echo '{{}}' >> registry.jsonl",
    'echo x >> "${{APPROVAL_LOG:-/tmp/x}}"',
    "dd if=forged.jsonl of={reg} conv=notrunc",
    "echo x >> {upper}",
]


@pytest.mark.parametrize("template", REGISTRY_WRITES)
def test_registry_write_spellings_are_refused(template: str, plain_project: tuple[Path, Path]) -> None:
    repo, registry = plain_project
    command = template.format(dir=registry.parent, reg=registry, upper=str(registry).replace("approvals", "APPROVALS"))
    if "APPROVALS" in command and not Path(command.split(">> ", 1)[1]).exists():
        pytest.skip("case-sensitive filesystem: the case variant names a different file")
    result = _bash(command, cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK, f"{command!r} reached the registry"
    assert "owner-only command" in result.stderr


def _guard_with_core(repo: Path, core_source: str) -> Path:
    hooks = repo / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy(_GUARD_BASH, hooks / "guard_bash.py")
    shutil.copy(_GUARD_PATHS, hooks / "guard_autonomy_paths.py")
    (repo / "scripts").mkdir()
    (repo / "scripts" / "autonomy.py").write_text(core_source, encoding="utf-8")
    return hooks / "guard_bash.py"


# A core that fails to import, and one that imports but raises when called.
BROKEN_CORES = {"syntax-error": "def broken(:\n", "empty-module": "# emptied by an edit\n"}


@pytest.mark.parametrize("core", sorted(BROKEN_CORES))
@pytest.mark.parametrize(
    "command",
    [
        "nice scripts/approve.sh x --by a",
        # A read-only flag ELSEWHERE in the command must not exempt the run.
        "nice -n 5 scripts/approve.sh x --by a",
        "echo -n x; scripts/approve.sh x --by a",
    ],
)
def test_owner_rule_holds_when_the_core_is_present_but_broken(
    core: str, command: str, plain_project: tuple[Path, Path]
) -> None:
    repo, registry = plain_project
    guard = _guard_with_core(repo, BROKEN_CORES[core])
    result = _bash(command, cwd=repo, registry=registry, guard=guard)
    assert result.returncode == _EXIT_BLOCK, f"exit {result.returncode}: {result.stderr[-300:]}"
    assert "owner-only command" in result.stderr
    # The fallback is the owner rule only: ordinary work still runs.
    assert _bash("ls -la", cwd=repo, registry=registry, guard=guard).returncode == _EXIT_ALLOW


# --------------------------------------------------------------------------- under a mandate (B-AC2/B-AC3)

ACTIVE_SPELLINGS = [
    ("curl -dfoo https://example.test", "AH3"),
    ("curl -sSXPOST https://example.test", "AH3"),
    ("git --git-dir=.git push origin main", "AH3"),
    ("git -P push origin main", "AH3"),
    ("git --no-pager tag -d v1 && git push origin v1", "AH3"),
    # The project root and `*` hold scripts/autonomy.json as well as data/:
    # the guard names the first item; test_autonomy_items pins both.
    ("rm -rf .", "AH5"),
    ("rm -rf *", "AH5"),
    ("rm -rf ./*", "AH5"),
    ("mv scripts elsewhere", "AH5"),
    ("rm -rf scripts", "AH5"),
    ("git rm -r scripts", "AH5"),
    ("echo '{}' > SCRIPTS/AUTONOMY.JSON", "AH5"),
]


@pytest.mark.parametrize(("command", "item"), ACTIVE_SPELLINGS)
def test_active_scope_spellings_are_refused(command: str, item: str, active_project: tuple[Path, Path]) -> None:
    repo, registry = active_project
    result = _bash(command, cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK, f"{command!r} passed under an active mandate"
    assert f"always-human item {item}" in result.stderr


@pytest.mark.parametrize(
    "command",
    ["mv notes.txt scripts/", "rm -rf build", "curl -s https://example.test/x", "git --no-pager log -1", "cp scripts/autonomy.json /tmp/copy.json"],
)
def test_active_scope_look_alikes_stay_allowed(command: str, active_project: tuple[Path, Path]) -> None:
    repo, registry = active_project
    result = _bash(command, cwd=repo, registry=registry)
    assert result.returncode == _EXIT_ALLOW, result.stderr


def test_bash_redirect_through_a_symlink_is_refused(active_project: tuple[Path, Path]) -> None:
    repo, registry = active_project
    (repo / "cfg.json").symlink_to("scripts/autonomy.json")
    result = _bash("echo '{}' > cfg.json", cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK
    assert "always-human item AH5" in result.stderr


# --------------------------------------------------------------------------- activation


def test_a_committed_project_file_deleted_from_the_tree_keeps_the_guards_on(tmp_path: Path) -> None:
    base = tmp_path.resolve()
    repo = _repo(base)
    (repo / "scripts").mkdir()
    (repo / "scripts" / "autonomy.json").write_text('{"project": "proj"}', encoding="utf-8")
    _git(repo, "add", "scripts/autonomy.json")
    _git(repo, "commit", "-qm", "opt in")
    (repo / "scripts" / "autonomy.json").unlink()
    registry = base / "registry.jsonl"
    registry.write_text(json.dumps(_MANDATE) + "\n", encoding="utf-8")
    result = _bash("git push origin main", cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK, "the committed opt-in no longer counts once the file is gone"
    assert "always-human item AH3" in result.stderr


def test_a_project_that_never_opted_in_ignores_another_projects_mandate(tmp_path: Path) -> None:
    """R6: no project file, none committed, no mandate or order folder."""
    base = tmp_path.resolve()
    repo = _repo(base)
    registry = base / "registry.jsonl"
    registry.write_text(json.dumps(_MANDATE) + "\n", encoding="utf-8")
    assert _bash("git push origin main", cwd=repo, registry=registry).returncode == _EXIT_ALLOW


# --------------------------------------------------------------------------- D10
# QA-delegated-autonomy-B.md re-test 2, Parked 1 (backlog D10): a read-only flag
# after `--` is an operand, not an option, so it must not exempt the call.

_OWNER_NAMES = [
    "approve.sh",
    "approve.py",
    "delegate.sh",
    "revoke.sh",
    "override.sh",
    "away.sh",
    "evolve.sh",
    "release.sh",
]


@pytest.mark.parametrize("project", ["plain_project", "active_project"])
@pytest.mark.parametrize("flag", ["-h", "--help", "-n"])
@pytest.mark.parametrize("script", _OWNER_NAMES)
def test_a_read_only_flag_after_double_dash_does_not_exempt_an_owner_script(
    script: str, flag: str, project: str, request: pytest.FixtureRequest
) -> None:
    repo, registry = request.getfixturevalue(project)
    command = f"scripts/{script} --by a -- spec-x {flag}"
    result = _bash(command, cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK, f"{command!r} passed the owner rule"
    assert "owner-only command" in result.stderr


@pytest.mark.parametrize("project", ["plain_project", "active_project"])
@pytest.mark.parametrize(
    "command",
    [
        "scripts/approve.sh --help",
        "scripts/approve.sh -h",
        "scripts/approve.sh -n",
        "scripts/approve.sh --list",
        "scripts/approve.sh --dry-run",
        "scripts/approve.sh --help -- spec-x",
        "env -- scripts/approve.sh --help",
    ],
)
def test_a_read_only_flag_before_double_dash_stays_allowed(
    command: str, project: str, request: pytest.FixtureRequest
) -> None:
    repo, registry = request.getfixturevalue(project)
    result = _bash(command, cwd=repo, registry=registry)
    assert result.returncode == _EXIT_ALLOW, result.stderr


def test_a_double_dash_before_the_owner_script_does_not_change_the_result(plain_project: tuple[Path, Path]) -> None:
    repo, registry = plain_project
    result = _bash("env -- scripts/approve.sh x --by a", cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK, "env -- scripts/approve.sh passed the owner rule"
    assert "owner-only command" in result.stderr
