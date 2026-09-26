# CRT Pro v2 — исходники

Сборка продаваемого пакета: `python3 make_release.py` →
- `dist/CRT Pro v2.zip` — архив для покупателя (payload + установщики macOS/Windows/Linux + README/LICENSE)
- `dist/Для магазина/` — обложка 1920×1080, сетка пресетов, узоры, текст описания

После правок генератора: `python3 gen_data.py build_crt_pro_2.py` (данные окна пресетов).
Подробности по файлам — в `/CLAUDE.md` в корне репозитория.
