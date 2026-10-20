"""`scripts/autonomy.py` — the always-human list (SPEC-delegated-autonomy, increment B).

What is pinned here, and why each half matters:

* **B-AC1** the five framework items print, a project file can only ADD to
  them, and any attempt to remove or narrow one is a load error (exit 2). An
  always-human list that a project file could quietly shorten would be a list
  the assistant could shorten too — the file is one Write away.
* **B-AC2** the command classifier names the item for every row of the
  design's command table (§B.2) AND returns nothing for the look-alikes. A
  classifier with false positives gets its guard switched off.
* **B-AC8** artifact classification fails closed: no `Decision-class:` on a
  PRD/spec, or no rule that matches, is `AH-UNSURE`; a header field can add an
  always-human touch but never remove one a path proves.
* **B-AC9** ADAPTERS.md declares, per adapter, what is enforced and where.

Run: `python3 -m pytest tests/framework/ -q`   (stdlib + git)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "autonomy.py"
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

import autonomy  # noqa: E402  (path set up above)

_ITEMS = ("AH1", "AH2", "AH3", "AH4", "AH5")


def _project(tmp_path: Path, config: dict | None) -> Path:
    """A throwaway git repo, optionally opted in with `scripts/autonomy.json`."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, timeout=30)
    if config is not None:
        (tmp_path / "scripts").mkdir(exist_ok=True)
        (tmp_path / "scripts" / "autonomy.json").write_text(json.dumps(config), encoding="utf-8")
    return tmp_path


def _items(cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_SCRIPT), "items"],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


# --------------------------------------------------------------------------- B-AC1


def _item_block(output: str, item: str) -> str:
    """The lines printed under one item heading, up to the next heading."""
    lines = output.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(item + " "))
    block = [lines[start]]
    for line in lines[start + 1 :]:
        if line[:3] == "AH" or (line and not line.startswith(" ")):
            break
        block.append(line)
    return "\n".join(block)


def test_items_prints_the_five_framework_items_with_their_matchers(tmp_path: Path) -> None:
    result = _items(_project(tmp_path, None))
    assert result.returncode == 0, result.stderr
    for item in _ITEMS:
        assert any(line.startswith(item + " ") for line in result.stdout.splitlines()), item
    # Each item lists at least one matcher of each kind it uses.
    assert "class: business-rules" in _item_block(result.stdout, "AH1")
    assert "field: " in _item_block(result.stdout, "AH1")
    assert "class: security" in _item_block(result.stdout, "AH2")
    assert "class: personal-data" in _item_block(result.stdout, "AH2")
    assert "command: git push <remote> <protected-branch>" in _item_block(result.stdout, "AH3")
    assert "command: " in _item_block(result.stdout, "AH4")
    ah5 = _item_block(result.stdout, "AH5")
    assert "path: scripts/autonomy.json" in ah5
    assert "command: owner-only scripts/approve.sh" in ah5


def test_a_project_path_pattern_appears_under_its_item(tmp_path: Path) -> None:
    root = _project(tmp_path, {"project": "proj", "extra": {"AH1": {"paths": ["src/pricing/**"]}}})
    result = _items(root)
    assert result.returncode == 0, result.stderr
    assert "path: src/pricing/** (project)" in _item_block(result.stdout, "AH1")
    assert "src/pricing/**" not in _item_block(result.stdout, "AH2")


def test_project_data_globs_appear_under_ah3(tmp_path: Path) -> None:
    result = _items(_project(tmp_path, {"project": "proj", "data_globs": ["data/**"]}))
    assert result.returncode == 0, result.stderr
    assert "path: data/** (project)" in _item_block(result.stdout, "AH3")


@pytest.mark.parametrize(
    ("config", "item"),
    [
        ({"project": "p", "disable": ["AH3"]}, "AH3"),
        ({"project": "p", "AH2": {"classes": []}}, "AH2"),
        ({"project": "p", "extra": {"AH1": {"paths": []}}}, "AH1"),
        ({"project": "p", "protected_branches": []}, "AH3"),
    ],
    ids=["disable-key", "redefined-item-id", "empty-override", "empty-framework-list"],
)
def test_a_project_file_cannot_remove_a_framework_item(
    tmp_path: Path, config: dict, item: str
) -> None:
    """The planted case of B-AC1. Each shape is a different way to shorten
    the list; each must be a load error, never a silently smaller list."""
    result = _items(_project(tmp_path, config))
    assert result.returncode == 2, result.stdout + result.stderr
    assert f"cannot remove framework item {item}" in result.stderr


def test_an_unknown_top_level_key_is_a_load_error(tmp_path: Path) -> None:
    result = _items(_project(tmp_path, {"project": "p", "except": ["rm -rf"]}))
    assert result.returncode == 2
    assert "unknown key 'except'" in result.stderr


def test_the_shipped_example_loads(tmp_path: Path) -> None:
    example = json.loads((_REPO_ROOT / "scripts" / "autonomy.json.example").read_text("utf-8"))
    root = _project(tmp_path, example)
    assert autonomy.load_config(root)["project"] == "my-project"
    assert _items(root).returncode == 0


def test_load_config_raises_instead_of_exiting(tmp_path: Path) -> None:
    """The library raises; only the CLI turns that into exit 2. A SystemExit
    from inside a hook would block every command the hook sees."""
    root = _project(tmp_path, {"project": "p", "disable": ["AH1"]})
    with pytest.raises(autonomy.ConfigError, match="cannot remove framework item AH1"):
        autonomy.load_config(root)


# --------------------------------------------------------------------------- B-AC2

_CONFIG = {
    "project": "proj",
    "data_globs": ["data/**"],
    "deploy_prod_patterns": ["scripts/deploy.sh prod"],
    "deploy_dev_patterns": ["scripts/deploy.sh dev"],
    "spend_patterns": ["cloudctl buy"],
    "outward_patterns": ["notify-team"],
}

COMMAND_TABLE = [
    # owner-only (AH5), every spelling of the program
    ("scripts/approve.sh x --by a", ["AH5"]),
    ("./scripts/approve.sh x", ["AH5"]),
    ("bash scripts/approve.sh x", ["AH5"]),
    ("python3 scripts/approve.py x", ["AH5"]),
    ("/abs/path/scripts/delegate.sh 't' --by a", ["AH5"]),
    ("scripts/revoke.sh k", ["AH5"]),
    ("scripts/override.sh d", ["AH5"]),
    ("scripts/away.sh --until d", ["AH5"]),
    ("scripts/evolve.sh", ["AH5"]),
    ("sh scripts/release.sh", ["AH5"]),
    ("APPROVAL_LOG=/tmp/x nohup scripts/approve.sh y --by a", ["AH5"]),
    # writes to the registry (AH5)
    ("echo '{}' >> ~/.jarvis/approvals/registry.jsonl", ["AH5"]),
    ('echo x | tee -a "$APPROVAL_LOG"', ["AH5"]),
    ("cp forged.jsonl ${APPROVAL_LOG}", ["AH5"]),
    ("echo x>>~/.jarvis/approvals/registry.jsonl", ["AH5"]),
    # writes to protected paths (AH5)
    ("echo '{}' > scripts/autonomy.json", ["AH5"]),
    ("sed -i 's/a/b/' doc/mandates/MANDATE-proj-first.md", ["AH5"]),
    ("mv x.json scripts/autonomy.json", ["AH5"]),
    ("rm scripts/autonomy.json", ["AH5"]),
    # irreversible / outward (AH3)
    ("git push origin main", ["AH3"]),
    ("git push origin HEAD:master", ["AH3"]),
    ("git push origin --delete feature/x", ["AH3"]),
    ("git push origin :feature/x", ["AH3"]),
    ("git tag -d v1 && git push origin v1", ["AH3"]),
    ("git branch -D main", ["AH3"]),
    ("curl -X POST https://example.test", ["AH3"]),
    ("curl -XPUT https://example.test", ["AH3"]),
    ("curl --data a=1 https://example.test", ["AH3"]),
    ("curl -F f=@x https://example.test", ["AH3"]),
    ("wget --post-data a=1 https://example.test", ["AH3"]),
    ("scp report.txt host:/srv/", ["AH3"]),
    ("rsync -a out/ host:/srv/", ["AH3"]),
    ("ssh host uptime", ["AH3"]),
    ("sendmail someone", ["AH3"]),
    ("rm -rf data/", ["AH3"]),
    ("rm -r ./data/raw", ["AH3"]),
    ("sqlite3 app.db 'DROP TABLE users'", ["AH3"]),
    ("psql -c 'DELETE FROM users'", ["AH3"]),
    ("notify-team release", ["AH3"]),
    ("scripts/deploy.sh prod", ["AH3"]),
    ("bash scripts/deploy.sh dev", ["AH3"]),
    # spend (AH4)
    ("cloudctl buy --size large", ["AH4"]),
]

ALLOW_CASES = [
    "grep -rn 'git push origin main' doc/",
    "git push origin feature/x",
    "curl -s https://example.test/x",
    "python3 - <<'PY'\nimport os\nos.system('git push origin main')\nPY",
    "python3 -m pytest",
    "grep -rn 'scripts/approve.sh' .",
    "scripts/approve.sh --list",
    "scripts/approve.sh x --dry-run",
    "python3 scripts/approve.py -n x",
    "cat ~/.jarvis/approvals/registry.jsonl",
    "rm -rf build/",
    "echo hi 2>&1 >/dev/null",
    "git branch -D feature/x",
    "ssh -V",
]


@pytest.mark.parametrize(("command", "expected"), COMMAND_TABLE)
def test_classify_command_names_the_item(command: str, expected: list[str]) -> None:
    assert autonomy.classify_command(command, _CONFIG) == expected


@pytest.mark.parametrize("command", ALLOW_CASES)
def test_classify_command_ignores_look_alikes(command: str) -> None:
    assert autonomy.classify_command(command, _CONFIG) == []


def test_owner_only_matches_are_marked_always_on() -> None:
    """ADR-6: the owner-script rule holds in every project; the rest only
    under autonomy. The scope travels with the match so the guard cannot mix
    them up."""
    scopes = {m.scope for m in autonomy.command_matches("scripts/approve.sh x", _CONFIG)}
    assert scopes == {"always"}
    scopes = {m.scope for m in autonomy.command_matches("git push origin main", _CONFIG)}
    assert scopes == {"active"}


def test_the_cli_defines_exactly_the_subcommands_the_guard_allows(tmp_path: Path) -> None:
    """`autonomy.py <anything else>` is refused as AH5 under autonomy, so the
    allow-list and the CLI must not drift: a new subcommand added to one only
    would be either blocked for no reason or reachable without review."""
    result = subprocess.run(
        [sys.executable, str(_SCRIPT), "--help"], capture_output=True, text=True, timeout=30
    )
    listed = result.stdout.split("{", 1)[1].split("}", 1)[0].split(",")
    assert tuple(listed) == autonomy.AGENT_SUBCOMMANDS


def test_merge_on_a_protected_branch_needs_the_current_branch() -> None:
    assert autonomy.classify_command("git merge feature/x", _CONFIG, current_branch="main") == [
        "AH3"
    ]
    assert autonomy.classify_command("git rebase main", _CONFIG, current_branch="feature/x") == []


# --------------------------------------------------------------------------- B-AC8


def _doc(tmp_path: Path, name: str, header: str) -> Path:
    path = tmp_path / name
    path.write_text(f"# Doc\n\nStatus: In Review\n{header}\nUpstream: x\n", encoding="utf-8")
    return path


def test_a_spec_with_no_decision_class_is_unsure(tmp_path: Path) -> None:
    doc = _doc(tmp_path, "SPEC-x.md", "Risk tier: 1.")
    cls, items = autonomy.classify_artifact(doc, ["tests/test_x.py"])
    assert "AH-UNSURE" in items


def test_a_changed_path_matching_no_class_rule_is_unsure(tmp_path: Path) -> None:
    doc = _doc(tmp_path, "DESIGN-x.md", "")
    cls, items = autonomy.classify_artifact(doc, ["src/app/x.py"])
    assert cls == "AH-UNSURE"
    assert "AH-UNSURE" in items


def test_a_field_cannot_remove_a_touch_a_path_proves(tmp_path: Path) -> None:
    config = {"project": "p", "extra": {"AH1": {"paths": ["src/pricing/**"]}}}
    doc = _doc(tmp_path, "SPEC-x.md", "Decision-class: tier-1; touches: none")
    _, items = autonomy.classify_artifact(doc, ["src/pricing/fees.py"], config)
    assert "AH1" in items


def test_a_field_can_add_a_touch(tmp_path: Path) -> None:
    doc = _doc(tmp_path, "SPEC-x.md", "Decision-class: tier-1; touches: security")
    _, items = autonomy.classify_artifact(doc, ["src/app/x.py"])
    assert "AH2" in items


def test_in_class_test_infra_is_not_always_human(tmp_path: Path) -> None:
    """The negative half: without it, an implementation returning AH-UNSURE
    for everything would pass every test above."""
    doc = _doc(tmp_path, "SPEC-x.md", "Decision-class: test-infra; touches: none")
    cls, items = autonomy.classify_artifact(doc, ["tests/framework/test_x.py"])
    assert cls == "test-infra"
    assert items == set()


def test_a_protected_path_is_ah5_whatever_the_class(tmp_path: Path) -> None:
    doc = _doc(tmp_path, "SPEC-x.md", "Decision-class: framework-non-business; touches: none")
    cls, items = autonomy.classify_artifact(doc, ["scripts/approve.py"])
    assert cls == "framework-non-business"
    assert "AH5" in items


def test_the_higher_tier_wins(tmp_path: Path) -> None:
    doc = _doc(tmp_path, "SPEC-x.md", "Risk tier: 2.\nDecision-class: tier-1; touches: none")
    cls, _ = autonomy.classify_artifact(doc, ["src/app/x.py"])
    assert cls == "tier-2-feature"


# --------------------------------------------------------------------------- B-AC9
# Spec names tests/framework/test_doc_contracts.py; that file belongs to the
# uncommitted verify-tiers J increment, so this contract lives here instead.


def test_adapters_md_declares_enforcement_points_per_adapter() -> None:
    text = (_REPO_ROOT / "doc" / "framework" / "ADAPTERS.md").read_text(encoding="utf-8")
    assert "## รายการที่มนุษย์ตัดสินเสมอ — จุดบังคับต่อตัวเชื่อม" in text
    section = text.split("## รายการที่มนุษย์ตัดสินเสมอ — จุดบังคับต่อตัวเชื่อม", 1)[1]
    section = section.split("\n## ", 1)[0]
    rows = [line for line in section.splitlines() if line.startswith("| ")]
    for point in ("คำสั่ง (commands)", "เส้นทางที่ป้องกัน (paths)", "การเรียกผู้ช่วย (spawn)"):
        row = next((r for r in rows if r.startswith(f"| {point}")), None)
        assert row is not None, f"no row for {point}"
        cells = [c.strip() for c in row.strip("|").split("|")]
        assert len(cells) == 3 and all(cells), row
    command_row = next(r for r in rows if r.startswith("| คำสั่ง (commands)"))
    assert "หยุดไม่ได้" in command_row.split("|")[3], "adapter ข must declare it cannot stop commands"
