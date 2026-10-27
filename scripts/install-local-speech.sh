#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
export PATH="$HOME/.local/bin:$PATH"
echo 'Installing Ubuntu speech dependencies. sudo may ask for your Linux password.'
sudo apt-get update
sudo apt-get install -y curl ca-certificates libgomp1 libsndfile1 espeak-ng ffmpeg
if ! command -v nvidia-smi >/dev/null 2>&1 || ! nvidia-smi >/dev/null 2>&1; then
  echo 'NVIDIA CUDA is unavailable in WSL. Install/update the NVIDIA Windows driver with WSL support, then rerun install.bat.' >&2
  exit 1
fi
if ! command -v uv >/dev/null 2>&1; then
  installer="$(mktemp)"
  trap 'rm -f -- "$installer"' EXIT
  curl --fail --location --retry 3 https://astral.sh/uv/install.sh --output "$installer"
  sh "$installer"
fi
export UV_PROJECT_ENVIRONMENT="$root/data/wsl-api-env"
export UV_LINK_MODE=copy
uv sync --project apps/api --extra voice --python 3.11 --locked
uv tool install huggingface-hub
bash apps/api/interviewer/voice/provision_models.sh "$root/data/models"
echo 'Speech dependencies and models installed. No server was started.'
