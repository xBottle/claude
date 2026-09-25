-- CRT Pro Panel — плавающее окно поверх DaVinci Resolve, управляющее нодой CRT Pro.
--
-- v2: параметры сгруппированы по разделам (как в обычном Inspector), разделы
-- сворачиваются кликом по заголовку — свёрнуты по умолчанию, кроме первого.
-- Группировка берётся из самой ноды: разделы там сделаны как LabelControl
-- с LBLC_DropDownButton/LBLC_NumInputs, скрипт читает эту же разметку, а не
-- гадает по именам.
--
-- Установка:
--   Скопировать этот файл в
--   ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Comp/
--   Имя файла не менять — "CRT Pro Panel.lua".
--
-- Запуск:
--   1. Выделить клип с эффектом CRT Pro, открыть страницу Fusion.
--   2. Кликнуть на ноду CRT Pro в графе (или просто иметь её единственной с "CRT" в имени).
--   3. Workspace > Scripts > Comp > CRT Pro Panel.

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
        if ok and name and name:lower():find("crt") then
            return active
        end
    end
    local toolList = comp:GetToolList(false)
    for _, tool in pairs(toolList) do
        local ok, name = pcall(function() return tool.Name end)
        if ok and name and name:lower():find("crt") then
            return tool
        end
    end
    return nil
end

local crtTool = findCRTTool()
if not crtTool then
    print("[CRT Pro Panel] Нода CRT Pro не найдена в текущем компе.")
    print("Открой Fusion-страницу, выдели ноду CRT Pro и запусти скрипт снова.")
    return
end

print("[CRT Pro Panel] Подключаюсь к ноде: " .. crtTool.Name)

----------------------------------------------------------------------------
-- 2. Прочитать входы В ИХ РЕАЛЬНОМ ПОРЯДКЕ и разложить по разделам
----------------------------------------------------------------------------

local rawInputs = crtTool:GetInputList()

-- Сначала собрать (номер, input) в массив и отсортировать по номеру —
-- GetInputList() в Lua отдаёт таблицу вперемешку по ключам, а порядок
-- создания (= порядок в Inspector) важен для разбивки на разделы.
local ordered = {}
for key, input in pairs(rawInputs) do
    if type(key) == "number" then
        table.insert(ordered, { key = key, input = input })
    end
end
table.sort(ordered, function(a, b) return a.key < b.key end)

local SKIP_IDS = { Blend = true }

local sections = {}          -- { {title=..., controls={...}}, ... } по порядку
local fallback = { title = "Общие (до первого раздела)", controls = {} }
local currentSection = nil
local skippedButtons, skippedCombos = 0, 0

-- Важно: LBLC_NumInputs (сколько входов относится к разделу) при чтении
-- через GetAttrs() после создания ноды не возвращается — это поле только
-- для момента сборки .setting. Поэтому границу раздела определяем проще
-- и надёжнее: "всё, что идёт после этого заголовка и до следующего —
-- относится к текущему разделу", без подсчёта штук.
for _, entry in ipairs(ordered) do
    local input = entry.input
    local ok, attrs = pcall(function() return input:GetAttrs() end)
    if ok and attrs then
        local id = attrs.INPS_ID or ("Input" .. tostring(entry.key))
        local name = attrs.INPS_Name or id
        local inputControl = attrs.INPID_InputControl or ""
        local dataType = attrs.INPS_DataType or ""

        if inputControl == "LabelControl" then
            local newSection = { title = name, controls = {} }
            table.insert(sections, newSection)
            currentSection = newSection

        elseif inputControl == "ButtonControl" then
            -- Кнопки (Применить пресет, Сохранить и т.п.) — не параметр, пропускаем.
            skippedButtons = skippedButtons + 1

        elseif not SKIP_IDS[id] then
            local kind = nil
            local cur = nil
            local okVal, val = pcall(function() return input[0] end)

            if dataType == "Number" and inputControl == "CheckboxControl" then
                kind = "checkbox"
                cur = okVal and val or 0
            elseif dataType == "Number" then
                kind = "number"
                cur = okVal and val or 0
            elseif dataType == "FuID" and inputControl == "ComboControl" then
                skippedCombos = skippedCombos + 1
            end

            if kind then
                local lo = attrs.INP_MinScale or attrs.INP_MinAllowed
                local hi = attrs.INP_MaxScale or attrs.INP_MaxAllowed
                if kind == "checkbox" then lo, hi = 0, 1 end
                if not lo or not hi or lo >= hi then lo, hi = 0, 1 end

                local ctrl = { id = id, name = name, kind = kind, value = cur, min = lo, max = hi }
                local target = currentSection and currentSection.controls or fallback.controls
                table.insert(target, ctrl)
            end
        end
    end
end

if #fallback.controls > 0 then
    table.insert(sections, 1, fallback)
end

-- Разные контролы с одинаковым именем ("Включить" в каждом разделе) —
-- дописываем ID в скобках, чтобы не путались при поиске в консоли.
do
    local nameCount = {}
    for _, sec in ipairs(sections) do
        for _, ctrl in ipairs(sec.controls) do
            nameCount[ctrl.name] = (nameCount[ctrl.name] or 0) + 1
        end
    end
    for _, sec in ipairs(sections) do
        for _, ctrl in ipairs(sec.controls) do
            ctrl.displayName = nameCount[ctrl.name] > 1 and (ctrl.name .. " (" .. ctrl.id .. ")") or ctrl.name
        end
    end
end

local totalControls = 0
for _, sec in ipairs(sections) do totalControls = totalControls + #sec.controls end

print(string.format(
    "[CRT Pro Panel] Разделов: %d, параметров: %d (пропущено кнопок: %d, выпадающих списков: %d)",
    #sections, totalControls, skippedButtons, skippedCombos
))

if totalControls == 0 then
    print("[CRT Pro Panel] Не нашлось ни одного слайдера/чекбокса — нечего показывать.")
    return
end

----------------------------------------------------------------------------
-- 3. Построить окно: каждый раздел — сворачиваемая группа
----------------------------------------------------------------------------

local ui = fu.UIManager
local disp = bmd.UIDispatcher(ui)
local tunpack = table.unpack or unpack

local sectionBlocks = {}   -- { {headerBtnID=..., bodyID=..., expanded=bool}, ... }
local allRows = {}         -- плоский список всех VGroup-секций для окна

for si, sec in ipairs(sections) do
    local rows = {}
    for i, ctrl in ipairs(sec.controls) do
        local widgetID = string.format("s%d_c%d", si, i)
        local labelID = string.format("s%d_l%d", si, i)
        ctrl.widgetID = widgetID
        ctrl.labelID = labelID

        if ctrl.kind == "number" then
            local span = ctrl.max - ctrl.min
            local sliderVal = math.floor(((ctrl.value - ctrl.min) / span) * 1000 + 0.5)
            table.insert(rows, ui:HGroup{
                Weight = 0,
                ui:Label{ Text = ctrl.displayName, MinimumSize = { 190, 0 } },
                ui:Slider{ ID = widgetID, Min = 0, Max = 1000, Value = sliderVal, MinimumSize = { 140, 0 } },
                ui:Label{ ID = labelID, Text = string.format("%.3f", ctrl.value), MinimumSize = { 55, 0 } },
            })
        else
            table.insert(rows, ui:HGroup{
                Weight = 0,
                ui:Label{ Text = ctrl.displayName, MinimumSize = { 190, 0 } },
                ui:CheckBox{ ID = widgetID, Checked = (tostring(ctrl.value) == "1" or ctrl.value == true) },
            })
        end
    end

    local bodyID = "body_" .. si
    local headerID = "hdr_" .. si
    local expanded = (si == 1) -- первый раздел открыт, остальные свёрнуты

    local body = ui:VGroup{ ID = bodyID, Hidden = not expanded, tunpack(rows) }
    local header = ui:Button{
        ID = headerID,
        Text = (expanded and "▼ " or "▶ ") .. sec.title .. "  (" .. #sec.controls .. ")",
        Flat = true,
        Weight = 0,
    }

    table.insert(sectionBlocks, { headerID = headerID, bodyID = bodyID, expanded = expanded, title = sec.title, count = #sec.controls })
    table.insert(allRows, header)
    table.insert(allRows, body)
end

local rowsGroup = ui:VGroup{ ID = "rowsGroup", tunpack(allRows) }

local win = disp:AddWindow({
    ID = "CRTProPanelWin",
    WindowTitle = "CRT Pro — " .. crtTool.Name,
    Geometry = { 80, 80, 480, 800 },
    Spacing = 4,

    ui:VGroup{
        ui:Label{ Text = "CRT Pro — свой плавающий Inspector. Клик по заголовку сворачивает/разворачивает раздел.", Alignment = { AlignHCenter = true }, WordWrap = true },
        ui:TextEdit{ ID = "log", ReadOnly = true, MaximumSize = { 2000, 40 }, Text = "" },
        rowsGroup,
        ui:HGroup{
            Weight = 0,
            ui:Button{ ID = "ExpandAllBtn", Text = "Развернуть всё" },
            ui:Button{ ID = "CollapseAllBtn", Text = "Свернуть всё" },
            ui:Button{ ID = "RefreshBtn", Text = "Обновить из ноды" },
            ui:Button{ ID = "CloseBtn", Text = "Закрыть" },
        },
    },
})

local itm = win:GetItems()

----------------------------------------------------------------------------
-- 4. Сворачивание разделов
----------------------------------------------------------------------------

local function setSectionExpanded(block, expanded)
    block.expanded = expanded
    itm[block.bodyID].Hidden = not expanded
    itm[block.headerID].Text = (expanded and "▼ " or "▶ ") .. block.title .. "  (" .. block.count .. ")"
end

for _, block in ipairs(sectionBlocks) do
    local capturedBlock = block
    win.On[block.headerID].Clicked = function(ev)
        setSectionExpanded(capturedBlock, not capturedBlock.expanded)
    end
end

function win.On.ExpandAllBtn.Clicked(ev)
    for _, block in ipairs(sectionBlocks) do setSectionExpanded(block, true) end
end
function win.On.CollapseAllBtn.Clicked(ev)
    for _, block in ipairs(sectionBlocks) do setSectionExpanded(block, false) end
end

----------------------------------------------------------------------------
-- 5. Двусторонняя связь: окно -> нода
----------------------------------------------------------------------------

for _, sec in ipairs(sections) do
    for _, ctrl in ipairs(sec.controls) do
        local capturedCtrl = ctrl
        if ctrl.kind == "number" then
            win.On[ctrl.widgetID].ValueChanged = function(ev)
                local raw = itm[capturedCtrl.widgetID].Value
                local span = capturedCtrl.max - capturedCtrl.min
                local v = capturedCtrl.min + (raw / 1000) * span
                itm[capturedCtrl.labelID].Text = string.format("%.3f", v)
                comp:StartUndo("CRT Pro Panel: " .. capturedCtrl.name)
                crtTool[capturedCtrl.id] = v
                comp:EndUndo(true)
            end
        else
            win.On[ctrl.widgetID].Clicked = function(ev)
                local checked = itm[capturedCtrl.widgetID].Checked
                comp:StartUndo("CRT Pro Panel: " .. capturedCtrl.name)
                crtTool[capturedCtrl.id] = checked and 1 or 0
                comp:EndUndo(true)
            end
        end
    end
end

function win.On.RefreshBtn.Clicked(ev)
    for _, sec in ipairs(sections) do
        for _, ctrl in ipairs(sec.controls) do
            local okVal, val = pcall(function() return crtTool[ctrl.id] end)
            if okVal then
                if ctrl.kind == "number" then
                    local span = ctrl.max - ctrl.min
                    local raw = math.floor(((val - ctrl.min) / span) * 1000 + 0.5)
                    itm[ctrl.widgetID].Value = raw
                    itm[ctrl.labelID].Text = string.format("%.3f", val)
                else
                    itm[ctrl.widgetID].Checked = (tostring(val) == "1")
                end
            end
        end
    end
    itm.log.Text = "Обновлено из ноды."
end

function win.On.CloseBtn.Clicked(ev)
    disp:ExitLoop()
end
function win.On.CRTProPanelWin.Close(ev)
    disp:ExitLoop()
end

win:Show()
disp:RunLoop()
win:Hide()
