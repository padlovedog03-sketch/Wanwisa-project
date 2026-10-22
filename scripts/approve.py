#!/usr/bin/env python3
"""Register the human's approval of one or more documents, by slug.

AGENTS.md §6 rule 2: only the human's approval flips an artifact to
`Status: Approved`, and only the human may append to the approval registry
(the interception adapter's approval guard — listed in
`doc/framework/ADAPTERS.md` — blocks every agent write to it).

WHY THIS EXISTS: on the project this framework came from, the ceremony — not
the rule — was the bottleneck. Each approval was a ~25-line command composed
fresh by the assistant and pasted by the owner, which is worse on both axes
that matter: it is long enough that nobody reads it before running it, and
composing it fresh each time is how a real defect shipped (a `Status:` line
was stamped onto a document with no `## Approval history` section, and the
exit gate went red for the lost wording). A reviewed script run by the owner
is both shorter to type and safer than prose regenerated every time.

**What this script deliberately does NOT change:** the human is still the
actor. This file cannot approve anything on its own, an agent running it is
still an agent writing to the registry, and the property that matters — that
a human chose — comes from a human invoking it. Per AGENTS.md §6 the local
guards make forgery tamper-evident rather than impossible; the real
enforcement is the CI check on the protected branch. This script changes the
typing, not the trust model.

Usage (through an assistant's run-a-shell-line prefix (`!`), or any shell):
    scripts/approve.sh --list                    # what awaits approval
    scripts/approve.sh <slug> --by <your-name>   # approve every In Review doc for that slug
    scripts/approve.sh <slug> --dry-run          # show what would happen, write nothing

There is no confirmation prompt: naming the slugs is the deliberate act, and
the first version's `confirm? [y/N]` aborted every real run because the owner
types this through an assistant's run-a-shell-line prefix (`!`), which supplies no tty.

Every candidate is validated before ANYTHING is written. One bad document
aborts the whole run, so a batch can never half-apply.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIGURATION — adapt these to your project. Everything below the line is
# the contract, not configuration.
#
# The registry contract is shared by THREE consumers: this script (writes),
# `scripts/verify_approvals.py` (verifies) and
# the interception adapter's approval guard (denies agent writes; listed in
# `doc/framework/ADAPTERS.md`). They must
# agree on REGISTRY_ENV and DEFAULT_REGISTRY, and
# `tests/hooks/test_verify_approvals.py` pins that agreement — change one
# without the others and a test names the drift.
# ---------------------------------------------------------------------------

#: Where approvable documents live. Must match the handoff protocol's layout;
#: `doc/templates/` and `doc/framework/` are excluded on purpose — templates
#: carry placeholder lines that must never be approvable.
DOC_DIRS = ("doc/requirements", "doc/specs", "doc/architecture", "doc/qa", "doc/tasks")

#: The status a document must be in to be approvable, out of the vocabulary
#: AGENTS.md §5 fixes (`Draft | In Review | Approved | Done | Living`).
#: `Draft` is excluded on purpose: the pipeline's own gate is that a document
#: is reviewed before it is approved, and approving straight out of Draft
#: skips the review it names.
APPROVABLE_FROM = "In Review"
APPROVED = "Approved"

#: The section every approvable document must carry, so the approval leaves a
#: record of what it replaced.
REQUIRED_SECTION = "## Approval history"

#: The registry: one JSON object per line, entries
#: {key, artifact, status, approved_by, approved_at, evidence}.
REGISTRY_ENV = "APPROVAL_LOG"
DEFAULT_REGISTRY = Path.home() / ".jarvis" / "approvals" / "registry.jsonl"

#: Registry key shape. `stem` is the slugified filename, `date` is YYYY-MM-DD.
KEY_TEMPLATE = "{stem}-{date}"

#: Who approved. There is NO default name: a template that ships someone's
#: username makes every unconfigured run sign as that person, and a canned
#: signature is not a signature. Pass `--by` or export this variable once.
APPROVER_ENV = "APPROVER"

# ---------------------------------------------------------------------------
# The contract. These refusals are the product — do not parameterize them:
#   1. only git-tracked documents are approvable (untracked files are invisible
#      to every check that enumerates via `git ls-files`);
#   2. exactly one `Status:` line, or refuse (two lines means the file carries
#      a status for something other than itself);
#   3. the REQUIRED_SECTION must exist (an approval must record what it replaced);
#   4. all-or-nothing batching (a half-applied batch leaves the registry
#      disagreeing with the documents about which are approved);
#   5. no confirmation prompt (an assistant's run-a-shell-line prefix (`!`) has no tty; the first
#      version's prompt aborted every real run while looking like a refusal).
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Printed on every refusal AND on every success. A mechanism must declare what
#: it cannot prevent, and overclaiming is worse than having nothing — the moment
#: this script prints "approved" is precisely when a reader is most likely to
#: believe the stamp proves a human chose. It does not. It proves a stamp was
#: applied by whoever ran this command.
LIMIT_NOTICE = (
    "LIMIT (stated limit): this script records an approval, it does not authenticate "
    "one. Anything that can run it can also write the registry, so it makes forgery "
    "EVIDENT, not impossible. The enforcing layer is the CI check on a protected "
    "branch — outside the reach of whatever is being gated."
)

#: Matches only a canonical status line — anchored, so occurrences of
#: `Status: In Review` inside prose (documents quote each other constantly)
#: are never mistaken for the document's own.
STATUS_LINE = re.compile(r"^Status: (.+)$", re.MULTILINE)
SECTION_LINE = re.compile(rf"^{re.escape(REQUIRED_SECTION)}\s*$", re.MULTILINE)


class ApprovalError(RuntimeError):
    """A candidate document cannot be approved, with the reason stated."""


@dataclass(frozen=True)
class Candidate:
    """A document that is ready to be approved, and the key it will carry."""

    path: Path
    relative: str
    key: str


def registry_path() -> Path:
    """The registry file, honouring the same override the other two consumers read."""
    override = os.environ.get(REGISTRY_ENV)
    if override:
        return Path(override).expanduser()
    return DEFAULT_REGISTRY


#: The fields every registry line needs, whatever its kind (ADR-1). One line
#: without them makes `verify_approvals.py` fail every key on the machine.
REQUIRED_FIELDS = ("key", "artifact", "status", "approved_by", "approved_at")


def registry_entries() -> list[dict]:
    """Every entry in the registry that parses; a malformed line is left for
    `verify_approvals.py` to report."""
    path = registry_path()
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def revise(base: str, taken: set[str]) -> str:
    """`base`, or `base-rN` with the first unused N from 2 (A-AC9, ADR-4)."""
    if base not in taken:
        return base
    n = 2
    while f"{base}-r{n}" in taken:
        n += 1
    return f"{base}-r{n}"


def write_entries(entries: list[dict]) -> Path:
    """The one registry writer every owner command uses (ADR-13): every entry
    carries the five required fields, and all are appended in one write."""
    for entry in entries:
        missing = [field for field in REQUIRED_FIELDS if not entry.get(field)]
        if missing:
            raise ApprovalError(f"registry entry {entry.get('key')!r} lacks required field(s): {missing}")
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("".join(json.dumps(entry, ensure_ascii=False) + "\n" for entry in entries))
    return path


def tracked_documents() -> set[str]:
    """Repo-relative paths of every git-tracked markdown document under `doc/`.

    Tracked-ness is a precondition, not a detail: `verify_approvals.py` and the
    CI gates enumerate documents through `git ls-files`, so an untracked file
    is invisible to them. On the originating project a suite reported
    `125 passed` with two unallowlisted specs sitting untracked in the working
    tree, and only went red after `git add`. Approving a file those checks
    cannot see produces a registry entry nothing verifies.
    """
    result = subprocess.run(
        ["git", "ls-files", "--", "doc"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return {line for line in result.stdout.splitlines() if line.endswith(".md")}


def find_documents(slug: str, tracked: set[str]) -> list[Path]:
    """Every tracked document whose filename carries `slug`.

    Matched case-insensitively against the filename only, so a slug mentioned
    in another document's body never drags that document into the batch.
    """
    needle = slug.lower()
    matches = [
        REPO_ROOT / rel
        for rel in sorted(tracked)
        if any(rel.startswith(f"{d}/") for d in DOC_DIRS) and needle in Path(rel).name.lower()
    ]
    return matches


def read_status(text: str, relative: str) -> str:
    """The document's own canonical status, refusing anything ambiguous.

    More than one anchored `Status:` line means the document carries a status
    for something other than itself — on the originating project an
    `In Review` amendment section lived inside a file whose own line said
    `Approved`. Flipping such a file would silently change two things at once,
    so this refuses instead of guessing.
    """
    found = STATUS_LINE.findall(text)
    if not found:
        raise ApprovalError(f"{relative}: ไม่มีบรรทัด `Status:`")
    if len(found) > 1:
        raise ApprovalError(
            f"{relative}: มีบรรทัด `Status:` ขึ้นต้นบรรทัดอยู่ {len(found)} แห่ง — "
            "เอกสารหนึ่งฉบับต้องมีบรรทัดเดียว แยกส่วนแก้ไขเพิ่มเติมออกเป็นไฟล์ของมันเอง"
        )
    return found[0].strip()


def build_key(relative: str, today: str) -> str:
    """The registry key for a document: KEY_TEMPLATE over its slugified stem and the date."""
    stem = Path(relative).stem.lower()
    stem = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    return KEY_TEMPLATE.format(stem=stem, date=today)


def validate(path: Path, tracked: set[str], today: str) -> Candidate:
    """Check every precondition for `path`, or raise `ApprovalError` naming the first failure."""
    relative = path.relative_to(REPO_ROOT).as_posix()
    if relative not in tracked:
        raise ApprovalError(
            f"{relative}: git ยังไม่ track ไฟล์นี้ — `git add` ก่อน ไม่งั้นทะเบียนจะบันทึก"
            "เอกสารที่ระบบตรวจสอบมองไม่เห็น"
        )

    text = path.read_text(encoding="utf-8")
    status = read_status(text, relative)
    if status == APPROVED:
        raise ApprovalError(f"{relative}: เป็น `Status: {APPROVED}` อยู่แล้ว — ไม่มีอะไรให้ทำ")
    if status != APPROVABLE_FROM:
        raise ApprovalError(
            f"{relative}: `Status: {status}` — อนุมัติได้เฉพาะเอกสารที่เป็น "
            f"`{APPROVABLE_FROM}` เพื่อไม่ให้ Draft ข้ามรอบรีวิวของตัวเอง"
        )
    if not SECTION_LINE.search(text):
        raise ApprovalError(
            f"{relative}: ไม่มีหัวข้อ `{REQUIRED_SECTION}` — อนุมัติไปแล้วจะไม่เหลือบันทึก"
            "ว่าคีย์นี้แทนที่ถ้อยคำใด (ความผิดพลาดจริงที่เคยทำประตูออกแดงมาแล้ว)"
        )
    return Candidate(path=path, relative=relative, key=build_key(relative, today))


def apply(candidate: Candidate, evidence: str, approved_at: str, approver: str) -> dict:
    """Stamp the document and return the registry entry to append.

    The document is written first and the registry entry is returned rather
    than written, so the caller can append every entry only after every
    document has been stamped without error.
    """
    text = candidate.path.read_text(encoding="utf-8")
    text = STATUS_LINE.sub(
        f"Status: {APPROVED}\nApproval: {candidate.key}",
        text,
        count=1,
    )
    text = SECTION_LINE.sub(
        f"{REQUIRED_SECTION}\n\n"
        f"- **{approved_at[:10]} — approved (human).** Registry key `{candidate.key}`, "
        "carried on the canonical `Approval:` line above.",
        text,
        count=1,
    )
    candidate.path.write_text(text, encoding="utf-8")
    return {
        "key": candidate.key,
        "artifact": candidate.relative,
        "status": APPROVED,
        "approved_by": approver,
        "approved_at": approved_at,
        "evidence": evidence,
    }


def list_pending(tracked: set[str]) -> list[str]:
    """Every tracked document currently awaiting approval."""
    pending = []
    for rel in sorted(tracked):
        if not any(rel.startswith(f"{d}/") for d in DOC_DIRS):
            continue
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        found = STATUS_LINE.findall(text)
        if len(found) == 1 and found[0].strip() == APPROVABLE_FROM:
            pending.append(rel)
    return pending


# ---------------------------------------------------------------------------
# Task orders (SPEC-delegated-autonomy J-AC1, J-AC2, A-AC7; am2 AM2-AC5 d).
# `scripts/delegate.sh` and `scripts/revoke.sh` are thin wrappers that call
# this file with a leading `--delegate` / `--revoke`, so every registry write
# goes through `write_entries` (ADR-13) and stays behind the owner-script rule.
# ---------------------------------------------------------------------------

#: An order's grants (R41). `--allow` names them exactly; without it an order
#: carries the defaults. The opt-in ones are granted by name only.
DEFAULT_GRANTS = ("prd", "spec", "code", "tests", "qa", "business-rules-in-task")
OPT_IN_GRANTS = ("merge", "deploy-dev", "deploy-prod")
NEVER_GRANTABLE = (
    "delete-data",
    "delete-history",
    "send-outside",
    "spend",
    "security",
    "personal-data",
    "change-mandate",
    "change-orders",
    "change-always-human",
    "change-approval",
    "change-bans",
    "widen",
)
ORDER_TEMPLATE = "doc/templates/order.md"
ORDER_DOC = "doc/orders/ORDER-{project}-{slug}.md"
PROJECT_FILE = "scripts/autonomy.json"
MERGE_GATE = "scripts/verify-merge.sh"
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_CONTROL = re.compile("[\x00-\x1f\x7f\u0085  ]")
_MARKER = re.compile(r"<(project|slug|key|issuer|issued|task|grants|expires)>")


def _refuse(message: str) -> int:
    print(f"refused — nothing written: {message}", file=sys.stderr)
    print(LIMIT_NOTICE, file=sys.stderr)
    return 2


def grant_problems(grants: list[str]) -> list[str]:
    """Why each named grant cannot go on an order (J-AC2), or `[]`."""
    problems = []
    for grant in grants:
        if grant in NEVER_GRANTABLE:
            problems.append(f"grant {grant} is never grantable by an order (R41)")
        elif grant == "deploy":
            problems.append("grant deploy is ambiguous — say deploy-dev or deploy-prod")
        elif grant == "merge" and not (REPO_ROOT / MERGE_GATE).is_file():
            problems.append(f"merge needs the verify-tiers merge gate ({MERGE_GATE} is missing)")
        elif grant not in DEFAULT_GRANTS + OPT_IN_GRANTS:
            problems.append(f"unknown grant {grant or '(empty)'}")
    return problems


def project_slug() -> str | None:
    try:
        value = json.loads((REPO_ROOT / PROJECT_FILE).read_text(encoding="utf-8")).get("project")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        return None
    return value if isinstance(value, str) and SLUG.match(value) else None


def delegate_main(argv: list[str]) -> int:
    """`scripts/delegate.sh "<task>" --by o --until <date> [--allow g1,g2] --slug s`."""
    parser = argparse.ArgumentParser(
        prog="scripts/delegate.sh",
        description="Issue a task order: write and stage doc/orders/ORDER-<project>-<slug>.md "
        "and append its kind order registry entry.",
    )
    parser.add_argument("task", help="the task, one line (point to a PRD for more)")
    parser.add_argument("--by", default=os.environ.get(APPROVER_ENV, ""), help="who issues the order")
    parser.add_argument("--until", required=True, help="the order expires after this date, YYYY-MM-DD")
    parser.add_argument("--slug", required=True, help="the order's name, lowercase words joined by -")
    parser.add_argument(
        "--allow",
        default=",".join(DEFAULT_GRANTS),
        help=f"the grants, comma-separated (default: {','.join(DEFAULT_GRANTS)}; "
        f"opt-in by name: {','.join(OPT_IN_GRANTS)})",
    )
    parser.add_argument("--evidence", default="", help="why, recorded in the registry")
    args = parser.parse_args(argv)

    now = datetime.now().astimezone()
    today = now.strftime("%Y-%m-%d")
    if "\n" in args.task or "\r" in args.task:
        return _refuse("the task is one line — point to a PRD for more")
    # Each lands on one header line of the order document; a control or
    # line-separator character there could start a second header line.
    for name, value in (("the task", args.task), ("--by", args.by)):
        if _CONTROL.search(value):
            return _refuse(f"{name} contains a control character — write it as plain text on one line")
    if not args.task.strip():
        return _refuse("the task is empty")
    if not args.by:
        return _refuse(f"who issues the order? pass `--by <your name>` or export {APPROVER_ENV}")
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.until):
            raise ValueError
        datetime.strptime(args.until, "%Y-%m-%d")
    except ValueError:
        return _refuse(f"--until {args.until!r} is not a date YYYY-MM-DD")
    if args.until < today:
        return _refuse(f"--until {args.until} is in the past")
    if not SLUG.match(args.slug):
        return _refuse(f"--slug {args.slug!r} must be lowercase letters and digits joined by -")
    grants = args.allow.split(",")
    problems = grant_problems(grants)
    if problems:
        return _refuse("; ".join(problems))
    project = project_slug()
    if project is None:
        return _refuse(f"{PROJECT_FILE} names no project slug — the order's key and document need it")
    relative = ORDER_DOC.format(project=project, slug=args.slug)
    path = REPO_ROOT / relative
    if path.exists():
        return _refuse(f"{relative} already exists — an issued order is never rewritten; choose another --slug")

    key = revise(f"order-{project}-{args.slug}-{today}", {str(e.get("key")) for e in registry_entries()})
    values = {
        "project": project,
        "slug": args.slug,
        "key": key,
        "issuer": args.by,
        "issued": today,
        "task": args.task,
        "grants": ", ".join(grants),
        "expires": args.until,
    }
    template = (REPO_ROOT / ORDER_TEMPLATE).read_text(encoding="utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    # One pass, so a marker-shaped string inside the task is written verbatim.
    path.write_text(_MARKER.sub(lambda match: values[match.group(1)], template), encoding="utf-8")
    staged = subprocess.run(["git", "add", "--", relative], cwd=REPO_ROOT, capture_output=True, text=True)
    if staged.returncode != 0:
        path.unlink()
        return _refuse(f"git add {relative} failed: {staged.stderr.strip()}")
    entry = {
        "key": key,
        "artifact": relative,
        "status": APPROVED,
        "approved_by": args.by,
        "approved_at": now.isoformat(timespec="seconds"),
        "evidence": args.evidence or f"order issued by {args.by} on {today} via scripts/delegate.sh",
        "kind": "order",
        "grants": grants,
        "expires": args.until,
        "task_sha256": hashlib.sha256(args.task.encode("utf-8")).hexdigest(),
    }
    registry = write_entries([entry])
    print(f"order issued: {relative}  key={key}")
    print(f"grants: {', '.join(grants)}  expires: {args.until}")
    print(f"registry: {registry}")
    print(f'next: git commit -m "order: {args.slug}" -m "Owner-Approved: {key}"')
    print(f"\n{LIMIT_NOTICE}")
    return 0


def revoke_main(argv: list[str]) -> int:
    """`scripts/revoke.sh <key> --by o`: append a revocation entry (A-AC7)."""
    parser = argparse.ArgumentParser(
        prog="scripts/revoke.sh",
        description="Revoke an order, mandate or approval: append its kind revocation registry entry. "
        "It takes effect at the next gate that reads the registry.",
    )
    parser.add_argument("target", help="the registry key to revoke")
    parser.add_argument("--by", default=os.environ.get(APPROVER_ENV, ""), help="who revokes it")
    parser.add_argument("--evidence", default="", help="why, recorded in the registry")
    args = parser.parse_args(argv)

    entries = registry_entries()
    by_key = {str(entry.get("key")): entry for entry in entries}
    target = by_key.get(args.target)
    if not args.target or target is None:
        return _refuse(f"{args.target!r} is not in the registry")
    if target.get("kind") == "revocation":
        return _refuse(f"{args.target} is itself a revocation")
    earlier = [e for e in entries if e.get("kind") == "revocation" and e.get("revokes") == args.target]
    if earlier:
        return _refuse(f"{args.target} is already revoked by {earlier[0].get('key')}")
    if not args.by:
        return _refuse(f"who revokes it? pass `--by <your name>` or export {APPROVER_ENV}")

    now = datetime.now().astimezone()
    today = now.strftime("%Y-%m-%d")
    key = revise(f"revoke-{args.target}-{today}", set(by_key))
    entry = {
        "key": key,
        "artifact": str(target.get("artifact", "")),
        "status": "Revoked",
        "approved_by": args.by,
        "approved_at": now.isoformat(timespec="seconds"),
        "evidence": args.evidence or f"revoked by {args.by} on {today} via scripts/revoke.sh",
        "kind": "revocation",
        "revokes": args.target,
    }
    try:
        registry = write_entries([entry])
    except ApprovalError as error:
        return _refuse(str(error))
    print(f"revoked: {args.target}  key={key}")
    print(f"registry: {registry}")
    print(f"\n{LIMIT_NOTICE}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code; never raises for expected failures."""
    argv = sys.argv[1:] if argv is None else argv
    # The order wrappers' entry points. A leading `--…` can never be a slug.
    if argv[:1] == ["--delegate"]:
        return delegate_main(argv[1:])
    if argv[:1] == ["--revoke"]:
        return revoke_main(argv[1:])
    parser = argparse.ArgumentParser(
        prog="scripts/approve.sh",
        description="Register the human's approval of documents, by slug.",
    )
    parser.add_argument("slugs", nargs="*", help="document slugs, e.g. payment-refunds")
    parser.add_argument("--list", action="store_true", help="show what awaits approval")
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="show what would be approved and write nothing",
    )
    parser.add_argument(
        "--by",
        default=os.environ.get(APPROVER_ENV, ""),
        help=f"who is approving (default: ${APPROVER_ENV}; there is no fallback name)",
    )
    parser.add_argument("--evidence", default="", help="why, recorded in the registry")
    args = parser.parse_args(argv)

    tracked = tracked_documents()

    if args.list or not args.slugs:
        pending = list_pending(tracked)
        if not pending:
            print("ไม่มีเอกสารรออนุมัติ")
            return 0
        print("รออนุมัติ:")
        for rel in pending:
            print(f"  {rel}")
        if not args.slugs:
            print("\nส่ง slug เพื่ออนุมัติ เช่น scripts/approve.sh <slug> --by <ชื่อคุณ>")
        return 0

    now = datetime.now().astimezone()
    today = now.strftime("%Y-%m-%d")

    # Resolve and validate EVERYTHING before writing anything, so a bad
    # document in a batch cannot leave the earlier ones half-applied.
    candidates: list[Candidate] = []
    problems: list[str] = []
    for slug in args.slugs:
        matches = find_documents(slug, tracked)
        if not matches:
            problems.append(f"{slug}: ไม่มีเอกสารที่ git track และชื่อไฟล์ตรงกับ slug นี้")
            continue
        for path in matches:
            try:
                candidates.append(validate(path, tracked, today))
            except ApprovalError as error:
                problems.append(str(error))

    if problems:
        print("ปฏิเสธทั้งชุด — ยังไม่ได้เขียนอะไรเลย:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        print(LIMIT_NOTICE, file=sys.stderr)
        return 1
    if not candidates:
        print("ปฏิเสธ — ไม่พบเอกสารที่อนุมัติได้", file=sys.stderr)
        print(LIMIT_NOTICE, file=sys.stderr)
        return 1

    # A same-day re-approval gets `-rN`, so no two registry lines share a key,
    # within this batch included (A-AC9).
    taken = {str(entry.get("key")) for entry in registry_entries()}
    for index, candidate in enumerate(candidates):
        key = revise(candidate.key, taken)
        taken.add(key)
        candidates[index] = Candidate(path=candidate.path, relative=candidate.relative, key=key)

    print("กำลังจะอนุมัติ:")
    for candidate in candidates:
        print(f"  {candidate.relative}\n      key: {candidate.key}")

    # No confirmation prompt, deliberately. The first version asked `confirm?
    # [y/N]` and was unusable: the owner types this through an assistant's `!`
    # prefix, which supplies no tty, so `input()` hit EOF and aborted every
    # run. It also bought nothing — naming the slugs explicitly IS the
    # deliberate act, and a prompt that cannot be answered is friction with no
    # safety. `--dry-run` exists for looking first.
    if args.dry_run:
        print("\n--dry-run: ยังไม่ได้เขียนอะไร")
        return 0

    if not args.by:
        print(
            f"ปฏิเสธ — ไม่รู้ว่าใครเป็นผู้อนุมัติ: ใส่ `--by <ชื่อคุณ>` หรือ export "
            f"{APPROVER_ENV}=<ชื่อคุณ> ไว้ครั้งเดียว (เทมเพลตนี้จงใจไม่มีชื่อ default — "
            "ลายเซ็นสำเร็จรูปไม่ใช่ลายเซ็น)",
            file=sys.stderr,
        )
        print(LIMIT_NOTICE, file=sys.stderr)
        return 1

    evidence = args.evidence or f"approved by {args.by} on {today} via scripts/approve.sh"
    approved_at = now.isoformat(timespec="seconds")
    entries = [apply(candidate, evidence, approved_at, args.by) for candidate in candidates]

    path = write_entries(entries)

    for entry in entries:
        print(f"อนุมัติแล้ว: {entry['artifact']}  key={entry['key']}")
    print(f"\nทะเบียน: {path}")
    print("ขั้นต่อไป: python3 scripts/verify_approvals.py แล้วค่อย commit เอกสารที่ถูกประทับ")
    print(f"\n{LIMIT_NOTICE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
