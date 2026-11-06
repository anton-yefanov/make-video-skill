---
name: make-video
description: Turn a one-prompt video idea into a finished MP4 of code-generated motion graphics (three.js 3D, canvas 2D, SVG), optionally synced to a song through local audio analysis. Use when the user says "make a video", "music video", "motion graphics", "animated explainer", "lyric video", or "/make-video <idea>".
---

# make-video

Turn one prompt into one finished MP4. Work autonomously from start to finish. Do not stop to ask questions. Make every creative decision yourself, and write any assumption in `brief.md`.

Tools live in `~/.claude/skills/make-video/tools` (`T` below):
- `T/analyze_audio.py`: you cannot hear audio, so this script turns a track into JSON. The JSON has tempo, beats, onsets, sections, key, and energy/brightness curves (0..1, every 0.25 s). With `--lyrics` it also adds lyrics with word timestamps.
- `T/render.mjs`: renders `scene.html` frame by frame in headless Chrome, then pipes the frames to ffmpeg to make an MP4. It also renders PNG stills for review.
- `T/template.html`: starter scene with three.js + a 2D canvas overlay, audio helpers, and a seeded RNG.
- `T/node_modules/three`: three.js, including addons (`three/addons/...`).

## Workflow

1. **Set up the run folder.**
   ```bash
   RUN=~/videos/$(date +%Y%m%d-%H%M)-<slug>; mkdir -p $RUN && cd $RUN
   ln -s ~/.claude/skills/make-video/tools tools
   cp tools/template.html scene.html
   ```
2. **Write the brief.** Write `brief.md`: the idea, format (default 1920x1080, 30 fps; vertical = 1080x1920), duration, style direction, color palette, typography, and a shot list with timestamps. If the user gave no duration: 15–30 s without audio, or the full audio clip with audio.
3. **Audio (only if the user gave a file or URL).**
   - Use a URL: `uvx yt-dlp -x --audio-format wav -o "song.%(ext)s" <url>`.
   - Trim: `ffmpeg -ss <start> -t <dur> -i in.wav song.wav`.
   - Analyze:
     `~/.claude/skills/make-video/.venv/bin/python -I tools/analyze_audio.py song.wav analysis.json [--lyrics]`.
     Use `--lyrics` for songs with vocals.
   - Read `analysis.json`. Write a short section in `brief.md` on the mood and story of the song. Map the shot list to the sections, map the cuts to downbeats, and map the motion intensity to `energy_curve`.
4. **Build `scene.html`.** Hard rules:
   - Set `window.SCENE = {width, height, fps, duration}`.
   - Make `window.renderFrame(t)` draw the complete frame for time `t` in seconds. The frame must depend only on `t`. Use no `Date.now()`, no `requestAnimationFrame` loops, no CSS animations, no unseeded `Math.random()`, and no physics that depends on earlier frames. If you need a simulation, precompute it in `window.ready`.
   - Load assets (fonts, textures, GLB) in `window.ready` (a Promise). Load files only from the run folder; the renderer serves the run folder over local HTTP. CDN imports work but are slower. Prefer `tools/node_modules`.
   - Mix layers as the idea needs: three.js on one canvas, a 2D canvas or SVG on top, and HTML/CSS text updated from `renderFrame` (set it from `t`, not from CSS animation).
   - Aim for real craft: camera moves, easing, depth, lighting, particles, post-processing (`three/addons/postprocessing`), typography, color grade, and transitions between shots. Avoid a cube that sits in the middle and spins.
5. **Review stills before the full render.** Render 6–10 key moments, and read each PNG with the Read tool:
   ```bash
   node tools/render.mjs scene.html --stills 0,3,7.5,12,20 --outdir previews
   ```
   Fix what looks wrong: empty frames, clipped text, bad contrast, dull composition, off-beat moments. Repeat. Two or three review rounds is the norm. Stop when it looks good, not when it looks perfect.
6. **Render the full video.**
   ```bash
   node tools/render.mjs scene.html out.mp4 [--audio song.wav]
   ```
   A full render takes several minutes, so run it with `run_in_background`. When it finishes, check the output with `ffprobe -v error -show_entries format=duration:stream=codec_name,width,height out.mp4`. Extract 3 frames with `ffmpeg -ss <t> -i out.mp4 -frames:v 1 check_<t>.png`, and read them to confirm the final render matches the stills.
7. **Deliver.** Report the full path of `out.mp4`, the duration and resolution, and 2–3 lines on the creative concept. Run `open $RUN/out.mp4`.

## Footage edits (remake a reference reel / edit real video clips)
1. Download the reference into `ref/`, using a yt-dlp venv: `python3 -m venv v && v/bin/pip install yt-dlp`. Extract its audio to `song.wav`.
2. Study the reference:
   - Detect the cuts: `ffmpeg -i ref/reel.mp4 -vf "select='gt(scene,0.25)',showinfo" -an -f null - 2>&1 | grep -o "pts_time:[0-9.]*"`.
   - Make contact sheets: `-vf "fps=4,scale=270:-1,tile=8x6"`. Read the full-res frames of every text or graphic insert.
   - Write the cut points, the insert timings, the grade and the typography into `brief.md`.
3. Get the footage from Pexels (free license):
   - Find clip pages with WebSearch (`allowed_domains: pexels.com`). The Pexels search pages return 403.
   - Download with `curl -sL -A "Mozilla/5.0" -o clips/<id>.mp4 https://www.pexels.com/download/video/<id>/`.
   - Prefer several clips from one shoot (adjacent IDs, same creator), so the story stays coherent.
   - Make a thumbnail strip of each clip, and pick the in-points from the strips.
4. Cut the base edit with a script (`cut.py`): use ffmpeg `-ss/-t`, `scale` + `crop` to the target aspect, `fps=30`, then concat into `base.mp4`. Use the reference's cut points.
5. Build `scene.html`:
   - Load `base.mp4` as a blob URL, which makes seeking reliable.
   - In `async renderFrame(t)`, seek to `t + 0.5/fps` and draw the video with `ctx.filter` for the grade.
   - Draw the inserts, grain and vignette on the canvas.
   - Render with `--audio song.wav`.
6. Tell the user about music licensing. Audio ripped from a reel can get muted on upload. Tell them to attach the sound in the app instead.

## Clip a long video (podcast/interview → short reel)
Worked example (code only, no media): `examples/podcast-to-reel/` — `cut.py`, `scene.html`, `transcribe.py`, `voiceid.py`, `loopfind.py`, `keylogo.py`, `brief.md`.
1. Download with a yt-dlp venv: `v/bin/yt-dlp -f "bv*[height<=1080]+ba/b" --merge-output-format mp4`. Subtitles often return 429, so do not depend on them.
2. Transcribe the whole video locally with word timestamps (faster-whisper `small.en`, `word_timestamps=True`).
   - Pass a numpy array from `soundfile`, not a path: the installed PyAV breaks `decode_audio`.
   - A 36 min video takes about 15 min on CPU, so run it in the background.
3. Pick one topic with a story: hook claim → concrete example → why → common mistake → takeaway. Do not pick random sound bites.
4. Identify speakers by voice, not by webcam motion: compare MFCC mean/std against reference clips of each person.
5. Cut points:
   - Snap them to the quietest 10 ms near the word boundary.
   - Whisper word times drift by ±150 ms, so verify by transcribing the final `dialogue.wav`.
   - Where a cut is wrong, check the RMS profile and whisper-probe short windows, then hard-set the onset.
6. Music:
   - If the source has a music bed (usually under the cold open), separate it with Demucs: `.demucs-venv/bin/python -m demucs --two-stems=vocals`.
   - Loop it on bar-aligned downbeats; find the most similar pair with chroma + MFCC.
   - End on the source's own sting, and time the logo to it.
7. Style match:
   - Read full-res frames of the source's text inserts for font, sizes and colors. Montserrat from github.com/JulietaUla/Montserrat matched here.
   - Key logos to alpha by color distance from the background.
   - Keep screen-share footage in natural sync with the speech that describes it.
8. Mix: sidechain-duck the music under the dialogue, then `loudnorm=I=-14:TP=-1.5` for Reels/TikTok.
9. Vertical safe zones: keep text in y 300–900 and the main media above y≈1650. Reels UI covers the bottom ~300 px and the right ~120 px.
- Do not run unsigned downloaded binaries (for example realesrgan-ncnn-vulkan): the permission classifier blocks them. For small webcam tiles, use lanczos + unsharp and keep the cards ≤2x upscale.

## Notes
- WebGL errors, or black frames in headless mode: check the `[scene error]` lines in the renderer output first. Set `preserveDrawingBuffer: true` (the template already sets it).
- Slow renders: lower the post-processing passes or the resolution, and do not raise the fps. 30 fps is the default.
- Video longer than about 2 min: split `renderFrame` into one function per shot, each in its own module, so each stays easy to edit.
- Single agent only. Do not fan out to subagents for review. In the source video, a multi-agent run cost more than 4 times the tokens of a single run.
