#!/usr/bin/env bash
# Copyright Schneider Electric 2026
# Spool a branch/PR diff to disk and print only a compact summary.
# Usage: review-diff.sh [--base <ref>] [--pr <n>] [stat|files|log|full]
set -uo pipefail

root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$root" || exit 1

base_ref=""
pr=""
mode="stat"

while [ $# -gt 0 ]; do
  case "$1" in
    --base) base_ref="${2:-}"; shift 2 ;;
    --pr) pr="${2:-}"; shift 2 ;;
    stat|files|log|full) mode="$1"; shift ;;
    -h|--help)
      echo "usage: review-diff.sh [--base <ref>] [--pr <n>] [stat|files|log|full]"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

git_cmd=(git --no-pager)
command -v rtk >/dev/null 2>&1 && git_cmd=(rtk git)

if [ -z "$base_ref" ]; then
  if [ -n "$pr" ] && command -v gh >/dev/null 2>&1; then
    base_ref="origin/$(gh pr view "$pr" --json baseRefName --jq .baseRefName 2>/dev/null)"
  fi
fi
if [ -z "$base_ref" ] || [ "$base_ref" = "origin/" ]; then
  base_ref="origin/main"
fi
git rev-parse --verify --quiet "$base_ref" >/dev/null || base_ref="main"

base="$(git merge-base "$base_ref" HEAD 2>/dev/null)"
if [ -z "$base" ]; then
  echo "cannot resolve merge-base against $base_ref" >&2
  exit 1
fi

log="${TMPDIR:-/tmp}/opencode-diff-$(basename "$root").log"
git --no-pager diff "$base...HEAD" > "$log" 2>&1

echo "base: ${base:0:12} ($base_ref)"
echo "log: $log"

case "$mode" in
  stat)  "${git_cmd[@]}" diff --stat "$base...HEAD" ;;
  files) "${git_cmd[@]}" diff --name-status --diff-filter=ACMR "$base...HEAD" ;;
  log)   "${git_cmd[@]}" log --oneline "$base..HEAD" ;;
  full)  tail -n 200 "$log" ;;
esac
