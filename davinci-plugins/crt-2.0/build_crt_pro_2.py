#!/usr/bin/env python3
"""Генератор эффекта CRT Pro для DaVinci Resolve (Fusion-шаблон для страницы Edit).

Запуск:  python3 build_crt_pro.py            -> собрать файлы в этой папке
         python3 build_crt_pro.py --install  -> ещё и установить в Resolve
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EFFECTS = os.path.expanduser("~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates/Edit/Effects")
LIB = os.path.join(EFFECTS, "Claude", "CRT")  # CRT Pixels + CRT Pro live here
USER_DIR = os.path.expanduser("~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/CRT Pro User Presets")
GROUP = "CRTPro"
FUSCRIPT = "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fuscript"
VALIDATOR = os.path.join(HERE, "validate_crt_pro.lua")
PIXELS_DIR = os.path.join(os.path.dirname(HERE), "CRT Pixels")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))  # корень рабочей папки
SHARE_MODE = False  # в пакете .drfx свои пресеты вшиваются внутрь эффекта


# ------------------------------------------------------------------ Lua helpers
def lnum(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    s = repr(float(v))
    return s[:-2] if s.endswith(".0") else s


def lstr(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t") + '"'


def lua_value(v):
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k} = {lua_value(x)}" for k, x in v.items()) + " }"
    if isinstance(v, str):
        return lstr(v)
    return lnum(v)


# ------------------------------------------------------------------ controls
class C:
    def __init__(self, cid, kind, name, default=0, lo=0, hi=1, amin=None, amax=None,
                 integer=False, options=None, action=None, width=1.0, rgb=None, is_open=False):
        self.id, self.kind, self.name, self.default = cid, kind, name, default
        self.lo, self.hi, self.amin, self.amax = lo, hi, amin, amax
        self.integer, self.options, self.action, self.width = integer, options, action, width
        self.rgb, self.is_open = rgb, is_open
        self.count = 0  # for labels


def slider(cid, name, d, lo, hi, amin, amax, integer=False):
    return C(cid, "slider", name, d, lo, hi, amin, amax, integer=integer)


def check(cid, name, d):
    return C(cid, "check", name, d)


def combo(cid, name, options, d=0):
    return C(cid, "combo", name, d, options=options)


def button(cid, name, action, width=1.0):
    return C(cid, "button", name, action=action, width=width)


def color(cid, name, rgb):
    return C(cid, "color", name, rgb=rgb)


def text(cid, name, d):
    return C(cid, "text", name, d)


PRESET_NAMES = [
    "По умолчанию (как в уроке)", "Классический ТВ", "Аркадный автомат", "Зелёный терминал",
    "Янтарный монитор", "VHS-мечта", "Сломанный телевизор", "Снято на камеру", "Мягкий ретро", "Киберпанк",
]

SECTIONS = [
    ("SecPresets", "Пресеты", True, [
        button("BtnWindow", "Окно пресетов", "window"),
        combo("PresetSel", "Пресет", PRESET_NAMES, 0),
        button("BtnApply", "Применить пресет", "apply"),
        button("BtnSave", "Сохранить мой пресет", "save", 0.5),
        button("BtnLoad", "Загрузить мой пресет", "load", 0.5),
        button("BtnDelete", "Удалить мой пресет", "delete", 0.5),
        button("BtnReset", "Сбросить всё", "reset", 0.5),
        button("BtnCopy", "Скопировать код", "copy", 0.5),
        button("BtnPaste", "Вставить код", "paste", 0.5),
    ]),
    ("SecPixels", "Пиксели", True, [
        check("PixOn", "Пиксельная маска", 1),
        combo("PixPattern", "Узор", ["Прямые", "Со сдвигом", "Апертурная решётка (Trinitron)", "Щелевая маска",
                                     "Теневая маска (триады)", "LCD-сетка", "LED-стена", "Точечная матрица",
                                     "Сетка без цвета", "Только строки"], 0),
        combo("RGBMode", "Режим RGB", ["Настоящий RGB", "Имитация (без цвета)", "Разделение RGB"], 0),
        slider("PixSize", "Размер пикселя", 1, 0.25, 4, 0.05, 32),
        check("PixScaleRes", "Масштабировать с разрешением", 0),
        check("PixDown", "Понижать разрешение", 1),
        check("PixSmoothDown", "Сглаживать при уменьшении", 0),
        slider("PixStrength", "Сила маски", 1, 0, 1, 0, 1),
        slider("PixSoft", "Мягкость пикселя", 0.2, 0, 1, 0, 10),
        check("PixBrightOn", "Компенсация яркости", 1),
        slider("PixBright", "Усиление яркости", 2, 0, 4, 0, 20),
        slider("PixGamma", "Гамма пикселей", 0.635, 0.2, 2, 0.01, 10),
    ]),
    ("SecScan", "Строки развёртки", False, [
        check("ScanOn", "Включить", 0),
        slider("ScanStrength", "Сила", 0.4, 0, 1, 0, 1),
        check("ScanLink", "Шаг = размер пикселя", 1),
        slider("ScanPeriod", "Шаг строк (px)", 4, 2, 32, 1, 256, integer=True),
        slider("ScanBeam", "Толщина луча", 0.6, 0.05, 1, 0.01, 1),
        slider("ScanSoft", "Мягкость строк", 0.5, 0, 3, 0, 20),
    ]),
    ("SecConv", "Сведение лучей (RGB)", False, [
        check("ConvOn", "Включить", 0),
        slider("ConvRX", "Красный по X (px)", 1.5, -10, 10, -1000, 1000),
        slider("ConvRY", "Красный по Y (px)", 0, -10, 10, -1000, 1000),
        slider("ConvBX", "Синий по X (px)", -1.5, -10, 10, -1000, 1000),
        slider("ConvBY", "Синий по Y (px)", 0, -10, 10, -1000, 1000),
    ]),
    ("SecBleed", "Растекание цвета", False, [
        check("BleedOn", "Включить", 0),
        slider("BleedStrength", "Сила", 0.7, 0, 1, 0, 1),
        slider("BleedBlur", "Размытие (px)", 8, 0, 40, 0, 500),
        slider("BleedShift", "Сдвиг вправо (px)", 2, -20, 20, -500, 500),
    ]),
    ("SecShift", "Сдвиг цвета", False, [
        check("ShiftOn", "Включить", 0),
        slider("HueShift", "Оттенок", 0, -180, 180, -1000, 1000),
        slider("SatShift", "Насыщенность", 1, 0, 2, 0, 10),
    ]),
    ("SecRes", "Цветовая глубина", False, [
        check("ColorResOn", "Включить", 0),
        slider("ColorLevels", "Уровней на канал", 16, 2, 64, 2, 1024, integer=True),
    ]),
    ("SecMono", "Монохромный экран", False, [
        check("MonoOn", "Включить", 0),
        slider("MonoAmount", "Сила", 1, 0, 1, 0, 1),
        combo("MonoMode", "Режим", ["Умножение", "Экран", "Наложение", "Затемнение основы"], 0),
        color("MonoColor", "Цвет люминофора", (0.25, 1.0, 0.4)),
        slider("MonoBoost", "Яркость", 1.3, 0, 3, 0, 20),
    ]),
    ("SecIn", "Цвет на входе", False, [
        slider("InGain", "Экспозиция", 1, 0, 4, 0, 100),
        slider("InLift", "Подъём теней", 0, -0.5, 0.5, -5, 5),
        slider("InGamma", "Гамма", 1, 0.2, 3, 0.01, 10),
        slider("InContrast", "Контраст", 0, -1, 1, -5, 5),
        slider("InSat", "Насыщенность", 1, 0, 3, 0, 10),
        slider("BalR", "Баланс: красный", 1, 0, 2, 0, 10),
        slider("BalG", "Баланс: зелёный", 1, 0, 2, 0, 10),
        slider("BalB", "Баланс: синий", 1, 0, 2, 0, 10),
    ]),
    ("SecGlow", "Свечение", False, [
        check("GlowOn", "Включить", 1),
        slider("GlowThreshold", "Порог", 0.1, 0, 1, 0, 1),
        slider("GlowGain", "Сила", 1.5, 0, 5, 0, 50),
        slider("GlowSize", "Размер", 8, 0, 60, 0, 500),
    ]),
    ("SecTube", "Свечение трубки", False, [
        check("TubeOn", "Включить", 0),
        slider("TubeAmount", "Сила", 0.25, 0, 1, 0, 5),
        slider("TubeSize", "Размер", 60, 5, 300, 0, 2000),
        color("TubeColor", "Оттенок", (0.65, 0.8, 1.0)),
    ]),
    ("SecScreen", "Экран", False, [
        check("CurveOn", "Выпуклость экрана", 0),
        slider("CurveAmount", "Сила выпуклости", 0.15, -0.6, 0.6, -3, 3),
        check("VigOn", "Виньетка", 0),
        slider("VigAmount", "Сила виньетки", 0.5, 0, 1, 0, 1),
        slider("VigSize", "Размер виньетки", 1.25, 0.3, 2.5, 0.01, 10),
        slider("VigSoft", "Мягкость виньетки", 0.5, 0, 1, 0, 5),
        check("CornerOn", "Скруглённые углы", 0),
        slider("CornerRadius", "Радиус углов", 0.08, 0, 0.5, 0, 1),
        slider("CornerInset", "Отступ рамки", 0.015, 0, 0.2, 0, 0.5),
        slider("CornerSoft", "Мягкость рамки", 0.004, 0, 0.05, 0, 1),
    ]),
    ("SecFlick", "Мерцание", False, [
        check("FlickOn", "Включить", 0),
        combo("FlickType", "Тип", ["Яркость", "Гамма"], 0),
        slider("FlickAmount", "Сила", 0.08, 0, 1, 0, 1),
        slider("FlickSpeed", "Частота", 1, 0.05, 5, 0.001, 100),
        slider("FlickSmooth", "Плавность", 0.5, 0, 1, 0, 1),
        check("FlickR", "Красный", 1),
        check("FlickG", "Зелёный", 1),
        check("FlickB", "Синий", 1),
    ]),
    ("SecShake", "Тряска", False, [
        check("ShakeOn", "Включить", 0),
        check("ShakeBefore", "До пикселей", 1),
        slider("ShakeX", "Амплитуда X", 0.002, 0, 0.03, 0, 1),
        slider("ShakeY", "Амплитуда Y", 0.002, 0, 0.03, 0, 1),
        slider("ShakeSpeed", "Скорость", 1, 0, 5, 0, 100),
        slider("ShakeJitter", "Дёрганость", 0.3, 0, 1, 0, 1),
        combo("ShakeEdges", "Края", ["Холст", "Повтор", "Дублирование", "Зеркало"], 3),
    ]),
    ("SecBand", "Затвор (бегущая полоса)", False, [
        check("BandOn", "Включить", 0),
        slider("BandStrength", "Сила", 0.25, 0, 1, 0, 5),
        slider("BandGamma", "Гамма полосы", 0, -1, 1, -5, 5),
        slider("BandSpeed", "Скорость", 0.3, 0, 3, 0, 100),
        check("BandReverse", "Обратное направление", 0),
        slider("BandHeight", "Высота", 0.3, 0.01, 1, 0.001, 5),
        slider("BandSoft", "Мягкость", 0.5, 0, 1, 0, 5),
        check("BandDark", "Тёмная полоса", 0),
    ]),
    ("SecNoise", "Плёночное зерно", False, [
        check("NoiseOn", "Включить", 0),
        slider("NoiseAmount", "Сила", 0.12, 0, 1, 0, 1),
        slider("NoiseSize", "Мелкость зерна", 400, 10, 1000, 1, 10000),
        slider("NoiseSpeed", "Скорость", 5, 0, 20, 0, 1000),
        slider("NoiseContrast", "Контраст зерна", 2, 0, 5, 0, 50),
    ]),
    ("SecOut", "Цвет на выходе", False, [
        slider("OutGain", "Яркость", 1, 0, 4, 0, 100),
        slider("OutLift", "Подъём теней", 0, -0.5, 0.5, -5, 5),
        slider("OutGamma", "Гамма", 1, 0.2, 3, 0.01, 10),
        slider("OutContrast", "Контраст", 0, -1, 1, -5, 5),
        slider("OutSat", "Насыщенность", 1, 0, 3, 0, 10),
        check("OutClip", "Обрезать 0–1", 0),
    ]),
    ("SecGlobal", "Общее", False, [
        slider("GlobalMix", "Интенсивность эффекта", 1, 0, 1, 0, 1),
    ]),
]

COLOR_GROUP = 40


def value_ids():
    """(id, default) of every control that stores a value (presets operate on these)."""
    out = []
    for _, _, _, items in SECTIONS:
        for c in items:
            if c.kind in ("slider", "check", "combo") and c.id != "PresetSel":
                out.append((c.id, c.default))
            elif c.kind == "color":
                for ch, v in zip(("Red", "Green", "Blue"), c.rgb):
                    out.append((c.id + ch, v))
    return out


DEFAULTS = dict(value_ids())

PRESETS = {
    0: {},
    1: dict(PixPattern=1, ScanOn=1, ScanStrength=0.35, VigOn=1, VigAmount=0.45, CornerOn=1, CurveOn=1,
            CurveAmount=0.12, FlickOn=1, FlickAmount=0.04, NoiseOn=1, NoiseAmount=0.08, GlowGain=1.2,
            OutSat=1.1, TubeOn=1, TubeAmount=0.2),
    2: dict(PixPattern=2, ScanOn=1, ScanStrength=0.5, ScanBeam=0.55, GlowGain=2.5, GlowSize=12,
            GlowThreshold=0.05, InSat=1.3, PixBright=2.2, VigOn=1, VigAmount=0.3, CurveOn=1, CurveAmount=0.08),
    3: dict(MonoOn=1, MonoColorRed=0.2, MonoColorGreen=1.0, MonoColorBlue=0.35, MonoBoost=1.4, PixPattern=8,
            ScanOn=1, ScanStrength=0.5, GlowGain=2.5, GlowSize=14, FlickOn=1, FlickAmount=0.05, VigOn=1,
            VigAmount=0.6, CornerOn=1, CornerRadius=0.1, InContrast=0.3, CurveOn=1, CurveAmount=0.18,
            TubeOn=1, TubeAmount=0.3, TubeColorRed=0.3, TubeColorGreen=1.0, TubeColorBlue=0.45),
    4: dict(MonoOn=1, MonoColorRed=1.0, MonoColorGreen=0.62, MonoColorBlue=0.12, MonoBoost=1.4, PixPattern=8,
            ScanOn=1, ScanStrength=0.5, GlowGain=2.5, GlowSize=14, FlickOn=1, FlickAmount=0.05, VigOn=1,
            VigAmount=0.6, CornerOn=1, CornerRadius=0.1, InContrast=0.3, CurveOn=1, CurveAmount=0.18,
            TubeOn=1, TubeAmount=0.3, TubeColorRed=1.0, TubeColorGreen=0.7, TubeColorBlue=0.25),
    5: dict(PixSoft=0.6, PixStrength=0.7, ConvOn=1, ConvRX=2.5, ConvBX=-2.5, NoiseOn=1, NoiseAmount=0.18,
            BandOn=1, BandStrength=0.15, BandSpeed=0.15, BandHeight=0.4, InSat=0.85, OutGamma=1.1,
            GlowGain=2, GlowSize=16, FlickOn=1, FlickAmount=0.05, ShakeOn=1, ShakeX=0.0015, ShakeY=0.001,
            ShakeJitter=0.1, BleedOn=1, BleedStrength=0.8, BleedBlur=12, BleedShift=3),
    6: dict(ShakeOn=1, ShakeX=0.008, ShakeY=0.006, ShakeSpeed=3, ShakeJitter=0.8, FlickOn=1, FlickAmount=0.35,
            FlickSpeed=3, FlickSmooth=0.1, BandOn=1, BandSpeed=1.5, BandStrength=0.4, BandDark=1, NoiseOn=1,
            NoiseAmount=0.3, ConvOn=1, ConvRX=4, ConvRY=1, ConvBX=-3, InSat=0.7, ColorResOn=1, ColorLevels=8,
            BleedOn=1, BleedStrength=0.6, BleedBlur=20, BleedShift=6),
    7: dict(PixSize=2, PixPattern=1, BandOn=1, BandStrength=0.35, BandSpeed=0.25, BandHeight=0.5, BandSoft=0.8,
            VigOn=1, VigAmount=0.5, CornerOn=1, CurveOn=1, CurveAmount=0.2, GlowGain=2, GlowSize=20,
            NoiseOn=1, NoiseAmount=0.1, TubeOn=1, TubeAmount=0.25),
    8: dict(PixStrength=0.6, PixSoft=0.5, PixGamma=0.85, PixBright=1.6, GlowGain=1.8, GlowSize=20,
            GlowThreshold=0.2, OutContrast=-0.05, InSat=0.9, VigOn=1, VigAmount=0.3, PixPattern=5),
    9: dict(BalR=1.1, BalG=0.85, BalB=1.25, InSat=1.4, InContrast=0.15, GlowGain=3, GlowSize=18,
            GlowThreshold=0.05, ConvOn=1, ConvRX=1.5, ConvBX=-1.5, PixPattern=2, ScanOn=1, ScanStrength=0.3,
            ShiftOn=1, HueShift=-12, SatShift=1.2, TubeOn=1, TubeAmount=0.35, TubeColorRed=0.5,
            TubeColorGreen=0.6, TubeColorBlue=1.0),
}

for _p in PRESETS.values():
    for _k in _p:
        assert _k in DEFAULTS, f"unknown preset key {_k}"

# ------------------------------------------------------------------ button scripts
LUA_COMMON = r'''
local IDS = __IDS__
local DEF = __DEF__
local PRESETS = __PRESETS__
local function fusionDir()  -- macOS, Windows или Linux
  local list, appdata, home = {}, os.getenv("APPDATA"), os.getenv("HOME") or ""
  if appdata and appdata ~= "" then
    list[#list + 1] = (appdata:gsub("\\", "/")) .. "/Blackmagic Design/DaVinci Resolve/Support/Fusion/"
  end
  if home ~= "" then
    list[#list + 1] = home .. "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/"
    list[#list + 1] = home .. "/.local/share/DaVinciResolve/Fusion/"
  end
  for _, dir in ipairs(list) do
    if bmd.fileexists(dir .. "Templates") then return dir end
  end
  return list[1] or ""
end
local FU = fusionDir()
local PRESET_DIR = FU .. "CRT Pro User Presets/"
local TEMPLATE = FU .. "Templates/Edit/Effects/Claude/CRT/CRT Pro v2.setting"
local NAMES = __NAMES__
local C = tool.Composition or comp
local function say(title, text)
  if C then C:AskUser(title, { { "Info", "Text", Name = "", Default = text, Lines = 3, Wrap = true } }) else print(text) end
end
local function applyTable(t)
  if C then pcall(function() C:StartUndo("CRT Pro") end) end
  for _, k in ipairs(IDS) do
    local v = t[k]
    if type(v) == "number" then tool:SetInput(k, v) end
  end
  if C then pcall(function() C:EndUndo(true) end) end
end
local function current()
  local t = {}
  for _, k in ipairs(IDS) do t[k] = tool:GetInput(k) end
  return t
end
local function cleanName(s)
  s = tostring(s or ""):gsub("[/\\:%*%?\"<>|]", "_"):gsub("^%s+", ""):gsub("%s+$", "")
  return s
end
local function listOwn()
  local names = {}
  for _, f in ipairs(bmd.readdir(PRESET_DIR .. "*.crtpreset") or {}) do
    if type(f) == "table" and f.Name and not f.IsDir then
      names[#names + 1] = (f.Name:gsub("%.crtpreset$", ""))
    end
  end
  table.sort(names)
  return names
end
-- rewrite the installed CRT Pro template so its "Пресет" list = built-in + own presets
local function rebuildTemplate()
  local src = bmd.readfile(TEMPLATE)
  if type(src) ~= "table" then return false end
  local grp
  for _, v in pairs(src.Tools) do if type(v) == "table" and v.Tools then grp = v end end
  if not grp then return false end
  local ucs = grp.Tools.Ctrl.UserControls
  local combo, apply = ucs.PresetSel, ucs.BtnApply
  if not combo or not apply then return false end
  local own = listOwn()
  for i = #combo, 1, -1 do combo[i] = nil end
  for i = 0, #NAMES do combo[#combo + 1] = { CCS_AddString = NAMES[i] } end
  local quoted = {}
  for _, n in ipairs(own) do
    combo[#combo + 1] = { CCS_AddString = "★ " .. n }
    quoted[#quoted + 1] = string.format("%q", n)
  end
  combo.INP_MaxScale = #combo - 1
  combo.INP_MaxAllowed = #combo - 1
  local key = "local USER_" .. "PRESETS = "  -- split so this line never matches itself
  local newList = key .. "{ " .. table.concat(quoted, ", ") .. " }"
  apply.BTNCS_Execute = apply.BTNCS_Execute:gsub(key .. "%b{}", function() return newList end, 1)
  return bmd.writefile(TEMPLATE, src) ~= false
end
'''

LUA_ACTIONS = {
    "apply": r'''
local USER_PRESETS = __USER__
local sel = math.floor((tool:GetInput("PresetSel") or 0) + 0.5)
if sel <= #NAMES then
  local t = {}
  for k, v in pairs(DEF) do t[k] = v end
  for k, v in pairs(PRESETS[sel] or {}) do t[k] = v end
  applyTable(t)
else
  local name = USER_PRESETS[sel - #NAMES]
  local t = name and bmd.readfile(PRESET_DIR .. name .. ".crtpreset")
  if type(t) == "table" then applyTable(t)
  else say("CRT Pro", "Пресет «" .. tostring(name) .. "» не найден — возможно, его удалили.") end
end
''',
    "reset": r'''
applyTable(DEF)
tool:SetInput("PresetSel", 0)
''',
    "save": r'''
local r = C:AskUser("Сохранить мой пресет", { { "Name", "Text", Name = "Название", Default = "Мой пресет", Lines = 1 } })
if not r then return end
local name = cleanName(r.Name)
if name == "" then return end
bmd.createdir(PRESET_DIR)
bmd.writefile(PRESET_DIR .. name .. ".crtpreset", current())
local ok = rebuildTemplate()
say("CRT Pro", "Пресет «" .. name .. "» сохранён" .. (ok and " и добавлен в список «Пресет» со звёздочкой ★. В списке он появится после перезапуска Resolve, когда перетащишь CRT Pro на клип. В этом клипе его можно применить кнопкой «Загрузить мой пресет»." or ". Список обновить не удалось — загрузить его можно кнопкой «Загрузить мой пресет»."))
''',
    "load": r'''
local names = listOwn()
if #names == 0 then say("CRT Pro", "Своих пресетов пока нет. Сначала нажми «Сохранить мой пресет».") return end
local r = C:AskUser("Загрузить мой пресет", { { "Preset", "Dropdown", Name = "Пресет", Options = names } })
if not r then return end
local t = bmd.readfile(PRESET_DIR .. names[(r.Preset or 0) + 1] .. ".crtpreset")
if type(t) == "table" then applyTable(t) else say("CRT Pro", "Не удалось прочитать пресет.") end
''',
    "delete": r'''
local names = listOwn()
if #names == 0 then say("CRT Pro", "Своих пресетов пока нет.") return end
local r = C:AskUser("Удалить мой пресет", { { "Preset", "Dropdown", Name = "Какой удалить", Options = names } })
if not r then return end
local name = names[(r.Preset or 0) + 1]
os.remove(PRESET_DIR .. name .. ".crtpreset")
rebuildTemplate()
say("CRT Pro", "Пресет «" .. name .. "» удалён.")
''',
    "window": r'''
local script = FU .. "Scripts/Comp/crt-2.0/CRT Presets.lua"
if not bmd.fileexists(script) then say("CRT Pro v2", "Не найдено окно пресетов:\n" .. script) return end
_G.CRT_TOOL = tool
local ok, err = pcall(dofile, script)
_G.CRT_TOOL = nil
if not ok then say("CRT Pro v2", "Ошибка окна пресетов: " .. tostring(err)) end
''',
    "copy": r'''
local parts = {}
local t = current()
for _, k in ipairs(IDS) do
  if type(t[k]) == "number" then parts[#parts + 1] = k .. "=" .. string.format("%.5g", t[k]) end
end
local code = "CRTPRO1;" .. table.concat(parts, ";")
pcall(function() bmd.setclipboard(code) end)
C:AskUser("Код настроек CRT Pro", { { "Code", "Text", Name = "Скопируй этот код", Default = code, Lines = 8, Wrap = true } })
''',
    "paste": r'''
local cur = ""
pcall(function() local cb = bmd.getclipboard(); if type(cb) == "string" then cur = cb end end)
local r = C:AskUser("Вставить код CRT Pro", { { "Code", "Text", Name = "Вставь код настроек", Default = cur, Lines = 8, Wrap = true } })
if not r or not r.Code then return end
local t = {}
for k, v in tostring(r.Code):gmatch("([%a_][%w_]*)=([%-%+%deE%.]+)") do t[k] = tonumber(v) end
applyTable(t)
''',
}


def lua_table_of_ids():
    return "{ " + ", ".join(lstr(k) for k, _ in value_ids()) + " }"


def lua_defaults():
    return "{ " + ", ".join(f"{k} = {lnum(v)}" for k, v in value_ids()) + " }"


def lua_presets():
    parts = []
    for i, p in PRESETS.items():
        parts.append(f"[{i}] = " + ("{ " + ", ".join(f"{k} = {lnum(v)}" for k, v in p.items()) + " }" if p else "{}"))
    return "{ " + ", ".join(parts) + " }"


def own_presets():
    if SHARE_MODE or not os.path.isdir(USER_DIR):
        return []
    return sorted(f[:-len(".crtpreset")] for f in os.listdir(USER_DIR) if f.endswith(".crtpreset"))


def read_own_preset(name):
    """Читает сохранённый пресет (таблица Lua) в обычный словарь."""
    with open(os.path.join(USER_DIR, name + ".crtpreset"), encoding="utf-8") as f:
        txt = f.read()
    return {k: float(v) for k, v in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(-?[\d.]+(?:[eE][-+]?\d+)?)", txt)}


def bake_own_presets():
    """Для .drfx: свои пресеты становятся встроенными, чтобы работали на чужом компьютере."""
    global SHARE_MODE
    baked = []
    for name in own_presets():
        values = read_own_preset(name)
        if values:
            PRESETS[len(PRESET_NAMES)] = values
            PRESET_NAMES.append("★ " + name)
            baked.append(name)
    SHARE_MODE = True
    return baked


def make_drfx(path, pro_dir):
    """Пакет .drfx — это zip со структурой Edit/Effects/Claude/CRT/."""
    tmp = tempfile.mkdtemp(prefix="crt-drfx-")
    try:
        inner = os.path.join(tmp, "Edit", "Effects", "Claude", "CRT")
        os.makedirs(inner)
        for src, name in ((pro_dir, "CRT Pro v2"),):
            for ext in (".setting", ".png"):
                f = os.path.join(src, name + ext)
                if os.path.exists(f):
                    shutil.copy2(f, os.path.join(inner, name + ext))
        if os.path.exists(path):
            os.remove(path)
        subprocess.run(["zip", "-r", "-q", "-X", path, "Edit", "-x", ".*", "-x", "__MACOSX*"],
                       cwd=tmp, check=True)
        return sorted(os.listdir(inner))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def button_script(action):
    script = LUA_COMMON.strip() + "\n" + LUA_ACTIONS[action].strip() + "\n"
    return (script.replace("__IDS__", lua_table_of_ids())
            .replace("__DEF__", lua_defaults())
            .replace("__PRESETS__", lua_presets())
            .replace("__NAMES__", "{ " + ", ".join(f"[{i}] = {lstr(n)}" for i, n in enumerate(PRESET_NAMES)) + " }")
            .replace("__USER__", "{ " + ", ".join(lstr(n) for n in own_presets()) + " }"))


# ------------------------------------------------------------------ tools
class Tool:
    def __init__(self, name, typ, pos, info="OperatorInfo"):
        self.name, self.typ, self.pos, self.info = name, typ, pos, info
        self.inputs = []
        self.pre = []
        self.user_controls = None

    def val(self, k, v):
        self.inputs.append((k, f"Input {{ Value = {lnum(v)}, }}"))
        return self

    def sval(self, k, s):
        self.inputs.append((k, f"Input {{ Value = {lstr(s)}, }}"))
        return self

    def pt(self, k, x, y):
        self.inputs.append((k, f"Input {{ Value = {{ {lnum(x)}, {lnum(y)} }}, }}"))
        return self

    def fuid(self, k, s):
        self.inputs.append((k, f"Input {{ Value = FuID {{ {lstr(s)} }}, }}"))
        return self

    def expr(self, k, e, init=0):
        v = f"{{ {lnum(init[0])}, {lnum(init[1])} }}" if isinstance(init, tuple) else lnum(init)
        self.inputs.append((k, f"Input {{\n\tValue = {v},\n\tExpression = {lstr(e)},\n}}"))
        return self

    def link(self, k, src, out="Output"):
        self.inputs.append((k, f"Input {{\n\tSourceOp = {lstr(src)},\n\tSource = {lstr(out)},\n}}"))
        return self

    def render(self, ind):
        t = "\t" * ind
        lines = [f"{t}{self.name} = {self.typ} {{", f"{t}\tCtrlWZoom = false,", f"{t}\tNameSet = true,"]
        lines += [f"{t}\t{p}" for p in self.pre]
        if self.inputs:
            lines.append(f"{t}\tInputs = {{")
            for k, v in self.inputs:
                vv = v.replace("\n", "\n" + t + "\t\t")
                key = k if k.replace("_", "").isalnum() else f'["{k}"]'
                lines.append(f"{t}\t\t{key} = {vv},")
            lines.append(f"{t}\t}},")
        lines.append(f"{t}\tViewInfo = {self.info} {{ Pos = {{ {lnum(self.pos[0])}, {lnum(self.pos[1])} }} }},")
        if self.user_controls:
            lines.append(f"{t}\tUserControls = ordered() {{")
            for uc in self.user_controls:
                lines.append(f"{t}\t\t{uc},")
            lines.append(f"{t}\t}},")
        lines.append(f"{t}}}")
        return "\n".join(lines)


BIG = 100000000  # generators stay valid for any clip length


def background(name, pos, w, h, rgba=(0, 0, 0, 1), exprs=None):
    b = Tool(name, "Background", pos)
    b.val("GlobalIn", -BIG).val("GlobalOut", BIG)
    if isinstance(w, str):
        b.expr("Width", w, 1)
    else:
        b.val("Width", w)
    if isinstance(h, str):
        b.expr("Height", h, 1)
    else:
        b.val("Height", h)
    b.val("UseFrameFormatSettings", 0).pt("PixelAspect", 1, 1)
    exprs = exprs or {}
    for ch, v in zip(("TopLeftRed", "TopLeftGreen", "TopLeftBlue", "TopLeftAlpha"), rgba):
        if ch in exprs:
            b.expr(ch, exprs[ch], v)
        else:
            b.val(ch, v)
    return b


def merge(name, pos, bg, fg, center=(0.5, 0.5), mode=None, edges=0, fm=0, blend=None, extra=None):
    m = Tool(name, "Merge", pos)
    m.link("Background", bg).link("Foreground", fg)
    if isinstance(center, str):
        m.expr("Center", center, (0.5, 0.5))
    else:
        m.pt("Center", *center)
    if mode:
        m.fuid("ApplyMode", mode)
    m.val("Edges", edges).val("FilterMethod", fm).val("PerformDepthMerge", 0)
    if blend is not None:
        m.expr("Blend", blend, 1)
    for k, v in (extra or {}).items():
        m.val(k, v)
    return m


def bc(name, pos, src, exprs, blend=None, mask=None, vals=None):
    b = Tool(name, "BrightnessContrast", pos)
    for k, v in (vals or {}).items():
        b.val(k, v)
    for k, e in exprs.items():
        b.expr(k, e, 1)
    if blend is not None:
        b.expr("Blend", blend, 1)
    b.link("Input", src)
    if mask:
        b.link("EffectMask", mask, "Mask")
    return b


def dissolve(name, pos, bg, fg, mix_expr):
    d = Tool(name, "Dissolve", pos)
    d.pre.append('Transitions = {\n\t\t[0] = "DFTDissolve"\n\t},'.replace("\n", "\n" + "\t" * 4))
    d.link("Background", bg).link("Foreground", fg).expr("Mix", mix_expr, 0)
    return d


def pattern_tiles():
    """10 пиксельных узоров. Каждый — плитка 24x12 px, её масштабирует TileScale."""
    T, made = [], {}
    col = {"R": (1, 0, 0), "G": (0, 1, 0), "B": (0, 0, 1)}

    def bg(kind, w, h, pos):
        name = f"Px{kind}{w}x{h}"
        if name not in made:
            if kind in col:
                rgb = col[kind]
                ex = {ch: ("1" if v else "Ctrl.Fake") for ch, v in
                      zip(("TopLeftRed", "TopLeftGreen", "TopLeftBlue"), rgb)}
                T.append(background(name, pos, w, h, (rgb[0], rgb[1], rgb[2], 1), ex))
            elif kind == "W":
                T.append(background(name, pos, w, h, (1, 1, 1, 1)))
            elif kind == "Y":
                T.append(background(name, pos, w, h, (0.25, 0.25, 0.25, 1)))
            else:
                T.append(background(name, pos, w, h, (0, 0, 0, 1)))
            made[name] = True
        return name

    def cell(name, cw, ch, elems, pos, base="K"):
        prev = bg(base, cw, ch, (pos[0] - 140, pos[1] - 40))
        for i, (ex_, ey, ew, eh, kind) in enumerate(elems):
            sub = bg(kind, ew, eh, (pos[0] - 140, pos[1] + 30 + 24 * i))
            m = f"{name}{i}"
            T.append(merge(m, (pos[0] + 24 * i, pos[1]), prev, sub,
                           ((ex_ + ew / 2) / cw, (ey + eh / 2) / ch)))
            prev = m
        return prev

    def wrap(name, src, cw, ch, W, H, pos, offy=0.0):
        canvas = bg("K", W, H, (pos[0] - 140, pos[1] - 40))
        T.append(merge(name, pos, canvas, src, ((cw / 2) / W, (ch / 2 + offy) / H), edges=1))
        return name

    def pair(name, a, b, pos):
        canvas = bg("K", 8, 12, (pos[0] - 140, pos[1] - 40))
        T.append(merge(name + "L", pos, canvas, a, (0.25, 0.5)))
        T.append(merge(name, (pos[0] + 40, pos[1]), name + "L", b, (0.75, 0.5)))
        return name

    y0, pats = -1000, []
    rgb3 = [(0, 1, 1, 3, "R"), (1, 1, 1, 3, "G"), (2, 1, 1, 3, "B")]
    straight = cell("CellStraight", 4, 4, rgb3, (-1600, y0))
    pats.append(wrap("Pat0", straight, 4, 4, 24, 12, (-1450, y0)))                      # прямые
    a = wrap("ShiftA", straight, 4, 4, 4, 12, (-1450, y0 + 55))
    b = wrap("ShiftB", straight, 4, 4, 4, 12, (-1450, y0 + 110), offy=2)
    pats.append(wrap("Pat1", pair("ShiftPair", a, b, (-1300, y0 + 80)), 8, 12, 24, 12,  # со сдвигом
                     (-1150, y0 + 80)))
    ap = cell("CellAperture", 4, 1, [(0, 0, 1, 1, "R"), (1, 0, 1, 1, "G"), (2, 0, 1, 1, "B")],
              (-1600, y0 + 165))
    pats.append(wrap("Pat2", ap, 4, 1, 24, 12, (-1450, y0 + 165)))                      # апертурная решётка
    slot = cell("CellSlot", 4, 6, [(0, 1, 1, 5, "R"), (1, 1, 1, 5, "G"), (2, 1, 1, 5, "B")],
                (-1600, y0 + 220))
    a = wrap("SlotA", slot, 4, 6, 4, 12, (-1450, y0 + 220))
    b = wrap("SlotB", slot, 4, 6, 4, 12, (-1450, y0 + 275), offy=3)
    pats.append(wrap("Pat3", pair("SlotPair", a, b, (-1300, y0 + 245)), 8, 12, 24, 12,  # щелевая маска
                     (-1150, y0 + 245)))
    shadow = cell("CellShadow", 6, 4, [(0, 2, 1, 1, "R"), (2, 2, 1, 1, "G"), (4, 2, 1, 1, "B"),
                                       (3, 0, 1, 1, "R"), (5, 0, 1, 1, "G"), (1, 0, 1, 1, "B")],
                  (-1600, y0 + 330))
    pats.append(wrap("Pat4", shadow, 6, 4, 24, 12, (-1450, y0 + 330)))                  # теневая маска
    lcd = cell("CellLCD", 4, 4, rgb3, (-1600, y0 + 385), base="Y")
    pats.append(wrap("Pat5", lcd, 4, 4, 24, 12, (-1450, y0 + 385)))                     # LCD-сетка
    led = cell("CellLED", 4, 4, [(0, 1, 1, 2, "R"), (1, 1, 1, 2, "G"), (2, 1, 1, 2, "B")],
               (-1600, y0 + 440))
    pats.append(wrap("Pat6", led, 4, 4, 24, 12, (-1450, y0 + 440)))                     # LED-стена
    dots = cell("CellDots", 4, 4, [(1, 1, 2, 2, "W")], (-1600, y0 + 495))
    pats.append(wrap("Pat7", dots, 4, 4, 24, 12, (-1450, y0 + 495)))                    # точечная матрица
    grid = cell("CellGrid", 4, 4, [(0, 1, 3, 3, "W")], (-1600, y0 + 550))
    pats.append(wrap("Pat8", grid, 4, 4, 24, 12, (-1450, y0 + 550)))                    # сетка без цвета
    rows = cell("CellRows", 4, 4, [(0, 1, 4, 3, "W")], (-1600, y0 + 605))
    pats.append(wrap("Pat9", rows, 4, 4, 24, 12, (-1450, y0 + 605)))                    # только строки

    prev = pats[0]
    for i, p in enumerate(pats[1:], start=1):
        name = f"PatSel{i}"
        T.append(dissolve(name, (-950, y0 + 40 * i), prev, p,
                          f"(Ctrl.PixPattern > {i - 0.5} and Ctrl.PixPattern < {i + 0.5}) and 1 or 0"))
        prev = name
    return T, prev


def build_tools():
    tools = []
    W, H = "InGrade.Input.Width", "InGrade.Input.Height"
    CELL = "InGrade.CellPx"  # размер пикселя в px: считается один раз в начале цепочки
    F = f"(Ctrl.PixDown > 0.5 and {CELL} or 1)"
    x, step = -1600, 115

    def nx():
        nonlocal x
        x += step
        return x

    tools.append(Tool("InRouter", "PipeRouter", (x, 0), info="PipeRouterInfo"))
    # --- цвет на входе
    ingrade = bc("InGrade", (nx(), 0), "InRouter",
                 {"Gain": "Ctrl.InGain", "Lift": "Ctrl.InLift", "Gamma": "Ctrl.InGamma",
                  "Contrast": "Ctrl.InContrast", "Saturation": "Ctrl.InSat",
                  "CellPx": "max(2, floor(4*Ctrl.PixSize*(Ctrl.PixScaleRes > 0.5 and "
                            "InGrade.Input.Height/1080 or 1) + 0.5))"})
    ingrade.user_controls = [
        'CellPx = { LINKS_Name = "Размер пикселя, px", LINKID_DataType = "Number", '
        'INPID_InputControl = "SliderControl", INP_Integer = false, INP_Default = 4, INP_MinScale = 1, '
        'INP_MaxScale = 64, INP_MinAllowed = 1, INP_MaxAllowed = 4096, ICS_ControlPage = "Controls" }']
    tools.append(ingrade)
    tools.append(background("BalColor", (x + step, -90), 1, 1, (1, 1, 1, 1),
                            {"TopLeftRed": "Ctrl.BalR", "TopLeftGreen": "Ctrl.BalG", "TopLeftBlue": "Ctrl.BalB"}))
    tools.append(merge("BalMerge", (nx(), 0), "InGrade", "BalColor", mode="Multiply", edges=1))
    cc = Tool("ColorShift", "ColorCorrector", (nx(), 0))
    cc.expr("WheelHue1", "Ctrl.HueShift", 0).expr("WheelSaturation1", "Ctrl.SatShift", 1)
    cc.expr("Blend", "Ctrl.ShiftOn", 0).link("Input", "BalMerge")
    tools.append(cc)
    # --- монохром: 4 режима смешивания + выбор
    tools.append(bc("MonoDesat", (x + step, 95), "ColorShift", {"Gain": "Ctrl.MonoBoost"}, vals={"Saturation": 0}))
    tools.append(background("MonoColorBG", (x + step, 190), 1, 1, (0.25, 1, 0.4, 1),
                            {"TopLeftRed": "Ctrl.MonoColorRed", "TopLeftGreen": "Ctrl.MonoColorGreen",
                             "TopLeftBlue": "Ctrl.MonoColorBlue"}))
    modes = [("MonoTintA", "Multiply"), ("MonoTintB", "Screen"), ("MonoTintC", "Overlay"),
             ("MonoTintD", "Color Burn")]
    for i, (nm, mode) in enumerate(modes):
        tools.append(merge(nm, (x + step + 30 * i, 140), "MonoDesat", "MonoColorBG", mode=mode, edges=1))
    prev = modes[0][0]
    for i, (nm, _) in enumerate(modes[1:], start=1):
        sel = f"MonoSel{i}"
        tools.append(dissolve(sel, (x + step + 30 * i, 95), prev, nm,
                              f"(Ctrl.MonoMode > {i - 0.5} and Ctrl.MonoMode < {i + 0.5}) and 1 or 0"))
        prev = sel
    tools.append(dissolve("MonoMix", (nx(), 0), "ColorShift", prev, "Ctrl.MonoOn*Ctrl.MonoAmount"))
    # --- растекание цвета
    bl = Tool("BleedBlur", "Blur", (x + step, 95))
    bl.fuid("Filter", "Fast Gaussian").val("LockXY", 0).val("YBlurSize", 0)
    bl.expr("XBlurSize", "Ctrl.BleedOn*Ctrl.BleedBlur", 8).link("Input", "MonoMix")
    tools.append(bl)
    bs = Tool("BleedShift", "Transform", (x + step, 160))
    bs.link("Input", "BleedBlur").val("Edges", 2)
    bs.expr("Center", f"Point(0.5 + Ctrl.BleedShift/{W}, 0.5)", (0.5, 0.5))
    tools.append(bs)
    tools.append(merge("BleedMerge", (nx(), 0), "MonoMix", "BleedShift", mode="Color",
                       blend="Ctrl.BleedOn*Ctrl.BleedStrength"))
    # --- тряска (до пикселей)
    sx = ("0.55*sin(time*Ctrl.ShakeSpeed*0.211 + 0.3) + 0.3*sin(time*Ctrl.ShakeSpeed*0.537 + 1.7)"
          " + 0.15*sin(time*Ctrl.ShakeSpeed*1.31 + 4.1)")
    sy = ("0.55*sin(time*Ctrl.ShakeSpeed*0.173 + 2.2) + 0.3*sin(time*Ctrl.ShakeSpeed*0.611 + 0.4)"
          " + 0.15*sin(time*Ctrl.ShakeSpeed*1.47 + 3.3)")
    jx = "(2*((sin(time*12.9898 + 1.1)*43758.5453) % 1) - 1)"
    jy = "(2*((sin(time*78.233 + 2.3)*43758.5453) % 1) - 1)"
    shake_center = (f"Point(0.5 + Ctrl.ShakeX*((1 - Ctrl.ShakeJitter)*({sx}) + Ctrl.ShakeJitter*{jx}), "
                    f"0.5 + Ctrl.ShakeY*((1 - Ctrl.ShakeJitter)*({sy}) + Ctrl.ShakeJitter*{jy}))")
    sh = Tool("ShakeXf", "Transform", (nx(), 0))
    sh.link("Input", "BleedMerge").expr("Edges", "Ctrl.ShakeEdges", 3)
    sh.expr("Center", shake_center, (0.5, 0.5)).expr("Blend", "Ctrl.ShakeOn*Ctrl.ShakeBefore", 1)
    tools.append(sh)
    # --- режим "разделение RGB": красный и синий берутся со сдвигом в треть пикселя
    split_on = "(Ctrl.RGBMode > 1.5) and 1 or 0"
    for ch, sgn, keep, src in (("R", "-", {"ProcessGreen": 0, "ProcessBlue": 0, "ProcessAlpha": 0}, "ShakeXf"),
                               ("B", "+", {"ProcessRed": 0, "ProcessGreen": 0, "ProcessAlpha": 0}, "SplitRMerge")):
        xf = Tool(f"Split{ch}Xf", "Transform", (x + step, 95 if ch == "R" else 160))
        xf.link("Input", "ShakeXf").val("Edges", 2)
        xf.expr("Center", f"Point(0.5 {sgn} ({CELL}/3)/{W}, 0.5)", (0.5, 0.5))
        tools.append(xf)
        tools.append(merge(f"Split{ch}Merge", (nx(), 0), src, f"Split{ch}Xf", blend=split_on, extra=keep))
    # --- понижение разрешения и обратно (пиксели)
    down = Tool("DownRes", "BetterResize", (nx(), 0))
    down.expr("Width", f"ceil({W}/{F})", 480).expr("Height", f"ceil({H}/{F})", 270)
    down.pt("PixelAspect", 1, 1).expr("FilterMethod", "Ctrl.PixSmoothDown*2", 0).link("Input", "SplitBMerge")
    tools.append(down)
    up = Tool("UpRes", "BetterResize", (nx(), 0))
    up.expr("Width", f"DownRes.Width*{F}", 1920).expr("Height", f"DownRes.Height*{F}", 1080)
    up.pt("PixelAspect", 1, 1).val("FilterMethod", 0).link("Input", "DownRes")
    tools.append(up)
    # --- сведение лучей
    for ch, keep, src in (("R", {"ProcessGreen": 0, "ProcessBlue": 0, "ProcessAlpha": 0}, "UpRes"),
                          ("B", {"ProcessRed": 0, "ProcessGreen": 0, "ProcessAlpha": 0}, "ConvRMerge")):
        xf = Tool(f"Conv{ch}Xf", "Transform", (x + step, -95 if ch == "R" else -165))
        xf.link("Input", "UpRes").val("Edges", 2)
        xf.expr("Center", f"Point(0.5 + Ctrl.Conv{ch}X/UpRes.Width, 0.5 + Ctrl.Conv{ch}Y/UpRes.Height)",
                (0.5, 0.5))
        tools.append(xf)
        tools.append(merge(f"Conv{ch}Merge", (nx(), 0), src, f"Conv{ch}Xf", blend="Ctrl.ConvOn", extra=keep))
    # --- сама маска
    tiles, tile_out = pattern_tiles()
    tools += tiles
    ts = Tool("TileScale", "BetterResize", (-800, -600))
    ts.expr("Width", f"6*{CELL}", 24).expr("Height", f"3*{CELL}", 12).pt("PixelAspect", 1, 1)
    ts.val("FilterMethod", 0).link("Input", tile_out)
    tools.append(ts)
    tools.append(merge("PixelMult", (nx(), 0), "ConvBMerge", "TileScale",
                       f"Point(3*{CELL}/UpRes.Width, 1.5*{CELL}/UpRes.Height)",
                       mode="Multiply", edges=1, blend="Ctrl.PixOn*Ctrl.PixStrength"))
    crop = Tool("FitCrop", "Crop", (nx(), 0))
    crop.val("XOffset", 0).val("YOffset", 0).expr("XSize", W, 1920).expr("YSize", H, 1080)
    crop.link("Input", "PixelMult")
    tools.append(crop)
    tools.append(bc("PixGrade", (nx(), 0), "FitCrop",
                    {"Gain": "1 + Ctrl.PixOn*Ctrl.PixStrength*Ctrl.PixBrightOn*(Ctrl.PixBright - 1)",
                     "Gamma": "1 + Ctrl.PixOn*(Ctrl.PixGamma - 1)"}))
    blur = Tool("PixBlur", "Blur", (nx(), 0))
    blur.fuid("Filter", "Fast Gaussian").expr("XBlurSize", f"Ctrl.PixSoft*{CELL}", 0.8).link("Input", "PixGrade")
    tools.append(blur)
    # --- строки развёртки
    P = f"(Ctrl.ScanLink > 0.5 and {CELL} or Ctrl.ScanPeriod)"
    tools.append(background("ScanBlack", (x, -320), 1, P))
    sm = Tool("ScanMask", "RectangleMask", (x + step, -390))
    sm.val("UseFrameFormatSettings", 0).val("MaskWidth", 1).expr("MaskHeight", "ScanBlack.Height", 4)
    sm.pt("PixelAspect", 1, 1).fuid("ClippingMode", "None").pt("Center", 0.5, 0.5).val("Width", 2)
    sm.expr("Height", "Ctrl.ScanBeam", 0.6).expr("SoftEdge", "Ctrl.ScanSoft", 0.5)
    tools.append(sm)
    sw = background("ScanWhite", (x + step, -320), 1, "ScanBlack.Height", (1, 1, 1, 1))
    sw.link("EffectMask", "ScanMask", "Mask")
    tools.append(sw)
    tools.append(merge("ScanTile", (x + step, -250), "ScanBlack", "ScanWhite"))
    tools.append(merge("ScanMult", (nx(), 0), "PixBlur", "ScanTile",
                       f"Point(0.5/{W}, ScanBlack.Height/2/{H})", mode="Multiply", edges=1,
                       blend="Ctrl.ScanOn*Ctrl.ScanStrength"))
    # --- тряска (после пикселей)
    sh2 = Tool("ShakeAfter", "Transform", (nx(), 0))
    sh2.link("Input", "ScanMult").expr("Edges", "Ctrl.ShakeEdges", 3)
    sh2.expr("Center", shake_center, (0.5, 0.5)).expr("Blend", "Ctrl.ShakeOn*(1 - Ctrl.ShakeBefore)", 0)
    tools.append(sh2)
    # --- свечение
    glow = Tool("Glow", "SoftGlow", (nx(), 0))
    glow.expr("Threshold", "Ctrl.GlowThreshold", 0.1).expr("Gain", "Ctrl.GlowGain", 1.5)
    glow.expr("XGlowSize", "Ctrl.GlowOn*Ctrl.GlowSize", 8).expr("Blend", "Ctrl.GlowOn", 1)
    glow.link("Input", "ShakeAfter")
    tools.append(glow)
    # --- свечение трубки (мягкий общий ореол)
    tb = Tool("TubeBlur", "Blur", (x + step, 95))
    tb.fuid("Filter", "Fast Gaussian").expr("XBlurSize", "Ctrl.TubeOn*Ctrl.TubeSize", 60).link("Input", "Glow")
    tools.append(tb)
    tools.append(background("TubeColorBG", (x + step, 190), 1, 1, (0.65, 0.8, 1, 1),
                            {"TopLeftRed": "Ctrl.TubeColorRed", "TopLeftGreen": "Ctrl.TubeColorGreen",
                             "TopLeftBlue": "Ctrl.TubeColorBlue"}))
    tools.append(merge("TubeTint", (x + step, 140), "TubeBlur", "TubeColorBG", mode="Multiply", edges=1))
    tools.append(merge("TubeMerge", (nx(), 0), "Glow", "TubeTint", mode="Screen",
                       blend="Ctrl.TubeOn*Ctrl.TubeAmount"))
    # --- выпуклость экрана + цветовая глубина (одна нода Custom)
    r2 = "(((x-0.5)*2*w1/h1)*((x-0.5)*2*w1/h1)+((y-0.5)*2)*((y-0.5)*2))"
    scale = f"(1+n1*{r2})"
    u, v = f"(0.5+(x-0.5)*{scale})", f"(0.5+(y-0.5)*{scale})"
    warp = Tool("ScreenWarp", "Custom", (nx(), 0))
    warp.link("Image1", "TubeMerge")
    warp.expr("NumberIn1", "Ctrl.CurveOn*Ctrl.CurveAmount", 0)
    warp.expr("NumberIn2", "(Ctrl.ColorResOn > 0.5 and Ctrl.ColorLevels or 1024)", 1024)
    for ch, letter in (("RedExpression", "r"), ("GreenExpression", "g"), ("BlueExpression", "b")):
        warp.inputs.append((ch, f'Input {{ Value = {lstr(f"floor(get{letter}1b({u},{v})*n2+0.5)/n2")}, }}'))
    warp.inputs.append(("AlphaExpression", f'Input {{ Value = {lstr(f"geta1b({u},{v})")}, }}'))
    warp.expr("Blend", "((Ctrl.CurveOn > 0.5 or Ctrl.ColorResOn > 0.5) and 1 or 0)", 0)
    tools.append(warp)
    # --- бегущая полоса (затвор)
    band = Tool("BandMask", "RectangleMask", (x + step, 130))
    band.val("UseFrameFormatSettings", 1).fuid("ClippingMode", "None").val("Width", 2)
    band.expr("Center", "Point(0.5, (1 + Ctrl.BandHeight)*((time*Ctrl.BandSpeed*(Ctrl.BandReverse > 0.5 and -1 or 1)"
                        "/24) % 1) - Ctrl.BandHeight/2)", (0.5, 0.5))
    band.expr("Height", "Ctrl.BandHeight", 0.3).expr("SoftEdge", "Ctrl.BandSoft*Ctrl.BandHeight*0.5", 0.07)
    tools.append(band)
    tools.append(bc("BandBC", (nx(), 0), "ScreenWarp",
                    {"Gain": "1 + Ctrl.BandStrength*(1 - 2*Ctrl.BandDark)", "Gamma": "1 + Ctrl.BandGamma"},
                    blend="Ctrl.BandOn", mask="BandMask"))
    # --- мерцание: по яркости или по гамме, с выбором каналов
    n_t = ("(Ctrl.FlickSmooth*(0.5 + 0.5*sin(time*Ctrl.FlickSpeed*0.9)*sin(time*Ctrl.FlickSpeed*0.37 + 1.3))"
           " + (1 - Ctrl.FlickSmooth)*((sin(floor(time*Ctrl.FlickSpeed)*12.9898 + 0.7)*43758.5453) % 1))")
    chan = {"ProcessRed": "Ctrl.FlickR", "ProcessGreen": "Ctrl.FlickG", "ProcessBlue": "Ctrl.FlickB"}
    fg_ = bc("FlickGain", (nx(), 0), "BandBC", dict({"Gain": f"1 - Ctrl.FlickAmount*{n_t}"}, **chan),
             blend="Ctrl.FlickOn*((Ctrl.FlickType < 0.5) and 1 or 0)")
    tools.append(fg_)
    fm_ = bc("FlickGamma", (nx(), 0), "FlickGain", dict({"Gamma": f"1 - 0.8*Ctrl.FlickAmount*{n_t}"}, **chan),
             blend="Ctrl.FlickOn*((Ctrl.FlickType > 0.5) and 1 or 0)")
    tools.append(fm_)
    # --- виньетка
    vm = Tool("VigMask", "EllipseMask", (x + step, 130))
    vm.val("UseFrameFormatSettings", 1).fuid("ClippingMode", "None").pt("Center", 0.5, 0.5).val("Invert", 1)
    vm.expr("Width", "Ctrl.VigSize", 1.25).expr("Height", "Ctrl.VigSize", 1.25)
    vm.expr("SoftEdge", "Ctrl.VigSoft", 0.5)
    tools.append(vm)
    tools.append(bc("VigBC", (nx(), 0), "FlickGamma", {"Gain": "1 - Ctrl.VigAmount"}, blend="Ctrl.VigOn",
                    mask="VigMask"))
    # --- плёночное зерно
    nz = Tool("NoiseGen", "FastNoise", (x + step, 130))
    nz.val("GlobalIn", -BIG).val("GlobalOut", BIG).val("UseFrameFormatSettings", 0)
    nz.expr("Width", f"Ctrl.NoiseOn > 0.5 and {W} or 8", 1920).expr("Height", f"Ctrl.NoiseOn > 0.5 and {H} or 8", 1080)
    nz.val("Detail", 3).val("LockXY", 1).val("Discontinuous", 0)
    nz.expr("Contrast", "Ctrl.NoiseContrast", 2)
    nz.expr("XScale", "Ctrl.NoiseSize", 400).expr("SeetheRate", "Ctrl.NoiseSpeed", 5)
    tools.append(nz)
    tools.append(merge("NoiseMerge", (nx(), 0), "VigBC", "NoiseGen", mode="Overlay",
                       blend="Ctrl.NoiseOn*Ctrl.NoiseAmount"))
    # --- скруглённые углы экрана
    cm = Tool("CornerMask", "RectangleMask", (x + step, 130))
    cm.val("UseFrameFormatSettings", 1).fuid("ClippingMode", "None").pt("Center", 0.5, 0.5).val("Invert", 1)
    cm.expr("Width", "1 - 2*Ctrl.CornerInset", 0.97)
    cm.expr("Height", f"1 - 2*Ctrl.CornerInset*{W}/{H}", 0.95)
    cm.expr("CornerRadius", "Ctrl.CornerRadius", 0.08).expr("SoftEdge", "Ctrl.CornerSoft", 0.004)
    tools.append(cm)
    tools.append(bc("CornerBC", (nx(), 0), "NoiseMerge", {}, blend="Ctrl.CornerOn", mask="CornerMask",
                    vals={"Gain": 0}))
    # --- цвет на выходе и общий микс
    out = bc("OutGrade", (nx(), 0), "CornerBC",
             {"Gain": "Ctrl.OutGain", "Lift": "Ctrl.OutLift", "Gamma": "Ctrl.OutGamma",
              "Contrast": "Ctrl.OutContrast", "Saturation": "Ctrl.OutSat",
              "ClipBlack": "Ctrl.OutClip", "ClipWhite": "Ctrl.OutClip"})
    tools.append(out)
    tools.append(dissolve("FinalMix", (nx(), 0), "InRouter", "OutGrade", "Ctrl.GlobalMix"))
    return tools


# ------------------------------------------------------------------ controls holder + group inputs
def uc_def(c):
    base = {"LINKS_Name": c.name, "LINKID_DataType": "Number", "ICS_ControlPage": "Controls"}
    if c.kind == "label":
        base.update(INPID_InputControl="LabelControl", LBLC_DropDownButton=True, LBLC_NumInputs=c.count,
                    INP_Default=1 if c.is_open else 0, INP_Integer=False)
    elif c.kind == "check":
        base.update(INPID_InputControl="CheckboxControl", CBC_TriState=False, INP_Integer=False,
                    INP_Default=c.default, INP_MinScale=0, INP_MaxScale=1)
    elif c.kind == "slider":
        base.update(INPID_InputControl="SliderControl", INP_Integer=c.integer, INP_Default=c.default,
                    INP_MinScale=c.lo, INP_MaxScale=c.hi, INP_MinAllowed=c.amin, INP_MaxAllowed=c.amax)
    elif c.kind == "button":
        base.update(INPID_InputControl="ButtonControl", INP_Integer=False, INP_External=False,
                    BTNCS_Execute=button_script(c.action), ICD_Width=c.width)
    elif c.kind == "text":
        base.update(LINKID_DataType="Text", INPID_InputControl="TextEditControl", TEC_Lines=1,
                    TEC_ReadOnly=True, TEC_Wrap=False, INP_External=False)
    body = ", ".join(f"{k} = {lua_value(v)}" for k, v in base.items())
    if c.kind == "combo":
        opts = ", ".join(f"{{ CCS_AddString = {lstr(o)} }}" for o in c.options)
        body = (opts + ", " + body + f", INPID_InputControl = \"ComboControl\", INP_Integer = true, "
                f"INP_External = false, CC_LabelPosition = \"Horizontal\", INP_Default = {lnum(c.default)}, "
                f"INP_MinScale = 0, INP_MaxScale = {len(c.options) - 1}, INP_MinAllowed = 0, "
                f"INP_MaxAllowed = {len(c.options) - 1}")
    return f"{c.id} = {{ {body} }}"


def color_defs(c):
    g = COLOR_GROUP
    out = [f"{c.id} = {{ LINKS_Name = {lstr(c.name)}, LINKID_DataType = \"Number\", INPID_InputControl = \"ColorControl\", "
           f"IC_ControlGroup = {g}, IC_ControlID = -1, CLRC_ShowWheel = false, CLRC_ColorSpace = 0, INP_Default = 0, "
           f"ICS_ControlPage = \"Controls\" }}"]
    for i, (ch, v) in enumerate(zip(("Red", "Green", "Blue"), c.rgb)):
        out.append(f"{c.id}{ch} = {{ LINKID_DataType = \"Number\", INPID_InputControl = \"ColorControl\", "
                   f"IC_ControlGroup = {g}, IC_ControlID = {i}, CLRC_ShowWheel = false, CLRC_ColorSpace = 0, "
                   f"INP_Default = {lnum(v)}, ICS_ControlPage = \"Controls\" }}")
    return out


def build_ctrl_and_inputs(values):
    ctrl = Tool("Ctrl", "Background", (-1100, -250))
    ctrl.val("Width", 1).val("Height", 1).val("UseFrameFormatSettings", 0)
    ctrl.user_controls = []
    group_inputs = ["MainInput1 = InstanceInput {\n\tSourceOp = \"InRouter\",\n\tSource = \"Input\",\n}"]
    first = True
    for sid, sname, is_open, items in SECTIONS:
        count = sum(3 if c.kind == "color" else 1 for c in items)
        lab = C(sid, "label", sname, is_open=is_open)
        lab.count = count
        ctrl.val(sid, 1 if is_open else 0)
        ctrl.user_controls.append(uc_def(lab))
        page = '\n\tPage = "Controls",' if first else ""
        first = False
        group_inputs.append(f"{sid} = InstanceInput {{\n\tSourceOp = \"Ctrl\",\n\tSource = \"{sid}\",{page}\n}}")
        for c in items:
            if c.kind == "color":
                ctrl.user_controls += color_defs(c)
                for i, ch in enumerate(("Red", "Green", "Blue")):
                    cid = c.id + ch
                    ctrl.val(cid, values[cid])
                    name = f"\n\tName = {lstr(c.name)}," if i == 0 else ""
                    group_inputs.append(
                        f"{cid} = InstanceInput {{\n\tSourceOp = \"Ctrl\",\n\tSource = \"{cid}\",{name}\n"
                        f"\tControlGroup = {COLOR_GROUP},\n\tDefault = {lnum(values[cid])},\n}}")
                continue
            ctrl.user_controls.append(uc_def(c))
            extra = ""
            if c.kind == "button":
                if c.width != 1.0:
                    extra = f"\n\tWidth = {lnum(c.width)},"
            elif c.kind == "text":
                ctrl.sval(c.id, values.get(c.id, c.default))
            else:
                v = values.get(c.id, c.default)
                ctrl.val(c.id, v)
                extra = f"\n\tDefault = {lnum(v)},"
            group_inputs.append(f"{c.id} = InstanceInput {{\n\tSourceOp = \"Ctrl\",\n\tSource = \"{c.id}\",{extra}\n}}")
    ctrl.user_controls.append(
        'Fake = { LINKS_Name = "Имитация RGB", LINKID_DataType = "Number", '
        'INPID_InputControl = "SliderControl", INP_Integer = false, INP_Default = 0, '
        'INP_MinScale = 0, INP_MaxScale = 1, INP_MinAllowed = 0, INP_MaxAllowed = 1, '
        'ICS_ControlPage = "Controls" }')
    ctrl.expr("Fake", "(Ctrl.RGBMode > 0.5 and Ctrl.RGBMode < 1.5) and 1 or 0", 0)
    return ctrl, group_inputs


def build_setting(preset_index=0):
    values = dict(DEFAULTS)
    values.update(PRESETS[preset_index])
    values["PresetSel"] = preset_index
    for c in SECTIONS[0][3]:
        if c.id == "PresetSel":
            c.options = PRESET_NAMES + ["★ " + n for n in own_presets()]
    ctrl, gin = build_ctrl_and_inputs(values)
    tools = [ctrl] + build_tools()
    ind = "\t\t\t\t"
    inputs_txt = ",\n".join(ind + g.replace("\n", "\n" + ind) for g in gin)
    tools_txt = ",\n".join(t.render(4) for t in tools)
    return (
        "{\n\tTools = ordered() {\n"
        f"\t\t{GROUP} = GroupOperator {{\n\t\t\tCtrlWZoom = false,\n\t\t\tNameSet = true,\n"
        "\t\t\tInputs = ordered() {\n" + inputs_txt + ",\n\t\t\t},\n"
        "\t\t\tOutputs = {\n\t\t\t\tMainOutput1 = InstanceOutput {\n\t\t\t\t\tSourceOp = \"FinalMix\",\n"
        "\t\t\t\t\tSource = \"Output\",\n\t\t\t\t},\n\t\t\t},\n"
        "\t\t\tViewInfo = GroupInfo { Pos = { 0, 0 } },\n"
        "\t\t\tTools = ordered() {\n" + tools_txt + ",\n\t\t\t},\n\t\t},\n\t},\n"
        f"\tActiveTool = \"{GROUP}\",\n}}\n"
    )


# ------------------------------------------------------------------ icons
def make_icon(path, tag, tint):
    flt = (
        "geq=r='255*lt(mod(X\\,4)\\,1)*lt(mod(Y\\,4)\\,3)':g='255*eq(floor(mod(X\\,4))\\,1)*lt(mod(Y\\,4)\\,3)'"
        ":b='255*eq(floor(mod(X\\,4))\\,2)*lt(mod(Y\\,4)\\,3)',"
        f"drawbox=x=0:y=0:w=iw:h=ih:color={tint}@0.35:t=fill,"
        "drawtext=fontfile=/System/Library/Fonts/Supplemental/Arial Bold.ttf:text='CRT PRO':fontsize=13:"
        "fontcolor=white:borderw=2:bordercolor=black:x=(w-text_w)/2:y=8,"
        f"drawtext=fontfile=/System/Library/Fonts/Supplemental/Arial Bold.ttf:text='{tag}':fontsize=17:"
        "fontcolor=white:borderw=2:bordercolor=black:x=(w-text_w)/2:y=30"
    )
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=black:s=104x58",
                    "-frames:v", "1", "-vf", flt, "-y", path], check=True)


def write_effect(folder, name, text, icon):
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, name + ".setting"), "w", encoding="utf-8") as f:
        f.write(text)
    make_icon(os.path.join(folder, name + ".png"), *icon)


def check(setting):
    """Прогоняет validate_crt_pro.lua во временной папке: свои пресеты при этом не трогаются."""
    if not (os.path.exists(FUSCRIPT) and os.path.exists(VALIDATOR)):
        print("проверка пропущена: не найден fuscript или validate_crt_pro.lua")
        return True
    tmp = tempfile.mkdtemp(prefix="crt-check-")
    try:
        lib = os.path.join(tmp, "Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion",
                           "Templates/Edit/Effects/Claude/CRT")
        os.makedirs(lib)
        shutil.copy2(setting, lib)
        runner = os.path.join(tmp, "run.lua")
        with open(runner, "w", encoding="utf-8") as f:
            f.write(f"_G.SETTING = [[{setting}]]\ndofile([[{VALIDATOR}]])\n")
        r = subprocess.run([FUSCRIPT, "-l", "lua", runner], env=dict(os.environ, HOME=tmp),
                           capture_output=True, text=True, timeout=600)
        out = (r.stdout or "") + (r.stderr or "")
        for line in out.splitlines():
            line = line.strip()
            if line and "Interpreter" not in line and "Copyright" not in line:
                print("  " + line)
        return "проблем не найдено" in out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    install = "--install" in sys.argv
    pack = "--pack" in sys.argv
    out_dir = HERE
    baked = []
    if pack:
        # по умолчанию свои пресеты в пакет не попадают: они остаются только на этом компьютере
        if "--with-my-presets" in sys.argv:
            baked = bake_own_presets()
        else:
            global SHARE_MODE
            SHARE_MODE = True
        out_dir = tempfile.mkdtemp(prefix="crt-pack-")
    setting = os.path.join(out_dir, "CRT Pro v2.setting")
    write_effect(out_dir, "CRT Pro v2", build_setting(0), ("2.0", "0x9933ff"))
    print(f"собрано: CRT Pro.setting (своих пресетов в списке: {len(own_presets())})")
    if not check(setting):
        print("ОСТАНОВКА: проверка нашла проблемы, в Resolve ничего не установлено")
        sys.exit(1)
    if pack:
        drfx = os.path.join(ROOT, "Claude CRT Pack.drfx")
        files = make_drfx(drfx, out_dir)
        shutil.rmtree(out_dir, ignore_errors=True)
        print("собран пакет: " + drfx)
        print("  внутри: " + ", ".join(files))
        if baked:
            print("  свои пресеты вшиты внутрь: " + ", ".join(baked))
        else:
            print("  свои пресеты НЕ включены (только 10 встроенных)")
        return
    if not install:
        print("готово. Для установки в Resolve: python3 build_crt_pro.py --install")
        return
    os.makedirs(LIB, exist_ok=True)
    for ext in (".setting", ".png"):
        shutil.copy2(os.path.join(HERE, "CRT Pro v2" + ext), os.path.join(LIB, "CRT Pro v2" + ext))
        old = os.path.join(os.path.dirname(LIB), "CRT Pro v2" + ext)  # старое место: прямо в Claude/
        if os.path.exists(old):
            os.remove(old)
    print(f"установлено: {LIB}")
    print("перезапусти Resolve и перетащи CRT Pro на клип заново")


if __name__ == "__main__":
    main()
