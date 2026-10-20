"""Increment D — the merge gate: one machine full run per merge candidate.

Spec: doc/specs/SPEC-verify-tiers-merge-gate.md (D-AC1 … D-AC5, D-AC8).
Design: doc/architecture/DESIGN-verify-tiers-merge-gate.md §D.

`scripts/verify-merge.sh` checks out the candidate commit in a fresh
`git worktree`, replaces its gate code (`verify-full.sh`, `verify_record.py`,
`verify.conf`) with the base ref's copies, runs the full tier there, and binds
the verdict to the candidate's tree and to the machine that ran it. It never says
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
    # `main` by name, whatever init.defaultBranch says: it is the default base ref.
    _git(root, "init", "-q")
    _git(root, "symbolic-ref", "HEAD", "refs/heads/main")
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


# ---- the candidate never judges itself with gate code it wrote (hostile) ---------
#
# Each case puts the candidate on a branch, so `main` (the default base ref) keeps
# the honest gate code. The forgeries pair a broken suite with gate code that hides
# it: before the base's copy was used, each of them printed MERGE GATE GREEN.

_NOTE = "note: this candidate changes the gate code — judged with main's copy; review the gate diff"
_FAILING_SUITE = ("passed, failed, skipped = (int(x) for x in pos[:3])\n",
                  "passed, failed, skipped = (int(x) for x in pos[:3])\nfailed = 1\n")
_SHORT_SUITE = ("passed, failed, skipped = (int(x) for x in pos[:3])\n",
                "passed, failed, skipped = (int(x) for x in pos[:3])\npassed -= 1\n")

#: The reviewer's forgery: runs nothing, writes a GREEN full record for HEAD's tree.
_FORGED_FULL = r"""#!/usr/bin/env bash
t=$(git rev-parse HEAD^{tree}); d=.verify/runs/forged; mkdir -p $d
printf '{"tier":"full","tree":{"before":"%s","after":"%s"},"runner":{"id":"%s","kind":"runner"},"verdict":"GREEN","count_check":"ok"}' "$t" "$t" "$VERIFY_RUNNER_ID" > $d/record.json
echo "EXIT GATE GREEN."; echo "record: $d/record.json"
"""


def _candidate(root: Path) -> None:
    _git(root, "checkout", "-q", "-b", "candidate")


def _edit(path: Path, old: str, new: str) -> None:
    body = path.read_text(encoding="utf-8")
    assert body.count(old) == 1, old
    path.write_text(body.replace(old, new), encoding="utf-8")


def test_forged_candidate_verify_full(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _candidate(root)
    _edit(root / "tools" / "stub_junit.py", *_FAILING_SUITE)
    (root / "scripts" / "verify-full.sh").write_text(_FORGED_FULL, encoding="utf-8")
    _commit(root, "forge")
    result = _run(root, "HEAD", env={"VERIFY_RUNNER_ID": "r1"})
    assert result.returncode == 1, result.stdout + result.stderr
    assert _banners(result.stdout) == [_last(result)]
    assert _last(result).startswith("MERGE GATE RED"), result.stdout
    assert _NOTE in result.stdout
    assert "FAIL tests" in result.stdout  # the real suite ran, and failed


def test_forged_candidate_recorder(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _candidate(root)
    _edit(root / "tools" / "stub_junit.py", *_SHORT_SUITE)  # 2 of 3 tests reported
    _edit(root / "scripts" / "verify_record.py", "elif reported_total != collected:", "elif False:")
    _commit(root, "forge")
    result = _run(root, "HEAD", env={"VERIFY_RUNNER_ID": "r1"})
    assert result.returncode == 1, result.stdout + result.stderr
    assert _last(result).startswith("MERGE GATE RED"), result.stdout
    assert "reported 2 of 3 collected" in result.stdout
    assert _NOTE in result.stdout


def test_forged_candidate_conf(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _candidate(root)
    shutil.copy(root / "tools" / "stub_junit.py", root / "tools" / "stub_ok.py")
    _edit(root / "tools" / "stub_junit.py", *_FAILING_SUITE)
    _edit(root / "scripts" / "verify.conf", "tools/stub_junit.py", "tools/stub_ok.py")
    _commit(root, "forge")
    result = _run(root, "HEAD", env={"VERIFY_RUNNER_ID": "r1"})
    assert result.returncode == 1, result.stdout + result.stderr
    assert _last(result).startswith("MERGE GATE RED"), result.stdout
    assert _NOTE in result.stdout


def test_a_conf_the_base_lacks_is_not_taken_from_the_candidate(tmp_path: Path) -> None:
    root = _repo(tmp_path, conf=None)
    _candidate(root)
    (root / "scripts" / "verify.conf").write_text(_CONF, encoding="utf-8")
    _commit(root, "opt in")
    result = _run(root, "HEAD", env={"VERIFY_RUNNER_ID": "r1"})
    assert result.returncode == 3, result.stdout + result.stderr
    assert _last(result) == "MERGE GATE NOT RUN — no runner and no local fallback configured"


def test_a_candidate_that_deletes_verify_full_is_judged_by_the_base_copy(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _candidate(root)
    (root / "scripts" / "verify-full.sh").unlink()
    _commit(root, "delete the gate")
    _, tree = _head(root)
    result = _run(root, "HEAD", env={"VERIFY_RUNNER_ID": "r1"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert _last(result) == f"MERGE GATE GREEN — tree {tree} — runner r1"
    assert "counts: reported 3 of 3 collected" in result.stdout
    assert _NOTE in result.stdout


def test_a_legitimate_gate_change_is_green_bound_to_the_candidates_tree(tmp_path: Path) -> None:
    """The base's gate runs, so the tree it judged is not the candidate's; the
    banner, the record and --check still name the candidate's own HEAD^{tree}."""
    root = _repo(tmp_path)
    base_sha = _git(root, "rev-parse", "main")
    _candidate(root)
    with (root / "scripts" / "verify-full.sh").open("a", encoding="utf-8") as fh:
        fh.write("# an improvement to the gate\n")
    _commit(root, "improve the gate")
    sha, tree = _head(root)
    result = _run(root, "HEAD", env={"VERIFY_RUNNER_ID": "r1"})
    assert result.returncode == 0, result.stdout + result.stderr
    lines = result.stdout.splitlines()
    assert lines[-1] == f"MERGE GATE GREEN — tree {tree} — runner r1"
    assert lines.index(_NOTE) < len(lines) - 1
    record = _merge_record(root, sha)
    assert record["tree"]["before"] == record["tree"]["after"] == tree
    assert record["tree"]["judged"] != tree
    assert record["gate_code"] == {"base_ref": "main", "base_commit": base_sha,
                                   "changed_by_candidate": ["scripts/verify-full.sh"]}
    check = _run(root, "--check", f".verify/merge/{sha}.json", "HEAD")
    assert _banners(check.stdout) == [f"MERGE GATE GREEN — tree {tree} — runner r1"]


def test_an_unchanged_gate_prints_no_note(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _candidate(root)
    (root / "feature.txt").write_text("x\n", encoding="utf-8")
    _commit(root, "feature")
    sha, tree = _head(root)
    result = _run(root, "HEAD", env={"VERIFY_RUNNER_ID": "r1"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert "note:" not in result.stdout
    assert _merge_record(root, sha)["tree"]["judged"] == tree


@pytest.mark.parametrize("how", ["named-ref-missing", "no-main"])
def test_no_base_ref_is_not_run(tmp_path: Path, how: str) -> None:
    root = _repo(tmp_path)
    env = {"VERIFY_RUNNER_ID": "r1"}
    if how == "named-ref-missing":
        env["VERIFY_MERGE_BASE_REF"] = "no-such-base"
    else:
        _git(root, "branch", "-m", "main", "trunk")
    result = _run(root, "HEAD", env=env)
    assert result.returncode == 3, result.stdout + result.stderr
    assert _banners(result.stdout) == ["MERGE GATE NOT RUN — no base ref to take the gate code from"]


def test_a_named_base_ref_supplies_the_gate_code(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _git(root, "branch", "release")
    _candidate(root)
    (root / "scripts" / "verify-full.sh").write_text(_FORGED_FULL, encoding="utf-8")
    _edit(root / "tools" / "stub_junit.py", *_FAILING_SUITE)
    _commit(root, "forge")
    _git(root, "branch", "-f", "main", "candidate")  # main itself is compromised
    result = _run(root, "HEAD", env={"VERIFY_RUNNER_ID": "r1", "VERIFY_MERGE_BASE_REF": "release"})
    assert result.returncode == 1, result.stdout + result.stderr
    assert _last(result).startswith("MERGE GATE RED")
    assert "judged with release's copy" in result.stdout


def test_a_crlf_conf_puts_no_carriage_return_in_the_banner(tmp_path: Path) -> None:
    root = _repo(tmp_path, _CONF.replace("\n", "\r\n"))
    result = _run(root, "HEAD", env={"VERIFY_RUNNER_ID": "r1"})
    assert result.returncode == 3, result.stdout + result.stderr
    assert "\r" not in result.stdout
    assert _banners(result.stdout) == ["MERGE GATE NOT RUN — unknown VERIFY_MERGE_GATE=runner\\r "
                                       "(runner, local-fallback or none)"]


# ---- shadowed imports and the runner's own record (hostile) -----------------------
#
# The gate's Python must import only the standard library it was written against:
# a candidate's `scripts/fnmatch.py` (the recorder's directory) or root `json.py`
# (the judge's directory) is candidate code, and must not run with gate privileges.

#: Shadows the recorder's `import fnmatch`: forges finalize, then hands back the real module.
_SHADOW_FNMATCH = r"""
import sys as _s, os as _o, json as _j
if "finalize" in _s.argv:
    _a = _s.argv; _tb = _a[_a.index("--tree-before") + 1]; _rd = _a[_a.index("--run-dir") + 1]
    open(_o.path.join(_rd, "record.json"), "w").write(_j.dumps({"tier": "full",
        "tree": {"before": _tb, "after": _tb},
        "runner": {"id": _o.environ.get("VERIFY_RUNNER_ID", ""), "kind": "runner"},
        "verdict": "GREEN", "count_check": "ok"}))
    print("VERDICT=GREEN"); _s.stdout.flush(); _o._exit(0)
_here = _o.path.dirname(_o.path.abspath(__file__))
_s.path[:] = [p for p in _s.path if _o.path.abspath(p or ".") != _here]
del _s.modules["fnmatch"]
import importlib; _real = importlib.import_module("fnmatch"); _s.modules["fnmatch"] = _real
globals().update(_real.__dict__)
"""

#: Shadows the judge's `import json`: prints a GREEN banner and exits 0.
_SHADOW_JSON = 'import sys\nprint("MERGE GATE GREEN — tree forged — runner r1")\nsys.exit(0)\n'


def test_a_candidate_module_shadowing_the_recorders_import_is_not_green(tmp_path: Path) -> None:
    """R6: the recorder runs isolated, so `scripts/fnmatch.py` is never imported.
    The suite exits 0 but runs nothing: only the real finalize sees no JUnit."""
    root = _repo(tmp_path)
    _candidate(root)
    (root / "tools" / "stub_junit.py").write_text("print('ran nothing')\n", encoding="utf-8")
    (root / "scripts" / "fnmatch.py").write_text(_SHADOW_FNMATCH, encoding="utf-8")
    _commit(root, "shadow")
    result = _run(root, "HEAD", env={"VERIFY_RUNNER_ID": "r1"})
    assert _banners(result.stdout) == [_last(result)]
    assert "GREEN" not in _last(result), result.stdout
    assert result.returncode in (1, 3), result.stdout + result.stderr


def test_a_candidate_module_shadowing_the_judges_import_is_not_green(tmp_path: Path) -> None:
    """The judge runs isolated too, so a root `json.py` in the caller's checkout
    (the candidate's, in local mode) never prints the banner."""
    root = _repo(tmp_path)
    _candidate(root)
    _edit(root / "tools" / "stub_junit.py", *_FAILING_SUITE)
    (root / "json.py").write_text(_SHADOW_JSON, encoding="utf-8")
    _commit(root, "shadow")
    result = _run(root, "HEAD", env={"VERIFY_RUNNER_ID": "r1"})
    assert result.returncode == 1, result.stdout + result.stderr
    assert "forged" not in result.stdout
    assert _last(result).startswith("MERGE GATE RED"), result.stdout


def _runner_record(root: Path) -> str:
    """Runs the checkout's scripts/verify-full.sh as CI gate 2 would, as runner ci-7."""
    full = subprocess.run(["bash", "scripts/verify-full.sh"], cwd=root, capture_output=True,
                          text=True, timeout=120, check=False,
                          env={**_env(), "VERIFY_RUNNER_ID": "ci-7"})
    rel = [line[len("record: "):] for line in full.stdout.splitlines() if line.startswith("record: ")]
    assert rel, full.stdout + full.stderr
    return rel[-1]


def test_check_of_a_record_from_the_candidates_own_gate_code_is_not_green(tmp_path: Path) -> None:
    """R11: a runner that ran the candidate's forged verify-full wrote a GREEN
    record for the candidate's tree. --check binds a record to the tree a runner
    judges — the candidate's, with the base's gate code in it — so it is refused."""
    root = _repo(tmp_path)
    _candidate(root)
    _edit(root / "tools" / "stub_junit.py", *_FAILING_SUITE)
    (root / "scripts" / "verify-full.sh").write_text(_FORGED_FULL, encoding="utf-8")
    _commit(root, "forge")
    _, tree = _head(root)
    record = _runner_record(root)
    result = _run(root, "--check", record, "HEAD")
    assert result.returncode == 3, result.stdout + result.stderr
    assert _banners(result.stdout) == [_last(result)]
    assert _last(result).startswith(f"MERGE GATE NOT RUN — record is for tree {tree}, judged tree "), result.stdout


def test_check_of_a_runner_record_made_with_the_base_gate_code_is_green(tmp_path: Path) -> None:
    """The honest path R11's fix must keep: gate 2 takes the base's gate code into
    the checkout and runs it; --check accepts that record for the candidate."""
    root = _repo(tmp_path)
    _candidate(root)
    with (root / "scripts" / "verify-full.sh").open("a", encoding="utf-8") as fh:
        fh.write("# an improvement to the gate\n")
    _commit(root, "improve the gate")
    _, tree = _head(root)
    _git(root, "checkout", "-q", "main", "--", "scripts/verify-full.sh")
    record = _runner_record(root)
    result = _run(root, "--check", record, "HEAD")
    assert result.returncode == 0, result.stdout + result.stderr
    assert _last(result) == f"MERGE GATE GREEN — tree {tree} — runner ci-7"


def test_check_without_a_base_ref_is_not_run(tmp_path: Path) -> None:
    root, record, _ = _green_record(tmp_path)
    _git(root, "branch", "-m", "main", "trunk")
    result = _run(root, "--check", str(record), "HEAD")
    assert result.returncode == 3, result.stdout + result.stderr
    assert _banners(result.stdout) == ["MERGE GATE NOT RUN — no base ref to take the gate code from"]


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
    assert "VERIFY_RUNNER_ID:" in _block(ado, "displayName: 'ประตูออก'", "- script:")


def test_the_example_conf_and_setup_document_runner_fallback_and_none() -> None:
    conf = (_REPO_ROOT / "scripts" / "verify.conf.example").read_text(encoding="utf-8")
    setup = (_REPO_ROOT / "doc" / "framework" / "SETUP.md").read_text(encoding="utf-8")
    assert "# VERIFY_MERGE_GATE=" in conf
    for text in (conf, setup):
        for mode in ("runner", "local-fallback", "none"):
            assert f"VERIFY_MERGE_GATE={mode}" in text, mode
    assert "scripts/verify-merge.sh" in setup
    assert "nohup scripts/verify-merge.sh" in setup
