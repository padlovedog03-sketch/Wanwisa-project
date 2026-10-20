"""Tests for `.githooks/pre-commit` — the interception fallback (adapter ข).

WHY THIS FILE EXISTS. For any assistant that cannot be stopped before it acts,
this hook is the only local gate. A hook that is not executable, or that runs
its checks but ignores their exit codes, passes every commit while looking
installed — the exact silent failure the framework is built against. So the
test commits for real in a throwaway repo, once clean and once with a planted
violation, and asserts the second commit is refused.

Run: `python3 -m pytest tests/framework/ -q`   (stdlib + git)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _git(repo: Path, *args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, env=env, check=False
    )


def _clone_template(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """A minimal template repo: the hook, the layer-1 scripts, this repo's memory
    and scars, and a placeholder AGENTS.md. Built from parts, not by copying the
    whole repo, so the test means the same thing in a project made from this
    template — where AGENTS.md is filled in and real approvals exist."""
    repo = tmp_path / "repo"
    repo.mkdir()
    ignore = shutil.ignore_patterns("__pycache__", "*.local.txt")
    for rel in (".githooks", ".agents", "scripts", "doc/memory", "doc/scars", "doc/templates"):
        if (_REPO_ROOT / rel).is_dir():
            shutil.copytree(_REPO_ROOT / rel, repo / rel, ignore=ignore)
    (repo / "AGENTS.md").write_text("# AGENTS.md — <PROJECT>\nrules\n", encoding="utf-8")
    env = {
        **os.environ,
        "APPROVAL_LOG": str(tmp_path / "registry.jsonl"),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }
    for var in ("MEMORY_DIR", "NEUTRALITY_ROOT", "SCAR_DIR"):
        env.pop(var, None)
    _git(repo, "init", "-q", env=env)
    _git(repo, "config", "core.hooksPath", ".githooks", env=env)
    return repo, env


def test_hook_is_executable() -> None:
    assert os.access(_REPO_ROOT / ".githooks" / "pre-commit", os.X_OK)


def test_clean_commit_passes_and_planted_violation_is_refused(tmp_path: Path) -> None:
    repo, env = _clone_template(tmp_path)
    _git(repo, "add", "-A", env=env)
    first = _git(repo, "commit", "-q", "-m", "clean", env=env)
    assert first.returncode == 0, first.stdout + first.stderr

    # Plant: an active memory entry the index never lists — it would never be read.
    (repo / "doc" / "memory" / "orphan.md").write_text(
        "---\nname: orphan\ndescription: x\ntype: project\nstatus: active\n"
        "date: 2026-10-08\nsource: test\n---\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A", env=env)
    second = _git(repo, "commit", "-q", "-m", "planted", env=env)
    assert second.returncode != 0
    assert "FAIL scripts/memory_lint.py" in second.stdout + second.stderr


def test_planted_provider_name_is_refused(tmp_path: Path) -> None:
    repo, env = _clone_template(tmp_path)
    _git(repo, "add", "-A", env=env)
    assert _git(repo, "commit", "-q", "-m", "clean", env=env).returncode == 0
    (repo / "scripts" / "planted.py").write_text("# Only works on OpenAI.\n", encoding="utf-8")
    _git(repo, "add", "-A", env=env)
    result = _git(repo, "commit", "-q", "-m", "planted", env=env)
    assert result.returncode != 0
    assert "FAIL scripts/check_neutrality.py" in result.stdout + result.stderr


# --------------------------------------------------------------------------- B-AC7
# SPEC-delegated-autonomy B-AC7 places this check in `.githooks/pre-commit`.
# Measured 2026-10-20: pre-commit runs BEFORE git writes the new message, so it
# sees no message on a first commit and the PREVIOUS commit's message after
# that — a trailer check there would accept a stale `Owner-Approved:`. The check
# therefore runs from `.githooks/commit-msg`, which receives the message file.
# These tests commit for real, so they hold whichever hook carries it.

_MANDATE_KEY = "mandate-proj-first-2026-10-20"


def _opt_in(repo: Path, env: dict[str, str]) -> None:
    """Commit the template, then put the project under an active mandate."""
    _git(repo, "add", "-A", env=env)
    assert _git(repo, "commit", "-q", "-m", "clean", env=env).returncode == 0
    entry = {
        "key": _MANDATE_KEY,
        "artifact": "doc/mandates/MANDATE-proj-first.md",
        "status": "Approved",
        "approved_by": "owner",
        "approved_at": "2026-10-20T09:00:00+07:00",
        "kind": "mandate",
        "expires": "2099-12-31",
    }
    Path(env["APPROVAL_LOG"]).write_text(json.dumps(entry) + "\n", encoding="utf-8")
    (repo / "scripts" / "autonomy.json").write_text('{"project": "proj"}\n', encoding="utf-8")
    _git(repo, "add", "-A", env=env)
    opted = _git(repo, "commit", "-q", "-m", f"opt in\n\nOwner-Approved: {_MANDATE_KEY}", env=env)
    assert opted.returncode == 0, opted.stdout + opted.stderr


def _widen(repo: Path, env: dict[str, str], message: str) -> subprocess.CompletedProcess[str]:
    (repo / "scripts" / "autonomy.json").write_text('{"project": "proj", "data_globs": []}\n')
    _git(repo, "add", "-A", env=env)
    return _git(repo, "commit", "-q", "-m", message, env=env)


def test_protected_path_without_owner_trailer_is_refused_under_autonomy(tmp_path: Path) -> None:
    repo, env = _clone_template(tmp_path)
    _opt_in(repo, env)
    result = _widen(repo, env, "widen")
    assert result.returncode != 0
    out = result.stdout + result.stderr
    assert "always-human item AH5" in out
    assert "scripts/autonomy.json" in out


def test_a_stale_trailer_from_the_previous_commit_does_not_count(tmp_path: Path) -> None:
    """The exact false pass a pre-commit placement would produce: the previous
    commit carried a valid trailer, this one carries none."""
    repo, env = _clone_template(tmp_path)
    _opt_in(repo, env)  # its message carried a valid Owner-Approved trailer
    assert _widen(repo, env, "widen, no trailer").returncode != 0


def test_protected_path_with_an_unknown_trailer_key_is_refused(tmp_path: Path) -> None:
    repo, env = _clone_template(tmp_path)
    _opt_in(repo, env)
    result = _widen(repo, env, "widen\n\nOwner-Approved: made-up-key")
    assert result.returncode != 0
    assert "always-human item AH5" in result.stdout + result.stderr


def test_protected_path_with_a_resolving_owner_trailer_passes(tmp_path: Path) -> None:
    """The trailer names the owner's approval of the changed path. A mandate
    key no longer counts here (QA S1, coordinator ruling 2026-10-20; pinned in
    tests/framework/test_commit_msg_owner_trailer.py)."""
    repo, env = _clone_template(tmp_path)
    _opt_in(repo, env)
    approval = {
        "key": "autonomy-json-2026-10-20",
        "artifact": "scripts/autonomy.json",
        "status": "Approved",
        "approved_by": "owner",
        "approved_at": "2026-10-20T10:00:00+07:00",
    }
    with Path(env["APPROVAL_LOG"]).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(approval) + "\n")
    result = _widen(repo, env, "widen\n\nOwner-Approved: autonomy-json-2026-10-20")
    assert result.returncode == 0, result.stdout + result.stderr


def test_ordinary_paths_commit_freely_under_autonomy(tmp_path: Path) -> None:
    repo, env = _clone_template(tmp_path)
    _opt_in(repo, env)
    (repo / "notes.txt").write_text("ordinary work\n", encoding="utf-8")
    _git(repo, "add", "-A", env=env)
    result = _git(repo, "commit", "-q", "-m", "work", env=env)
    assert result.returncode == 0, result.stdout + result.stderr


def test_protected_path_commits_freely_without_autonomy(tmp_path: Path) -> None:
    repo, env = _clone_template(tmp_path)
    _git(repo, "add", "-A", env=env)
    assert _git(repo, "commit", "-q", "-m", "clean", env=env).returncode == 0
    (repo / "scripts" / "approve.py").write_text("# edited\n", encoding="utf-8")
    _git(repo, "add", "-A", env=env)
    result = _git(repo, "commit", "-q", "-m", "edit", env=env)
    assert result.returncode == 0, result.stdout + result.stderr
