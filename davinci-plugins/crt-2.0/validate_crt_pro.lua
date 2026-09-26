-- Проверка CRT Pro.setting без запуска Resolve (через fuscript из комплекта Resolve).
-- Запуск: HOME=<временная папка> fuscript -l lua validate_crt_pro.lua "<путь к .setting>"
local path = _G.SETTING or (arg and arg[1])
local problems = 0
local function bad(msg) problems = problems + 1; print("  ПРОБЛЕМА: " .. msg) end

local t = bmd.readfile(path)
if type(t) ~= "table" then print("PARSE FAILED: " .. tostring(path)); return end
local grp
for _, v in pairs(t.Tools) do if type(v) == "table" and v.Tools then grp = v end end
local tools = {}
for k, v in pairs(grp.Tools) do if type(v) == "table" then tools[k] = v end end
local ctrl = tools.Ctrl
local ucs = {}
for k, v in pairs(ctrl.UserControls) do if type(v) == "table" then ucs[k] = v end end

-- 1. links between tools
local ntools = 0
for name, tool in pairs(tools) do
  ntools = ntools + 1
  for inp, v in pairs(tool.Inputs or {}) do
    if type(v) == "table" and v.SourceOp and not tools[v.SourceOp] then bad(name .. "." .. inp .. " -> " .. v.SourceOp) end
  end
end
print("инструментов внутри: " .. ntools)

-- 2. group inputs: sources exist, labels count correctly
local order = {}  -- ordered() tables iterate in file order; skip the __flags entry
for k, v in pairs(grp.Inputs) do if type(v) == "table" then order[#order + 1] = k end end
local nin = 0
for _, k in ipairs(order) do
  local ii = grp.Inputs[k]
  nin = nin + 1
  if not tools[ii.SourceOp] then bad("InstanceInput " .. k .. " -> " .. tostring(ii.SourceOp)) end
  if ii.SourceOp == "Ctrl" and not ucs[ii.Source] then bad("нет контрола " .. ii.Source) end
end
print("входов группы: " .. nin)
local labels = 0
for i, k in ipairs(order) do
  local uc = ucs[grp.Inputs[k].Source]
  if uc and uc.INPID_InputControl == "LabelControl" and uc.LBLC_DropDownButton then
    labels = labels + 1
    local n = uc.LBLC_NumInputs
    for j = i + 1, i + n do
      local kk = order[j]
      if not kk then bad("раздел " .. k .. " выходит за конец списка"); break end
      local u2 = ucs[grp.Inputs[kk].Source]
      if u2 and u2.INPID_InputControl == "LabelControl" and u2.LBLC_DropDownButton then bad("раздел " .. k .. " захватывает раздел " .. kk) end
    end
    local nxt = order[i + n + 1]
    if nxt then
      local u3 = ucs[grp.Inputs[nxt].Source]
      if not (u3 and u3.INPID_InputControl == "LabelControl") then bad("после раздела " .. k .. " остался контрол вне раздела: " .. nxt) end
    end
  end
end
print("разделов: " .. labels)

-- 3. expressions
local vals = {}
for k, v in pairs(ctrl.Inputs) do if type(v) == "table" and type(v.Value) == "number" then vals[k] = v.Value end end
local function env(over)
  local c = {}
  for k, v in pairs(vals) do c[k] = v end
  for k, v in pairs(over or {}) do c[k] = v end
  local e = { Ctrl = c, time = 37,
    InGrade = { Input = { Width = 1920, Height = 1080 }, CellPx = 4 },
    DownRes = { Input = { Width = 1920, Height = 1080 }, Width = 480, Height = 270 },
    UpRes = { Width = 1920, Height = 1080 }, ScanBlack = { Height = 4 },
    BleedShift = { Input = { Width = 1920, Height = 1080 } },
    SplitRXf = { Input = { Width = 1920, Height = 1080 } },
    SplitBXf = { Input = { Width = 1920, Height = 1080 } },
    Point = function(x, y) return { x, y } end }
  for _, f in ipairs({ "sin", "cos", "floor", "ceil", "abs", "min", "max", "sqrt" }) do e[f] = math[f] end
  return e
end
local scenarios = {
  {}, { PixDown = 0, ScanLink = 0, RGBMode = 2, CurveOn = 1, ColorResOn = 1, BleedOn = 1, ShiftOn = 1, TubeOn = 1, MonoMode = 3, FlickType = 1, ShakeBefore = 0, BandReverse = 1, NoiseOn = 1, ShakeOn = 1, FlickOn = 1, BandOn = 1, BandSpeed = -1.3 },
  { PixSize = 2.5, PixPattern = 4, ConvOn = 1, MonoOn = 1, CornerOn = 1, VigOn = 1 },
}
local nexpr = 0
for name, tool in pairs(tools) do
  for inp, v in pairs(tool.Inputs or {}) do
    if type(v) == "table" and v.Expression then
      nexpr = nexpr + 1
      local f, err = loadstring("return " .. v.Expression)
      if not f then bad(name .. "." .. inp .. " не компилируется: " .. err) else
        for si, sc in ipairs(scenarios) do
          setfenv(f, env(sc))
          local ok, res = pcall(f)
          if not ok then bad(name .. "." .. inp .. " [сценарий " .. si .. "]: " .. tostring(res))
          elseif inp == "Center" then
            if type(res) ~= "table" or res[1] ~= res[1] or res[2] ~= res[2] then bad(name .. ".Center не точка") end
          elseif type(res) ~= "number" or res ~= res or res == math.huge then
            bad(name .. "." .. inp .. " = " .. tostring(res))
          end
        end
      end
    end
  end
end
print("выражений проверено: " .. nexpr .. " (в 3 сценариях)")

-- 4. button scripts, executed against a fake tool/comp
local store = {}
local function resetStore() store = {}; for k, v in pairs(vals) do store[k] = v end end
resetStore()
local answers, captured = {}, {}
comp = {
  AskUser = function(self, title, fields)
    captured[#captured + 1] = { title = title, fields = fields }
    return table.remove(answers, 1)
  end,
  StartUndo = function() end, EndUndo = function() end,
}
tool = setmetatable({}, { __index = {
  GetInput = function(self, k) return store[k] end,
  SetInput = function(self, k, v) store[k] = v end,
} })
local buttons = {}
for k, uc in pairs(ucs) do if uc.BTNCS_Execute then buttons[k] = uc.BTNCS_Execute end end
local function press(id, ...)
  answers = { ... }
  local f, err = loadstring(buttons[id])
  if not f then bad(id .. " не компилируется: " .. err); return end
  local ok, e = pcall(f)
  if not ok then bad(id .. " упал: " .. tostring(e)) end
end
local nb = 0; for _ in pairs(buttons) do nb = nb + 1 end
print("кнопок: " .. nb)

local function runCode(code, ...)
  answers = { ... }
  local f, err = loadstring(code)
  if not f then bad("скрипт не компилируется: " .. err); return end
  local ok, e = pcall(f)
  if not ok then bad("скрипт упал: " .. tostring(e)) end
end
local function comboOf(file)
  local x = bmd.readfile(file); if type(x) ~= "table" then return nil end
  local g; for _, v in pairs(x.Tools) do if type(v) == "table" and v.Tools then g = v end end
  local names = {}
  for _, e in ipairs(g.Tools.Ctrl.UserControls.PresetSel) do names[#names + 1] = e.CCS_AddString end
  return names, g.Tools.Ctrl.UserControls.BtnApply.BTNCS_Execute
end
local _, baseApply = comboOf(path)   -- сколько пресетов встроено в сам эффект
local nBuilt = 10
do
  local list = baseApply and baseApply:match("local NAMES = (%b{})")
  local f = list and loadstring("return " .. list)
  if f then nBuilt = #f() + 1 end
end
store.PresetSel = 3; press("BtnApply")
if store.MonoOn ~= 1 or store.MonoColorRed ~= 0.2 or store.PixPattern ~= 8 then bad("пресет «Зелёный терминал» не применился") end
store.PresetSel = 9; press("BtnApply")
if store.MonoOn ~= 0 or store.BalB ~= 1.25 or store.PixPattern ~= 2 then bad("пресет «Киберпанк» не применился поверх другого") end
if nBuilt > 10 then store.PresetSel = 10; press("BtnApply", nil) end  -- вшитый пресет из пакета  -- свой пресет из сборки: файла тут нет, не должно падать
press("BtnReset")
if store.PresetSel ~= 0 or store.GlowGain ~= 1.5 or store.BalB ~= 1 then bad("сброс не сработал") end
store.GlowGain = 3.3; store.PixSize = 2
captured = {}; press("BtnCopy", nil)
local code = captured[1] and captured[1].fields[1].Default
if not code or not code:find("GlowGain=3.3") then bad("код настроек не содержит GlowGain") end
press("BtnReset"); press("BtnPaste", { Code = code })
if store.GlowGain ~= 3.3 or store.PixSize ~= 2 then bad("вставка кода не восстановила настройки") end
local FU = os.getenv("HOME") .. "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/"
local pdir, template = FU .. "CRT Pro User Presets/", FU .. "Templates/Edit/Effects/Claude/CRT/CRT Pro v2.setting"
press("BtnSave", { Name = "Тест/1" }, nil)
if not bmd.fileexists(pdir .. "Тест_1.crtpreset") then bad("свой пресет не сохранился") end
local names, applyCode = comboOf(template)
if not names or names[#names] ~= "★ Тест_1" or #names ~= nBuilt + 1 then bad("список «Пресет» в шаблоне не обновился") end
-- «новый клип»: берём кнопку «Применить» из переписанного шаблона
press("BtnReset"); store.PresetSel = nBuilt; runCode(applyCode or "", nil)
if store.GlowGain ~= 3.3 or store.PixSize ~= 2 then bad("свой пресет не применился из списка нового клипа") end
press("BtnReset"); press("BtnLoad", { Preset = 0 })
if store.GlowGain ~= 3.3 then bad("загрузка своего пресета не сработала") end
press("BtnDelete", { Preset = 0 }, nil)
if bmd.fileexists(pdir .. "Тест_1.crtpreset") then bad("свой пресет не удалился") end
names = comboOf(template)
if not names or #names ~= nBuilt then bad("после удаления список в шаблоне не очистился") end
print("кнопки прогнаны: применить (встроенные и свой), сброс, код, сохранить → список, новый клип, загрузить, удалить → список")
print(problems == 0 and "ИТОГ: проблем не найдено" or ("ИТОГ: проблем — " .. problems))
