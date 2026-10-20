"""QA regression tests for the meter's size classes (J2, R41, R22, R23, R39).

WHY THIS FILE EXISTS. The engineer's J2 tests drive probe exclusion and the
canary through the neutral stub reader, and the verdict through two literal
medians. QA attacked the same properties end to end through adapter ก's real
reader and at the edges the literal fixtures do not reach:

- a `PROBE:` marker in a real first user message (CRLF line ends), and look-alike
  markers that must NOT exclude a run;
- a canary in `cwd`, in a pathless edit's line and in an unreadable line, which
  must not reach any new output line (class headers, `size unknown` reasons,
  `acceptance:`);
- `--targets` / `--min-runs` values carrying a canary, which must not be echoed;
- every active time around the 15-minute target, whose verdict must agree with
  the median printed beside it.

doc/qa/QA-verify-tiers-J2-size-class.md records the runs.

Run: `python3 -m pytest tests/hooks/test_regression_agent_time_size_class.py -q`   (stdlib only)
"""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
import agent_time  # noqa: E402  (path must be set up first)

_READER = _REPO_ROOT / ".claude" / "meter" / "transcript_reader.py"
_CANARY = "CANARY-7f3a"
_CWD = f"/work/{_CANARY}/repo"
_TARGETS = ("--targets", "small=15,medium=25,large=50")


def _meter(source: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "scripts/agent_time.py", "--reader", str(_READER), "--dir", str(source),
         "--since", "2000-01-01", *extra],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def _user(ts: str, content: object) -> str:
    return json.dumps({"type": "user", "timestamp": ts, "cwd": _CWD, "message": {"content": content}}) + "\n"


def _edit(ts: str, tool_id: str, tool_input: object) -> str:
    message = {"id": "m-" + tool_id, "content": [{"type": "tool_use", "id": tool_id, "name": "Edit", "input": tool_input}]}
    return json.dumps({"type": "assistant", "timestamp": ts, "cwd": _CWD, "message": message}) + "\n"


def _result(ts: str, tool_id: str) -> str:
    return _user(ts, [{"type": "tool_result", "tool_use_id": tool_id, "content": "ok"}])


def _engineer(root: Path, name: str, brief: str, body: str) -> None:
    sub = root / "s" / "subagents"
    sub.mkdir(parents=True, exist_ok=True)
    (sub / f"agent-{name}.meta.json").write_text(json.dumps({"agentType": "ai-engineer"}), "utf-8")
    (sub / f"agent-{name}.jsonl").write_text(_user("2026-10-20T00:00:00.000Z", brief) + body, "utf-8")


def _one_edit(path: str) -> str:
    return _edit("2026-10-20T00:01:00.000Z", "T1", {"file_path": path}) + _result("2026-10-20T00:02:00.000Z", "T1")


def _assert_clean(result: subprocess.CompletedProcess) -> str:
    assert result.returncode == 0 and "Traceback" not in result.stderr, result.stderr.splitlines()[-1:]
    for leaked in (_CANARY, str(Path.home())):
        assert leaked not in result.stdout and leaked not in result.stderr, f"{leaked!r} printed"
    return result.stdout


# ---- R23 / J2-AC7 through the real reader -----------------------------------------


def test_regression_a_probe_brief_is_excluded_through_the_real_reader(tmp_path: Path) -> None:
    _engineer(tmp_path, "probe", "Slice: 9\r\nPROBE: dropped-test (trial probe)\r\n", _one_edit(f"{_CWD}/a.py"))
    _engineer(tmp_path, "real", "Slice: 9\r\n", _one_edit(f"{_CWD}/b.py"))
    out = _assert_clean(_meter(tmp_path, *_TARGETS))
    assert "probe runs excluded: 1" in out, out
    assert "all engineer runs n=1" in out
    assert "small  n=1" in out


@pytest.mark.parametrize(
    "brief",
    ["x PROBE: y", "x\rPROBE: y", "﻿PROBE: y", "> PROBE: y", "`PROBE: y`", "\tPROBE: y", "PROBE : y"],
    ids=["line-separator", "bare-cr", "bom", "quoted", "backticked", "tab-indented", "space-before-colon"],
)
def test_regression_a_look_alike_probe_marker_does_not_exclude_the_run(tmp_path: Path, brief: str) -> None:
    """ADR-3: only a line that starts `PROBE:` marks a probe; a look-alike must stay counted.

    Conservative on purpose: a probe that is missed shows up as a mismatch in
    F-AM3's count against the trial log, but a real run that is wrongly excluded
    leaves no trace anywhere.
    """
    _engineer(tmp_path, "r", brief, _one_edit(f"{_CWD}/a.py"))
    out = _assert_clean(_meter(tmp_path))
    assert "probe runs excluded: 0" in out and "all engineer runs n=1" in out, out


# ---- R39 / J2-AC8 through the real reader: the new lines carry no path -------------


def test_regression_no_path_reaches_a_size_line_through_the_real_reader(tmp_path: Path) -> None:
    """Canary in cwd, a relative edit, a pathless edit, a Read and an unreadable line."""
    _engineer(tmp_path, "known", "Slice: 1", _one_edit("rel/" + _CANARY + ".py"))
    pathless = _edit("2026-10-20T00:01:00.000Z", "T1", {"old_string": _CANARY}) + _result("2026-10-20T00:02:00.000Z", "T1")
    _engineer(tmp_path, "pathless", "Slice: 2", pathless)
    _engineer(tmp_path, "unreadable", "Slice: 3", _one_edit(f"{_CWD}/c.py") + "{not json " + _CANARY + "\n")
    out = _assert_clean(_meter(tmp_path, *_TARGETS, "--min-runs", "1"))
    assert "small  n=1" in out, out
    assert "size unknown: 2 (path missing: 1 · unreadable lines: 1)" in out
    assert "acceptance: NOT met (met 1 of 3 classes)" in out


@pytest.mark.parametrize(
    "bad",
    [
        ["--targets", f"small={_CANARY},medium=25,large=50"],
        ["--targets", f"{_CANARY}=15,medium=25,large=50"],
        ["--targets", _CANARY],
        ["--min-runs", _CANARY],
    ],
    ids=["target-value", "target-name", "targets-whole", "min-runs"],
)
def test_regression_a_bad_flag_value_is_not_echoed(tmp_path: Path, bad: list) -> None:
    _engineer(tmp_path, "r", "Slice: 1", _one_edit("/work/repo/a.py"))
    out = _assert_clean(_meter(tmp_path, *bad))
    assert re.fullmatch(r"agent-time: error: [^\n]+\n", out), out


# ---- R22 / J2-AC6: the verdict agrees with the printed median at every second -------


def _run_of(active_s: int) -> agent_time.Run:
    t0 = dt.datetime(2026, 10, 20, tzinfo=dt.timezone.utc)
    at = lambda s: t0 + dt.timedelta(seconds=s)  # noqa: E731
    return agent_time.Run(
        "ai-engineer",
        [
            agent_time.Event(at(0), "inbound", text="Slice: 1"),
            agent_time.Event(at(0), "model", message_id="m0"),
            agent_time.Event(at(0), "tool_call", tool_id="T", tool_kind="edit", paths=("/work/repo/a.py",)),
            agent_time.Event(at(0), "tool_result", tool_id="T"),
            agent_time.Event(at(active_s), "model", message_id="m1"),
        ],
    )


@pytest.mark.parametrize("active_s", range(880, 921))
def test_regression_the_verdict_agrees_with_the_printed_median(active_s: int) -> None:
    text = agent_time.size_report([_run_of(active_s)], {"small": 15.0, "medium": 25.0, "large": 50.0}, 1)
    line = next(x for x in text.splitlines() if x.lstrip().startswith("small "))
    match = re.search(r"median (\d+\.\d) min · (met|NOT met) \(median (\d+\.\d) [≤>] 15\)", line)
    assert match, line
    printed, verdict, compared = float(match.group(1)), match.group(2), float(match.group(3))
    assert printed == compared, line
    assert (verdict == "met") == (printed <= 15.0), line


def test_regression_zero_runs_is_never_met_even_with_min_runs_1() -> None:
    text = agent_time.size_report([_run_of(60)], {"small": 15.0, "medium": 25.0, "large": 50.0}, 1)
    assert "large  n=0  no median · not enough runs (0) — extend the trial for this class; not met" in text, text
    assert "acceptance: NOT met (met 1 of 3 classes)" in text
