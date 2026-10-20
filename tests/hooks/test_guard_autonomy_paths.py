"""`guard_autonomy_paths.py` — Write/Edit guard on the protected paths (B-AC6).

While autonomy is active, the assistant must not be able to edit the mandate,
the always-human list, or the code that enforces either (R4: it can never
create, widen or renew its own authority). The registry guard already denies
Write-tool writes to the registry; this guard covers everything else that
defines or enforces the assistant's authority inside the repo.

Both halves are pinned: refused under an active mandate, allowed when autonomy
is not active (R6, ADR-6 — outside autonomy these files change through the
ordinary tier-2 gates, which is how this very feature gets built).

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
_GUARD = _REPO_ROOT / ".claude" / "hooks" / "guard_autonomy_paths.py"
_SETTINGS = _REPO_ROOT / ".claude" / "settings.json"

_EXIT_ALLOW = 0
_EXIT_BLOCK = 2

PROTECTED = [
    "scripts/autonomy.json",
    "scripts/autonomy.py",
    "scripts/approve.py",
    "scripts/approve.sh",
    "scripts/verify_approvals.py",
    "scripts/delegate.sh",
    "scripts/revoke.sh",
    "scripts/override.sh",
    "scripts/away.sh",
    "scripts/evolve.sh",
    "scripts/release.sh",
    "scripts/check_neutrality.py",
    "doc/mandates/MANDATE-proj-first.md",
    "doc/orders/ORDER-proj-x.md",
    "doc/decisions/decision-log.jsonl",
    "doc/evolution/ledger.jsonl",
    ".claude/hooks/guard_bash.py",
    ".claude/settings.json",
    ".githooks/pre-commit",
    "ci-examples/github-actions.yml",
]
UNPROTECTED = ["src/app.py", "doc/specs/SPEC-x.md", "tests/test_x.py", "scripts/memory_lint.py"]


def _make_project(tmp_path: Path, *, active: bool) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, timeout=30)
    registry = tmp_path / "registry.jsonl"
    registry.write_text("", encoding="utf-8")
    if active:
        (repo / "scripts").mkdir()
        (repo / "scripts" / "autonomy.json").write_text('{"project": "proj"}', encoding="utf-8")
        entry = {
            "key": "mandate-proj-first-2026-10-20",
            "artifact": "doc/mandates/MANDATE-proj-first.md",
            "status": "Approved",
            "approved_by": "owner",
            "approved_at": "2026-10-20T09:00:00+07:00",
            "kind": "mandate",
            "expires": "2099-12-31",
        }
        registry.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    return repo, registry


def _run(tool: str, file_path: str, *, cwd: Path, registry: Path) -> subprocess.CompletedProcess[str]:
    key = "notebook_path" if tool == "NotebookEdit" else "file_path"
    payload = json.dumps({"tool_name": tool, "tool_input": {key: file_path}})
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


@pytest.mark.parametrize("rel", PROTECTED)
def test_protected_paths_are_refused_under_autonomy(rel: str, tmp_path: Path) -> None:
    repo, registry = _make_project(tmp_path, active=True)
    result = _run("Edit", rel, cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK, f"{rel} allowed: {result.stderr}"
    assert "always-human item AH5" in result.stderr
    assert rel in result.stderr


@pytest.mark.parametrize("tool", ["Write", "Edit", "MultiEdit", "NotebookEdit"])
def test_every_write_tool_is_covered_and_absolute_paths_resolve(tool: str, tmp_path: Path) -> None:
    repo, registry = _make_project(tmp_path, active=True)
    result = _run(tool, str(repo / "doc" / "mandates" / "MANDATE-proj-first.md"), cwd=repo, registry=registry)
    assert result.returncode == _EXIT_BLOCK, result.stderr


@pytest.mark.parametrize("rel", UNPROTECTED)
def test_ordinary_paths_are_allowed_under_autonomy(rel: str, tmp_path: Path) -> None:
    repo, registry = _make_project(tmp_path, active=True)
    assert _run("Edit", rel, cwd=repo, registry=registry).returncode == _EXIT_ALLOW


@pytest.mark.parametrize("rel", PROTECTED)
def test_protected_paths_are_allowed_without_autonomy(rel: str, tmp_path: Path) -> None:
    repo, registry = _make_project(tmp_path, active=False)
    result = _run("Edit", rel, cwd=repo, registry=registry)
    assert result.returncode == _EXIT_ALLOW, result.stderr


def test_malformed_payload_fails_open(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(_GUARD)],
        input="not json",
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        cwd=str(tmp_path),
    )
    assert result.returncode == _EXIT_ALLOW


def test_the_guard_is_registered_for_every_write_tool() -> None:
    """An unregistered hook never runs — the quietest failure there is."""
    settings = json.loads(_SETTINGS.read_text(encoding="utf-8"))
    entries = settings["hooks"]["PreToolUse"]
    matchers = [
        e["matcher"]
        for e in entries
        if any("guard_autonomy_paths.py" in h["command"] for h in e["hooks"])
    ]
    assert matchers, "guard_autonomy_paths.py is not registered"
    assert set(matchers[0].split("|")) >= {"Write", "Edit", "MultiEdit", "NotebookEdit"}
