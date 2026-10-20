"""Tests for `scripts/check_neutrality.py` and the open-standard layout it guards.

WHY THIS FILE EXISTS. RUNTIME-CONTRACT criterion 1 ("layers ๐–๑ carry no
provider name, checked by machine") was false when first written and nobody
noticed for weeks. A checker that always prints 0 would make it false again
without a sound, so every rule here is proven by planting the violation it
exists to catch (NORTH-STAR truth 2). The layout pins exist because the whole
point of moving to AGENTS.md and `.agents/skills/` is lost the moment the
adapter copy and the canonical copy can drift apart.

Run: `python3 -m pytest tests/framework/ -q`   (stdlib only)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "check_neutrality.py"


def _run(root: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "NEUTRALITY_ROOT": str(root)}
    return subprocess.run(
        [sys.executable, str(_SCRIPT)], capture_output=True, text=True, env=env, check=False
    )


def _template(tmp_path: Path) -> Path:
    root = tmp_path / "tpl"
    root.mkdir()
    (root / "AGENTS.md").write_text("# AGENTS.md — <PROJECT>\nrules\n", encoding="utf-8")
    (root / "scripts").mkdir()
    (root / "scripts" / "tool.py").write_text("print('neutral')\n", encoding="utf-8")
    return root


def test_this_repo_is_neutral() -> None:
    result = _run(_REPO_ROOT)
    assert result.returncode == 0, result.stdout


def test_planted_provider_name_in_core_fails(tmp_path: Path) -> None:
    root = _template(tmp_path)
    assert _run(root).returncode == 0
    (root / "scripts" / "tool.py").write_text("# needs Anthropic to run\n", encoding="utf-8")
    result = _run(root)
    assert result.returncode == 1
    assert "scripts/tool.py:1: Anthropic" in result.stdout


def test_provider_name_in_adapter_folder_is_allowed(tmp_path: Path) -> None:
    root = _template(tmp_path)
    (root / ".claude").mkdir()
    (root / ".claude" / "settings.json").write_text('{"claude": true}\n', encoding="utf-8")
    assert _run(root).returncode == 0


def test_symlinked_skill_is_not_double_counted_or_followed(tmp_path: Path) -> None:
    root = _template(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "SKILL.md").write_text("uses gemini\n", encoding="utf-8")
    (root / ".agents").mkdir()
    (root / ".agents" / "linked").symlink_to(outside)
    assert _run(root).returncode == 0


def test_local_denylist_catches_a_project_leak_anywhere(tmp_path: Path) -> None:
    root = _template(tmp_path)
    (root / ".claude").mkdir()
    (root / ".claude" / "hook.py").write_text("# copied from ACME-PORTAL\n", encoding="utf-8")
    assert _run(root).returncode == 0
    (root / "scripts" / "neutrality-denylist.local.txt").write_text(
        "# project terms\nacme-portal\n", encoding="utf-8"
    )
    result = _run(root)
    assert result.returncode == 1
    assert ".claude/hook.py:1: ACME-PORTAL" in result.stdout


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, capture_output=True, check=True)


def _git_template(tmp_path: Path) -> Path:
    """A template under git with a local denylist, tracked files indexed."""
    root = _template(tmp_path)
    (root / "scripts" / "neutrality-denylist.local.txt").write_text(
        "acme-portal\n", encoding="utf-8"
    )
    _git(root, "init", "-q")
    _git(root, "add", "AGENTS.md", "scripts/tool.py")
    return root


def test_untracked_worktree_copy_is_not_scanned(tmp_path: Path) -> None:
    """An isolated agent's worktree holds an untracked copy of the denylist
    (and of anything else); scanning it turned verify-full red for nothing."""
    root = _git_template(tmp_path)
    wt = root / ".claude" / "worktrees" / "agent-x"
    (wt / "scripts").mkdir(parents=True)
    (wt / "scripts" / "neutrality-denylist.local.txt").write_text("acme-portal\n", encoding="utf-8")
    (wt / "notes.md").write_text("ACME-PORTAL\n", encoding="utf-8")
    (root / "scripts" / "scratch.py").write_text("# uses openai\n", encoding="utf-8")
    result = _run(root)
    assert result.returncode == 0, result.stdout
    assert "0 project leak(s)" in result.stdout


def test_tracked_leak_is_still_caught_in_a_git_repo(tmp_path: Path) -> None:
    root = _git_template(tmp_path)
    (root / ".claude").mkdir()
    (root / ".claude" / "hook.py").write_text("# copied from ACME-PORTAL\n", encoding="utf-8")
    (root / "scripts" / "tool.py").write_text("# needs Anthropic\n", encoding="utf-8")
    _git(root, "add", ".claude/hook.py")
    # Even force-tracked, the denylist is never reported as a leak of itself.
    _git(root, "add", "-f", "scripts/neutrality-denylist.local.txt")
    result = _run(root)
    assert result.returncode == 1
    assert ".claude/hook.py:1: ACME-PORTAL" in result.stdout
    assert "scripts/tool.py:1: Anthropic" in result.stdout
    assert "neutrality-denylist.local.txt:" not in result.stdout


def test_outside_git_still_scans_but_skips_worktrees(tmp_path: Path) -> None:
    """Fallback for a plain copy with no `.git` (README quick start is `cp -R`)."""
    root = _template(tmp_path)
    (root / "scripts" / "neutrality-denylist.local.txt").write_text(
        "acme-portal\n", encoding="utf-8"
    )
    wt = root / ".claude" / "worktrees" / "agent-x"
    wt.mkdir(parents=True)
    (wt / "notes.md").write_text("ACME-PORTAL\n", encoding="utf-8")
    env = {**os.environ, "NEUTRALITY_ROOT": str(root), "GIT_CEILING_DIRECTORIES": str(tmp_path)}

    def run() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(_SCRIPT)], capture_output=True, text=True, env=env, check=False
        )

    first = run()
    assert first.returncode == 0, first.stdout
    (root / "notes.md").write_text("ACME-PORTAL\n", encoding="utf-8")
    result = run()
    assert result.returncode == 1
    assert "notes.md:1: ACME-PORTAL" in result.stdout
    assert ".claude/worktrees" not in result.stdout


def test_bootstrapped_project_skips_loudly(tmp_path: Path) -> None:
    root = _template(tmp_path)
    (root / "AGENTS.md").write_text("# AGENTS.md — Payments\n", encoding="utf-8")
    (root / "scripts" / "tool.py").write_text("# deploys to Azure\n", encoding="utf-8")
    result = _run(root)
    assert result.returncode == 0
    assert result.stdout.startswith("SKIP:")


def test_denylist_is_git_ignored() -> None:
    """Read `.gitignore` itself, so this holds in a fresh copy with no `.git` yet."""
    ignored = (_REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "scripts/neutrality-denylist.local.txt" in ignored, (
        "the denylist names a project; it must never be committed"
    )


def test_agent_worktrees_are_git_ignored() -> None:
    ignored = (_REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".claude/worktrees/" in ignored, "an agent's worktree is not part of this repo"


def test_claude_shim_imports_agents_md_and_holds_no_rules() -> None:
    shim = (_REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "\n@AGENTS.md" in shim
    assert "## " not in shim, "rules belong in AGENTS.md, where every tool can read them"


def test_every_skill_is_canonical_in_agents_and_linked_for_claude() -> None:
    canonical = {p.name for p in (_REPO_ROOT / ".agents" / "skills").iterdir() if p.is_dir()}
    linked = _REPO_ROOT / ".claude" / "skills"
    assert canonical, "no skills found"
    assert {p.name for p in linked.iterdir()} == canonical
    for name in canonical:
        link = linked / name
        assert link.is_symlink(), f"{link} must be a link, not a second copy that can drift"
        assert link.resolve() == (_REPO_ROOT / ".agents" / "skills" / name).resolve()
        assert (link / "SKILL.md").is_file()


def test_bootstrap_copy_keeps_skill_links_working(tmp_path: Path) -> None:
    """README's quick start is `cp -R`; macOS and GNU cp both keep relative
    symlinks as links by default with -R, so the copy must still resolve."""
    dest = tmp_path / "copy"
    shutil.copytree(_REPO_ROOT, dest, symlinks=True, ignore=shutil.ignore_patterns(".git"))
    for link in (dest / ".claude" / "skills").iterdir():
        assert (link / "SKILL.md").is_file(), f"{link} broke after copying"
