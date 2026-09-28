#!/usr/bin/env bash
#
# Launch BRIDGE COMMANDER from this checkout.
#
#   ./bridge_commander.sh                     # player UI :8787, GM console :8788
#   ./bridge_commander.sh --flavor wc         # new rooms start on the wc setting
#   ./bridge_commander.sh --list-flavors      # print installed settings and exit
#   ./bridge_commander.sh --check-flavor wc   # validate one setting and exit
#
# Everything below is a default: export the variable before running to override
# it (e.g. PORT=9000 ./bridge_commander.sh).
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# Run from the repository root so ``python -m bridge`` imports this checkout
# rather than an installed copy, and so the relative DATA_DIR (./data) lands
# beside it.
cd "$SCRIPT_DIR"

# Prefer the project virtualenv, which is where ``pip install -e ".[dev]"``
# puts the runtime dependencies; fall back to whatever python3 is on PATH.
PYTHON="python3"
if [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
  PYTHON="$SCRIPT_DIR/.venv/bin/python"
fi

export HOST="${HOST:-127.0.0.1}"
export PORT="${PORT:-8787}"

# The GM console starts only when ADMIN_PORT is set, and then requires a
# non-empty ADMIN_TOKEN (the server fails closed otherwise).  This token is a
# local-development placeholder: replace it before putting the console anywhere
# another host can reach.
export ADMIN_HOST="${ADMIN_HOST:-127.0.0.1}"
export ADMIN_PORT="${ADMIN_PORT:-8788}"
export ADMIN_TOKEN="${ADMIN_TOKEN:-change-me}"
export ADMIN_ORIGINS="${ADMIN_ORIGINS:-http://localhost:${ADMIN_PORT}}"

# ACTIVITY_DIST and ASSET_DIR are deliberately left unset: the packaged
# bridge/activity/dist bundle and bridge/img tree are auto-discovered from this
# checkout.  Export them only to serve a bundle or art tree from elsewhere.

exec "$PYTHON" -m bridge "$@"
