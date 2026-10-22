"""`guard_bash.py` — the always-human rules (SPEC-delegated-autonomy, increment B).

Two rules with two different scopes, tested apart on purpose:

* **B-AC4 owner-script rule — always on.** An agent's Bash call to an owner
  command (`approve.sh` and the other owner wrappers) or a shell write into the
  approval registry is refused in EVERY project, autonomy or not. Before this
  rule the registry guard watched only the Write/Edit tools, so
  `scripts/approve.sh <slug> --by <name>` from an agent was not intercepted at
  all — the agent could approve its own upstream.
* **B-AC3 always-human command rule — only while autonomy is active.** Each
  planted attempt per item is refused under an active mandate, and the same
  command is allowed in a project that has not opted in (R6: nothing changes
  for a project that did not ask for this).

Every scenario runs the hook as the tool runner does (JSON on stdin, exit code
out) with its cwd in a throwaway git repo and `APPROVAL_LOG` pointed at a
temporary registry — the real registry is never read or written.

Run: `python3 -m pytest tests/hooks/ -q`   (stdlib + git)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GUARD = _REPO_ROOT / ".claude" / "hooks" / "guard_bash.py"

_EXIT_ALLOW = 0
_EXIT_BLOCK = 2

_MANDATE_KEY = "mandate-proj-first-2026-10-20"
_CONFIG = {
    "project": "proj",
    "data_globs": ["data/**"],
    "deploy_prod_patterns": ["scripts/deploy.sh prod"],
    "spend_patterns": ["cloudctl buy"],
}


def _registry_entry(**extra: str) -> dict:
    entry = {
        "key": _MANDATE_KEY,
        "artifact": "doc/mandates/MANDATE-proj-first.md",
        "status": "Approved",
        "approved_by": "owner",
        "approved_at": "2026-10-20T09:00:00+07:00",
        "kind": "mandate",
        "expires": "2099-12-31",
    }
    entry.update(extra)
    return entry


def _run_guard(command: str, *, cwd: Path, registry: Path) -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    return subprocess.run(
        [sys.executable, str(_GUARD)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        cwd=str(cwd),
        env={**os.environ, "APPROVAL_LOG": str(registry)},
    )


def _init_repo(path: Path, *, branch: str = "feature/x") -> None:
    subprocess.run(["git", "init", "-q", "-b", branch], cwd=path, check=True, timeout=30)
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
    """A project that has NOT opted in: no autonomy.json, empty registry."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    registry = tmp_path / "registry.jsonl"
    registry.write_text("", encoding="utf-8")
    return repo, registry


@pytest.fixture
def active_project(tmp_path: Path) -> tuple[Path, Path]:
    """A project under an active, unexpired, unrevoked mandate."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "scripts").mkdir()
    (repo / "scripts" / "autonomy.json").write_text(json.dumps(_CONFIG), encoding="utf-8")
    registry = tmp_path / "registry.jsonl"
    registry.write_text(json.dumps(_registry_entry()) + "\n", encoding="utf-8")
    return repo, registry


# --------------------------------------------------------------------------- B-AC4

OWNER_ONLY = [
    "scripts/approve.sh x --by a",
    "./scripts/approve.sh x",
    "bash scripts/approve.sh x",
    "python3 scripts/approve.py x",
    'scripts/delegate.sh "t" --by a',
    "scripts/revoke.sh k",
    "scripts/override.sh d",
    "scripts/away.sh --until d",
    "scripts/evolve.sh",
    "echo '{\"key\": \"k\"}' >> ~/.jarvis/approvals/registry.jsonl",
    'tee -a "$APPROVAL_LOG"',
    # Spellings that must not slip past: an env prefix, a wrapper, a chain.
    "APPROVAL_LOG=/tmp/x scripts/approve.sh y --by a",
    "nohup scripts/approve.sh y --by a",
    "cd scripts && ./approve.sh y --by a",
]


@pytest.mark.parametrize("command", OWNER_ONLY)
def test_owner_commands_are_refused_in_a_project_without_autonomy(
    command: str, plain_project: tuple[Path, Path]
) -> None:
    repo, registry = plain_project
    result = _run_guard(command, cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK, f"{command!r} allowed: {result.stderr}"
    assert "owner-only command" in result.stderr


@pytest.mark.parametrize("command", OWNER_ONLY[:3])
def test_owner_commands_are_refused_under_autonomy_too(
    command: str, active_project: tuple[Path, Path]
) -> None:
    repo, registry = active_project
    result = _run_guard(command, cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK
    assert "owner-only command" in result.stderr


def test_allow_destructive_does_not_waive_the_owner_rule(plain_project: tuple[Path, Path]) -> None:
    """The A1' escape hatch is scoped to discards. An override that also
    waived this rule would hand the agent the approval stamp."""
    repo, registry = plain_project
    result = _run_guard("ALLOW_DESTRUCTIVE=1 scripts/approve.sh x --by a", cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK
    assert "owner-only command" in result.stderr


@pytest.mark.parametrize(
    "command",
    [
        "scripts/approve.sh --list",
        "python3 scripts/approve.py --dry-run x",
        "grep -rn 'scripts/approve.sh' .",
        "cat ~/.jarvis/approvals/registry.jsonl",
        "echo hi 2>&1 >/dev/null",
    ],
)
def test_read_only_owner_commands_and_mentions_stay_allowed(
    command: str, plain_project: tuple[Path, Path]
) -> None:
    repo, registry = plain_project
    result = _run_guard(command, cwd=repo, registry=registry)
    assert result.returncode == _EXIT_ALLOW, result.stderr


# --------------------------------------------------------------------------- B-AC10
# SPEC-delegated-autonomy-am1-guards-catch-accidents B-AC10 (defect 7): ordinary
# read-only work that names an owner script is allowed in every project; its
# hostile neighbours, which run the script, stay refused.

READS_AN_OWNER_SCRIPT = [
    "find . -name approve.sh",
    "ruff check scripts/approve.py",
    "scripts/approve.sh --help",
    "scripts/approve.sh -h",
    "scripts/approve.sh spec-x --by a --help",
    "nl scripts/approve.sh",
    "sort scripts/approve.sh",
    "bash -n scripts/approve.sh",
    "python3 -m py_compile scripts/approve.py",
]

RUNS_AN_OWNER_SCRIPT = [
    "find . -name approve.sh -exec sh {} \\;",
    "find . -name approve.sh -execdir sh {} \\;",
    "find . -name approve.sh -ok sh {} \\;",
    "bash scripts/approve.sh x",
    "sh scripts/approve.sh x",
    "python3 scripts/approve.py x",
    "scripts/approve.sh x --by a",
    "python3 -m py_compile scripts/approve.py && python3 scripts/approve.py x",
]


@pytest.mark.parametrize("project", ["plain_project", "active_project"])
@pytest.mark.parametrize("command", READS_AN_OWNER_SCRIPT)
def test_reading_an_owner_script_is_allowed_in_every_project(
    command: str, project: str, request: pytest.FixtureRequest
) -> None:
    repo, registry = request.getfixturevalue(project)
    result = _run_guard(command, cwd=repo, registry=registry)
    assert result.returncode == _EXIT_ALLOW, f"{command!r} only reads, yet was refused: {result.stderr[:200]}"


@pytest.mark.parametrize("project", ["plain_project", "active_project"])
@pytest.mark.parametrize("command", RUNS_AN_OWNER_SCRIPT)
def test_running_an_owner_script_next_to_a_read_stays_refused(
    command: str, project: str, request: pytest.FixtureRequest
) -> None:
    repo, registry = request.getfixturevalue(project)
    result = _run_guard(command, cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK, f"{command!r} runs an owner script and passed"
    assert "owner-only command" in result.stderr


# --------------------------------------------------------------------------- B-AC3

ALWAYS_HUMAN = [
    ("git push origin main", "AH3"),
    ("curl -X POST https://example.test", "AH3"),
    ("rm -rf data/", "AH3"),
    ("git push origin --delete feature/x", "AH3"),
    ("scripts/deploy.sh prod", "AH3"),
    ("cloudctl buy --size large", "AH4"),
    ("bash scripts/autonomy.py grant tier-2-feature", "AH5"),
    ("echo '{}' > scripts/autonomy.json", "AH5"),
]


@pytest.mark.parametrize(("command", "item"), ALWAYS_HUMAN)
def test_always_human_commands_are_refused_under_an_active_mandate(
    command: str, item: str, active_project: tuple[Path, Path]
) -> None:
    repo, registry = active_project
    result = _run_guard(command, cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK, f"{command!r} allowed: {result.stderr}"
    assert f"always-human item {item}" in result.stderr
    assert "matched:" in result.stderr


@pytest.mark.parametrize(("command", "item"), ALWAYS_HUMAN)
def test_the_same_commands_are_allowed_without_autonomy(
    command: str, item: str, plain_project: tuple[Path, Path]
) -> None:
    """R6 / ADR-6: a project that has not opted in sees no change."""
    repo, registry = plain_project
    result = _run_guard(command, cwd=repo, registry=registry)
    assert result.returncode == _EXIT_ALLOW, result.stderr


def test_an_expired_mandate_is_not_active(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "scripts").mkdir()
    (repo / "scripts" / "autonomy.json").write_text(json.dumps(_CONFIG), encoding="utf-8")
    registry = tmp_path / "registry.jsonl"
    registry.write_text(json.dumps(_registry_entry(expires="2000-01-01")) + "\n", encoding="utf-8")
    assert _run_guard("git push origin main", cwd=repo, registry=registry).returncode == _EXIT_ALLOW


def test_a_revoked_mandate_is_not_active(active_project: tuple[Path, Path]) -> None:
    repo, registry = active_project
    revocation = {
        "key": f"revoke-{_MANDATE_KEY}-2026-10-21",
        "artifact": "doc/mandates/MANDATE-proj-first.md",
        "status": "Revoked",
        "approved_by": "owner",
        "approved_at": "2026-10-21T09:00:00+07:00",
        "kind": "revocation",
        "revokes": _MANDATE_KEY,
    }
    with registry.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(revocation) + "\n")
    assert _run_guard("git push origin main", cwd=repo, registry=registry).returncode == _EXIT_ALLOW


def test_a_merge_while_on_a_protected_branch_is_refused(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo, branch="main")
    (repo / "scripts").mkdir()
    (repo / "scripts" / "autonomy.json").write_text(json.dumps(_CONFIG), encoding="utf-8")
    registry = tmp_path / "registry.jsonl"
    registry.write_text(json.dumps(_registry_entry()) + "\n", encoding="utf-8")
    result = _run_guard("git merge feature/x", cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK
    assert "always-human item AH3" in result.stderr


# --------------------------------------------------------------------------- F-AC1 (commit half)

_ON_A_BRANCH = "work under autonomy happens on a branch or worktree"
_ORDER_KEY = "order-proj-first-2026-10-20"


def _project_on(tmp_path: Path, branch: str, *, entry: dict | None, config: dict = _CONFIG) -> tuple[Path, Path]:
    """A repo on `branch`, opted in with `config`, and a registry holding `entry` (none = empty)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo, branch=branch)
    (repo / "scripts").mkdir()
    (repo / "scripts" / "autonomy.json").write_text(json.dumps(config), encoding="utf-8")
    registry = tmp_path / "registry.jsonl"
    registry.write_text(json.dumps(entry) + "\n" if entry else "", encoding="utf-8")
    return repo, registry


_ORDER_ENTRY = _registry_entry(key=_ORDER_KEY, kind="order", artifact="doc/orders/ORDER-proj-first.md")
_ABSENCE_ENTRY = {
    "key": "absence-proj-2026-10-20",
    "artifact": "",
    "status": "Approved",
    "approved_by": "owner",
    "approved_at": "2026-10-20T09:00:00+07:00",
    "kind": "absence",
    "until": "2099-12-31",
}


@pytest.mark.parametrize(
    ("branch", "entry", "config"),
    [
        ("main", _registry_entry(), _CONFIG),
        ("master", _registry_entry(), _CONFIG),
        ("main", _ORDER_ENTRY, _CONFIG),
        ("release", _ORDER_ENTRY, {**_CONFIG, "protected_branches": ["release"]}),
        ("main", _ABSENCE_ENTRY, _CONFIG),
    ],
    ids=["mandate-main", "mandate-master", "order-main", "order-project-listed-branch", "absence-main"],
)
@pytest.mark.parametrize("command", ["git commit -m x", "git -c user.name=a commit -qm x", "git add . && git commit -m x"])
def test_a_commit_on_a_protected_branch_is_refused_under_autonomy(
    command: str, branch: str, entry: dict, config: dict, tmp_path: Path
) -> None:
    repo, registry = _project_on(tmp_path, branch, entry=entry, config=config)
    result = _run_guard(command, cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK, f"{command!r} on {branch} allowed: {result.stderr}"
    assert _ON_A_BRANCH in result.stderr
    assert branch in result.stderr


def test_a_commit_on_a_working_branch_is_allowed_under_autonomy(tmp_path: Path) -> None:
    repo, registry = _project_on(tmp_path, "feature/x", entry=_ORDER_ENTRY)
    result = _run_guard("git commit -m x", cwd=repo, registry=registry)
    assert result.returncode == _EXIT_ALLOW, result.stderr


def _worktree_on(repo: Path, branch: str, path: Path) -> None:
    """Commit the project file first, as a real project has, so the worktree is opted in too."""
    subprocess.run(["git", "add", "scripts/autonomy.json"], cwd=repo, check=True, timeout=30)
    subprocess.run(
        ["git", "-c", "user.email=t@example.test", "-c", "user.name=t", "commit", "-qm", "opt in"],
        cwd=repo,
        check=True,
        timeout=30,
    )
    subprocess.run(["git", "worktree", "add", "-q", "-b", branch, str(path)], cwd=repo, check=True, timeout=30)


@pytest.mark.parametrize(
    "spelling",
    ["cd {wt} && git commit -m x", "cd {wt}; git commit -m x", "git -C {wt} commit -m x", "cd ../wt && git commit -m x"],
)
def test_a_commit_in_a_worktree_on_a_working_branch_is_allowed_from_main(spelling: str, tmp_path: Path) -> None:
    """The refusal's own advice must work: commit where the commit lands, not where the hook runs."""
    repo, registry = _project_on(tmp_path, "main", entry=_ORDER_ENTRY)
    worktree = tmp_path / "wt"
    _worktree_on(repo, "wip/x", worktree)
    command = spelling.format(wt=worktree)
    result = _run_guard(command, cwd=repo, registry=registry)
    assert result.returncode == _EXIT_ALLOW, f"{command!r}: {result.stderr}"


@pytest.mark.parametrize("spelling", ["cd {main} && git commit -m x", "git -C {main} commit -m x"])
def test_a_commit_aimed_at_main_from_a_worktree_is_refused(spelling: str, tmp_path: Path) -> None:
    repo, registry = _project_on(tmp_path, "main", entry=_ORDER_ENTRY)
    worktree = tmp_path / "wt"
    _worktree_on(repo, "wip/x", worktree)
    command = spelling.format(main=repo)
    result = _run_guard(command, cwd=worktree, registry=registry)
    assert result.returncode == _EXIT_BLOCK, f"{command!r} allowed: {result.stderr}"
    assert _ON_A_BRANCH in result.stderr


@pytest.mark.parametrize(
    "spelling",
    [
        "cd /nonexistent-f-ac1; git commit -m x",
        "cd /nonexistent-f-ac1 && git commit -m x",
        "git -C /nonexistent-f-ac1 commit -m x",
        "(cd {wt} && git commit -m x); git commit -m y",
        "(cd {wt}; git commit -m x) && git commit -m y",
        "( cd {wt} ) ; git commit -m y",
    ],
)
def test_a_commit_that_does_not_land_in_the_worktree_is_judged_on_main(spelling: str, tmp_path: Path) -> None:
    """A failed `cd`, an unreadable target, or a `cd` scoped to a subshell must
    not move the judged directory off the protected branch."""
    repo, registry = _project_on(tmp_path, "main", entry=_ORDER_ENTRY)
    worktree = tmp_path / "wt"
    _worktree_on(repo, "wip/x", worktree)
    command = spelling.format(wt=worktree)
    result = _run_guard(command, cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK, f"{command!r} allowed: {result.stderr}"
    assert _ON_A_BRANCH in result.stderr


def test_a_failed_cd_does_not_move_a_relative_git_dash_c(tmp_path: Path) -> None:
    """From repo/sub: the `cd` fails, so `-C ..` lands in the main checkout —
    not in the worktree the missing path was named under."""
    repo, registry = _project_on(tmp_path, "main", entry=_ORDER_ENTRY)
    worktree = tmp_path / "wt"
    _worktree_on(repo, "wip/x", worktree)
    (repo / "sub").mkdir()
    command = f"cd {worktree}/missing; git -C .. commit -m x"
    result = _run_guard(command, cwd=repo / "sub", registry=registry)
    assert result.returncode == _EXIT_BLOCK, f"{command!r} allowed: {result.stderr}"
    assert _ON_A_BRANCH in result.stderr


def test_a_commit_inside_a_subshell_cd_to_the_worktree_is_allowed(tmp_path: Path) -> None:
    repo, registry = _project_on(tmp_path, "main", entry=_ORDER_ENTRY)
    worktree = tmp_path / "wt"
    _worktree_on(repo, "wip/x", worktree)
    result = _run_guard(f"(cd {worktree} && git commit -m x)", cwd=repo, registry=registry)
    assert result.returncode == _EXIT_ALLOW, result.stderr


def test_a_commit_on_an_unborn_main_is_refused_under_autonomy(tmp_path: Path) -> None:
    """No commits yet: `rev-parse --abbrev-ref HEAD` fails, the branch is still main."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True, timeout=30)
    (repo / "scripts").mkdir()
    (repo / "scripts" / "autonomy.json").write_text(json.dumps(_CONFIG), encoding="utf-8")
    registry = tmp_path / "registry.jsonl"
    registry.write_text(json.dumps(_ORDER_ENTRY) + "\n", encoding="utf-8")
    result = _run_guard("git commit -m x", cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK, result.stderr
    assert _ON_A_BRANCH in result.stderr


@pytest.mark.parametrize(
    "entry",
    [None, _registry_entry(expires="2000-01-01")],
    ids=["no-order-or-mandate", "expired-mandate"],
)
def test_a_commit_on_main_is_allowed_without_live_autonomy(entry: dict | None, tmp_path: Path) -> None:
    """A-AC8: with no live order or mandate the guard behaves exactly as before."""
    repo, registry = _project_on(tmp_path, "main", entry=entry)
    result = _run_guard("git commit -m x", cwd=repo, registry=registry)
    assert result.returncode == _EXIT_ALLOW, result.stderr


def test_a_commit_on_main_is_allowed_in_a_project_that_never_opted_in(tmp_path: Path) -> None:
    """A-AC8: no autonomy.json, no mandate or order folder — today's behaviour."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo, branch="main")
    registry = tmp_path / "registry.jsonl"
    registry.write_text(json.dumps(_registry_entry()) + "\n", encoding="utf-8")
    result = _run_guard("git commit -m x", cwd=repo, registry=registry)
    assert result.returncode == _EXIT_ALLOW, result.stderr


@pytest.mark.parametrize("command", ['echo "git commit -m x"', "git log --grep commit", "git status"])
def test_mentioning_a_commit_on_main_is_allowed_under_autonomy(command: str, tmp_path: Path) -> None:
    repo, registry = _project_on(tmp_path, "main", entry=_registry_entry())
    result = _run_guard(command, cwd=repo, registry=registry)
    assert result.returncode == _EXIT_ALLOW, result.stderr


def test_a_malformed_project_file_keeps_the_framework_rules_on(
    active_project: tuple[Path, Path],
) -> None:
    """Fail direction: a broken autonomy.json must neither switch the guard
    off nor wedge every command. Framework rules stay on; ordinary work runs."""
    repo, registry = active_project
    (repo / "scripts" / "autonomy.json").write_text('{"project": "proj", "disable": ["AH3"]}')
    blocked = _run_guard("git push origin main", cwd=repo, registry=registry)
    assert blocked.returncode == _EXIT_BLOCK
    assert "always-human item AH3" in blocked.stderr
    assert "cannot remove framework item AH3" in blocked.stderr
    assert _run_guard("git status", cwd=repo, registry=registry).returncode == _EXIT_ALLOW
