#!/usr/bin/env bash
# Revoke an order, mandate or approval (owner only). See revoke_main in scripts/approve.py.
#
#   scripts/revoke.sh <registry key> --by <your-name>
#   scripts/revoke.sh --help
#
# Appends a `kind: revocation` registry entry; it takes effect at the next
# gate that reads the registry. Every rule lives in the Python.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -x "${here}/../.venv/bin/python" ]; then
  PY="${here}/../.venv/bin/python"
else
  PY="$(command -v python3)"
fi
exec "$PY" "${here}/approve.py" --revoke "$@"
