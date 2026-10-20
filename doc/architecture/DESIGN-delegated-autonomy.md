# DESIGN: Delegated autonomy

Status: Approved
Approval: design-delegated-autonomy-2026-10-20
Owner: ba-sa
Upstream: doc/specs/SPEC-delegated-autonomy.md (which derives from doc/requirements/PRD-delegated-autonomy.md)
Date: 2026-10-20

This design gives interfaces, data shapes, algorithms and decisions. Code appears only as pseudocode and signatures. The markers mean the same as in the spec:
- `[MEASURED: cmd]` — I ran it.
- `[INFERRED]` — I derived it by reading.
- `[RELAYED: PRD]` — a figure taken from the PRD.

## 0. Layering

| Layer | Files | Rule |
|---|---|---|
| 0–1 core (neutral) | `scripts/autonomy.py`, `scripts/digest.py`, `scripts/learning_loop.py`, the owner wrappers (`delegate.sh`, `revoke.sh`, `override.sh`, `away.sh`, `evolve.sh`, `release.sh`), `scripts/approve.py`, `scripts/verify_approvals.py`, the templates, `AGENTS.md`, the skills | Must not name any provider. `check_neutrality.py` must report 0. |
| 3 adapter ก | `.claude/hooks/guard_bash.py`, `guard_autonomy_paths.py`, `guard_agent_spawn.py`, `.claude/settings.json`, `.claude/agents/reviewer.md`, `evolution-scout.md` | Declared in ADAPTERS.md |
| 3 adapter ข | `.githooks/pre-commit`, `ci-examples/*` | Declared in ADAPTERS.md |

The hooks import the core validator. They do not copy it. They locate `scripts/autonomy.py` from the repo root, the same way `guard_agent_spawn.py` resolves the repo root today `[INFERRED from its _repo_root at line 66]`.

---

## B. The always-human list

### B.1 Items (constant `FRAMEWORK_ITEMS` in `scripts/autonomy.py`)

| ID | Item (PRD R7) | Matchers |
|---|---|---|
| AH1 | Business rules and numbers | Field: `Decision-class:` touches `business-rules`. Path globs from the project file. A PRD or spec under autonomy with no `Decision-class:` line → `AH-UNSURE` (R10). |
| AH2 | Security and personal data | Field: touches `security`/`personal-data`. Project path globs, for example auth modules and data schemas. |
| AH3 | Irreversible or outward-facing | Command table §B.2. Project path globs for data (`data_globs`). Protected branches. |
| AH4 | Spend beyond budget | Project `spend_patterns`. Any match while the mandate's `max_spend` is 0. |
| AH5 | Changing the mandate, the list or their enforcement | The protected paths in §B.3. Invoking an owner command (§B.2). |

**Project file `scripts/autonomy.json`.** It holds: `project` (slug), `protected_branches`, `data_globs`, `deploy_dev_patterns`, `deploy_prod_patterns`, `spend_patterns`, `outward_patterns`, `extra` (additions per AH ID), and `evolution.schedule`.

**Loading.** The file is unioned with `FRAMEWORK_ITEMS`. Any attempt to remove a framework matcher is a load error (exit 2). That covers an unknown top-level key, a `disable` key, or a framework ID redefined with fewer matchers.

**Fail-closed check.** `autonomy.py doctor` lists every AH class that has no detectable pattern on this project. When autonomy is active, `deploy_prod_patterns` and `spend_patterns` must both be non-empty, or `approve-under` refuses. The template cannot know how a project deploys or spends.

### B.2 Command table

Matching runs over `guard_bash._executable_segments` (heredocs stripped, quotes defused) at command position. This is the same parser the existing rules use `[MEASURED: verify-tiers G probe of _executable_segments]`.

| Pattern (program plus args) | Item | When |
|---|---|---|
| `scripts/approve.sh`, `approve.py`, `delegate.sh`, `revoke.sh`, `override.sh`, `away.sh`, `evolve.sh`, `release.sh` as the program; as the first argument of `bash`/`sh`/`python3`/`python`; or with any `./` or absolute prefix (matched by basename). Read-only flags (`--list`, `--dry-run`/`-n`) are allowed. | owner-only (AH5) | **always** |
| A redirect (`>`, `>>`), `tee [-a]`, `cp`/`mv`/`ln` whose target resolves to the registry path (`$APPROVAL_LOG` or the default) or its directory | owner-only (AH5) | **always** |
| A redirect, `tee`, `sed -i`, `cp`/`mv` targeting a §B.3 protected path | AH5 | autonomy active |
| `git push <remote> <protected-branch>`, `git push … --delete`, `git push … :<ref>`, `git tag -d` followed by a push, `git branch -D` on a protected branch, `git merge` / `git rebase` while on a protected branch | AH3 | autonomy active |
| `git commit` while `HEAD` is on a protected branch | AH3 (F-AC1) | autonomy active |
| `curl`/`wget` with `-X POST\|PUT\|PATCH\|DELETE`, `-d`, `--data*`, `-F`, `-T`, `--upload-file`; `scp`, `rsync` to `host:`; `ssh host …`; `sendmail`, `mail`; plus project `outward_patterns` | AH3 | autonomy active |
| `rm -r*`/`-f*` on a `data_globs` path; a SQL text matching `\b(DROP\|TRUNCATE)\b\|\bDELETE\s+FROM\b` anywhere in the segment arguments | AH3 | autonomy active |
| project `deploy_prod_patterns` | AH3 | autonomy active, unless an order grants `deploy-prod` and the owner is not absent |
| project `deploy_dev_patterns` | AH3 | autonomy active, unless an order grants `deploy-dev` |
| project `spend_patterns` | AH4 | autonomy active |

**Stated limits.**
- Commands hidden inside scripts, `bash -c "…"` or `python -c` are not seen.
- A pattern only knows the words it matches.

The guard makes such evasion tamper-*evident*. The trial's N7 probes and the CI checks are the backstop.

### B.3 Protected paths (AH5)

`scripts/autonomy.json`, `scripts/autonomy.py`, `scripts/approve.py`, `scripts/approve.sh`, `scripts/verify_approvals.py`, the six owner wrappers, `scripts/check_neutrality.py`, `doc/mandates/**`, `doc/orders/**`, `doc/decisions/**`, `doc/evolution/ledger.jsonl`, `.claude/hooks/**`, `.claude/settings.json`, `.githooks/**`, `ci-examples/**`, and the ban list in `scripts/verify_record.py` (once verify-tiers increment 2 ships).

`doc/decisions/**` and the ledger are written only through `autonomy.py` via Bash, never by Write/Edit, and the path guard blocks direct edits.

### B.4 Interception matrix (ADR-16)

| Point | Adapter ก (has C1) | Adapter ข (no C1) |
|---|---|---|
| Commands (§B.2) | `guard_bash.py`, refused before running | **Not stopped.** Effects are caught at commit (protected paths, branch) and at CI (stamps, log). Outward sends, deploys and spend cannot be caught at all; this is declared. |
| Writes to protected paths | `guard_autonomy_paths.py` (Write/Edit tools) and the guard_bash redirect rule | `pre-commit` → `autonomy.py check-commit`: protected paths need an `Owner-Approved: <key>` trailer while autonomy is active |
| Spawning on an unapproved, forged or provisional upstream | `guard_agent_spawn.py` with the shared validator | None at run time. CI `autonomy.py verify --ci` fails the PR. |
| QA without a review | `guard_agent_spawn.py` | None at run time. CI: a `QA-*.md` with no matching `REVIEW-*.md` fails `autonomy.py verify --ci`. |
| The owner's own commands | Assumed not intercepted when typed through the shell prefix `[INFERRED — B-AC5 proves or disproves this]` | Not applicable |

---

## A/G. Registry, stamps and the shared validator

### Registry entry kinds (ADR-1)

Every line keeps the five fields `load_registry` requires: `key`, `artifact`, `status`, `approved_by`, `approved_at`. Missing even one makes the whole registry unreadable for every project on the machine `[MEASURED: temp APPROVAL_LOG + one line without artifact → exit 1, 5/5 keys "registry unavailable"; same line with artifact plus extra fields kind/revokes → exit 0]`.

The existing fields `evidence` and the new optional ones (`kind`, …) are ignored by older verifiers `[MEASURED: same probe]`.

| kind | key | artifact | status | extra |
|---|---|---|---|---|
| (absent) = `approval` | `<stem>-<date>[-rN]` | the document | `Approved` | — |
| `mandate` | `mandate-<project>-<name>-<date>[-rN]` | `doc/mandates/MANDATE-<project>-<name>.md` | `Approved` | `expires`, `terms_sha256` |
| `order` | `order-<project>-<slug>-<date>[-rN]` | `doc/orders/ORDER-<project>-<slug>.md` | `Approved` | `grants`, `expires`, `task_sha256` |
| `revocation` | `revoke-<target>-<date>[-rN]` | the target's document | `Revoked` | `revokes` |
| `override` | `override-<decision-id>-<date>[-rN]` | `doc/decisions/decision-log.jsonl` | `Overridden` | `target`, `significant`, `reverse_requested` |
| `absence` | `absence-<project>-<date>[-rN]` | `doc/decisions/decision-log.jsonl` | `Declared` | `until` |
| `answer` | `answer-<ask-id>-<date>[-rN]` | `doc/decisions/decision-log.jsonl` | `Answered` | `target`, `choice` |

`verify_approvals.py` resolves keys only for documents that declare an approval line. Revocation and override keys are never declared by any document, so `entry.status != document status` cannot fire for them `[INFERRED from verify(): it looks entries up only by declared keys]`.

### Key revisions (ADR-4)

Today `approve.py` builds `stem-date`, so a same-day re-approval appends a second line with the same key. The registry holds one such pair now (`prd-verify-tiers-merge-gate-2026-10-20` ×2) `[MEASURED]`. `load_registry` keeps the last one written `[MEASURED: read — entries[key] = entry]`.

New rule, applied by the shared writer `approve.py:write_entries` that all owner wrappers use:

```
base = build_key(...)
key = base if base not in registry else f"{base}-r{n}"   # n = 2, 3, … first unused
```

Each key now identifies one decision. For mandates and orders, that means one version and one revocation.

### Stamps (ADR-2)

The status vocabulary is unchanged. The table shows how each kind of approval appears in a document's header lines.

| Situation | Status line | Approval line | Extra header line |
|---|---|---|---|
| Owner approved | `Approved` | `<key>` (in the registry) | none |
| Approved under a mandate | `Approved` | `<artifact key>` (in the **decision log**, not the registry) | `Approved-under: mandate <mandate key>` |
| Approved under an order | `Approved` | `<artifact key>` (decision log) | `Approved-under: order <order key>` |
| Provisional (during absence) | `In Review` | **none** | `Provisional: <decision-id>` |

`approve.py` refuses to stamp a document that already has an `Approved-under:` line. When the owner confirms a provisional document, `approve.py` removes the `Provisional:` line in the same write, so the document carries only owner-approval lines.

### The shared validator (ADR-3)

```python
# scripts/autonomy.py
@dataclass(frozen=True)
class Verdict: ok: bool; basis: str; reason: str        # basis: owner | mandate | order | provisional | none

def validate_approval(doc: Path, registry: dict, log: list[dict], today: date) -> Verdict
    # owner:     no Approved-under, key ∈ registry (existing rules)
    # mandate:   key ∈ log (kind approval, artifact == doc, under == mkey);
    #            mkey ∈ registry kind mandate; approval ts < any revocation of mkey; ts ≤ expires;
    #            class(doc) ∈ effective_classes(mkey, at=ts); count(approvals under mkey up to ts) ≤ max_decisions;
    #            not always_human(doc)
    # order:     same with okey; filename carries the order slug; class within grants
    # provisional: Provisional id ∈ log (kind provisional); no Approval line; Status In Review
def effective_classes(mandate_key: str, at: datetime, registry: dict, log: list[dict]) -> set[str]   # ADR-8
def classify_artifact(doc: Path, changed_paths: list[str]) -> tuple[str, set[str]]                 # (class, AH ids)
def status() -> str                         # "inactive" | "mandate <k>" | "order <k>" | "absence since <t>" (several joined)
```

There are three callers:
- `verify_approvals.py` calls `validate_approval` for every declared key that has `Approved-under:` and for every `Provisional:` document. Owner-basis keys keep today's code path unchanged.
- `guard_agent_spawn.py` replaces its plain status check with `validate_approval(...).ok`, and accepts `provisional` only when `status()` includes absence.
- `autonomy.py verify --ci` runs the same checks plus the log chain and the append-only check.

**CI gate 1**, which is inline and byte-identical in both YAML files, gains two rules:
1. If the document has `Approved-under: <basis> <k>`, the approval key must appear in the checkout's `doc/decisions/decision-log.jsonl` as `kind: approval` for this artifact, and `k` must appear in the registry with the matching kind.
2. A `Provisional:` document must not be `Approved`.

The full class and budget checks run in the next CI step (`autonomy.py verify --ci`). Gate 1 stays short enough to read in review.

### Classes (ADR-9)

Vocabulary: `tier-0`, `tier-1`, `test-infra`, `framework-non-business`, `tier-2-feature`, `merge`.

Derivation, given the document's tier and the changed paths (from `git diff --name-only <base>` for the work branch):

```
tier from the PRD/spec "Risk tier" text or the Decision-class line, whichever is HIGHER
test-infra             iff every changed path ∈ tests/**, ci-examples/**, scripts/verify*, fixtures
framework-non-business iff every changed path ∈ AGENTS.md, .agents/**, doc/framework/**, doc/templates/**, scripts/**
                       AND touches == none
then: any changed path ∈ protected paths (§B.3) → AH5, whatever the class
      any AH1/AH2 path glob hit or touches field → AH1/AH2
      no rule matched → AH-UNSURE (R10)
```

Required header lines apply only while autonomy is active. Documents written before that, or outside autonomy, are never failed retroactively. This is the same upgrade-safety rule as verify-tiers H.

---

## C. Decision log, overrides and narrowing

**`doc/decisions/decision-log.jsonl`**, one JSON object per line:

```json
{"id": "d-2026-10-21-0007", "prev": "<sha256 of previous line's bytes, or 64 zeros>", "ts": "...",
 "project": "<slug>", "kind": "approval|decision|provisional|ask|answer|queued|task-start|absence-start|absence-end|merge|close-order",
 "class": "...", "under": "mandate <k>|order <k>|absence|none", "artifact": "<path>",
 "options": ["..."], "choice": "...", "why": "...", "reverse": "<one action>", "depth": "...", "design": "..."}
```

- **Hash chain (ADR-7).** `verify-log` recomputes the chain. In CI, `--append-only <base>` requires that `git diff <base>..HEAD` on the file shows only added lines at the end.
- **Anchoring.** Every owner command records the current log head hash in its registry entry's `evidence` field (`log_head=<sha>`). Truncating the log back past an owner action is then detectable against the registry, which the assistant cannot write.
- **Field checks.** Free text is limited to 500 characters per field. The 13-digit identifier shape is refused (AGENTS.md §8).

**Override rate (R12) and narrowing (R14, ADR-8):**

```
decisions(window) = log entries kind ∈ {approval, decision, provisional} with ts in window, under != none
overrides(window) = registry kind override whose target ∈ decisions(window)
rate = |overrides| / |decisions|     (n printed; rate "n/a" when |decisions| == 0)
effective_classes(m, at):
    classes = terms.classes
    − {class(target) for o in overrides(at-14d..at) if o.significant}
    if rate(at-14d..at) > terms.override_threshold: − {class(target) for o in overrides(...)}; if none identifiable → ∅ (suspended)
    if correction_rate rose two consecutive 14-day windows → ∅
    if N4/N5 unmeasurable → ∅   (ADR-12)
```

Everything above is computed from the registry (owner-written), the log, `doc/memory` and `doc/qa`. The assistant writes nothing to narrow its own mandate (C-AC5). `correction_rate.measure()` is imported, not re-implemented. It currently counts 7-day windows `[MEASURED: correction_rate.py WINDOW_DAYS = 7]`; the 14-day comparison calls it with two windows.

---

## J. Orders

```
delegate.sh "<task>" --by <name> --until <YYYY-MM-DD> --allow <g1,g2> --slug <s>
  grants vocabulary: default {prd, spec, code, tests, qa, business-rules-in-task}; opt-in {merge, deploy-dev, deploy-prod}
  never-grantable set → exit 2; unknown → exit 2; "deploy" → exit 2; "merge" while scripts/verify-merge.sh absent → exit 2
  write doc/orders/ORDER-<project>-<s>.md (template order.md: task, grants, expiry, Status Approved + key) ; git add
  registry entry kind order (via approve.py writer; key revision rule applies)
  print effective default grants after narrowing (J-AC8)
```

- `approve-under --order` checks three things: the filename carries `<s>`, the class is inside the grants, and nothing it touches is never-grantable.
- `close-order` writes the single report.
- Gate integrity (R43) has two checks:
  - `approve-under` refuses a FAIL QA report.
  - A `merge` decision needs `verify-merge.sh --check <record> <ref>` to report `MERGE GATE GREEN` or the baseline-RED form (verify-tiers D).

## K. Absence

- `away.sh` writes the registry `absence` entry.
- `autonomy.py absence-start --trigger silence --ask <id>` checks that the ask has a recommendation and that `now - ask.ts > 4h`. It also checks that no `answer` or registry entry targets the ask (ADR-14).
- `absence-end` is logged by the coordinator on the first owner message. This is a coordinator-discipline rule; it cannot be machine-checked, and is stated as such. `status()` also ends a declared absence when `until` has passed.
- `merge-check <range>` refuses when any `provisional` entry's artifact lies in the range. If it is of class business-rules, it is refused regardless of the merge gate.
- **Queued items** (never-while-absent) are logged `kind: queued` by the guard's refusal message instruction. They are listed by `return-review` `[INFERRED: the guard cannot write the log itself without becoming a writer; it tells the agent to run autonomy.py queue … — the trial checks that queued items appear]`.

## D. Digest

`scripts/digest.py [--brief]` reads the registry, the log and the mandate terms, and prints sections D-AC1. Adapter ก runs it at SessionStart, next to `correction_rate.py --brief` `[MEASURED: settings.json SessionStart already runs correction_rate.py --brief]`. Push delivery is adapter-declared and unproven.

## E. Review gate

- `doc/templates/review-report.md` has these header lines: `Author-run: <id>` (from the engineer's handback) and `Reviewer-run: <id>`, plus `Verdict: PASS | FAIL`.
- `guard_agent_spawn.py` adds `qa` and `frontend-qa` to the gated types, with a check that is separate from the engineer check: the review file for the slug the prompt names must exist with a PASS verdict, and its two run IDs must differ.
- Run IDs come from the adapter. For ก, that is the subagent's agent ID, which appears in the transcript `[MEASURED: "agentId" key present on subagent events]`.
- Equality of run IDs proves only that they are different runs, not that the review was independent of the author's conversation. That part is the reviewer definition's instruction, and is stated as such.

## H. `--owner` measurement

The reader classifies an inbound `user` line as the owner's when all of these hold:
- `message.content` is a `str`;
- it does not start with `<`;
- `isMeta` is not true.

This follows the prior-art rule `[INFERRED from the coordinator's deep3.py is_human; H-AC1's fixture settles it]`. The meter attributes owner messages to feature windows taken from the registry and the log. Overlaps are split equally, which is a stated limit.

## I. Evolution

- `ledger.jsonl` entries: `id`, `title`, `source`, `verdict`, `reason`, `pain`, `expected`, `trial`, `excerpt`. The normalised title (lowercased, whitespace collapsed) and the source must be unique unless the re-entry is a `rejected → new_evidence` case.
- `excerpt` is the only field that holds fetched text. Reports render it inside `>` blockquotes.
- `evolution-scout` has `tools: WebSearch, WebFetch`. Its handback is data the coordinator reads; the coordinator writes ledger entries through `ledger-add`.
- `release.sh` runs `check_neutrality.py`, checks the CHANGELOG entry's four fields, then runs `git tag`. Tagging is local; pushing a tag is AH3.

## G. R27 patterns (for G-AC2)

| Pattern | Requires the qualifier `AGENTS.md §6` (mandate / order / absence) |
|---|---|
| `👤` | yes (the pipeline diagrams) |
| `human approval gate`, `no stage starts until the human` | yes |
| `only the human`, `Only the \*\*human\*\*`, `only the human approves`, `มีแต่มนุษย์` | yes |
| `must not start until the human`, `the human gives final approval` | yes |
| `ไม่มีการเดินข้ามมนุษย์` | yes |
| Exempt | Lines starting `Do not:`; lines inside the status-grammar code block (AGENTS.md:66-70) |

---

## ADRs

- **ADR-1 — One registry; every entry keeps the five required fields.**
  - **Context:** One file is shared per user. A new kind missing a field breaks every project's verification `[MEASURED]`.
  - **Decision:** Every new kind carries `key`, `artifact`, `status`, `approved_by` and `approved_at`, plus `kind`. Revocations, overrides and answers get their own keys.
  - **Consequences:** Projects still on an older framework keep verifying. They see the new lines but ignore them.
- **ADR-2 — Non-owner approval is a stamp plus a log entry; provisional is a stamp.**
  - **Context:** Agents must never write the registry (§6.2, R4). R3 needs a record that both humans and machines can tell apart. The PRD asks that §5 grammar change as little as possible.
  - **Decision:** Two optional header lines, `Approved-under:` and `Provisional:`. The status vocabulary is unchanged. Approvals made under a mandate or order go to the hash-chained log.
  - **Consequences:** Every Approved document still traces to a human registry line. That line is either the document's own approval or the mandate or order that covers it (R25).
- **ADR-3 — One validator, three callers.**
  - **Context:** `verify_approvals`, CI gate 1 and the spawn guard each decide whether a stamp counts. Today the guard reads only the status line `[MEASURED]`, so a forged `Approved-under:` would pass it.
  - **Decision:** `autonomy.validate_approval` is the single implementation. CI gate 1 mirrors its two cheap rules inline, and the full check runs as its own CI step.
  - **Consequences:** The guard can no longer disagree with verification.
- **ADR-4 — Keys gain a `-rN` revision suffix on collision.**
  - **Context:** Same-day re-approval reuses the key, and the registry already holds one duplicate `[MEASURED]`. Mandates and orders will be amended and revoked.
  - **Decision:** Every writer applies the suffix. Mandate and order keys include the project slug.
  - **Consequences:** First approvals keep today's key format, so existing tests still pass `[INFERRED]`. The existing duplicate is reported as legacy and never rewritten.
- **ADR-5 — Mandate and order slugs match the filename stem exactly.**
  - **Context:** `approve.py` matches a slug as a substring of the filename `[MEASURED: find_documents uses needle in name]`, so a short slug can sweep in other documents.
  - **Decision:** Slugs starting `mandate-` or `order-` must equal the stem.
  - **Consequences:** Ordinary slugs behave as before.
- **ADR-6 — The AH and path guards are on only while autonomy is active. The owner-script rule is always on.**
  - **Context:** R4 says "can never". Outside autonomy, the tier-2 gates already cover these paths, and this feature itself must be buildable.
  - **Decision:** As stated. This is spec open question 2.
  - **Consequences:** R6 holds: nothing changes for projects that have not opted in, except that agents can no longer run the owner's commands. That has always been a §6 violation.
- **ADR-7 — The decision log lives in the repo, hash-chained and append-only.**
  - **Context:** The assistant must write the log, and CI must read it. R11 requires tamper evidence "at the registry's level".
  - **Decision:** A JSONL hash chain, an append-only diff check in CI and at commit, and the head hash anchored in owner registry entries.
  - **Consequences:** Edits, deletions and reorders are detectable. Fabricating new entries is still possible, but each one is bounded by the validator.
- **ADR-8 — Narrowing is derived, never stored.**
  - **Context:** R14 says narrowing "never needs the assistant's consent".
  - **Decision:** `effective_classes` is computed from owner-written overrides and the measured guards.
  - **Consequences:** There is no state the assistant could forget to update or decline to write.
- **ADR-9 — The class is derived; fields can only add touches; protected paths are subtracted.**
  - **Context:** A self-declared class would let the approver choose its own scope. D3's `framework-non-business` would otherwise include hooks.
  - **Decision:** As described in §A/G Classes.
  - **Consequences:** A PRD that understates its own risk tier is caught by the path rules or the higher-tier rule, though not always. Overrides then narrow the class.
- **ADR-10 — The review gate sits at the QA spawn, for all work (D5).**
  - **Decision:** As described in §E.
  - **Consequences:** Every project that upgrades gains one step per feature. Its time is measured by the J meter in the trial.
- **ADR-11 — The scout is limited to its tool list; web text is stored only as quoted data.**
  - **Context:** R37c. Prompt injection cannot be ruled out by testing a model.
  - **Decision:** A deterministic tool restriction plus data-only storage. The behavioural part is a trial probe.
  - **Consequences:** It is stated honestly in I-AC6.
- **ADR-12 — A mandate cannot activate while N4 or N5 is unmeasurable.**
  - **Context:** R14 narrows when guard metrics rise. A metric that cannot be measured can never trigger.
  - **Decision:** Fail closed. This is spec open question 3.
  - **Consequences:** The first mandate waits for verify-tiers H plus 28 days of escaped-defect records.
- **ADR-13 — The owner commands are thin wrappers over `approve.py`'s writer.**
  - **Decision:** One code path for every registry write, including validation, key revision, log-head anchoring and the all-or-nothing write.
  - **Consequences:** The approve.py contract (tracked documents, one `Status:`, the history section, no prompt) applies to mandates and orders too.
- **ADR-14 — Silence-triggered absence needs a recorded ask with a recommendation that is more than 4 hours old.**
  - **Decision:** This makes R46's trigger checkable instead of asserted.
  - **Consequences:** Absence never starts from a question the owner has not been given a recommendation for.
- **ADR-15 — Merges under an order or absence need verify-tiers D.**
  - **Decision:** They are refused until `verify-merge.sh` exists.
  - **Consequences:** The `merge` grant and absence merges arrive with verify-tiers D.
- **ADR-16 — The interception matrix in §B.4 is declared per adapter in ADAPTERS.md.** Adapter ข cannot stop outward sends, deploys or spend, and that is stated there, not hidden.

## Approval history

- **2026-10-20 — approved (human).** Registry key `design-delegated-autonomy-2026-10-20`, carried on the canonical `Approval:` line above.
<!-- scripts/approve.sh writes the approval entry here. Leave this heading in
     place: approve.py REFUSES any document that lacks it. Dates and amendment
     history belong here, never on the canonical status line. -->

- **2026-10-20 — drafted.** ba-sa, alongside SPEC-delegated-autonomy.md.
