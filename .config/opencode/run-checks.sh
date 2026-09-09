#!/usr/bin/env bash
# Quality gates for the one-analytics monorepo. Mirrors run-tests.sh:
# logs full output to a file, prints the log path + last 60 lines.
#
# Usage:
#   run-checks.sh                 # all gates, whole repo
#   run-checks.sh --changed       # all gates, only files changed vs origin/main
#   run-checks.sh ruff ty         # only the named gates
#   run-checks.sh --changed ruff  # combine
#   run-checks.sh --base <ref>    # override merge-base ref (default origin/main)
#
# Gates: ruff (check), format (ruff format --check), ty, complexipy, codespell
set -uo pipefail

root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$root" || exit 1

log="${TMPDIR:-/tmp}/opencode-checks-$(basename "$root").log"
: > "$log"

runner=(uv run)
command -v rtk >/dev/null 2>&1 && runner=(rtk uv run)

changed=0
base="origin/main"
gates=()

while [ $# -gt 0 ]; do
  case "$1" in
    --changed) changed=1; shift ;;
    --base) base="${2:-origin/main}"; shift 2 ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) gates+=("$1"); shift ;;
  esac
done

[ ${#gates[@]} -eq 0 ] && gates=(ruff format ty complexipy codespell)

targets=()
if [ "$changed" -eq 1 ]; then
  mb="$(git merge-base HEAD "$base" 2>/dev/null)"
  if [ -z "$mb" ]; then
    echo "run-checks: cannot resolve merge-base with '$base'" | tee -a "$log"
    exit 2
  fi
  while IFS= read -r f; do
    [ -n "$f" ] && [ -f "$f" ] && targets+=("$f")
  done < <(git diff --name-only --diff-filter=ACMR "$mb"...HEAD -- '*.py')
  if [ ${#targets[@]} -eq 0 ]; then
    echo "run-checks: no changed .py files vs $base — nothing to do." | tee -a "$log"
    echo "log: $log"
    exit 0
  fi
fi

rc=0
run_gate() {
  local name="$1"; shift
  echo "===== $name =====" >> "$log"
  "$@" >> "$log" 2>&1
  local code=$?
  if [ $code -ne 0 ]; then
    echo "----- $name FAILED (exit $code) -----" >> "$log"
    rc=1
  else
    echo "----- $name ok -----" >> "$log"
  fi
}

for g in "${gates[@]}"; do
  case "$g" in
    ruff)
      if [ ${#targets[@]} -gt 0 ]; then
        run_gate ruff "${runner[@]}" ruff check "${targets[@]}"
      else
        run_gate ruff "${runner[@]}" ruff check .
      fi ;;
    format)
      if [ ${#targets[@]} -gt 0 ]; then
        run_gate format "${runner[@]}" ruff format --check "${targets[@]}"
      else
        run_gate format "${runner[@]}" ruff format --check .
      fi ;;
    ty)
      # ty is package-scoped; whole-src check is the safe default.
      run_gate ty "${runner[@]}" ty check packages ;;
    complexipy)
      if [ ${#targets[@]} -gt 0 ]; then
        run_gate complexipy "${runner[@]}" complexipy "${targets[@]}"
      else
        run_gate complexipy "${runner[@]}" complexipy packages tests notebooks
      fi ;;
    codespell)
      if [ ${#targets[@]} -gt 0 ]; then
        run_gate codespell "${runner[@]}" codespell "${targets[@]}"
      else
        run_gate codespell "${runner[@]}" codespell
      fi ;;
    *)
      echo "run-checks: unknown gate '$g'" | tee -a "$log"; rc=2 ;;
  esac
done

echo "log: $log"
tail -n 60 "$log"
exit $rc
