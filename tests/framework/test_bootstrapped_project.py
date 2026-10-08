"""The framework's own tests must stay green in a project made from it.

WHY THIS FILE EXISTS. `tests/framework/` is a permanent step of the exit gate,
and every project starts as a copy of this repo. A test that is only true of
the unfilled template — one that relies on `<PROJECT>` still being present, or
on the approval registry being empty — would turn every new project's exit
gate red on day one, and the cheapest fix a team reaches for is deleting the
step. The first draft of the open-standards wave shipped exactly that defect;
this file runs the real bootstrap on a scratch copy and the suite inside it,
so it cannot ship again.

Run: `python3 -m pytest tests/framework/ -q`   (stdlib + git + bash)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
#: Set inside the nested run so this test does not bootstrap a copy of a copy.
_NESTED = "JARVIS_FRAMEWORK_NESTED"


@pytest.mark.skipif(os.environ.get(_NESTED) == "1", reason="already inside the nested run")
def test_framework_suite_is_green_after_bootstrap(tmp_path: Path) -> None:
    project = tmp_path / "acme"
    shutil.copytree(
        _REPO_ROOT,
        project,
        symlinks=True,
        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.local.txt"),
    )
    home = tmp_path / "home"
    home.mkdir()
    env = {**os.environ, "HOME": str(home), _NESTED: "1"}
    for var in ("APPROVAL_LOG", "MEMORY_DIR", "NEUTRALITY_ROOT", "SCAR_DIR"):
        env.pop(var, None)

    boot = subprocess.run(
        ["bash", "scripts/bootstrap.sh"],
        cwd=project,
        input="Acme Portal\nacme\n\n\n",
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )
    assert boot.returncode == 0, boot.stdout + boot.stderr
    assert "<PROJECT>" not in (project / "AGENTS.md").read_text(encoding="utf-8")

    suite = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/framework/", "-q", "-p", "no:cacheprovider"],
        cwd=project,
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
        check=False,
    )
    assert suite.returncode == 0, suite.stdout[-3000:] + suite.stderr[-2000:]

    neutrality = subprocess.run(
        [sys.executable, "scripts/check_neutrality.py"],
        cwd=project,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert neutrality.returncode == 0
    assert neutrality.stdout.startswith("SKIP:"), "a project must see the skip, not a silent pass"
