-- Прототип: плавающее окно поверх Resolve через Fusion UIManager (Lua).
-- НЕ встроено в Inspector — отдельное окно, которое можно таскать по экрану.
-- Запуск: DaVinci Resolve → страница Fusion → Console (или через меню Scripts) →
--   Workspace > Scripts > Comp > положить этот файл в
--   ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Comp/
--   и запустить из меню Workspace > Scripts > Comp > "CRT Proto Window".
--
-- Идея: три слайдера в своём окне управляют тремя инпутами ноды Custom1
-- в текущем композе (или просто печатают значения в консоль, если ноды нет).

local ui = fu.UIManager
local disp = bmd.UIDispatcher(ui)

local win = disp:AddWindow({
    ID = "CRTProtoWin",
    WindowTitle = "CRT Pro (прототип, UIManager)",
    Geometry = { 100, 100, 340, 260 },
    Spacing = 10,

    ui:VGroup{
        ID = "root",
        ui:Label{ Text = "Прототип окна поверх Resolve", Weight = 0, Alignment = { AlignHCenter = true } },

        ui:VGroup{
            ui:Label{ Text = "Размер пикселя" },
            ui:HGroup{
                ui:Slider{ ID = "SizeSlider", Min = 1, Max = 20, Value = 4 },
                ui:Label{ ID = "SizeLabel", Text = "4", MinimumSize = { 30, 0 } },
            },
        },

        ui:VGroup{
            ui:Label{ Text = "Свечение" },
            ui:HGroup{
                ui:Slider{ ID = "GlowSlider", Min = 0, Max = 100, Value = 30 },
                ui:Label{ ID = "GlowLabel", Text = "30", MinimumSize = { 30, 0 } },
            },
        },

        ui:VGroup{
            ui:Label{ Text = "Развёртка (Scanlines)" },
            ui:HGroup{
                ui:Slider{ ID = "ScanSlider", Min = 0, Max = 100, Value = 50 },
                ui:Label{ ID = "ScanLabel", Text = "50", MinimumSize = { 30, 0 } },
            },
        },

        ui:HGroup{
            Weight = 0,
            ui:Button{ ID = "ApplyBtn", Text = "Применить к комп-нодам" },
            ui:Button{ ID = "CloseBtn", Text = "Закрыть" },
        },
    },
})

local itm = win:GetItems()

-- Живое обновление подписей при движении слайдера
function win.On.SizeSlider.ValueChanged(ev)
    itm.SizeLabel.Text = tostring(itm.SizeSlider.Value)
end
function win.On.GlowSlider.ValueChanged(ev)
    itm.GlowLabel.Text = tostring(itm.GlowSlider.Value)
end
function win.On.ScanSlider.ValueChanged(ev)
    itm.ScanLabel.Text = tostring(itm.ScanSlider.Value)
end

-- Применить значения к реальной ноде в компе (если есть comp и нода "CRTProto")
function win.On.ApplyBtn.Clicked(ev)
    local comp = fu:GetCurrentComp()
    if not comp then
        print("Нет активного компа Fusion — открой страницу Fusion с любым клипом.")
        return
    end
    local tool = comp:FindTool("CRTProto")
    if not tool then
        print(string.format(
            "Нода 'CRTProto' не найдена в текущем компе. Значения: Size=%s Glow=%s Scan=%s",
            itm.SizeSlider.Value, itm.GlowSlider.Value, itm.ScanSlider.Value
        ))
        return
    end
    comp:StartUndo("CRT Proto: применить из окна")
    tool.PixelSize = itm.SizeSlider.Value
    tool.Glow = itm.GlowSlider.Value / 100.0
    tool.Scanlines = itm.ScanSlider.Value / 100.0
    comp:EndUndo(true)
    print("Применено к ноде CRTProto.")
end

function win.On.CloseBtn.Clicked(ev)
    disp:ExitLoop()
end
function win.On.CRTProtoWin.Close(ev)
    disp:ExitLoop()
end

win:Show()
disp:RunLoop()
win:Hide()
