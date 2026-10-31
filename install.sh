#!/usr/bin/env bash
# One-time install for the local live interpreter.
# Creates .venv/ and voices/ inside this project folder (both are git-ignored).
# Usage: bash install.sh [voice]   (default voice: en_US-ljspeech-medium, public domain)
# Normally run through `make install`, which then asks for your language.
set -euo pipefail

cd "$(dirname "$0")"
VOICE="${1:-en_US-ljspeech-medium}"

echo "==> Audio tools"
if [ "$(uname)" = "Darwin" ]; then
  command -v brew >/dev/null || { echo "Install Homebrew first: https://brew.sh"; exit 1; }
  command -v ffmpeg >/dev/null || brew install ffmpeg
  [ -d "/Library/Audio/Plug-Ins/HAL/BlackHole2ch.driver" ] || brew install --cask blackhole-2ch
else
  if ! command -v parec >/dev/null || ! command -v pactl >/dev/null; then
    echo "parec/pactl missing, installing pulseaudio-utils (needs sudo)"
    sudo apt install -y pulseaudio-utils pavucontrol
  fi
  if ! command -v ffmpeg >/dev/null; then
    echo "ffmpeg missing (needed for --input-file tests), installing (needs sudo)"
    sudo apt install -y ffmpeg
  fi
fi

echo "==> Python venv in .venv/"
if [ ! -x .venv/bin/python ]; then
  if ! python3 -m venv .venv 2>/dev/null; then
    # python3.x-venv not installed: create without pip and bootstrap it
    rm -rf .venv
    python3 -m venv --without-pip .venv
    curl -fsSL https://bootstrap.pypa.io/get-pip.py | .venv/bin/python
  fi
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

if command -v nvidia-smi >/dev/null 2>&1; then
  echo "==> NVIDIA GPU found, installing CUDA runtime libs"
  .venv/bin/python -m pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"
fi

echo "==> Piper voice: $VOICE"
mkdir -p voices
LANG_CODE="${VOICE%%-*}"; REST="${VOICE#*-}"; SPEAKER="${REST%-*}"; QUALITY="${REST##*-}"
BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/${LANG_CODE%%_*}/${LANG_CODE}/${SPEAKER}/${QUALITY}"
for ext in onnx onnx.json; do
  [ -f "voices/$VOICE.$ext" ] || curl -fL -o "voices/$VOICE.$ext" "$BASE/$VOICE.$ext"
done

echo
echo "Done. Next: make run   (asks for your language the first time)"
