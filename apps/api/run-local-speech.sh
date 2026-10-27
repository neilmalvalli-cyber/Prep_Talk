#!/usr/bin/env bash
set -euo pipefail
# Application speech runtime only. Never installs Docker, gVisor or the runner.
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"
export UV_PROJECT_ENVIRONMENT="$root/data/wsl-api-env"
export UV_LINK_MODE=copy
uv sync --project apps/api --extra voice --python 3.11 --locked
python_bin="$UV_PROJECT_ENVIRONMENT/bin/python"
export LD_LIBRARY_PATH="$("$python_bin" -c 'import glob,site; print(":".join(path for base in site.getsitepackages() for path in glob.glob(base+"/nvidia/*/lib")))')${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PYTHONPATH="$root/apps/api"
export VOICE_MODEL_DIR="$root/data/models"
if [[ -z "${FIELDNOTE_AUTH_URL:-}" ]]; then
  host_gateway="$(ip route | awk '$1 == "default" { print $3; exit }')"
  if [[ -z "$host_gateway" ]]; then
    echo "Could not find the Windows host address for the Better Auth service." >&2
    exit 1
  fi
  export FIELDNOTE_AUTH_URL="http://${host_gateway}:8001"
fi
exec "$python_bin" -m uvicorn interviewer.main:app --host 127.0.0.1 --port 8000 --workers 1
