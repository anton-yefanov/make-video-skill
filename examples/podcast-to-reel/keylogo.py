import subprocess, numpy as np, sys
def key(src, dst, w, h):
    raw = subprocess.run(['ffmpeg','-v','error','-i',src,'-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True).stdout
    p = np.frombuffer(raw,np.uint8).reshape(h,w,3).astype(float)
    bg = np.median(np.concatenate([p[:6].reshape(-1,3), p[-6:].reshape(-1,3)]),0)
    d = np.sqrt(((p-bg)**2).sum(2))
    a = np.clip((d-25)/150,0,1)
    col = np.where(a[...,None]>0.01, (p - bg*(1-a[...,None]))/np.maximum(a[...,None],1e-3), 0)
    out = np.dstack([np.clip(col,0,255), a*255]).astype(np.uint8)
    subprocess.run(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgba','-s',f'{w}x{h}','-i','-',dst],input=out.tobytes())
key('assets/logo.png','assets/logo_a.png',600,260)
key('assets/header.png','assets/header_a.png',420,130)
