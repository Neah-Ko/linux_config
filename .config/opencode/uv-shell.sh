#!/usr/bin/env bash

set -euo pipefail

# Walk up from cwd looking for a venv dir, then exec a normal shell with it active.
dir="$PWD"
while [ "$dir" != "/" ]; do
  for name in .venv venv env .env; do
    if [ -f "$dir/$name/bin/activate" ]; then
      source "$dir/$name/bin/activate"
      exec /bin/bash "$@"
    fi
  done
  # stop at repo root if there's a .git, otherwise keep going to /
  [ -d "$dir/.git" ] && break
  dir="$(dirname "$dir")"
done

# Setup providers
# STATE_FILE="$HOME/.config/opencode/current_provider"
# PROVIDER="$(cat "$STATE_FILE" 2>/dev/null || echo anthropic)"
# ENV_FILE="$HOME/.config/opencode/.env.$PROVIDER"
# [ -f "$ENV_FILE" ] && source "$ENV_FILE"

exec /bin/bash "$@"

