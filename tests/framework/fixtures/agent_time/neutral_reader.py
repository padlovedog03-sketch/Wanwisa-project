"""A neutral stub reader for the meter's core tests.

It implements the reader contract in `scripts/agent_time.py` over neutral JSON
files (one run per `*.json` in the source directory), so the core can be tested
without any assistant's transcript format. A file that is not valid JSON counts
as one unreadable line.
"""

from __future__ import annotations

import datetime as dt
import json
from collections import Counter
from pathlib import Path
from typing import Iterator

import agent_time


def run_from_dict(data: dict) -> agent_time.Run:
    """Build a Run from the neutral fixture shape (times in seconds from t0)."""
    t0 = dt.datetime.fromisoformat(data["t0"])
    events = []
    for raw in data["events"]:
        fields = {k: v for k, v in raw.items() if k != "t"}
        if "job_ids" in fields:
            fields["job_ids"] = tuple(fields["job_ids"])
        events.append(agent_time.Event(t=t0 + dt.timedelta(seconds=raw["t"]), **fields))
    return agent_time.Run(
        agent_type=data["agent_type"],
        events=events,
        excluded=Counter(data.get("excluded", {})),
        unreadable_lines=data.get("unreadable_lines", 0),
    )


def runs(source: Path, since: dt.datetime) -> Iterator[agent_time.Run]:
    """Yield one Run per neutral JSON file whose last event is on or after `since`."""
    for path in sorted(Path(source).glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            yield agent_time.Run("(unreadable)", [], Counter(), 1)
            continue
        run = run_from_dict(data)
        if not run.events or run.events[-1].t >= since:
            yield run
