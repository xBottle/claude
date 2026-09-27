"""Единые установщики и инструкция по установке для всех наборов STORYVERSE.

spec = {
  "name": "CRT Pro",                    # имя эффекта в библиотеке
  "code": "CRT",                        # подпапка в Effects/STORYVERSE/
  "scripts": "crt-pro" | None,          # папка окна пресетов в Scripts/Comp (None — окна нет)
  "dctl": True/False,                   # есть ли версия для страницы Color (DCTL)
  "demo": True/False,
}
Правила (см. STYLE.md):
- пароль НЕ нужен для основной установки; DCTL — только по согласию (нужен пароль Mac);
- перед установкой — одно подтверждение Enter, в конце — понятное «Готово»;
- снимаем «карантин» macOS с установленных файлов (xattr), чтобы Resolve их не блокировал.
"""

FU_MAC = "$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion"
FU_LIN = "$HOME/.local/share/DaVinciResolve/Fusion"
LUT_MAC = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/STORYVERSE"
LUT_LIN = "/opt/resolve/LUT/STORYVERSE"


def _items(s):
    out = [("Effect", f"Templates/Edit/Effects/STORYVERSE/{s['code']}", "эффект"),
           ("Fuses", "Fuses", "ядро (GPU)")]
    if s.get("scripts"):
        out.append(("Presets", f"Scripts/Comp/{s['scripts']}", "окно пресетов"))
    return out


def mac(s):
    L = ["#!/bin/bash", f"# {s['name']} — установка для macOS", "clear",
         f'echo "  {s["name"].upper()}  ·  by STORYVERSE"', 'echo "  ------------------------------------"',
         f'echo "  Установка эффекта в DaVinci Resolve."', 'echo',
         'if pgrep -xq "Resolve"; then echo "  ! DaVinci Resolve открыт — после установки его нужно будет перезапустить."; echo; fi',
         'echo "  Устанавливая, вы соглашаетесь с условиями лицензии (LICENSE.txt рядом с установщиком)."', 'echo',
         'read -r -p "  Нажмите Enter, чтобы согласиться и установить (или закройте окно, чтобы отменить)... " _',
         'cd "$(dirname "$0")/payload" || { echo "  Не найдена папка payload рядом с установщиком."; read -r _; exit 1; }',
         f'FU="{FU_MAC}"']
    for src, dst, label in _items(s):
        L += [f'mkdir -p "$FU/{dst}" && cp -Rf {src}/. "$FU/{dst}/" && xattr -dr com.apple.quarantine "$FU/{dst}" 2>/dev/null',
              f'echo "  ✓ {label}"']
    if s.get("dctl"):
        L += ['echo',
              'echo "  Версия для страницы Color (DCTL, только Resolve Studio) ставится в системную папку."',
              'read -r -p "  Установить её? Потребуется пароль от Mac. [y — да / Enter — пропустить] " a',
              'if [[ "$a" =~ ^[YyДдНн] ]]; then',
              f'  sudo mkdir -p "{LUT_MAC}" && sudo cp -f Color/* "{LUT_MAC}/" && echo "  ✓ DCTL для страницы Color"',
              'else echo "  – DCTL пропущен (можно поставить позже, запустив установщик ещё раз)"; fi']
    L += ['echo', 'echo "  Готово! Полностью закройте DaVinci Resolve (Cmd+Q) и откройте снова."',
          f'echo "  Эффект: Effects → STORYVERSE → {s["code"]} → «{s["name"]}»"', 'echo',
          'read -r -p "  Нажмите Enter, чтобы закрыть окно. " _', ""]
    return "\n".join(L)


def win(s):
    L = ["@echo off", "chcp 65001 >nul", f"title {s['name']} — установка", "cls",
         f"echo   {s['name'].upper()}  ·  by STORYVERSE", "echo   ------------------------------------",
         "echo   Установка эффекта в DaVinci Resolve.", "echo.",
         'tasklist /FI "IMAGENAME eq Resolve.exe" 2>nul | find /I "Resolve.exe" >nul && echo   ! DaVinci Resolve открыт — после установки его нужно будет перезапустить.',
         "echo   Устанавливая, вы соглашаетесь с условиями лицензии (LICENSE.txt рядом с установщиком).", "echo.",
         "set /p _=  Нажмите Enter, чтобы согласиться и установить (или закройте окно, чтобы отменить)... ",
         'cd /d "%~dp0payload" || (echo   Не найдена папка payload. & pause & exit /b 1)',
         'set "FU=%APPDATA%\\Blackmagic Design\\DaVinci Resolve\\Support\\Fusion"']
    for src, dst, label in _items(s):
        d = dst.replace("/", "\\")
        L += [f'mkdir "%FU%\\{d}" 2>nul', f'xcopy /Y /Q /E /I "{src}\\*" "%FU%\\{d}\\" >nul && echo   + {label}']
    if s.get("dctl"):
        L += ["echo.", "echo   Версия для страницы Color (DCTL, только Resolve Studio) ставится в общую папку.",
              "echo   Если появится ошибка доступа — запустите установщик правой кнопкой → «Запуск от имени администратора».",
              'set "a="', "set /p a=  Установить её? [y — да / Enter — пропустить] ",
              'if /I "%a%"=="y" (',
              '  mkdir "%ProgramData%\\Blackmagic Design\\DaVinci Resolve\\Support\\LUT\\STORYVERSE" 2>nul',
              '  xcopy /Y /Q "Color\\*" "%ProgramData%\\Blackmagic Design\\DaVinci Resolve\\Support\\LUT\\STORYVERSE\\" >nul && echo   + DCTL для страницы Color',
              ") else echo   - DCTL пропущен"]
    L += ["echo.", "echo   Готово! Полностью закройте DaVinci Resolve и откройте снова.",
          f"echo   Эффект: Effects → STORYVERSE → {s['code']} → «{s['name']}»", "echo.", "pause", ""]
    return "\r\n".join(L)


def linux(s):
    L = ["#!/bin/bash", f"# {s['name']} — установка для Linux: bash install-linux.sh",
         f'echo "{s["name"].upper()} · by STORYVERSE"',
         'echo "Устанавливая, вы соглашаетесь с условиями лицензии (LICENSE.txt)."',
         'read -r -p "Нажмите Enter, чтобы согласиться и установить... " _',
         'cd "$(dirname "$0")/payload" || exit 1', f'FU="{FU_LIN}"']
    for src, dst, label in _items(s):
        L += [f'mkdir -p "$FU/{dst}" && cp -rf {src}/. "$FU/{dst}/" && echo "✓ {label}"']
    if s.get("dctl"):
        L += ['if [ -d /opt/resolve/LUT ]; then',
              '  read -r -p "Установить DCTL для страницы Color (нужен sudo)? [y/Enter] " a',
              f'  [[ "$a" =~ ^[Yy] ]] && sudo mkdir -p {LUT_LIN} && sudo cp -f Color/* {LUT_LIN}/ && echo "✓ DCTL"',
              'fi']
    L += ['echo "Готово! Перезапустите DaVinci Resolve."', ""]
    return "\n".join(L)


CONTACT = "__CONTACT__"   # почта/контакт поддержки — подставить, когда заказчик пришлёт
YEAR = "2026"
RED = "#C9352B"            # фирменный красный STORYVERSE (насыщенный, не яркий)

ICON = {  # простые монохромные значки систем (SVG, цвет = currentColor)
    "macOS": '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M16.4 12.6c0-2.5 2-3.7 2.1-3.8-1.2-1.7-3-1.9-3.6-2-1.5-.2-3 .9-3.8.9-.8 0-2-.9-3.3-.9-1.7 0-3.3 1-4.1 2.5-1.8 3.1-.5 7.6 1.3 10.1.8 1.2 1.8 2.6 3.1 2.5 1.3-.1 1.7-.8 3.2-.8s1.9.8 3.2.8c1.3 0 2.2-1.2 3-2.4.9-1.4 1.3-2.7 1.3-2.8-.1 0-2.4-.9-2.4-4.1zM14 5.2c.7-.8 1.1-2 1-3.2-1 .1-2.2.7-2.9 1.5-.6.7-1.2 1.9-1 3.1 1.1.1 2.2-.6 2.9-1.4z"/></svg>',
    "Windows": '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M2 4.5l8.2-1.1v7.9H2zm9.2-1.3L22 1.7v9.6H11.2zM2 12.3h8.2v7.9L2 19.1zm9.2 0H22V22l-10.8-1.5z"/></svg>',
    "Linux": '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M12 2c-2.2 0-3.6 1.8-3.6 4.4 0 1.3.3 2.2-.4 3.4-.8 1.4-2.8 3.6-2.8 6.3 0 .8.2 1.5.5 2.1-.7.3-1.7.6-1.7 1.5 0 1 1.6 1.2 3.2 1.6 1.2.3 2 .7 2.6.7.8 0 1.2-.5 1.5-.9h1.4c.3.4.7.9 1.5.9.6 0 1.4-.4 2.6-.7 1.6-.4 3.2-.6 3.2-1.6 0-.9-1-1.2-1.7-1.5.3-.6.5-1.3.5-2.1 0-2.7-2-4.9-2.8-6.3-.7-1.2-.4-2.1-.4-3.4C15.6 3.8 14.2 2 12 2zm-1.4 4c.5 0 .8.5.8 1.1s-.3 1.1-.8 1.1-.8-.5-.8-1.1.4-1.1.8-1.1zm2.8 0c.5 0 .8.5.8 1.1s-.3 1.1-.8 1.1-.8-.5-.8-1.1.3-1.1.8-1.1zM12 9.2c.8 0 1.9.6 1.9 1s-1.1.9-1.9.9-1.9-.5-1.9-.9 1.1-1 1.9-1z"/></svg>',
}

GUIDE_CSS = """
:root{color-scheme:dark;--red:#C9352B;--bg:#1b1b1a;--card:#252524;--line:#363634}*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:#ebebe8;font:16px/1.6 -apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:760px;margin:0 auto;padding:48px 20px 40px}
.brand{letter-spacing:.35em;color:var(--red);font-size:12px;font-weight:600}
h1{font-size:40px;margin:6px 0 4px}h2{margin:40px 0 10px;font-size:22px;padding-left:12px;border-left:3px solid var(--red)}
.sub{color:#a8a8a3;margin:0 0 24px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 22px;margin:14px 0}
ol{padding-left:22px}li{margin:6px 0}li::marker{color:var(--red);font-weight:600}
code{background:#30302e;padding:2px 6px;border-radius:6px;color:#f2cfc9}
.os{display:inline-flex;align-items:center;gap:8px;color:#fff;font-weight:600;font-size:15px;margin-bottom:4px}
.os svg{color:var(--red)}
.warn{border-color:#6a2c26;background:#2a1d1b}
dt{font-weight:600;margin-top:14px}dd{margin:4px 0 0 0;color:#cacac5}
.path{font-family:ui-monospace,Menlo,monospace;font-size:13px;color:#e8776c;word-break:break-all}
a{color:#e8776c}
footer{max-width:760px;margin:0 auto;padding:22px 20px 48px;border-top:1px solid var(--line);color:#8f8f8a;font-size:13px}
footer b{color:#e8e8ea}
"""


def guide_html(s):
    n, code = s["name"], s["code"]
    items = _items(s)
    fuse = f"{code}Core{'Demo' if s.get('demo') else ''}.fuse"
    rows = "".join(f"<li>{lbl}: <span class='path'>…/Fusion/{dst}/" + (fuse if src == "Fuses" else "") + "</span></li>"
                   for src, dst, lbl in items)
    dctl_mac = ("<li>Если установщик спросит про <b>DCTL для страницы Color</b> — это по желанию (нужна Resolve Studio). "
                "Нажмите <code>y</code> и введите пароль от Mac (символы при вводе не видны — это нормально), "
                "или просто <code>Enter</code>, чтобы пропустить.</li>") if s.get("dctl") else ""
    window = (f"<li>Вкладка «Управление» → кнопка <b>«▣ ОКНО ПРЕСЕТОВ»</b>.</li>") if s.get("scripts") else ""
    color = ("<li>Страница <b>Color</b> (только Resolve Studio, если при установке выбрали DCTL): выберите ноду → "
             "Effects → <b>DCTL</b> (группа ResolveFX) → перетащите на ноду → в его настройках, в списке DCTL, "
             f"выберите <b>STORYVERSE → {n}</b>. Не ставьте эффект одновременно на Edit и на Color — появится муар.</li>"
             ) if s.get("dctl") else ""
    demo = ("<div class='card warn'><b>Это демо-версия.</b> Внизу кадра надпись, часть пресетов и настроек недоступна. "
            "Полная версия ставится так же и не конфликтует с демо.</div>") if s.get("demo") else ""
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{n} — установка</title>
<style>{GUIDE_CSS}</style></head><body><main>
<div class="brand">S T O R Y V E R S E</div>
<h1>{n}</h1><p class="sub">Инструкция по установке в DaVinci Resolve 18+ · около 1 минуты</p>
{demo}
<div class="card"><b>Лицензия.</b> Устанавливая и используя {n}, вы соглашаетесь с условиями лицензионного соглашения —
файл <code>LICENSE.txt</code> в архиве.</div>
<h2>Установка</h2>
<div class="card"><span class="os">{ICON["macOS"]}macOS</span><ol>
<li>Распакуйте архив (двойной клик по .zip).</li>
<li>Откройте <b>Терминал</b> (Cmd+Пробел → «Терминал» → Enter).</li>
<li>Напечатайте <code>bash</code> и <b>пробел</b>, затем <b>перетащите мышкой</b> файл <code>Установить (macOS).command</code> в окно Терминала и нажмите <code>Enter</code>.
<br><small>Так установщик запускается всегда: macOS не блокирует его, как при двойном клике (файл не из App Store и не подписан Apple).</small></li>
<li>Нажмите <code>Enter</code> ещё раз — начнётся установка.</li>
{dctl_mac}
<li>Когда появится «Готово!», полностью закройте Resolve (<code>Cmd+Q</code>) и откройте снова.</li></ol></div>
<div class="card"><span class="os">{ICON["Windows"]}Windows</span><ol>
<li>Распакуйте архив (правой кнопкой → «Извлечь всё»). Из самого .zip не запускайте.</li>
<li>Двойной клик <code>Установить (Windows).bat</code>. Если Windows покажет «Система Windows защитила ваш компьютер» — «Подробнее» → «Выполнить в любом случае».</li>
<li>Нажмите <code>Enter</code>{" (DCTL — по желанию: <code>y</code>)" if s.get("dctl") else ""}. Затем перезапустите Resolve.</li></ol></div>
<div class="card"><span class="os">{ICON["Linux"]}Linux</span><ol><li><code>bash install-linux.sh</code> → <code>Enter</code> → перезапустите Resolve.</li></ol></div>

<h2>Где найти</h2>
<div class="card"><ol>
<li>Страница <b>Edit</b> или <b>Cut</b> → Effects → <b>STORYVERSE → {code}</b> → перетащите «{n}» на клип.</li>
<li>Fusion: <code>Shift+Пробел</code> → «{code} Core{" Demo" if s.get("demo") else ""}».</li>
{window}
{color}
</ol></div>

<h2>Если что-то не так</h2>
<div class="card"><dl>
<dt>macOS пишет «не удалось проверить разработчика», «файл повреждён» или не открывает по двойному клику</dt>
<dd>Это защита macOS от неподписанных файлов (в macOS 15 правый клик → «Открыть» больше не помогает).
Запустите через Терминал, как в шаге 3: <code>bash</code> + пробел + перетащить файл + Enter.
Либо: двойной клик → «Готово» → Системные настройки → Конфиденциальность и безопасность → внизу «Всё равно открыть» → ввести пароль.</dd>
<dt>Эффекта нет в списке</dt><dd>Полностью закройте Resolve (Cmd+Q / через «Файл → Выход») и откройте снова — эффекты подгружаются только при запуске.</dd>
<dt>«Unknown tool» или серый/чёрный кадр</dt><dd>Ядро не загрузилось: перезапустите Resolve. Если не помогло — запустите установщик ещё раз.</dd>
<dt>Нет новых кнопок или пресетов после обновления</dt><dd>Удалите эффект с клипа и перетащите заново — эффект, уже стоящий на клипе, не обновляется.</dd>
{"<dt>Кнопка «Окно пресетов» ничего не открывает</dt><dd>Запустите установщик ещё раз (окно ставится в <span class='path'>Fusion/Scripts/Comp/" + s['scripts'] + "/</span>) и перезапустите Resolve.</dd>" if s.get("scripts") else ""}
{"<dt>Нет в списке DCTL на странице Color</dt><dd>DCTL работает только в Resolve Studio и ставится по желанию — запустите установщик и нажмите <code>y</code> на вопросе про DCTL.</dd>" if s.get("dctl") else ""}
<dt>Как удалить</dt><dd>Удалите папки:<ul>{rows}</ul></dd>
<dt>Ничего не помогло</dt><dd>Напишите нам: <a href="mailto:{CONTACT}">{CONTACT}</a> — приложите скриншот и версию Resolve и системы.</dd>
</dl></div>
</main>
<footer><b>© {YEAR} STORYVERSE.</b> Все права защищены. · Поддержка: <a href="mailto:{CONTACT}">{CONTACT}</a></footer></body></html>
"""


def readme(s):
    """README.txt — единый формат для всех наборов. Поля spec: tagline, usage[], demo_note[]."""
    n, code = s["name"], s["code"]
    L = [f"{n.upper()}  ·  by STORYVERSE", s["tagline"], "=" * 64, "",
         "УСТАНОВКА  (подробно, с решением проблем — «Инструкция по установке.html»)",
         "  macOS   — Терминал → напечатайте «bash » (с пробелом) → перетащите в окно",
         "            «Установить (macOS).command» → Enter → Enter. Пароль не нужен.",
         "            (двойной клик macOS может заблокировать — файл не подписан Apple)",
         "  Windows — распакуйте архив → «Установить (Windows).bat» → Enter.",
         "  Linux   — bash install-linux.sh → Enter.",
         "  После установки полностью перезапустите DaVinci Resolve.", "",
         "ГДЕ НАЙТИ",
         f"  Edit / Cut : Effects → STORYVERSE → {code} → «{n}»",
         f"  Fusion     : Shift+Пробел → «{code} Core{' Demo' if s.get('demo') else ''}»"]
    if s.get("dctl"):
        L.append(f"  Color      : нода → Effects → DCTL → в списке DCTL «STORYVERSE → {n}» (Resolve Studio)")
    usage = (["Вкладка «Управление»: выберите пресет → «Применить пресет», ниже — три настройки."]
             if s.get("demo") else s["usage"])
    L += ["", "КАК ПОЛЬЗОВАТЬСЯ"] + [f"  • {u}" for u in usage]
    if s.get("demo"):
        L += ["", "ДЕМО-ВЕРСИЯ"] + [f"  {d}" for d in s["demo_note"]]
    L += ["", "ЛИЦЕНЗИЯ",
          "  Устанавливая и используя эффект, вы соглашаетесь с условиями LICENSE.txt.", "",
          f"© {YEAR} STORYVERSE. Все права защищены. · Поддержка: {CONTACT}", ""]
    return "\n".join(L)


def license_text(s):
    """LICENSE.txt — единое лицензионное соглашение (EULA) для всех наборов."""
    n = s["name"]
    demo = s.get("demo")
    return f"""ЛИЦЕНЗИОННОЕ СОГЛАШЕНИЕ — {n.upper()}
Правообладатель: STORYVERSE. © {YEAR} STORYVERSE. Все права защищены.

Устанавливая, копируя или используя {n} (далее — «Продукт»), вы подтверждаете,
что прочитали это соглашение и принимаете его условия. Если вы не согласны —
не устанавливайте и не используйте Продукт.

1. ЛИЦЕНЗИЯ
   {"Демо-версия предоставляется бесплатно только для ознакомления с Продуктом." if demo else
    "Вам предоставляется простая (неисключительная), непередаваемая лицензия для одного"}
   {"Использование результатов демо-версии в коммерческих проектах не допускается." if demo else
    "пользователя на установку Продукта на его компьютеры и использование в личных"}
   {"" if demo else "и коммерческих проектах (видео, клипы, реклама, соцсети) без ограничения тиража."}

2. ЗАПРЕЩЕНО
   • продавать, сдавать в аренду, публиковать, раздавать или иным образом передавать
     файлы Продукта (в том числе пресеты, ядро, скрипты) третьим лицам — целиком
     или частями, в исходном или изменённом виде;
   • выдавать Продукт или его части за свою разработку, включать их в другие
     продаваемые продукты, шаблоны и наборы;
   • удалять или изменять упоминания правообладателя{", обходить ограничения и надпись демо-версии" if demo else ""}.

3. РЕЗУЛЬТАТЫ
   Видео и изображения, созданные с помощью {"полной версии " if demo else ""}Продукта, принадлежат вам.

4. БЕЗ ГАРАНТИЙ
   Продукт предоставляется «как есть». Правообладатель не гарантирует работу
   с любыми версиями DaVinci Resolve, оборудованием и системами и не отвечает
   за прямые или косвенные убытки, потерю данных или сроков, связанные
   с использованием Продукта, в пределах, допускаемых законом.

5. ПРЕКРАЩЕНИЕ
   При нарушении условий лицензия прекращается автоматически; вы обязаны
   удалить все копии Продукта.

6. ПРОЧЕЕ
   DaVinci Resolve — товарный знак Blackmagic Design Pty. Ltd.; Продукт не является
   продуктом Blackmagic Design и не одобрен ею.
   Вопросы и поддержка: {CONTACT}
"""
