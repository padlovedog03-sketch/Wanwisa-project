#!/usr/bin/env bash
# Issue a task order (owner only). See delegate_main in scripts/approve.py.
#
#   scripts/delegate.sh "<task, one line>" --by <your-name> --until <YYYY-MM-DD> --slug <name> [--allow g1,g2]
#   scripts/delegate.sh --help
#
# Writes and stages doc/orders/ORDER-<project>-<slug>.md and appends its
# `kind: order` registry entry. Commit the document with the printed
# `Owner-Approved: <key>` trailer. Every rule lives in the Python.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -x "${here}/../.venv/bin/python" ]; then
  PY="${here}/../.venv/bin/python"
else
  PY="$(command -v python3)"
fi
exec "$PY" "${here}/approve.py" --delegate "$@"
