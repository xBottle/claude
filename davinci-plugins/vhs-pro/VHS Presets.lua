-- VHS Pro — окно пресетов.
-- Открывается кнопкой «ОКНО ПРЕСЕТОВ» в Инспекторе эффекта (страница Edit).
-- Список пресетов с превью (прокрутка), быстрые кнопки, свои пресеты ★.

local function scriptDir()
    local src = debug.getinfo(1, "S").source
    local path = src:match("^@(.*)$") or src
    return (path:match("^(.*)[/\\][^/\\]+$") or ".") .. "/"
end
local DIR = scriptDir()
local DEMO = false          -- make_release.py ставит true в демо-сборке
local DEMO_FREE = 3         -- в демо доступны первые 3 пресета
local DEMO_MSG = "Это доступно в полной версии VHS Pro."

local chunk, err = loadfile(DIR .. "vhs_pro_data.lua")
if not chunk then print("[VHS Presets] нет vhs_pro_data.lua: " .. tostring(err)) return end
local DATA = chunk()

local FUAPP = fu or app
local comp = (FUAPP and FUAPP:GetCurrentComp()) or comp

-- Нода эффекта: из кнопки приходит готовая (VHS_TOOL), иначе ищем в компе.
local tool = _G.VHS_TOOL
if not tool and comp then
    local a = comp.ActiveTool and comp:ActiveTool()
    if a and tostring(a.Name):lower():find("vhs") then tool = a end
    if not tool then
        for _, t in pairs(comp:GetToolList(false)) do
            if tostring(t.Name):lower():find("vhs") then tool = t break end
        end
    end
end
if not tool then print("[VHS Presets] Нода VHS Pro не найдена.") return end

-- Папка своих пресетов — та же, что у кнопок эффекта.
local function fusionDir()
    local list, appdata, home = {}, os.getenv("APPDATA"), os.getenv("HOME") or ""
    if appdata and appdata ~= "" then
        list[#list + 1] = (appdata:gsub("\\", "/")) .. "/Blackmagic Design/DaVinci Resolve/Support/Fusion/"
    end
    if home ~= "" then
        list[#list + 1] = home .. "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/"
        list[#list + 1] = home .. "/.local/share/DaVinciResolve/Fusion/"
    end
    for _, d in ipairs(list) do if bmd.fileexists(d .. "Templates") then return d end end
    return list[1] or ""
end
local PRESET_DIR = fusionDir() .. "VHS Pro User Presets/"

local IDS = {}
for k in pairs(DATA.DEFAULTS) do IDS[#IDS + 1] = k end
table.sort(IDS)

local function applyTable(t, label)
    -- Lock: пока ставим ~100 значений, Resolve не перерисовывает кадр.
    -- Иначе каждый SetInput запускает рендер, прерывает прошлый (отсюда
    -- ошибки ScreenWarp/FinalMix в консоли) и часть значений «теряется».
    if comp then
        pcall(function() comp:Lock() end)
        pcall(function() comp:StartUndo("VHS пресет: " .. label) end)
    end
    local failed = 0
    for _, k in ipairs(IDS) do
        local v = t[k]
        if type(v) == "number" then
            local ok = pcall(function() tool:SetInput(k, v) end)
            if not ok then failed = failed + 1 end
        end
    end
    if comp then
        pcall(function() comp:EndUndo(true) end)
        pcall(function() comp:Unlock() end)
    end
    if failed > 0 then print("[VHS Presets] не применилось параметров: " .. failed) end
end
local function current()
    local t = {}
    for _, k in ipairs(IDS) do
        local ok, v = pcall(function() return tool:GetInput(k) end)
        if ok and type(v) == "number" then t[k] = v end
    end
    return t
end
local function toCode(t)
    local parts = {}
    for _, k in ipairs(IDS) do
        if type(t[k]) == "number" then parts[#parts + 1] = k .. "=" .. string.format("%.5g", t[k]) end
    end
    return "VHSPRO1;" .. table.concat(parts, ";")
end
local function fromCode(s)
    local t, n = {}, 0
    for k, v in tostring(s or ""):gmatch("([%a_][%w_]*)=([%-%+%deE%.]+)") do
        t[k] = tonumber(v); n = n + 1
    end
    return n > 0 and t or nil
end
local function cleanName(s)
    return (tostring(s or ""):gsub("[/\\:%*%?\"<>|]", "_"):gsub("^%s+", ""):gsub("%s+$", ""))
end
local function listOwn()
    local names = {}
    for _, f in ipairs(bmd.readdir(PRESET_DIR .. "*.vhspreset") or {}) do
        if type(f) == "table" and f.Name and not f.IsDir then
            names[#names + 1] = (f.Name:gsub("%.vhspreset$", ""))
        end
    end
    table.sort(names)
    return names
end
-- Список «Пресет» в шаблоне эффекта = встроенные + свои (★).
-- Новые пункты видны в эффектах, перетащенных на клип после перезапуска Resolve.
local TEMPLATE = fusionDir() .. "Templates/Edit/Effects/STORYVERSE/VHS/VHS Pro.setting"
local function syncTemplate()
    local ok = pcall(function()
        local src = bmd.readfile(TEMPLATE)
        if type(src) ~= "table" then return end
        local grp
        for _, v in pairs(src.Tools) do if type(v) == "table" and v.Tools then grp = v end end
        local ucs = grp.Tools.Ctrl.UserControls
        local combo, apply = ucs.PresetSel, ucs.BtnApply
        for i = #combo, 1, -1 do combo[i] = nil end
        for _, n in ipairs(DATA.PRESET_NAMES) do combo[#combo + 1] = { CCS_AddString = n } end
        local quoted = {}
        for _, n in ipairs(listOwn()) do
            combo[#combo + 1] = { CCS_AddString = "★ " .. n }
            quoted[#quoted + 1] = string.format("%q", n)
        end
        combo.INP_MaxScale = #combo - 1
        combo.INP_MaxAllowed = #combo - 1
        local key = "local USER_" .. "PRESETS = "
        apply.BTNCS_Execute = apply.BTNCS_Execute:gsub(key .. "%b{}", function() return key .. "{ " .. table.concat(quoted, ", ") .. " }" end, 1)
        bmd.writefile(TEMPLATE, src)
    end)
    return ok
end

local function builtinValues(i)
    local t = {}
    for k, v in pairs(DATA.DEFAULTS) do t[k] = v end
    for k, v in pairs(DATA.PRESETS[i] or {}) do t[k] = v end
    return t
end

local ui = FUAPP.UIManager

local disp = bmd.UIDispatcher(ui)
local tunpack = table.unpack or unpack

local function icon(name)
    local p = DIR .. "icons/" .. name .. ".png"
    if not bmd.fileexists(p) then return nil end
    local ok, ic = pcall(function() return ui:Icon{ File = p } end)
    return ok and ic or nil
end

pcall(syncTemplate)
local selected = nil
local statusText = ""
local reopen = true
local geom = { 200, 60, 620, 860 }

while reopen do
    reopen = false

    -- все пресеты: встроенные + свои (★)
    local items = {}
    for i, n in ipairs(DATA.PRESET_NAMES) do
        items[#items + 1] = { kind = "builtin", index = i - 1, name = n, ico = "preset_" .. (i - 1),
            locked = DEMO and i > DEMO_FREE }
    end
    for _, n in ipairs(DEMO and {} or listOwn()) do
        items[#items + 1] = { kind = "own", name = n, ico = "preset_own", thumb = PRESET_DIR .. n .. ".png" }
    end

    local function btnStyle(color)
        return "QPushButton { background:#17181f; color:" .. color .. "; border:1px solid #2b2c36; " ..
            "border-radius:10px; padding:9px; font-weight:600; } QPushButton:hover { border-color:" .. color ..
            "; background:#1e1f28; }"
    end
    local BLUE, WHITE, GREEN, RED = "#9d8cff", "#e6e7ee", "#5eead4", "#fb7185"

    local function iconFor(it)
        if it.thumb and bmd.fileexists(it.thumb) then
            local ok, ic = pcall(function() return ui:Icon{ File = it.thumb } end)
            if ok and ic then return ic end
        end
        return icon(it.ico) or icon("preset_0")
    end
    -- список с прокруткой: одна строка = один пресет
    local function label(it) return (it.kind == "own" and "★ " or "") .. it.name .. (it.locked and "   🔒" or "") end
    local byLabel = {}
    for _, it in ipairs(items) do byLabel[label(it)] = it end

    -- быстрые кнопки: режим магнитофона и главные модули
    local MODES = { "► PLAY", "❚❚ PAUSE", "◄◄ REW", "►► FF" }
    local TOGGLES = { { "CamOn", "Съёмка с рук" }, { "OSDOn", "Дата и время" },
        { "CreaseOn", "Залом плёнки" }, { "Aspect43", "Формат 4:3" } }
    local function getv(k) local v = 0; pcall(function() v = tool:GetInput(k) or 0 end); return v end
    local QB = [[QPushButton { background:#101116; color:#c9cad4; border:1px solid #25262e; border-radius:10px; padding:8px; font-weight:600; }
QPushButton:hover { border:1px solid #22d3ee; }]]
    local QB_ON = [[QPushButton { background:#0f2230; color:#ffffff; border:2px solid #22d3ee; border-radius:10px; padding:7px; font-weight:700; }]]
    local curMode = math.floor(getv("Mode") + 0.5)
    local modeCells, togCells = {}, {}
    for i = 0, 3 do
        modeCells[#modeCells + 1] = ui:Button{ ID = "mode_" .. i, Text = MODES[i + 1],
            StyleSheet = (i == curMode) and QB_ON or QB }
    end
    for i, tg in ipairs(TOGGLES) do
        togCells[#togCells + 1] = ui:Button{ ID = "tog_" .. i, Text = tg[2],
            StyleSheet = (getv(tg[1]) > 0.5) and QB_ON or QB }
    end

    local win = disp:AddWindow({
        ID = "VHSPresetsWin",
        WindowTitle = DEMO and "VHS PRO — DEMO" or "VHS PRO",
        Geometry = geom,
        StyleSheet = [[QWidget { background:#0e0f14; color:#e6e7ee; font-size:12px; }
QLineEdit { background:#15161c; border:1px solid #2b2c36; border-radius:10px; padding:9px; font-size:13px; color:#e6e7ee; }
QLineEdit:focus { border:1px solid #8b7bff; }]],
        ui:VGroup{
            Spacing = 8,
            ui:Label{ Text = "<img src='" .. DIR .. "icons/title.png'>", Alignment = { AlignHCenter = true }, Weight = 0 },
            ui:Tree{ ID = "PresetList", Weight = 1, MinimumSize = { 560, 340 },
                IconSize = { 128, 72 }, HeaderHidden = true, RootIsDecorated = false,
                SelectionMode = "SingleSelection", ColumnCount = 1, UniformRowHeights = true,
                StyleSheet = [[QTreeWidget { background:#0e0f14; border:1px solid #25262e; border-radius:12px; padding:6px; outline:0; }
QTreeWidget::item { color:#d6d8e2; font-size:13px; padding:4px 6px; border-radius:10px; }
QTreeWidget::item:hover { background:#1b1c24; }
QTreeWidget::item:selected { background:#221d3d; color:#ffffff; }
QScrollBar:vertical { background:#0e0f14; width:8px; }
QScrollBar::handle:vertical { background:#34353f; border-radius:4px; min-height:30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }]] },
            ui:Label{ Weight = 0, StyleSheet = "color:#22d3ee; font-weight:600; letter-spacing:1px; margin-top:8px;",
                Text = "МАГНИТОФОН" },
            ui:HGroup{ Weight = 0, Spacing = 6, tunpack(modeCells) },
            ui:Label{ Weight = 0, StyleSheet = "color:#22d3ee; font-weight:600; letter-spacing:1px; margin-top:4px;",
                Text = "КАМЕРА И КАДР" },
            ui:HGroup{ Weight = 0, Spacing = 6, tunpack(togCells) },
            ui:VGap(0, 1),
            ui:LineEdit{ ID = "NameEdit", PlaceholderText = "Название пресета", Weight = 0,
                Text = selected and selected.name or "" },
            ui:HGroup{ Weight = 0,
                ui:Button{ ID = "BtnLoad", Text = "Сбросить всё", StyleSheet = btnStyle(WHITE) },
                ui:Button{ ID = "BtnCopy", Text = "Скопировать код", StyleSheet = btnStyle(WHITE) },
            },
            ui:HGroup{ Weight = 0,
                ui:Button{ ID = "BtnSave", Text = "Сохранить мой", StyleSheet = btnStyle(GREEN) },
                ui:Button{ ID = "BtnPaste", Text = "Сохранить из буфера", StyleSheet = btnStyle(GREEN) },
            },
            ui:HGroup{ Weight = 0,
                ui:Button{ ID = "BtnRename", Text = "Переименовать", StyleSheet = btnStyle(WHITE) },
                ui:Button{ ID = "BtnDelete", Text = "Удалить", StyleSheet = btnStyle(RED) },
            },
            ui:Button{ ID = "BtnThumb", Text = "Снять превью с текущего кадра (для своего ★)", StyleSheet = btnStyle(WHITE), Weight = 0 },
            ui:Label{ ID = "Status", Text = statusText, Weight = 0, WordWrap = true, StyleSheet = "color:#9d8cff;" },
            ui:Label{ Text = DEMO and "VHS PRO  ·  DEMO  ·  полная версия без надписи" or "VHS PRO  ·  GPU procedural tape", Weight = 0, Alignment = { AlignHCenter = true },
                StyleSheet = "color:#4a4c58; font-size:10px; letter-spacing:1px;" },
        },
    })
    local itm = win:GetItems()

    local function status(s) statusText = s; itm.Status.Text = s end
    local function valuesOf(it)
        if it.kind == "builtin" then return builtinValues(it.index) end
        local t = bmd.readfile(PRESET_DIR .. it.name .. ".vhspreset")
        return type(t) == "table" and t or nil
    end
    local function apply(it)
        local t = valuesOf(it)
        if not t then status("Не удалось прочитать «" .. it.name .. "».") return end
        applyTable(t, it.name)
        if it.kind == "builtin" then pcall(function() tool:SetInput("PresetSel", it.index) end) end
        status("Применён «" .. it.name .. "».")
    end
    local function restart()
        pcall(syncTemplate)
        local ok, g = pcall(function() return win:GetGeometry() end)
        if ok and type(g) == "table" and g[3] then geom = { g[1], g[2], g[3], g[4] } end
        reopen = true
        disp:ExitLoop()
    end

    -- заполнить список; клик по строке = выбрать и сразу применить
    pcall(function()
        local tr = itm.PresetList
        pcall(function() tr:SetIconSize({ 128, 72 }) end)
        -- одна строка = один пресет: превью слева, название справа
        for _, it in ipairs(items) do
            local row = tr:NewItem()
            row.Text[0] = "   " .. label(it)
            row.Icon[0] = iconFor(it)
            tr:AddTopLevelItem(row)
            if selected and selected.name == it.name and selected.kind == it.kind then
                pcall(function() row.Selected = true end)
            end
        end
    end)
    function win.On.PresetList.ItemClicked(ev)
        local txt = ev.item and ev.item.Text[0]
        local it = txt and byLabel[(txt:gsub("^%s+", ""))]
        if not it then return end
        if it.locked then status("🔒 «" .. it.name .. "» — " .. DEMO_MSG) return end
        selected = it
        itm.NameEdit.Text = it.name
        apply(it)
    end

    for i = 0, 3 do
        win.On["mode_" .. i].Clicked = function()
            pcall(function() tool:SetInput("Mode", i) end)
            for j = 0, 3 do pcall(function() itm["mode_" .. j].StyleSheet = (j == i) and QB_ON or QB end) end
            status("Режим: " .. MODES[i + 1])
        end
    end
    for i, tg in ipairs(TOGGLES) do
        win.On["tog_" .. i].Clicked = function()
            local on = getv(tg[1]) > 0.5 and 0 or 1
            pcall(function() tool:SetInput(tg[1], on) end)
            pcall(function() itm["tog_" .. i].StyleSheet = (on == 1) and QB_ON or QB end)
            status(tg[2] .. (on == 1 and ": включено" or ": выключено"))
        end
    end

    function win.On.BtnLoad.Clicked()
        applyTable(builtinValues(0), "сброс")
        pcall(function() tool:SetInput("PresetSel", 0) end)
        selected = nil
        pcall(function() itm.PresetList:ClearSelection() end)
        itm.NameEdit.Text = ""
        status("Все настройки сброшены к значениям по умолчанию.")
    end

    function win.On.BtnCopy.Clicked()
        local code = toCode(current())
        local ok = pcall(function() bmd.setclipboard(code) end)
        status(ok and "Код текущих настроек скопирован в буфер." or code)
    end

    local function saveAs(name, t)
        name = cleanName(name)
        if name == "" then status("Введи название в поле выше.") return end
        bmd.createdir(PRESET_DIR)
        bmd.writefile(PRESET_DIR .. name .. ".vhspreset", t)
        -- превью: текущий кадр из вьюера Resolve (Resolve 18+)
        local shot = false
        pcall(function()
            local rs = (Resolve and Resolve()) or bmd.scriptapp("Resolve")
            local pj = rs:GetProjectManager():GetCurrentProject()
            shot = pj:ExportCurrentFrameAsStill(PRESET_DIR .. name .. ".png") and true or false
        end)
        selected = { kind = "own", name = name }
        statusText = "Сохранён «" .. name .. "»" .. (shot and " с превью текущего кадра." or ".")
        restart()
    end

    function win.On.BtnSave.Clicked()
        if DEMO then status("Свои пресеты — " .. DEMO_MSG) return end
        saveAs(itm.NameEdit.Text, current())
    end

    function win.On.BtnPaste.Clicked()
        if DEMO then status("Свои пресеты — " .. DEMO_MSG) return end
        local cb = ""
        pcall(function() local x = bmd.getclipboard(); if type(x) == "string" then cb = x end end)
        local t = fromCode(cb)
        if not t then status("В буфере нет кода VHS Pro (VHSPRO1;...).") return end
        saveAs(itm.NameEdit.Text, t)
    end

    function win.On.BtnRename.Clicked()
        if DEMO then status("Свои пресеты — " .. DEMO_MSG) return end
        if not selected or selected.kind ~= "own" then status("Переименовать можно только свой пресет (★).") return end
        local new = cleanName(itm.NameEdit.Text)
        if new == "" or new == selected.name then status("Впиши новое название в поле.") return end
        local t = bmd.readfile(PRESET_DIR .. selected.name .. ".vhspreset")
        if type(t) ~= "table" then status("Не удалось прочитать пресет.") return end
        bmd.writefile(PRESET_DIR .. new .. ".vhspreset", t)
        os.remove(PRESET_DIR .. selected.name .. ".vhspreset")
        os.rename(PRESET_DIR .. selected.name .. ".png", PRESET_DIR .. new .. ".png")
        statusText = "Переименован в «" .. new .. "»."
        selected = { kind = "own", name = new }
        restart()
    end

    function win.On.BtnThumb.Clicked()
        if DEMO then status("Свои пресеты — " .. DEMO_MSG) return end
        if not selected or selected.kind ~= "own" then status("Сначала выбери свой пресет (★).") return end
        local ok = false
        pcall(function()
            local rs = (Resolve and Resolve()) or bmd.scriptapp("Resolve")
            ok = rs:GetProjectManager():GetCurrentProject():ExportCurrentFrameAsStill(PRESET_DIR .. selected.name .. ".png")
        end)
        if ok then statusText = "Превью обновлено."; restart() else status("Не удалось снять кадр: открой клип во вьюере страницы Edit.") end
    end

    function win.On.BtnDelete.Clicked()
        if DEMO then status("Свои пресеты — " .. DEMO_MSG) return end
        if not selected or selected.kind ~= "own" then status("Удалить можно только свой пресет (★).") return end
        os.remove(PRESET_DIR .. selected.name .. ".vhspreset")
        os.remove(PRESET_DIR .. selected.name .. ".png")
        statusText = "Удалён «" .. selected.name .. "»."
        selected = nil
        restart()
    end

    function win.On.VHSPresetsWin.Close() reopen = false; disp:ExitLoop() end
    win:Show()
    disp:RunLoop()
    win:Hide()
end
