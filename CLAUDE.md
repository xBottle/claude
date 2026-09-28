# Эффекты для DaVinci Resolve (заказчик: Илья, общение по-русски, коротко)

## Главный продукт — CRT Pro v2 (`davinci-plugins/crt-2.0/`)

ПРАВИЛО: после ЛЮБОЙ правки эффекта пересобрать и отдать финальный архив:
`cd davinci-plugins/crt-2.0 && python3 make_release.py` → `dist/CRT Pro.zip` (полная) и `dist/CRT Pro Demo.zip` (демо: водяной знак, 3 пресета, 3 крутилки — PixSize/PixBright/PixGamma, без окна и DCTL)
(dist/ в .gitignore; архив отправлять пользователю через SendUserFile).

| Файл | Что это |
|---|---|
| `build_crt_pro_2.py` | генератор: SECTIONS (все контролы), PRESETS (18), PAGES/TAB_NOTES (вкладки Инспектора), цепочка нод, `.setting` + `.fuse` |
| `crt_core_template.fuse` | GPU-ядро (DVIPComputeNode), 2 прохода: Stage 0 цвет/пиксели/строки/сведение, Stage 1 выпуклость/полоса/мерцание/виньетка/зерно/углы/блик/послесвечение/микс. Править шаблон, не `effect/CRTCore.fuse` |
| `CRT Presets.lua` | окно пресетов (UIManager): плитка пресетов на ui:Tree (3 колонки, своя прокрутка), узоры, свои пресеты с превью (`ExportCurrentFrameAsStill`), синхронизация списка в шаблоне |
| `crt_pro_data.lua` | данные для окна: `python3 gen_data.py build_crt_pro_2.py` после правок генератора |
| `CRT Pro v2.dctl` | упрощённая версия для страницы Color (ASCII-подписи, без времени/размытия) |
| `icons/` | превью пресетов — `python3 render_previews.py` (ядро через gcc на CPU, сцена `store_assets/scene.png` — временное фото (огонь)); также пишет cover_bg.png и иконку эффекта. Узоры pattern_*.png — старые |
| `make_release.py` | чистый пакет: payload + установщики macOS/Windows/Linux + README/LICENSE; `dist/Для магазина/` (обложка из `store_assets/`, сетка пресетов, описание) |
| публичные пути | `Effects/STORYVERSE/CRT/`, `Scripts/Comp/crt-pro/`, `LUT/STORYVERSE/` (make_release.py подменяет пути исходников v2) |
| `validate_crt_pro.lua` | валидатор (запускается через fuscript на Mac при `--install`) |

Проверки без Resolve: `luac5.1 -p` для Lua/fuse; ядро компилировать gcc с заглушками макросов.

## VHS Pro (`davinci-plugins/vhs-pro/`) — та же система
`python3 build_vhs_pro.py` (генератор; берёт помощники из crt-2.0/build_crt_pro_2.py) →
`python3 render_previews.py` (превью: ядро через gcc на CPU) → `python3 make_release.py` →
`dist/VHS Pro.zip` + `dist/VHS Pro Demo.zip` (3 пресета, ChromaShift/Snow/LineJitter, Text+ надпись, нода VHSCoreDemo).
Ядро `vhs_core_template.fuse` (1 проход): камера с рук (Lua считает camX/camY/camR/camS), трекинг, полоса головок,
залом, пауза/перемотка, размытие Y/IQ по строке, цвет, снег/выпадения, OSD (шрифт `font.inc`, строки упакованы в T0..T17).
Сцена превью/обложки — `store_assets/scene.png` (кадр клипа заказчика). Обложки обоих эффектов — сдержанный стиль: кадр, затемнение снизу, заголовок слева, STORYVERSE справа сверху.
Окно пресетов `VHS Presets.lua` (копия окна CRT: вместо узоров — кнопки режима магнитофона и быстрые тумблеры), данные `vhs_pro_data.lua` пишет build_vhs_pro.py.
Пути: `Effects/STORYVERSE/VHS/`, Fuses/VHSCore.fuse, `Scripts/Comp/vhs-pro/`. В демо окна нет.

## Flow Pro (`davinci-plugins/flow-pro/`) — В РАЗРАБОТКЕ (папка Claude)
Flow edit одной нодой по видео-гайду (методичка: `flow-pro/Методичка — Flow Edit (по видео).txt`).
`python3 build_flow_pro.py --dev-zip` → `dist-dev/Flow Pro (Claude).zip` (установщик в Effects/Claude/FLOW, без инструкций);
`python3 render_previews.py` — превью: Lua-часть FlowCore.fuse через lua5.1 + ядро через gcc, график кривой поверх.
Цепочка: InRouter → [OpticalFlow → TimeStretcher(Flow)] → Dissolve-переключатель (Quality=2) → FlowCore.fuse → SoftGlow.
Кривая времени — одна формула `CURVE_LUA` (Fuse и выражение Source Time TimeStretcher), `curve_py` — её копия для иконок.
FlowCore берёт 2–4 кадра через InImage:GetSource (ремап), камера/тряска/слайд-смаз/затемнение считаются в Lua.
Не проверено в Resolve: имена входов TimeStretcher (InterpolationMode) и `comp.RenderStart/End` в выражении.
Релиза (STORYVERSE, демо, make_release) пока нет — делать по образцу vhs-pro, когда заказчик скажет «публикуем».

## Папки в Resolve: работа vs публикация (правило заказчика)
- В разработке эффект ставится в Effects → **Claude** → <КОД> (наша рабочая папка; там же другие рабочие эффекты — не удалять).
- В **STORYVERSE** → <КОД> эффект попадает ТОЛЬКО из релизного архива (make_release.py / установщик покупателя).
- Новый набор: сначала рабочая сборка в Claude/<КОД>, релиз — через make_release.py с путями STORYVERSE.

## Единый стиль — `davinci-plugins/STYLE.md` + `storyverse_style.py`
Обложки, иконки библиотеки, листы пресетов, шапки окон — только через storyverse_style.py.
Окна пресетов — палитра DaVinci (серый) + красный акцент: `SV.recolor_window()` / `WINDOW_PALETTE`; фиолетовый/бирюзовый больше не использовать.
⚠ Фото в store_assets/scene.png у CRT (огонь) и VHS (клип) — ВРЕМЕННЫЕ, заказчик пришлёт финальные; таблица замены в STYLE.md.
Установщики и «Инструкция по установке.html» — только через storyverse_install.py (без пароля; DCTL по вопросу).
Свои пресеты заказчика хранятся только у него (Fusion/<КОД> Pro User Presets), в архивы не попадают (SHARE_MODE).

## Архив
- `crt-pro-v1/` — стабильная CRT Pro 1.0, НЕ МЕНЯТЬ.
- `fuse-uimanager-proto/`, `ofx-proto/` — ранние прототипы.

## Факты о Resolve (проверено у заказчика)
- Точка в имени файла эффекта скрывает его из библиотеки → «CRT Pro v2», не «2.0».
- Вкладка «Controls/Управление» есть всегда → главная вкладка = `Controls`; параметры привязывать к вкладке через `ICS_ControlPage`.
- Переключение `.Hidden` по клику и ScrollArea в UIManager не работают; каждое нажатие кнопки = отдельный запуск скрипта.
- DCTL на Mac — в системной `/Library/.../LUT` (нужен sudo).
- Ядро: ~1 мс/проход на 1080p (замер заказчика).
