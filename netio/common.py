"""Shared helpers: config, paths, fonts with glyph fallback, drawing utilities, brand palette."""
from __future__ import annotations

import json
import math
import os
import random
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
CONTENT = ROOT / "content"
STATE_DIR = ROOT / "state"
OUT = ROOT / "out"

# ---------------------------------------------------------------- config
@lru_cache(maxsize=1)
def config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_json(path: Path, default=None):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)

# ---------------------------------------------------------------- palette
NAVY = (34, 30, 58)
INK = (34, 30, 56)
PINK = (231, 90, 138)
YEL = (255, 206, 64)
CREAM = (246, 241, 234)
WHITE = (255, 255, 255)
GREEN = (58, 170, 88)
GREY = (120, 114, 140)

SUBJECT_COLORS = {
    "Matematik": (52, 104, 214), "Geometri": (32, 150, 170), "Fizik": (238, 124, 52),
    "Kimya": (124, 86, 214), "Biyoloji": (214, 72, 128), "Türkçe": (58, 160, 86),
    "Edebiyat": (190, 70, 70), "Tarih": (176, 112, 60), "Coğrafya": (40, 140, 120),
    "Felsefe": (96, 96, 180),
}
def subject_color(subject: str):
    return SUBJECT_COLORS.get(subject, PINK)

def darker(c, k=0.6):
    return tuple(int(v * k) for v in c)

def lighter(c, k=0.5):
    return tuple(int(v + (255 - v) * k) for v in c)

# ---------------------------------------------------------------- fonts
FONT_FILES = {
    "display": ASSETS / "fonts" / "Poppins-Bold.ttf",
    "medium": ASSETS / "fonts" / "Poppins-Medium.ttf",
    "body": ASSETS / "fonts" / "Inter-SemiBold.otf",
    "bold": ASSETS / "fonts" / "Inter-Bold.otf",
    "black": ASSETS / "fonts" / "Inter-ExtraBold.otf",
    "fallback": ASSETS / "fonts" / "DejaVuSans-Bold.ttf",
}

@lru_cache(maxsize=None)
def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_FILES[kind]), size)

@lru_cache(maxsize=None)
def _cmap(kind: str) -> frozenset:
    tt = TTFont(str(FONT_FILES[kind]), lazy=True)
    return frozenset(tt.getBestCmap().keys())

def _runs(text: str, kind: str):
    """Split text into runs of (font_kind, substring) so missing glyphs use the fallback font."""
    cm = _cmap(kind)
    runs, cur, cur_kind = [], "", None
    for ch in text:
        k = kind if (ord(ch) in cm or ch in " \n") else "fallback"
        if k != cur_kind and cur:
            runs.append((cur_kind, cur)); cur = ""
        cur_kind = k; cur += ch
    if cur:
        runs.append((cur_kind, cur))
    return runs

def text_width(text: str, kind: str, size: int) -> float:
    return sum(font(k, size).getlength(s) for k, s in _runs(text, kind))

def draw_text(d: ImageDraw.ImageDraw, xy, text: str, kind: str, size: int, fill, stroke=0, stroke_fill=None):
    x, y = xy
    for k, s in _runs(text, kind):
        f = font(k, size)
        dy = 0 if k == kind else int(size * 0.06)
        d.text((x, y + dy), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
        x += f.getlength(s)
    return x

def wrap(text: str, kind: str, size: int, max_w: float) -> list[str]:
    out = []
    for para in text.split("\n"):
        words, line = para.split(" "), ""
        for w in words:
            cand = (line + " " + w).strip()
            if line and text_width(cand, kind, size) > max_w:
                out.append(line); line = w
            else:
                line = cand
        out.append(line)
    return out

def fit_lines(text: str, kind: str, size: int, max_w: float, max_lines: int, min_size: int = 24):
    """Shrink font until text fits in max_lines."""
    s = size
    while s > min_size:
        lines = wrap(text, kind, s, max_w)
        if len(lines) <= max_lines:
            return lines, s
        s -= 2
    return wrap(text, kind, min_size, max_w), min_size

def draw_block(d, x, y, lines, kind, size, fill, line_h=1.18, align="left", width=None):
    lh = int(size * line_h)
    for i, ln in enumerate(lines):
        lx = x
        if align == "center" and width:
            lx = x + (width - text_width(ln, kind, size)) / 2
        draw_text(d, (lx, y + i * lh), ln, kind, size, fill)
    return y + lh * len(lines)

# ---------------------------------------------------------------- images
def vgrad(size, c1, c2, c3=None) -> Image.Image:
    w, h = size
    y = np.linspace(0, 1, h)[:, None]
    if c3 is None:
        arr = np.array(c1) * (1 - y) + np.array(c2) * y
    else:
        a = np.clip(y * 2, 0, 1); b = np.clip(y * 2 - 1, 0, 1)
        arr = np.where(y < .5, np.array(c1) * (1 - a) + np.array(c2) * a, np.array(c2) * (1 - b) + np.array(c3) * b)
    arr = np.repeat(arr[:, None, :], w, axis=1)
    return Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA")

def rounded(im: Image.Image, r: int) -> Image.Image:
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.size[0] - 1, im.size[1] - 1], r, fill=255)
    out = im.convert("RGBA")
    out.putalpha(Image.fromarray(np.minimum(np.array(out.getchannel("A")), np.array(m))))
    return out

def shadowed(im: Image.Image, blur=24, off=(0, 18), alpha=90) -> Image.Image:
    pad = blur * 3
    sh = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    a = im.getchannel("A").point(lambda v: v * alpha // 255)
    blk = Image.new("RGBA", im.size, (20, 15, 40, 255)); blk.putalpha(a)
    sh.paste(blk, (pad + off[0], pad + off[1]), blk)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    sh.alpha_composite(im, (pad, pad))
    return sh

def paste_center(canvas, im, cx, cy, scale=1.0, opacity=1.0, rot=0.0):
    if scale <= 0.01 or opacity <= 0.01:
        return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if rot:
        im = im.rotate(rot, Image.BICUBIC, expand=True)
    if opacity < 1:
        im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * opacity)))
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def pill(text, size, bg, fg, padx=36, pady=18, kind="black") -> Image.Image:
    w = int(text_width(text, kind, size)) + padx * 2
    h = int(size * 1.25) + pady * 2
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], h // 2, fill=bg)
    draw_text(d, (padx, pady + int(size * 0.02)), text, kind, size, fg)
    return im

_GRAIN = {}
def grain(im: Image.Image, strength=0.06, seed=0) -> Image.Image:
    key = (im.size, seed % 4)
    if key not in _GRAIN:
        r = np.random.default_rng(seed % 4)
        g = r.normal(0, 1, (im.size[1] // 2, im.size[0] // 2))
        _GRAIN[key] = Image.fromarray(np.clip(128 + g * 40, 0, 255).astype(np.uint8), "L").resize(im.size, Image.BILINEAR)
    rgb = im.convert("RGB")
    gl = _GRAIN[key]
    from PIL import ImageChops
    over = ImageChops.overlay(rgb, Image.merge("RGB", (gl, gl, gl)))
    return Image.blend(rgb, over, strength * 3)

@lru_cache(maxsize=None)
def asset(name: str) -> Image.Image:
    return Image.open(ASSETS / "img" / name).convert("RGBA")

@lru_cache(maxsize=None)
def icon(size: int, radius_k=0.23) -> Image.Image:
    return rounded(asset("icon.png").resize((size, size), Image.LANCZOS), int(size * radius_k))

def check_mark(d, x, y, s, col, w=10):
    d.line([(x, y + s * .5), (x + s * .38, y + s * .85), (x + s, y + s * .1)], fill=col, width=w, joint="curve")

# ---------------------------------------------------------------- options shuffling
_NUM = re.compile(r"^[−\-]?\d+([.,/]\d+)?\s*°?$")
def prepared_options(item: dict, key_q: dict | None = None):
    """Return (options, answer_index). Non-numeric option lists are shuffled with a
    deterministic seed (content id) so correct answers are spread across A–E."""
    q = key_q or item
    opts, ans = list(q["options"]), q["answer"]
    if all(_NUM.match(o.strip()) for o in opts):
        return opts, ans
    rnd = random.Random(item["id"])
    order = list(range(len(opts))); rnd.shuffle(order)
    return [opts[i] for i in order], order.index(ans)

LETTERS = "ABCDE"
