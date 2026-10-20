#!/usr/bin/env bash
# THE HANDOFF TIER (opt-in). A machine chooses the tests from the diff against
# VERIFY_BASE_REF; paths you name can add to that choice, never remove from it.
#
#   scripts/verify-handoff.sh [paths…]   run the tier
#   scripts/verify-handoff.sh --status   print "opted in" or "not opted in"
#
# A project is opted in when scripts/verify.conf sets VERIFY_HANDOFF_TIER=on (see
# scripts/verify.conf.example). Otherwise this prints HANDOFF TIER NOT CONFIGURED
# and exits 3: scripts/verify-full.sh before every handoff stays in force.
#
# It never prints GREEN. It says how many tests it ran of how many exist
# ("ran N of M") and why it chose them; a run of 0 tests is a failure (exit 1).
# Exit codes: 0 ran and passed · 1 RED or EMPTY · 2 BANNED · 3 NOT CONFIGURED.
set -uo pipefail
CALLER_DIR="$(pwd -P)"
cd "$(dirname "$0")/.."

FALLBACK="scripts/verify-full.sh before every handoff stays in force"
not_configured() {
  echo "HANDOFF TIER NOT CONFIGURED — $1; $FALLBACK"
  exit 3
}

RUN_DIR=".verify/runs/$(date -u +%Y%m%dT%H%M%SZ)-$$-handoff"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
# Exported before the conf is sourced: a conf written for the fast tier expands
# $VERIFY_JUNIT_DIR in its arrays at assignment time.
export VERIFY_RUN_DIR="$RUN_DIR" VERIFY_JUNIT_DIR="$RUN_DIR/junit/conf"

# A conf with a syntax error is never "opted in": bash would keep whatever it
# read before the error and drop the rest without a word.
conf_state="absent"
if [ -f scripts/verify.conf ]; then
  if "$BASH" -n scripts/verify.conf 2>/dev/null; then
    . scripts/verify.conf || true
    conf_state="loaded"
  else
    conf_state="broken"
  fi
fi
opted_in=""
[ "$conf_state" = loaded ] && [ "${VERIFY_HANDOFF_TIER:-}" = on ] && opted_in=1

if [ "${1:-}" = "--status" ]; then
  if [ -n "$opted_in" ]; then
    echo "opted in"
  else
    echo "not opted in"
    [ "$conf_state" = broken ] && echo "scripts/verify.conf failed to load (syntax error)" >&2
  fi
  exit 0
fi
[ "$conf_state" = broken ] && not_configured "scripts/verify.conf failed to load (syntax error)"
[ -n "$opted_in" ] || not_configured "this project has not opted in"
# A tier that quietly skipped its own counting would be the failure it exists to catch.
# The recorder runs with `python3 -I`: a project script saved next to it under a
# stdlib name (scripts/select.py, scripts/json.py) would otherwise be imported in
# place of that module, and every run would die in an import.
if [ ! -f scripts/verify_record.py ]; then
  echo "HANDOFF TIER RED — recorder missing (scripts/verify_record.py)"
  exit 1
fi
[ "$(git rev-parse --is-inside-work-tree 2>/dev/null)" = true ] || not_configured "not a git work tree"
for var in VERIFY_SELECT_CMD VERIFY_FULL_TEST_CMD VERIFY_COLLECT_CMD; do
  [ -n "${!var:-}" ] || not_configured "$var is not set"
done

# ---- bans: the pytest family's argv in every configured command (am2), and ----
# ---- no flags at all among the arguments, which are paths --------------------
mkdir -p "$RUN_DIR"
named=()
flags=()
for a in "$@"; do
  case "$a" in
    -*) flags+=("$a") ;;
    *) named+=("$a") ;;
  esac
done
allow_args=()
for e in ${VERIFY_ALLOWED_FILTERS[@]+"${VERIFY_ALLOWED_FILTERS[@]}"}; do allow_args+=("--allow=$e"); done
ban_args=(${allow_args[@]+"${allow_args[@]}"})
for r in ${VERIFY_TEST_RUNNERS[@]+"${VERIFY_TEST_RUNNERS[@]}"}; do ban_args+=("--runner=$r"); done
ban_args+=("--step=select|${VERIFY_SELECT_CMD}" "--step=full|${VERIFY_FULL_TEST_CMD}"
           "--step=VERIFY_COLLECT_CMD|${VERIFY_COLLECT_CMD}")
has_lint=""
if [ -n "${LINT[*]+x}" ]; then
  has_lint=1
  ban_args+=("--step=lint|$(printf '%q ' "${LINT[@]}")")
fi
for f in ${flags[@]+"${flags[@]}"}; do ban_args+=("--runtime=$f"); done
ban_out="$(python3 -I scripts/verify_record.py check-banned "--extra=${VERIFY_EXTRA_BANNED:-}" \
  "--test-steps=select full" "${ban_args[@]}")"
ban_rc=$?
[ -n "$ban_out" ] && printf '%s\n' "$ban_out"
if [ "$ban_rc" -ne 0 ] && [ "$ban_rc" -ne 2 ]; then
  echo "HANDOFF TIER RED — recorder failed (check-banned exit ${ban_rc})"
  exit 1
fi
for f in ${flags[@]+"${flags[@]}"}; do
  case "$ban_out" in
    *"BANNED: $f "*) ;;
    *) echo "BANNED: $f — verify-handoff.sh takes paths only; a flag belongs in scripts/verify.conf" ;;
  esac
done
if [ "$ban_rc" -eq 2 ] || [ ${#flags[@]} -ne 0 ]; then exit 2; fi

# ---- the selection: diff against the base ∪ the paths you named ------------------
TREE_BEFORE="$(python3 -I scripts/verify_record.py tree-hash)"
# `--opt=value`, so a value that starts with `-` is still a value.
python3 -I scripts/verify_record.py diff-paths "--run-dir=$RUN_DIR" \
  "--base=${VERIFY_BASE_REF:-origin/main}" "--inputs=${VERIFY_UNTRACKED_INPUTS:-}" \
  "--cwd=$CALLER_DIR" -- ${named[@]+"${named[@]}"}
diff_rc=$?
if [ "$diff_rc" -ne 0 ] || [ ! -f "$RUN_DIR/mode" ]; then
  echo "HANDOFF TIER RED — the diff could not be read (diff-paths exit ${diff_rc})"
  exit 1
fi
# NUL-separated, so a space or a newline in a name stays inside that name.
selected=()
while IFS= read -r -d '' p; do selected+=("$p"); done <"$RUN_DIR/selected.z"
lint_paths=()
while IFS= read -r -d '' p; do lint_paths+=("$p"); done <"$RUN_DIR/lint.z"
mode="$(cat "$RUN_DIR/mode")"
: >"$RUN_DIR/steps.tsv"

# Output a step printed is indented, so no line of it can pass for a banner.
show_tail() { printf '%s\n' "$1" | tail -30 | sed 's/^/    /'; }

if [ -n "$has_lint" ] && [ ${#lint_paths[@]} -ne 0 ]; then
  t0=$(date +%s)
  if out="$("${LINT[@]}" "${lint_paths[@]}" 2>&1)"; then rc=0; else rc=$?; fi
  secs=$(( $(date +%s) - t0 ))
  if [ "$rc" -eq 0 ]; then
    printf '  %-5s%-18s(%ss)\n' "OK" "lint" "$secs"
  else
    printf '  %-5s%-18s(%ss) (exit %s)\n' "FAIL" "lint" "$secs" "$rc"
    show_tail "$out"
  fi
  printf 'lint\t%s\t%s\t0\t\n' "$rc" "$secs" >>"$RUN_DIR/steps.tsv"
fi

crc=0
eval "$VERIFY_COLLECT_CMD" >"$RUN_DIR/collect.txt" 2>"$RUN_DIR/collect.err" || crc=$?

if [ "$mode" = select ]; then label=select; else label=full; fi
export VERIFY_JUNIT_DIR="$RUN_DIR/junit/$label"
mkdir -p "$VERIFY_JUNIT_DIR"
t0=$(date +%s)
if [ "$label" = select ]; then
  # The paths go in as separate words, never pasted into the command string.
  if out="$(set -- "${selected[@]}"; eval "$VERIFY_SELECT_CMD"' "$@"' 2>&1)"; then rc=0; else rc=$?; fi
else
  if out="$(eval "$VERIFY_FULL_TEST_CMD" 2>&1)"; then rc=0; else rc=$?; fi
fi
secs=$(( $(date +%s) - t0 ))
if [ "$rc" -eq 0 ]; then
  printf '  %-5s%-18s(%ss) %s\n' "OK" "$label" "$secs" "$(printf '%s' "$out" | tail -1)"
else
  printf '  %-5s%-18s(%ss) (exit %s)\n' "FAIL" "$label" "$secs" "$rc"
  show_tail "$out"
fi
printf '%s\t%s\t%s\t0\t%s\n' "$label" "$rc" "$secs" "$VERIFY_JUNIT_DIR" >>"$RUN_DIR/steps.tsv"

# ---- counts, tree identity, record; the banner is the last line ------------------
TREE_AFTER="$(python3 -I scripts/verify_record.py tree-hash)"
python3 -I scripts/verify_record.py finalize --tier handoff --run-dir "$RUN_DIR" \
  --started-at "$STARTED_AT" --tree-before "$TREE_BEFORE" --tree-after "$TREE_AFTER" \
  --conf-present --collect-file "$RUN_DIR/collect.txt" --collect-rc "$crc" \
  ${allow_args[@]+"${allow_args[@]}"}
fin_rc=$?
case "$fin_rc" in
  0 | 1) exit "$fin_rc" ;;
  *) echo "HANDOFF TIER RED — recorder failed (finalize exit ${fin_rc})"; exit 1 ;;
esac
