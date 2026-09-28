"""Единый стиль STORYVERSE для всех наборов (CRT Pro, VHS Pro, следующие).
Правила — в STYLE.md рядом. Любая обложка/иконка/лист пресетов делается ТОЛЬКО этими функциями.
"""
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BG = (14, 15, 20)          # фон листов и окон
INK = (245, 245, 248)      # основной текст
SUB = (205, 207, 215)      # подписи
DARK = (8, 8, 12)          # затемнение
BRAND = "S T O R Y V E R S E"


def _shade(size, top=0.35, strength=235):
    """Маска затемнения: снизу и слева сильнее (под заголовок)."""
    W, H = size
    m = Image.new("L", (W, H))
    p = m.load()
    for y in range(H):
        v = strength * max(0.0, (y / H - top) / (1 - top)) ** 1.4
        for x in range(W):
            p[x, y] = int(v * (1 - 0.35 * x / W))
    return m


def cover(frame, title, subtitle, brightness=1.0):
    """Обложка 1920x1080: кадр эффекта, затемнение снизу, название слева, STORYVERSE справа сверху."""
    W, H = 1920, 1080
    img = frame.convert("RGB").resize((W, H), Image.LANCZOS)
    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)
    img = Image.composite(Image.new("RGB", (W, H), DARK), img, _shade((W, H)))
    d = ImageDraw.Draw(img)
    d.text((W - 110, 96), BRAND, font=ImageFont.truetype(FONT_R, 26), fill=(200, 202, 210), anchor="ra")
    d.text((104, 770), title, font=ImageFont.truetype(FONT_B, 150), fill=INK, anchor="ls")
    d.text((110, 840), subtitle, font=ImageFont.truetype(FONT_R, 40), fill=SUB, anchor="ls")
    d.line([(110, 880), (230, 880)], fill=(255, 255, 255), width=3)
    return img


def library_icon(frame, code, demo=False, brightness=1.0):
    """Иконка в библиотеке эффектов Resolve 104x58: тот же кадр, что на обложке,
    затемнение снизу, код набора (CRT / VHS) слева внизу; у демо — метка DEMO справа сверху."""
    W, H = 104, 58
    big = frame.convert("RGB").resize((W * 4, H * 4), Image.LANCZOS)
    if brightness != 1.0:
        big = ImageEnhance.Brightness(big).enhance(brightness)
    big = Image.composite(Image.new("RGB", big.size, DARK), big, _shade(big.size, top=0.25, strength=215))
    d = ImageDraw.Draw(big)
    d.text((24, H * 4 - 22), code, font=ImageFont.truetype(FONT_B, 76), fill=INK, anchor="ls")
    if demo:
        d.rounded_rectangle([W * 4 - 176, 18, W * 4 - 18, 74], radius=12, fill=DARK, outline=INK, width=3)
        d.text((W * 4 - 97, 47), "DEMO", font=ImageFont.truetype(FONT_B, 34), fill=INK, anchor="mm")
    return big.resize((W, H), Image.LANCZOS)


def preset_sheet(thumbs, names, cols=3):
    """Лист пресетов для магазина: превью 320x180, подпись под каждым."""
    w, h = 320, 180
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w + (cols + 1) * 12, rows * (h + 34) + 12), BG)
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(FONT_R, 15)
    for i, (im, nm) in enumerate(zip(thumbs, names)):
        x, y = 12 + (i % cols) * (w + 12), 12 + (i // cols) * (h + 34)
        sheet.paste(im.convert("RGB").resize((w, h)), (x, y))
        d.text((x + 4, y + h + 8), nm, font=f, fill=(214, 216, 226))
    return sheet


def window_title(name, sub):
    """Шапка окна пресетов 330x64 (палитра DaVinci): название белым, красная черта-акцент, плашка PRESETS."""
    W, H = 330, 64
    im = Image.new("RGB", (W, H), (31, 31, 31))
    d = ImageDraw.Draw(im)
    d.text((10, 2), name, font=ImageFont.truetype(FONT_B, 34), fill=(236, 236, 234))
    d.rectangle([11, 44, 41, 46], fill=(201, 53, 43))
    d.rounded_rectangle([232, 12, 322, 36], radius=12, fill=(40, 40, 40), outline=(201, 53, 43), width=1)
    d.text((277, 24), "PRESETS", font=ImageFont.truetype(FONT_R, 11), fill=(226, 226, 224), anchor="mm")
    d.text((50, 50), sub, font=ImageFont.truetype(FONT_R, 11), fill=(120, 120, 118), anchor="lm")
    return im


# Палитра окон пресетов — как интерфейс DaVinci Resolve: нейтральный серый, красный STORYVERSE только акцентом.
WINDOW_PALETTE = {
    "#0e0f14": "#1f1f1f",  # фон окна
    "#15161c": "#282828",  # поле ввода
    "#2b2c36": "#3a3a3a",  # рамки полей и кнопок
    "#8b7bff": "#c9352b",  # фокус поля
    "#25262e": "#333333",  # рамки списка/узоров
    "#1b1c24": "#2c2c2c",  # наведение на строку
    "#221d3d": "#43231f",  # выделенная строка
    "#34353f": "#4a4a4a",  # полоса прокрутки
    "#101116": "#262626",  # фон кнопок-узоров
    "#22d3ee": "#c9352b",  # акцент: подписи разделов, выбранный узор
    "#0f2230": "#3a211e",  # фон включённой кнопки
    "#c9cad4": "#cfcfcd",  # текст быстрых кнопок
    "#17181f": "#2a2a2a",  # фон кнопок
    "#1e1f28": "#333333",  # наведение на кнопку
    "#9d8cff": "#d0584d",  # статус / акцентный текст
    "#e6e7ee": "#e2e2e0",  # основной текст
    "#5eead4": "#e06a5f",  # «Сохранить» — акцентные кнопки
    "#fb7185": "#b8b8b5",  # «Удалить» — спокойный серый
    "#d6d8e2": "#d4d4d2",  # текст строк списка
    "#4a4c58": "#6a6a68",  # подвал
}


def recolor_window(src):
    """Перекрашивает Lua-окно пресетов в палитру STORYVERSE/DaVinci."""
    for a, b in WINDOW_PALETTE.items():
        src = src.replace(a, b).replace(a.upper(), b)
    return src
