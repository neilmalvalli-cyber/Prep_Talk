#!/usr/bin/env bash
set -euo pipefail

# Provision local speech assets for the interviewer voice adapter.
# Run at deployment/build time; the runtime adapter never downloads assets.
# Usage: ./provision_models.sh [VOICE_MODEL_DIR]

model_root="${1:-${VOICE_MODEL_DIR:-data/models}}"
mkdir -p "$model_root"

command -v hf >/dev/null 2>&1 || {
  echo "Install the Hugging Face CLI (huggingface_hub) before running this script." >&2
  exit 1
}
command -v curl >/dev/null 2>&1 || { echo "curl is required." >&2; exit 1; }

# CTranslate2 conversion of Whisper large-v3-turbo. Live repository metadata
# verified 2026-10-20: license MIT; pin the revision for reproducibility.
hf download dropbox-dash/faster-whisper-large-v3-turbo \
  --revision 0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf \
  --local-dir "$model_root/faster-whisper-large-v3-turbo"

# Kokoro ONNX project release assets; upstream project and license metadata:
# https://github.com/thewh1teagle/kokoro-onnx
curl --fail --location --retry 3 \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx \
  --output "$model_root/kokoro-v1.0.onnx"
curl --fail --location --retry 3 \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin \
  --output "$model_root/voices-v1.0.bin"

cat <<'NOTICE'
Assets were fetched from dropbox-dash/faster-whisper-large-v3-turbo on Hugging Face
and thewh1teagle/kokoro-onnx GitHub release. Review and retain each upstream
model card, license, and attribution requirements before redistribution or use.
NOTICE
