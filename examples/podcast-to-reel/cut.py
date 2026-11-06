"""Build the reel's media: base.mp4 (visual track), dialogue.wav, music.wav, timeline.json.
Run with the skill venv: ~/.claude/skills/make-video/.venv/bin/python -I cut.py
"""
import json, subprocess, os, re
import numpy as np, soundfile as sf

SRC = 'ref/src.mp4'
FPS = 30
SR = 44100
os.makedirs('build', exist_ok=True)
T = json.load(open('ref/transcript.json'))
WORDS = [w for s in T for w in s['words']]

TILES = {'nick': (46, 282, 390, 218), 'dan': (46, 550, 390, 218), 'axel': (46, 818, 390, 218)}
NAMES = {'nick': 'NICK PETRANGELO', 'dan': 'DANIEL DVORESS', 'axel': 'AXEL HALLAY'}
BROLL = {  # intro b-roll in source: (start, end, crop_x) for a 608x1080 vertical crop that avoids burned-in text
    'A': (1.10, 2.45, 700), 'B': (2.50, 3.75, 930), 'C': (3.80, 4.75, 1100), 'D': (4.80, 5.55, 980), 'E': (13.10, 16.20, 716)}

# Audio segments: (src_in, src_out, speaker, shots, captions)
# shots: list of (src_time_switch_or_None, kind, arg). kind: cam | grid | broll
# captions: lines separated by ' / ', groups by ' // ', style suffix: word~s (small) word~b (big) word~r (big red). default small.
SEGS = [
    (868.45, 869.40, 'nick', [(None, 'cam', None)],
     "I'M IN A / BOUNTY.~r"),
    (869.68, 871.38, 'nick', [(None, 'broll', 'A')],
     "// I'LL ADJUST~b A LITTLE BIT,"),
    (871.80, 873.10, 'nick', [(None, 'broll', 'C')],
     "/ I'LL CALL~b A LITTLE BIT WIDER.~b"),
    (873.20, 874.56, 'nick', [(None, 'broll', 'D')],
     "/ I'LL PLAY~b A LITTLE BIT LOOSER.~b"),
    (874.96, 878.30, 'nick', [(None, 'cam', None)],
     "// AND REALLY THE ANSWER IS / YOU'RE PLAYING A / COMPLETELY~r / DIFFERENT~r GAME.~b"),
    (912.22, 913.98, 'dan', [(None, 'cam', None)],
     "// LET'S SAY LIKE / HIJACK~b GOES / ALL~r IN.~r"),
    (914.84, 916.20, 'dan', [(None, 'cam', None)],
     "/ WHAT DO WE CALL FROM THE / BIG~b BLIND?~b"),
    (917.12, 919.86, 'axel', [(None, 'cam', None)],
     "// I CAN ALREADY TELL YOU THAT / WE'RE GOING TO CALL / ANY~r TWO.~r"),
    (933.92, 939.62, 'nick', [(None, 'grid', 'strategy')],
     "// SO EVERYONE / PAUSE~b A MOMENT~b / AND JUST ASK YOURSELF // LIKE ARE YOU / CALLING~b / ANY~r TWO~r / VERSUS 11~b HERE?~b"),
    (1042.06, 1045.70, 'nick', [(None, 'grid', 'pp')],
     "// THERE'S A BUNCH OF HANDS / THAT ARE JUST / NEGATIVE,~r RIGHT? // LIKE YOU'RE DOING ALL THIS / NEGATIVE~r / STUFF.~b"),
    (1045.72, 1047.42, 'nick', [(None, 'grid', 'pp')],
     "// BUT THEN WHEN YOU / GO~b TO~b KO,~b"),
    (1049.18, 1052.10, 'nick', [(None, 'grid', 'pp'), (1049.85, 'grid', 'ko')],
     "// YOU'RE GOING TO SEE THAT / IT'S GOING TO START / MAKING~b YOU~b / MONEY.~r"),
    (1059.40, 1065.12, 'nick', [(None, 'grid', 'ev')],
     "// BUT THE STRATEGY / THAT COMES TOGETHER / IS WHEN YOU / ADD~b THE~b TWO~b UP,~b // YOU'RE MAKING / MORE~r MONEY~r / THAN IF YOU / FOLDED.~b"),
    (845.38, 850.05, 'axel', [(None, 'cam', None)],
     "// I WOULD SAY THIS IS THE / COMMON~r MISTAKE~r / JUST BEING / TIGHTER~b / AT THIS STAGE."),
    (853.33, 860.10, 'nick', [(None, 'cam', None), (855.40, 'broll', 'E'), (859.00, 'broll', 'C')],
     "// PEOPLE ARE PLAYING / TOO~r TIGHT~r // AND JUST / MISSING~b OUT~b / ON THIS / MONEY~r // THAT THEY COULD JUST / PICK~b RIGHT~b UP~b / OFF~r THE~r TABLE.~r"),
    (1497.02, 1504.48, 'dan', [(None, 'cam', None)],
     "// YOU NEED TO KNOW / WHAT FACTORS~b / TO FOCUS ON // SO THAT YOU CAN / SWITCH~r GEARS~r / FASTER~b / THAN YOUR OPPONENTS."),
]

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: raise SystemExit(' '.join(cmd) + '\n' + r.stderr[-2000:])

# ---- snap cut points to the quietest 10 ms within a small window (avoids clipped consonants)
def load(a, b):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{a:.3f}', '-t', f'{b - a:.3f}', '-i', SRC, '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2)

def snap(t, lo, hi):
    x = load(t + lo, t + hi).mean(1); n = int(SR * 0.01)
    rms = [np.sqrt((x[i:i + n] ** 2).mean()) for i in range(0, len(x) - n, n // 2)]
    return t + lo + int(np.argmin(rms)) * (n // 2) / SR + 0.005

segs = []
for i, (a, b, spk, shots, cap) in enumerate(SEGS):
    NOSNAP = {933.92, 1042.06, 845.38, 1504.48}  # hand-verified onsets (whisper-probed)
    a2, b2 = (a if a in NOSNAP else snap(a, -0.06, 0.06)), (b if b in NOSNAP else snap(b, -0.06, 0.08))
    segs.append(dict(i=i, a=a2, b=b2, spk=spk, shots=shots, cap=cap))

# ---- reel timing: gaps; music fixes logo pop time
LOOP_A, LOOP_B, STING_DB, STING_END = 8.429, 20.828, 22.384, 25.4
N_LOOPS = 4
base_gaps = [0.10 if segs[k + 1]['spk'] == segs[k]['spk'] else 0.20 for k in range(len(segs) - 1)]
speech = sum(s['b'] - s['a'] for s in segs)
# first pass starts at an earlier downbeat (s0) so the music length fits the dialogue; pick the tightest fit
DOWNBEATS = json.load(open('ref/intro_music.json'))['downbeats_guess']
def logo_t(s0): return (LOOP_B - s0) + (N_LOOPS - 1) * (LOOP_B - LOOP_A) + (STING_DB - LOOP_B)
fits = [d for d in DOWNBEATS if d <= LOOP_A and logo_t(d) - 0.40 - speech - sum(base_gaps) >= -0.04 * len(base_gaps)]
S0 = max(fits)
LOGO_T = logo_t(S0)
slack = LOGO_T - 0.40 - speech - sum(base_gaps)
gaps = [g + slack / len(base_gaps) for g in base_gaps]
assert min(gaps) >= 0.05, f'dialogue too long for music plan: gaps {min(gaps):.3f}'
t = 0.0
for k, s in enumerate(segs):
    s['t0'] = round(t * FPS) / FPS          # frame-aligned reel start
    s['dur'] = s['b'] - s['a']
    t = s['t0'] + s['dur'] + (gaps[k] if k < len(gaps) else 0)
    s['t1'] = round(t * FPS) / FPS          # visual end (includes gap)
END = LOGO_T + 2.9
print(f'music from {S0}, speech {speech:.2f}s, gaps avg {np.mean(gaps):.3f}, logo at {LOGO_T:.3f}, end {END:.2f}')

# ---- visual shots -> clips -> base.mp4 (1080x1920, all-intra for exact seeks)
shots_out = []
clips = []
for s in segs:
    sw = [(x if x is not None else s['a'], k, arg) for x, k, arg in s['shots']]
    for j, (src_t, kind, arg) in enumerate(sw):
        r0 = s['t0'] + (src_t - s['a'])
        r1 = s['t0'] + (sw[j + 1][0] - s['a']) if j + 1 < len(sw) else s['t1']
        r0, r1 = round(r0 * FPS) / FPS, round(r1 * FPS) / FPS
        nfr = int(round((r1 - r0) * FPS)); dur = nfr / FPS
        if kind == 'broll':
            b0, b1, cx = BROLL[arg]
            speed = min(1.0, (b1 - b0) / dur)
            ss, span = b0, dur * speed
            vf = f'crop=608:1080:{cx}:0,scale=1080:1920:flags=lanczos,eq=contrast=1.05:saturation=1.08,setpts=(PTS-STARTPTS)/{speed:.4f}'
        elif kind == 'cam':
            x, y, w, h = TILES[s['spk']]
            ss, span = src_t, dur
            vf = f'crop={w}:{h}:{x}:{y},scale=1080:604:flags=lanczos,unsharp=5:5:0.7:3:3:0,eq=contrast=1.04:saturation=1.06,pad=1080:1920:0:0:black'
        else:  # grid
            ss, span = src_t, dur
            vf = 'crop=686:604:676:340,scale=1080:951:flags=lanczos,unsharp=3:3:0.4,pad=1080:1920:0:0:black'
        f = f'build/clip_{len(clips):02d}.mp4'
        run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{ss:.3f}', '-t', f'{span + 0.2:.3f}', '-i', SRC, '-an',
             '-vf', vf + f',fps={FPS},trim=end_frame={nfr},setpts=PTS-STARTPTS', '-frames:v', str(nfr),
             '-c:v', 'libx264', '-crf', '14', '-g', '1', '-pix_fmt', 'yuv420p', f])
        clips.append(f)
        shots_out.append(dict(t0=r0, t1=r1, kind=kind, arg=arg, spk=s['spk'], name=NAMES[s['spk']], seg=s['i']))
with open('build/concat.txt', 'w') as fh:
    fh.writelines(f"file '{os.path.basename(c)}'\n" for c in clips)
run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', 'build/concat.txt', '-c', 'copy', 'base.mp4'])

# ---- dialogue
total = int(END * SR)
dia = np.zeros((total, 2), np.float32)
fade = int(0.012 * SR)
for s in segs:
    x = load(s['a'], s['b']).copy()
    x[:fade] *= np.linspace(0, 1, fade)[:, None]; x[-fade:] *= np.linspace(1, 0, fade)[:, None]
    o = int(s['t0'] * SR); dia[o:o + len(x)] += x[:total - o]
sf.write('build/dialogue.wav', dia, SR)

# ---- music: [LOOP_A..LOOP_B] x N, then LOOP_B..STING_END (logo sting), equal-power 25 ms splices
m, msr = sf.read('ref/stems/htdemucs/intro/no_vocals.wav', dtype='float32'); assert msr == SR
cut = lambda a, b: m[int(a * SR):int(b * SR)]
parts = [cut(S0, LOOP_B)] + [cut(LOOP_A, LOOP_B)] * (N_LOOPS - 1) + [cut(LOOP_B, STING_END)]
xf = int(0.025 * SR); mus = parts[0].copy()
for p in parts[1:]:
    w = np.linspace(0, np.pi / 2, xf)[:, None]
    tail = mus[-xf:] * np.cos(w) + p[:xf] * np.sin(w)
    mus = np.concatenate([mus[:-xf], tail, p[xf:]])
mus = np.pad(mus, ((0, max(0, total - len(mus))), (0, 0)))[:total]
tail_n = int(1.2 * SR); mus[-tail_n:] *= np.linspace(1, 0, tail_n)[:, None]
sf.write('build/music.wav', mus, SR)

# ---- captions: map authored words to transcript words (in order) inside each segment
norm = lambda w: re.sub(r"[^a-z0-9]", '', w.lower().replace('’', "'"))
groups = []; cur = None
for s in segs:
    tw = [w for w in WORDS if s['a'] - 0.05 <= w['s'] < s['b']]
    toks = s['cap'].split()
    wi = 0; line = None
    for tok in toks:
        if tok == '//':
            cur = {'lines': [[]]}; groups.append(cur); continue
        if tok == '/':
            if cur is None: cur = {'lines': [[]]}; groups.append(cur)
            if cur['lines'][-1]: cur['lines'].append([])
            continue
        if cur is None: cur = {'lines': [[]]}; groups.append(cur)
        text, _, sty = tok.partition('~')
        while wi < len(tw) and norm(tw[wi]['w']) != norm(text):
            print(f'  skip transcript word {tw[wi]["w"]!r} (seg {s["i"]}, want {text})'); wi += 1
        assert wi < len(tw), f'caption word {text} not found in seg {s["i"]}'
        rt = s['t0'] + (tw[wi]['s'] - s['a'])
        cur['lines'][-1].append({'w': text, 's': sty or 's', 't': round(max(rt, s['t0']), 3)}); wi += 1
for g in groups:
    g['t'] = g['lines'][0][0]['t']
for k, g in enumerate(groups):
    g['end'] = groups[k + 1]['t'] if k + 1 < len(groups) else LOGO_T - 0.3

json.dump(dict(fps=FPS, duration=round(END, 3), logo=round(LOGO_T, 3), shots=shots_out, groups=groups,
               segs=[{k: s[k] for k in ('t0', 't1', 'a', 'b', 'spk')} for s in segs]),
          open('timeline.json', 'w'), indent=1)
print(f'{len(clips)} shots, {len(groups)} caption groups -> base.mp4, build/dialogue.wav, build/music.wav, timeline.json')
