"""QA regression tests for the agent-time meter with adapter ก's reader (J-AC6, J-AC7, R39).

WHY THIS FILE EXISTS. R39 says the meter "always exits 0" and "never prints
real identifiers or transcript content", and the spec's Functional Behavior
says its output never carries user identifiers. The engineer's tests prove
this for the spec's literal fixtures. QA probed odd input shapes found in or
plausible for real transcripts, and some of them crash the meter with a
traceback (exit 1). One of those tracebacks prints the absolute transcript
path, which carries the user's home directory and the J-AC6 canary file name.
Each test below is the smallest variant of an AC's own fixture that shows one
such case (doc/qa/QA-verify-tiers-J-meter.md, Defects).

The `--since` boundary tests fill a gap: no existing test pins the
inclusive midnight-UTC boundary or a non-UTC offset.

Run: `python3 -m pytest tests/hooks/test_regression_agent_time_reader.py -q`   (stdlib only)
"""

from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
import agent_time  # noqa: E402  (path must be set up first)

_READER = _REPO_ROOT / ".claude" / "meter" / "transcript_reader.py"
_FIXTURE_RUN = _REPO_ROOT / "tests" / "hooks" / "fixtures" / "transcripts" / "session-0001" / "subagents"
_CANARY = "CANARY-7f3a"


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


def _subagent_dir(root: Path) -> Path:
    sub = root / "s" / "subagents"
    sub.mkdir(parents=True)
    return sub


def _lines(*records: dict) -> str:
    return "".join(json.dumps(r) + "\n" for r in records)


def _user(ts: str, content: object = "go") -> dict:
    return {"type": "user", "timestamp": ts, "message": {"content": content}}


def _assistant(ts: str, content: object = (), message_id: str = "m") -> dict:
    return {"type": "assistant", "timestamp": ts, "message": {"id": message_id, "content": list(content)}}


def _assert_reported_cleanly(result: subprocess.CompletedProcess) -> None:
    """R39: exit 0, no traceback, and nothing the transcript or its path carried."""
    assert "Traceback" not in result.stderr, result.stderr.splitlines()[-1:]
    assert result.returncode == 0
    for leaked in (_CANARY, str(Path.home())):
        assert leaked not in result.stdout and leaked not in result.stderr, f"{leaked!r} printed"


# ---- R39 / J-AC6: an unreadable file must neither crash nor print its path ----


@pytest.mark.parametrize("unreadable", ["meta", "transcript"])
def test_regression_an_unreadable_file_neither_crashes_nor_prints_its_path(tmp_path: Path, unreadable: str) -> None:
    """The J-AC6 fixture, with one of its files unreadable (a directory where a file should be).

    A directory is used rather than chmod 000 so the case holds even when tests run as root.
    """
    sub = _subagent_dir(tmp_path)
    for path in _FIXTURE_RUN.iterdir():
        shutil.copy(path, sub / path.name)
    target = sub / (f"agent-{_CANARY}.meta.json" if unreadable == "meta" else f"agent-{_CANARY}.jsonl")
    target.unlink()
    target.mkdir()
    _assert_reported_cleanly(_meter(tmp_path, "--rework"))


# ---- R39 / J-AC7: odd but well-formed JSON must not crash the meter -------------


@pytest.mark.parametrize(
    "first_ts, last_ts",
    [("2026-10-20T00:00:00", "2026-10-20T00:00:05"), ("2026-10-20T00:00:00.000Z", "2026-10-20T00:00:05")],
    ids=["no-offset", "mixed-offset-and-none"],
)
def test_regression_a_timestamp_without_an_offset_does_not_crash(tmp_path: Path, first_ts: str, last_ts: str) -> None:
    (_subagent_dir(tmp_path) / "agent-a.jsonl").write_text(_lines(_user(first_ts), _assistant(last_ts)), "utf-8")
    _assert_reported_cleanly(_meter(tmp_path))


def test_regression_a_meta_file_that_is_not_an_object_is_an_unknown_role(tmp_path: Path) -> None:
    sub = _subagent_dir(tmp_path)
    (sub / "agent-a.meta.json").write_text("[]", "utf-8")
    (sub / "agent-a.jsonl").write_text(
        _lines(_user("2026-10-20T00:00:00.000Z"), _assistant("2026-10-20T00:00:05.000Z")), "utf-8"
    )
    result = _meter(tmp_path)
    _assert_reported_cleanly(result)
    assert "(unknown): 1 runs" in result.stdout


def test_regression_a_shell_command_that_is_not_a_string_does_not_crash(tmp_path: Path) -> None:
    call = {"type": "tool_use", "id": "T", "name": "Bash", "input": {"command": ["ls"]}}
    result_block = {"type": "tool_result", "tool_use_id": "T", "content": "x"}
    (_subagent_dir(tmp_path) / "agent-a.jsonl").write_text(
        _lines(
            _user("2026-10-20T00:00:00.000Z"),
            _assistant("2026-10-20T00:00:05.000Z", [call]),
            _user("2026-10-20T00:00:09.000Z", [result_block]),
        ),
        "utf-8",
    )
    _assert_reported_cleanly(_meter(tmp_path))


def test_regression_a_two_digit_fraction_timestamp_is_timed_not_excluded(tmp_path: Path) -> None:
    """Python 3.9's fromisoformat rejects `.50`; 3.11+ accepts it, so totals differ by version.

    Green on the suite's interpreter (3.11+); it is the version-independence the
    reader owes, and it goes red if the reader is run on 3.9.
    """
    reader = agent_time.load_reader(_READER)
    (tmp_path / "s.jsonl").write_text(_lines(_user("2026-10-20T00:00:00.50Z")), "utf-8")
    runs = list(reader.runs(tmp_path, dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)))
    assert dict(runs[0].excluded) == {}, dict(runs[0].excluded)
    assert [e.kind for e in runs[0].events] == ["inbound"]


# ---- --since boundaries (gap filler: green, and shown to bite) ------------------


@pytest.mark.parametrize(
    "last_event, kept",
    [
        ("2026-10-20T00:00:00.000Z", True),        # exactly midnight UTC: inside the window
        ("2026-10-19T23:59:59.999Z", False),       # one millisecond before: outside
        ("2026-10-19T20:00:00.000-05:00", True),   # 01:00 UTC on the 20th, written with an offset
        ("2026-10-20T06:59:59.000+07:00", False),  # 23:59:59 UTC on the 19th, written with an offset
    ],
)
def test_regression_since_is_inclusive_midnight_utc_whatever_the_offset(
    tmp_path: Path, last_event: str, kept: bool
) -> None:
    reader = agent_time.load_reader(_READER)
    (tmp_path / "s.jsonl").write_text(
        _lines(_user("2026-10-01T00:00:00.000Z"), _assistant(last_event)), "utf-8"
    )
    found = list(reader.runs(tmp_path, agent_time.parse_since("2026-10-20")))
    assert (len(found) == 1) is kept, f"{last_event}: kept={len(found) == 1}, expected {kept}"


# ---- R39: names that are not printed stay unprinted ------------------------------


def test_regression_a_canary_in_tool_names_and_ids_is_never_printed(tmp_path: Path) -> None:
    call = {"type": "tool_use", "id": f"{_CANARY}-T", "name": f"{_CANARY}-Tool", "input": {"command": _CANARY}}
    result_block = {"type": "tool_result", "tool_use_id": f"{_CANARY}-T", "content": _CANARY}
    sub = _subagent_dir(tmp_path)
    (sub / "agent-a.meta.json").write_text(json.dumps({"agentType": "qa"}), "utf-8")
    (sub / "agent-a.jsonl").write_text(
        _lines(
            _user("2026-10-20T00:00:00.000Z"),
            _assistant("2026-10-20T00:00:05.000Z", [call], message_id=f"{_CANARY}-id"),
            _user("2026-10-20T00:00:09.000Z", [result_block]),
        ),
        "utf-8",
    )
    result = _meter(tmp_path, "--rework")
    _assert_reported_cleanly(result)
    assert "qa: 1 runs" in result.stdout, "the run must actually be read"


# ---- Re-test (round 2): values printed as category labels must be labels ---------
#
# The meter prints a run's role (`agentType`) and each excluded event `type` as
# category labels. R39 allows "categories, counts and durations" only. A value that
# carries a newline is not a label: it writes its own lines into the report, so
# transcript data can forge any report line, including the M11 rework share the
# owner's acceptance rests on. A non-string role prints its str(), contents and all.


@pytest.mark.parametrize("field", ["type", "agentType"])
def test_regression_a_label_carrying_a_newline_cannot_forge_a_report_line(tmp_path: Path, field: str) -> None:
    forged = "rework share: 0 of 9 engineer runs (0%)"
    sub = _subagent_dir(tmp_path)
    records = [_user("2026-10-20T00:00:00.000Z"), _assistant("2026-10-20T00:00:05.000Z")]
    if field == "type":
        records.append({"type": f"x\n{forged}"})
    else:
        (sub / "agent-a.meta.json").write_text(json.dumps({"agentType": f"qa\n{forged}"}), "utf-8")
    (sub / "agent-a.jsonl").write_text(_lines(*records), "utf-8")
    result = _meter(tmp_path)
    _assert_reported_cleanly(result)
    assert not [line for line in result.stdout.splitlines() if line.startswith(forged)], result.stdout


def test_regression_a_role_that_is_not_a_string_is_not_printed(tmp_path: Path) -> None:
    sub = _subagent_dir(tmp_path)
    (sub / "agent-a.meta.json").write_text(json.dumps({"agentType": {"description": _CANARY}}), "utf-8")
    (sub / "agent-a.jsonl").write_text(
        _lines(_user("2026-10-20T00:00:00.000Z"), _assistant("2026-10-20T00:00:05.000Z")), "utf-8"
    )
    _assert_reported_cleanly(_meter(tmp_path))


def test_regression_a_value_the_reader_cannot_handle_reaches_the_guard_as_its_type_only(tmp_path: Path) -> None:
    """An unhashable event `type` holding the canary: exit 0, no traceback, no canary.

    It pins the guard's shape, not today's path to it: if the reader learns to count
    such a line instead, no `internal error` line appears and this still holds.
    """
    (_subagent_dir(tmp_path) / "agent-a.jsonl").write_text(
        _lines(_user("2026-10-20T00:00:00.000Z"), {"type": [_CANARY]}), "utf-8"
    )
    result = _meter(tmp_path)
    _assert_reported_cleanly(result)
    guard_lines = [line for line in result.stdout.splitlines() if "internal error" in line]
    assert all(re.fullmatch(r"agent-time: internal error: \w+", line) for line in guard_lines), guard_lines


# ---- Re-test 2: a valid line must be read whole (J-AC2, J-AC7) --------------------
#
# JSON allows U+2028, U+2029 and U+0085 raw inside a string, and real transcripts
# carry them (QA measured 14 such characters on 9 lines in 4 of 902 local files). Python's
# str.splitlines() breaks a line on each of them. That splits one valid line into
# fragments, so the meter reports unreadable lines that are not there, and the
# clock event is lost: its time silently moves to another category (ADR-2's
# failure shape). The fixture is J-AC2's own golden run, with one valid line changed.

_GOLDEN_FIXTURE = _REPO_ROOT / "tests" / "hooks" / "fixtures" / "transcripts"
_SEPARATORS = {"U+2028": " ", "U+2029": " ", "U+0085": "\x85"}


@pytest.mark.parametrize("separator", sorted(_SEPARATORS))
def test_regression_a_valid_line_carrying_a_unicode_line_separator_is_read_whole(
    tmp_path: Path, separator: str
) -> None:
    """J-AC2's golden run with one valid tool result carrying the separator: totals and unreadable count unchanged."""
    shutil.copytree(_GOLDEN_FIXTURE, tmp_path / "t")
    transcript = next((tmp_path / "t").rglob("agent-*.jsonl"))
    lines = transcript.read_text("utf-8").split("\n")
    index = next(i for i, line in enumerate(lines) if '"1 passed"' in line)
    record = json.loads(lines[index])
    record["message"]["content"][0]["content"] = f"1{_SEPARATORS[separator]}passed"
    lines[index] = json.dumps(record, ensure_ascii=False)  # raw, as the assistant writes it
    assert json.loads(lines[index]) == record, "the changed line must still be valid JSON"
    transcript.write_text("\n".join(lines), "utf-8")

    reader = agent_time.load_reader(_READER)
    (run,) = list(reader.runs(tmp_path / "t", dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)))
    totals = agent_time.categorise(run)
    got = (run.unreadable_lines, totals["model"], totals["tests:running"], totals["active"], totals["idle"])
    assert got == (1, 150, 120, 578, 600), f"(unreadable, model, tests:running, active, idle) = {got}"


# ---- Re-test 2: D5/D6 hold for every line-break and whitespace shape ---------------
#
# Green: these pin the D5/D6 fixes against shapes the round-1 newline test did not
# cover. Each was shown to go red with the matching `_label` replaced by identity.

_FORGED = "rework share: 0 of 9 engineer runs (0%)"
_ODD_LABELS = {
    "NEL": f"x\x85{_FORGED}",
    "LS": f"x {_FORGED}",
    "CR": f"x\r{_FORGED}",
    "tab": "x\ty",
    "nbsp": "x y",
    "over-long": "a" * 101,
}


def _forged_lines(text: str) -> list:
    """Lines that begin with the forged rework line, split the way `--qa-dir` parsing and editors split."""
    return [line for line in text.splitlines() if line.startswith(_FORGED)]


@pytest.mark.parametrize("label", sorted(_ODD_LABELS))
def test_regression_the_reader_never_passes_an_odd_label_through(tmp_path: Path, label: str) -> None:
    """The same odd value as a role and as an event type: both become the placeholder in the reader."""
    value = _ODD_LABELS[label]
    sub = _subagent_dir(tmp_path)
    (sub / "agent-a.meta.json").write_text(json.dumps({"agentType": value}), "utf-8")
    (sub / "agent-a.jsonl").write_text(
        _lines(_user("2026-10-20T00:00:00.000Z"), _assistant("2026-10-20T00:00:05.000Z"), {"type": value}), "utf-8"
    )
    reader = agent_time.load_reader(_READER)
    (run,) = list(reader.runs(tmp_path, dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)))
    assert run.agent_type == "(unprintable label)"
    assert dict(run.excluded) == {"(unprintable label)": 1}


@pytest.mark.parametrize("label", sorted(_ODD_LABELS))
def test_regression_the_core_never_prints_an_odd_label_from_any_reader(label: str) -> None:
    """A stub reader's run reaches only the core: its own `_label` is the last defence."""
    value = _ODD_LABELS[label]
    t0 = dt.datetime(2026, 10, 20, tzinfo=dt.timezone.utc)
    events = [
        agent_time.Event(t0, "inbound", text="go"),
        agent_time.Event(t0 + dt.timedelta(seconds=5), "model", message_id="m"),
    ]
    text = agent_time.report([agent_time.Run(value, events, Counter({value: 1}))], t0, "stub")
    assert value not in text
    assert not _forged_lines(text), _forged_lines(text)
    assert "(unprintable label): 1 runs" in text and "(unprintable label) 1" in text
