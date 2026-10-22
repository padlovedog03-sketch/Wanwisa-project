"""The owner's order commands: `scripts/delegate.sh` and `scripts/revoke.sh` (row 5, increment 3).

SPEC-delegated-autonomy.md J-AC1 (issuing an order), J-AC2 (never-grantable,
unknown and conditional grants), A-AC7's registry half (`revoke.sh` writes the
revocation entry) and A-AC10 (every new entry kind carries the five fields),
as amended by SPEC-delegated-autonomy-am2-task-orders-scope.md AM2-AC5 (d)
(the task is one line and `task_sha256` hashes its bytes verbatim) and
AM2-AC3 (b) (the owner commits the new order document with its own key).

Every case runs the wrappers from copies inside a throwaway git repo, with
`HOME` and `APPROVAL_LOG` pointed into `tmp_path`: the real registry is never
read or written.

Assumption (stated, the spec leaves it open): `--allow` names the order's
grants exactly; with no `--allow` the order carries the default grants (R41).

Run: `python3 -m pytest tests/framework/test_delegate.py -q`
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TODAY = date.today().isoformat()
_UNTIL = (date.today() + timedelta(days=30)).isoformat()
_KEY = f"order-proj-first-{_TODAY}"
_DOC = "doc/orders/ORDER-proj-first.md"
_REQUIRED = ("key", "artifact", "status", "approved_by", "approved_at")
_DEFAULT_GRANTS = ["prd", "spec", "code", "tests", "qa", "business-rules-in-task"]
_NEVER = [
    "delete-data",
    "delete-history",
    "send-outside",
    "spend",
    "security",
    "personal-data",
    "change-mandate",
    "change-orders",
    "change-always-human",
    "change-approval",
    "change-bans",
    "widen",
]


def _env(tmp_path: Path) -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(tmp_path / "home"),
        "APPROVAL_LOG": str(tmp_path / "registry.jsonl"),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.test",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.test",
    }


def _git(repo: Path, *args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, env=env, check=False)


@pytest.fixture
def project(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """Opted in (`scripts/autonomy.json` committed) on a working branch, with
    the hooks wired and an empty registry."""
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / ".githooks").mkdir()
    (repo / "doc" / "templates").mkdir(parents=True)
    for name in (
        "approve.py",
        "approve.sh",
        "delegate.sh",
        "revoke.sh",
        "autonomy.py",
        "verify_approvals.py",
        "check_fix_has_test.py",
        "verify-merge.sh",
    ):
        shutil.copy2(_REPO_ROOT / "scripts" / name, repo / "scripts" / name)
    shutil.copy2(_REPO_ROOT / ".githooks" / "commit-msg", repo / ".githooks" / "commit-msg")
    shutil.copy2(_REPO_ROOT / "doc" / "templates" / "order.md", repo / "doc" / "templates" / "order.md")
    (repo / "scripts" / "autonomy.json").write_text('{"project": "proj"}\n', encoding="utf-8")
    (tmp_path / "registry.jsonl").write_text("", encoding="utf-8")
    env = _env(tmp_path)
    assert _git(repo, "init", "-q", "-b", "feature/x", env=env).returncode == 0
    _git(repo, "config", "core.hooksPath", ".githooks", env=env)
    _git(repo, "add", "-A", env=env)
    assert _git(repo, "commit", "-q", "-m", "opt in", env=env).returncode == 0
    return repo, env


def _run(repo: Path, env: dict[str, str], script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(repo / "scripts" / script), *args],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
        stdin=subprocess.DEVNULL,
        check=False,
    )


def _delegate(repo: Path, env: dict[str, str], *extra: str, task: str = "build the refunds export",
              slug: str = "first") -> subprocess.CompletedProcess[str]:
    return _run(repo, env, "delegate.sh", task, "--by", "o", "--until", _UNTIL, "--slug", slug, *extra)


def _registry(env: dict[str, str]) -> list[dict]:
    text = Path(env["APPROVAL_LOG"]).read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _status(repo: Path, env: dict[str, str]) -> str:
    return subprocess.run(
        [sys.executable, "-I", str(repo / "scripts" / "autonomy.py"), "status"],
        cwd=repo, capture_output=True, text=True, env=env, check=True,
    ).stdout.strip()


# --------------------------------------------------------------------------- J-AC1


def test_delegate_writes_the_document_stages_it_and_appends_one_order_entry(
    project: tuple[Path, dict[str, str]],
) -> None:
    repo, env = project
    result = _delegate(repo, env)
    assert result.returncode == 0, result.stderr

    entries = _registry(env)
    assert len(entries) == 1
    entry = entries[0]
    assert all(entry.get(field) for field in _REQUIRED), entry
    assert entry["key"] == _KEY
    assert entry["artifact"] == _DOC
    assert entry["status"] == "Approved"
    assert entry["approved_by"] == "o"
    assert entry["kind"] == "order"
    assert entry["grants"] == _DEFAULT_GRANTS
    assert entry["expires"] == _UNTIL
    assert entry["task_sha256"] == hashlib.sha256(b"build the refunds export").hexdigest()

    text = (repo / _DOC).read_text(encoding="utf-8")
    lines = text.splitlines()
    assert "Status: Approved" in lines
    assert f"Approval: {_KEY}" in lines
    assert "Task: build the refunds export" in lines
    assert [line for line in lines if line.startswith("Status:")] == ["Status: Approved"]
    assert [line for line in lines if line.startswith("Task:")] == ["Task: build the refunds export"]
    assert any(line.startswith("Upstream: ") and len(line) > len("Upstream: ") for line in lines)
    assert "## Approval history" in lines
    assert "<" not in text.replace("<!--", "").replace("-->", ""), "a template marker survived"

    staged = _git(repo, "diff", "--cached", "--name-only", env=env).stdout.split()
    assert staged == [_DOC], "delegate.sh must `git add` the order document, and only it"
    assert _status(repo, env) == f"order {_KEY}"


def test_the_order_key_gains_a_revision_suffix_on_a_same_day_collision(
    project: tuple[Path, dict[str, str]],
) -> None:
    """A-AC9 through the order writer: an earlier entry already holds the key."""
    repo, env = project
    earlier = {"key": _KEY, "artifact": "doc/orders/ORDER-proj-gone.md", "status": "Approved",
               "approved_by": "o", "approved_at": "2026-10-22T09:00:00+07:00", "kind": "order",
               "grants": ["spec"], "expires": _UNTIL, "task_sha256": "0" * 64}
    Path(env["APPROVAL_LOG"]).write_text(json.dumps(earlier) + "\n", encoding="utf-8")
    result = _delegate(repo, env)
    assert result.returncode == 0, result.stderr
    assert [e["key"] for e in _registry(env)] == [_KEY, f"{_KEY}-r2"]
    assert f"Approval: {_KEY}-r2" in (repo / _DOC).read_text(encoding="utf-8")


def test_the_issued_order_commits_with_its_own_key_and_the_committed_task_hashes_to_the_entry(
    project: tuple[Path, dict[str, str]],
) -> None:
    """AM2-AC5 (d)'s green case, delegate's half, end to end: a second order is
    issued under a live first one, committed through commit-msg with its own
    key as the trailer (AM2-AC3 b), and the committed `Task:` bytes hash to the
    registry's `task_sha256`, spaces and all."""
    repo, env = project
    assert _delegate(repo, env).returncode == 0
    assert _git(repo, "commit", "-q", "-m", "order: first", "-m", f"Owner-Approved: {_KEY}",
                env=env).returncode == 0

    task = "  task with spaces  "
    result = _delegate(repo, env, task=task, slug="second")
    assert result.returncode == 0, result.stderr
    second = _registry(env)[-1]
    commit = _git(repo, "commit", "-q", "-m", "order: second", "-m", f"Owner-Approved: {second['key']}", env=env)
    assert commit.returncode == 0, commit.stderr

    committed = subprocess.run(
        ["git", "show", "HEAD:doc/orders/ORDER-proj-second.md"], cwd=repo, capture_output=True, env=env, check=True
    ).stdout
    line = next(raw for raw in committed.split(b"\n") if raw.startswith(b"Task: "))
    assert line[len(b"Task: "):] == task.encode("utf-8")
    assert hashlib.sha256(line[len(b"Task: "):]).hexdigest() == second["task_sha256"]


def test_allow_names_the_grants_exactly(project: tuple[Path, dict[str, str]]) -> None:
    repo, env = project
    result = _delegate(repo, env, "--allow", "spec,code,tests,merge")
    assert result.returncode == 0, result.stderr
    assert _registry(env)[0]["grants"] == ["spec", "code", "tests", "merge"]
    assert "Grants: spec, code, tests, merge" in (repo / _DOC).read_text(encoding="utf-8").splitlines()


def test_a_task_with_a_newline_is_refused(project: tuple[Path, dict[str, str]]) -> None:
    repo, env = project
    for task in ("line one\nline two", "line one\r\nline two"):
        result = _delegate(repo, env, task=task)
        assert result.returncode == 2
        assert "the task is one line — point to a PRD for more" in result.stderr
    assert _registry(env) == []
    assert not (repo / _DOC).exists()


@pytest.mark.parametrize(
    ("args", "reason"),
    [
        (("--until", "2001-01-01"), "in the past"),
        (("--until", "next week"), "YYYY-MM-DD"),
        (("--slug", "Bad Slug"), "--slug"),
    ],
)
def test_bad_arguments_are_refused_and_write_nothing(
    project: tuple[Path, dict[str, str]], args: tuple[str, str], reason: str
) -> None:
    repo, env = project
    values = {"--until": _UNTIL, "--slug": "first", args[0]: args[1]}
    result = _run(repo, env, "delegate.sh", "t", "--by", "o", "--until", values["--until"], "--slug", values["--slug"])
    assert result.returncode == 2
    assert reason in result.stderr
    assert _registry(env) == []
    assert not (repo / "doc" / "orders").exists()


# NUL is absent: an argv cannot carry it, so no caller can pass one.
_CONTROL = ["\n", "\r", "\t", "\v", "\f", "\x01", "\x1b", "\x1f", " ", " ", "\u0085"]


@pytest.mark.parametrize("char", _CONTROL, ids=[f"U+{ord(c):04X}" for c in _CONTROL])
@pytest.mark.parametrize("field", ["task", "by"])
def test_a_control_character_in_the_task_or_issuer_is_refused(
    project: tuple[Path, dict[str, str]], field: str, char: str
) -> None:
    """A line break inside `--by` or the task would write a second header line
    (for example `--by $'o\\nStatus: Done'`) into the order document."""
    repo, env = project
    values = {"task": "t", "by": "o", field: f"o{char}Status: Done"}
    result = _run(repo, env, "delegate.sh", values["task"], "--by", values["by"], "--until", _UNTIL,
                  "--slug", "first")
    assert result.returncode == 2, result.stdout
    assert "refused — nothing written" in result.stderr
    assert "control character" in result.stderr or "one line" in result.stderr
    assert _registry(env) == []
    assert not (repo / _DOC).exists()


def test_no_issuer_is_refused(project: tuple[Path, dict[str, str]]) -> None:
    repo, env = project
    result = _run(repo, env, "delegate.sh", "t", "--until", _UNTIL, "--slug", "first")
    assert result.returncode == 2
    assert "--by" in result.stderr
    assert _registry(env) == []


def test_an_existing_order_document_is_never_overwritten(project: tuple[Path, dict[str, str]]) -> None:
    """AM2-AC3 refuses a modified order document at commit, so issuing over one
    would leave the owner an order nobody can commit."""
    repo, env = project
    assert _delegate(repo, env).returncode == 0
    before = (repo / _DOC).read_bytes()
    result = _delegate(repo, env, task="something else")
    assert result.returncode == 2
    assert _DOC in result.stderr
    assert (repo / _DOC).read_bytes() == before
    assert len(_registry(env)) == 1


def test_a_project_without_a_slug_is_refused(project: tuple[Path, dict[str, str]]) -> None:
    repo, env = project
    (repo / "scripts" / "autonomy.json").unlink()
    result = _delegate(repo, env)
    assert result.returncode == 2
    assert "scripts/autonomy.json" in result.stderr
    assert _registry(env) == []


# --------------------------------------------------------------------------- J-AC2


@pytest.mark.parametrize("grant", _NEVER)
def test_a_never_grantable_grant_is_refused_by_name(project: tuple[Path, dict[str, str]], grant: str) -> None:
    repo, env = project
    result = _delegate(repo, env, "--allow", f"spec,{grant}")
    assert result.returncode == 2
    assert grant in result.stderr
    assert "never grantable" in result.stderr
    assert _registry(env) == []
    assert not (repo / _DOC).exists()


@pytest.mark.parametrize(
    ("grant", "reason"),
    [("deploy", "deploy-dev or deploy-prod"), ("fly", "unknown grant fly"), ("", "unknown grant")],
)
def test_an_unknown_or_bare_deploy_grant_is_refused(
    project: tuple[Path, dict[str, str]], grant: str, reason: str
) -> None:
    repo, env = project
    result = _delegate(repo, env, "--allow", f"spec,{grant}")
    assert result.returncode == 2
    assert reason in result.stderr
    assert _registry(env) == []


def test_merge_is_refused_without_the_merge_gate(project: tuple[Path, dict[str, str]]) -> None:
    repo, env = project
    (repo / "scripts" / "verify-merge.sh").unlink()
    result = _delegate(repo, env, "--allow", "spec,merge")
    assert result.returncode == 2
    assert "merge needs the verify-tiers merge gate" in result.stderr
    assert _registry(env) == []


@pytest.mark.parametrize("grant", ["merge", "deploy-dev", "deploy-prod"])
def test_an_opt_in_grant_is_issued_when_named(project: tuple[Path, dict[str, str]], grant: str) -> None:
    repo, env = project
    result = _delegate(repo, env, "--allow", f"spec,{grant}")
    assert result.returncode == 0, result.stderr
    assert _registry(env)[0]["grants"] == ["spec", grant]


# --------------------------------------------------------------------------- A-AC7 (registry half), A-AC10


def test_revoke_appends_a_revocation_entry_and_the_order_stops_governing(
    project: tuple[Path, dict[str, str]],
) -> None:
    repo, env = project
    assert _delegate(repo, env).returncode == 0
    assert _status(repo, env) == f"order {_KEY}"

    result = _run(repo, env, "revoke.sh", _KEY, "--by", "o")
    assert result.returncode == 0, result.stderr
    order, revocation = _registry(env)
    assert all(revocation.get(field) for field in _REQUIRED), revocation
    assert revocation["key"] == f"revoke-{_KEY}-{_TODAY}"
    assert revocation["kind"] == "revocation"
    assert revocation["revokes"] == _KEY
    assert revocation["artifact"] == order["artifact"] == _DOC
    assert revocation["status"] == "Revoked"
    assert revocation["approved_by"] == "o"
    assert _status(repo, env) == "inactive"


def test_a_second_revocation_of_the_same_key_is_refused(project: tuple[Path, dict[str, str]]) -> None:
    repo, env = project
    assert _delegate(repo, env).returncode == 0
    assert _run(repo, env, "revoke.sh", _KEY, "--by", "o").returncode == 0
    result = _run(repo, env, "revoke.sh", _KEY, "--by", "o")
    assert result.returncode == 2
    assert "already revoked" in result.stderr
    assert len(_registry(env)) == 2


@pytest.mark.parametrize("target", ["order-proj-nothing-2026-01-01", ""])
def test_revoking_an_unknown_key_is_refused(project: tuple[Path, dict[str, str]], target: str) -> None:
    repo, env = project
    result = _run(repo, env, "revoke.sh", target, "--by", "o")
    assert result.returncode == 2
    assert "not in the registry" in result.stderr
    assert _registry(env) == []


def test_revoke_without_an_issuer_is_refused(project: tuple[Path, dict[str, str]]) -> None:
    repo, env = project
    assert _delegate(repo, env).returncode == 0
    result = _run(repo, env, "revoke.sh", _KEY)
    assert result.returncode == 2
    assert "--by" in result.stderr
    assert len(_registry(env)) == 1


def test_every_entry_the_owner_commands_write_resolves_for_the_verifier(
    project: tuple[Path, dict[str, str]],
) -> None:
    """A-AC10: an order and its revocation leave a registry every project on the
    machine can still read, and the order document's own key resolves."""
    repo, env = project
    assert _delegate(repo, env).returncode == 0
    assert _git(repo, "commit", "-q", "-m", "order", "-m", f"Owner-Approved: {_KEY}", env=env).returncode == 0
    assert _run(repo, env, "revoke.sh", _KEY, "--by", "o").returncode == 0

    probe = (
        "import sys; sys.path.insert(0, 'scripts'); import verify_approvals as v; "
        "entries, problem = v.load_registry(v.registry_path()); "
        "print(problem); print(entries[sys.argv[1]]['artifact'])"
    )
    result = subprocess.run([sys.executable, "-c", probe, _KEY], cwd=repo, capture_output=True, text=True,
                            env=env, check=False)
    assert result.stdout.splitlines() == ["None", _DOC], result.stderr
    verified = subprocess.run([sys.executable, str(repo / "scripts" / "verify_approvals.py")], cwd=repo,
                              capture_output=True, text=True, env=env, check=False)
    assert verified.returncode == 0, verified.stdout
