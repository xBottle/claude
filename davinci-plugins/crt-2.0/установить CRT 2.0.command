#!/bin/bash
# Ставит CRT Pro 2.0 (эффект + окно пресетов). CRT Pro 1.0 не трогает.
cd "$(dirname "$0")"
FU="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion"
mkdir -p "$FU/Templates/Edit/Effects/Claude/CRT" "$FU/Scripts/Comp/crt-2.0/icons"
cp "effect/CRT Pro 2.0.setting" "effect/CRT Pro 2.0.png" "$FU/Templates/Edit/Effects/Claude/CRT/"
cp "CRT Presets.lua" crt_pro_data.lua "$FU/Scripts/Comp/crt-2.0/"
cp icons/*.png "$FU/Scripts/Comp/crt-2.0/icons/"
rm -f "$FU/Scripts/Comp/crt-2.0/CRT 2.0.lua" "$FU/Scripts/Comp/crt-2.0/CRT Pro Panel.lua"
echo "Готово. Перезапусти Resolve и перетащи «CRT Pro 2.0» на клип."
read -n 1 -s -r -p "Нажми любую клавишу..."
