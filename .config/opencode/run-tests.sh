#!/usr/bin/env bash
# ~/.config/opencode/run-tests.sh
set -uo pipefail

root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$root" || exit 1

log="${TMPDIR:-/tmp}/opencode-tests-$(basename "$root").log"

runner=(uv run pytest)
command -v rtk >/dev/null 2>&1 && runner=(rtk uv run pytest)

"${runner[@]}" -q --no-header --tb=line -rf -p no:cacheprovider "$@" \
  > "$log" 2>&1
code=$?

echo "log: $log"
tail -n 60 "$log"
exit $code
