#!/usr/bin/env python3
"""Превью пресетов VHS Pro: то же ядро (из VHSCore.fuse), скомпилированное gcc и
запущенное на CPU по тестовой сцене. Результат: icons/preset_N.png (320x180).
Запуск: python3 render_previews.py
"""
import math, os, re, subprocess, tempfile, importlib.util
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location("b", os.path.join(HERE, "build_vhs_pro.py"))
b = importlib.util.module_from_spec(sp); sp.loader.exec_module(b)
CHARS = open(os.path.join(HERE, "charset.txt")).read()
MONTHS = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()
W, H = 960, 540

HDR = r'''
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct {float x,y,z,w;} float4;
static float4 make_float4(float a,float b,float c,float d){float4 r={a,b,c,d};return r;}
typedef struct {int w,h; float *d;} Img;
#define __DEVICE__ static
#define __KERNEL__ static
#define __CONSTANTREF__ const
#define __TEXTURE2D__ const Img*
#define __TEXTURE2D_WRITE__ Img*
#define _fminf fminf
#define _fmaxf fmaxf
#define _floor floorf
#define _sinf sinf
#define _cosf cosf
#define _fabs fabsf
static int GX,GY;
#define DEFINE_KERNEL_ITERATORS_XY(a,b) int a=GX, b=GY;
static float4 px(const Img*t,int x,int y){ if(x<0)x=0; if(y<0)y=0; if(x>=t->w)x=t->w-1; if(y>=t->h)y=t->h-1; float*p=t->d+4*(y*t->w+x); return make_float4(p[0],p[1],p[2],p[3]);}
static float4 _tex2DVecN(const Img*t,float u,float v,int m){ float x=u*t->w-0.5f,y=v*t->h-0.5f; int x0=floorf(x),y0=floorf(y); float fx=x-x0,fy=y-y0;
 float4 a=px(t,x0,y0),b=px(t,x0+1,y0),c=px(t,x0,y0+1),d=px(t,x0+1,y0+1); float4 r;
 r.x=(a.x*(1-fx)+b.x*fx)*(1-fy)+(c.x*(1-fx)+d.x*fx)*fy; r.y=(a.y*(1-fx)+b.y*fx)*(1-fy)+(c.y*(1-fx)+d.y*fx)*fy;
 r.z=(a.z*(1-fx)+b.z*fx)*(1-fy)+(c.z*(1-fx)+d.z*fx)*fy; r.w=(a.w*(1-fx)+b.w*fx)*(1-fy)+(c.w*(1-fx)+d.w*fx)*fy; return r;}
static void _tex2DVec4Write(Img*t,int x,int y,float4 c){float*p=t->d+4*(y*t->w+x);p[0]=c.x;p[1]=c.y;p[2]=c.z;p[3]=c.w;}
'''
MAIN = r'''
int main(int argc,char**argv){ int W,H; FILE*f=fopen(argv[1],"rb"); if(fscanf(f,"%d %d\n",&W,&H)!=2) return 1;
 Img s={W,H,malloc(W*H*16)}; if(fread(s.d,4,W*H*4,f)){} fclose(f);
 Img o={W,H,malloc(W*H*16)}; VHSParams P; memset(&P,0,sizeof P);
 FILE*pf=fopen(argv[2],"r"); char k[64]; float v; while(fscanf(pf,"%63s %f",k,&v)==2){ __ASSIGN__ } fclose(pf);
 for(GY=0;GY<H;GY++)for(GX=0;GX<W;GX++) VHSKernel(&P,&s,&s,&o);
 f=fopen(argv[3],"wb"); fwrite(o.d,4,W*H*4,f); fclose(f); return 0;}
'''


def compile_kernel(tmp):
    fuse = b.build_fuse()
    params = re.search(r'VHSParams = \[\[(.*?)\]\]', fuse, re.S).group(1)
    kern = re.search(r'VHSKernel = \[\[(.*?)\]\]', fuse, re.S).group(1)
    names = re.findall(r'float (\w+);', params)
    assign = " ".join(f'if(!strcmp(k,"{n}")) P.{n}=v;' for n in names)
    src = HDR + "typedef struct {" + params + "} VHSParams;\n" + kern + MAIN.replace("__ASSIGN__", assign)
    c = os.path.join(tmp, "k.c"); exe = os.path.join(tmp, "k")
    open(c, "w").write(src)
    subprocess.run(["gcc", "-O2", "-o", exe, c, "-lm"], check=True)
    return exe


def scene():
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H; d.line([(0, y), (W, y)], fill=(int(40 + 180 * t), int(90 + 100 * t), int(200 - 60 * t)))
    d.ellipse([650, 60, 780, 190], fill=(255, 220, 120))
    d.polygon([(0, 380), (250, 260), (520, 380), (760, 280), (960, 370), (960, 540), (0, 540)], fill=(40, 120, 60))
    d.rectangle([120, 300, 300, 470], fill=(200, 40, 50)); d.rectangle([160, 340, 220, 470], fill=(250, 240, 220))
    d.rectangle([520, 330, 600, 500], fill=(30, 60, 160)); d.ellipse([540, 280, 580, 330], fill=(240, 190, 150))
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64)
    d.text((330, 120), "SUMMER", font=f, fill=(255, 255, 255))
    return im


def h1(x): return (math.sin(x * 12.9898 + 0.7) * 43758.5453) % 1


def pack(s):
    out = [0] * 6
    for i, ch in enumerate(s.upper()[:18]):
        c = CHARS.find(ch); out[i // 3] += (0 if c < 0 else c) * 64 ** (i % 3)
    return out


def params(V, t, fps=24):
    """Копия расчётов из Process() в VHSCore.fuse (на один кадр)."""
    S = math.sin
    p = dict(V); sec = t / fps; s = H / 1080 if V['ScaleRes'] > 0.5 else 1
    p.update(w=W, h=H, s=s, sec=sec, seed=t % 997, camX=0, camY=0, camR=0, camS=1, expo=1)
    if V['CamOn'] > 0.5:
        tt = sec * V['CamSpeed']
        nx = .5*S(tt*1.13+.3)+.3*S(tt*2.71+1.7)+.2*S(tt*4.97+4.1); ny = .5*S(tt*.97+2.2)+.3*S(tt*2.39+.4)+.2*S(tt*5.31+3.3)
        nr = .6*S(tt*.87+2.1)+.4*S(tt*2.3+.4); tx = .5*S(tt*23.1+.5)+.5*S(tt*31.7+2.9); ty = .5*S(tt*19.3+1.4)+.5*S(tt*29.9+.2)
        st = sec*V['CamSpeed']*3.3; wy = abs(S(st))-.63; wx = S(st*.5)
        p['camX'] = V['CamShake']*.01*nx+V['CamTremor']*.002*tx+V['CamWalk']*.004*wx
        p['camY'] = V['CamShake']*.01*ny+V['CamTremor']*.002*ty+V['CamWalk']*.012*wy
        p['camR'] = math.radians(V['CamRot']*nr+V['CamTremor']*.1*tx)
        zoom = 1+V['CamZoom']*.08*(.5+.5*S(tt*.41)); fill = 1
        if V['CamFill'] > .5:
            ms = V['CamShake']*.01+V['CamTremor']*.002+V['CamWalk']*.012
            fill = 1+2.2*ms+math.sin(math.radians(V['CamRot']+V['CamTremor']*.1))*(W/H+1)
        p['camS'] = zoom*fill
        p['expo'] = 1+V['ExpoPump']*.25*S(sec*.7*V['CamSpeed'])*S(sec*.23+1)
    jr = h1(t+.37)
    p['jumpY'] = ((h1(t+5.1)-.5)*2*V['FrameJitter']*s if jr > .9 else (h1(t+9.3)-.5)*.3*V['FrameJitter']*s) if V['TrackOn'] > .5 else 0
    p['creaseY'] = -1e5
    if V['CreaseOn'] > .5:
        tr = (sec % max(V['CreaseEvery'], .1))*V['CreaseSpeed']
        if tr < 1.3: p['creaseY'] = H*(1.15-tr)
    p.update(bar0=-10, bar1=-10, bar2=-10, barH=0, skew=0); mode = int(V['Mode']+.5)
    if mode == 1: p.update(bar0=.28, bar1=.74, barH=.035)
    elif mode >= 2:
        d = 1 if mode == 2 else -1
        for i in range(3): p[f'bar{i}'] = (sec*.9*d+i/3) % 1
        p['barH'] = .07; p['skew'] = d*V['ModeAmount']
    lines = ["", "", ""]
    if V['OSDOn'] > .5:
        lab = int(V['OSDLabel']+.5)
        if lab == 0: lines[0] = ["PLAY >", "PAUSE |", "REW <<", "FF >>"][min(mode, 3)]
        elif lab == 1: lines[0] = "* REC"
        tot = int(V['Hour'])*3600+int(V['Minute'])*60+int(V['Second'])+(int(sec) if V['ClockRun'] > .5 else 0)
        hh, mm, ss = tot//3600 % 24, tot//60 % 60, tot % 60
        lines[1] = ("%s %2d:%02d:%02d" % ("PM" if hh >= 12 else "AM", (hh % 12) or 12, mm, ss)
                    if V['Clock12'] > .5 else "%02d:%02d:%02d" % (hh, mm, ss))
        mo, dd, y, fmt = int(V['Month']), int(V['Day']), int(V['Year']), int(V['DateFormat']+.5)
        lines[2] = ["%s. %d %d" % (MONTHS[mo-1], dd, y), "%02d.%02d.%d" % (dd, mo, y), "%d. %d.%2d" % (y, mo, dd)][fmt]
    k = 0
    for ln in lines:
        for v in pack(ln): p[f'T{k}'] = v; k += 1
    p['osdPx'] = max(1, math.floor(3*V['OSDSize']*s+.5)); p['osdX'] = V['OSDMargin']*H*1.3
    p['osdTop'] = p['osdBot'] = V['OSDMargin']*H
    if V['Aspect43'] > .5: p['osdX'] += max(0, (W-H*4/3)/2)
    return p


def render(exe, tmp, preset, t):
    V = dict(b.DEFAULTS); V.update(b.PRESETS[preset])
    im = np.asarray(scene().transpose(Image.FLIP_TOP_BOTTOM), dtype=np.float32) / 255
    rgba = np.concatenate([im, np.ones((H, W, 1), np.float32)], 2)
    fin, fp, fo = (os.path.join(tmp, n) for n in ("in.bin", "p.txt", "out.bin"))
    with open(fin, "wb") as f:
        f.write(f"{W} {H}\n".encode()); f.write(rgba.tobytes())
    with open(fp, "w") as f:
        for k, v in params(V, t).items(): f.write(f"{k} {float(v)}\n")
    subprocess.run([exe, fin, fp, fo], check=True)
    o = np.fromfile(fo, np.float32).reshape(H, W, 4)[:, :, :3]
    return Image.fromarray((np.clip(o, 0, 1) * 255).astype(np.uint8)).transpose(Image.FLIP_TOP_BOTTOM)


def main():
    tmp = tempfile.mkdtemp(prefix="vhs-")
    exe = compile_kernel(tmp)
    os.makedirs(os.path.join(HERE, "icons"), exist_ok=True)
    frames = {3: 40, 5: 12, 7: 30, 10: 30, 11: 25}
    for i in range(len(b.PRESET_NAMES)):
        img = render(exe, tmp, i, frames.get(i, 10))
        img.save(os.path.join(HERE, "store_assets", f"full_{i}.png")) if os.path.isdir(os.path.join(HERE, "store_assets")) else None
        img.resize((320, 180), Image.LANCZOS).save(os.path.join(HERE, "icons", f"preset_{i}.png"))
    print("превью:", len(b.PRESET_NAMES))


if __name__ == "__main__":
    main()
