-- CRT Pro 2.0 — окно пресетов (как у Procedural CRT).
-- Открывается кнопкой «Окно пресетов» в Инспекторе эффекта (страница Edit),
-- либо вручную: Рабочая область → Сценарии → Comp → CRT Presets.
-- Ползунки остаются в обычном Инспекторе, здесь — только пресеты.

local function scriptDir()
    local src = debug.getinfo(1, "S").source
    local path = src:match("^@(.*)$") or src
    return (path:match("^(.*)[/\\][^/\\]+$") or ".") .. "/"
end
local DIR = scriptDir()

local chunk, err = loadfile(DIR .. "crt_pro_data.lua")
if not chunk then print("[CRT Presets] нет crt_pro_data.lua: " .. tostring(err)) return end
local DATA = chunk()

local FUAPP = fu or app
local comp = (FUAPP and FUAPP:GetCurrentComp()) or comp

-- Нода эффекта: из кнопки приходит готовая (CRT_TOOL), иначе ищем в компе.
local tool = _G.CRT_TOOL
if not tool and comp then
    local a = comp.ActiveTool and comp:ActiveTool()
    if a and tostring(a.Name):lower():find("crt") then tool = a end
    if not tool then
        for _, t in pairs(comp:GetToolList(false)) do
            if tostring(t.Name):lower():find("crt") then tool = t break end
        end
    end
end
if not tool then print("[CRT Presets] Нода CRT Pro не найдена.") return end

-- Папка своих пресетов — та же, что у кнопок эффекта (общая с 1.0).
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
local PRESET_DIR = fusionDir() .. "CRT Pro User Presets/"

local IDS = {}
for k in pairs(DATA.DEFAULTS) do IDS[#IDS + 1] = k end
table.sort(IDS)

local function applyTable(t, label)
    -- Lock: пока ставим ~100 значений, Resolve не перерисовывает кадр.
    -- Иначе каждый SetInput запускает рендер, прерывает прошлый (отсюда
    -- ошибки ScreenWarp/FinalMix в консоли) и часть значений «теряется».
    if comp then
        pcall(function() comp:Lock() end)
        pcall(function() comp:StartUndo("CRT пресет: " .. label) end)
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
    if failed > 0 then print("[CRT Presets] не применилось параметров: " .. failed) end
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
    return "CRTPRO1;" .. table.concat(parts, ";")
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
    for _, f in ipairs(bmd.readdir(PRESET_DIR .. "*.crtpreset") or {}) do
        if type(f) == "table" and f.Name and not f.IsDir then
            names[#names + 1] = (f.Name:gsub("%.crtpreset$", ""))
        end
    end
    table.sort(names)
    return names
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

local selected = nil     -- { kind = "builtin"/"own", index = i, name = "..." }
local statusText = ""
local reopen = true
local geom = { 200, 100, 390, 860 }

while reopen do
    reopen = false

    -- все карточки: 10 встроенных + свои
    local items = {}
    for i, n in ipairs(DATA.PRESET_NAMES) do
        items[#items + 1] = { kind = "builtin", index = i - 1, name = n, ico = "preset_" .. (i - 1) }
    end
    for _, n in ipairs(listOwn()) do
        items[#items + 1] = { kind = "own", name = n, ico = "preset_own" }
    end

    local CARD = [[QPushButton { background:#15171c; border:2px solid #2a2e37; border-radius:8px; padding:2px; }
QPushButton:hover { border-color:#4b8fd6; }]]
    local CARD_SEL = [[QPushButton { background:#15171c; border:2px solid #5fd3ff; border-radius:8px; padding:2px; }]]
    local function btnStyle(color)
        return "QPushButton { background:#1c1f26; color:" .. color .. "; border:1px solid " .. color ..
            "; border-radius:6px; padding:7px; font-weight:bold; } QPushButton:hover { background:#252a33; }"
    end
    local BLUE, WHITE, GREEN, RED = "#6fb7ff", "#e8e8e8", "#6fdc8c", "#ff7a7a"

    local rows = {}
    for r = 1, #items, 2 do
        local cells = {}
        for c = r, math.min(r + 1, #items) do
            local it = items[c]
            local isSel = selected and selected.name == it.name and selected.kind == it.kind
            cells[#cells + 1] = ui:VGroup{
                Weight = 1, Spacing = 2,
                ui:Button{
                    ID = "card_" .. c, Text = "",
                    Icon = icon(it.ico) or icon("preset_0"),
                    IconSize = { 150, 84 }, MinimumSize = { 160, 92 }, MaximumSize = { 400, 92 },
                    ToolTip = it.name, StyleSheet = isSel and CARD_SEL or CARD,
                },
                ui:Label{
                    Text = (it.kind == "own" and "★ " or "") .. it.name, Alignment = { AlignHCenter = true },
                    StyleSheet = "color:#d8dce4; font-weight:bold;",
                },
            }
        end
        if #cells == 1 then cells[2] = ui:HGap(160) end
        rows[#rows + 1] = ui:HGroup{ Weight = 0, Spacing = 8, tunpack(cells) }
    end

    local win = disp:AddWindow({
        ID = "CRTPresetsWin",
        WindowTitle = "CRT Pro v2 — Пресеты",
        Geometry = geom,
        StyleSheet = [[QWidget { background:#181a20; color:#d8dce4; font-size:12px; }
QLineEdit { background:#111318; border:1px solid #333844; border-radius:6px; padding:7px; font-size:13px; }]],
        ui:VGroup{
            Spacing = 8,
            ui:Label{ Text = "<img src='" .. DIR .. "icons/title.png'>", Alignment = { AlignHCenter = true }, Weight = 0 },
            ui:VGroup{ Weight = 1, Spacing = 6, tunpack(rows) },
            ui:LineEdit{ ID = "NameEdit", PlaceholderText = "Название пресета", Weight = 0,
                Text = selected and selected.name or "" },
            ui:HGroup{ Weight = 0,
                ui:Button{ ID = "BtnLoad", Text = "Применить", StyleSheet = btnStyle(BLUE) },
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
            ui:Label{ ID = "Status", Text = statusText, Weight = 0, WordWrap = true, StyleSheet = "color:#6fb7ff;" },
            ui:Label{ Text = "CRT Pro v2 · процедурное ядро", Weight = 0, Alignment = { AlignHCenter = true },
                StyleSheet = "color:#5a606c; font-size:10px;" },
        },
    })
    local itm = win:GetItems()

    local function status(s) statusText = s; itm.Status.Text = s end
    local function valuesOf(it)
        if it.kind == "builtin" then return builtinValues(it.index) end
        local t = bmd.readfile(PRESET_DIR .. it.name .. ".crtpreset")
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
        local ok, g = pcall(function() return win:GetGeometry() end)
        if ok and type(g) == "table" and g[3] then geom = { g[1], g[2], g[3], g[4] } end
        reopen = true
        disp:ExitLoop()
    end

    -- клик по карточке: выбрать и сразу применить
    for c, it in ipairs(items) do
        win.On["card_" .. c].Clicked = function()
            for c2 = 1, #items do pcall(function() itm["card_" .. c2].StyleSheet = (c2 == c) and CARD_SEL or CARD end) end
            selected = it
            itm.NameEdit.Text = it.name
            apply(it)
        end
    end

    function win.On.BtnLoad.Clicked()
        if selected then apply(selected) else status("Сначала выбери пресет.") end
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
        bmd.writefile(PRESET_DIR .. name .. ".crtpreset", t)
        selected = { kind = "own", name = name }
        statusText = "Сохранён «" .. name .. "»."
        restart()
    end

    function win.On.BtnSave.Clicked()
        saveAs(itm.NameEdit.Text, current())
    end

    function win.On.BtnPaste.Clicked()
        local cb = ""
        pcall(function() local x = bmd.getclipboard(); if type(x) == "string" then cb = x end end)
        local t = fromCode(cb)
        if not t then status("В буфере нет кода CRT Pro (CRTPRO1;...).") return end
        saveAs(itm.NameEdit.Text, t)
    end

    function win.On.BtnRename.Clicked()
        if not selected or selected.kind ~= "own" then status("Переименовать можно только свой пресет (★).") return end
        local new = cleanName(itm.NameEdit.Text)
        if new == "" or new == selected.name then status("Впиши новое название в поле.") return end
        local t = bmd.readfile(PRESET_DIR .. selected.name .. ".crtpreset")
        if type(t) ~= "table" then status("Не удалось прочитать пресет.") return end
        bmd.writefile(PRESET_DIR .. new .. ".crtpreset", t)
        os.remove(PRESET_DIR .. selected.name .. ".crtpreset")
        statusText = "Переименован в «" .. new .. "»."
        selected = { kind = "own", name = new }
        restart()
    end

    function win.On.BtnDelete.Clicked()
        if not selected or selected.kind ~= "own" then status("Удалить можно только свой пресет (★).") return end
        os.remove(PRESET_DIR .. selected.name .. ".crtpreset")
        statusText = "Удалён «" .. selected.name .. "»."
        selected = nil
        restart()
    end

    function win.On.CRTPresetsWin.Close() disp:ExitLoop() end

    win:Show()
    disp:RunLoop()
    win:Hide()
end
