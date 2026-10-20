"""Increment B — the handoff tier: a machine chooses the tests from the diff.

Spec: doc/specs/SPEC-verify-tiers-merge-gate.md (B-AC1 … B-AC12), as amended by
doc/specs/SPEC-verify-tiers-merge-gate-am2-scanner-scope.md (the pytest-family
ban scope applies to VERIFY_SELECT_CMD). Design §B.

Every case runs a COPY of `verify-handoff.sh` and the recorder inside `tmp_path`
(the `_copy` helper of `test_verify_scripts.py`), in a throwaway git repo. The
selector is a stub that records the paths it was given and writes synthetic
JUnit into `$VERIFY_JUNIT_DIR`, so the selection, counting and verdict logic
under test are the real ones.

B-AC8 is checked on EVERY run, by `_run` itself: no stdout of this tier may
contain `GREEN` or `suite passes`, and nothing may end in a traceback.

Run: `python3 -m pytest tests/hooks/test_verify_handoff.py -q`
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from test_verify_scripts import _copy

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HANDOFF = _REPO_ROOT / "scripts" / "verify-handoff.sh"

NOT_OPTED_IN = (
    "HANDOFF TIER NOT CONFIGURED — this project has not opted in; "
    "scripts/verify-full.sh before every handoff stays in force"
)

#: The stub selector. Options are `--name=value` words from the conf; every other
#: argument is a path the wrapper passed. It records what it got into the run
#: directory (git-ignored by the recorder, so the tree does not change) and writes
#: one JUnit case per path, or `--full=N` cases for the full collected set.
_STUB_SELECT = r'''
import json, os, sys
import xml.etree.ElementTree as ET
from pathlib import Path
opts, paths = {}, []
for a in sys.argv[1:]:
    if a.startswith("--") and "=" in a:
        k, v = a[2:].split("=", 1)
        opts[k] = v
    else:
        paths.append(a)
run = Path(os.environ["VERIFY_RUN_DIR"])
name = "full-args.json" if "full" in opts else "selector-args.json"
(run / name).write_text(json.dumps(paths))
if "touch" in opts:
    with open(opts["touch"], "a") as fh:
        fh.write("# edited during the run\n")
if "crash" in opts:
    print("selector: internal error", file=sys.stderr)
    sys.exit(int(opts["crash"]))
ids = (["full_%d" % i for i in range(int(opts["full"]))] if "full" in opts else paths)
if "cases" in opts:
    ids = ids[:int(opts["cases"])]
fail = set(opts.get("fail-for", "").split(",")) - {""}
if "no-junit" not in opts:
    suite = ET.Element("testsuite", name="stub")
    for tid in ids:
        case = ET.SubElement(suite, "testcase", classname="tests.test_" + tid,
                             name="test_it", time="0.01")
        if tid in fail:
            ET.SubElement(case, "failure", message="planted regression")
    root = ET.Element("testsuites")
    root.append(suite)
    target = Path(os.environ["VERIFY_JUNIT_DIR"])
    target.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(str(target / "stub.xml"), encoding="utf-8")
print("%d cases" % len(ids))
sys.exit(int(opts.get("exit", "1" if fail & set(ids) else "0")))
'''

_BASE_CONF = {
    "VERIFY_HANDOFF_TIER": "on",
    "VERIFY_BASE_REF": "base",
    "VERIFY_SELECT_CMD": "python3 scripts/stub_select.py",
    "VERIFY_FULL_TEST_CMD": "python3 scripts/stub_select.py --full=5",
    "VERIFY_COLLECT_CMD": "echo 5",
    "VERIFY_UNTRACKED_INPUTS": "doc/**",
}


def _env() -> dict[str, str]:
    """No GIT_* (a git hook's GIT_DIR would aim every call at the real repo) and
    no VERIFY_* (this file runs inside verify-full, whose run dir must not leak)."""
    return {k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "VERIFY_"))}


def _git(root: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
         "-c", "commit.gpgsign=false", *args],
        cwd=root, capture_output=True, text=True, check=True, env=_env(),
    )
    return out.stdout.strip()


def _conf_text(**overrides: str | None) -> str:
    conf = dict(_BASE_CONF)
    conf.update(overrides)
    return "".join("%s='%s'\n" % (k, v) for k, v in conf.items() if v is not None)


def _repo(tmp_path: Path, conf: str | None = None, *, changes: bool = True,
          extra: dict[str, str] | None = None) -> Path:
    """The B-AC1 tree: base commit (branch `base`), then `a.py` changed in a
    commit, `b.py` modified but uncommitted, `c.py` untracked. `d.py`, `src/e.py`
    and `doc/readme.md` are committed at the base and left alone. No .gitignore,
    on purpose: the tier's own `.verify/` must stay out of the selection."""
    probe = _copy(tmp_path, _HANDOFF)
    (tmp_path / "scripts" / "stub_select.py").write_text(_STUB_SELECT, encoding="utf-8")
    (tmp_path / "scripts" / "verify.conf").write_text(
        _conf_text() if conf is None else conf, encoding="utf-8")
    files = {n: "x = 1\n" for n in ("a.py", "b.py", "d.py", "src/e.py", "doc/readme.md")}
    files.update(extra or {})
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text, encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "base")
    _git(tmp_path, "branch", "base")
    if changes:
        (tmp_path / "a.py").write_text("x = 2\n", encoding="utf-8")
        _git(tmp_path, "commit", "-q", "-am", "change a")
        (tmp_path / "b.py").write_text("x = 3\n", encoding="utf-8")
        (tmp_path / "c.py").write_text("x = 4\n", encoding="utf-8")
    return probe


def _run(probe: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["bash", str(probe), *args], cwd=cwd or probe.parent.parent,
        capture_output=True, text=True, timeout=120, check=False, env=_env(),
    )
    # B-AC8, on every run of every case.
    assert "GREEN" not in result.stdout, result.stdout
    assert "suite passes" not in result.stdout, result.stdout
    # Hostile inputs: never a crash.
    assert "Traceback" not in result.stdout + result.stderr, result.stdout + result.stderr
    return result


def _last(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout.rstrip("\n").splitlines()[-1]


def _run_dir(tmp_path: Path, result: subprocess.CompletedProcess[str]) -> Path:
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("record: ")]
    assert len(lines) == 1, result.stdout
    return (tmp_path / lines[0][len("record: "):]).parent


def _selector_args(tmp_path: Path, result: subprocess.CompletedProcess[str]) -> list[str] | None:
    path = _run_dir(tmp_path, result) / "selector-args.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _full_ran(tmp_path: Path, result: subprocess.CompletedProcess[str]) -> bool:
    return (_run_dir(tmp_path, result) / "full-args.json").is_file()


def _record(tmp_path: Path, result: subprocess.CompletedProcess[str]) -> dict:
    return json.loads((_run_dir(tmp_path, result) / "record.json").read_text(encoding="utf-8"))


def _nothing_ran(tmp_path: Path) -> bool:
    runs = tmp_path / ".verify"
    return not any(p.name in ("selector-args.json", "full-args.json") for p in runs.rglob("*")) \
        if runs.exists() else True


# ---------------------------------------------------------------------------
# B-AC1 … B-AC3 — the selection is the diff, plus whatever the agent names
# ---------------------------------------------------------------------------


def test_b1_the_selector_receives_exactly_the_diff(tmp_path: Path) -> None:
    probe = _repo(tmp_path)

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    assert sorted(_selector_args(tmp_path, result)) == ["a.py", "b.py", "c.py"]
    assert not _full_ran(tmp_path, result)
    assert _last(result) == "HANDOFF TIER — ran 3 of 5 (selected by machine from the diff against base)"


def test_b2_paths_left_out_by_the_agent_are_still_selected_and_named(tmp_path: Path) -> None:
    probe = _repo(tmp_path)

    result = _run(probe, "a.py")

    assert result.returncode == 0, result.stdout + result.stderr
    assert sorted(_selector_args(tmp_path, result)) == ["a.py", "b.py", "c.py"]
    assert "touched by the diff but not named by you: b.py c.py" in result.stdout.splitlines()


def test_b2_no_touched_but_not_named_line_when_nothing_is_named(tmp_path: Path) -> None:
    probe = _repo(tmp_path)

    result = _run(probe)

    assert "not named by you" not in result.stdout


def test_b3_a_named_path_adds_to_the_selection_never_removes(tmp_path: Path) -> None:
    probe = _repo(tmp_path)

    result = _run(probe, "d.py")

    assert result.returncode == 0, result.stdout + result.stderr
    assert sorted(_selector_args(tmp_path, result)) == ["a.py", "b.py", "c.py", "d.py"]
    assert "named by you but not touched by the diff: d.py" in result.stdout.splitlines()
    assert _last(result) == "HANDOFF TIER — ran 4 of 5 (selected by machine from the diff against base)"


def test_b3_a_named_path_is_read_from_the_callers_directory(tmp_path: Path) -> None:
    """Named from inside `src/`, `e.py` means `src/e.py` — the tier changes to the
    repo root, so a path taken literally there would name a file that is not there."""
    probe = _repo(tmp_path)

    result = _run(probe, "e.py", cwd=tmp_path / "src")

    assert sorted(_selector_args(tmp_path, result)) == ["a.py", "b.py", "c.py", "src/e.py"]
    assert "named by you but not touched by the diff: src/e.py" in result.stdout.splitlines()


def test_b3_spelling_variants_of_a_touched_path_are_the_same_path(tmp_path: Path) -> None:
    probe = _repo(tmp_path)

    result = _run(probe, "./a.py", str(tmp_path / "b.py"), "c.py")

    assert sorted(_selector_args(tmp_path, result)) == ["a.py", "b.py", "c.py"]
    assert "not touched by the diff" not in result.stdout
    assert "not named by you" not in result.stdout


def test_b3_a_named_directory_covers_the_touched_paths_under_it(tmp_path: Path) -> None:
    probe = _repo(tmp_path)
    (tmp_path / "src" / "e.py").write_text("x = 9\n", encoding="utf-8")

    result = _run(probe, "src", "a.py", "b.py", "c.py")

    assert sorted(_selector_args(tmp_path, result)) == ["a.py", "b.py", "c.py", "src", "src/e.py"]
    assert "not named by you" not in result.stdout


# ---------------------------------------------------------------------------
# B-AC4, B-AC5 — inputs the selector cannot track force the full set
# ---------------------------------------------------------------------------


def test_b4_a_declared_untracked_input_forces_the_full_set(tmp_path: Path) -> None:
    probe = _repo(tmp_path)
    (tmp_path / "doc" / "x.md").write_text("new\n", encoding="utf-8")

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _full_ran(tmp_path, result)
    assert _selector_args(tmp_path, result) is None
    assert "full collected set — declared untracked input changed: doc/x.md" in result.stdout
    assert _last(result) == (
        "HANDOFF TIER — ran 5 of 5 (full collected set — declared untracked input changed: doc/x.md)")


def test_b4_a_diff_of_only_non_code_inputs_forces_the_full_set(tmp_path: Path) -> None:
    probe = _repo(tmp_path, changes=False)
    (tmp_path / "doc" / "readme.md").write_text("changed\n", encoding="utf-8")

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _full_ran(tmp_path, result) and _selector_args(tmp_path, result) is None
    assert "declared untracked input changed: doc/readme.md" in _last(result)


@pytest.mark.parametrize(
    ("glob", "changed"),
    [
        ("doc/**", "doc/deep/er/x.md"),       # fnmatch's * crosses '/'
        ("**/*.json", "settings.json"),       # ** also matches zero directories
        ("**/*.json", "conf/sub/settings.json"),
        ("doc/", "doc/x.md"),                  # a directory, written with its slash
        ("doc", "doc/x.md"),                   # ... or without
        ("*.yaml doc/**", "ci.yaml"),          # space-separated globs
    ],
)
def test_b4_glob_shapes_match_what_a_reader_would_expect(
        tmp_path: Path, glob: str, changed: str) -> None:
    probe = _repo(tmp_path, _conf_text(VERIFY_UNTRACKED_INPUTS=glob), changes=False)
    (tmp_path / changed).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / changed).write_text("x\n", encoding="utf-8")

    result = _run(probe)

    assert _full_ran(tmp_path, result), result.stdout
    assert "declared untracked input changed: %s" % changed in _last(result)


def test_b4_a_glob_is_not_expanded_against_the_disk(tmp_path: Path) -> None:
    """`doc/**` must reach the matcher as written, not as the files bash finds."""
    probe = _repo(tmp_path, _conf_text(VERIFY_UNTRACKED_INPUTS="*.md"))

    result = _run(probe)

    assert _selector_args(tmp_path, result) is not None, result.stdout


def test_b5_no_declared_untracked_inputs_means_the_full_set_every_time(tmp_path: Path) -> None:
    probe = _repo(tmp_path, _conf_text(VERIFY_UNTRACKED_INPUTS=""))

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _full_ran(tmp_path, result) and _selector_args(tmp_path, result) is None
    assert _last(result) == "HANDOFF TIER — ran 5 of 5 (full collected set — no untracked inputs declared)"


def test_b5_an_unset_untracked_inputs_is_the_same_as_empty(tmp_path: Path) -> None:
    probe = _repo(tmp_path, _conf_text(VERIFY_UNTRACKED_INPUTS=None))

    result = _run(probe)

    assert _last(result).endswith("(full collected set — no untracked inputs declared)")


def test_b5_the_full_set_reporting_fewer_than_collected_is_red(tmp_path: Path) -> None:
    probe = _repo(tmp_path, _conf_text(
        VERIFY_UNTRACKED_INPUTS="", VERIFY_FULL_TEST_CMD="python3 scripts/stub_select.py --full=4"))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert "reported 4 of 5 collected" in result.stdout
    assert _last(result).startswith("HANDOFF TIER RED — ran 4 of 5")


# ---------------------------------------------------------------------------
# B-AC6 — not opted in
# ---------------------------------------------------------------------------


def test_b6_no_conf_means_not_configured_and_nothing_runs(tmp_path: Path) -> None:
    probe = _repo(tmp_path)
    (tmp_path / "scripts" / "verify.conf").unlink()

    result = _run(probe)

    assert result.returncode == 3, result.stdout + result.stderr
    assert result.stdout.strip() == NOT_OPTED_IN
    assert _nothing_ran(tmp_path)

    status = _run(probe, "--status")
    assert (status.returncode, status.stdout) == (0, "not opted in\n")


@pytest.mark.parametrize("value", ["off", "", "ON", "on ", "yes", None])
def test_b6_only_the_exact_word_on_opts_in(tmp_path: Path, value: str | None) -> None:
    probe = _repo(tmp_path, _conf_text(VERIFY_HANDOFF_TIER=value))

    result = _run(probe)
    status = _run(probe, "--status")

    assert result.returncode == 3 and result.stdout.strip() == NOT_OPTED_IN
    assert _nothing_ran(tmp_path)
    assert (status.returncode, status.stdout) == (0, "not opted in\n")


def test_b6_status_says_opted_in_and_runs_nothing(tmp_path: Path) -> None:
    probe = _repo(tmp_path)

    status = _run(probe, "--status")

    assert (status.returncode, status.stdout) == (0, "opted in\n")
    assert _nothing_ran(tmp_path)


def test_b6_a_conf_that_fails_to_load_is_never_opted_in(tmp_path: Path) -> None:
    probe = _repo(tmp_path, _conf_text() + "if then fi (\n")

    status = _run(probe, "--status")
    result = _run(probe)

    assert (status.returncode, status.stdout) == (0, "not opted in\n")
    assert result.returncode == 3, result.stdout
    assert _last(result).startswith("HANDOFF TIER NOT CONFIGURED — scripts/verify.conf failed to load")
    assert _nothing_ran(tmp_path)


@pytest.mark.parametrize("missing", ["VERIFY_SELECT_CMD", "VERIFY_FULL_TEST_CMD", "VERIFY_COLLECT_CMD"])
def test_b6_an_opted_in_project_missing_a_command_is_not_configured(
        tmp_path: Path, missing: str) -> None:
    probe = _repo(tmp_path, _conf_text(**{missing: None}))

    result = _run(probe)

    assert result.returncode == 3, result.stdout
    assert _last(result) == (
        "HANDOFF TIER NOT CONFIGURED — %s is not set; "
        "scripts/verify-full.sh before every handoff stays in force" % missing)
    assert _nothing_ran(tmp_path)


def test_b6_outside_a_git_work_tree_is_not_configured(tmp_path: Path) -> None:
    probe = _repo(tmp_path)
    subprocess.run(["rm", "-rf", str(tmp_path / ".git")], check=True)

    result = _run(probe)

    assert result.returncode == 3, result.stdout
    assert _last(result) == (
        "HANDOFF TIER NOT CONFIGURED — not a git work tree; "
        "scripts/verify-full.sh before every handoff stays in force")
    assert _nothing_ran(tmp_path)


def test_b6_a_missing_recorder_is_red_not_a_skip(tmp_path: Path) -> None:
    probe = _repo(tmp_path)
    (tmp_path / "scripts" / "verify_record.py").unlink()

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert _last(result) == "HANDOFF TIER RED — recorder missing (scripts/verify_record.py)"


# ---------------------------------------------------------------------------
# B-AC7, B-AC10 — empty and red
# ---------------------------------------------------------------------------


def test_b7_a_selector_that_reports_zero_cases_verified_nothing(tmp_path: Path) -> None:
    probe = _repo(tmp_path, _conf_text(VERIFY_SELECT_CMD="python3 scripts/stub_select.py --cases=0"))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert _last(result) == "HANDOFF TIER EMPTY — ran 0 of 5; nothing was verified"


def test_b7_zero_cases_with_a_non_zero_exit_is_still_not_a_pass(tmp_path: Path) -> None:
    """pytest exits 5 when it collected nothing."""
    probe = _repo(tmp_path, _conf_text(
        VERIFY_SELECT_CMD="python3 scripts/stub_select.py --cases=0 --exit=5"))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert _last(result) == "HANDOFF TIER EMPTY — ran 0 of 5; nothing was verified"


def test_b10_a_planted_regression_in_a_selected_test_is_red(tmp_path: Path) -> None:
    """RED-FIRST (B-AC10): the stub fails the test tied to `a.py`."""
    probe = _repo(tmp_path, _conf_text(
        VERIFY_SELECT_CMD="python3 scripts/stub_select.py --fail-for=a.py"))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert "failed: tests.test_a.py::test_it" in result.stdout.splitlines()
    assert _last(result).startswith("HANDOFF TIER RED — ran 3 of 5")


def test_b10_a_failure_the_selector_exit_code_hides_is_still_red(tmp_path: Path) -> None:
    probe = _repo(tmp_path, _conf_text(
        VERIFY_SELECT_CMD="python3 scripts/stub_select.py --fail-for=a.py --exit=0"))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert "failed: tests.test_a.py::test_it" in result.stdout.splitlines()
    assert _last(result).startswith("HANDOFF TIER RED")


def test_b10_a_failure_in_the_full_set_is_red(tmp_path: Path) -> None:
    probe = _repo(tmp_path, _conf_text(
        VERIFY_UNTRACKED_INPUTS="",
        VERIFY_FULL_TEST_CMD="python3 scripts/stub_select.py --full=5 --fail-for=full_2"))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert "failed: tests.test_full_2::test_it" in result.stdout.splitlines()
    assert _last(result).startswith("HANDOFF TIER RED — ran 5 of 5")


def test_hostile_a_crashing_selector_is_red(tmp_path: Path) -> None:
    probe = _repo(tmp_path, _conf_text(VERIFY_SELECT_CMD="python3 scripts/stub_select.py --crash=3"))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert "selector exited 3" in result.stdout
    assert _last(result).startswith("HANDOFF TIER RED — ran ? of 5")


def test_hostile_a_selector_that_exits_non_zero_over_a_passing_report_is_red(
        tmp_path: Path) -> None:
    """A crash after a partial, all-passing JUnit is not a pass."""
    probe = _repo(tmp_path, _conf_text(
        VERIFY_SELECT_CMD="python3 scripts/stub_select.py --cases=1 --exit=2"))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert "selector exited 2" in result.stdout
    assert _last(result).startswith("HANDOFF TIER RED — ran 1 of 5")


def test_hostile_a_selector_that_writes_no_report_is_red(tmp_path: Path) -> None:
    probe = _repo(tmp_path, _conf_text(VERIFY_SELECT_CMD="python3 scripts/stub_select.py --no-junit=1"))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert "no JUnit report written by the selector" in result.stdout
    assert _last(result).startswith("HANDOFF TIER RED — ran ? of 5")


def test_hostile_a_full_set_that_writes_no_report_is_red_and_recorded_as_a_mismatch(
        tmp_path: Path) -> None:
    probe = _repo(tmp_path, _conf_text(
        VERIFY_UNTRACKED_INPUTS="", VERIFY_FULL_TEST_CMD="python3 scripts/stub_select.py --full=5 --no-junit=1"))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert "no JUnit report written by VERIFY_FULL_TEST_CMD" in result.stdout
    assert _last(result).startswith("HANDOFF TIER RED — ran ? of 5")
    assert _record(tmp_path, result)["count_check"] == "mismatch"


def test_hostile_a_failing_collect_command_is_red(tmp_path: Path) -> None:
    probe = _repo(tmp_path, _conf_text(VERIFY_COLLECT_CMD="echo 5; false"))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert "VERIFY_COLLECT_CMD failed (exit 1)" in result.stdout
    assert _last(result).startswith("HANDOFF TIER RED — ran 3 of ?")


def test_hostile_a_tree_edited_during_the_run_is_red(tmp_path: Path) -> None:
    probe = _repo(tmp_path, _conf_text(VERIFY_SELECT_CMD="python3 scripts/stub_select.py --touch=d.py"))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert "tree changed during the run" in result.stdout
    assert _last(result).startswith("HANDOFF TIER RED")


def test_hostile_a_failing_lint_over_the_selection_is_red(tmp_path: Path) -> None:
    probe = _repo(tmp_path, _conf_text() + "LINT=(false)\n")

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert "lint exited 1" in result.stdout
    assert _last(result).startswith("HANDOFF TIER RED")


def test_lint_gets_the_selected_paths_that_exist(tmp_path: Path) -> None:
    stub_lint = ("import json, os, sys\nfrom pathlib import Path\n"
                 "Path(os.environ['VERIFY_RUN_DIR'], 'lint-args.json')"
                 ".write_text(json.dumps(sys.argv[1:]))\n")
    probe = _repo(tmp_path, _conf_text() + "LINT=(python3 scripts/stub_lint.py)\n",
                  extra={"scripts/stub_lint.py": stub_lint})
    (tmp_path / "d.py").unlink()  # deleted: in the selection, not linted

    result = _run(probe)

    assert result.returncode == 0, result.stdout
    linted = json.loads((_run_dir(tmp_path, result) / "lint-args.json").read_text(encoding="utf-8"))
    assert sorted(linted) == ["a.py", "b.py", "c.py"]
    assert "d.py" in _selector_args(tmp_path, result)


# ---------------------------------------------------------------------------
# B-AC9 — a base that does not resolve never selects nothing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ref", ["nope", "origin/main", "-x", "base; touch pwned"])
def test_b9_a_base_that_does_not_resolve_runs_the_full_set(tmp_path: Path, ref: str) -> None:
    probe = _repo(tmp_path, _conf_text(VERIFY_BASE_REF=ref))

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _full_ran(tmp_path, result) and _selector_args(tmp_path, result) is None
    assert _last(result) == "HANDOFF TIER — ran 5 of 5 (full collected set — base %s not found)" % ref
    assert not (tmp_path / "pwned").exists()


def test_b9_an_unset_base_defaults_to_origin_main(tmp_path: Path) -> None:
    probe = _repo(tmp_path, _conf_text(VERIFY_BASE_REF=None))

    result = _run(probe)

    assert _last(result).endswith("(full collected set — base origin/main not found)")


def test_b9_a_base_with_no_common_history_runs_the_full_set(tmp_path: Path) -> None:
    probe = _repo(tmp_path, _conf_text(VERIFY_BASE_REF="orphan"))
    empty_tree = _git(tmp_path, "hash-object", "-t", "tree", "/dev/null")
    _git(tmp_path, "branch", "orphan", _git(tmp_path, "commit-tree", empty_tree, "-m", "unrelated"))

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _full_ran(tmp_path, result)
    assert _last(result).endswith("(full collected set — no common ancestor with orphan)")


def test_hostile_an_empty_diff_runs_the_full_set_never_a_bare_selector(tmp_path: Path) -> None:
    """A selector called with no paths is, for pytest, every test — labelled
    "selected by machine". So an empty selection takes the full set, said so."""
    probe = _repo(tmp_path, changes=False)

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _full_ran(tmp_path, result) and _selector_args(tmp_path, result) is None
    assert _last(result) == "HANDOFF TIER — ran 5 of 5 (full collected set — empty diff against base)"


@pytest.mark.parametrize("module", ["select", "shlex", "subprocess"])
def test_hostile_a_project_script_named_like_a_stdlib_module_does_not_break_the_tier(
        tmp_path: Path, module: str) -> None:
    """Found in the real-selector trial: a project selector saved as
    `scripts/select.py` shadowed the stdlib for the recorder, which lives in the
    same directory, and every run died in an import."""
    probe = _repo(tmp_path, extra={"scripts/%s.py" % module: "raise SystemExit('shadowed!')\n"})

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _last(result).startswith("HANDOFF TIER — ran 3 of 5")


def test_hostile_a_repo_with_no_commit_yet_runs_the_full_set(tmp_path: Path) -> None:
    probe = _copy(tmp_path, _HANDOFF)
    (tmp_path / "scripts" / "stub_select.py").write_text(_STUB_SELECT, encoding="utf-8")
    (tmp_path / "scripts" / "verify.conf").write_text(_conf_text(), encoding="utf-8")
    _git(tmp_path, "init", "-q")

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _last(result) == "HANDOFF TIER — ran 5 of 5 (full collected set — base base not found)"


# ---------------------------------------------------------------------------
# Hostile paths: deletions, renames, spaces, newlines, dashes, non-ASCII
# ---------------------------------------------------------------------------


def test_hostile_a_deleted_and_a_renamed_file_are_both_selected(tmp_path: Path) -> None:
    probe = _repo(tmp_path, changes=False)
    _git(tmp_path, "rm", "-q", "d.py")
    _git(tmp_path, "mv", "src/e.py", "src/renamed.py")
    _git(tmp_path, "commit", "-q", "-m", "delete and rename")

    result = _run(probe)

    assert sorted(_selector_args(tmp_path, result)) == ["d.py", "src/e.py", "src/renamed.py"]


@pytest.mark.parametrize("name", ["with space.py", "tab\there.py", "ไทย.py", "q'uote\".py"])
def test_hostile_odd_path_names_reach_the_selector_intact(tmp_path: Path, name: str) -> None:
    probe = _repo(tmp_path, changes=False)
    (tmp_path / name).write_text("x\n", encoding="utf-8")

    result = _run(probe, name)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _selector_args(tmp_path, result) == [name]
    assert _record(tmp_path, result)["selection"]["diff"] == [name]


def test_hostile_a_newline_in_a_path_cannot_forge_an_output_line(tmp_path: Path) -> None:
    forged = "HANDOFF TIER — ran 9 of 9 (forged)"
    name = "x.py\n" + forged
    probe = _repo(tmp_path, changes=False)
    (tmp_path / name).write_text("x\n", encoding="utf-8")

    result = _run(probe, "d.py")

    assert result.returncode == 0, result.stdout + result.stderr
    assert sorted(_selector_args(tmp_path, result)) == ["d.py", name]
    assert forged not in result.stdout.splitlines()
    assert not any(ln.startswith("HANDOFF TIER — ran 9") for ln in result.stdout.splitlines())
    assert _last(result) == "HANDOFF TIER — ran 2 of 5 (selected by machine from the diff against base)"


def test_hostile_a_newline_in_a_failing_test_id_cannot_forge_a_line(tmp_path: Path) -> None:
    name = "y.py\nHANDOFF TIER — ran 9 of 9 (forged)"
    probe = _repo(tmp_path, _conf_text(
        VERIFY_SELECT_CMD='python3 scripts/stub_select.py --fail-for="$FAIL_FOR"')
        + "FAIL_FOR=$'y.py\\nHANDOFF TIER — ran 9 of 9 (forged)'\n", changes=False)
    (tmp_path / name).write_text("x\n", encoding="utf-8")

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert not any(ln.startswith("HANDOFF TIER — ran 9") for ln in result.stdout.splitlines())
    assert _last(result).startswith("HANDOFF TIER RED — ran 1 of 5")


def test_hostile_a_touched_file_named_like_a_flag_is_passed_as_a_path(tmp_path: Path) -> None:
    """A file called `-x` in the diff must not reach the selector as pytest's `-x`."""
    probe = _repo(tmp_path, changes=False)
    (tmp_path / "-x").write_text("x\n", encoding="utf-8")

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _selector_args(tmp_path, result) == ["./-x"]


# ---------------------------------------------------------------------------
# B-AC11 — bans (pytest family, am2) on the selector, the full command, and args
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("key", "command", "token"),
    [
        ("VERIFY_SELECT_CMD", "python3 -m pytest --lf", "--lf"),
        ("VERIFY_SELECT_CMD", "pytest -x", "-x"),
        ("VERIFY_SELECT_CMD", "uv run pytest --reruns 2", "--reruns"),
        ("VERIFY_SELECT_CMD", "PYTEST_ADDOPTS=--sw pytest", "--sw"),
        ("VERIFY_FULL_TEST_CMD", "pytest -q -xq", "-xq"),
        ("VERIFY_COLLECT_CMD", "pytest --co -q --ff | tail -1", "--ff"),
    ],
)
def test_b11_a_banned_form_in_a_configured_command_is_refused(
        tmp_path: Path, key: str, command: str, token: str) -> None:
    probe = _repo(tmp_path, _conf_text(**{key: command}))

    result = _run(probe)

    assert result.returncode == 2, result.stdout + result.stderr
    assert any(ln.startswith("BANNED: %s" % token) for ln in result.stdout.splitlines()), result.stdout
    assert _nothing_ran(tmp_path)


def test_b11_an_undeclared_filter_in_the_selector_is_refused(tmp_path: Path) -> None:
    probe = _repo(tmp_path, _conf_text(VERIFY_SELECT_CMD='pytest -m "not slow"'))

    result = _run(probe)

    assert result.returncode == 2, result.stdout
    assert 'BANNED: -m "not slow" — undeclared filter' in result.stdout


def test_b11_other_programs_flags_in_the_selector_are_not_refused(tmp_path: Path) -> None:
    """am2 AC-AC8b: only pytest-family argv carries the built-in bans."""
    probe = _repo(tmp_path, _conf_text(
        VERIFY_SELECT_CMD="git log -x -1 >/dev/null 2>&1; python3 scripts/stub_select.py"))

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("arg", ["-x", "--lf", "-k", "--verbose", "-p"])
def test_b11_a_flag_passed_as_an_argument_is_refused(tmp_path: Path, arg: str) -> None:
    probe = _repo(tmp_path)

    result = _run(probe, "a.py", arg)

    assert result.returncode == 2, result.stdout + result.stderr
    assert any(ln.startswith("BANNED: %s" % arg) for ln in result.stdout.splitlines()), result.stdout
    assert _nothing_ran(tmp_path)


def test_b11_an_extra_banned_token_in_the_selector_is_refused(tmp_path: Path) -> None:
    probe = _repo(tmp_path, _conf_text(VERIFY_SELECT_CMD="jest --onlyChanged")
                  + "VERIFY_EXTRA_BANNED='--onlyChanged'\n")

    result = _run(probe)

    assert result.returncode == 2, result.stdout
    assert "BANNED: --onlyChanged — project-declared" in result.stdout


# ---------------------------------------------------------------------------
# B-AC12 — the record
# ---------------------------------------------------------------------------


def test_b12_a_handoff_run_writes_a_record_with_both_tree_hashes(tmp_path: Path) -> None:
    probe = _repo(tmp_path)

    result = _run(probe, "a.py", "d.py")

    rec = _record(tmp_path, result)
    assert rec["tier"] == "handoff"
    assert rec["tree"]["before"] and rec["tree"]["before"] == rec["tree"]["after"]
    head_tree = _git(tmp_path, "rev-parse", "HEAD^{tree}")
    assert rec["tree"]["before"] != head_tree and rec["tree"]["dirty"] is True
    assert rec["selection"] == {
        "base": "base", "diff": ["a.py", "b.py", "c.py"], "named": ["a.py", "d.py"],
        "touched_not_named": ["b.py", "c.py"], "named_not_touched": ["d.py"],
        "full_set_reason": None,
    }
    assert rec["collected"] == 5 and rec["verdict"] == "OK"
    assert [s["label"] for s in rec["steps"]] == ["select"]
    assert rec["steps"][0]["tests"]["reported"] == 4
    assert rec["runner"]["kind"] == "local"


def test_b12_the_record_line_comes_before_the_banner(tmp_path: Path) -> None:
    probe = _repo(tmp_path)

    result = _run(probe)

    lines = result.stdout.rstrip("\n").splitlines()
    assert lines[-2].startswith("record: .verify/runs/") and lines[-2].endswith("-handoff/record.json")
    assert lines[-1].startswith("HANDOFF TIER — ran")


def test_b12_a_full_set_run_records_its_reason_and_red_records_failures(tmp_path: Path) -> None:
    probe = _repo(tmp_path, _conf_text(
        VERIFY_UNTRACKED_INPUTS="",
        VERIFY_FULL_TEST_CMD="python3 scripts/stub_select.py --full=5 --fail-for=full_0"))

    result = _run(probe)

    rec = _record(tmp_path, result)
    assert rec["selection"]["full_set_reason"] == "no untracked inputs declared"
    assert rec["steps"][0]["label"] == "full"
    assert rec["failures"] == ["tests.test_full_0::test_it"]
    assert rec["verdict"] == "RED"


def test_b12_handoff_runs_never_evict_a_full_record(tmp_path: Path) -> None:
    """AM2-R5's rule for the new tier: handoff runs keep their own 20 slots."""
    probe = _repo(tmp_path)
    runs = tmp_path / ".verify" / "runs"
    full = runs / "20200101T000000Z-1"
    full.mkdir(parents=True)
    for i in range(25):
        (runs / ("20200102T0000%02dZ-1-handoff" % i)).mkdir()

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    assert full.is_dir()
    assert len([p for p in runs.iterdir() if p.name.endswith("-handoff")]) == 20
