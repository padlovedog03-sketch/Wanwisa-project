"""Tests for `scripts/check_fix_has_test.py` and `.githooks/commit-msg` — risk tier 0.

WHY THIS FILE EXISTS. Tier 0 lets a bugfix skip the spec on the promise that it
carries a reproducing test. If the hook stopped biting, that promise would be
prose again — so the planted violation (a `fix` commit with no test) is
committed for real through the hook and must be refused.

Run: `python3 -m pytest tests/framework/ -q`   (stdlib + git)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
import check_fix_has_test as cf  # noqa: E402  (path must be set up first)


def test_non_fix_commit_is_ignored() -> None:
    assert cf.violation("feat: add a thing\n", ["src/a.py"]) is None


def test_fix_with_a_test_change_passes() -> None:
    assert cf.violation("fix(api): handle null\n", ["src/a.py", "tests/test_a.py"]) is None


def test_fix_without_a_test_is_refused() -> None:
    for subject in ("fix: x", "fix(api): x", "fix!: x", "Fix(api): x"):
        assert cf.violation(subject + "\n", ["src/a.py"]) is not None, subject


def test_no_test_trailer_needs_a_reason() -> None:
    assert cf.violation("fix: x\n\nNo-Test: docs\n", ["README.md"]) is not None
    assert cf.violation("fix: x\n\nNo-Test: docs-only typo fix\n", ["README.md"]) is None


def test_comment_lines_are_not_the_subject() -> None:
    assert cf.violation("# Please enter\nfix: x\n", ["src/a.py"]) is not None


def _git(repo: Path, *args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, env=env, check=False)


def test_hook_refuses_a_real_fix_commit_without_a_test(tmp_path: Path) -> None:
    assert os.access(_REPO_ROOT / ".githooks" / "commit-msg", os.X_OK)
    repo = tmp_path / "repo"
    (repo / ".githooks").mkdir(parents=True)
    (repo / "scripts").mkdir()
    shutil.copy2(_REPO_ROOT / ".githooks" / "commit-msg", repo / ".githooks" / "commit-msg")
    shutil.copy2(_REPO_ROOT / "scripts" / "check_fix_has_test.py", repo / "scripts")
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }
    _git(repo, "init", "-q", env=env)
    _git(repo, "config", "core.hooksPath", ".githooks", env=env)
    (repo / "a.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "-A", env=env)
    refused = _git(repo, "commit", "-q", "-m", "fix: planted, no test", env=env)
    assert refused.returncode != 0
    assert "stages no change under tests/" in refused.stdout + refused.stderr

    (repo / "tests").mkdir()
    (repo / "tests" / "test_a.py").write_text("def test_a(): pass\n", encoding="utf-8")
    _git(repo, "add", "-A", env=env)
    accepted = _git(repo, "commit", "-q", "-m", "fix: with its test", env=env)
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
