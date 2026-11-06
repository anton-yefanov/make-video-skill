import librosa, numpy as np
y, sr = librosa.load('ref/full16k.wav', sr=16000)
def emb(a,b):
    s=y[int(a*sr):int(b*sr)]
    m=librosa.feature.mfcc(y=s,sr=sr,n_mfcc=24)[1:]
    return np.concatenate([m.mean(1), m.std(1)])
refs={'nick':[(868.5,878),(1397,1404.5),(30,57)],'dan':[(879.4,890),(1290.4,1312)],'axel':[(822.5,849),(1168,1200)]}
R={k:np.mean([emb(a,b) for a,b in v],0) for k,v in refs.items()}
allv=np.stack(list(R.values())); mu=allv.mean(0); sd=np.abs(allv).std(0)+1e-6
def score(a,b):
    e=emb(a,b)
    return {k:round(float(-np.linalg.norm((e-v))),1) for k,v in R.items()}
for a,b,lab in [(912.3,913.7,'S2a hijack all in'),(914.9,915.9,'S2 what do we call'),(917.2,919.8,'S2b call any two'),(920.1,921.6,'any two close'),(930.7,932.5,'oh yeah almost'),(934.3,939.3,'S3 pause'),(1042,1045.4,'S4a'),(1045.7,1051.9,'S4b'),(1052.9,1058.8,'S4 both together'),(1059.4,1065,'S4c'),(844.3,849.5,'axel mistake'),(850.3,860.2,'S5 over and over'),(1497,1504.2,'S6'),(1464.2,1470,'it is that pivoting')]:
    print(lab, score(a,b))
