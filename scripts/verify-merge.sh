#!/usr/bin/env bash
# THE MERGE GATE. One machine full run per merge candidate.
#
#   scripts/verify-merge.sh [<ref>]                  judge <ref> (default HEAD)
#   scripts/verify-merge.sh --check <record> [<ref>] re-check an existing record
#                                                    (e.g. one a CI runner wrote)
#
# The candidate commit is checked out in a fresh `git worktree`, so the verdict
# is about the committed tree, never the caller's working copy (which may be
# dirty). The gate code in it -- scripts/verify-full.sh, scripts/verify_record.py
# and scripts/verify.conf -- is first replaced by the BASE ref's copies, so a
# candidate cannot judge itself with gate code it wrote. The result is bound to
# the candidate's tree and to the machine that ran it, and ends in exactly one of:
#
#   MERGE GATE GREEN — tree <hash> — runner <id>   exit 0
#   MERGE GATE RED …                               exit 1
#   MERGE GATE NOT RUN — <reason>                  exit 3
#
# GREEN needs all of: verify-full exited 0 and wrote its record; that record is
# GREEN; it counted executed == collected; it judged exactly the candidate's
# tree, and that tree did not change during the run; and it names a runner.
# "Merge gate not run" is never green.
#
# Configuration comes from the BASE ref's committed scripts/verify.conf plus the
# environment — never from the candidate or the caller's working copy:
#   VERIFY_MERGE_GATE      runner | local-fallback | none (default none)
#   VERIFY_RUNNER_ID       set by the runner in its environment; a conf may not set it
#   VERIFY_MERGE_BASE_REF  environment only; default origin/main, else main
# Opted-in projects run this once per merge instead of a full run per handoff
# (scripts/verify-handoff.sh --status says whether a project has opted in).
#
# LIMIT: a candidate that changes the gate code legitimately is judged by the
# base's old copy; a `note:` line and the merge record say so.
# LIMIT: the base ref is trusted. A base the agent can write (a local `main`,
# or VERIFY_MERGE_BASE_REF=HEAD) makes base == candidate, and forged gate code
# is judged by itself again; only a protected base closes this.
# LIMIT: this script itself runs from the caller's checkout; only a copy from
# the runner's trusted checkout of the base is a gate.
# LIMIT: VERIFY_RUNNER_ID and VERIFY_MERGE_BASE_REF come from the environment,
# so whoever runs the gate can set them; `runner <id>` names where it says it ran.
set -uo pipefail
ORIG_PWD="$(pwd)"
cd "$(dirname "$0")/.." || exit 3

not_run() {
  # A CRLF conf must not put a carriage return inside the banner line.
  echo "MERGE GATE NOT RUN — ${1//$'\r'/\\r}"
  exit 3
}

check_mode=""
record=""
if [ "${1:-}" = "--check" ]; then
  check_mode=1
  [ -n "${2:-}" ] || not_run "--check needs a record path: scripts/verify-merge.sh --check <record> [<ref>]"
  record="$2"
  case "$record" in /*) ;; *) record="$ORIG_PWD/$record" ;; esac
  ref="${3:-HEAD}"
else
  ref="${1:-HEAD}"
fi

command -v git >/dev/null 2>&1 || not_run "git is not available"
[ "$(git rev-parse --is-inside-work-tree 2>/dev/null)" = "true" ] || not_run "not inside a git work tree"
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT" || not_run "cannot enter $ROOT"
# Resolved once: whatever the ref points at later, this run judges this commit.
sha="$(git rev-parse --verify --quiet "${ref}^{commit}")" || not_run "$ref does not name a commit"
want="$(git rev-parse "${sha}^{tree}")"

# The judge: one place that turns a record into the one banner line. Inputs are
# arguments; it never trusts the record's shape and never prints a traceback.
judge() {
  python3 - "$@" <<'PY'
import json, sys

args = dict(a.split("=", 1) for a in sys.argv[1:])
WEAKER = " (local fallback — weaker: same machine and same user as the agent)"


def done(kind, text, code, record=None, runner=None):
    if args.get("out"):
        merge = {"schema": 1, "tier": "merge", "ref": args["ref"], "commit": args["sha"],
                 "tree": bound or ((record or {}).get("tree") if isinstance(record, dict) else None),
                 "gate_code": {"base_ref": args["base_ref"], "base_commit": args["base_sha"],
                               "changed_by_candidate": args["changed"].split()},
                 "runner": runner, "count_check": (record or {}).get("count_check")
                 if isinstance(record, dict) else None,
                 "verdict": kind, "outcome": text, "full_exit": int(args["rc"]),
                 "full_record": record}
        with open(args["out"], "w", encoding="utf-8") as fh:
            json.dump(merge, fh, indent=2)
            fh.write("\n")
        print("record: %s" % args["out_shown"])
    print(text)
    sys.exit(code)


def nr(reason, record=None, runner=None):
    done("NOT-RUN", "MERGE GATE NOT RUN — " + reason, 3, record, runner)


main_run = "rc" in args
bound = None
try:
    with open(args["record"], encoding="utf-8") as fh:
        rec = json.load(fh)
    if not isinstance(rec, dict):
        raise ValueError("not an object")
except (OSError, ValueError, KeyError):
    if main_run:
        done("RED", "MERGE GATE RED — verify-full.sh exited %s and wrote no readable record" % args["rc"], 1)
    nr("record %s is missing or unreadable" % args.get("record", "?"))

tier = rec.get("tier")
if tier not in ("full", "merge"):
    nr("record is a %s run, not a full run" % tier, rec)

tree = rec.get("tree") if isinstance(rec.get("tree"), dict) else {}
before, after = tree.get("before"), tree.get("after")
# A main run judged the candidate's tree with the base's gate code in it.
judged = args.get("judged", args["want"])
if before != judged:
    nr("record is for tree %s, %s tree %s" % (
        before, "candidate is" if judged == args["want"] else "judged", judged), rec)
if main_run:
    # Bound to the candidate's own tree: after == before stays the same test.
    bound = {"before": args["want"], "after": args["want"] if after == before else after,
             "judged": judged}

if main_run:
    runner = {"id": args["runner_id"], "kind": args["kind"]}
    if args["kind"] == "local-fallback":
        inner = rec.get("runner") if isinstance(rec.get("runner"), dict) else {}
        runner["id"] = str(inner.get("id") or "").strip()
else:
    runner = rec.get("runner") if isinstance(rec.get("runner"), dict) else {}
    runner = {"id": str(runner.get("id") or "").strip(), "kind": runner.get("kind")}
if not runner["id"] or runner["kind"] not in ("runner", "local-fallback"):
    nr("record names no runner" + (" (kind %s)" % runner["kind"] if runner.get("kind") else ""), rec)

tail = " — tree %s — runner %s%s" % (args["want"], runner["id"],
                                      WEAKER if runner["kind"] == "local-fallback" else "")
verdict = rec.get("verdict")
if main_run and args["rc"] != "0" and verdict not in ("RED", "RED-BASELINE"):
    done("RED", "MERGE GATE RED — verify-full.sh exited %s" % args["rc"] + tail, 1, rec, runner)
if after != before:
    done("RED", "MERGE GATE RED — tree changed during the run" + tail, 1, rec, runner)
if verdict in ("RED", "RED-BASELINE"):
    done("RED", "MERGE GATE RED" + tail, 1, rec, runner)
if verdict == "INCOMPLETE":
    todo = [s.get("label") for s in rec.get("steps") or [] if isinstance(s, dict) and s.get("todo")]
    nr("verify-full was INCOMPLETE (steps not configured: %s)" % " ".join(map(str, todo)), rec, runner)
if verdict not in ("GREEN", "NOT-RUN"):
    nr("record verdict is %s" % verdict, rec, runner)
if verdict == "NOT-RUN":
    nr("record verdict is NOT-RUN (%s)" % rec.get("outcome"), rec, runner)
if rec.get("count_check") != "ok":
    nr("executed == collected is not configured", rec, runner)
done("GREEN", "MERGE GATE GREEN" + tail, 0, rec, runner)
PY
}

if [ -n "$check_mode" ]; then
  judge "record=$record" "want=$want"
  exit $?
fi

# ---- run: a fresh worktree of the candidate ----------------------------------
# The gate code comes from the base ref, resolved once like the candidate.
if [ -n "${VERIFY_MERGE_BASE_REF:-}" ]; then
  base_ref="$VERIFY_MERGE_BASE_REF"
  base_sha="$(git rev-parse --verify --quiet "${base_ref}^{commit}")" || base_sha=""
else
  for base_ref in origin/main main; do
    base_sha="$(git rev-parse --verify --quiet "${base_ref}^{commit}")" && break
  done
fi
[ -n "$base_sha" ] || not_run "no base ref to take the gate code from"
base="$(mktemp -d "${TMPDIR:-/tmp}/merge-gate.XXXXXX")" || not_run "cannot create a temporary directory"
wt="$base/merge-gate-$sha"
cleanup() {
  git -C "$ROOT" worktree remove --force "$wt" >/dev/null 2>&1
  git -C "$ROOT" worktree prune >/dev/null 2>&1
  rm -rf "$base"
}
trap cleanup EXIT
git worktree add --detach --quiet "$wt" "$sha" >/dev/null 2>&1 || not_run "could not create a worktree of $sha"

# The base's gate code replaces the candidate's; a file the base lacks is removed.
gate_files="scripts/verify-full.sh scripts/verify_record.py scripts/verify.conf"
changed=""
from_sha="$(git merge-base "$base_sha" "$sha" 2>/dev/null)" || from_sha="$base_sha"
for f in $gate_files; do
  git diff --quiet "$from_sha" "$sha" -- "$f" 2>/dev/null || changed="$changed $f"
  if git cat-file -e "$base_sha:$f" 2>/dev/null; then
    git -C "$wt" checkout -q "$base_sha" -- "$f" || not_run "could not take $f from $base_ref"
  else
    git -C "$wt" rm -q --ignore-unmatch -- "$f" >/dev/null || not_run "could not remove $f"
  fi
done
[ -z "$changed" ] ||
  echo "note: this candidate changes the gate code — judged with $base_ref's copy; review the gate diff"
# The tree the run will see: the candidate's, with the base's gate code in it.
judged="$(git -C "$wt" write-tree)" || not_run "could not hash the tree to be judged"

# The base's committed conf, read in a subshell: its values reach this
# script only as the three printed variables.
env_runner="${VERIFY_RUNNER_ID:-}"
conf="$wt/scripts/verify.conf"
if [ -f "$conf" ]; then
  echo "conf: scripts/verify.conf as committed in $base_ref ($base_sha)"
  bash -n "$conf" >/dev/null 2>&1 || not_run "scripts/verify.conf in $base_ref failed to load (syntax error)"
  # A conf that fails at load time ends this subshell before printf runs.
  settings="$(cd "$wt" && set +u && . scripts/verify.conf >/dev/null 2>&1
    printf 'conf_mode=%q\nconf_collect=%q\nconf_runner=%q\n' \
      "${VERIFY_MERGE_GATE:-}" "${VERIFY_COLLECT_CMD:-}" "${VERIFY_RUNNER_ID:-}")"
  case "$settings" in
    conf_mode=*) eval "$settings" ;;
    *) not_run "scripts/verify.conf in $base_ref failed to load" ;;
  esac
else
  echo "conf: none committed in $base_ref; environment only"
  conf_mode="${VERIFY_MERGE_GATE:-}"
  conf_collect="${VERIFY_COLLECT_CMD:-}"
  conf_runner="$env_runner"
fi
[ "$conf_runner" = "$env_runner" ] ||
  not_run "scripts/verify.conf sets VERIFY_RUNNER_ID; only the runner's environment may name the runner"

mode="${conf_mode:-none}"
case "$mode" in
  none) not_run "no runner and no local fallback configured" ;;
  runner | local-fallback) ;;
  *) not_run "unknown VERIFY_MERGE_GATE=$mode (runner, local-fallback or none)" ;;
esac
[ -n "$conf_collect" ] || not_run "executed == collected is not configured"

if [[ "$env_runner" =~ [^[:space:]] ]]; then
  kind="runner"
elif [ "$mode" = "runner" ]; then
  not_run "VERIFY_MERGE_GATE=runner but VERIFY_RUNNER_ID is empty"
else
  kind="local-fallback"
  env_runner=""
fi

# verify-full's own output is relayed indented, so no line of it can be read as
# this gate's banner.
echo "MERGE CANDIDATE — $ref = $sha, tree $want ($kind)"
(cd "$wt" && VERIFY_RUNNER_ID="$env_runner" bash scripts/verify-full.sh) 2>&1 |
  tee "$base/full.out" | while IFS= read -r line; do printf '  | %s\n' "$line"; done
rc="${PIPESTATUS[0]}"

# Only a record inside this run's own worktree counts.
inner=""
rel="$(sed -n 's/^record: //p' "$base/full.out" | tail -1)"
case "$rel" in
  .verify/runs/*/record.json) [ -f "$wt/$rel" ] && inner="$wt/$rel" ;;
esac

now="$(git rev-parse --verify --quiet "${ref}^{commit}")"
if [ -n "$now" ] && [ "$now" != "$sha" ]; then
  echo "note: $ref now points at $now; this verdict is for $sha only"
fi

mkdir -p "$ROOT/.verify/merge"
judge "record=${inner:-$base/no-record}" "want=$want" "judged=$judged" "rc=$rc" "kind=$kind" \
  "runner_id=$env_runner" "ref=$ref" "sha=$sha" \
  "base_ref=$base_ref" "base_sha=$base_sha" "changed=$changed" \
  "out=$ROOT/.verify/merge/$sha.json" "out_shown=.verify/merge/$sha.json"
