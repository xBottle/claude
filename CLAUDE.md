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
| `icons/` | превью пресетов/узоров — рендер реального ядра на CPU (C-копия ядра, см. историю в git) |
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
Окно пресетов `VHS Presets.lua` (копия окна CRT: вместо узоров — кнопки режима магнитофона и быстрые тумблеры), данные `vhs_pro_data.lua` пишет build_vhs_pro.py.
Пути: `Effects/STORYVERSE/VHS/`, Fuses/VHSCore.fuse, `Scripts/Comp/vhs-pro/`. В демо окна нет.

## Отложенные правки (заказчик просил запомнить)
- В окна пресетов (CRT и VHS) добавить брендинг STORYVERSE (напр. «by STORYVERSE» в шапке/подвале) — сделать вместе, когда вернёмся к CRT.

## Архив
- `crt-pro-v1/` — стабильная CRT Pro 1.0, НЕ МЕНЯТЬ.
- `fuse-uimanager-proto/`, `ofx-proto/` — ранние прототипы.

## Факты о Resolve (проверено у заказчика)
- Точка в имени файла эффекта скрывает его из библиотеки → «CRT Pro v2», не «2.0».
- Вкладка «Controls/Управление» есть всегда → главная вкладка = `Controls`; параметры привязывать к вкладке через `ICS_ControlPage`.
- Переключение `.Hidden` по клику и ScrollArea в UIManager не работают; каждое нажатие кнопки = отдельный запуск скрипта.
- DCTL на Mac — в системной `/Library/.../LUT` (нужен sudo).
- Ядро: ~1 мс/проход на 1080p (замер заказчика).
