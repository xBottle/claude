#!/usr/bin/env python3
"""Собирает чистую папку для продажи/раздачи: dist/CRT Pro v2/ + zip.
В пакет попадает только то, что нужно покупателю: файлы эффекта и установщики
для macOS, Windows и Linux. Исходники, генераторы, валидаторы — не попадают.

Запуск: python3 make_release.py
"""
import os
import shutil
import zipfile
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "CRT Pro v2"
DIST = os.path.join(HERE, "dist")
OUT = os.path.join(DIST, NAME)
P = os.path.join(OUT, "payload")


def load_builder():
    spec = importlib.util.spec_from_file_location("b", os.path.join(HERE, "build_crt_pro_2.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.SHARE_MODE = True  # свои пресеты автора в продаваемый пакет не попадают
    return m


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
# CRT Pro v2 — установка для macOS. Двойной клик.
cd "$(dirname "$0")/payload"
FU="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion"
mkdir -p "$FU/Templates/Edit/Effects/Claude/CRT" "$FU/Fuses" "$FU/Scripts/Comp/crt-2.0"
cp -f Effect/* "$FU/Templates/Edit/Effects/Claude/CRT/"
cp -f Fuses/* "$FU/Fuses/"
cp -Rf Presets/* "$FU/Scripts/Comp/crt-2.0/"
echo "CRT Pro v2: эффект установлен."
SYS="/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/Claude"
echo "Для страницы Color нужен пароль администратора (можно пропустить: Ctrl+C):"
sudo mkdir -p "$SYS" && sudo cp -f Color/* "$SYS/" && echo "DCTL для страницы Color установлен."
echo
echo "Готово. Перезапустите DaVinci Resolve."
read -n 1 -s -r -p "Нажмите любую клавишу..."
'''

WIN = r'''@echo off
chcp 65001 >nul
REM CRT Pro v2 — установка для Windows. Двойной клик (для страницы Color — «Запуск от имени администратора»).
cd /d "%~dp0payload"
set "FU=%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion"
mkdir "%FU%\Templates\Edit\Effects\Claude\CRT" 2>nul
mkdir "%FU%\Fuses" 2>nul
mkdir "%FU%\Scripts\Comp\crt-2.0" 2>nul
xcopy /Y /Q "Effect\*" "%FU%\Templates\Edit\Effects\Claude\CRT\" >nul
xcopy /Y /Q "Fuses\*" "%FU%\Fuses\" >nul
xcopy /Y /Q /E "Presets\*" "%FU%\Scripts\Comp\crt-2.0\" >nul
echo CRT Pro v2: эффект установлен.
set "LUT=%ProgramData%\Blackmagic Design\DaVinci Resolve\Support\LUT\Claude"
mkdir "%LUT%" 2>nul
xcopy /Y /Q "Color\*" "%LUT%\" >nul && echo DCTL для страницы Color установлен. || echo Для страницы Color запустите установщик от имени администратора.
echo.
echo Готово. Перезапустите DaVinci Resolve.
pause
'''

LINUX = r'''#!/bin/bash
# CRT Pro v2 — установка для Linux: bash install-linux.sh
cd "$(dirname "$0")/payload"
FU="$HOME/.local/share/DaVinciResolve/Fusion"
mkdir -p "$FU/Templates/Edit/Effects/Claude/CRT" "$FU/Fuses" "$FU/Scripts/Comp/crt-2.0"
cp -f Effect/* "$FU/Templates/Edit/Effects/Claude/CRT/"
cp -f Fuses/* "$FU/Fuses/"
cp -rf Presets/* "$FU/Scripts/Comp/crt-2.0/"
echo "CRT Pro v2: эффект установлен."
if [ -d /opt/resolve/LUT ]; then
  sudo mkdir -p /opt/resolve/LUT/Claude && sudo cp -f Color/* /opt/resolve/LUT/Claude/ && echo "DCTL установлен."
fi
echo "Готово. Перезапустите DaVinci Resolve."
'''

README = '''CRT PRO v2 — процедурный CRT-эффект для DaVinci Resolve 18+ (Studio / Free*)
=========================================================================

УСТАНОВКА
  macOS   — двойной клик «Установить (macOS).command»
            (если macOS не открывает: правый клик → Открыть)
  Windows — двойной клик «Установить (Windows).bat»
            (для страницы Color — правый клик → Запуск от имени администратора)
  Linux   — bash install-linux.sh
  После установки перезапустите DaVinci Resolve.

ГДЕ НАЙТИ
  Edit / Cut : Effects → Эффекты → Claude → CRT → «CRT Pro v2»
  Fusion     : Shift+Пробел → «CRT Core»
  Color      : Effects → DCTL → в списке DCTL выбрать Claude / CRT Pro v2

КАК ПОЛЬЗОВАТЬСЯ
  • Вкладка «Управление» → «ОКНО ПРЕСЕТОВ»: 18 пресетов с превью, узоры пикселей,
    свои пресеты со снимком кадра, листание ◀ ▶.
  • Вкладки Пиксели / Экран / Цвет / Помехи — ручная настройка.
  • Эффект считается на видеокарте (≈1–2 мс на кадр 1080p).
  • Не накладывайте эффект одновременно на Edit и на Color — двойная сетка даёт муар.

* Страница Color (DCTL) работает в DaVinci Resolve Studio.

© CRT Pro. Лицензия — см. LICENSE.txt
'''

LICENSE = '''CRT PRO v2 — ЛИЦЕНЗИЯ
Лицензия даёт право одному пользователю устанавливать и использовать эффект
в личных и коммерческих проектах (видео, клипы, реклама) без ограничений.
Запрещено: перепродавать, публиковать или передавать файлы эффекта третьим
лицам, в том числе в изменённом виде.
'''


def main():
    m = load_builder()
    shutil.rmtree(DIST, ignore_errors=True)
    for d in ("Effect", "Fuses", "Presets/icons", "Color"):
        os.makedirs(os.path.join(P, d), exist_ok=True)
    with open(os.path.join(P, "Effect", NAME + ".setting"), "w", encoding="utf-8") as f:
        f.write(m.build_setting(0))
    shutil.copy2(os.path.join(HERE, "effect", NAME + ".png"), os.path.join(P, "Effect"))
    with open(os.path.join(P, "Fuses", "CRTCore.fuse"), "w", encoding="utf-8") as f:
        f.write(strip_lua_comments(m.build_fuse()))
    with open(os.path.join(HERE, "CRT Presets.lua"), encoding="utf-8") as f:
        presets = strip_lua_comments(f.read())
    with open(os.path.join(P, "Presets", "CRT Presets.lua"), "w", encoding="utf-8") as f:
        f.write(presets)
    shutil.copy2(os.path.join(HERE, "crt_pro_data.lua"), os.path.join(P, "Presets"))
    for fn in os.listdir(os.path.join(HERE, "icons")):
        if fn.endswith(".png"):
            shutil.copy2(os.path.join(HERE, "icons", fn), os.path.join(P, "Presets", "icons"))
    shutil.copy2(os.path.join(HERE, NAME + ".dctl"), os.path.join(P, "Color"))

    files = {"Установить (macOS).command": MAC, "Установить (Windows).bat": WIN.replace("\n", "\r\n"),
             "install-linux.sh": LINUX, "README.txt": README, "LICENSE.txt": LICENSE}
    for fn, txt in files.items():
        with open(os.path.join(OUT, fn), "w", encoding="utf-8", newline="") as f:
            f.write(txt)
        if fn.endswith((".command", ".sh")):
            os.chmod(os.path.join(OUT, fn), 0o755)

    zpath = os.path.join(DIST, NAME + ".zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, fs in os.walk(OUT):
            for fn in fs:
                full = os.path.join(root, fn)
                info = zipfile.ZipInfo.from_file(full, os.path.relpath(full, DIST))
                if fn.endswith((".command", ".sh")):
                    info.external_attr = (0o755 | 0o100000) << 16  # исполняемый после распаковки на Mac/Linux
                with open(full, "rb") as fh:
                    z.writestr(info, fh.read(), zipfile.ZIP_DEFLATED)
    print("готово:", zpath)


if __name__ == "__main__":
    main()
