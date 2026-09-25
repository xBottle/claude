-- CRT Pro Panel v4 — плавающее окно поверх DaVinci Resolve, управляющее нодой CRT Pro.
--
-- В отличие от v1-v3 (которые угадывали структуру через GetInputList()),
-- этот файл использует ТОЧНЫЕ данные из build_crt_pro.py (тот же генератор,
-- что собрал саму ноду) — они лежат рядом, в crt_pro_data.lua. Поэтому здесь
-- есть то, чего не было раньше: настоящие выпадающие списки (Узор, Режим RGB
-- и т.д.) и иконки — сетка из 10 узоров пикселей и 10 пресетов, кликабельные,
-- как на референсе (sh4rkk.com/procedural-crt).
--
-- Установка (ВАЖНО: теперь нужна вся папка, не один файл — иконки и данные
-- лежат рядом):
--   Скопируй ЦЕЛИКОМ папку crt-pro-panel (со всем содержимым: .lua, .png в
--   icons/, crt_pro_data.lua) в
--   ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Comp/
--   Так, чтобы получилось: .../Scripts/Comp/crt-pro-panel/CRT Pro Panel.lua
--   Пункт меню будет называться по имени файла: "CRT Pro Panel".
--
-- Запуск: выдели ноду CRT Pro на странице Fusion, Workspace > Scripts > Comp > CRT Pro Panel.

-- Определяем папку, где лежит сам этот .lua файл — чтобы найти crt_pro_data.lua
-- и icons/ рядом, независимо от того, куда именно его скопировали.
local function scriptDir()
    local src = debug.getinfo(1, "S").source
    local path = src:match("^@(.*)$") or src
    return path:match("^(.*)[/\\][^/\\]+$") .. "/"
end
local DIR = scriptDir()

local dataChunk, dataErr = loadfile(DIR .. "crt_pro_data.lua")
if not dataChunk then
    print("[CRT Pro Panel] Не найден crt_pro_data.lua рядом со скриптом: " .. tostring(dataErr))
    print("Убедись, что скопировал ВСЮ папку crt-pro-panel, а не один .lua файл.")
    return
end
local DATA = dataChunk()

local comp = fu:GetCurrentComp()
if not comp then
    print("[CRT Pro Panel] Нет активного компа. Открой страницу Fusion с клипом, на который накинут эффект.")
    return
end

----------------------------------------------------------------------------
-- 1. Найти ноду CRT Pro
----------------------------------------------------------------------------

local function findCRTTool()
    local active = comp.ActiveTool and comp:ActiveTool()
    if active then
        local ok, name = pcall(function() return active.Name end)
        if ok and name and name:lower():find("crt") then return active end
    end
    local toolList = comp:GetToolList(false)
    for _, tool in pairs(toolList) do
        local ok, name = pcall(function() return tool.Name end)
        if ok and name and name:lower():find("crt") then return tool end
    end
    return nil
end

local crtTool = findCRTTool()
if not crtTool then
    print("[CRT Pro Panel] Нода CRT Pro не найдена. Выдели её на странице Fusion и запусти скрипт снова.")
    return
end
print("[CRT Pro Panel] Подключаюсь к ноде: " .. crtTool.Name)

----------------------------------------------------------------------------
-- 2. UI
----------------------------------------------------------------------------

local ui = fu.UIManager
local disp = bmd.UIDispatcher(ui)
local tunpack = table.unpack or unpack

local function readVal(id)
    local ok, v = pcall(function() return crtTool[id] end)
    if not ok then return nil end
    return v -- может быть nil, false, число — не подменяем через "or", чтобы не терять 0/false
end
-- Числовое значение с гарантированным фолбэком — если с ноды пришло не
-- число (nil, отсутствующий параметр, рассинхрон версий) — берём дефолт,
-- а если и дефолта нет — 0. Никогда не возвращает nil, чтобы арифметика
-- ниже не падала.
local function num(v, default)
    if type(v) == "number" then return v end
    if type(default) == "number" then return default end
    return 0
end
local function icon(name)
    local p = DIR .. "icons/" .. name .. ".png"
    if bmd.fileexists and not bmd.fileexists(p) then return nil end
    local ok, ic = pcall(function() return ui:Icon{ File = p } end)
    return ok and ic or nil
end

----------------------------------------------------------------------------
-- 2a. Верхняя панель: иконки пресетов
----------------------------------------------------------------------------

local presetIconRow = {}
for i, presetName in ipairs(DATA.PRESET_NAMES) do
    local idx = i - 1
    local ic = icon("preset_" .. idx)
    table.insert(presetIconRow, ui:Button{
        ID = "preset_" .. idx,
        Text = "",
        Icon = ic,
        IconSize = { 46, 26 },
        ToolTip = presetName,
        Weight = 0,
        MinimumSize = { 50, 40 },
    })
end
local presetRow = ui:HGroup{ ID = "presetRow", tunpack(presetIconRow) }

----------------------------------------------------------------------------
-- 2b. Секции с параметрами (кроме «Пресеты» — та уже сверху иконками)
----------------------------------------------------------------------------

local sectionBlocks = {}
local allSectionRows = {}
local widgetIndex = {}   -- id -> {widgetID=..., labelID=..., ctrl=...}

-- Собрать один ряд параметра — вынесено в функцию, чтобы обернуть в pcall:
-- если конкретный параметр почему-то сломан (нет на ноде, битые данные),
-- вся панель не падает, а этот один ряд заменяется меткой с ошибкой.
local function buildControlRow(ctrl, widgetID, labelID)
    local rows = {}
    -- v5: сетку иконок для "Узор" убрал — она ломала раскладку аккордеона
    -- (все параметры схлопывались в одну точку). Пока "Узор" — обычный
    -- дропдаун, как остальные combo-параметры. Иконки узоров остаются
    -- в icons/pattern_*.png на будущее — можно будет попробовать другой
    -- способ их встроить отдельным шагом.
    if ctrl.kind == "slider" then
                    local lo = num(ctrl.lo, 0)
                    local hi = num(ctrl.hi, 1)
                    if hi <= lo then hi = lo + 1 end
                    local span = hi - lo
                    local v = num(readVal(ctrl.id), num(ctrl.default, lo))
                    local sliderVal = math.floor(((v - lo) / span) * 1000 + 0.5)
                    table.insert(rows, ui:HGroup{
                        Weight = 0,
                        ui:Label{ Text = ctrl.name, MinimumSize = { 190, 0 } },
                        ui:Slider{ ID = widgetID, Min = 0, Max = 1000, Value = sliderVal, MinimumSize = { 140, 0 } },
                        ui:Label{ ID = labelID, Text = string.format("%.3f", v), MinimumSize = { 55, 0 } },
                    })
                elseif ctrl.kind == "check" then
                    local v = readVal(ctrl.id)
                    if v == nil then v = ctrl.default end
                    table.insert(rows, ui:HGroup{
                        Weight = 0,
                        ui:Label{ Text = ctrl.name, MinimumSize = { 190, 0 } },
                        ui:CheckBox{ ID = widgetID, Checked = (v == 1 or v == true) },
                    })
                elseif ctrl.kind == "combo" then
                    local combo = ui:ComboBox{ ID = widgetID, MinimumSize = { 200, 0 } }
                    table.insert(rows, ui:HGroup{
                        Weight = 0,
                        ui:Label{ Text = ctrl.name, MinimumSize = { 190, 0 } },
                        combo,
                    })
                    -- список опций наполняется после создания окна (нужен itm)
                elseif ctrl.kind == "color" then
                    for _, ch in ipairs({ "Red", "Green", "Blue" }) do
                        local subID = "w_" .. ctrl.id .. ch
                        local subLbl = "l_" .. ctrl.id .. ch
                        local v = num(readVal(ctrl.id .. ch), 0)
                        widgetIndex[ctrl.id .. ch] = { widgetID = subID, labelID = subLbl,
                            ctrl = { id = ctrl.id .. ch, kind = "slider", lo = 0, hi = 2, name = ctrl.name .. ": " .. ch } }
                        table.insert(rows, ui:HGroup{
                            Weight = 0,
                            ui:Label{ Text = ctrl.name .. ": " .. ch, MinimumSize = { 190, 0 } },
                            ui:Slider{ ID = subID, Min = 0, Max = 1000, Value = math.floor((v / 2) * 1000 + 0.5), MinimumSize = { 140, 0 } },
                            ui:Label{ ID = subLbl, Text = string.format("%.3f", v), MinimumSize = { 55, 0 } },
                        })
                    end
    end
    return rows
end

for si, sec in ipairs(DATA.SECTIONS) do
    if sec.id ~= "SecPresets" then
        local rows = {}
        for ci, ctrl in ipairs(sec.controls) do
            if ctrl.kind ~= "button" then
                local widgetID = string.format("w_%s", ctrl.id)
                local labelID = "l_" .. ctrl.id
                widgetIndex[ctrl.id] = { widgetID = widgetID, labelID = labelID, ctrl = ctrl }

                local ok, result = pcall(buildControlRow, ctrl, widgetID, labelID)
                if ok and result then
                    for _, r in ipairs(result) do table.insert(rows, r) end
                else
                    widgetIndex[ctrl.id] = nil
                    print(string.format("[CRT Pro Panel] Параметр %s (%s) пропущен из-за ошибки: %s",
                        ctrl.id, ctrl.name, tostring(result)))
                    table.insert(rows, ui:Label{ Text = "⚠ " .. ctrl.name .. " — не удалось построить (см. консоль)", Weight = 0 })
                end
            end
        end

        local bodyID = "body_" .. si
        local headerID = "hdr_" .. si
        local expanded = sec.open
        local body = ui:VGroup{ ID = bodyID, Hidden = not expanded, tunpack(rows) }
        local header = ui:Button{ ID = headerID, Flat = true, Weight = 0,
            Text = (expanded and "▼ " or "▶ ") .. sec.title .. "  (" .. #sec.controls .. ")" }

        table.insert(sectionBlocks, { headerID = headerID, bodyID = bodyID, expanded = expanded,
            title = sec.title, count = #sec.controls })
        table.insert(allSectionRows, header)
        table.insert(allSectionRows, body)
    end
end

local rowsGroup = ui:VGroup{ ID = "rowsGroup", tunpack(allSectionRows) }

local win = disp:AddWindow({
    ID = "CRTProPanelWin",
    WindowTitle = "CRT Pro — " .. crtTool.Name,
    Geometry = { 80, 80, 500, 820 },
    Spacing = 4,

    ui:VGroup{
        ui:Label{ Text = "Пресеты", Weight = 0 },
        presetRow,
        ui:TextEdit{ ID = "log", ReadOnly = true, MaximumSize = { 2000, 36 }, Text = "" },
        rowsGroup,
        ui:HGroup{ Weight = 0,
            ui:Button{ ID = "ExpandAllBtn", Text = "Развернуть всё" },
            ui:Button{ ID = "CollapseAllBtn", Text = "Свернуть всё" },
            ui:Button{ ID = "RefreshBtn", Text = "Обновить из ноды" },
            ui:Button{ ID = "CloseBtn", Text = "Закрыть" },
        },
    },
})

local itm = win:GetItems()

-- Наполнить дропдауны опциями (после создания окна, когда itm доступен).
for _, sec in ipairs(DATA.SECTIONS) do
    for _, ctrl in ipairs(sec.controls) do
        if ctrl.kind == "combo" and ctrl.id ~= "PresetSel" then
            local w = widgetIndex[ctrl.id]
            if w and itm[w.widgetID] then
                local okFill, err = pcall(function()
                    for _, opt in ipairs(ctrl.options or {}) do itm[w.widgetID]:AddItem(opt) end
                    local v = num(readVal(ctrl.id), num(ctrl.default, 0))
                    itm[w.widgetID].CurrentIndex = math.floor(v + 0.5)
                end)
                if not okFill then
                    print("[CRT Pro Panel] Дропдаун " .. ctrl.id .. " не заполнился: " .. tostring(err))
                end
            end
        end
    end
end

----------------------------------------------------------------------------
-- 3. Сворачивание разделов
----------------------------------------------------------------------------

local function setSectionExpanded(block, expanded)
    block.expanded = expanded
    itm[block.bodyID].Hidden = not expanded
    itm[block.headerID].Text = (expanded and "▼ " or "▶ ") .. block.title .. "  (" .. block.count .. ")"
end
for _, block in ipairs(sectionBlocks) do
    local b = block
    win.On[block.headerID].Clicked = function(ev) setSectionExpanded(b, not b.expanded) end
end
function win.On.ExpandAllBtn.Clicked(ev) for _, b in ipairs(sectionBlocks) do setSectionExpanded(b, true) end end
function win.On.CollapseAllBtn.Clicked(ev) for _, b in ipairs(sectionBlocks) do setSectionExpanded(b, false) end end

----------------------------------------------------------------------------
-- 4. Двусторонняя связь: окно -> нода
----------------------------------------------------------------------------

local function setValue(id, v)
    comp:StartUndo("CRT Pro Panel")
    crtTool[id] = v
    comp:EndUndo(true)
end

local function refreshAllWidgets()
    for id, w in pairs(widgetIndex) do
        local v = readVal(id)
        if type(v) == "number" and itm[w.widgetID] then
            if w.ctrl.kind == "slider" then
                local lo = num(w.ctrl.lo, 0)
                local hi = num(w.ctrl.hi, 1)
                if hi <= lo then hi = lo + 1 end
                itm[w.widgetID].Value = math.floor(((v - lo) / (hi - lo)) * 1000 + 0.5)
                itm[w.labelID].Text = string.format("%.3f", v)
            elseif w.ctrl.kind == "check" then
                itm[w.widgetID].Checked = (v == 1)
            elseif w.ctrl.kind == "combo" then
                itm[w.widgetID].CurrentIndex = math.floor(v + 0.5)
            end
        end
    end
end

for id, w in pairs(widgetIndex) do
    local ctrl = w.ctrl
    if ctrl.kind == "slider" then
        local lo = num(ctrl.lo, 0)
        local hi = num(ctrl.hi, 1)
        if hi <= lo then hi = lo + 1 end
        win.On[w.widgetID].ValueChanged = function(ev)
            local raw = itm[w.widgetID].Value
            local v = lo + (raw / 1000) * (hi - lo)
            itm[w.labelID].Text = string.format("%.3f", v)
            setValue(id, v)
        end
    elseif ctrl.kind == "check" then
        win.On[w.widgetID].Clicked = function(ev)
            setValue(id, itm[w.widgetID].Checked and 1 or 0)
        end
    elseif ctrl.kind == "combo" then
        win.On[w.widgetID].CurrentIndexChanged = function(ev)
            setValue(id, itm[w.widgetID].CurrentIndex)
        end
    end
end

-- Иконки пресетов: применяем DEFAULTS + PRESETS[i] локально (без нажатия
-- родной кнопки — она рассчитана на клик из самого Inspector).
for i = 0, #DATA.PRESET_NAMES - 1 do
    win.On["preset_" .. i].Clicked = function(ev)
        comp:StartUndo("CRT Pro Panel: пресет " .. DATA.PRESET_NAMES[i + 1])
        for k, v in pairs(DATA.DEFAULTS) do crtTool[k] = v end
        for k, v in pairs(DATA.PRESETS[i] or {}) do crtTool[k] = v end
        crtTool.PresetSel = i
        comp:EndUndo(true)
        refreshAllWidgets()
        itm.log.Text = "Применён пресет: " .. DATA.PRESET_NAMES[i + 1]
    end
end

function win.On.RefreshBtn.Clicked(ev)
    refreshAllWidgets()
    itm.log.Text = "Обновлено из ноды."
end
function win.On.CloseBtn.Clicked(ev) disp:ExitLoop() end
function win.On.CRTProPanelWin.Close(ev) disp:ExitLoop() end

win:Show()
disp:RunLoop()
win:Hide()
