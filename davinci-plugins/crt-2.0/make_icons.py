#!/usr/bin/env python3
"""Генерирует иконки для панели CRT Pro: 10 узоров пикселей + 10 пресетов.

Не рендерит настоящий кадр (для этого нужен сам Resolve на Mac) — рисует
упрощённые, но узнаваемые превью средствами Pillow. Результат кладётся в
./icons/pattern_0..9.png и ./icons/preset_0..9.png, скрипт CRT Pro Panel.lua
подключает их по относительному пути от себя.

Запуск: python3 make_icons.py
"""
import os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "icons")
os.makedirs(OUT, exist_ok=True)

W, H = 64, 36  # размер иконки в панели

# ---------------------------------------------------------------- узоры пикселей
# Каждый узор рисуется на маленькой сетке (в духе pattern_tiles() из
# build_crt_pro.py), потом апскейлится без сглаживания — тот же "пиксельный"
# вид, что и в реальном эффекте.

def tile_straight():
    im = Image.new("RGB", (6, 3), "black")
    for x in range(0, 6, 3):
        im.putpixel((x, 0), (255, 0, 0))
        im.putpixel((x + 1, 0), (0, 255, 0))
        im.putpixel((x + 2, 0), (0, 0, 255))
    return im

def tile_shifted():
    im = Image.new("RGB", (6, 4), "black")
    for x in range(0, 6, 3):
        im.putpixel((x, 0), (255, 0, 0)); im.putpixel((x + 1, 0), (0, 255, 0)); im.putpixel((x + 2, 0), (0, 0, 255))
    for x in range(0, 6, 3):
        im.putpixel(((x + 1) % 6, 2), (255, 0, 0)); im.putpixel(((x + 2) % 6, 2), (0, 255, 0)); im.putpixel((x % 6, 2), (0, 0, 255))
    return im

def tile_aperture():
    im = Image.new("RGB", (6, 2), "black")
    for x in range(0, 6, 3):
        im.putpixel((x, 0), (255, 0, 0)); im.putpixel((x + 1, 0), (0, 255, 0)); im.putpixel((x + 2, 0), (0, 0, 255))
        im.putpixel((x, 1), (255, 0, 0)); im.putpixel((x + 1, 1), (0, 255, 0)); im.putpixel((x + 2, 1), (0, 0, 255))
    return im

def tile_slot():
    im = Image.new("RGB", (6, 6), "black")
    for x in range(0, 6, 3):
        for y in (0, 1, 2):
            im.putpixel((x, y), (255, 0, 0)); im.putpixel((x + 1, y), (0, 255, 0)); im.putpixel((x + 2, y), (0, 0, 255))
        for y in (3, 4, 5):
            im.putpixel(((x + 1) % 6, y), (255, 0, 0)); im.putpixel(((x + 2) % 6, y), (0, 255, 0)); im.putpixel((x % 6, y), (0, 0, 255))
    return im

def tile_shadow():
    im = Image.new("RGB", (6, 4), "black")
    coords = [(0, 2, (255, 0, 0)), (2, 2, (0, 255, 0)), (4, 2, (0, 0, 255)),
              (3, 0, (255, 0, 0)), (5, 0, (0, 255, 0)), (1, 0, (0, 0, 255))]
    for x, y, c in coords:
        im.putpixel((x, y), c)
    return im

def tile_lcd():
    im = Image.new("RGB", (6, 3), (30, 30, 30))
    for x in range(0, 6, 3):
        im.putpixel((x, 1), (255, 60, 60)); im.putpixel((x + 1, 1), (60, 255, 60)); im.putpixel((x + 2, 1), (60, 60, 255))
    return im

def tile_led():
    im = Image.new("RGB", (6, 4), "black")
    for x in range(0, 6, 3):
        im.putpixel((x, 1), (255, 0, 0)); im.putpixel((x, 2), (255, 0, 0))
        im.putpixel((x + 1, 1), (0, 255, 0)); im.putpixel((x + 1, 2), (0, 255, 0))
        im.putpixel((x + 2, 1), (0, 0, 255)); im.putpixel((x + 2, 2), (0, 0, 255))
    return im

def tile_dots():
    im = Image.new("RGB", (4, 4), "black")
    im.putpixel((1, 1), (230, 230, 230)); im.putpixel((2, 1), (230, 230, 230))
    im.putpixel((1, 2), (230, 230, 230)); im.putpixel((2, 2), (230, 230, 230))
    return im

def tile_grid():
    im = Image.new("RGB", (4, 4), "black")
    for x in range(4):
        for y in range(4):
            if x in (0, 3) or y in (0, 3):
                im.putpixel((x, y), (210, 210, 210))
    return im

def tile_rows():
    im = Image.new("RGB", (4, 4), "black")
    for x in range(4):
        im.putpixel((x, 1), (220, 220, 220))
    return im

PATTERNS = [tile_straight, tile_shifted, tile_aperture, tile_slot, tile_shadow,
            tile_lcd, tile_led, tile_dots, tile_grid, tile_rows]

for i, fn in enumerate(PATTERNS):
    tile = fn()
    icon = tile.resize((W, H), Image.NEAREST)
    icon.save(os.path.join(OUT, f"pattern_{i}.png"))

# ---------------------------------------------------------------- пресеты
# Настоящего кадра у нас нет (нужен рендер на Mac), поэтому рисуем цветовую
# карточку по характерному цвету пресета — люминофор/оттенок трубки из
# самого build_crt_pro.py, плюс лёгкие "строки развёртки" для узнаваемости.

PRESET_COLORS = [
    (90, 200, 255),     # 0 по умолчанию — нейтрально-голубой
    (255, 210, 140),    # 1 классический ТВ — тёплый
    (255, 140, 60),     # 2 аркадный автомат — оранжевый
    (60, 255, 110),     # 3 зелёный терминал
    (255, 190, 60),     # 4 янтарный монитор
    (200, 140, 255),    # 5 VHS-мечта — лиловый
    (150, 150, 160),    # 6 сломанный телевизор — серый шум
    (255, 170, 130),    # 7 снято на камеру
    (255, 225, 190),    # 8 мягкий ретро — светлый тёплый
    (255, 60, 220),     # 9 киберпанк — магента
]

def preset_icon(rgb):
    im = Image.new("RGB", (W, H), (10, 10, 12))
    d = ImageDraw.Draw(im)
    r, g, b = rgb
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(r * (1 - t * 0.6)), int(g * (1 - t * 0.6)), int(b * (1 - t * 0.6))))
    for y in range(0, H, 3):
        d.line([(0, y), (W, y)], fill=(0, 0, 0), width=1)
    d.rectangle([0, 0, W - 1, H - 1], outline=(0, 0, 0))
    return im

for i, rgb in enumerate(PRESET_COLORS):
    preset_icon(rgb).save(os.path.join(OUT, f"preset_{i}.png"))

print(f"Готово: {len(PATTERNS)} иконок узоров + {len(PRESET_COLORS)} иконок пресетов -> {OUT}")
