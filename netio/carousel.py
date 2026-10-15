"""Carousel (kaydırmalı post) — natural "study notes on a desk" look.

Slide order (8 slides):
  1 cover (handwritten title on a notebook page)
  2-3 topic notes
  4 Netio, naturally: phone on the desk showing THIS topic's question in the app + sticky note
  5-7 topic notes
  8 answer to the phone's question, solved in red pen
"""
from __future__ import annotations

import math
import random
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .appscreen import question_screen
from .common import LETTERS, config, draw_text, font, prepared_options, shadowed, text_width, wrap
from .phone import build_phone, PW, PH

W, H = 1080, 1350
PAPER_W, PAPER_H = 930, 1220
RULE = 74                      # ruled line spacing on the paper
LINE0 = 210                    # first ruled line (paper coords)
MARGIN_X = 150                 # red margin line
TEXT_X = MARGIN_X + 34
TEXT_R = PAPER_W - 60

INK_BLUE = (32, 52, 120)
INK_BLACK = (34, 32, 44)
INK_RED = (196, 48, 52)
PENCIL = (110, 106, 118)
HL = {"yellow": (255, 232, 70, 150), "pink": (255, 140, 180, 130), "green": (150, 235, 140, 130), "blue": (140, 210, 255, 130)}

# ------------------------------------------------------------------ textures
@lru_cache(maxsize=4)
def desk(variant: int = 0) -> Image.Image:
    r = np.random.default_rng(100 + variant)
    base = [((214, 180, 138), (176, 134, 92)), ((222, 196, 160), (190, 156, 116)), ((196, 160, 122), (156, 116, 80))][variant % 3]
    n = r.normal(0, 1, (H // 6, 40))
    streak = np.array(Image.fromarray(((n - n.min()) / (n.max() - n.min()) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)) / 255.0
    yy, xx = np.mgrid[0:H, 0:W]
    rings = 0.5 + 0.5 * np.sin((yy / 26.0) + streak * 6 + np.sin(xx / 210.0) * 1.5)
    t = np.clip(0.55 * streak + 0.45 * rings, 0, 1)[..., None]
    arr = np.array(base[0]) * (1 - t) + np.array(base[1]) * t
    light = 1.08 - 0.22 * np.sqrt(((xx - W * 0.25) / W) ** 2 + ((yy - H * 0.15) / H) ** 2)[..., None]
    arr = np.clip(arr * light + r.normal(0, 3, (H, W, 1)), 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA")

@lru_cache(maxsize=1)
def paper_base() -> Image.Image:
    r = np.random.default_rng(7)
    arr = np.full((PAPER_H, PAPER_W, 3), (252, 250, 243), np.float32)
    arr += r.normal(0, 2.2, (PAPER_H, PAPER_W, 1))
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    d = ImageDraw.Draw(im)
    for y in range(LINE0, PAPER_H - 40, RULE):
        d.line([(0, y), (PAPER_W, y)], fill=(176, 202, 232), width=2)
    d.line([(MARGIN_X, 0), (MARGIN_X, PAPER_H)], fill=(232, 150, 150), width=3)
    for k in range(9):  # spiral holes
        x = 60 + k * 103
        d.ellipse([x, 22, x + 30, 52], fill=(196, 170, 140))
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, PAPER_W - 1, PAPER_H - 1], 14, fill=255)
    im.putalpha(m)
    return im

def spiral(layer):
    d = ImageDraw.Draw(layer)
    for k in range(9):
        x = 60 + k * 103
        d.arc([x - 8, -34, x + 38, 48], 200, 340, fill=(90, 92, 104), width=7)

# ------------------------------------------------------------------ hand-drawn primitives
def _jit(rnd, a):
    return rnd.uniform(-a, a)

def wobble_line(d, p0, p1, col, w, rnd, amp=2.2, steps=18):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        x = p0[0] + (p1[0] - p0[0]) * t; y = p0[1] + (p1[1] - p0[1]) * t
        pts.append((x + _jit(rnd, amp * .4), y + _jit(rnd, amp)))
    d.line(pts, fill=col, width=w, joint="curve")

def hand_rect(d, box, col, w, rnd):
    x0, y0, x1, y1 = box; o = 8
    wobble_line(d, (x0 - o, y0), (x1 + o, y0 + _jit(rnd, 3)), col, w, rnd)
    wobble_line(d, (x1, y0 - o), (x1 + _jit(rnd, 3), y1 + o), col, w, rnd)
    wobble_line(d, (x1 + o, y1), (x0 - o, y1 + _jit(rnd, 3)), col, w, rnd)
    wobble_line(d, (x0, y1 + o), (x0 + _jit(rnd, 3), y0 - o), col, w, rnd)

def hand_ellipse(d, box, col, w, rnd):
    x0, y0, x1, y1 = box; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
    pts = []
    a0 = rnd.uniform(0, 6.28)
    for i in range(64):
        a = a0 + i / 60 * 2 * math.pi * 1.08
        k = 1 + 0.04 * math.sin(a * 3 + a0) + i * 0.0012
        pts.append((cx + math.cos(a) * rx * k, cy + math.sin(a) * ry * k))
    d.line(pts, fill=col, width=w, joint="curve")

def squiggle(d, x0, x1, y, col, w, rnd):
    pts = [(x, y + math.sin((x - x0) / 14) * 5 + _jit(rnd, 1)) for x in range(int(x0), int(x1), 6)]
    d.line(pts, fill=col, width=w, joint="curve")

def highlight(layer, box, col, rnd):
    ov = Image.new("RGBA", layer.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    x0, y0, x1, y1 = box
    pts = [(x0 + _jit(rnd, 4), y0 + _jit(rnd, 3)), (x1 + _jit(rnd, 6), y0 + _jit(rnd, 4)),
           (x1 + _jit(rnd, 4), y1 + _jit(rnd, 3)), (x0 + _jit(rnd, 6), y1 + _jit(rnd, 4))]
    d.polygon(pts, fill=col)
    layer.alpha_composite(ov.filter(ImageFilter.GaussianBlur(1.2)))

def arrow(d, p0, p1, col, w, rnd):
    wobble_line(d, p0, p1, col, w, rnd, amp=2)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    for s in (-1, 1):
        a = ang + math.pi + s * 0.5
        d.line([p1, (p1[0] + math.cos(a) * 22, p1[1] + math.sin(a) * 22)], fill=col, width=w)

def line_top(i, size):
    """Top y so that text of `size` sits on ruled line i."""
    return LINE0 + i * RULE - size * 0.98

# ------------------------------------------------------------------ props
def pencil(length=520, rot=-28):
    im = Image.new("RGBA", (length, 60), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([60, 10, length - 70, 50], fill=(250, 200, 50)); d.rectangle([60, 10, length - 70, 22], fill=(255, 220, 90))
    d.rectangle([60, 38, length - 70, 50], fill=(220, 168, 30))
    d.rectangle([length - 70, 8, length - 40, 52], fill=(190, 190, 196)); d.rectangle([length - 40, 10, length, 50], fill=(240, 140, 150))
    d.polygon([(60, 10), (60, 50), (0, 30)], fill=(236, 200, 150)); d.polygon([(18, 22), (18, 38), (0, 30)], fill=(60, 60, 66))
    return shadowed(im.rotate(rot, Image.BICUBIC, expand=True), 8, (6, 10), 70)

def highlighter_pen(rot=20, col=(255, 220, 60)):
    im = Image.new("RGBA", (380, 80), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([40, 8, 300, 72], 20, fill=col); d.rounded_rectangle([290, 4, 380, 76], 18, fill=(60, 60, 70))
    d.polygon([(40, 20), (40, 60), (0, 48), (0, 32)], fill=tuple(int(c * .8) for c in col))
    d.rounded_rectangle([60, 18, 280, 30], 6, fill=(255, 255, 255, 90))
    return shadowed(im.rotate(rot, Image.BICUBIC, expand=True), 8, (6, 10), 70)

def sticky(text_lines, col=(255, 236, 120), size=(330, 300), rot=4, fsize=46, ink=INK_BLACK):
    im = Image.new("RGBA", size, (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, size[0] - 1, size[1] - 1], fill=col)
    d.rectangle([0, 0, size[0] - 1, 34], fill=tuple(max(0, c - 14) for c in col))
    y = 54
    for ln in text_lines:
        draw_text(d, (26, y), ln, "note", fsize, ink); y += int(fsize * 1.1)
    return shadowed(im.rotate(rot, Image.BICUBIC, expand=True), 10, (4, 10), 80)

import zlib
def _var(item):
    return zlib.crc32(item['id'].encode()) % 3

# ------------------------------------------------------------------ slide assembly
def compose(paper: Image.Image, seed: str, variant=0, props=True, page_rot=None):
    rnd = random.Random(seed)
    c = desk(variant).copy()
    rot = page_rot if page_rot is not None else rnd.uniform(-1.6, 1.6)
    p = paper.rotate(rot, Image.BICUBIC, expand=True)
    sh = shadowed(p, 18, (8, 16), 95)
    c.alpha_composite(sh, ((W - sh.width) // 2 + rnd.randint(-8, 8), (H - sh.height) // 2 + 24))
    if props:
        k = rnd.random()
        if k < 0.45:
            pc = pencil(rot=rnd.uniform(-34, -18)); c.alpha_composite(pc, (W - pc.width + rnd.randint(40, 120), H - pc.height + rnd.randint(10, 70)))
        elif k < 0.8:
            hp = highlighter_pen(rnd.uniform(14, 30), rnd.choice([(255, 220, 60), (255, 130, 180), (130, 220, 120)]))
            c.alpha_composite(hp, (W - hp.width + rnd.randint(60, 140), rnd.randint(-40, 30)))
    return c

def new_page(number=None, total=None, seed="x"):
    pg = paper_base().copy()
    spiral(pg)
    d = ImageDraw.Draw(pg)
    if number is not None:
        rnd = random.Random(seed + "pn")
        t = f"{number}/{total}"
        x = PAPER_W - 110; y = 92
        draw_text(d, (x, y), t, "note", 46, PENCIL)
    handle = "@" + config()["brand"]["instagram_handle"]
    draw_text(d, (PAPER_W - 60 - text_width(handle, "note", 34), PAPER_H - 62), handle, "note", 34, (150, 146, 160))
    return pg, d

def write_lines(pg, d, lines, start_line, kind, size, col, x=TEXT_X):
    for i, ln in enumerate(lines):
        draw_text(d, (x, line_top(start_line + i, size)), ln, kind, size, col)
    return start_line + len(lines)

MARGIN_NOTES = ["önemli!", "unutma!", "dikkat!", "ezberle", "çok sorulur", "püf nokta"]

def cover(item, total):
    rnd = random.Random(item["id"] + "cover")
    pg, d = new_page(seed=item["id"])
    size = 92
    lines = wrap(item["title"], "hand_title", size, TEXT_R - TEXT_X)
    while len(lines) > 4 and size > 60:
        size -= 6; lines = wrap(item["title"], "hand_title", size, TEXT_R - TEXT_X)
    first = 2
    step = 2 if size > 70 else 1.5
    # highlight the last line of the title
    hl_i = len(lines) - 1
    for i, ln in enumerate(lines):
        li = first + i * step
        ty = line_top(li, size)
        if i == hl_i:
            w = text_width(ln, "hand_title", size)
            highlight(pg, (TEXT_X - 10, ty + size * .55, TEXT_X + w + 10, ty + size * 1.05), HL[rnd.choice(["yellow", "pink", "green"])], rnd)
            d = ImageDraw.Draw(pg)
        draw_text(d, (TEXT_X, ty), ln, "hand_title", size, INK_BLACK)
    nxt = int(first + len(lines) * step) + 1
    hook = wrap(item.get("hook", ""), "hand", 60, TEXT_R - TEXT_X)
    write_lines(pg, d, hook[:3], nxt, "hand", 60, INK_BLUE)
    yarrow = LINE0 + (nxt + len(hook[:3]) + 1) * RULE
    draw_text(d, (TEXT_X, yarrow - 66), "kaydır, 4. sayfada bir sorum var", "note", 56, INK_RED)
    arrow(d, (TEXT_X + 610, yarrow - 34), (TEXT_X + 720, yarrow - 34), INK_RED, 5, rnd)
    c = compose(pg, item["id"] + "c", variant=_var(item))
    st = sticky([item["exam"], item["subject"]], rot=rnd.uniform(5, 9), size=(300, 210), fsize=56)
    c.alpha_composite(st, (W - st.width - 10, 40))
    return c

def notes_slide(item, slide, number, total):
    rnd = random.Random(item["id"] + str(number))
    pg, d = new_page(number, total, item["id"])
    size = 80
    hl = wrap(slide["h"], "hand_title", size, TEXT_R - TEXT_X)
    while len(hl) > 2 and size > 52:
        size -= 4; hl = wrap(slide["h"], "hand_title", size, TEXT_R - TEXT_X)
    li = 1
    for ln in hl:
        draw_text(d, (TEXT_X, line_top(li, size)), ln, "hand_title", size, INK_BLACK)
        last_w = text_width(ln, "hand_title", size); li += 1
    squiggle(d, TEXT_X, TEXT_X + min(last_w, TEXT_R - TEXT_X), LINE0 + (li - 1) * RULE + 12, INK_RED, 4, rnd)
    li += 1
    if slide.get("formula"):
        f = slide["formula"]; fs = 80
        while text_width(f, "hand_med", fs) > TEXT_R - TEXT_X - 80 and fs > 36: fs -= 2
        fw = text_width(f, "hand_med", fs)
        fx = TEXT_X + (TEXT_R - TEXT_X - fw) / 2
        ty = line_top(li + 1, fs)
        highlight(pg, (fx - 18, ty + fs * .25, fx + fw + 18, ty + fs * 1.1), HL[rnd.choice(["yellow", "green", "blue"])], rnd)
        d = ImageDraw.Draw(pg)
        draw_text(d, (fx, ty), f, "hand_med", fs, INK_BLACK)
        hand_rect(d, (fx - 34, LINE0 + li * RULE - 18, fx + fw + 34, LINE0 + (li + 1) * RULE + 22), INK_RED, 4, rnd)
        li += 3
    bs = 60
    for b in slide.get("body", []):
        bl = wrap(b, "hand", bs, TEXT_R - TEXT_X - 40)
        y0 = line_top(li, bs)
        d.ellipse([TEXT_X + 2, y0 + bs * .5, TEXT_X + 18, y0 + bs * .5 + 16], fill=INK_BLUE)
        li = write_lines(pg, d, bl, li, "hand", bs, INK_BLUE, x=TEXT_X + 40) + 1
        if li > 13: break
    if rnd.random() < 0.55:
        note = rnd.choice(MARGIN_NOTES)
        y = line_top(2, 44)
        nd = Image.new("RGBA", (190, 120), (0, 0, 0, 0)); ndd = ImageDraw.Draw(nd)
        draw_text(ndd, (6, 20), note, "note", 44, INK_RED)
        nd = nd.rotate(rnd.uniform(-14, -6), Image.BICUBIC, expand=True)
        pg.alpha_composite(nd, (int(max(0, MARGIN_X - nd.width + 10)), int(LINE0 + 9 * RULE)))
    return compose(pg, item["id"] + str(number), variant=_var(item))

def app_slide(item, number, total):
    rnd = random.Random(item["id"] + "app")
    q = item["quiz"]; opts, _ = prepared_options(item, q)
    # partial notebook page underneath (natural continuity)
    pg, d = new_page(number, total, item["id"])
    c = compose(pg, item["id"] + "app", variant=_var(item), props=False, page_rot=rnd.uniform(-5, -3))
    scr = question_screen(item["exam"], item["subject"], q["q"], opts, progress=rnd.uniform(.35, .7))
    ph = build_phone(scr)
    pw = 560
    ph = ph.resize((pw, int(pw * PH / PW)), Image.LANCZOS).rotate(rnd.uniform(5, 9), Image.BICUBIC, expand=True)
    c.alpha_composite(shadowed(ph, 24, (14, 22), 120), (W - ph.width + 10, 110))
    b = config()["brand"]
    st = sticky(["Bu konunun sorusunu", f"{b['app_name']}'da çözdüm.", "Sence cevap ne?", "Cevap son sayfada!"],
                col=(255, 238, 120), size=(400, 320), rot=rnd.uniform(-8, -4), fsize=46)
    c.alpha_composite(st, (10, 560))
    pc = pencil(rot=-24); c.alpha_composite(pc, (-120, H - pc.height + 30))
    st2 = sticky([f"@{b['instagram_handle']}"], col=(170, 220, 255), size=(330, 130), rot=rnd.uniform(3, 6), fsize=50)
    c.alpha_composite(st2, (40, 930))
    return c

def answer_slide(item, number, total):
    rnd = random.Random(item["id"] + "ans")
    q = item["quiz"]; opts, ans = prepared_options(item, q)
    pg, d = new_page(number, total, item["id"])
    draw_text(d, (TEXT_X, line_top(1, 70)), "Cevap", "hand_title", 70, INK_RED)
    squiggle(d, TEXT_X, TEXT_X + 210, LINE0 + RULE + 12, INK_RED, 4, rnd)
    ql = wrap(q["q"], "hand", 54, TEXT_R - TEXT_X)
    li = write_lines(pg, d, ql[:4], 3, "hand", 54, INK_BLACK) + 1
    for i, o in enumerate(opts):
        s = 56; ty = line_top(li, s)
        txt = f"{LETTERS[i]})  {o}"
        draw_text(d, (TEXT_X + 10, ty), txt, "hand", s, INK_BLUE)
        if i == ans:
            w = text_width(txt, "hand", s)
            hand_ellipse(d, (TEXT_X - 14, ty - 2, TEXT_X + w + 40, ty + s * 1.15), INK_RED, 5, rnd)
            draw_text(d, (TEXT_X + w + 60, ty - 4), "✓", "fallback", 52, INK_RED)
        li += 1
    el = wrap(q.get("explain", ""), "hand", 54, TEXT_R - TEXT_X - 20)
    write_lines(pg, d, el[:3], li, "hand", 54, INK_RED)
    c = compose(pg, item["id"] + "ans", variant=_var(item))
    b = config()["brand"]
    st = sticky(["Doğru bildin mi?", "Yorumlara yaz!", f"@{b['instagram_handle']}"],
                col=(255, 200, 220), size=(360, 240), rot=rnd.uniform(4, 8), fsize=46)
    c.alpha_composite(st, (W - st.width - 10, 20))
    return c

def render(item: dict, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    slides = item["slides"][:5]
    total = 1 + len(slides) + 2
    imgs = [cover(item, total)]
    n = 2
    for i, s in enumerate(slides):
        if n == 4:
            imgs.append(app_slide(item, n, total)); n += 1
        imgs.append(notes_slide(item, s, n, total)); n += 1
    if len(imgs) < 4:
        imgs.append(app_slide(item, n, total)); n += 1
    imgs.append(answer_slide(item, n, total))
    paths = []
    for i, im in enumerate(imgs):
        p = out_dir / f"{item['id']}_{i + 1:02d}.jpg"
        im.convert("RGB").save(p, "JPEG", quality=92)
        paths.append(p)
    return paths
