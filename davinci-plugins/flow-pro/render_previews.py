#!/usr/bin/env python3
"""Превью Flow Pro на реальном ядре: Lua-часть FlowCore.fuse (lua5.1 + заглушки Fusion) считает
параметры кадра, GPU-часть компилируется gcc и рендерит кадр на CPU. Поверх превью — график кривой
скорости. Также рисует иконки кривых для окна, шапку окна и cover_bg.png.
Запуск: python3 render_previews.py
"""
import os, re, subprocess, sys, tempfile, importlib.util
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import storyverse_style as SV  # noqa: E402
sp = importlib.util.spec_from_file_location("b", os.path.join(HERE, "build_flow_pro.py"))
b = importlib.util.module_from_spec(sp); sp.loader.exec_module(b)
RED = (201, 53, 43)
CLIP = 48          # длина тестового клипа, кадров

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
int main(int argc,char**argv){ int W=atoi(argv[1]),H=atoi(argv[2]);
 Img s={W,H,malloc(W*H*16)}; FILE*f=fopen(argv[3],"rb"); if(fread(s.d,4,W*H*4,f)){} fclose(f);
 Img o={W,H,malloc(W*H*16)}; FlowParams P; memset(&P,0,sizeof P);
 FILE*pf=fopen(argv[4],"r"); char k[64]; float v; while(fscanf(pf,"%63s %f",k,&v)==2){ __ASSIGN__ } fclose(pf);
 for(GY=0;GY<H;GY++)for(GX=0;GX<W;GX++) FlowKernel(&P,&s,&s,&s,&s,&s,&o);
 f=fopen(argv[5],"wb"); fwrite(o.d,4,W*H*4,f); fclose(f); return 0;}
'''

LUA_DUMP = r'''
FuRegisterClass = function() end
CT_Tool = 1
TEX_FILTER_MODE_LINEAR, TEX_ADDRESS_MODE_CLAMP, TEX_NORMALIZED_COORDS_TRUE = 1, 1, 1
local W, H, OUT, TIME, CLIP = tonumber(arg[1]), tonumber(arg[2]), arg[3], tonumber(arg[4]), tonumber(arg[5])
local vals = {}
local function img() return { Width = W, Height = H } end
Image = img
self = { AddInput = function(_, name, id, o) local inp = { id = id, def = o and o.INP_Default or 0 }
    inp.GetValue = function(me) if me.id == "Input" or me.id == "Original" then return img() end
      local v = vals[me.id]; if v == nil then v = me.def end return { Value = v } end
    inp.GetSource = function() return img() end
    return inp end,
  AddOutput = function() return { Set = function() end } end,
  Comp = { GetAttrs = function() return { COMPN_RenderStart = 0, COMPN_RenderEnd = CLIP - 1 } end,
           GetPrefs = function() return 24 end } }
DVIPComputeNode = function() local P = {}
  return { GetParamBlock = function() return P end, SetParamBlock = function() end, AddSampler = function() end,
    AddInput = function() end, AddOutput = function() end, GetErrorLog = function() end,
    RunSession = function() local f = io.open(OUT, "w")
      for k, v in pairs(P) do if type(v) == "number" then f:write(k, " ", v, "\n") end end f:close() return true end } end
dump = print
dofile(arg[6])
Create()
local D = dofile(arg[7])
for k, v in pairs(D.PRESETS[tonumber(arg[8])] or {}) do vals[k] = v end
Process({ Time = TIME, GetFlags = function() return 0 end })
'''


def compile_kernel(tmp):
    fuse = open(os.path.join(HERE, "FlowCore.fuse"), encoding="utf-8").read()
    params = re.search(r'FlowParams = \[\[(.*?)\]\]', fuse, re.S).group(1)
    kern = re.search(r'FlowKernel = \[\[(.*?)\]\]', fuse, re.S).group(1)
    names = re.findall(r'float (\w+);', params)
    assign = " ".join(f'if(!strcmp(k,"{n}")) P.{n}=v;' for n in names)
    src = HDR + "typedef struct {" + params + "} FlowParams;\n" + kern + MAIN.replace("__ASSIGN__", assign)
    c, exe = os.path.join(tmp, "k.c"), os.path.join(tmp, "k")
    open(c, "w").write(src)
    subprocess.run(["gcc", "-O2", "-o", exe, c, "-lm"], check=True)
    open(os.path.join(tmp, "dump.lua"), "w").write(LUA_DUMP)
    return exe


def glow(im, thr, gain, size):
    """Грубая замена SoftGlow для превью."""
    a = np.asarray(im, np.float32) / 255
    g = Image.fromarray((np.clip(a - thr, 0, 1) * 255).astype(np.uint8)).filter(
        __import__("PIL.ImageFilter", fromlist=["x"]).GaussianBlur(max(1, size * im.size[1] / 1080)))
    a = np.clip(a + np.asarray(g, np.float32) / 255 * gain * 0.6, 0, 1)
    return Image.fromarray((a * 255).astype(np.uint8))


def render(exe, tmp, preset, t, W, H):
    scene = Image.open(os.path.join(HERE, "store_assets", "scene.png")).convert("RGB").resize((W, H), Image.LANCZOS)
    a = np.asarray(scene.transpose(Image.FLIP_TOP_BOTTOM), np.float32) / 255
    rgba = np.concatenate([a, np.ones((H, W, 1), np.float32)], 2)
    fin, fp, fo = (os.path.join(tmp, n) for n in ("in.bin", "p.txt", "out.bin"))
    rgba.tofile(fin)
    subprocess.run(["lua5.1", os.path.join(tmp, "dump.lua"), str(W), str(H), fp, str(t), str(CLIP),
                    os.path.join(HERE, "FlowCore.fuse"), os.path.join(HERE, "flow_pro_data.lua"), str(preset)],
                   check=True, cwd=HERE)
    subprocess.run([exe, str(W), str(H), fin, fp, fo], check=True)
    o = np.fromfile(fo, np.float32).reshape(H, W, 4)[:, :, :3]
    im = Image.fromarray((np.clip(o, 0, 1) * 255).astype(np.uint8)).transpose(Image.FLIP_TOP_BOTTOM)
    V = dict(b.DEFAULTS); V.update(b.PRESETS[preset])
    if V["GlowOn"] > 0.5:
        im = glow(im, V["GlowThreshold"], V["GlowGain"], V["GlowSize"])
    return im, V


def draw_curve(d, box, T, k, a=1.0, h=0.35, color=RED, width=3):
    x0, y0, x1, y1 = box
    pts = [(x0 + (x1 - x0) * i / 60, y1 - (y1 - y0) * b.curve_py(i / 60, T, k, a, h)) for i in range(61)]
    d.line(pts, fill=color, width=width, joint="curve")


def overlay_curve(im, V):
    if V["RampOn"] < 0.5:
        return im
    im = im.copy()
    d = ImageDraw.Draw(im, "RGBA")
    W, H = im.size
    bw, bh = int(W * 0.2), int(H * 0.2)
    x0, y0 = W - bw - int(W * 0.03), H - bh - int(H * 0.05)
    d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=int(bh * 0.12), fill=(20, 20, 20, 170))
    pad = int(bh * 0.14)
    d.line([(x0 + pad, y0 + bh - pad), (x0 + bw - pad, y0 + pad)], fill=(120, 120, 118, 200), width=1)
    draw_curve(d, (x0 + pad, y0 + pad, x0 + bw - pad, y0 + bh - pad), V["RampType"], 1 + V["RampStrength"] * 4,
               V["RampAmount"], V["HoldPoint"], width=max(2, H // 180))
    return im


def curve_icons():
    for T in range(len(b.CURVES)):
        im = Image.new("RGB", (96, 54), (37, 37, 36))
        d = ImageDraw.Draw(im)
        for i in range(1, 4):
            d.line([(8 + 80 * i / 4, 6), (8 + 80 * i / 4, 48)], fill=(50, 50, 48))
        d.line([(8, 48), (88, 6)], fill=(70, 70, 67))
        draw_curve(d, (8, 6, 88, 48), T, 3.4, width=3)
        im.save(os.path.join(HERE, "icons", f"curve_{T}.png"))


TIMES = {8: 1, 9: 1, 11: 44, 6: 3, 13: 3}


def main():
    tmp = tempfile.mkdtemp(prefix="flow-")
    exe = compile_kernel(tmp)
    os.makedirs(os.path.join(HERE, "icons"), exist_ok=True)
    for i in range(len(b.PRESET_NAMES)):
        im, V = render(exe, tmp, i, TIMES.get(i, 6), 640, 360)
        overlay_curve(im, V).resize((320, 180), Image.LANCZOS).save(os.path.join(HERE, "icons", f"preset_{i}.png"))
    im, V = render(exe, tmp, 0, 6, 1920, 1080)
    im.save(os.path.join(HERE, "store_assets", "cover_bg.png"))
    curve_icons()
    SV.window_title("FLOW PRO", "GPU · speed ramp · camera").save(os.path.join(HERE, "icons", "title.png"))
    Image.open(os.path.join(os.path.dirname(HERE), "crt-2.0", "icons", "preset_own.png")).save(
        os.path.join(HERE, "icons", "preset_own.png"))
    print("превью:", len(b.PRESET_NAMES))


if __name__ == "__main__":
    main()
