"""Which `Owner-Approved:` trailer lets a protected path through commit-msg (B-AC7, S1).

QA-delegated-autonomy-B.md S1: any registry key satisfied the check, including
the mandate key that `autonomy.py status` prints to the agent, so the agent
could supply the owner's consent itself. Coordinator ruling 2026-10-20 (under
the owner's delegation; the owner may reverse it): a trailer counts only when
its key is an owner entry of kind `approval` (no `kind`, or `approval`), not
revoked, whose `artifact` is one of the paths the commit changes or the
mandate/order document governing this project. A mandate or order key never
counts on a commit made while that mandate is in force.

Each case commits for real through `.githooks/commit-msg` in a throwaway repo
whose HEAD already holds `scripts/autonomy.json`, so the opt-in commit's own
exception (see `autonomy.check_commit`) never applies here.

Run: `python3 -m pytest tests/framework/test_commit_msg_owner_trailer.py -q`
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MANDATE_KEY = "mandate-proj-first-2026-10-20"


def _entry(key: str, artifact: str, **extra: str) -> dict:
    return {
        "key": key,
        "artifact": artifact,
        "status": "Approved",
        "approved_by": "owner",
        "approved_at": "2026-10-20T09:00:00+07:00",
        **extra,
    }


_MANDATE = _entry(_MANDATE_KEY, "doc/mandates/MANDATE-proj-first.md", kind="mandate", expires="2099-12-31")


def _git(repo: Path, *args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, env=env, check=False)


def _opted_in(tmp_path: Path, *extra_entries: dict) -> tuple[Path, dict[str, str]]:
    """Opted in and committed while the registry was empty; then the owner's
    mandate (and any extra entries) land in the registry."""
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / ".githooks").mkdir()
    shutil.copy(_REPO_ROOT / ".githooks" / "commit-msg", repo / ".githooks" / "commit-msg")
    for name in ("autonomy.py", "verify_approvals.py", "check_fix_has_test.py"):
        shutil.copy(_REPO_ROOT / "scripts" / name, repo / "scripts" / name)
    (repo / "scripts" / "autonomy.json").write_text('{"project": "proj"}\n', encoding="utf-8")
    registry = tmp_path / "registry.jsonl"
    registry.write_text("", encoding="utf-8")
    env = {
        **os.environ,
        "APPROVAL_LOG": str(registry),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.test",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.test",
    }
    assert _git(repo, "init", "-q", "-b", "feature/x", env=env).returncode == 0
    _git(repo, "config", "core.hooksPath", ".githooks", env=env)
    _git(repo, "add", "-A", env=env)
    assert _git(repo, "commit", "-q", "-m", "opt in", env=env).returncode == 0
    registry.write_text("".join(json.dumps(e) + "\n" for e in (_MANDATE, *extra_entries)), encoding="utf-8")
    return repo, env


def _widen(repo: Path, env: dict[str, str], message: str) -> subprocess.CompletedProcess[str]:
    (repo / "scripts" / "autonomy.json").write_text('{"project": "proj", "data_globs": []}\n', encoding="utf-8")
    _git(repo, "add", "-A", env=env)
    return _git(repo, "commit", "-q", "-m", message, env=env)


def test_the_mandate_key_as_a_trailer_is_refused(tmp_path: Path) -> None:
    repo, env = _opted_in(tmp_path)
    result = _widen(repo, env, f"widen\n\nOwner-Approved: {_MANDATE_KEY}")
    assert result.returncode != 0, "the mandate key, which status prints to the agent, passed as consent"
    assert "always-human item AH5" in result.stderr
    assert "scripts/autonomy.json" in result.stderr


def test_an_approval_of_an_unrelated_artifact_is_refused(tmp_path: Path) -> None:
    unrelated = _entry("SPEC-other-2026-10-20", "doc/specs/SPEC-other.md")
    repo, env = _opted_in(tmp_path, unrelated)
    result = _widen(repo, env, "widen\n\nOwner-Approved: SPEC-other-2026-10-20")
    assert result.returncode != 0, "an approval of another document passed as consent for this path"
    assert "always-human item AH5" in result.stderr


def test_a_revoked_approval_of_the_path_is_refused(tmp_path: Path) -> None:
    approval = _entry("autonomy-json-2026-10-20", "scripts/autonomy.json")
    revocation = _entry(
        "revoke-autonomy-json-2026-10-21",
        "scripts/autonomy.json",
        kind="revocation",
        revokes="autonomy-json-2026-10-20",
        status="Revoked",
    )
    repo, env = _opted_in(tmp_path, approval, revocation)
    result = _widen(repo, env, "widen\n\nOwner-Approved: autonomy-json-2026-10-20")
    assert result.returncode != 0


def test_an_owner_approval_of_the_changed_path_passes(tmp_path: Path) -> None:
    approval = _entry("autonomy-json-2026-10-20", "scripts/autonomy.json")
    repo, env = _opted_in(tmp_path, approval)
    result = _widen(repo, env, "widen\n\nOwner-Approved: autonomy-json-2026-10-20")
    assert result.returncode == 0, result.stderr


def test_an_owner_approval_of_the_governing_mandate_passes(tmp_path: Path) -> None:
    approval = _entry("MANDATE-proj-first-amend-2026-10-20", "doc/mandates/MANDATE-proj-first.md")
    repo, env = _opted_in(tmp_path, approval)
    result = _widen(repo, env, "widen\n\nOwner-Approved: MANDATE-proj-first-amend-2026-10-20")
    assert result.returncode == 0, result.stderr


def test_renaming_the_project_file_needs_an_owner_trailer(tmp_path: Path) -> None:
    repo, env = _opted_in(tmp_path)
    _git(repo, "mv", "scripts/autonomy.json", "scripts/autonomy.off", env=env)
    result = _git(repo, "commit", "-q", "-m", "chore: rename", env=env)
    assert result.returncode != 0, "a rename of scripts/autonomy.json committed with no trailer"
    assert "scripts/autonomy.json" in result.stderr


def test_an_approval_of_another_staged_document_does_not_clear_a_protected_path(tmp_path: Path) -> None:
    """The agent can touch any approved document and quote that document's own
    key. Only an approval of a PROTECTED path in the commit, or of the
    governing mandate, is consent for a protected path."""
    spec = _entry("SPEC-x-2026-10-20", "doc/specs/SPEC-x.md")
    repo, env = _opted_in(tmp_path, spec)
    (repo / "doc" / "specs").mkdir(parents=True)
    (repo / "doc" / "specs" / "SPEC-x.md").write_text("Status: Approved\n", encoding="utf-8")
    result = _widen(repo, env, "widen\n\nOwner-Approved: SPEC-x-2026-10-20")
    assert result.returncode != 0, "an approval of a co-staged ordinary document cleared scripts/autonomy.json"
    assert "scripts/autonomy.json" in result.stderr


def test_the_opt_in_exception_does_not_cover_edits_to_existing_protected_files(tmp_path: Path) -> None:
    """The commit that first adds scripts/autonomy.json may carry the mandate
    key, which `status` prints. That must clear only what the commit ADDS, not
    an edit to enforcement code that HEAD already holds."""
    repo, env = _opted_in(tmp_path)
    # Rebuild: HEAD without the project file, mandate already live.
    shutil.rmtree(repo / ".git")
    (repo / "scripts" / "autonomy.json").unlink()
    registry = Path(env["APPROVAL_LOG"])
    live = registry.read_text(encoding="utf-8")
    registry.write_text("", encoding="utf-8")
    assert _git(repo, "init", "-q", "-b", "feature/x", env=env).returncode == 0
    _git(repo, "config", "core.hooksPath", ".githooks", env=env)
    _git(repo, "add", "-A", env=env)
    assert _git(repo, "commit", "-q", "-m", "base", env=env).returncode == 0
    registry.write_text(live, encoding="utf-8")

    (repo / "scripts" / "autonomy.json").write_text('{"project": "proj"}\n', encoding="utf-8")
    with (repo / ".githooks" / "commit-msg").open("a", encoding="utf-8") as handle:
        handle.write("# edited by the agent\n")
    _git(repo, "add", "-A", env=env)
    result = _git(repo, "commit", "-q", "-m", f"opt in\n\nOwner-Approved: {_MANDATE_KEY}", env=env)
    assert result.returncode != 0, "the opt-in commit carried an edit to .githooks/commit-msg"
    assert ".githooks/commit-msg" in result.stderr
    assert "scripts/autonomy.json is protected" not in result.stderr


# --------------------------------------------------------------------------- AM1-ADR-3
# SPEC-delegated-autonomy-am1-guards-catch-accidents B-AC7: the opt-in commit
# clears only scripts/autonomy.json and the document its trailer's registry
# entry names as `artifact`. Any other protected path it adds needs an owner
# trailer of its own.


def _opt_in_with(tmp_path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    """Framework files committed at install while the registry was empty; the
    owner's mandate then lands in the registry, and the agent commits the
    opt-in: the project file, the mandate document and each `extra` path."""
    repo, env = _opted_in(tmp_path)
    shutil.rmtree(repo / ".git")
    (repo / "scripts" / "autonomy.json").unlink()
    registry = Path(env["APPROVAL_LOG"])
    live = registry.read_text(encoding="utf-8")
    registry.write_text("", encoding="utf-8")
    assert _git(repo, "init", "-q", "-b", "feature/x", env=env).returncode == 0
    _git(repo, "config", "core.hooksPath", ".githooks", env=env)
    _git(repo, "add", "-A", env=env)
    assert _git(repo, "commit", "-q", "-m", "install", env=env).returncode == 0
    registry.write_text(live, encoding="utf-8")

    (repo / "scripts" / "autonomy.json").write_text('{"project": "proj"}\n', encoding="utf-8")
    for rel in ("doc/mandates/MANDATE-proj-first.md", *extra):
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text("added in the opt-in\n", encoding="utf-8")
    _git(repo, "add", "-A", env=env)
    return _git(repo, "commit", "-q", "-m", f"opt in\n\nOwner-Approved: {_MANDATE_KEY}", env=env)


def test_the_opt_in_clears_the_project_file_and_its_own_mandate_document(tmp_path: Path) -> None:
    result = _opt_in_with(tmp_path)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "extra",
    ["doc/orders/ORDER-self.md", "doc/mandates/MANDATE-wide.md", "scripts/release.sh", ".githooks/post-checkout"],
)
def test_the_opt_in_does_not_clear_another_protected_path_it_adds(tmp_path: Path, extra: str) -> None:
    result = _opt_in_with(tmp_path, extra)
    assert result.returncode != 0, f"the opt-in commit carried a new {extra} with no owner trailer"
    assert f"always-human item AH5: {extra} is protected" in result.stderr
    assert "scripts/autonomy.json is protected" not in result.stderr
    assert "MANDATE-proj-first.md is protected" not in result.stderr
