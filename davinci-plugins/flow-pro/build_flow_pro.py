#!/usr/bin/env python3
"""Flow Pro — flow edit одной нодой (ремап скорости + наезд/слайд + тряска + смаз + цвет).

Система та же, что CRT Pro / VHS Pro: группа с нодой Ctrl (все ползунки) + GPU-ядро
FlowCore.fuse (+ опционально OpticalFlow/TimeStretcher для качества «как в видео»).
Рабочая установка — Effects → Claude → FLOW (правило: публикация только через релиз в STORYVERSE).

Запуск: python3 build_flow_pro.py            → Flow Pro.setting + FlowCore.fuse + flow_pro_data.lua
        python3 build_flow_pro.py --dev-zip  → dist-dev/Flow Pro (Claude).zip с установщиком в папку Claude
"""
import importlib.util
import os
import shutil
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "crtlib", os.path.join(os.path.dirname(HERE), "crt-2.0", "build_crt_pro_2.py"))
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)
lnum, lstr, lua_value, C, Tool = L.lnum, L.lstr, L.lua_value, L.C, L.Tool
slider, combo, button, note = L.slider, L.combo, L.button, L.note


def check(cid, name, d):
    return C(cid, "check", name, d)


NAME = "Flow Pro"
GROUP = "FlowPro"
CODE = "FLOW"
CATEGORY = "Claude/FLOW"             # рабочая папка; make_release подменит на STORYVERSE/FLOW
SCRIPTS = "flow-pro"
USER_PRESETS = "Flow Pro User Presets"
SHARE_MODE = True

CURVES = ["Удар (быстро → медленно)", "Разгон (медленно → быстро)", "Плавно (S-кривая)",
          "Рывок в середине", "Замирание (удар и стоп)", "Бумеранг (туда-обратно)"]

# ------------------------------------------------------------------ controls
PRESET_NAMES = [
    "Удар", "Мягкий флоу", "Разгон", "Рывок", "Замирание", "Бумеранг", "Толчок камеры",
    "Наезд", "Слайд вправо", "Слайд влево", "Вращение", "Кино", "Сон", "Жёсткий клип",
]

SECTIONS = [
    ("SecPresets", "Пресеты", True, [
        button("BtnWindow", "▣  ОКНО ПРЕСЕТОВ", "window"),
        combo("PresetSel", "Пресет", PRESET_NAMES, 0),
        button("BtnApply", "Применить пресет", "apply"),
        button("BtnSave", "Сохранить мой пресет", "save", 0.5),
        button("BtnLoad", "Загрузить мой пресет", "load", 0.5),
        button("BtnDelete", "Удалить мой пресет", "delete", 0.5),
        button("BtnReset", "Сбросить всё", "reset", 0.5),
        button("BtnCopy", "Скопировать код", "copy", 0.5),
        button("BtnPaste", "Вставить код", "paste", 0.5),
    ]),
    ("SecGlobal", "Общее", True, [
        slider("GlobalMix", "Сила эффекта", 1, 0, 1, 0, 1),
        slider("ClipLen", "Длина клипа, кадров (0 = авто)", 0, 0, 600, 0, 100000, integer=True),
        check("PerfOn", "Замер скорости (в консоль)", 0),
    ]),
    ("SecRamp", "Кривая скорости", True, [
        check("RampOn", "Включить", 1),
        combo("RampType", "Кривая", CURVES, 0),
        slider("RampStrength", "Резкость", 0.6, 0, 1, 0, 2),
        slider("RampAmount", "Сила ремапа", 1, 0, 1, 0, 1),
        slider("HoldPoint", "Точка замирания", 0.35, 0.05, 0.95, 0.05, 0.95),
        combo("Quality", "Качество", ["Кадры (без смешивания)", "Смешивание — реальное время",
                                      "Оптический поток — как в видео (медленно)"], 1),
        slider("TimeBlur", "Смаз на скорости", 0.5, 0, 2, 0, 4),
    ]),
    ("SecMove", "Наезд и слайд", True, [
        check("MoveOn", "Включить", 1),
        combo("MoveType", "Кривая движения", CURVES[:5], 0),
        slider("MoveStrength", "Резкость", 0.6, 0, 1, 0, 2),
        slider("Zoom", "Наезд", 0.08, -0.5, 1, -0.9, 5),
        slider("PanX", "Сдвиг X", 0, -0.5, 0.5, -3, 3),
        slider("PanY", "Сдвиг Y", 0, -0.5, 0.5, -3, 3),
        slider("Rotate", "Поворот (градусы)", 0, -45, 45, -360, 360),
        combo("EdgeMode", "Края", ["Зеркало (как в видео)", "Чёрные", "Автозум (без пустых краёв)"], 0),
    ]),
    ("SecShake", "Тряска", True, [
        check("ShakeOn", "Включить", 1),
        combo("ShakeMode", "Когда", ["Удар в начале", "Постоянно", "Удар в конце"], 0),
        slider("ShakeAmount", "Сила", 0.8, 0, 3, 0, 10),
        slider("ShakeDecay", "Затухание (доля клипа)", 0.35, 0.02, 1, 0.01, 1),
        slider("ShakeX", "По X", 1, 0, 3, 0, 10),
        slider("ShakeY", "По Y", 0.6, 0, 3, 0, 10),
        slider("ShakeRot", "Наклон (градусы)", 1.5, 0, 10, 0, 45),
        slider("ShakeFreq", "Частота", 2, 0.05, 30, 0.01, 100),
        slider("ShakeSeed", "Рисунок (seed)", 0, 0, 99, 0, 9999, integer=True),
        slider("MotionBlur", "Смаз движения камеры", 0.5, 0, 2, 0, 5),
    ]),
    ("SecWhip", "Слайд-переход (смаз)", False, [
        check("WhipOn", "Включить", 0),
        combo("WhipDir", "Направление", ["Влево", "Вправо", "Вверх", "Вниз"], 1),
        check("WhipIn", "На входе в клип", 1),
        check("WhipOut", "На выходе из клипа", 1),
        slider("WhipAmount", "Сила сдвига", 0.6, 0, 2, 0, 5),
        slider("WhipFrames", "Длина, кадров", 6, 1, 30, 1, 200, integer=True),
        slider("WhipBlur", "Смаз", 1, 0, 3, 0, 10),
    ]),
    ("SecLook", "Цвет", True, [
        check("LookOn", "Включить", 1),
        slider("Exposure", "Экспозиция", 0, -2, 2, -6, 6),
        slider("Contrast", "Контраст", 0.1, -0.5, 1, -1, 3),
        slider("Sat", "Насыщенность", 1, 0, 2, 0, 4),
        slider("Warmth", "Тепло", 0, -1, 1, -3, 3),
        slider("Vignette", "Виньетка", 0.25, 0, 1, 0, 2),
    ]),
    ("SecGlow", "Свечение", False, [
        check("GlowOn", "Включить", 0),
        slider("GlowThreshold", "Порог", 0.5, 0, 1, 0, 1),
        slider("GlowGain", "Сила", 1, 0, 5, 0, 20),
        slider("GlowSize", "Размер", 12, 0, 60, 0, 300),
    ]),
    ("SecFade", "Затемнение", False, [
        slider("FadeIn", "Из чёрного, кадров", 0, 0, 48, 0, 1000, integer=True),
        slider("FadeOut", "В чёрный, кадров", 0, 0, 48, 0, 1000, integer=True),
    ]),
]

PAGES = [
    ("Controls", ["SecPresets", "SecGlobal"]),
    ("Скорость", ["SecRamp"]),
    ("Камера", ["SecMove", "SecShake", "SecWhip"]),
    ("Вид", ["SecLook", "SecGlow", "SecFade"]),
]
_by_id = {sec[0]: sec for sec in SECTIONS}
assert sorted(_by_id) == sorted(i for _, ids in PAGES for i in ids), "PAGES must cover all sections"
PAGE_OF = {i: pg for pg, ids in PAGES for i in ids}
SECTIONS[:] = [_by_id[i] for _, ids in PAGES for i in ids]
TAB_NOTES = {
    "Скорость": "Вкладка «Скорость» — ремап времени по всей длине клипа: движение стартует резко и доезжает плавно (или наоборот). «Оптический поток» — как в видео-гайде: плавнее, но не в реальном времени.",
    "Камера": "Вкладка «Камера» — наезд/слайд/поворот со своей кривой, тряска-удар с затуханием и слайд-переход со смазом на входе и выходе клипа.",
    "Вид": "Вкладка «Вид» — цвет, виньетка, свечение и затемнение из чёрного / в чёрный.",
}


def value_ids():
    out = []
    for _, _, _, items in SECTIONS:
        for c in items:
            if c.kind in ("slider", "check", "combo") and c.id != "PresetSel":
                out.append((c.id, c.default))
    return out


DEFAULTS = dict(value_ids())

PRESETS = {
    0: {},
    1: dict(RampType=2, RampStrength=0.4, MoveType=2, Zoom=0.05, ShakeAmount=0.4, TimeBlur=0.8),
    2: dict(RampType=1, RampStrength=0.6, MoveType=1, Zoom=0.12, ShakeMode=2, WhipOn=1, WhipIn=0, WhipOut=1),
    3: dict(RampType=3, RampStrength=0.75, ShakeAmount=1.2, Zoom=0.06),
    4: dict(RampType=4, HoldPoint=0.3, RampStrength=0.7, Zoom=0.06, ShakeAmount=1.0),
    5: dict(RampType=5, RampStrength=0.5, MoveOn=0, ShakeOn=0),
    6: dict(RampOn=0, MoveOn=0, ShakeAmount=1.6, ShakeRot=3, ShakeDecay=0.3, MotionBlur=0.8),
    7: dict(RampOn=0, Zoom=0.18, MoveStrength=0.8, ShakeOn=0),
    8: dict(RampOn=0, MoveOn=0, ShakeOn=0, WhipOn=1, WhipDir=1, WhipAmount=0.8),
    9: dict(RampOn=0, MoveOn=0, ShakeOn=0, WhipOn=1, WhipDir=0, WhipAmount=0.8),
    10: dict(Rotate=6, Zoom=0.1, MoveStrength=0.7, ShakeAmount=0.5, EdgeMode=0),
    11: dict(RampType=2, RampStrength=0.5, Zoom=0.05, Contrast=0.2, Sat=0.9, Warmth=0.15, Vignette=0.45,
             GlowOn=1, GlowThreshold=0.55, GlowGain=0.8, FadeOut=6, ShakeAmount=0.4),
    12: dict(RampType=2, RampStrength=0.4, TimeBlur=1.2, GlowOn=1, GlowThreshold=0.35, GlowGain=1.2,
             Exposure=0.1, Contrast=-0.05, Warmth=0.2, ShakeOn=0, Zoom=0.04),
    13: dict(RampStrength=1, ShakeAmount=2, ShakeRot=3, Zoom=0.2, MoveStrength=0.9, WhipOn=1, WhipIn=0,
             WhipOut=1, WhipDir=1, Contrast=0.3, Vignette=0.4),
}
for _p in PRESETS.values():
    for _k in _p:
        assert _k in DEFAULTS, f"unknown preset key {_k}"


# ------------------------------------------------------------------ кривая (одна формула для Fuse и TimeStretcher)
# x — положение в клипе 0..1, T — тип кривой, k — резкость (1..5), a — сила (0..1), h — точка замирания
CURVE_LUA = ("(function(x, T, k, a, h) local y "
             "if T < 0.5 then y = 1 - (1 - x) ^ k "
             "elseif T < 1.5 then y = x ^ k "
             "elseif T < 2.5 then if x < 0.5 then y = 0.5 * (2 * x) ^ k else y = 1 - 0.5 * (2 - 2 * x) ^ k end "
             "elseif T < 3.5 then if x < 0.5 then y = 0.5 * (1 - (1 - 2 * x) ^ k) else y = 0.5 + 0.5 * (2 * x - 1) ^ k end "
             "elseif T < 4.5 then h = math.min(0.95, math.max(0.05, h)) "
             "if x < h then y = 0.92 * (1 - (1 - x / h) ^ k) else y = 0.92 + 0.08 * (x - h) / (1 - h) end "
             "else if x < 0.5 then y = 1 - (1 - 2 * x) ^ k else y = 1 - (2 * x - 1) ^ k end end "
             "return x + (y - x) * a end)")


def curve_py(x, T, k, a=1.0, h=0.35):
    """Та же кривая на Python — для иконок и превью."""
    if T < 0.5: y = 1 - (1 - x) ** k
    elif T < 1.5: y = x ** k
    elif T < 2.5: y = 0.5 * (2 * x) ** k if x < 0.5 else 1 - 0.5 * (2 - 2 * x) ** k
    elif T < 3.5: y = 0.5 * (1 - (1 - 2 * x) ** k) if x < 0.5 else 0.5 + 0.5 * (2 * x - 1) ** k
    elif T < 4.5:
        h = min(0.95, max(0.05, h))
        y = 0.92 * (1 - (1 - x / h) ** k) if x < h else 0.92 + 0.08 * (x - h) / (1 - h)
    else: y = 1 - (1 - 2 * x) ** k if x < 0.5 else 1 - (2 * x - 1) ** k
    return x + (y - x) * a


def source_time_expr():
    """Выражение Source Time для TimeStretcher (режим «Оптический поток»)."""
    lm1 = "max(1, (Ctrl.ClipLen > 1.5 and Ctrl.ClipLen - 1 or comp.RenderEnd - comp.RenderStart))"
    x = f"min(1, max(0, (time - comp.RenderStart) / {lm1}))"
    return (f"Ctrl.RampOn > 0.5 and (comp.RenderStart + {lm1} * {CURVE_LUA}({x}, Ctrl.RampType, "
            f"1 + Ctrl.RampStrength * 4, Ctrl.RampAmount, Ctrl.HoldPoint)) or time")


# ------------------------------------------------------------------ button scripts (как в CRT Pro)
def _flow_lua(txt):
    return (txt.replace("CRT Pro User Presets", USER_PRESETS)
               .replace("Templates/Edit/Effects/Claude/CRT/CRT Pro v2.setting",
                        f"Templates/Edit/Effects/{CATEGORY}/{NAME}.setting")
               .replace(".crtpreset", ".flowpreset").replace("CRTPRO1", "FLOWPRO1")
               .replace("CRT Pro", NAME))


LUA_COMMON = _flow_lua(L.LUA_COMMON)
LUA_ACTIONS = {k: _flow_lua(v) for k, v in L.LUA_ACTIONS.items() if k != "window"}
LUA_ACTIONS["window"] = r'''
local script = FU .. "Scripts/Comp/__SCRIPTS__/Flow Presets.lua"
if not bmd.fileexists(script) then say("Flow Pro", "Не найдено окно пресетов:\n" .. script) return end
_G.FLOW_TOOL = tool
local ok, err = pcall(dofile, script)
_G.FLOW_TOOL = nil
if not ok then say("Flow Pro", "Ошибка окна пресетов: " .. tostring(err)) end
'''.replace("__SCRIPTS__", SCRIPTS)


def write_data():
    """flow_pro_data.lua — пресеты для окна (чтобы не расходились с эффектом)."""
    out = ["-- Автосгенерировано build_flow_pro.py — не редактировать руками.", "return {"]
    out.append("  PRESET_NAMES = { " + ", ".join(lstr(n) for n in PRESET_NAMES) + " },")
    out.append("  CURVES = { " + ", ".join(lstr(n) for n in CURVES) + " },")
    out.append("  DEFAULTS = { " + ", ".join(f"{k} = {lnum(v)}" for k, v in DEFAULTS.items()) + " },")
    out.append("  PRESETS = {")
    for i, p in PRESETS.items():
        out.append(f"    [{i}] = {{ " + ", ".join(f"{k} = {lnum(v)}" for k, v in p.items()) + " },")
    out.append("  },")
    out.append("}")
    with open(os.path.join(HERE, "flow_pro_data.lua"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def lua_presets():
    parts = []
    for i, p in PRESETS.items():
        parts.append(f"[{i}] = " + ("{ " + ", ".join(f"{k} = {lnum(v)}" for k, v in p.items()) + " }" if p else "{}"))
    return "{ " + ", ".join(parts) + " }"


def button_script(action):
    script = LUA_COMMON.strip() + "\n" + LUA_ACTIONS[action].strip() + "\n"
    return (script.replace("__IDS__", "{ " + ", ".join(lstr(k) for k, _ in value_ids()) + " }")
            .replace("__DEF__", "{ " + ", ".join(f"{k} = {lnum(v)}" for k, v in value_ids()) + " }")
            .replace("__PRESETS__", lua_presets())
            .replace("__NAMES__", "{ " + ", ".join(f"[{i}] = {lstr(n)}" for i, n in enumerate(PRESET_NAMES)) + " }")
            .replace("__USER__", "{}"))


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
    elif c.kind == "note":
        base.update(INPID_InputControl="LabelControl", LBLC_MultiLine=True, INP_External=False,
                    INP_Passive=True, IC_NoLabel=False, INP_Default=0)
    body = ", ".join(f"{k} = {lua_value(v)}" for k, v in base.items())
    if c.kind == "combo":
        opts = ", ".join(f"{{ CCS_AddString = {lstr(o)} }}" for o in c.options)
        body = (opts + ", " + body + f", INPID_InputControl = \"ComboControl\", INP_Integer = true, "
                f"INP_External = false, CC_LabelPosition = \"Horizontal\", INP_Default = {lnum(c.default)}, "
                f"INP_MinScale = 0, INP_MaxScale = {len(c.options) - 1}, INP_MinAllowed = 0, "
                f"INP_MaxAllowed = {len(c.options) - 1}")
    return f"{c.id} = {{ {body} }}"


def build_ctrl_and_inputs(values):
    ctrl = Tool("Ctrl", "Background", (-1100, -250))
    ctrl.val("Width", 1).val("Height", 1).val("UseFrameFormatSettings", 0)
    ctrl.user_controls = []
    gin = ["MainInput1 = InstanceInput {\n\tSourceOp = \"InRouter\",\n\tSource = \"Input\",\n}"]
    cur = [None]

    def page_fix(txt, pg):
        return txt.replace('ICS_ControlPage = "Controls"', "ICS_ControlPage = " + lstr(pg))

    def flush_note(new_page):
        pg = cur[0]
        if pg and pg in TAB_NOTES and pg != new_page:
            nid = "Tab" + str(list(TAB_NOTES).index(pg)) + "Info"
            ctrl.user_controls.append(page_fix(uc_def(note(nid, TAB_NOTES[pg])), pg))
            gin.append(f"{nid} = InstanceInput {{\n\tSourceOp = \"Ctrl\",\n\tSource = \"{nid}\",\n}}")

    for sid, sname, is_open, items in SECTIONS:
        pg = PAGE_OF[sid]
        flush_note(pg)
        lab = C(sid, "label", sname, is_open=is_open)
        lab.count = len(items)
        ctrl.val(sid, 1 if is_open else 0)
        ctrl.user_controls.append(page_fix(uc_def(lab), pg))
        page = f'\n\tPage = {lstr(pg)},' if pg != cur[0] else ""
        cur[0] = pg
        gin.append(f"{sid} = InstanceInput {{\n\tSourceOp = \"Ctrl\",\n\tSource = \"{sid}\",{page}\n}}")
        for c in items:
            ctrl.user_controls.append(page_fix(uc_def(c), pg))
            extra = ""
            if c.kind == "button":
                if c.width != 1.0:
                    extra = f"\n\tWidth = {lnum(c.width)},"
            else:
                v = values.get(c.id, c.default)
                ctrl.val(c.id, v)
                extra = f"\n\tDefault = {lnum(v)},"
            gin.append(f"{c.id} = InstanceInput {{\n\tSourceOp = \"Ctrl\",\n\tSource = \"{c.id}\",{extra}\n}}")
    flush_note(None)
    return ctrl, gin


# ------------------------------------------------------------------ tools
def build_tools(fuse_id="FlowCore"):
    tools = [Tool("InRouter", "PipeRouter", (-1600, 0), info="PipeRouterInfo")]
    # ветка «Оптический поток» (как в гайде): OpticalFlow → TimeStretcher (Flow) по той же кривой
    of = Tool("OptFlow", "OpticalFlow", (-1480, 110))
    of.link("Input", "InRouter")
    tools.append(of)
    ts = Tool("TSFlow", "TimeStretcher", (-1360, 110))
    ts.expr("SourceTime", source_time_expr(), 0)
    ts.val("InterpolationMode", 2).val("InterpolateBetweenFrames", 2).val("DepthOrdering", 0)
    ts.val("ClampEdges", 1).val("EdgeSoftness", 0.01)
    ts.link("Input", "OptFlow")
    tools.append(ts)
    sw = Tool("QSwitch", "Dissolve", (-1240, 0))
    sw.link("Background", "InRouter").link("Foreground", "TSFlow")
    sw.expr("Mix", "(Ctrl.RampOn > 0.5 and Ctrl.Quality > 1.5) and 1 or 0", 0)
    tools.append(sw)
    core = Tool("FlowCoreNode", f"Fuse.{fuse_id}", (-1110, 0))
    for k, _ in value_ids():
        core.expr(k, f"Ctrl.{k}", DEFAULTS[k])
    core.link("Input", "QSwitch").link("Original", "InRouter")
    tools.append(core)
    glow = Tool("Glow", "SoftGlow", (-980, 0))
    glow.expr("Threshold", "Ctrl.GlowThreshold", 0.5).expr("Gain", "Ctrl.GlowGain", 1)
    glow.expr("XGlowSize", "Ctrl.GlowOn*Ctrl.GlowSize", 0).expr("Blend", "Ctrl.GlowOn", 0)
    glow.link("Input", "FlowCoreNode")
    tools.append(glow)
    return tools


OUT_TOOL = "Glow"


def build_fuse(category=None):
    tpl = open(os.path.join(HERE, "flow_core_template.fuse"), encoding="utf-8").read()
    ids = [k for k, _ in value_ids()]
    fields = "\n".join(f"    float {k};" for k in ids)
    create = "    INP = {}\n" + "\n".join(
        f'    INP["{k}"] = self:AddInput("{k}", "{k}", {{ LINKID_DataType = "Number", '
        f'INPID_InputControl = "SliderControl", INP_Default = {lnum(DEFAULTS[k])} }})' for k in ids)
    read = "    for k, inp in pairs(INP) do V[k] = num(inp, req) end"
    cat = (category or CATEGORY).replace("/", "\\")
    return (tpl.replace("__PARAM_FIELDS__", fields).replace("__CREATE_INPUTS__", create)
            .replace("__READ_INPUTS__", read).replace("__CURVE__", CURVE_LUA).replace("__CATEGORY__", cat))


def build_setting(preset_index=0, fuse_id="FlowCore"):
    values = dict(DEFAULTS)
    values.update(PRESETS[preset_index])
    values["PresetSel"] = preset_index
    ctrl, gin = build_ctrl_and_inputs(values)
    tools = [ctrl] + build_tools(fuse_id)
    ind = "\t\t\t\t"
    inputs_txt = ",\n".join(ind + g.replace("\n", "\n" + ind) for g in gin)
    tools_txt = ",\n".join(t.render(4) for t in tools)
    return (
        "{\n\tTools = ordered() {\n"
        f"\t\t{GROUP} = GroupOperator {{\n\t\t\tCtrlWZoom = false,\n\t\t\tNameSet = true,\n"
        "\t\t\tInputs = ordered() {\n" + inputs_txt + ",\n\t\t\t},\n"
        "\t\t\tOutputs = {\n\t\t\t\tMainOutput1 = InstanceOutput {\n"
        f"\t\t\t\t\tSourceOp = \"{OUT_TOOL}\",\n"
        "\t\t\t\t\tSource = \"Output\",\n\t\t\t\t},\n\t\t\t},\n"
        "\t\t\tViewInfo = GroupInfo { Pos = { 0, 0 } },\n"
        "\t\t\tTools = ordered() {\n" + tools_txt + ",\n\t\t\t},\n\t\t},\n\t},\n"
        f"\tActiveTool = \"{GROUP}\",\n}}\n"
    )


# ------------------------------------------------------------------ рабочий пакет (папка Claude)
DEV_MAC = """#!/bin/bash
# Flow Pro — РАБОЧАЯ установка в папку Claude (не для покупателей)
cd "$(dirname "$0")/payload" || exit 1
FU="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion"
mkdir -p "$FU/Templates/Edit/Effects/Claude/FLOW" "$FU/Fuses" "$FU/Scripts/Comp/flow-pro"
cp -Rf Effect/. "$FU/Templates/Edit/Effects/Claude/FLOW/"
cp -Rf Fuses/. "$FU/Fuses/"
cp -Rf Presets/. "$FU/Scripts/Comp/flow-pro/"
xattr -dr com.apple.quarantine "$FU/Templates/Edit/Effects/Claude/FLOW" "$FU/Fuses/FlowCore.fuse" "$FU/Scripts/Comp/flow-pro" 2>/dev/null
echo "Flow Pro установлен в Effects → Claude → FLOW. Перезапустите DaVinci Resolve (Cmd+Q)."
"""

DEV_WIN = "\r\n".join([
    "@echo off", "chcp 65001 >nul", 'cd /d "%~dp0payload"',
    'set "FU=%APPDATA%\\Blackmagic Design\\DaVinci Resolve\\Support\\Fusion"',
    'xcopy /Y /Q /E /I "Effect\\*" "%FU%\\Templates\\Edit\\Effects\\Claude\\FLOW\\" >nul',
    'xcopy /Y /Q /E /I "Fuses\\*" "%FU%\\Fuses\\" >nul',
    'xcopy /Y /Q /E /I "Presets\\*" "%FU%\\Scripts\\Comp\\flow-pro\\" >nul',
    "echo Flow Pro установлен в Effects - Claude - FLOW. Перезапустите DaVinci Resolve.", "pause", ""])


def dev_zip():
    sys.path.insert(0, os.path.dirname(HERE))
    import storyverse_style as SV
    from PIL import Image
    out = os.path.join(HERE, "dist-dev", "Flow Pro (Claude)")
    shutil.rmtree(os.path.join(HERE, "dist-dev"), ignore_errors=True)
    P = os.path.join(out, "payload")
    for d in ("Effect", "Fuses", "Presets/icons"):
        os.makedirs(os.path.join(P, d), exist_ok=True)
    shutil.copy2(os.path.join(HERE, NAME + ".setting"), os.path.join(P, "Effect"))
    SV.library_icon(Image.open(os.path.join(HERE, "store_assets", "cover_bg.png")), CODE).save(
        os.path.join(P, "Effect", NAME + ".png"))
    shutil.copy2(os.path.join(HERE, "FlowCore.fuse"), os.path.join(P, "Fuses"))
    shutil.copy2(os.path.join(HERE, "Flow Presets.lua"), os.path.join(P, "Presets"))
    shutil.copy2(os.path.join(HERE, "flow_pro_data.lua"), os.path.join(P, "Presets"))
    for fn in os.listdir(os.path.join(HERE, "icons")):
        shutil.copy2(os.path.join(HERE, "icons", fn), os.path.join(P, "Presets", "icons"))
    for fn, txt in (("Установить в Claude (macOS).command", DEV_MAC), ("Установить в Claude (Windows).bat", DEV_WIN)):
        with open(os.path.join(out, fn), "w", encoding="utf-8", newline="") as f:
            f.write(txt)
        os.chmod(os.path.join(out, fn), 0o755)
    zpath = os.path.join(HERE, "dist-dev", "Flow Pro (Claude).zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, fs in os.walk(out):
            for fn in fs:
                full = os.path.join(root, fn)
                info = zipfile.ZipInfo.from_file(full, os.path.relpath(full, os.path.dirname(out)))
                if fn.endswith(".command"):
                    info.external_attr = (0o755 | 0o100000) << 16
                with open(full, "rb") as fh:
                    z.writestr(info, fh.read(), zipfile.ZIP_DEFLATED)
    print("рабочий пакет:", zpath)


def main():
    with open(os.path.join(HERE, NAME + ".setting"), "w", encoding="utf-8") as f:
        f.write(build_setting(0))
    with open(os.path.join(HERE, "FlowCore.fuse"), "w", encoding="utf-8") as f:
        f.write(build_fuse())
    write_data()
    print("собрано:", NAME + ".setting", "FlowCore.fuse", f"({len(value_ids())} параметров, {len(PRESETS)} пресетов)")
    if "--dev-zip" in sys.argv:
        dev_zip()


if __name__ == "__main__":
    main()
