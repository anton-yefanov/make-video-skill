#!/usr/bin/env bash
# One-time setup for the make-video skill. Safe to re-run.
# Usage: ./setup.sh [--no-demucs]
set -euo pipefail
cd "$(dirname "$0")"

missing=()
for c in node npm ffmpeg ffprobe python3; do command -v "$c" >/dev/null || missing+=("$c"); done
if ((${#missing[@]})); then
  echo "Missing: ${missing[*]}"
  echo "macOS: brew install node ffmpeg python   |   Ubuntu: sudo apt install nodejs npm ffmpeg python3-venv"
  exit 1
fi
python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' || { echo "Need Python >= 3.10"; exit 1; }

CHROME="${CHROME_PATH:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
if [[ ! -x "$CHROME" ]]; then
  echo "Google Chrome not found at: $CHROME"
  echo "Install Chrome, or export CHROME_PATH=/path/to/chrome (add it to your shell profile)."
  exit 1
fi

echo "==> node deps (three, puppeteer-core)"
(cd tools && npm install --no-fund --no-audit)

echo "==> python venv for audio analysis + transcription"
[[ -d .venv ]] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

if [[ "${1:-}" != "--no-demucs" ]]; then
  echo "==> demucs venv for voice/music separation (~800 MB)"
  [[ -d .demucs-venv ]] || python3 -m venv .demucs-venv
  .demucs-venv/bin/pip install -q --upgrade pip
  .demucs-venv/bin/pip install -q demucs soundfile
fi

echo "==> self-check"
.venv/bin/python -c "import librosa, faster_whisper, soundfile; print('python deps ok')"
[[ -d .demucs-venv ]] && .demucs-venv/bin/python -c "import demucs; print('demucs ok')"
node -e "import('puppeteer-core').then(()=>console.log('node deps ok'))" --input-type=module 2>/dev/null || (cd tools && node -e "import('puppeteer-core').then(()=>console.log('node deps ok'))")
echo "Done. Restart Claude Code, then try: /make-video <idea>"
