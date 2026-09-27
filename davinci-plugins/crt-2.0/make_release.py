#!/usr/bin/env python3
"""Собирает чистую папку для продажи/раздачи: dist/CRT Pro/ и dist/CRT Pro Demo/ + zip.
В пакет попадает только то, что нужно покупателю: файлы эффекта и установщики
для macOS, Windows и Linux. Исходники, генераторы, валидаторы — не попадают.

Запуск: python3 make_release.py
"""
import os
import re
import shutil
import zipfile
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = "CRT Pro v2"            # имя исходников в репозитории
DIST = os.path.join(HERE, "dist")
DEMO_PRESETS = (0, 1, 3)       # пресеты демо: по умолчанию, классический ТВ, зелёный терминал
DEMO_KEEP = ("PresetSel", "BtnApply", "PixSize", "PixBright", "PixGamma")
# Публичные пути (не пересекаются с CRT Pro 1.0 в Claude/CRT)
CAT, SCR, LUTD = "STORYVERSE/CRT", "crt-pro", "STORYVERSE"


def load_builder(demo=False):
    spec = importlib.util.spec_from_file_location("b", os.path.join(HERE, "build_crt_pro_2.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.SHARE_MODE = True  # свои пресеты автора в продаваемый пакет не попадают
    if demo:  # демо: 3 пресета и 4 крутилки, остальное спрятано внутри группы
        names, pres = m.PRESET_NAMES[:], dict(m.PRESETS)
        m.PRESET_NAMES[:] = [names[i] for i in DEMO_PRESETS]
        m.PRESETS.clear()
        m.PRESETS.update({k: pres[i] for k, i in enumerate(DEMO_PRESETS)})
        m.own_presets = lambda: []
        orig = m.build_ctrl_and_inputs

        def demo_ctrl(values):
            ctrl, gin = orig(values)
            keep = [g for g in gin if g.split(" = ", 1)[0] in ("MainInput1",) + DEMO_KEEP]
            keep.sort(key=lambda g: (("MainInput1",) + DEMO_KEEP).index(g.split(" = ", 1)[0]))
            keep = [re.sub(r"\n\tPage = [^\n]*", "", g) for g in keep]
            keep[1] = keep[1].replace("InstanceInput {", 'InstanceInput {\n\tPage = "Controls",', 1)
            return ctrl, keep
        m.build_ctrl_and_inputs = demo_ctrl
    return m


DEMO_TOOLS = """
				DemoText = TextPlus {
					Inputs = {
						UseFrameFormatSettings = Input { Value = 1, },
						Width = Input { Value = 1920, },
						Height = Input { Value = 1080, },
						StyledText = Input { Value = "STORYVERSE-CORE-CRT-PRO.DEMO", },
						Font = Input { Value = "Open Sans", },
						Style = Input { Value = "Bold", },
						Size = Input { Value = 0.035, },
						Center = Input { Value = { 0.5, 0.07 }, },
						Red1 = Input { Value = 1, },
						Green1 = Input { Value = 1, },
						Blue1 = Input { Value = 1, },
						Alpha1 = Input { Value = 0.55, },
					},
					ViewInfo = OperatorInfo { Pos = { -795, 80 } },
				},
				DemoMerge = Merge {
					Inputs = {
						Background = Input { SourceOp = "FinalMix", Source = "Output", },
						Foreground = Input { SourceOp = "DemoText", Source = "Output", },
						PerformDepthMerge = Input { Value = 0, },
					},
					ViewInfo = OperatorInfo { Pos = { -685, 0 } },
				},
"""


def add_demo_mark(st):
    """Одна надпись внизу по центру штатными нодами Text+ и Merge поверх результата."""
    out = 'MainOutput1 = InstanceOutput {\n\t\t\t\t\tSourceOp = "FinalMix",'
    end = "\t\t\t},\n\t\t},\n\t},\n\tActiveTool"
    assert out in st and st.count(end) == 1
    st = st.replace(out, out.replace("FinalMix", "DemoMerge"))
    return st.replace(end, DEMO_TOOLS.lstrip("\n") + end)


def publicize(src, name):
    return (src.replace("Templates/Edit/Effects/Claude/CRT/CRT Pro v2.setting", f"Templates/Edit/Effects/{CAT}/{name}.setting")
               .replace("Scripts/Comp/crt-2.0/", f"Scripts/Comp/{SCR}/")
               .replace("CRT Pro v2", name).replace("CRT PRO v2", "CRT PRO"))


def strip_lua_comments(src):
    """Убирает строки-комментарии Lua (-- ...) — меньше «внутренностей» в поставке."""
    out = []
    for line in src.split("\n"):
        t = line.strip()
        if t.startswith("--") and not t.startswith("--[["):
            continue
        out.append(line)
    return "\n".join(out)


MAC = r'''#!/bin/bash
# @NAME@ — установка для macOS. Двойной клик.
cd "$(dirname "$0")/payload"
FU="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion"
mkdir -p "$FU/Templates/Edit/Effects/@CAT@" "$FU/Fuses" "$FU/Scripts/Comp/@SCR@"
cp -f Effect/* "$FU/Templates/Edit/Effects/@CAT@/"
cp -f Fuses/* "$FU/Fuses/"
cp -Rf Presets/* "$FU/Scripts/Comp/@SCR@/"
echo "@NAME@: эффект установлен."
SYS="/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/@LUT@"
echo "Для страницы Color нужен пароль администратора (можно пропустить: Ctrl+C):"
sudo mkdir -p "$SYS" && sudo cp -f Color/* "$SYS/" && echo "DCTL для страницы Color установлен."
echo
echo "Готово. Перезапустите DaVinci Resolve."
read -n 1 -s -r -p "Нажмите любую клавишу..."
'''

WIN = r'''@echo off
chcp 65001 >nul
REM @NAME@ — установка для Windows. Двойной клик (для страницы Color — «Запуск от имени администратора»).
cd /d "%~dp0payload"
set "FU=%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion"
mkdir "%FU%\Templates\Edit\Effects\@CAT@" 2>nul
mkdir "%FU%\Fuses" 2>nul
mkdir "%FU%\Scripts\Comp\@SCR@" 2>nul
xcopy /Y /Q "Effect\*" "%FU%\Templates\Edit\Effects\@CAT@\" >nul
xcopy /Y /Q "Fuses\*" "%FU%\Fuses\" >nul
xcopy /Y /Q /E "Presets\*" "%FU%\Scripts\Comp\@SCR@\" >nul
echo @NAME@: эффект установлен.
set "LUT=%ProgramData%\Blackmagic Design\DaVinci Resolve\Support\LUT\@LUT@"
mkdir "%LUT%" 2>nul
xcopy /Y /Q "Color\*" "%LUT%\" >nul && echo DCTL для страницы Color установлен. || echo Для страницы Color запустите установщик от имени администратора.
echo.
echo Готово. Перезапустите DaVinci Resolve.
pause
'''

LINUX = r'''#!/bin/bash
# @NAME@ — установка для Linux: bash install-linux.sh
cd "$(dirname "$0")/payload"
FU="$HOME/.local/share/DaVinciResolve/Fusion"
mkdir -p "$FU/Templates/Edit/Effects/@CAT@" "$FU/Fuses" "$FU/Scripts/Comp/@SCR@"
cp -f Effect/* "$FU/Templates/Edit/Effects/@CAT@/"
cp -f Fuses/* "$FU/Fuses/"
cp -rf Presets/* "$FU/Scripts/Comp/@SCR@/"
echo "@NAME@: эффект установлен."
if [ -d /opt/resolve/LUT ]; then
  sudo mkdir -p /opt/resolve/LUT/@LUT@ && sudo cp -f Color/* /opt/resolve/LUT/@LUT@/ && echo "DCTL установлен."
fi
echo "Готово. Перезапустите DaVinci Resolve."
'''

README = '''@UNAME@ — процедурный CRT-эффект для DaVinci Resolve 18+ (Studio / Free*)
=========================================================================

УСТАНОВКА
  macOS   — двойной клик «Установить (macOS).command»
            (если macOS не открывает: правый клик → Открыть)
  Windows — двойной клик «Установить (Windows).bat»
            (для страницы Color — правый клик → Запуск от имени администратора)
  Linux   — bash install-linux.sh
  После установки перезапустите DaVinci Resolve.

ГДЕ НАЙТИ
  Edit / Cut : Effects → Эффекты → STORYVERSE → CRT → «@NAME@»
  Fusion     : Shift+Пробел → «CRT Core»
  Color      : Effects → DCTL → в списке DCTL выбрать @LUT@ / @NAME@

КАК ПОЛЬЗОВАТЬСЯ
  • Вкладка «Управление» → «ОКНО ПРЕСЕТОВ»: 18 пресетов с превью (список с прокруткой),
    10 узоров пикселей, свои пресеты ★ со снимком кадра, код настроек в буфер/из буфера.
  • Вкладки Пиксели / Экран / Цвет / Помехи — ручная настройка.
  • Эффект считается на видеокарте (≈1–2 мс на кадр 1080p).
  • Не накладывайте эффект одновременно на Edit и на Color — двойная сетка даёт муар.

* Страница Color (DCTL) работает в DaVinci Resolve Studio.

© CRT Pro. Лицензия — см. LICENSE.txt
'''

LICENSE = '''@UNAME@ — ЛИЦЕНЗИЯ
Лицензия даёт право одному пользователю устанавливать и использовать эффект
в личных и коммерческих проектах (видео, клипы, реклама) без ограничений.
Запрещено: перепродавать, публиковать или передавать файлы эффекта третьим
лицам, в том числе в изменённом виде.
'''


STORE_TEXT = """@UNAME@ — процедурный CRT для DaVinci Resolve
====================================================

Настоящие пиксели кинескопа, а не наложенная картинка. Эффект считается
на видеокарте формулами — ~1 мс на кадр 1080p, реальное время.

ЧТО ВНУТРИ
• 18 готовых пресетов: от классического ТВ и VHS до неонового клуба и глитч-клипа
• 10 узоров пикселей: апертурная решётка (Trinitron), щелевая и теневая маски,
  LCD, LED-стена, точечная матрица и др.
• Плавный размер пикселя, настоящий / имитационный / разделённый RGB
• Строки развёртки, сведение лучей, растекание цвета, глубина цвета
• Выпуклость экрана, скруглённые углы, виньетка, свечение и ореол трубки
• Послесвечение люминофора (хвосты от движения) и блик на стекле
• Мерцание, бегущая полоса, живое зерно, тряска
• Окно пресетов с превью, свои пресеты со снимком кадра, обмен кодом настроек
• Работает на страницах Edit, Fusion и Color (DCTL, Resolve Studio)
• Установщики для macOS, Windows и Linux

ТРЕБОВАНИЯ
DaVinci Resolve 18 и новее (проверено на 20). Страница Color — Resolve Studio.
"""


def make_cover():
    """Сдержанная обложка 1920x1080 (как у VHS Pro): кадр эффекта, затемнение снизу, заголовок слева."""
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1920, 1080
    bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    reg = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    from PIL import ImageEnhance
    cover = Image.open(os.path.join(HERE, "store_assets", "cover_bg.png")).convert("RGB").resize((W, H), Image.LANCZOS)
    cover = ImageEnhance.Brightness(cover).enhance(1.9)
    shade = Image.new("L", (W, H))
    sp = shade.load()
    for y in range(H):
        v = int(235 * max(0.0, (y / H - 0.35) / 0.65) ** 1.4)
        for x in range(W):
            sp[x, y] = int(v * (1 - 0.35 * x / W))
    cover = Image.composite(Image.new("RGB", (W, H), (8, 8, 12)), cover, shade)
    d = ImageDraw.Draw(cover)
    d.text((W - 110, 96), "S T O R Y V E R S E", font=ImageFont.truetype(reg, 26), fill=(200, 202, 210), anchor="ra")
    d.text((104, 770), "CRT PRO", font=ImageFont.truetype(bold, 150), fill=(245, 245, 248), anchor="ls")
    d.text((110, 840), "Настоящий кинескоп для DaVinci Resolve", font=ImageFont.truetype(reg, 40),
           fill=(205, 207, 215), anchor="ls")
    d.line([(110, 880), (230, 880)], fill=(255, 255, 255), width=3)
    return cover


def make_store(m):
    """Материалы для страницы товара — отдельно от архива покупателя."""
    from PIL import Image, ImageDraw
    st = os.path.join(DIST, "Для магазина")
    os.makedirs(st, exist_ok=True)
    icons = os.path.join(HERE, "icons")
    n = len(m.PRESET_NAMES)
    cols, w, h = 3, 320, 180
    rows = (n + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w + (cols + 1) * 12, rows * (h + 34) + 12), (14, 15, 20))
    d = ImageDraw.Draw(sheet)
    for i, name in enumerate(m.PRESET_NAMES):
        x, y = 12 + (i % cols) * (w + 12), 12 + (i // cols) * (h + 34)
        sheet.paste(Image.open(os.path.join(icons, f"preset_{i}.png")).resize((w, h)), (x, y))
        d.text((x + 4, y + h + 8), name, fill=(214, 216, 226))
    sheet.save(os.path.join(st, "Пресеты.png"))
    pat = Image.new("RGB", (5 * 172 + 12, 2 * 102 + 12), (14, 15, 20))
    for i in range(10):
        pat.paste(Image.open(os.path.join(icons, f"pattern_{i}.png")), (12 + (i % 5) * 172, 12 + (i // 5) * 102))
    pat.save(os.path.join(st, "Узоры пикселей.png"))
    cover = make_cover()
    cover.save(os.path.join(st, "Обложка.png"))
    shutil.copy2(os.path.join(HERE, "store_assets", "Страница товара.md"), os.path.join(st, "Страница товара.md"))
    with open(os.path.join(st, "Описание товара.txt"), "w", encoding="utf-8") as f:
        f.write(fill(STORE_TEXT, "CRT Pro", False))


DEMO_NOTE = """
ДЕМО-ВЕРСИЯ
  Это демо «просто попробовать»: водяной знак CRT PRO DEMO, 3 пресета
  и 3 настройки — размер пикселя, яркость, гамма.
  Полная версия: 18 пресетов, окно пресетов, 10 узоров пикселей, 18 модулей
  (свечение, строки, выпуклость, послесвечение, помехи…), DCTL для Color,
  без водяного знака.
"""


def fill(txt, name, demo):
    txt = (txt.replace("@NAME@", name).replace("@UNAME@", name.upper())
              .replace("@CAT@", CAT).replace("@SCR@", SCR).replace("@LUT@", LUTD))
    if demo:  # в демо нет DCTL — убираем строки установки Color
        keys = ("Presets", "Страница Color (DCTL)", "ОКНО ПРЕСЕТОВ", "10 узоров", "Вкладки Пиксели", "Color      :", "LUT", "Color/*", "Color\\*", "страницы Color", "Для страницы Color")
        txt = "\n".join(l for l in txt.split("\n") if not any(k in l for k in keys) and l.strip() != "fi")
    return txt


def build_edition(name, demo):
    m = load_builder(demo)
    out = os.path.join(DIST, name)
    P = os.path.join(out, "payload")
    for d in ("Effect", "Fuses") + (() if demo else ("Presets/icons", "Color")):
        os.makedirs(os.path.join(P, d), exist_ok=True)
    with open(os.path.join(P, "Effect", name + ".setting"), "w", encoding="utf-8") as f:
        st = publicize(m.build_setting(0), name)
        f.write(add_demo_mark(st.replace("Fuse.CRTCore", "Fuse.CRTCoreDemo")) if demo else st)
    shutil.copy2(os.path.join(HERE, "effect", SRC + ".png"), os.path.join(P, "Effect", name + ".png"))
    fuse = publicize(strip_lua_comments(m.build_fuse()), "CRT Pro").replace('REGS_Category = "Claude"', 'REGS_Category = "STORYVERSE\\\\CRT"')
    if demo:
        assert "DEMO_BUILD = false" in fuse
        # своё имя ноды и ядра: полная версия не перезапишет демо, Resolve не возьмёт ядро из кэша
        fuse = (fuse.replace("p.demo = DEMO_BUILD and 1 or 0", "p.demo = 0")
                    .replace('FuRegisterClass("CRTCore"', 'FuRegisterClass("CRTCoreDemo"')
                    .replace('REGS_Name = "CRT Core"', 'REGS_Name = "CRT Core Demo"')
                    .replace('"CRTKernel"', '"CRTKernelDemo"')
                    .replace("void CRTKernel(", "void CRTKernelDemo("))
        assert "CRTCoreDemo" in fuse and "CRTKernelDemo" in fuse and "p.demo = 0" in fuse
    with open(os.path.join(P, "Fuses", "CRTCoreDemo.fuse" if demo else "CRTCore.fuse"), "w", encoding="utf-8") as f:
        f.write(fuse)
    if not demo:
        with open(os.path.join(HERE, "CRT Presets.lua"), encoding="utf-8") as f:
            presets = publicize(f.read(), name)
        if demo:
            assert "local DEMO = false" in presets
            presets = presets.replace("local DEMO = false", "local DEMO = true")  # не используется
        with open(os.path.join(P, "Presets", "CRT Presets.lua"), "w", encoding="utf-8") as f:
            f.write(strip_lua_comments(presets))
        shutil.copy2(os.path.join(HERE, "crt_pro_data.lua"), os.path.join(P, "Presets"))
        for fn in os.listdir(os.path.join(HERE, "icons")):
            if fn.endswith(".png"):
                shutil.copy2(os.path.join(HERE, "icons", fn), os.path.join(P, "Presets", "icons"))
    if not demo:
        with open(os.path.join(HERE, SRC + ".dctl"), encoding="utf-8") as f:
            dctl = f.read().replace("CRT Pro v2", "CRT Pro")
        with open(os.path.join(P, "Color", "CRT Pro.dctl"), "w", encoding="utf-8") as f:
            f.write(dctl)

    readme = fill(README, name, demo) + (DEMO_NOTE if demo else "")
    files = {"Установить (macOS).command": fill(MAC, name, demo),
             "Установить (Windows).bat": fill(WIN, name, demo).replace(CAT, CAT.replace("/", "\\")).replace("\n", "\r\n"),
             "install-linux.sh": fill(LINUX, name, demo), "README.txt": readme,
             "LICENSE.txt": fill(LICENSE, name, demo)}
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
                    info.external_attr = (0o755 | 0o100000) << 16  # исполняемый после распаковки на Mac/Linux
                with open(full, "rb") as fh:
                    z.writestr(info, fh.read(), zipfile.ZIP_DEFLATED)
    print("готово:", zpath)
    return m


def main():
    shutil.rmtree(DIST, ignore_errors=True)
    m = build_edition("CRT Pro", False)
    build_edition("CRT Pro Demo", True)
    make_store(m)


if __name__ == "__main__":
    main()
