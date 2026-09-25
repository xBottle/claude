#!/usr/bin/env python3
"""Экспортирует SECTIONS/PRESETS/PRESET_NAMES из build_crt_pro.py в Lua-таблицу,
чтобы плавающая панель (CRT Pro Panel.lua) не дублировала эти данные руками
и не могла разойтись с реальной нодой.

Запуск: python3 gen_data.py <путь к build_crt_pro.py> [--out crt_pro_data.lua]
"""
import importlib.util
import os
import sys

def load_module(path):
    spec = importlib.util.spec_from_file_location("build_crt_pro", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def lstr(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'

def lnum(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    return repr(float(v))

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "build_crt_pro.py")
    out = os.path.join(os.path.dirname(__file__), "crt_pro_data.lua")
    m = load_module(src)

    lines = ["-- Автосгенерировано gen_data.py из build_crt_pro.py — не редактировать руками.",
             "return {"]

    lines.append("  SECTIONS = {")
    for sec_id, title, open_by_default, items in m.SECTIONS:
        lines.append(f"    {{ id = {lstr(sec_id)}, title = {lstr(title)}, open = {lnum(open_by_default)}, controls = {{")
        for c in items:
            parts = [f"id = {lstr(c.id)}", f"kind = {lstr(c.kind)}", f"name = {lstr(c.name)}"]
            if c.kind == "slider":
                parts += [f"default = {lnum(c.default)}", f"lo = {lnum(c.lo)}", f"hi = {lnum(c.hi)}",
                          f"amin = {lnum(c.amin) if c.amin is not None else 'nil'}",
                          f"amax = {lnum(c.amax) if c.amax is not None else 'nil'}",
                          f"integer = {lnum(c.integer)}"]
            elif c.kind == "check":
                parts += [f"default = {lnum(c.default)}"]
            elif c.kind == "combo":
                opts = ", ".join(lstr(o) for o in c.options)
                parts += [f"default = {lnum(c.default)}", f"options = {{ {opts} }}"]
            elif c.kind == "color":
                r, g, b = c.rgb
                parts += [f"rgb = {{ {lnum(r)}, {lnum(g)}, {lnum(b)} }}"]
            elif c.kind == "button":
                parts += [f"action = {lstr(c.action)}"]
            lines.append("      { " + ", ".join(parts) + " },")
        lines.append("    } },")
    lines.append("  },")

    lines.append("  PRESET_NAMES = { " + ", ".join(lstr(n) for n in m.PRESET_NAMES) + " },")

    lines.append("  DEFAULTS = { " + ", ".join(f"{k} = {lnum(v)}" for k, v in m.DEFAULTS.items()) + " },")

    lines.append("  PRESETS = {")
    for i, p in m.PRESETS.items():
        body = ", ".join(f"{k} = {lnum(v)}" for k, v in p.items())
        lines.append(f"    [{i}] = {{ {body} }},")
    lines.append("  },")

    lines.append("}")

    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Записано: {out}")

if __name__ == "__main__":
    main()
