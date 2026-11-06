"""Audio analysis so Claude can "hear" a track: tempo, beats, onsets, energy curve,
sections, key, brightness, and optional timestamped lyrics (faster-whisper).

Usage: .venv/bin/python -I analyze_audio.py song.mp3 analysis.json [--lyrics] [--start S --dur D]
"""
import argparse, json
import numpy as np
import librosa

KEYS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

def key_of(chroma):
    c = chroma.mean(axis=1)
    best = max(((np.corrcoef(np.roll(p, k), c)[0, 1], f"{KEYS[k]} {m}")
                for p, m in ((MAJ, 'major'), (MIN, 'minor')) for k in range(12)))
    return best[1]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('audio'); ap.add_argument('out')
    ap.add_argument('--lyrics', action='store_true')
    ap.add_argument('--start', type=float, default=0.0); ap.add_argument('--dur', type=float)
    a = ap.parse_args()

    y, sr = librosa.load(a.audio, sr=22050, mono=True, offset=a.start, duration=a.dur)
    dur = len(y) / sr
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units='time')
    onsets = librosa.onset.onset_detect(y=y, sr=sr, units='time')

    hop = 512
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    cent = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)
    # energy/brightness sampled every 0.25s, normalized 0..1 for direct use in animation
    grid = np.arange(0, dur, 0.25)
    norm = lambda v: (v - v.min()) / (np.ptp(v) or 1)
    energy = np.interp(grid, times, norm(rms))
    bright = np.interp(grid, times, norm(cent))

    # sections: agglomerative clustering on beat-synced chroma+mfcc
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, hop_length=hop, n_mfcc=13)
    feat = np.vstack([librosa.util.normalize(chroma), librosa.util.normalize(mfcc)])
    k = int(np.clip(dur // 12, 2, 10))
    bounds = librosa.segment.agglomerative(feat, k)
    bt = list(librosa.frames_to_time(bounds, sr=sr, hop_length=hop)) + [dur]
    sections = []
    for s, e in zip(bt[:-1], bt[1:]):
        m = (times >= s) & (times < e)
        sections.append({'start': round(float(s), 2), 'end': round(float(e), 2),
                         'energy': round(float(norm(rms)[m].mean()) if m.any() else 0, 3)})

    # harmonic vs percussive balance hints at instrumentation
    h, p = librosa.effects.hpss(y)
    res = {
        'file': a.audio, 'offset': a.start, 'duration': round(dur, 2),
        'tempo_bpm': round(float(np.atleast_1d(tempo)[0]), 1),
        'key': key_of(chroma),
        'percussive_ratio': round(float(np.abs(p).mean() / (np.abs(h).mean() + np.abs(p).mean())), 3),
        'beats': [round(float(b), 3) for b in beats],
        'downbeats_guess': [round(float(b), 3) for b in beats[::4]],
        'onsets': [round(float(o), 3) for o in onsets],
        'sections': sections,
        'curve_step_s': 0.25,
        'energy_curve': [round(float(v), 3) for v in energy],
        'brightness_curve': [round(float(v), 3) for v in bright],
    }

    if a.lyrics:
        from faster_whisper import WhisperModel
        model = WhisperModel('small', device='cpu', compute_type='int8')
        segs, info = model.transcribe(librosa.load(a.audio, sr=16000)[0], word_timestamps=True, vad_filter=True,
                                      clip_timestamps=[a.start, a.start + dur] if a.dur else '0')
        res['language'] = info.language
        res['lyrics'] = [{'start': round(s.start - a.start, 2), 'end': round(s.end - a.start, 2), 'text': s.text.strip(),
                          'words': [{'w': w.word.strip(), 't': round(w.start - a.start, 2)} for w in (s.words or [])]}
                         for s in segs]

    json.dump(res, open(a.out, 'w'), indent=1)
    print(f"{a.out}: {res['duration']}s, {res['tempo_bpm']} bpm, {res['key']}, "
          f"{len(res['beats'])} beats, {len(sections)} sections, lyrics={'lyrics' in res}")

if __name__ == '__main__':
    main()
