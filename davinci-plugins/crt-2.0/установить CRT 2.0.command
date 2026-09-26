#!/bin/bash
# Ставит CRT Pro v2: эффект + процедурное GPU-ядро + окно пресетов. CRT Pro 1.0 не трогает.
cd "$(dirname "$0")"
FU="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion"
mkdir -p "$FU/Templates/Edit/Effects/Claude/CRT" "$FU/Scripts/Comp/crt-2.0/icons" "$FU/Fuses"
rm -f "$FU/Templates/Edit/Effects/Claude/CRT/CRT Pro 2.0."*
cp "effect/CRT Pro v2.setting" "effect/CRT Pro v2.png" "$FU/Templates/Edit/Effects/Claude/CRT/"
cp "effect/CRTCore.fuse" "$FU/Fuses/"
LUT="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT"
mkdir -p "$LUT/Claude" && cp "CRT Pro v2.dctl" "$LUT/Claude/"
# Resolve на Mac берёт DCTL из системной папки LUT — нужен пароль администратора
SYS="/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/Claude"
echo "Для страницы Color нужен пароль Mac (копирую DCTL в системную папку LUT):"
sudo mkdir -p "$SYS" && sudo cp "CRT Pro v2.dctl" "$SYS/" && echo "DCTL: $SYS"
cp "CRT Presets.lua" crt_pro_data.lua "$FU/Scripts/Comp/crt-2.0/"
cp icons/*.png "$FU/Scripts/Comp/crt-2.0/icons/"
rm -f "$FU/Scripts/Comp/crt-2.0/CRT 2.0.lua" "$FU/Scripts/Comp/crt-2.0/CRT Pro Panel.lua"
echo "Установлено:"
ls "$FU/Templates/Edit/Effects/Claude/CRT/" "$FU/Fuses/CRTCore.fuse" "$SYS/"
echo
echo "Перезапусти Resolve (Cmd+Q) и перетащи «CRT Pro v2» на клип."
read -n 1 -s -r -p "Нажми любую клавишу..."
