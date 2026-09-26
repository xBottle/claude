#!/usr/bin/env python3
"""VHS Pro — генератор эффекта для DaVinci Resolve (Edit/Fusion).

Та же система, что CRT Pro: группа с нодой Ctrl (все ползунки) + одно GPU-ядро
VHSCore.fuse. Общие помощники (Tool, контролы, Lua-строки) берутся из
генератора CRT Pro, всё специфичное для VHS — здесь.

Запуск: python3 build_vhs_pro.py        → VHS Pro.setting + VHSCore.fuse рядом
"""
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "crtlib", os.path.join(os.path.dirname(HERE), "crt-2.0", "build_crt_pro_2.py"))
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)
lnum, lstr, lua_value, C, Tool = L.lnum, L.lstr, L.lua_value, L.C, L.Tool
slider, combo, button, note = L.slider, L.combo, L.button, L.note


def check(cid, name, d):
    return C(cid, "check", name, d)

NAME = "VHS Pro"
GROUP = "VHSPro"
CATEGORY = "STORYVERSE/VHS"          # папка в Effects
USER_PRESETS = "VHS Pro User Presets"
SHARE_MODE = True                    # свои пресеты автора в эффект не вшиваются

# ------------------------------------------------------------------ controls
PRESET_NAMES = [
    "Домашняя кассета", "Чистый VHS", "Хоум-видео 90-х", "Затёртая кассета", "Пауза", "Перемотка",
    "Камкордер с рук", "Музыкальный клип", "Ночная съёмка", "Тёплое лето", "Кассета из подвала",
    "Глитч-кассета", "Свадьба 1995",
]

SECTIONS = [
    ("SecPresets", "Пресеты", True, [
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
        check("ScaleRes", "Масштабировать с разрешением", 1),
    ]),
    ("SecTape", "Качество кассеты", True, [
        slider("LumaBlur", "Размытие яркости", 2.5, 0, 10, 0, 40),
        slider("ChromaBlur", "Размытие цвета", 9, 0, 30, 0, 80),
        slider("ChromaShift", "Сдвиг цвета", 3, -15, 15, -60, 60),
        slider("Sharpen", "Ореол на краях", 0.6, 0, 2, 0, 5),
    ]),
    ("SecColor", "Цвет плёнки", True, [
        slider("Sat", "Насыщенность", 0.85, 0, 2, 0, 4),
        slider("Hue", "Оттенок", 0, -30, 30, -180, 180),
        slider("Warmth", "Тепло", 0.1, -1, 1, -3, 3),
        slider("Gain", "Яркость", 1, 0, 2, 0, 4),
        slider("BlackLift", "Подъём чёрного", 0.04, 0, 0.3, 0, 1),
        slider("Contrast", "Контраст", -0.05, -0.5, 0.5, -1, 2),
    ]),
    ("SecTrack", "Трекинг и дрожание", True, [
        check("TrackOn", "Включить", 1),
        slider("LineJitter", "Дрожание строк", 0.6, 0, 6, 0, 40),
        slider("Wobble", "Волна", 0.5, 0, 5, 0, 40),
        slider("WobbleSpeed", "Скорость волны", 1, 0, 5, 0, 20),
        slider("FrameJitter", "Подскок кадра", 0.3, 0, 4, 0, 30),
    ]),
    ("SecHead", "Полоса внизу (смена головок)", True, [
        check("HeadOn", "Включить", 1),
        slider("HeadHeight", "Высота", 0.02, 0, 0.1, 0, 0.5),
        slider("HeadShift", "Сдвиг", 25, 0, 80, 0, 300),
        slider("HeadNoise", "Шум", 0.6, 0, 1, 0, 2),
    ]),
    ("SecNoise", "Снег и выпадения", True, [
        check("NoiseOn", "Включить", 1),
        slider("Snow", "Снег", 0.06, 0, 1, 0, 2),
        slider("ChromaNoise", "Цветной шум", 0.25, 0, 1, 0, 3),
        slider("Dropouts", "Выпадения (белые штрихи)", 0.3, 0, 1, 0, 5),
    ]),
    ("SecCrease", "Залом плёнки", False, [
        check("CreaseOn", "Включить", 0),
        slider("CreaseAmount", "Сила", 0.5, 0, 1, 0, 3),
        slider("CreaseHeight", "Высота полосы", 0.06, 0.01, 0.3, 0.005, 1),
        slider("CreaseSpeed", "Скорость", 0.6, 0.05, 3, 0.01, 10),
        slider("CreaseEvery", "Раз в N секунд", 4, 0.5, 20, 0.1, 120),
    ]),
    ("SecMode", "Режим магнитофона", False, [
        combo("Mode", "Режим", ["Воспроизведение", "Пауза", "Перемотка назад", "Перемотка вперёд"], 0),
        slider("ModeAmount", "Сила", 1, 0, 1, 0, 2),
    ]),
    ("SecCam", "Съёмка с рук", True, [
        check("CamOn", "Включить", 0),
        slider("CamShake", "Блуждание кадра", 0.6, 0, 3, 0, 10),
        slider("CamRot", "Наклон (градусы)", 0.5, 0, 5, 0, 20),
        slider("CamTremor", "Дрожь рук", 0.4, 0, 2, 0, 10),
        slider("CamWalk", "Шаги", 0, 0, 2, 0, 10),
        slider("CamZoom", "Дыхание зума", 0, 0, 1, 0, 3),
        slider("CamSpeed", "Скорость", 1, 0.1, 4, 0.01, 20),
        check("CamFill", "Прятать края (автозум)", 1),
    ]),
    ("SecCamAuto", "Автоматика камеры", False, [
        slider("FocusHunt", "Поиск фокуса", 0, 0, 1, 0, 3),
        slider("ExpoPump", "Автоэкспозиция", 0, 0, 1, 0, 3),
    ]),
    ("SecOSD", "Надписи камеры", False, [
        check("OSDOn", "Включить", 0),
        combo("OSDLabel", "Надпись сверху", ["По режиму (PLAY / PAUSE)", "REC", "Нет"], 0),
        combo("DateFormat", "Формат даты", ["SEP. 26 1996", "26.09.1996", "1996. 9.26"], 0),
        slider("Day", "День", 26, 1, 31, 1, 31, integer=True),
        slider("Month", "Месяц", 9, 1, 12, 1, 12, integer=True),
        slider("Year", "Год", 1996, 1970, 2030, 1900, 2100, integer=True),
        slider("Hour", "Часы", 22, 0, 23, 0, 23, integer=True),
        slider("Minute", "Минуты", 24, 0, 59, 0, 59, integer=True),
        slider("Second", "Секунды", 37, 0, 59, 0, 59, integer=True),
        check("Clock12", "12 часов (AM/PM)", 1),
        check("ClockRun", "Часы идут", 1),
        slider("OSDSize", "Размер", 1, 0.5, 3, 0.2, 8),
        slider("OSDMargin", "Отступ от края", 0.06, 0, 0.2, 0, 0.5),
        slider("OSDOpacity", "Непрозрачность", 0.9, 0, 1, 0, 1),
    ]),
    ("SecFrame", "Кадр", True, [
        check("Aspect43", "Формат 4:3 (чёрные поля)", 0),
        slider("Vignette", "Виньетка", 0.25, 0, 1, 0, 2),
    ]),
]

PAGES = [
    ("Controls", ["SecPresets", "SecGlobal"]),
    ("Плёнка", ["SecTape", "SecColor"]),
    ("Помехи", ["SecTrack", "SecHead", "SecNoise", "SecCrease", "SecMode"]),
    ("Камера", ["SecCam", "SecCamAuto", "SecOSD"]),
    ("Кадр", ["SecFrame"]),
]
_by_id = {sec[0]: sec for sec in SECTIONS}
assert sorted(_by_id) == sorted(i for _, ids in PAGES for i in ids), "PAGES must cover all sections"
PAGE_OF = {i: pg for pg, ids in PAGES for i in ids}
SECTIONS[:] = [_by_id[i] for _, ids in PAGES for i in ids]
TAB_NOTES = {
    "Плёнка": "Вкладка «Плёнка» — как кассета записывает картинку: яркость и цвет размыты по строке, цвет отстаёт, ореол на краях, выцветший цвет плёнки.",
    "Помехи": "Вкладка «Помехи» — всё, что делает магнитофон: дрожание строк, полоса смены головок внизу, снег, белые штрихи, залом плёнки, пауза и перемотка.",
    "Камера": "Вкладка «Камера» — как будто снято на камкордер: съёмка с рук, дрожь, шаги, поиск фокуса, автоэкспозиция и надписи даты/времени.",
    "Кадр": "Вкладка «Кадр» — формат 4:3 с чёрными полями и виньетка.",
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
    1: dict(LumaBlur=1.5, ChromaBlur=5, ChromaShift=2, Sharpen=0.4, Sat=0.95, LineJitter=0.3, Wobble=0.2,
            FrameJitter=0.1, HeadHeight=0.012, HeadShift=12, Snow=0.03, ChromaNoise=0.12, Dropouts=0.1, Vignette=0.15),
    2: dict(CamOn=1, CamShake=0.5, CamRot=0.4, CamTremor=0.3, OSDOn=1, OSDLabel=1, Warmth=0.3, Sat=0.9,
            BlackLift=0.06, FocusHunt=0.25, ExpoPump=0.3),
    3: dict(LumaBlur=4, ChromaBlur=16, ChromaShift=5, Sat=0.6, BlackLift=0.08, LineJitter=1.5, Wobble=1.2,
            FrameJitter=0.8, HeadHeight=0.035, HeadShift=45, Snow=0.2, ChromaNoise=0.6, Dropouts=0.8,
            CreaseOn=1, CreaseAmount=0.6, CreaseEvery=3, Vignette=0.4),
    4: dict(Mode=1, OSDOn=1, OSDLabel=0, LineJitter=1, Snow=0.1),
    5: dict(Mode=2, OSDOn=1, OSDLabel=0, LineJitter=2, Snow=0.15, ChromaNoise=0.4),
    6: dict(CamOn=1, CamShake=1.2, CamRot=1, CamTremor=0.7, CamWalk=0.5, CamZoom=0.3, FocusHunt=0.35,
            ExpoPump=0.4, OSDOn=1, OSDLabel=1),
    7: dict(ChromaShift=6, Sat=1.25, Contrast=0.1, Wobble=1.5, LineJitter=1.2, CreaseOn=1, CreaseAmount=0.8,
            CreaseEvery=2.5, Dropouts=0.5, Vignette=0.35),
    8: dict(Gain=1.3, BlackLift=0.08, Sat=0.5, Snow=0.25, ChromaNoise=0.7, LumaBlur=3.5, ChromaBlur=14,
            Warmth=-0.2, Vignette=0.45, CamOn=1, CamShake=0.4, CamTremor=0.3),
    9: dict(Warmth=0.45, Sat=1.1, Hue=-5, Gain=1.08, BlackLift=0.07, Contrast=-0.1, Vignette=0.3),
    10: dict(LumaBlur=5, ChromaBlur=20, ChromaShift=7, Sat=0.45, Hue=8, BlackLift=0.1, Contrast=-0.15,
             LineJitter=2, Wobble=2, FrameJitter=1.2, HeadHeight=0.05, HeadShift=60, Snow=0.3, ChromaNoise=0.8,
             Dropouts=1, CreaseOn=1, CreaseAmount=0.9, CreaseEvery=2, Aspect43=1, Vignette=0.55),
    11: dict(ChromaShift=10, LineJitter=4, Wobble=2.5, HeadHeight=0.06, HeadShift=70, Dropouts=1,
             CreaseOn=1, CreaseAmount=1, CreaseEvery=1.2, CreaseSpeed=1.5, Sat=1.3),
    12: dict(Aspect43=1, OSDOn=1, OSDLabel=2, Day=17, Month=6, Year=1995, Hour=15, Minute=40, Warmth=0.35,
             Sat=0.9, LumaBlur=3, BlackLift=0.06, CamOn=1, CamShake=0.3, CamTremor=0.2, Vignette=0.35),
}
for _p in PRESETS.values():
    for _k in _p:
        assert _k in DEFAULTS, f"unknown preset key {_k}"


# ------------------------------------------------------------------ button scripts (как в CRT Pro)
def _vhs_lua(txt):
    return (txt.replace("CRT Pro User Presets", USER_PRESETS)
               .replace("Templates/Edit/Effects/Claude/CRT/CRT Pro v2.setting",
                        f"Templates/Edit/Effects/{CATEGORY}/{NAME}.setting")
               .replace(".crtpreset", ".vhspreset").replace("CRTPRO1", "VHSPRO1")
               .replace("CRT Pro", NAME))


LUA_COMMON = _vhs_lua(L.LUA_COMMON)
LUA_ACTIONS = {k: _vhs_lua(v) for k, v in L.LUA_ACTIONS.items() if k != "window"}


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
def build_tools(fuse_id="VHSCore"):
    tools = [Tool("InRouter", "PipeRouter", (-1600, 0), info="PipeRouterInfo")]
    fb = Tool("FocusBlur", "Blur", (-1450, 0))
    pulse = "max(0, sin(time*Ctrl.CamSpeed*0.035))"
    fb.fuid("Filter", "Fast Gaussian")
    fb.expr("XBlurSize", f"Ctrl.CamOn*Ctrl.FocusHunt*8*{pulse}*{pulse}*max(0, sin(time*Ctrl.CamSpeed*0.013 + 1))", 0)
    fb.link("Input", "InRouter")
    tools.append(fb)
    core = Tool("VHSCoreNode", f"Fuse.{fuse_id}", (-1300, 0))
    for k, _ in value_ids():
        core.expr(k, f"Ctrl.{k}", DEFAULTS[k])
    core.link("Input", "FocusBlur").link("Original", "InRouter")
    tools.append(core)
    return tools


OUT_TOOL = "VHSCoreNode"


def build_fuse():
    tpl = open(os.path.join(HERE, "vhs_core_template.fuse"), encoding="utf-8").read()
    font = open(os.path.join(HERE, "font.inc"), encoding="utf-8").read()
    chars = open(os.path.join(HERE, "charset.txt"), encoding="utf-8").read()
    ids = [k for k, _ in value_ids()]
    fields = "\n".join(f"    float {k};" for k in ids)
    create = "    INP = {}\n" + "\n".join(
        f'    INP["{k}"] = self:AddInput("{k}", "{k}", {{ LINKID_DataType = "Number", '
        f'INPID_InputControl = "SliderControl", INP_Default = {lnum(DEFAULTS[k])} }})' for k in ids)
    read = "    for k, inp in pairs(INP) do V[k] = num(inp, req) end"
    return (tpl.replace("__PARAM_FIELDS__", fields).replace("__CREATE_INPUTS__", create)
            .replace("__READ_INPUTS__", read).replace("__FONT__", font.strip())
            .replace("__CHARS__", lstr(chars)))


def build_setting(preset_index=0, fuse_id="VHSCore"):
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


def main():
    with open(os.path.join(HERE, NAME + ".setting"), "w", encoding="utf-8") as f:
        f.write(build_setting(0))
    with open(os.path.join(HERE, "VHSCore.fuse"), "w", encoding="utf-8") as f:
        f.write(build_fuse())
    print("собрано:", NAME + ".setting", "VHSCore.fuse", f"({len(value_ids())} параметров, {len(PRESETS)} пресетов)")


if __name__ == "__main__":
    main()
