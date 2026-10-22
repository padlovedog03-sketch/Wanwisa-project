"""`autonomy.py approve-under <doc> --order <key>` (row 5, increment 4).

SPEC-delegated-autonomy-am2-task-orders-scope.md AM2-AC5 (= A-AC3, A-AC4 (a)(b)
(c)(f)(g) and J-AC3 under an order, F-AC1's `approve-under` half), A-AC7's
`approve-under` half (refused after revocation) and A-AC8 (no autonomy: refused
with `no active mandate or order`).

Every case runs the real scripts, copied into a throwaway git repo, with
`HOME` and `APPROVAL_LOG` pointed into `tmp_path`: the real registry is never
read or written. The order is issued with `delegate.sh` and committed through
the commit-msg hook with its own key, exactly as the owner does it.

Assumption (stated): under an order the grant is checked by document kind
(AM2-ADR-4), so a document that yields no decision class is not refused for
that alone. A PRD or SPEC with no `Decision-class:` line still is (AH-UNSURE),
and so is any touch or protected path.

Run: `python3 -m pytest tests/framework/test_autonomy_approve.py -q`
"""

from __future__ import annotations

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
_ORDER_DOC = "doc/orders/ORDER-proj-first.md"
_SPEC = "doc/specs/SPEC-first.md"
_LOG = "doc/decisions/decision-log.jsonl"
_R42 = "outside the order — stop and ask (R42)"
_SCRIPTS = (
    "approve.py",
    "approve.sh",
    "delegate.sh",
    "revoke.sh",
    "autonomy.py",
    "verify_approvals.py",
    "check_fix_has_test.py",
    "verify-merge.sh",
)


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


def _doc(status: str = "In Review", decision: str | None = "Decision-class: tier-1; touches: none",
         history: bool = True) -> str:
    lines = ["# probe", "", f"Status: {status}", "Upstream: the order"]
    if decision:
        lines.append(decision)
    lines.append("")
    if history:
        lines += ["## Approval history", "", "- drafted."]
    return "\n".join(lines) + "\n"


def _write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _base_repo(tmp_path: Path, *, opted_in: bool = True) -> tuple[Path, dict[str, str]]:
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / ".githooks").mkdir()
    (repo / "doc" / "templates").mkdir(parents=True)
    for name in _SCRIPTS:
        shutil.copy2(_REPO_ROOT / "scripts" / name, repo / "scripts" / name)
    shutil.copy2(_REPO_ROOT / ".githooks" / "commit-msg", repo / ".githooks" / "commit-msg")
    shutil.copy2(_REPO_ROOT / "doc" / "templates" / "order.md", repo / "doc" / "templates" / "order.md")
    if opted_in:
        _write(repo, "scripts/autonomy.json", '{"project": "proj"}\n')
    (tmp_path / "registry.jsonl").write_text("", encoding="utf-8")
    env = _env(tmp_path)
    assert _git(repo, "init", "-q", "-b", "feature/x", env=env).returncode == 0
    _git(repo, "config", "core.hooksPath", ".githooks", env=env)
    _git(repo, "add", "-A", env=env)
    assert _git(repo, "commit", "-q", "-m", "base", env=env).returncode == 0
    return repo, env


def _delegate(repo: Path, env: dict[str, str], *extra: str, task: str = "  task with spaces  ",
              slug: str = "first") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(repo / "scripts" / "delegate.sh"), task, "--by", "o", "--until", _UNTIL, "--slug", slug,
         *extra],
        cwd=repo, capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL, check=False,
    )


def _commit_docs(repo: Path, env: dict[str, str], *docs: tuple[str, str]) -> None:
    for rel, text in docs:
        _write(repo, rel, text)
    _git(repo, "add", "--", *(rel for rel, _ in docs), env=env)
    result = _git(repo, "commit", "-q", "-m", "docs", env=env)
    assert result.returncode == 0, result.stderr


def _ordered(tmp_path: Path, *extra: str) -> tuple[Path, dict[str, str]]:
    """Opted in on `feature/x`, the order `first` issued and committed by the
    owner (task with leading and trailing spaces), and `SPEC-first.md` In Review."""
    repo, env = _base_repo(tmp_path)
    assert _delegate(repo, env, *extra).returncode == 0
    committed = _git(repo, "commit", "-q", "-m", "order: first", "-m", f"Owner-Approved: {_KEY}", env=env)
    assert committed.returncode == 0, committed.stderr
    _commit_docs(repo, env, (_SPEC, _doc()))
    return repo, env


@pytest.fixture
def ordered(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    return _ordered(tmp_path)


def _approve_under(repo: Path, env: dict[str, str], doc: str = _SPEC, key: str = _KEY,
                   ) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(repo / "scripts" / "autonomy.py"), "approve-under", doc, "--order", key],
        cwd=repo, capture_output=True, text=True, env=env, check=False,
    )


def _log(repo: Path) -> list[dict]:
    path = repo / _LOG
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _registry_bytes(env: dict[str, str]) -> bytes:
    return Path(env["APPROVAL_LOG"]).read_bytes()


def _add_registry(env: dict[str, str], entry: dict) -> None:
    with Path(env["APPROVAL_LOG"]).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def _assert_refused(result: subprocess.CompletedProcess[str], repo: Path, reason: str,
                    doc: str = _SPEC, before: str | None = None) -> None:
    assert result.returncode == 2, result.stdout + result.stderr
    assert reason in result.stderr, result.stderr
    assert _log(repo) == [], "a refusal appends nothing to the decision log"
    if before is not None:
        assert (repo / doc).read_text(encoding="utf-8") == before, "a refusal leaves the document untouched"


# --------------------------------------------------------------------------- green (A-AC3, J-AC3, J-AC1)


def test_approve_under_stamps_the_document_and_appends_one_approval_entry(
    ordered: tuple[Path, dict[str, str]],
) -> None:
    repo, env = ordered
    registry_before = _registry_bytes(env)
    result = _approve_under(repo, env)
    assert result.returncode == 0, result.stderr

    lines = (repo / _SPEC).read_text(encoding="utf-8").splitlines()
    assert [line for line in lines if line.startswith("Status:")] == ["Status: Approved"]
    approval = [line for line in lines if line.startswith("Approval:")]
    assert len(approval) == 1
    akey = approval[0].removeprefix("Approval: ")
    assert f"Approved-under: order {_KEY}" in lines
    assert any(f"approved under order {_KEY} (assistant)" in line for line in lines)

    (entry,) = _log(repo)
    assert entry["id"] == akey
    assert entry["kind"] == "approval"
    assert entry["under"] == f"order {_KEY}"
    assert entry["artifact"] == _SPEC
    assert entry["project"] == "proj"
    assert entry["reverse"] == f"remove stamp {_SPEC}"
    assert "prev" not in entry, "no hash chain (AM2-ADR-2)"
    assert _registry_bytes(env) == registry_before, "no registry line is written"

    verified = subprocess.run([sys.executable, str(repo / "scripts" / "verify_approvals.py")], cwd=repo,
                              capture_output=True, text=True, env=env, check=False)
    assert verified.returncode == 0, verified.stdout


def test_a_qa_report_with_no_decision_header_is_approved_under_the_qa_grant(
    ordered: tuple[Path, dict[str, str]],
) -> None:
    """The assumption above: a QA report yields no decision class, which under
    an order is not a reason to refuse (the grant is by kind, AM2-ADR-4)."""
    repo, env = ordered
    _commit_docs(repo, env, ("doc/qa/QA-first.md", _doc(decision="Verdict: PASS")))
    result = _approve_under(repo, env, "doc/qa/QA-first.md")
    assert result.returncode == 0, result.stderr


# --------------------------------------------------------------------------- (a) (b) (c), A-AC7


@pytest.mark.parametrize("key", ["order-proj-nothing-2026-01-01", "spec-owner-approved-2026-01-01"])
def test_a_key_that_is_not_an_order_entry_is_refused(ordered: tuple[Path, dict[str, str]], key: str) -> None:
    repo, env = ordered
    _add_registry(env, {"key": "spec-owner-approved-2026-01-01", "artifact": "doc/specs/SPEC-x.md",
                        "status": "Approved", "approved_by": "o", "approved_at": "2026-01-01T00:00:00+00:00"})
    before = (repo / _SPEC).read_text(encoding="utf-8")
    _assert_refused(_approve_under(repo, env, key=key), repo, "is not a kind order registry entry", before=before)


def test_an_expired_order_is_refused(ordered: tuple[Path, dict[str, str]]) -> None:
    repo, env = ordered
    old = "order-proj-old-2026-01-01"
    _add_registry(env, {"key": old, "artifact": "doc/orders/ORDER-proj-old.md", "status": "Approved",
                        "approved_by": "o", "approved_at": "2026-01-01T00:00:00+00:00", "kind": "order",
                        "grants": ["spec"], "expires": "2026-01-31", "task_sha256": "0" * 64})
    _commit_docs(repo, env, ("doc/specs/SPEC-old.md", _doc()))
    _assert_refused(_approve_under(repo, env, "doc/specs/SPEC-old.md", key=old), repo, "expired")


def test_approve_under_is_refused_after_the_owner_revokes_the_order(ordered: tuple[Path, dict[str, str]]) -> None:
    """A-AC7: revocation takes effect at the next approve-under."""
    repo, env = ordered
    revoked = subprocess.run(["bash", str(repo / "scripts" / "revoke.sh"), _KEY, "--by", "o"], cwd=repo,
                             capture_output=True, text=True, env=env, check=False)
    assert revoked.returncode == 0, revoked.stderr
    before = (repo / _SPEC).read_text(encoding="utf-8")
    _assert_refused(_approve_under(repo, env), repo, f"order {_KEY} revoked", before=before)


# --------------------------------------------------------------------------- (d) RED-FIRST


def test_an_order_document_not_committed_is_refused(tmp_path: Path) -> None:
    """The red-first case: an order entry whose document is not committed."""
    repo, env = _base_repo(tmp_path)
    assert _delegate(repo, env).returncode == 0
    assert _git(repo, "reset", "-q", "--", _ORDER_DOC, env=env).returncode == 0  # never committed
    _commit_docs(repo, env, (_SPEC, _doc()))
    assert _git(repo, "ls-files", "--", _ORDER_DOC, env=env).stdout == ""
    before = (repo / _SPEC).read_text(encoding="utf-8")
    _assert_refused(_approve_under(repo, env), repo, "order document not committed as issued", before=before)


def test_an_order_document_committed_with_a_different_task_is_refused(tmp_path: Path) -> None:
    repo, env = _base_repo(tmp_path)
    assert _delegate(repo, env).returncode == 0
    doc = repo / _ORDER_DOC
    doc.write_text(doc.read_text(encoding="utf-8").replace("Task:   task with spaces  ", "Task: task with spaces"),
                   encoding="utf-8")
    _git(repo, "add", "-A", env=env)
    assert _git(repo, "commit", "-q", "--no-verify", "-m", "trimmed", env=env).returncode == 0
    _commit_docs(repo, env, (_SPEC, _doc()))
    _assert_refused(_approve_under(repo, env), repo, "order document not committed as issued")


def test_the_task_line_is_hashed_with_no_newline_normalisation(tmp_path: Path) -> None:
    """The hashed bytes stop at `\\n` only: a committed CRLF line carries its
    `\\r`, so it no longer matches the hash of the task as given."""
    repo, env = _base_repo(tmp_path)
    assert _delegate(repo, env).returncode == 0
    doc = repo / _ORDER_DOC
    doc.write_bytes(doc.read_bytes().replace(b"Task:   task with spaces  \n", b"Task:   task with spaces  \r\n"))
    _git(repo, "-c", "core.autocrlf=false", "add", "-A", env=env)
    assert _git(repo, "commit", "-q", "--no-verify", "-m", "crlf", env=env).returncode == 0
    _commit_docs(repo, env, (_SPEC, _doc()))
    _assert_refused(_approve_under(repo, env), repo, "order document not committed as issued")


# --------------------------------------------------------------------------- (e)


@pytest.mark.parametrize(
    "rel",
    [
        "doc/specs/SPEC-other.md",  # filename lacks the slug
        "doc/specs/SPEC-firstly.md",  # the slug only as part of a longer word
        "doc/tasks/TASK-first.md",  # a kind no grant covers
    ],
)
def test_a_document_outside_the_order_is_refused(ordered: tuple[Path, dict[str, str]], rel: str) -> None:
    repo, env = ordered
    _commit_docs(repo, env, (rel, _doc()))
    _assert_refused(_approve_under(repo, env, rel), repo, _R42, doc=rel)


def test_a_kind_the_order_does_not_grant_is_refused(tmp_path: Path) -> None:
    repo, env = _ordered(tmp_path, "--allow", "spec")
    _commit_docs(repo, env, ("doc/requirements/PRD-first.md", _doc()))
    _assert_refused(_approve_under(repo, env, "doc/requirements/PRD-first.md"), repo, _R42,
                    doc="doc/requirements/PRD-first.md")
    _commit_docs(repo, env, ("doc/architecture/DESIGN-first.md", _doc()))
    assert _approve_under(repo, env, "doc/architecture/DESIGN-first.md").returncode == 0


# --------------------------------------------------------------------------- (f)


@pytest.mark.parametrize(
    ("decision", "item"),
    [
        ("Decision-class: tier-1; touches: security", "AH2"),
        ("Decision-class: tier-1; touches: personal-data", "AH2"),
        ("Decision-class: tier-1; touches: something-new", "AH-UNSURE"),
        (None, "AH-UNSURE"),  # a SPEC with no Decision-class line
    ],
)
def test_a_document_touching_an_always_human_item_is_refused(
    ordered: tuple[Path, dict[str, str]], decision: str | None, item: str
) -> None:
    repo, env = ordered
    _commit_docs(repo, env, (_SPEC, _doc(decision=decision)))
    _assert_refused(_approve_under(repo, env), repo, item)


def test_a_business_rule_touch_is_allowed_only_with_the_business_rules_grant(tmp_path: Path) -> None:
    rule = "Decision-class: tier-1; touches: business-rules"
    repo, env = _ordered(tmp_path)  # the default grants include business-rules-in-task
    _commit_docs(repo, env, (_SPEC, _doc(decision=rule)))
    assert _approve_under(repo, env).returncode == 0

    narrow, narrow_env = _ordered(tmp_path / "narrow", "--allow", "spec")
    _commit_docs(narrow, narrow_env, (_SPEC, _doc(decision=rule)))
    _assert_refused(_approve_under(narrow, narrow_env), narrow, "AH1")


# --------------------------------------------------------------------------- (g)


@pytest.mark.parametrize("rel", [_ORDER_DOC, "scripts/autonomy.json"])
def test_the_order_document_and_the_project_file_are_never_approved_under_an_order(
    ordered: tuple[Path, dict[str, str]], rel: str
) -> None:
    repo, env = ordered
    before = (repo / rel).read_text(encoding="utf-8")
    _assert_refused(_approve_under(repo, env, rel), repo, "never approved under an order", doc=rel, before=before)


# --------------------------------------------------------------------------- (h), F-AC1


@pytest.mark.parametrize("branch", ["main", "master"])
def test_approve_under_on_a_protected_branch_is_refused(ordered: tuple[Path, dict[str, str]], branch: str) -> None:
    repo, env = ordered
    assert _git(repo, "switch", "-q", "-c", branch, env=env).returncode == 0
    _assert_refused(_approve_under(repo, env), repo, "work under autonomy happens on a branch or worktree")


# --------------------------------------------------------------------------- the document itself


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        (_doc(status="Draft"), "In Review"),
        (_doc(status="Approved"), "In Review"),
        (_doc(history=False), "## Approval history"),
    ],
)
def test_a_document_not_ready_for_approval_is_refused(
    ordered: tuple[Path, dict[str, str]], text: str, reason: str
) -> None:
    repo, env = ordered
    _commit_docs(repo, env, (_SPEC, text))
    _assert_refused(_approve_under(repo, env), repo, reason, before=text)


def test_a_missing_document_is_refused_not_crashed(ordered: tuple[Path, dict[str, str]]) -> None:
    repo, env = ordered
    _assert_refused(_approve_under(repo, env, "doc/specs/SPEC-first-missing.md"), repo, "not found",
                    doc="doc/specs/SPEC-first-missing.md")


def test_an_untracked_document_is_refused(ordered: tuple[Path, dict[str, str]]) -> None:
    repo, env = ordered
    _write(repo, "doc/specs/SPEC-first-untracked.md", _doc())
    _assert_refused(_approve_under(repo, env, "doc/specs/SPEC-first-untracked.md"), repo, "not tracked",
                    doc="doc/specs/SPEC-first-untracked.md")


# --------------------------------------------------------------------------- A-AC8


def test_without_autonomy_approve_under_refuses_with_no_active_mandate_or_order(tmp_path: Path) -> None:
    repo, env = _base_repo(tmp_path, opted_in=False)
    _commit_docs(repo, env, (_SPEC, _doc()))
    _assert_refused(_approve_under(repo, env), repo, "no active mandate or order", before=_doc())
    status = subprocess.run([sys.executable, "-I", str(repo / "scripts" / "autonomy.py"), "status"], cwd=repo,
                            capture_output=True, text=True, env=env, check=False)
    assert status.stdout.strip() == "inactive"
