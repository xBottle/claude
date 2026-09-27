#!/usr/bin/env python3
"""Превью пресетов CRT Pro на реальном ядре: CRTCore (из build_fuse) компилируется gcc и
запускается на CPU. Цепочка как в эффекте: проход 0 → свечение → ореол трубки → проход 1.
Сцена: store_assets/scene.png (кадр заказчика; scene_eye.png — глаз, на потом). Результат: icons/preset_N.png,
store_assets/cover_bg.png, effect/CRT Pro v2.png.
Запуск: python3 render_previews.py
"""
import math, os, re, subprocess, tempfile, importlib.util
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location("b", os.path.join(HERE, "build_crt_pro_2.py"))
b = importlib.util.module_from_spec(sp); sp.loader.exec_module(b)
b.SHARE_MODE = True
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
#define _powf powf
#define _sqrtf sqrtf
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
static Img load(const char*fn,int W,int H){Img s={W,H,malloc(W*H*16)}; FILE*f=fopen(fn,"rb"); if(fread(s.d,4,W*H*4,f)){} fclose(f); return s;}
int main(int argc,char**argv){ int W=atoi(argv[1]),H=atoi(argv[2]);
 Img s=load(argv[3],W,H), o=load(argv[4],W,H); Img d={W,H,malloc(W*H*16)}; CRTParams P; memset(&P,0,sizeof P);
 FILE*pf=fopen(argv[5],"r"); char k[64]; float v; while(fscanf(pf,"%63s %f",k,&v)==2){ __ASSIGN__ } fclose(pf);
 for(GY=0;GY<H;GY++)for(GX=0;GX<W;GX++) CRTKernel(&P,&s,&o,&s,&d);
 FILE*f=fopen(argv[6],"wb"); fwrite(d.d,4,W*H*4,f); fclose(f); return 0;}
'''


def compile_kernel(tmp):
    fuse = b.build_fuse()
    params = re.search(r'CRTParams = \[\[(.*?)\]\]', fuse, re.S).group(1)
    kern = re.search(r'CRTKernel = \[\[(.*?)\]\]', fuse, re.S).group(1)
    names = re.findall(r'float (\w+);', params)
    assign = " ".join(f'if(!strcmp(k,"{n}")) P.{n}=v;' for n in names)
    src = HDR + "typedef struct {" + params + "} CRTParams;\n" + kern + MAIN.replace("__ASSIGN__", assign)
    c, exe = os.path.join(tmp, "k.c"), os.path.join(tmp, "k")
    open(c, "w").write(src)
    subprocess.run(["gcc", "-O2", "-o", exe, c, "-lm"], check=True)
    return exe


def blur(a, r):
    """Быстрое размытие (3 прохода box) — замена Fast Gaussian."""
    r = int(max(0, r))
    if r < 1:
        return a
    out = a.copy()
    for _ in range(3):
        for ax in (0, 1):
            c = np.cumsum(np.pad(out, [(r + 1, r) if i == ax else (0, 0) for i in range(3)], mode="edge"), axis=ax)
            if ax == 0:
                out = (c[2 * r + 1:] - c[:-2 * r - 1]) / (2 * r + 1)
            else:
                out = (c[:, 2 * r + 1:] - c[:, :-2 * r - 1]) / (2 * r + 1)
    return out


def scene():
    im = Image.open(os.path.join(HERE, "store_assets", "scene.png")).convert("RGB").resize((W, H), Image.LANCZOS)
    a = np.asarray(im.transpose(Image.FLIP_TOP_BOTTOM), dtype=np.float32) / 255
    return np.concatenate([a, np.ones((H, W, 1), np.float32)], 2)


def run(exe, tmp, stage, src, org, P):
    fs, fo, fp, fd = (os.path.join(tmp, n) for n in ("s.bin", "o.bin", "p.txt", "d.bin"))
    src.astype(np.float32).tofile(fs); org.astype(np.float32).tofile(fo)
    with open(fp, "w") as f:
        for k, v in P.items():
            f.write(f"{k} {float(v)}\n")
        f.write(f"stage {stage}\n")
    subprocess.run([exe, str(W), str(H), fs, fo, fp, fd], check=True)
    return np.fromfile(fd, np.float32).reshape(H, W, 4)


def render(exe, tmp, idx, t=10):
    V = dict(b.DEFAULTS); V.update(b.PRESETS[idx])
    P = dict(V); P.update(w=W, h=H, hasPrev=0, demo=0, shakeU=0, shakeV=0)
    cell = max(1.5, 4 * V["PixSize"] * ((H / 1080) if V["PixScaleRes"] > 0.5 else 1))
    P["cell"] = cell
    P["period"] = cell if V["ScanLink"] > 0.5 else V["ScanPeriod"]
    fs = V["FlickSpeed"]
    P["flickN"] = V["FlickSmooth"] * (0.5 + 0.5 * math.sin(t * fs * 0.9) * math.sin(t * fs * 0.37 + 1.3)) + \
        (1 - V["FlickSmooth"]) * ((math.sin(math.floor(t * fs) * 12.9898 + 0.7) * 43758.5453) % 1)
    d = -1 if V["BandReverse"] > 0.5 else 1
    P["bandY"] = (1 + V["BandHeight"]) * ((t * V["BandSpeed"] * d / 24) % 1) - V["BandHeight"] / 2
    P["seed"] = math.floor(t * V["NoiseSpeed"])
    src = scene()
    k = H / 1080  # размеры нод Fusion заданы для 1080p
    a = run(exe, tmp, 0, src, src, P)
    if V["GlowOn"] > 0.5:  # SoftGlow: порог → размытие → сложение
        g = np.clip(a[:, :, :3] - V["GlowThreshold"], 0, None)
        a[:, :, :3] += blur(g, V["GlowSize"] * 0.6 * k) * V["GlowGain"] * 0.5
    if V["TubeOn"] > 0.5:  # ореол трубки: размытие × цвет, экраном
        tint = np.array([V["TubeColorRed"], V["TubeColorGreen"], V["TubeColorBlue"]], np.float32)
        tb = np.clip(blur(a[:, :, :3], V["TubeSize"] * 0.35 * k) * tint, 0, 1)
        base = np.clip(a[:, :, :3], 0, 1)
        scr = 1 - (1 - base) * (1 - tb)
        a[:, :, :3] = a[:, :, :3] + (scr - base) * V["TubeAmount"]
    o = run(exe, tmp, 1, a, src, P)[:, :, :3]
    return Image.fromarray((np.clip(o, 0, 1) * 255).astype(np.uint8)).transpose(Image.FLIP_TOP_BOTTOM)


def main():
    global W, H
    tmp = tempfile.mkdtemp(prefix="crt-")
    exe = compile_kernel(tmp)
    for i in range(len(b.PRESET_NAMES)):
        render(exe, tmp, i).resize((320, 180), Image.LANCZOS).save(os.path.join(HERE, "icons", f"preset_{i}.png"))
    W, H = 1920, 1080  # фон обложки — в полном размере
    render(exe, tmp, 1).save(os.path.join(HERE, "store_assets", "cover_bg.png"))
    Image.open(os.path.join(HERE, "store_assets", "cover_bg.png")).resize((104, 58), Image.LANCZOS).save(
        os.path.join(HERE, "effect", "CRT Pro v2.png"))
    print("превью:", len(b.PRESET_NAMES))


if __name__ == "__main__":
    main()
