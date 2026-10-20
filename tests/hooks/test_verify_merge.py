"""Increment D — the merge gate: one machine full run per merge candidate.

Spec: doc/specs/SPEC-verify-tiers-merge-gate.md (D-AC1 … D-AC5, D-AC8).
Design: doc/architecture/DESIGN-verify-tiers-merge-gate.md §D.

`scripts/verify-merge.sh` checks out the candidate commit in a fresh
`git worktree`, runs that commit's own `verify-full.sh` there, and binds the
verdict to the candidate's tree and to the machine that ran it. It never says
GREEN unless the full run was GREEN, counted executed == collected, judged
exactly the candidate's tree and names a runner.

Every case runs a COPY of the scripts inside a temp git repo, built with the
`_copy` helper of `test_verify_scripts.py`: the real `verify-full.sh` runs
`pytest tests/hooks/`, which collects this file, so running the real gate from
here would recurse without bound. The copies are COMMITTED, because the merge
gate's worktree holds only what the candidate commit holds.

Run: `python3 -m pytest tests/hooks/test_verify_merge.py -q`
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from test_verify_scripts import _FULL, _copy
from test_verify_tiers import _STUB_JUNIT, _STUB_PERMANENT, _env, _git

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MERGE = _REPO_ROOT / "scripts" / "verify-merge.sh"
_BANNER = re.compile(r"^MERGE GATE (GREEN|RED|NOT RUN)", re.M)
_WEAKER = "(local fallback — weaker: same machine and same user as the agent)"

#: A configured project: one lint step, one test step writing 3 JUnit cases, and a
#: collect command that agrees. Committed in the candidate, as a real project would.
_CONF = """\
STEPS=(
  'lint|echo lint ok'
  'tests|python3 tools/stub_junit.py 3 0 0'
)
VERIFY_TEST_STEPS="tests"
VERIFY_COLLECT_CMD='echo 3'
VERIFY_MERGE_GATE=runner
"""


def _repo(tmp_path: Path, conf: str | None = _CONF) -> Path:
    """A temp repo whose single commit carries the gate scripts and `conf`."""
    root = tmp_path / "repo"
    root.mkdir()
    _copy(root, _FULL, *_STUB_PERMANENT)
    _copy(root, _MERGE)
    (root / "tools").mkdir()
    (root / "tools" / "stub_junit.py").write_text(_STUB_JUNIT, encoding="utf-8")
    (root / ".gitignore").write_text(".verify/\n__pycache__/\n", encoding="utf-8")
    if conf is not None:
        (root / "scripts" / "verify.conf").write_text(conf, encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    return root


def _commit(root: Path, message: str = "change") -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)


def _worktrees(root: Path) -> list[str]:
    out = _git(root, "worktree", "list", "--porcelain")
    return [line for line in out.splitlines() if line.startswith("worktree ")]


def _run(root: Path, *args: str, env: dict[str, str] | None = None,
         script: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run the committed copy of the gate. Afterwards the gate's worktree must be
    gone, whatever the outcome: a leaked worktree is a leaked checkout per run."""
    full_env = {**_env(), "TMPDIR": str(root.parent), **(env or {})}
    result = subprocess.run(
        [shutil.which("bash") or "bash", str(script or root / "scripts" / "verify-merge.sh"), *args],
        cwd=root, capture_output=True, text=True, timeout=120, check=False, env=full_env,
    )
    if (root / ".git").exists():
        assert len(_worktrees(root)) == 1, "the merge gate left a worktree behind:\n" + "\n".join(_worktrees(root))
    return result


def _banners(out: str) -> list[str]:
    return [line for line in out.splitlines() if _BANNER.match(line)]


def _last(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout.rstrip("\n").splitlines()[-1]


def _head(root: Path) -> tuple[str, str]:
    return _git(root, "rev-parse", "HEAD"), _git(root, "rev-parse", "HEAD^{tree}")


def _merge_record(root: Path, sha: str) -> dict:
    return json.loads((root / ".verify" / "merge" / f"{sha}.json").read_text(encoding="utf-8"))


# ---- D-AC1: a clean candidate, counts configured, a named runner ------------------


def test_green_runs_in_a_fresh_worktree_and_binds_tree_and_runner(tmp_path: Path) -> None:
    root = _repo(tmp_path, _CONF.replace("STEPS=(", "STEPS=(\n  'where|git rev-parse --show-toplevel'"))
    sha, tree = _head(root)

    result = _run(root, "HEAD", env={"VERIFY_RUNNER_ID": "runner-7"})

    assert result.returncode == 0, result.stdout + result.stderr
    assert _last(result) == f"MERGE GATE GREEN — tree {tree} — runner runner-7"
    assert len(_banners(result.stdout)) == 1
    record = _merge_record(root, sha)
    assert record["tier"] == "merge"
    assert record["tree"]["before"] == tree
    assert record["runner"] == {"id": "runner-7", "kind": "runner"}
    assert record["full_record"]["runner"]["id"] == "runner-7"
    # verify-full ran somewhere other than the caller's tree, and that place is gone.
    where = re.search(r"where\s+\(\d+s\) (\S+)", result.stdout)
    assert where, result.stdout
    ran_in = Path(where.group(1))
    assert ran_in.resolve() != root.resolve()
    assert not ran_in.exists()


# ---- D-AC2: exactly one banner line, with the right exit code ----------------------


@pytest.mark.parametrize(
    ("conf", "line", "code"),
    [
        (_CONF.replace("'lint|echo lint ok'", "'lint|echo lint broke; exit 1'"),
         "MERGE GATE RED", 1),
        (_CONF.replace("VERIFY_COLLECT_CMD='echo 3'\n", ""),
         "MERGE GATE NOT RUN — executed == collected is not configured", 3),
        (_CONF.replace("VERIFY_MERGE_GATE=runner", "VERIFY_MERGE_GATE=none"),
         "MERGE GATE NOT RUN — no runner and no local fallback configured", 3),
    ],
    ids=["failing-step", "counts-not-configured", "mode-none"],
)
def test_each_outcome_prints_exactly_one_banner(tmp_path: Path, conf: str, line: str, code: int) -> None:
    root = _repo(tmp_path, conf)
    result = _run(root, env={"VERIFY_RUNNER_ID": "runner-7"})
    assert result.returncode == code, result.stdout + result.stderr
    assert len(_banners(result.stdout)) == 1, result.stdout
    assert _last(result).startswith(line), result.stdout


def test_no_conf_and_no_mode_is_not_run(tmp_path: Path) -> None:
    root = _repo(tmp_path, conf=None)
    result = _run(root, env={"VERIFY_RUNNER_ID": "runner-7"})
    assert result.returncode == 3
    assert _last(result) == "MERGE GATE NOT RUN — no runner and no local fallback configured"


def test_an_inner_line_that_says_merge_gate_green_is_not_a_second_banner(tmp_path: Path) -> None:
    """A failing step's output is printed unindented by verify-full; relayed raw,
    a line `MERGE GATE GREEN` in it would be a banner a reader could paste."""
    root = _repo(tmp_path, _CONF.replace("'lint|echo lint ok'", "'lint|echo MERGE GATE GREEN; exit 1'"))
    result = _run(root, env={"VERIFY_RUNNER_ID": "runner-7"})
    assert result.returncode == 1
    assert _banners(result.stdout) == [_last(result)]
    assert _last(result).startswith("MERGE GATE RED")


def test_counts_set_but_no_test_step_named_is_not_run_although_full_is_green(tmp_path: Path) -> None:
    """The fake-green path: VERIFY_COLLECT_CMD set, VERIFY_TEST_STEPS empty. The
    full tier keeps GREEN with `counts: not configured` (R12); the merge gate refuses."""
    conf = _CONF.replace('VERIFY_TEST_STEPS="tests"\n', "").replace(
        "python3 tools/stub_junit.py 3 0 0", "echo 3 passed")
    root = _repo(tmp_path, conf)
    result = _run(root, env={"VERIFY_RUNNER_ID": "runner-7"})
    assert "EXIT GATE GREEN" in result.stdout
    assert result.returncode == 3
    assert _last(result) == "MERGE GATE NOT RUN — executed == collected is not configured"


def test_a_count_mismatch_is_red(tmp_path: Path) -> None:
    root = _repo(tmp_path, _CONF.replace("echo 3", "echo 4"))
    result = _run(root, env={"VERIFY_RUNNER_ID": "runner-7"})
    assert result.returncode == 1
    assert _last(result).startswith("MERGE GATE RED")


def test_unconfigured_template_steps_are_never_green(tmp_path: Path) -> None:
    """This repo's own state: the three TODO steps unfilled. verify-full is
    INCOMPLETE, so the merge gate has nothing to call GREEN."""
    conf = "VERIFY_TEST_STEPS=\nVERIFY_COLLECT_CMD='echo 3'\nVERIFY_MERGE_GATE=local-fallback\n"
    root = _repo(tmp_path, conf)
    result = _run(root)
    assert "EXIT GATE INCOMPLETE" in result.stdout
    assert result.returncode == 3
    assert _last(result).startswith("MERGE GATE NOT RUN — verify-full was INCOMPLETE")
    assert "GREEN" not in "\n".join(_banners(result.stdout))


def test_an_unknown_mode_is_not_run(tmp_path: Path) -> None:
    root = _repo(tmp_path, _CONF.replace("VERIFY_MERGE_GATE=runner", "VERIFY_MERGE_GATE=Runner"))
    result = _run(root, env={"VERIFY_RUNNER_ID": "runner-7"})
    assert result.returncode == 3
    assert _last(result).startswith("MERGE GATE NOT RUN — unknown VERIFY_MERGE_GATE=Runner")


def test_a_conf_with_a_syntax_error_is_not_run(tmp_path: Path) -> None:
    root = _repo(tmp_path, _CONF + "if then\n")
    result = _run(root, env={"VERIFY_RUNNER_ID": "runner-7"})
    assert result.returncode == 3
    assert _last(result).startswith("MERGE GATE NOT RUN — scripts/verify.conf in")


def test_a_ref_that_names_no_commit_is_not_run(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    result = _run(root, "no-such-branch", env={"VERIFY_RUNNER_ID": "runner-7"})
    assert result.returncode == 3
    assert _last(result) == "MERGE GATE NOT RUN — no-such-branch does not name a commit"


# ---- D-AC3: --check refuses a record for another tree, or with no runner ----------


def _green_record(tmp_path: Path) -> tuple[Path, Path, str]:
    root = _repo(tmp_path)
    sha, tree = _head(root)
    result = _run(root, env={"VERIFY_RUNNER_ID": "runner-7"})
    assert result.returncode == 0, result.stdout
    return root, root / ".verify" / "merge" / f"{sha}.json", tree


def test_check_accepts_the_record_for_the_candidates_tree(tmp_path: Path) -> None:
    root, record, tree = _green_record(tmp_path)
    result = _run(root, "--check", str(record), "HEAD")
    assert result.returncode == 0, result.stdout + result.stderr
    assert _last(result) == f"MERGE GATE GREEN — tree {tree} — runner runner-7"


def test_check_refuses_a_record_for_another_tree(tmp_path: Path) -> None:
    """The planted case: a GREEN record reused for a candidate whose tree differs."""
    root, record, old_tree = _green_record(tmp_path)
    (root / "new.txt").write_text("changed\n", encoding="utf-8")
    _commit(root)
    _, new_tree = _head(root)
    result = _run(root, "--check", str(record), "HEAD")
    assert result.returncode == 3
    assert _last(result) == f"MERGE GATE NOT RUN — record is for tree {old_tree}, candidate is tree {new_tree}"


@pytest.mark.parametrize(
    "runner",
    [None, {"kind": "runner"}, {"id": "  ", "kind": "runner"}, {"id": "local:abc", "kind": "local"}],
    ids=["no-runner-key", "no-id", "blank-id", "agent-local-run"],
)
def test_check_refuses_a_record_that_names_no_runner(tmp_path: Path, runner: dict | None) -> None:
    root, record, _ = _green_record(tmp_path)
    data = json.loads(record.read_text(encoding="utf-8"))
    if runner is None:
        del data["runner"]
    else:
        data["runner"] = runner
    planted = tmp_path / "planted.json"
    planted.write_text(json.dumps(data), encoding="utf-8")
    result = _run(root, "--check", str(planted), "HEAD")
    assert result.returncode == 3
    assert _last(result).startswith("MERGE GATE NOT RUN — record names no runner")


@pytest.mark.parametrize("tier", ["handoff", "fast"])
def test_check_refuses_a_record_that_is_not_a_full_run(tmp_path: Path, tier: str) -> None:
    root, record, _ = _green_record(tmp_path)
    data = json.loads(record.read_text(encoding="utf-8"))
    data["tier"] = tier
    planted = tmp_path / "planted.json"
    planted.write_text(json.dumps(data), encoding="utf-8")
    result = _run(root, "--check", str(planted), "HEAD")
    assert result.returncode == 3
    assert _last(result) == f"MERGE GATE NOT RUN — record is a {tier} run, not a full run"


def test_check_of_a_full_record_written_by_a_ci_runner_is_accepted(tmp_path: Path) -> None:
    """CI runs verify-full.sh with VERIFY_RUNNER_ID set (D-AC8); its record is
    then checked against the candidate. The inner record is that same shape."""
    root, record, tree = _green_record(tmp_path)
    inner = tmp_path / "full.json"
    inner.write_text(json.dumps(json.loads(record.read_text())["full_record"]), encoding="utf-8")
    result = _run(root, "--check", str(inner), "HEAD")
    assert result.returncode == 0, result.stdout + result.stderr
    assert _last(result) == f"MERGE GATE GREEN — tree {tree} — runner runner-7"


@pytest.mark.parametrize("content", ["", "not json", "[]", '{"tree": "x"}'], ids=["empty", "text", "list", "odd-shape"])
def test_check_of_an_unreadable_record_is_not_run_and_never_crashes(tmp_path: Path, content: str) -> None:
    root = _repo(tmp_path)
    planted = tmp_path / "planted.json"
    planted.write_text(content, encoding="utf-8")
    result = _run(root, "--check", str(planted), "HEAD")
    assert result.returncode == 3, result.stdout + result.stderr
    assert len(_banners(result.stdout)) == 1
    assert _last(result).startswith("MERGE GATE NOT RUN")
    assert "Traceback" not in result.stdout + result.stderr


def test_check_of_a_missing_record_is_not_run(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    result = _run(root, "--check", str(tmp_path / "absent.json"), "HEAD")
    assert result.returncode == 3
    assert _last(result).startswith("MERGE GATE NOT RUN — record")


def test_check_of_a_red_record_is_red(tmp_path: Path) -> None:
    root, record, _ = _green_record(tmp_path)
    data = json.loads(record.read_text(encoding="utf-8"))
    data["verdict"] = "RED"
    planted = tmp_path / "planted.json"
    planted.write_text(json.dumps(data), encoding="utf-8")
    result = _run(root, "--check", str(planted), "HEAD")
    assert result.returncode == 1
    assert _last(result).startswith("MERGE GATE RED")


def test_check_of_a_record_whose_tree_changed_during_its_run_is_red(tmp_path: Path) -> None:
    root, record, _ = _green_record(tmp_path)
    data = json.loads(record.read_text(encoding="utf-8"))
    data["tree"]["after"] = "0" * 40
    planted = tmp_path / "planted.json"
    planted.write_text(json.dumps(data), encoding="utf-8")
    result = _run(root, "--check", str(planted), "HEAD")
    assert result.returncode == 1
    assert "tree changed during the run" in _last(result)


# ---- D-AC4: the local fallback is labelled weaker ----------------------------------


def test_local_fallback_without_a_runner_id_is_labelled_weaker(tmp_path: Path) -> None:
    root = _repo(tmp_path, _CONF.replace("VERIFY_MERGE_GATE=runner", "VERIFY_MERGE_GATE=local-fallback"))
    sha, tree = _head(root)
    result = _run(root)
    assert result.returncode == 0, result.stdout + result.stderr
    assert _last(result).startswith(f"MERGE GATE GREEN — tree {tree} — runner local:")
    assert _last(result).endswith(_WEAKER)
    record = _merge_record(root, sha)
    assert record["runner"]["kind"] == "local-fallback"
    assert record["runner"]["id"].startswith("local:")
    # The fallback record survives --check, still labelled weaker.
    again = _run(root, "--check", str(root / ".verify" / "merge" / f"{sha}.json"))
    assert again.returncode == 0
    assert _last(again).endswith(_WEAKER)


# ---- runner identity (hostile) ----------------------------------------------------


@pytest.mark.parametrize("runner_id", [None, "", "   "], ids=["unset", "empty", "blank"])
def test_runner_mode_without_a_runner_id_is_not_run_never_a_quiet_fallback(tmp_path: Path, runner_id: str | None) -> None:
    root = _repo(tmp_path)
    env = {} if runner_id is None else {"VERIFY_RUNNER_ID": runner_id}
    result = _run(root, env=env)
    assert result.returncode == 3
    assert _last(result) == "MERGE GATE NOT RUN — VERIFY_MERGE_GATE=runner but VERIFY_RUNNER_ID is empty"
    assert "EXIT GATE" not in result.stdout


def test_a_runner_id_written_in_the_conf_is_refused(tmp_path: Path) -> None:
    """The conf is in the repo, which the agent edits; only the runner's own
    environment may name the runner."""
    root = _repo(tmp_path, _CONF + "VERIFY_RUNNER_ID=ci-runner\n")
    result = _run(root)
    assert result.returncode == 3
    assert _last(result).startswith("MERGE GATE NOT RUN — scripts/verify.conf sets VERIFY_RUNNER_ID")


# ---- D-AC5 and the caller's tree (hostile) -----------------------------------------


def _snapshot(root: Path) -> dict[str, bytes]:
    files = {}
    for path in root.rglob("*"):
        rel = path.relative_to(root).as_posix()
        if path.is_file() and not rel.startswith((".git/", ".verify/")):
            files[rel] = path.read_bytes()
    return files


def test_a_dirty_caller_tree_is_judged_as_committed_and_left_untouched(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    sha, tree = _head(root)
    (root / "tools" / "stub_junit.py").write_text("raise SystemExit(1)\n", encoding="utf-8")  # modified
    (root / "untracked.txt").write_text("loose\n", encoding="utf-8")  # untracked
    (root / "staged.txt").write_text("staged\n", encoding="utf-8")
    _git(root, "add", "staged.txt")  # staged
    status_before = _git(root, "status", "--porcelain")
    files_before = _snapshot(root)

    result = _run(root, env={"VERIFY_RUNNER_ID": "runner-7"})

    assert result.returncode == 0, result.stdout + result.stderr
    assert _last(result) == f"MERGE GATE GREEN — tree {tree} — runner runner-7"
    assert _merge_record(root, sha)["tree"]["before"] == tree
    # Only the gate's own output directory (.verify/, git-ignored) may change.
    assert _git(root, "status", "--porcelain") == status_before
    assert _snapshot(root) == files_before


def test_a_dirty_caller_conf_does_not_leak_into_the_run(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "scripts" / "verify.conf").write_text(
        _CONF.replace("python3 tools/stub_junit.py 3 0 0", "true").replace("VERIFY_TEST_STEPS=\"tests\"\n", ""),
        encoding="utf-8")
    result = _run(root, env={"VERIFY_RUNNER_ID": "runner-7"})
    assert result.returncode == 0, result.stdout
    assert "counts: reported 3 of 3 collected" in result.stdout


def test_head_moving_during_the_run_does_not_move_the_verdict(tmp_path: Path) -> None:
    move = (
        "'move|echo moved > \"$CALLER_ROOT/moved.txt\""
        " && git -C \"$CALLER_ROOT\" add moved.txt"
        " && git -C \"$CALLER_ROOT\" -c user.name=t -c user.email=t@example.invalid commit -q -m moved'"
    )
    root = _repo(tmp_path, _CONF.replace("STEPS=(", "STEPS=(\n  " + move))
    sha, tree = _head(root)

    result = _run(root, "HEAD", env={"VERIFY_RUNNER_ID": "runner-7", "CALLER_ROOT": str(root)})

    new_sha, new_tree = _head(root)
    assert new_sha != sha and new_tree != tree, "the step did not move HEAD; the case proves nothing"
    assert result.returncode == 0, result.stdout + result.stderr
    assert _last(result) == f"MERGE GATE GREEN — tree {tree} — runner runner-7"
    assert f"HEAD now points at {new_sha}" in result.stdout
    assert (root / ".verify" / "merge" / f"{sha}.json").is_file()
    assert not (root / ".verify" / "merge" / f"{new_sha}.json").exists()


def test_a_detached_caller_head_is_judged_normally(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _git(root, "checkout", "-q", "--detach")
    _, tree = _head(root)
    result = _run(root, env={"VERIFY_RUNNER_ID": "runner-7"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert _last(result) == f"MERGE GATE GREEN — tree {tree} — runner runner-7"


# ---- verify-full crashing (hostile) ----------------------------------------------


def test_a_missing_recorder_is_red_not_green(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "scripts" / "verify_record.py").unlink()
    _commit(root)
    result = _run(root, env={"VERIFY_RUNNER_ID": "runner-7"})
    assert result.returncode == 1
    assert _last(result).startswith("MERGE GATE RED — verify-full.sh exited 1 and wrote no readable record")


@pytest.mark.parametrize(
    ("body", "rc"),
    [("exit 0\n", 0), ("kill -KILL $$\n", 137)],
    ids=["exits-0-without-a-record", "killed"],
)
def test_a_verify_full_that_dies_without_a_record_is_red(tmp_path: Path, body: str, rc: int) -> None:
    root = _repo(tmp_path)
    (root / "scripts" / "verify-full.sh").write_text("#!/usr/bin/env bash\n" + body, encoding="utf-8")
    _commit(root)
    result = _run(root, env={"VERIFY_RUNNER_ID": "runner-7"})
    assert result.returncode == 1
    assert _last(result).startswith(f"MERGE GATE RED — verify-full.sh exited {rc} and wrote no readable record")


def test_a_green_record_with_a_non_zero_exit_is_red(tmp_path: Path) -> None:
    """verify-full wrote a GREEN record, then its process failed: the exit code wins."""
    root = _repo(tmp_path)
    (root / "scripts" / "verify-full.sh").rename(root / "scripts" / "verify-full-inner.sh")
    (root / "scripts" / "verify-full.sh").write_text(
        "#!/usr/bin/env bash\nbash \"$(dirname \"$0\")/verify-full-inner.sh\"\nexit 1\n", encoding="utf-8")
    _commit(root)
    result = _run(root, env={"VERIFY_RUNNER_ID": "runner-7"})
    assert "EXIT GATE GREEN" in result.stdout
    assert result.returncode == 1
    assert _last(result).startswith("MERGE GATE RED — verify-full.sh exited 1 — tree")


def test_a_record_line_pointing_outside_the_run_is_not_trusted(tmp_path: Path) -> None:
    """A candidate whose verify-full prints `record:` at a GREEN record from
    somewhere else (another tree's run) must not borrow that record's verdict."""
    (tmp_path / "other").mkdir()
    _, foreign, _ = _green_record(tmp_path / "other")
    root = _repo(tmp_path)
    (root / "scripts" / "verify-full.sh").write_text(
        f"#!/usr/bin/env bash\necho 'EXIT GATE GREEN.'\necho 'record: {foreign}'\n", encoding="utf-8")
    _commit(root)
    result = _run(root, env={"VERIFY_RUNNER_ID": "runner-7"})
    assert result.returncode == 1
    assert _last(result).startswith("MERGE GATE RED — verify-full.sh exited 0 and wrote no readable record")


# ---- no git (hostile) ----------------------------------------------------------


def test_outside_a_git_work_tree_is_not_run(tmp_path: Path) -> None:
    root = tmp_path / "plain"
    root.mkdir()
    _copy(root, _MERGE)
    result = _run(root)
    assert result.returncode == 3
    assert _last(result) == "MERGE GATE NOT RUN — not inside a git work tree"


def test_without_git_on_the_path_is_not_run(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("dirname",):
        (bin_dir / tool).symlink_to(shutil.which(tool))
    result = _run(root, env={"PATH": str(bin_dir)}, script=root / "scripts" / "verify-merge.sh")
    assert result.returncode == 3
    assert _last(result) == "MERGE GATE NOT RUN — git is not available"


# ---- D-AC8: the CI examples bind the gate-2 run to the runner -----------------------


def _block(text: str, start: str, end: str) -> str:
    i = text.index(start)
    j = text.find(end, i + len(start))
    return text[i:] if j == -1 else text[i:j]


def test_both_ci_examples_set_the_runner_id_on_the_gate_2_step() -> None:
    gh = (_REPO_ROOT / "ci-examples" / "github-actions.yml").read_text(encoding="utf-8")
    ado = (_REPO_ROOT / "ci-examples" / "azure-pipelines.yml").read_text(encoding="utf-8")
    assert "VERIFY_RUNNER_ID:" in _block(gh, "- name: ประตูออก", "- name:")
    assert "VERIFY_RUNNER_ID:" in _block(ado, "- script: ./scripts/verify-full.sh", "- script:")


def test_the_example_conf_and_setup_document_runner_fallback_and_none() -> None:
    conf = (_REPO_ROOT / "scripts" / "verify.conf.example").read_text(encoding="utf-8")
    setup = (_REPO_ROOT / "doc" / "framework" / "SETUP.md").read_text(encoding="utf-8")
    assert "# VERIFY_MERGE_GATE=" in conf
    for text in (conf, setup):
        for mode in ("runner", "local-fallback", "none"):
            assert f"VERIFY_MERGE_GATE={mode}" in text, mode
    assert "scripts/verify-merge.sh" in setup
    assert "nohup scripts/verify-merge.sh" in setup
