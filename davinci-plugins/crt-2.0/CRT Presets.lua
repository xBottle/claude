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
-- Список «Пресет» в шаблоне эффекта = встроенные + свои (★), как в 1.0.
-- Новые пункты видны в эффектах, перетащенных на клип после перезапуска Resolve.
local TEMPLATE = fusionDir() .. "Templates/Edit/Effects/Claude/CRT/CRT Pro v2.setting"
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

-- Переключатель: если окно уже открыто — эта кнопка его закрывает.
local function getD(k) local ok, v = pcall(function() return FUAPP:GetData(k) end); return ok and v or nil end
local function setD(k, v) pcall(function() FUAPP:SetData(k, v) end) end
local MARK_DIR = (os.getenv("TMPDIR") or "/tmp/") .. "/"
local OPEN_MARK, CLOSE_MARK = MARK_DIR .. "crtpro_presets.open", MARK_DIR .. "crtpro_presets.close"
local function exists(f) local h = io.open(f, "r"); if h then h:close() return true end return false end
local function touch(f) local h = io.open(f, "w"); if h then h:write(tostring(os.time())); h:close() end end
if exists(OPEN_MARK) then
    -- окно уже открыто: просим его закрыться и выходим (второе нажатие = закрыть)
    touch(CLOSE_MARK)
    os.remove(OPEN_MARK)
    local w; pcall(function() w = ui:FindWindow("CRTPresetsWin") end)
    if w then pcall(function() w:Hide() end) end
    return
end
os.remove(CLOSE_MARK)
touch(OPEN_MARK)
local disp = bmd.UIDispatcher(ui)
local tunpack = table.unpack or unpack

local function icon(name)
    local p = DIR .. "icons/" .. name .. ".png"
    if not bmd.fileexists(p) then return nil end
    local ok, ic = pcall(function() return ui:Icon{ File = p } end)
    return ok and ic or nil
end

pcall(syncTemplate)
local selected = nil     -- { kind = "builtin"/"own", index = i, name = "..." }
local statusText = ""
local reopen = true
local geom = { 200, 80, 590, 760 }

while reopen do
    reopen = false

    -- все карточки: 10 встроенных + свои
    local items = {}
    for i, n in ipairs(DATA.PRESET_NAMES) do
        items[#items + 1] = { kind = "builtin", index = i - 1, name = n, ico = "preset_" .. (i - 1) }
    end
    for _, n in ipairs(listOwn()) do
        items[#items + 1] = { kind = "own", name = n, ico = "preset_own", thumb = PRESET_DIR .. n .. ".png" }
    end

    local CARD = [[QPushButton { background:#16171d; border:1px solid #25262e; border-radius:12px; padding:3px; }
QPushButton:hover { border:1px solid #6d5dfc; background:#1b1c24; }]]
    local CARD_SEL = [[QPushButton { background:#1d1a33; border:2px solid #8b7bff; border-radius:12px; padding:2px; }]]
    local function btnStyle(color)
        return "QPushButton { background:#17181f; color:" .. color .. "; border:1px solid #2b2c36; " ..
            "border-radius:10px; padding:9px; font-weight:600; } QPushButton:hover { border-color:" .. color ..
            "; background:#1e1f28; }"
    end
    local BLUE, WHITE, GREEN, RED = "#9d8cff", "#e6e7ee", "#5eead4", "#fb7185"

    local rows = {}
    local COLS = 4
    local function iconFor(it)
        if it.thumb and bmd.fileexists(it.thumb) then
            local ok, ic = pcall(function() return ui:Icon{ File = it.thumb } end)
            if ok and ic then return ic end
        end
        return icon(it.ico) or icon("preset_0")
    end
    for r = 1, #items, COLS do
        local cells = {}
        for c = r, math.min(r + COLS - 1, #items) do
            local it = items[c]
            local isSel = selected and selected.name == it.name and selected.kind == it.kind
            cells[#cells + 1] = ui:VGroup{
                Weight = 1, Spacing = 2,
                ui:Button{
                    ID = "card_" .. c, Text = "",
                    Icon = iconFor(it),
                    IconSize = { 120, 67 }, MinimumSize = { 128, 74 }, MaximumSize = { 128, 74 },
                    ToolTip = it.name, StyleSheet = isSel and CARD_SEL or CARD,
                },
                ui:Label{
                    Text = (it.kind == "own" and "★ " or "") .. it.name, Alignment = { AlignHCenter = true },
                    StyleSheet = "color:#b9bbc7; font-size:11px;", WordWrap = true,
                },
            }
        end
        while #cells < COLS do cells[#cells + 1] = ui:HGap(128) end
        rows[#rows + 1] = ui:HGroup{ Weight = 0, Spacing = 8, tunpack(cells) }
    end

    local PAT_NAMES = {}
    for _, sec in ipairs(DATA.SECTIONS) do
        for _, c in ipairs(sec.controls) do if c.id == "PixPattern" then PAT_NAMES = c.options end end
    end
    local curPat = -1
    pcall(function() curPat = math.floor((tool:GetInput("PixPattern") or 0) + 0.5) end)
    local PAT = [[QPushButton { background:#101116; border:1px solid #25262e; border-radius:10px; padding:2px; }
QPushButton:hover { border:1px solid #22d3ee; }]]
    local PAT_SEL = [[QPushButton { background:#0f2230; border:2px solid #22d3ee; border-radius:10px; padding:1px; }]]
    local patRows = {}
    for r = 0, 9, 5 do
        local cells = {}
        for i = r, r + 4 do
            cells[#cells + 1] = ui:Button{ ID = "pat_" .. i, Text = "", Icon = icon("pattern_" .. i),
                IconSize = { 96, 54 }, MinimumSize = { 104, 60 }, MaximumSize = { 104, 60 },
                ToolTip = PAT_NAMES[i + 1] or ("Узор " .. i), StyleSheet = (i == curPat) and PAT_SEL or PAT }
        end
        patRows[#patRows + 1] = ui:HGroup{ Weight = 0, Spacing = 6, tunpack(cells) }
    end

    local win = disp:AddWindow({
        ID = "CRTPresetsWin",
        WindowTitle = "CRT PRO v2",
        Geometry = geom,
        StyleSheet = [[QWidget { background:#0e0f14; color:#e6e7ee; font-size:12px; }
QLineEdit { background:#15161c; border:1px solid #2b2c36; border-radius:10px; padding:9px; font-size:13px; color:#e6e7ee; }
QLineEdit:focus { border:1px solid #8b7bff; }]],
        ui:VGroup{
            Spacing = 8,
            ui:Label{ Text = "<img src='" .. DIR .. "icons/title.png'>", Alignment = { AlignHCenter = true }, Weight = 0 },
            ui:VGroup{ Weight = 0, Spacing = 6, tunpack(rows) },
            ui:Label{ ID = "PatLabel", Weight = 0, StyleSheet = "color:#22d3ee; font-weight:600; letter-spacing:1px; margin-top:8px;",
                Text = "УЗОР ПИКСЕЛЕЙ" .. ((PAT_NAMES[curPat + 1] and ("  ·  " .. PAT_NAMES[curPat + 1])) or "") },
            ui:VGroup{ Weight = 0, Spacing = 6, tunpack(patRows) },
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
            ui:Label{ Text = "CRT PRO v2  ·  GPU procedural core", Weight = 0, Alignment = { AlignHCenter = true },
                StyleSheet = "color:#4a4c58; font-size:10px; letter-spacing:1px;" },
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
        pcall(syncTemplate)
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

    for i = 0, 9 do
        win.On["pat_" .. i].Clicked = function()
            pcall(function() tool:SetInput("PixPattern", i) end)
            pcall(function() tool:SetInput("PixOn", 1) end)
            for j = 0, 9 do pcall(function() itm["pat_" .. j].StyleSheet = (j == i) and PAT_SEL or PAT end) end
            itm.PatLabel.Text = "УЗОР ПИКСЕЛЕЙ  ·  " .. (PAT_NAMES[i + 1] or "")
            status("Узор: " .. (PAT_NAMES[i + 1] or i))
        end
    end

    function win.On.BtnLoad.Clicked()
        applyTable(builtinValues(0), "сброс")
        pcall(function() tool:SetInput("PresetSel", 0) end)
        selected = nil
        for c2 = 1, #items do pcall(function() itm["card_" .. c2].StyleSheet = CARD end) end
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
        bmd.writefile(PRESET_DIR .. name .. ".crtpreset", t)
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
        os.rename(PRESET_DIR .. selected.name .. ".png", PRESET_DIR .. new .. ".png")
        statusText = "Переименован в «" .. new .. "»."
        selected = { kind = "own", name = new }
        restart()
    end

    function win.On.BtnThumb.Clicked()
        if not selected or selected.kind ~= "own" then status("Сначала выбери свой пресет (★).") return end
        local ok = false
        pcall(function()
            local rs = (Resolve and Resolve()) or bmd.scriptapp("Resolve")
            ok = rs:GetProjectManager():GetCurrentProject():ExportCurrentFrameAsStill(PRESET_DIR .. selected.name .. ".png")
        end)
        if ok then statusText = "Превью обновлено."; restart() else status("Не удалось снять кадр: открой клип во вьюере страницы Edit.") end
    end

    function win.On.BtnDelete.Clicked()
        if not selected or selected.kind ~= "own" then status("Удалить можно только свой пресет (★).") return end
        os.remove(PRESET_DIR .. selected.name .. ".crtpreset")
        os.remove(PRESET_DIR .. selected.name .. ".png")
        statusText = "Удалён «" .. selected.name .. "»."
        selected = nil
        restart()
    end

    function win.On.CRTPresetsWin.Close() reopen = false; disp:ExitLoop() end
    local timer
    pcall(function()
        timer = ui:Timer{ ID = "CRTCloseTimer", Interval = 300 }
        local function tick()
            if exists(CLOSE_MARK) then reopen = false; disp:ExitLoop() end
        end
        disp.On.Timeout = tick
        win.On.CRTCloseTimer.Timeout = tick
        timer:Start()
    end)

    win:Show()
    disp:RunLoop()
    if timer then pcall(function() timer:Stop() end) end
    win:Hide()
end
os.remove(OPEN_MARK)
os.remove(CLOSE_MARK)
