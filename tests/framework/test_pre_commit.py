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
    for rel in (".githooks", "scripts", "doc/memory", "doc/scars", "doc/templates"):
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
