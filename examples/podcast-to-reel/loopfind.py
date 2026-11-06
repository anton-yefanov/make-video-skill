import librosa, numpy as np, json
y, sr = librosa.load('ref/stems/htdemucs/intro/no_vocals.wav', sr=22050)
db=json.load(open('ref/intro_music.json'))['downbeats_guess']
def feat(t, dur=1.6):
    s=y[int(t*sr):int((t+dur)*sr)]
    c=librosa.feature.chroma_cqt(y=s,sr=sr); m=librosa.feature.mfcc(y=s,sr=sr,n_mfcc=13)
    return np.concatenate([c.mean(1), m.mean(1)/50, [np.sqrt((s**2).mean())*20]])
F={d:feat(d) for d in db if d<20.9}
res=[]
for a in F:
    for b in F:
        if b-a>6:
            res.append((float(np.linalg.norm(F[a]-F[b])),a,b))
for r in sorted(res)[:10]: print(r)
for d in db: 
    s=y[int(d*sr):int((d+1.6)*sr)]; print(d, round(float(20*np.log10(np.sqrt((s**2).mean())+1e-9)),1))
