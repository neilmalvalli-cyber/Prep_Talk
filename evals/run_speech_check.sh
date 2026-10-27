#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
python_bin="$root/data/wsl-api-env/bin/python"
export LD_LIBRARY_PATH="$("$python_bin" -c 'import glob,site; print(":".join(path for base in site.getsitepackages() for path in glob.glob(base+"/nvidia/*/lib")))')${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PYTHONPATH="$root/apps/api"
exec "$python_bin" "${SPEECH_CHECK_SCRIPT:-evals/local_speech_check.py}" "$@"
