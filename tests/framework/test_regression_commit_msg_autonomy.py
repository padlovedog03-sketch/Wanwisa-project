"""Regression test: the commit-time AH5 check is blind to deleting the project file.

QA-delegated-autonomy-B.md, 2026-10-20 (B-AC7). `check_commit` asks
`is_active(root)` first, and `is_active` reads `scripts/autonomy.json` from the
working tree. A commit that deletes that file therefore finds autonomy
inactive and skips the protected-path check, although the file it stages is
itself a protected path and the mandate is still in the registry. Measured at
9670f32: `git rm -f scripts/autonomy.json && git commit -m 'chore: tidy'`
commits with exit 0 and no trailer.

Only `.githooks/commit-msg` and the scripts it calls are installed, so the test
holds the hook under test and nothing else.

Run: `python3 -m pytest tests/framework/test_regression_commit_msg_autonomy.py -q`
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MANDATE_KEY = "mandate-proj-first-2026-10-20"


def _git(repo: Path, *args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, env=env, check=False)


def test_regression_deleting_the_project_file_needs_an_owner_trailer(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / ".githooks").mkdir()
    shutil.copy(_REPO_ROOT / ".githooks" / "commit-msg", repo / ".githooks" / "commit-msg")
    for name in ("autonomy.py", "verify_approvals.py", "check_fix_has_test.py"):
        shutil.copy(_REPO_ROOT / "scripts" / name, repo / "scripts" / name)
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
    # The framework files are committed at install, before the opt-in: the
    # opt-in commit clears only the project file and its mandate's document
    # (SPEC-delegated-autonomy-am1-guards-catch-accidents AM1-ADR-3).
    assert _git(repo, "commit", "-q", "-m", "install", env=env).returncode == 0
    registry.write_text(
        json.dumps(
            {
                "key": _MANDATE_KEY,
                "artifact": "doc/mandates/MANDATE-proj-first.md",
                "status": "Approved",
                "approved_by": "owner",
                "approved_at": "2026-10-20T09:00:00+07:00",
                "kind": "mandate",
                "expires": "2099-12-31",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (repo / "scripts" / "autonomy.json").write_text('{"project": "proj"}\n', encoding="utf-8")
    _git(repo, "add", "-A", env=env)
    opted = _git(repo, "commit", "-q", "-m", f"opt in\n\nOwner-Approved: {_MANDATE_KEY}", env=env)
    assert opted.returncode == 0, opted.stderr

    _git(repo, "rm", "-q", "scripts/autonomy.json", env=env)
    result = _git(repo, "commit", "-q", "-m", "chore: tidy", env=env)

    assert result.returncode != 0, "a commit deleting scripts/autonomy.json passed with no trailer"
    assert "always-human item AH5" in result.stderr
    assert "scripts/autonomy.json" in result.stderr


_ARGPARSE_SHIM = '''class _Namespace:
    command = "status"


class ArgumentParser:
    def __init__(self, *args, **kwargs): pass
    def add_subparsers(self, **kwargs): return self
    def add_parser(self, *args, **kwargs): return self
    def add_argument(self, *args, **kwargs): pass
    def parse_args(self, argv=None): return _Namespace()
'''


def test_regression_a_shadow_module_cannot_switch_the_commit_check_off(tmp_path: Path) -> None:
    """Re-test 1, measured at 7309362: `python3 scripts/autonomy.py` puts
    `scripts/` first on the import path, and `scripts/argparse.py` is not a
    protected path. Committed alongside it, a mandate edit with no trailer
    passed commit-msg (exit 0): the shim turned `check-commit` into `status`."""
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / ".githooks").mkdir()
    (repo / "doc" / "mandates").mkdir(parents=True)
    shutil.copy(_REPO_ROOT / ".githooks" / "commit-msg", repo / ".githooks" / "commit-msg")
    for name in ("autonomy.py", "verify_approvals.py", "check_fix_has_test.py"):
        shutil.copy(_REPO_ROOT / "scripts" / name, repo / "scripts" / name)
    (repo / "scripts" / "autonomy.json").write_text('{"project": "proj"}\n', encoding="utf-8")
    (repo / "doc" / "mandates" / "MANDATE-proj-first.md").write_text("mandate\n", encoding="utf-8")
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
    assert _git(repo, "commit", "-q", "-m", "chore: opt in", env=env).returncode == 0
    registry.write_text(
        json.dumps(
            {
                "key": _MANDATE_KEY,
                "artifact": "doc/mandates/MANDATE-proj-first.md",
                "status": "Approved",
                "approved_by": "owner",
                "approved_at": "2026-10-20T09:00:00+07:00",
                "kind": "mandate",
                "expires": "2099-12-31",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    (repo / "doc" / "mandates" / "MANDATE-proj-first.md").write_text("widened\n", encoding="utf-8")
    (repo / "scripts" / "argparse.py").write_text(_ARGPARSE_SHIM, encoding="utf-8")
    _git(repo, "add", "-A", env=env)
    result = _git(repo, "commit", "-q", "-m", "chore: tidy", env=env)

    assert result.returncode != 0, "a mandate edit with no trailer passed commit-msg behind scripts/argparse.py"
