#!/usr/bin/env python3
"""Чистые пакеты VHS Pro: dist/VHS Pro.zip (полная) и dist/VHS Pro Demo.zip (демо)
+ dist/Для магазина/. Установка в Effects/STORYVERSE/VHS, ядро в Fuses.
Запуск: python3 make_release.py
"""
import importlib.util
import os
import re
import shutil
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(HERE, "dist")
CAT = "STORYVERSE/VHS"
DEMO_PRESETS = (0, 2, 6)   # демо: домашняя кассета, хоум-видео 90-х, камкордер с рук
DEMO_KEEP = ("PresetSel", "BtnApply", "ChromaShift", "Snow", "LineJitter")
DEMO_TEXT = "STORYVERSE-CORE-VHS-PRO.DEMO"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def strip_lua_comments(src):
    return "\n".join(l for l in src.split("\n") if not (l.strip().startswith("--") and not l.strip().startswith("--[[")))


def load_builder(demo=False):
    spec = importlib.util.spec_from_file_location("vhs", os.path.join(HERE, "build_vhs_pro.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    if demo:
        names, pres = m.PRESET_NAMES[:], dict(m.PRESETS)
        m.PRESET_NAMES[:] = [names[i] for i in DEMO_PRESETS]
        m.PRESETS.clear()
        m.PRESETS.update({k: pres[i] for k, i in enumerate(DEMO_PRESETS)})
        orig = m.build_ctrl_and_inputs

        def demo_ctrl(values):
            ctrl, gin = orig(values)
            order = ("MainInput1",) + DEMO_KEEP
            keep = [g for g in gin if g.split(" = ", 1)[0] in order]
            keep.sort(key=lambda g: order.index(g.split(" = ", 1)[0]))
            keep = [re.sub(r"\n\tPage = [^\n]*", "", g) for g in keep]
            keep[1] = keep[1].replace("InstanceInput {", 'InstanceInput {\n\tPage = "Controls",', 1)
            return ctrl, keep
        m.build_ctrl_and_inputs = demo_ctrl
        m.OUT_TOOL = "DemoMerge"
        orig_tools = m.build_tools

        def demo_tools(fuse_id="VHSCore"):
            tools = orig_tools(fuse_id)
            txt = m.Tool("DemoText", "TextPlus", (-1300, 80))
            txt.val("UseFrameFormatSettings", 1).val("Width", 1920).val("Height", 1080)
            txt.sval("StyledText", DEMO_TEXT).sval("Font", "Open Sans").sval("Style", "Bold")
            txt.val("Size", 0.035).pt("Center", 0.5, 0.07)
            txt.val("Red1", 1).val("Green1", 1).val("Blue1", 1).val("Alpha1", 0.55)
            mg = m.Tool("DemoMerge", "Merge", (-1150, 0))
            mg.link("Background", "VHSCoreNode").link("Foreground", "DemoText").val("PerformDepthMerge", 0)
            return tools + [txt, mg]
        m.build_tools = demo_tools
    return m


MAC = r'''#!/bin/bash
# @NAME@ — установка для macOS. Двойной клик.
cd "$(dirname "$0")/payload"
FU="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion"
mkdir -p "$FU/Templates/Edit/Effects/@CAT@" "$FU/Fuses"
cp -f Effect/* "$FU/Templates/Edit/Effects/@CAT@/"
cp -f Fuses/* "$FU/Fuses/"
mkdir -p "$FU/Scripts/Comp/vhs-pro" && cp -Rf Presets/* "$FU/Scripts/Comp/vhs-pro/"
echo "@NAME@: эффект установлен."
echo
echo "Готово. Полностью перезапустите DaVinci Resolve (Cmd+Q)."
read -n 1 -s -r -p "Нажмите любую клавишу..."
'''

WIN = r'''@echo off
chcp 65001 >nul
cd /d "%~dp0payload"
set "FU=%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion"
mkdir "%FU%\Templates\Edit\Effects\@WCAT@" 2>nul
mkdir "%FU%\Fuses" 2>nul
xcopy /Y /Q "Effect\*" "%FU%\Templates\Edit\Effects\@WCAT@\" >nul
xcopy /Y /Q "Fuses\*" "%FU%\Fuses\" >nul
mkdir "%FU%\Scripts\Comp\vhs-pro" 2>nul & xcopy /Y /Q /E "Presets\*" "%FU%\Scripts\Comp\vhs-pro\" >nul
echo @NAME@: эффект установлен.
echo.
echo Готово. Полностью перезапустите DaVinci Resolve.
pause
'''

LINUX = r'''#!/bin/bash
# @NAME@ — установка для Linux: bash install-linux.sh
cd "$(dirname "$0")/payload"
FU="$HOME/.local/share/DaVinciResolve/Fusion"
mkdir -p "$FU/Templates/Edit/Effects/@CAT@" "$FU/Fuses"
cp -f Effect/* "$FU/Templates/Edit/Effects/@CAT@/"
cp -f Fuses/* "$FU/Fuses/"
mkdir -p "$FU/Scripts/Comp/vhs-pro" && cp -rf Presets/* "$FU/Scripts/Comp/vhs-pro/"
echo "@NAME@: эффект установлен. Перезапустите DaVinci Resolve."
'''

README = '''@UNAME@ — процедурный VHS-эффект для DaVinci Resolve 18+ (Studio и бесплатная)
=============================================================================

УСТАНОВКА
  macOS   — двойной клик «Установить (macOS).command»
            (если macOS не открывает: правый клик → Открыть)
  Windows — двойной клик «Установить (Windows).bat»
  Linux   — bash install-linux.sh
  После установки полностью перезапустите DaVinci Resolve.

ГДЕ НАЙТИ
  Edit / Cut : Effects → Эффекты → STORYVERSE → VHS → «@NAME@»
  Fusion     : Shift+Пробел → «VHS Core»

КАК ПОЛЬЗОВАТЬСЯ
  • Вкладка «Управление» → «ОКНО ПРЕСЕТОВ»: 13 пресетов с превью, режим магнитофона,
    быстрые кнопки (съёмка с рук, дата, залом, 4:3), свои пресеты ★ со снимком кадра.
  • Или в Инспекторе: пресет → «Применить пресет».
  • Плёнка / Помехи / Камера / Кадр — ручная настройка, описание внизу каждой вкладки.
  • Камера: съёмка с рук, дрожь, шаги, поиск фокуса, дата и время на экране.
  • Эффект считается на видеокарте одной нодой — работает в реальном времени.

ЕСЛИ НЕ ВИДНО КНОПКИ «ОКНО ПРЕСЕТОВ» ИЛИ ЭФФЕКТА
  • Полностью закройте Resolve (Cmd+Q / Alt+F4) и откройте снова.
  • Удалите эффект с клипа и перетащите заново — старые копии на клипах не обновляются.

© STORYVERSE. Лицензия — см. LICENSE.txt
'''

DEMO_NOTE = '''
ДЕМО-ВЕРСИЯ
  Надпись STORYVERSE-CORE-VHS-PRO.DEMO внизу кадра, 3 пресета
  и 3 настройки: сдвиг цвета, снег, дрожание строк.
  Полная версия: 13 пресетов, 58 настроек — съёмка с рук, надписи камеры,
  пауза и перемотка, залом плёнки, свои пресеты — без надписи.
'''

LICENSE = '''@UNAME@ — ЛИЦЕНЗИЯ
Лицензия даёт право одному пользователю устанавливать и использовать эффект
в личных и коммерческих проектах (видео, клипы, реклама) без ограничений.
Запрещено: перепродавать, публиковать или передавать файлы эффекта третьим
лицам, в том числе в изменённом виде.
'''

STORE_TEXT = """VHS PRO — настоящая кассета и камкордер для DaVinci Resolve
============================================================

Не наложение с помехами, а процедурная кассета: картинка проходит через
«магнитофон» на видеокарте — в реальном времени, одной нодой.

ЧТО ВНУТРИ
• Съёмка с рук: блуждание кадра, наклон, дрожь рук, шаги, дыхание зума,
  поиск фокуса и автоэкспозиция — видео выглядит снятым на камкордер
• Надписи камеры: PLAY / PAUSE / REC, дата и идущие часы (свои дата и время)
• Кассета: яркость и цвет размыты по строке, цвет отстаёт, ореол на краях
• Трекинг: дрожание строк, волна, подскок кадра
• Полоса смены головок внизу кадра, снег, цветной шум, белые выпадения
• Залом плёнки, режимы: пауза, перемотка назад и вперёд
• Цвет плёнки: насыщенность, оттенок, тепло, подъём чёрного; формат 4:3
• Окно пресетов с превью: 13 пресетов, режим магнитофона в один клик,
  свои пресеты со снимком кадра, обмен кодом настроек
• Установщики для macOS, Windows и Linux

ТРЕБОВАНИЯ
DaVinci Resolve 18 и новее (Edit, Cut, Fusion). Работает и в бесплатной версии.
"""


def fill(txt, name, demo=False):
    if demo:  # в демо нет окна пресетов
        txt = "\n".join(l for l in txt.split("\n") if "Presets" not in l and "ОКНО" not in l)
    return (txt.replace("@NAME@", name).replace("@UNAME@", name.upper())
               .replace("@CAT@", CAT).replace("@WCAT@", CAT.replace("/", "\\")))


def make_icon(path, demo):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(os.path.join(HERE, "icons", "preset_2.png")).resize((104, 58), Image.LANCZOS)
    im = Image.blend(im, Image.new("RGB", im.size, (10, 10, 16)), 0.35)
    d = ImageDraw.Draw(im)
    d.text((52, 22), "VHS", font=ImageFont.truetype(FONT_B, 20), fill=(255, 255, 255), anchor="mm",
           stroke_width=2, stroke_fill=(0, 0, 0))
    d.text((52, 44), "DEMO" if demo else "PRO", font=ImageFont.truetype(FONT_B, 11), fill=(255, 90, 170),
           anchor="mm", stroke_width=1, stroke_fill=(0, 0, 0))
    im.save(path)


def build_edition(name, demo):
    m = load_builder(demo)
    fuse_id = "VHSCoreDemo" if demo else "VHSCore"
    out = os.path.join(DIST, name)
    P = os.path.join(out, "payload")
    for d in ("Effect", "Fuses"):
        os.makedirs(os.path.join(P, d), exist_ok=True)
    with open(os.path.join(P, "Effect", name + ".setting"), "w", encoding="utf-8") as f:
        f.write(m.build_setting(0, fuse_id))
    make_icon(os.path.join(P, "Effect", name + ".png"), demo)
    if not demo:  # окно пресетов: скрипт + данные + превью
        os.makedirs(os.path.join(P, "Presets", "icons"), exist_ok=True)
        with open(os.path.join(HERE, "VHS Presets.lua"), encoding="utf-8") as f:
            win = strip_lua_comments(f.read())
        with open(os.path.join(P, "Presets", "VHS Presets.lua"), "w", encoding="utf-8") as f:
            f.write(win)
        shutil.copy2(os.path.join(HERE, "vhs_pro_data.lua"), os.path.join(P, "Presets"))
        for fn in os.listdir(os.path.join(HERE, "icons")):
            if fn.endswith(".png"):
                shutil.copy2(os.path.join(HERE, "icons", fn), os.path.join(P, "Presets", "icons"))
    fuse = strip_lua_comments(m.build_fuse())
    if demo:  # своя нода и своё ядро: полная версия не перезапишет демо
        fuse = (fuse.replace('FuRegisterClass("VHSCore"', 'FuRegisterClass("VHSCoreDemo"')
                    .replace('REGS_Name = "VHS Core"', 'REGS_Name = "VHS Core Demo"')
                    .replace('"VHSKernel"', '"VHSKernelDemo"')
                    .replace("void VHSKernel(", "void VHSKernelDemo("))
        assert "VHSCoreDemo" in fuse and "void VHSKernelDemo(" in fuse
    with open(os.path.join(P, "Fuses", fuse_id + ".fuse"), "w", encoding="utf-8") as f:
        f.write(fuse)
    files = {"Установить (macOS).command": fill(MAC, name, demo),
             "Установить (Windows).bat": fill(WIN, name, demo).replace("\n", "\r\n"),
             "install-linux.sh": fill(LINUX, name, demo),
             "README.txt": fill(README, name, demo) + (DEMO_NOTE if demo else ""),
             "LICENSE.txt": fill(LICENSE, name)}
    for fn, txt in files.items():
        with open(os.path.join(out, fn), "w", encoding="utf-8", newline="") as f:
            f.write(txt)
        if fn.endswith((".command", ".sh")):
            os.chmod(os.path.join(out, fn), 0o755)
    zpath = os.path.join(DIST, name + ".zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, fs in os.walk(out):
            for fn in fs:
                full = os.path.join(root, fn)
                info = zipfile.ZipInfo.from_file(full, os.path.relpath(full, DIST))
                if fn.endswith((".command", ".sh")):
                    info.external_attr = (0o755 | 0o100000) << 16
                with open(full, "rb") as fh:
                    z.writestr(info, fh.read(), zipfile.ZIP_DEFLATED)
    print("готово:", zpath)
    return m


def make_store(m):
    from PIL import Image, ImageDraw, ImageFont
    st = os.path.join(DIST, "Для магазина")
    os.makedirs(st, exist_ok=True)
    n, cols, w, h = len(m.PRESET_NAMES), 3, 320, 180
    rows = (n + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w + (cols + 1) * 12, rows * (h + 34) + 12), (14, 15, 20))
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(FONT_R, 15)
    for i, nm in enumerate(m.PRESET_NAMES):
        x, y = 12 + (i % cols) * (w + 12), 12 + (i // cols) * (h + 34)
        sheet.paste(Image.open(os.path.join(HERE, "icons", f"preset_{i}.png")), (x, y))
        d.text((x + 4, y + h + 8), nm, font=f, fill=(214, 216, 226))
    sheet.save(os.path.join(st, "Пресеты.png"))
    W, H = 1920, 1080
    cover = Image.open(os.path.join(HERE, "store_assets", "full_6.png")).resize((W, H), Image.LANCZOS)
    cover = Image.blend(cover, Image.new("RGB", (W, H), (10, 10, 16)), 0.45)
    d = ImageDraw.Draw(cover)
    for off, col in ((-7, (255, 60, 140)), (7, (40, 220, 255)), (0, (255, 255, 255))):
        d.text((W // 2 + off, H // 2 - 60), "VHS PRO", font=ImageFont.truetype(FONT_B, 230), fill=col, anchor="mm")
    d.text((W // 2, H // 2 + 110), "tape  ·  camcorder  ·  DaVinci Resolve", font=ImageFont.truetype(FONT_R, 46),
           fill=(230, 231, 238), anchor="mm")
    cover.save(os.path.join(st, "Обложка.png"))
    shutil.copy2(os.path.join(HERE, "store_assets", "Страница товара.md"), os.path.join(st, "Страница товара.md"))
    with open(os.path.join(st, "Описание товара.txt"), "w", encoding="utf-8") as f:
        f.write(STORE_TEXT)


def main():
    shutil.rmtree(DIST, ignore_errors=True)
    m = build_edition("VHS Pro", False)
    build_edition("VHS Pro Demo", True)
    make_store(m)


if __name__ == "__main__":
    main()
