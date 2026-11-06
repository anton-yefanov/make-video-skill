import json, sys
from faster_whisper import WhisperModel
m = WhisperModel('small.en', device='cpu', compute_type='int8')
import soundfile as sf
audio, _sr = sf.read(sys.argv[1], dtype="float32")
segs, _ = m.transcribe(audio, word_timestamps=True, vad_filter=True)
out = []
with open(sys.argv[3], 'w') as txt:
    for s in segs:
        out.append({'start': s.start, 'end': s.end, 'text': s.text, 'words': [{'w': w.word, 's': w.start, 'e': w.end} for w in s.words]})
        txt.write(f"[{s.start:7.1f}] {s.text.strip()}\n"); txt.flush()
json.dump(out, open(sys.argv[2], 'w'))
