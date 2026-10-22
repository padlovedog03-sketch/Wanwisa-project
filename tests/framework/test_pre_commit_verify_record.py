"""`.githooks/pre-commit` refuses a commit whose staged tree's newest gate record is RED.

SPEC-verify-tiers-merge-gate-am3-commit-on-red, AM3-AC1 to AM3-AC13.

WHY THIS FILE EXISTS. Incident 1 (doc/memory/gate-exit-code-before-commit.md):
a commit went through while verify-full had just printed RED on that very tree.
The hook now hashes the tree being committed and refuses when the newest
`full`/`handoff` record taken on exactly that tree is RED. Every test commits
for real through the hook in a throwaway repo built the way
`tests/framework/test_pre_commit.py::_clone_template` builds one; records are
planted as JSON files (no gate is ever run here).

Run: `python3 -m pytest tests/framework/test_pre_commit_verify_record.py -q`
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_OTHER_TREE = "0" * 40
_NO_RECORD = "WARN no gate record for the staged tree"


def _env(tmp_path: Path) -> dict:
    """The parent environment minus everything that would steer the hook or
    the recorder: verify-full exports VERIFY_* while tests/framework runs
    inside it, and a leaked GIT_DIR/GIT_INDEX_FILE would point git elsewhere.
    HOME is a scratch dir so nothing can reach the owner's real registry."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("VERIFY_", "GIT_"))}
    for var in ("MEMORY_DIR", "NEUTRALITY_ROOT", "SCAR_DIR", "XDG_CONFIG_HOME"):
        env.pop(var, None)
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env.update({
        "HOME": str(home),
        "APPROVAL_LOG": str(tmp_path / "registry.jsonl"),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
    })
    return env


def _git(repo: Path, *args: str, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True,
                          env=env, check=False)


@pytest.fixture(scope="module")
def _base(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Built once: the hook, the layer-1 scripts, this repo's memory and scars,
    a placeholder AGENTS.md, and `.verify/` git-ignored. Nothing committed."""
    root = tmp_path_factory.mktemp("base")
    repo = root / "repo"
    repo.mkdir()
    ignore = shutil.ignore_patterns("__pycache__", "*.local.txt")
    for rel in (".githooks", ".agents", "scripts", "doc/memory", "doc/scars", "doc/templates"):
        if (_REPO_ROOT / rel).is_dir():
            shutil.copytree(_REPO_ROOT / rel, repo / rel, ignore=ignore)
    (repo / "AGENTS.md").write_text("# AGENTS.md — <PROJECT>\nrules\n", encoding="utf-8")
    (repo / ".gitignore").write_text(".verify/\n", encoding="utf-8")
    (repo / "f.txt").write_text("f\n", encoding="utf-8")
    (repo / "g.txt").write_text("g\n", encoding="utf-8")
    env = _env(root)
    _git(repo, "init", "-q", env=env)
    _git(repo, "config", "core.hooksPath", ".githooks", env=env)
    return repo


@pytest.fixture()
def repo_env(_base: Path, tmp_path: Path) -> tuple:
    repo = tmp_path / "repo"
    shutil.copytree(_base, repo, symlinks=True)
    return repo, _env(tmp_path)


def _head(repo: Path, env: dict) -> Optional[str]:
    r = _git(repo, "rev-parse", "-q", "--verify", "HEAD", env=env)
    return r.stdout.strip() or None


def _stage_all(repo: Path, env: dict) -> str:
    _git(repo, "add", "-A", env=env)
    return _git(repo, "write-tree", env=env).stdout.strip()


def _tree_of(repo: Path, env: dict, *paths: str) -> str:
    """The tree HEAD + `paths` (all of the working tree when none are named)
    would have, built in a throwaway index so the real index is untouched."""
    scratch = {**env, "GIT_INDEX_FILE": str(repo.parent / "scratch-index")}
    _git(repo, "read-tree", "HEAD", env=scratch)
    _git(repo, "add", *(paths or ("-A",)), env=scratch)
    tree = _git(repo, "write-tree", env=scratch).stdout.strip()
    os.unlink(scratch["GIT_INDEX_FILE"])
    return tree


def _record(repo: Path, name: str, tier: str, verdict: object, before: object,
            after: object, ended_at: str = "2026-10-22T10:00:00Z") -> Path:
    run = repo / ".verify" / "runs" / name
    run.mkdir(parents=True, exist_ok=True)
    record = {"schema": 1, "tier": tier, "run_id": name, "started_at": ended_at,
              "ended_at": ended_at,
              "tree": {"before": before, "after": after, "head": None, "dirty": None},
              "verdict": verdict}
    path = run / "record.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def _commit(repo: Path, env: dict, *args: str) -> tuple:
    """(result, combined output, HEAD moved?)."""
    before = _head(repo, env)
    result = _git(repo, "commit", "-q", "-m", "c", *args, env=env)
    return result, result.stdout + result.stderr, _head(repo, env) != before


def _assert_refused(result: subprocess.CompletedProcess, out: str, moved: bool) -> None:
    assert result.returncode != 0 and not moved, out


def _assert_passed(result: subprocess.CompletedProcess, out: str, moved: bool) -> None:
    assert result.returncode == 0 and moved, out


def _rel(name: str) -> str:
    return ".verify/runs/%s/record.json" % name


# --------------------------------------------------------------------------- AM3-AC1
def test_ac1_matching_red_full_record_is_refused_and_named(repo_env: tuple) -> None:
    repo, env = repo_env
    tree = _stage_all(repo, env)
    _record(repo, "20261022T100000Z-1", "full", "RED", tree, tree)
    result, out, moved = _commit(repo, env)
    _assert_refused(result, out, moved)
    assert "FAIL verify record" in out
    assert _rel("20261022T100000Z-1") in out


# --------------------------------------------------------------------------- AM3-AC2
@pytest.mark.parametrize(("tier", "verdict"), [
    ("full", "INCOMPLETE"), ("full", "GREEN"), ("handoff", "OK")])
def test_ac2_non_red_verdicts_pass_and_are_printed_verbatim(
        repo_env: tuple, tier: str, verdict: str) -> None:
    repo, env = repo_env
    tree = _stage_all(repo, env)
    _record(repo, "20261022T100000Z-1", tier, verdict, tree, tree)
    result, out, moved = _commit(repo, env)
    _assert_passed(result, out, moved)
    assert "verify record: %s for the staged tree" % verdict in out
    if verdict != "GREEN":
        assert "GREEN" not in out


# --------------------------------------------------------------------------- AM3-AC3
def test_ac3_empty_handoff_record_warns_and_never_claims_a_pass(repo_env: tuple) -> None:
    repo, env = repo_env
    tree = _stage_all(repo, env)
    _record(repo, "20261022T100000Z-1-handoff", "handoff", "EMPTY", tree, tree)
    result, out, moved = _commit(repo, env)
    _assert_passed(result, out, moved)
    assert _NO_RECORD in out
    assert "verify record:" not in out


# --------------------------------------------------------------------------- AM3-AC4
def test_ac4a_later_ended_green_beats_earlier_red_despite_name_order(repo_env: tuple) -> None:
    repo, env = repo_env
    tree = _stage_all(repo, env)
    _record(repo, "20261022T100002Z-1", "full", "RED", tree, tree, "2026-10-22T10:00:00Z")
    _record(repo, "20261022T100001Z-1", "full", "GREEN", tree, tree, "2026-10-22T10:00:05Z")
    result, out, moved = _commit(repo, env)
    _assert_passed(result, out, moved)
    assert "verify record: GREEN" in out


def test_ac4b_later_ended_red_beats_earlier_green_despite_name_order(repo_env: tuple) -> None:
    repo, env = repo_env
    tree = _stage_all(repo, env)
    _record(repo, "20261022T100002Z-1", "full", "GREEN", tree, tree, "2026-10-22T10:00:00Z")
    _record(repo, "20261022T100001Z-1", "full", "RED", tree, tree, "2026-10-22T10:00:05Z")
    result, out, moved = _commit(repo, env)
    _assert_refused(result, out, moved)
    assert _rel("20261022T100001Z-1") in out


@pytest.mark.parametrize(("first", "second", "refused"), [
    ("GREEN", "RED", True), ("RED", "GREEN", False)])
def test_ac4c_same_ended_at_the_later_directory_name_wins(
        repo_env: tuple, first: str, second: str, refused: bool) -> None:
    repo, env = repo_env
    tree = _stage_all(repo, env)
    _record(repo, "20261022T100000Z-1", "full", first, tree, tree)
    _record(repo, "20261022T100000Z-2", "full", second, tree, tree)
    result, out, moved = _commit(repo, env)
    (_assert_refused if refused else _assert_passed)(result, out, moved)


# --------------------------------------------------------------------------- AM3-AC5
def _plant_ac5(repo: Path, tree: str, case: str) -> None:
    runs = repo / ".verify" / "runs"
    if case == "stale":
        _record(repo, "20261022T100000Z-1", "full", "RED", _OTHER_TREE, _OTHER_TREE)
    elif case == "no-verify-dir":
        assert not (repo / ".verify").exists()
    elif case == "empty-runs":
        runs.mkdir(parents=True)
    elif case == "dirs-without-record":
        (runs / "20261022T100000Z-1").mkdir(parents=True)
        (runs / "20261022T100000Z-1" / "steps.tsv").write_text("x\t0\t0\t0\t\n")
        (runs / "20261022T100001Z-1-fast" / "junit").mkdir(parents=True)
    elif case == "fast-null-tree":
        _record(repo, "20261022T100000Z-1-fast", "fast", "RED", None, None)
    elif case == "changed-mid-run":
        _record(repo, "20261022T100000Z-1", "full", "RED", _OTHER_TREE, tree)


@pytest.mark.parametrize("case", ["stale", "no-verify-dir", "empty-runs",
                                  "dirs-without-record", "fast-null-tree",
                                  "changed-mid-run"])
def test_ac5_no_usable_record_warns_exactly_once_and_passes(repo_env: tuple, case: str) -> None:
    repo, env = repo_env
    tree = _stage_all(repo, env)
    _plant_ac5(repo, tree, case)
    result, out, moved = _commit(repo, env)
    _assert_passed(result, out, moved)
    lines = [ln for ln in out.splitlines() if _NO_RECORD in ln]
    assert len(lines) == 1, out
    assert "scripts/verify-full.sh" in lines[0]


# --------------------------------------------------------------------------- AM3-AC6
def _committed_base(repo: Path, env: dict) -> None:
    _stage_all(repo, env)
    result, out, moved = _commit(repo, env)
    _assert_passed(result, out, moved)


def test_ac6a_commit_a_uses_gits_index_not_dot_git_index(repo_env: tuple) -> None:
    repo, env = repo_env
    _committed_base(repo, env)
    (repo / "f.txt").write_text("f edited\n")
    tree = _tree_of(repo, env)
    _record(repo, "20261022T100000Z-1", "full", "RED", tree, tree)
    result, out, moved = _commit(repo, env, "-a")
    _assert_refused(result, out, moved)
    assert "FAIL verify record" in out


def test_ac6b_commit_path_leaves_g_out_so_a_working_tree_red_does_not_match(
        repo_env: tuple) -> None:
    repo, env = repo_env
    _committed_base(repo, env)
    (repo / "f.txt").write_text("f edited\n")
    (repo / "g.txt").write_text("g edited\n")
    tree = _tree_of(repo, env)
    _record(repo, "20261022T100000Z-1", "full", "RED", tree, tree)
    result, out, moved = _commit(repo, env, "--", "f.txt")
    _assert_passed(result, out, moved)
    assert _NO_RECORD in out


def test_ac6c_commit_path_red_on_exactly_that_tree_is_refused(repo_env: tuple) -> None:
    repo, env = repo_env
    _committed_base(repo, env)
    (repo / "f.txt").write_text("f edited\n")
    (repo / "g.txt").write_text("g edited\n")
    tree = _tree_of(repo, env, "f.txt")
    _record(repo, "20261022T100000Z-1", "full", "RED", tree, tree)
    result, out, moved = _commit(repo, env, "--", "f.txt")
    _assert_refused(result, out, moved)
    assert "FAIL verify record" in out


# --------------------------------------------------------------------------- AM3-AC7
def test_ac7_a_record_in_another_checkout_never_counts(repo_env: tuple, tmp_path: Path) -> None:
    repo, env = repo_env
    _committed_base(repo, env)
    wt = tmp_path / "wt"
    added = _git(repo, "worktree", "add", "-q", "-b", "side", str(wt), env=env)
    assert added.returncode == 0, added.stderr
    (wt / "n.txt").write_text("n\n")
    tree = _stage_all(wt, env)
    _record(repo, "20261022T100000Z-1", "full", "RED", tree, tree)
    assert not (wt / ".verify").exists()
    result, out, moved = _commit(wt, env)
    _assert_passed(result, out, moved)
    assert _NO_RECORD in out


# --------------------------------------------------------------------------- AM3-AC8
def _matching(staged: str, **override: object) -> dict:
    record = {"schema": 1, "tier": "full", "run_id": "x", "ended_at": "2026-10-22T10:00:00Z",
              "tree": {"before": staged, "after": staged}, "verdict": "RED"}
    record.update(override)
    return record


_HOSTILE = {
    "malformed": lambda t: b"{not json",
    "truncated": lambda t: json.dumps(_matching(t)).encode()[:40],
    "empty": lambda t: b"",
    "array": lambda t: json.dumps([_matching(t)]).encode(),
    "tree-number": lambda t: json.dumps(_matching(t, tree=5)).encode(),
    "after-list": lambda t: json.dumps(_matching(t, tree={"before": t, "after": [t]})).encode(),
    "verdict-missing": lambda t: json.dumps(
        {k: v for k, v in _matching(t).items() if k != "verdict"}).encode(),
    "verdict-lower": lambda t: json.dumps(_matching(t, verdict="red")).encode(),
    "verdict-space": lambda t: json.dumps(_matching(t, verdict="RED ")).encode(),
    "verdict-title": lambda t: json.dumps(_matching(t, verdict="Red")).encode(),
    "non-utf8": lambda t: json.dumps(_matching(t, run_id="X")).encode().replace(b"X", b"\xff\xfe"),
    "over-1mib": lambda t: json.dumps(_matching(t)).encode() + b" " * (1 << 20),
}


@pytest.mark.parametrize("case", sorted(_HOSTILE) + [
    "symlinked-record", "symlinked-run-dir", "record-is-a-directory"])
def test_ac8_hostile_record_warns_by_path_and_never_refuses_or_passes_silently(
        repo_env: tuple, tmp_path: Path, case: str) -> None:
    repo, env = repo_env
    tree = _stage_all(repo, env)
    name = "20261022T100000Z-1"
    run = repo / ".verify" / "runs" / name
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "record.json").write_text(json.dumps(_matching(tree)))
    if case == "symlinked-run-dir":
        run.parent.mkdir(parents=True)
        run.symlink_to(elsewhere, target_is_directory=True)
    else:
        run.mkdir(parents=True)
        if case == "symlinked-record":
            (run / "record.json").symlink_to(elsewhere / "record.json")
        elif case == "record-is-a-directory":
            (run / "record.json").mkdir()
        else:
            (run / "record.json").write_bytes(_HOSTILE[case](tree))
    result, out, moved = _commit(repo, env)
    _assert_passed(result, out, moved)
    assert "Traceback" not in out
    assert "verify record:" not in out
    assert "WARN unreadable gate record ignored: %s" % _rel(name) in out
    assert _NO_RECORD in out


def test_ac8_control_characters_in_a_run_name_are_escaped_on_one_line(repo_env: tuple) -> None:
    repo, env = repo_env
    _stage_all(repo, env)
    run = repo / ".verify" / "runs" / "2026\nforged\x01"
    run.mkdir(parents=True)
    (run / "record.json").write_text("{")
    result, out, moved = _commit(repo, env)
    _assert_passed(result, out, moved)
    assert "WARN unreadable gate record ignored: .verify/runs/2026\\x0aforged\\x01/record.json" in out
    assert "\nforged" not in out


def test_ac8i_an_unreadable_newer_record_never_cancels_a_matching_red(repo_env: tuple) -> None:
    repo, env = repo_env
    tree = _stage_all(repo, env)
    _record(repo, "20261022T100000Z-1", "full", "RED", tree, tree)
    newer = repo / ".verify" / "runs" / "20261022T100001Z-1"
    newer.mkdir()
    (newer / "record.json").write_text("{")
    result, out, moved = _commit(repo, env)
    _assert_refused(result, out, moved)
    assert "FAIL verify record" in out


def test_ac8ii_an_unreadable_newer_record_never_lets_an_older_green_speak(repo_env: tuple) -> None:
    repo, env = repo_env
    tree = _stage_all(repo, env)
    _record(repo, "20261022T100000Z-1", "full", "GREEN", tree, tree)
    newer = repo / ".verify" / "runs" / "20261022T100001Z-1"
    newer.mkdir()
    (newer / "record.json").write_text("{")
    result, out, moved = _commit(repo, env)
    _assert_passed(result, out, moved)
    assert "WARN unreadable gate record ignored: %s" % _rel("20261022T100001Z-1") in out
    assert _NO_RECORD in out
    assert "GREEN" not in out


# --------------------------------------------------------------------------- AM3-AC9
def test_ac9a_a_lookup_that_cannot_run_refuses_and_names_the_escape(repo_env: tuple) -> None:
    repo, env = repo_env
    (repo / "scripts" / "verify_record.py").write_text("import sys\nsys.exit(3)\n")
    _stage_all(repo, env)
    result, out, moved = _commit(repo, env)
    _assert_refused(result, out, moved)
    assert "FAIL verify record — the check could not run (exit 3)" in out
    assert "--no-verify" in out


def test_ac9b_a_missing_recorder_warns_and_passes(repo_env: tuple) -> None:
    repo, env = repo_env
    (repo / "scripts" / "verify_record.py").unlink()
    _stage_all(repo, env)
    result, out, moved = _commit(repo, env)
    _assert_passed(result, out, moved)
    assert "WARN verify record not checked — recorder missing" in out


def test_ac9c_an_index_naming_a_missing_object_fails_loudly(repo_env: tuple) -> None:
    repo, env = repo_env
    _stage_all(repo, env)
    _git(repo, "update-index", "--add", "--cacheinfo", "100644,%s,ghost" % ("1" * 40), env=env)
    result, out, moved = _commit(repo, env)
    _assert_refused(result, out, moved)
    assert "staged tree could not be hashed" in out


# --------------------------------------------------------------------------- AM3-AC10
def test_ac10_no_verify_still_skips_the_hook(repo_env: tuple) -> None:
    """Pins the declared escape (limit 5): nothing may quietly remove it."""
    repo, env = repo_env
    tree = _stage_all(repo, env)
    _record(repo, "20261022T100000Z-1", "full", "RED", tree, tree)
    result, out, moved = _commit(repo, env, "--no-verify")
    _assert_passed(result, out, moved)


# --------------------------------------------------------------------------- AM3-AC11
def test_ac11_the_record_check_adds_to_the_other_checks_never_replaces_them(
        repo_env: tuple) -> None:
    repo, env = repo_env
    (repo / "doc" / "memory" / "orphan.md").write_text(
        "---\nname: orphan\ndescription: x\ntype: project\nstatus: active\n"
        "date: 2026-10-08\nsource: test\n---\n", encoding="utf-8")
    tree = _stage_all(repo, env)
    _record(repo, "20261022T100000Z-1", "full", "RED", tree, tree)
    result, out, moved = _commit(repo, env)
    _assert_refused(result, out, moved)
    assert "FAIL scripts/memory_lint.py" in out
    assert "FAIL verify record" in out


# --------------------------------------------------------------------------- AM3-AC12
@pytest.mark.parametrize(("step", "verdict", "refused"), [
    ("lint\t0\t0\t1\t\n", "INCOMPLETE", False),
    ("test\t1\t0\t0\t\n", "RED", True)])
def test_ac12_real_recorder_output_is_read_correctly(
        repo_env: tuple, step: str, verdict: str, refused: bool) -> None:
    """The record comes from the real `finalize`, not a hand-written file.
    verify-full.sh itself is never run here (minutes, and it would recurse)."""
    repo, env = repo_env
    tree = _stage_all(repo, env)
    run = repo / ".verify" / "runs" / "20261022T100000Z-1"
    run.mkdir(parents=True)
    (run / "steps.tsv").write_text(step, encoding="utf-8")
    fin = subprocess.run(
        ["python3", "-I", "scripts/verify_record.py", "finalize", "--tier", "full",
         "--run-dir", str(run.relative_to(repo)), "--tree-before", tree, "--tree-after", tree],
        cwd=repo, capture_output=True, text=True, env=env, check=False)
    assert fin.returncode == 0, fin.stdout + fin.stderr
    written = json.loads((run / "record.json").read_text(encoding="utf-8"))
    assert written["verdict"] == verdict and written["tree"]["after"] == tree
    result, out, moved = _commit(repo, env)
    if refused:
        _assert_refused(result, out, moved)
        assert "FAIL verify record" in out
    else:
        _assert_passed(result, out, moved)
        assert "verify record: INCOMPLETE for the staged tree" in out
        assert "GREEN" not in out


# --------------------------------------------------------------------------- AM3-AC13
def test_ac13_a_fixture_shaped_like_test_pre_commit_still_commits(tmp_path: Path) -> None:
    """The shape `tests/framework/test_pre_commit.py` commits: no `.verify`, no
    `.gitignore`, PROJECT tokens only, AGENTS.md in template mode (F22). That
    file itself must stay green unchanged; this pins why it can."""
    repo = tmp_path / "repo"
    repo.mkdir()
    ignore = shutil.ignore_patterns("__pycache__", "*.local.txt")
    for rel in (".githooks", ".agents", "scripts", "doc/memory", "doc/scars", "doc/templates"):
        if (_REPO_ROOT / rel).is_dir():
            shutil.copytree(_REPO_ROOT / rel, repo / rel, ignore=ignore)
    (repo / "AGENTS.md").write_text("# AGENTS.md — <PROJECT>\nrules\n", encoding="utf-8")
    env = _env(tmp_path)
    _git(repo, "init", "-q", env=env)
    _git(repo, "config", "core.hooksPath", ".githooks", env=env)
    _stage_all(repo, env)
    result, out, moved = _commit(repo, env)
    _assert_passed(result, out, moved)
    assert _NO_RECORD in out
    assert "FAIL" not in out
