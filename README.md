# make-video: a Claude Code skill

Turns a one-line prompt into a finished MP4. It can make:
- code-generated motion graphics with three.js, canvas or SVG, optionally synced to a song;
- footage edits from stock clips;
- short vertical reels cut from a long YouTube video, such as a podcast or interview.

Rendering is deterministic: headless Chrome renders each frame, and ffmpeg encodes them. Audio analysis and transcription run locally, so no API keys are needed.

Usage, once installed: `/make-video <idea>`.

## Install (paste this repo link into Claude Code and say "install this skill")

### Instructions for Claude
1. Clone the repo into the user's skills folder:
   `git clone <this-repo-url> ~/.claude/skills/make-video`.
   If that folder already exists, run `git -C ~/.claude/skills/make-video pull` instead.
2. Run `~/.claude/skills/make-video/setup.sh`.
   - If it reports missing tools on macOS, install them with `brew install node ffmpeg python`, then re-run it.
   - If Google Chrome is missing, ask the user to install it. On Linux, ask for the Chrome path and export `CHROME_PATH`.
   - `--no-demucs` skips the voice/music separation venv (about 800 MB). Use it only if the user says they never need music pulled from footage.
3. Confirm the script ends with `Done.`. Then tell the user to restart Claude Code, so the `make-video` skill loads.

### What gets installed
| Thing | Where | Size |
|---|---|---|
| three.js, puppeteer-core | `tools/node_modules` | ~55 MB |
| librosa, faster-whisper (Python venv) | `.venv` | ~550 MB |
| demucs (optional) | `.demucs-venv` | ~800 MB |
| Whisper and Demucs models | downloaded on first use | ~0.5 GB |

### Requirements
- Claude Code
- Google Chrome
- Node 18+
- ffmpeg
- Python 3.10+

The skill is tested on macOS with Apple Silicon. On another OS, set `CHROME_PATH`.

## Layout
- `SKILL.md`: the workflow Claude follows.
- `tools/render.mjs`: renders `scene.html` frame by frame and encodes the MP4 (or PNG stills).
- `tools/analyze_audio.py`: writes tempo, beats, sections, energy curves and optional lyrics to JSON.
- `tools/template.html`: starter scene.
- `examples/podcast-to-reel/`: the full code of a podcast-to-reel run (`cut.py`, `scene.html` and helpers). It contains no media.

## Notes
- Use only footage and music your team has the rights to. Audio taken from a video can get muted on upload; attach a licensed sound in the app instead.
- Updating: `git -C ~/.claude/skills/make-video pull`, then re-run `setup.sh`.
