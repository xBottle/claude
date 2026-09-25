-- CRT Pro Panel — плавающее окно поверх DaVinci Resolve, управляющее нодой CRT Pro.
--
-- Как это работает:
--   1. Скрипт находит выделенную ноду в активном Fusion-компе (странице Edit/Fusion).
--   2. Читает СПИСОК ЕЁ ВХОДОВ через GetInputList() — то есть не нужно вручную
--      прописывать имена всех 129 контролов, скрипт видит их сам, какие они есть
--      в реальном .setting на твоей машине.
--   3. Строит окно: числовые входы -> слайдер, булевы -> галочка, FuID (режимы) ->
--      выпадающий список, цвет -> цветовой квадрат.
--   4. Любое движение в окне сразу пишет в comp:SetInput(...) — то есть это
--      обычный Fusion-инструмент, просто с другим лицом поверх Resolve.
--
-- Установка:
--   Скопировать этот файл в
--   ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Comp/
--   Дать имя без изменений — "CRT Pro Panel.lua" (имя файла = имя в меню Scripts).
--
-- Запуск:
--   1. Открыть страницу Edit (или Fusion), выделить клип с эффектом CRT Pro.
--   2. Кликнуть на ноду CRT Pro в Fusion (если открыт Fusion) ЛИБО просто иметь
--      эффект применённым на клипе — скрипт сам найдёт первую ноду с именем,
--      содержащим "CRT" в активном компе.
--   3. Workspace > Scripts > Comp > CRT Pro Panel.
--
-- Если хочешь навесить на горячую клавишу — Resolve позволяет назначить
-- сочетание на пункт меню Scripts через System Preferences > Keyboard (macOS)
-- либо через Fusion Keyboard Customization (страница Fusion > меню Fusion).

local comp = fu:GetCurrentComp()
if not comp then
    print("[CRT Pro Panel] Нет активного компа. Открой страницу Edit/Fusion с клипом, на который накинут эффект.")
    return
end

----------------------------------------------------------------------------
-- 1. Найти ноду CRT Pro
----------------------------------------------------------------------------

local function findCRTTool()
    -- Сначала — активный выделенный инструмент.
    local active = comp.ActiveTool and comp:ActiveTool()
    if active then
        local ok, name = pcall(function() return active.Name end)
        if ok and name and name:lower():find("crt") then
            return active
        end
    end
    -- Иначе перебрать все ноды и найти первую с "crt" в имени.
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
    print("Открой Fusion-страницу, выдели ноду CRT Pro (или её GroupOperator) и запусти скрипт снова.")
    return
end

print("[CRT Pro Panel] Подключаюсь к ноде: " .. crtTool.Name)

----------------------------------------------------------------------------
-- 2. Прочитать список входов ноды
----------------------------------------------------------------------------

-- GetInputList() возвращает таблицу Input-объектов, индексированных по номеру
-- и по имени. Идём по числовым ключам, чтобы не задвоить.
local rawInputs = crtTool:GetInputList()
local controls = {}  -- { {id=..., name=..., kind=..., value=..., min=..., max=...}, ... }

local SKIP_NAMES = {
    -- Служебные/внутренние входы, которые не нужно показывать в UI.
    ["Blend"] = true,
}

for key, input in pairs(rawInputs) do
    if type(key) == "number" then
        local ok, attrs = pcall(function() return input:GetAttrs() end)
        if ok and attrs then
            local id = attrs.INPS_ID or ("Input" .. tostring(key))
            local name = attrs.INPS_Name or id
            if not SKIP_NAMES[id] then
                local dataType = attrs.INPS_DataType or ""
                local kind = "unknown"
                local cur = nil
                local okVal, val = pcall(function() return input[0] end) -- значение на текущем кадре (числовое/текст)

                if dataType == "Number" then
                    kind = "number"
                    cur = okVal and val or 0
                elseif dataType == "FuID" then
                    -- Может быть чекбокс (Boolean под капотом отдаёт 0/1) либо режим (строка).
                    kind = "fuid"
                    cur = okVal and val or ""
                elseif dataType == "Point" then
                    kind = "point"
                elseif dataType == "Image" then
                    kind = "image" -- пропускаем, это вход картинки, не параметр
                else
                    kind = "other"
                end

                if kind == "number" or kind == "fuid" then
                    table.insert(controls, {
                        id = id,
                        name = name,
                        kind = kind,
                        value = cur,
                        min = attrs.INPID_InputControl == "SliderControl" and 0 or nil,
                    })
                end
            end
        end
    end
end

table.sort(controls, function(a, b) return a.name < b.name end)

print(string.format("[CRT Pro Panel] Найдено параметров для панели: %d", #controls))

if #controls == 0 then
    print("[CRT Pro Panel] У ноды нет читаемых числовых/FuID входов — нечего показывать.")
    return
end

----------------------------------------------------------------------------
-- 3. Построить окно
----------------------------------------------------------------------------

local ui = fu.UIManager
local disp = bmd.UIDispatcher(ui)

-- Собираем колонку виджетов динамически.
local rows = {}
for i, ctrl in ipairs(controls) do
    local sliderID = "ctrl_" .. i
    local labelID = "lbl_" .. i

    if ctrl.kind == "number" then
        table.insert(rows, ui:HGroup{
            Weight = 0,
            ui:Label{ Text = ctrl.name, MinimumSize = { 160, 0 } },
            ui:Slider{ ID = sliderID, Min = -100, Max = 100, Value = ctrl.value, MinimumSize = { 140, 0 } },
            ui:Label{ ID = labelID, Text = string.format("%.2f", ctrl.value), MinimumSize = { 50, 0 } },
        })
    else -- fuid — чаще всего чекбокс 0/1
        table.insert(rows, ui:HGroup{
            Weight = 0,
            ui:Label{ Text = ctrl.name, MinimumSize = { 160, 0 } },
            ui:CheckBox{ ID = sliderID, Checked = (tostring(ctrl.value) == "1" or ctrl.value == true) },
        })
    end
end

local scrollContent = ui:VGroup{ ID = "scrollRoot" }
for _, row in ipairs(rows) do
    table.insert(scrollContent, row)
end

local win = disp:AddWindow({
    ID = "CRTProPanelWin",
    WindowTitle = "CRT Pro — " .. crtTool.Name,
    Geometry = { 80, 80, 420, 600 },
    Spacing = 6,

    ui:VGroup{
        ui:Label{ Text = "CRT Pro — свой плавающий Inspector", Alignment = { AlignHCenter = true } },
        ui:TextEdit{ ID = "log", ReadOnly = true, MaximumSize = { 2000, 0 }, Text = "" },
        ui:Tree{ ID = "unused", Hidden = true }, -- (место для будущего дерева пресетов)
        table.unpack(rows),
        ui:HGroup{
            Weight = 0,
            ui:Button{ ID = "RefreshBtn", Text = "Обновить из ноды" },
            ui:Button{ ID = "CloseBtn", Text = "Закрыть" },
        },
    },
})

local itm = win:GetItems()

----------------------------------------------------------------------------
-- 4. Двусторонняя связь: окно -> нода
----------------------------------------------------------------------------

for i, ctrl in ipairs(controls) do
    local sliderID = "ctrl_" .. i
    local labelID = "lbl_" .. i
    local capturedCtrl = ctrl -- локальная копия для замыкания

    if ctrl.kind == "number" then
        win.On[sliderID].ValueChanged = function(ev)
            local v = itm[sliderID].Value
            itm[labelID].Text = string.format("%.2f", v)
            comp:StartUndo("CRT Pro Panel: " .. capturedCtrl.name)
            crtTool[capturedCtrl.id] = v
            comp:EndUndo(true)
        end
    else
        win.On[sliderID].Clicked = function(ev)
            local checked = itm[sliderID].Checked
            comp:StartUndo("CRT Pro Panel: " .. capturedCtrl.name)
            crtTool[capturedCtrl.id] = checked and 1 or 0
            comp:EndUndo(true)
        end
    end
end

function win.On.RefreshBtn.Clicked(ev)
    -- Перечитать значения из ноды (например, если их поменяли в самом Inspector)
    -- и обновить виджеты без пересоздания окна.
    for i, ctrl in ipairs(controls) do
        local okVal, val = pcall(function() return crtTool[ctrl.id] end)
        if okVal then
            if ctrl.kind == "number" then
                itm["ctrl_" .. i].Value = val
                itm["lbl_" .. i].Text = string.format("%.2f", val)
            else
                itm["ctrl_" .. i].Checked = (tostring(val) == "1")
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
