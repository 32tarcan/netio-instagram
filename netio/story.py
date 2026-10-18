"""Story renderer (1080x1920): a question frame ("Cevap için dokun") and an answer frame.
Both are posted back-to-back, so tapping forward reveals the answer — Instagram's API does
not allow poll/quiz stickers, this keeps the tap-to-reveal interaction fully automatic."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from PIL import Image, ImageDraw

from .common import (GREEN, INK, LETTERS, NAVY, PINK, WHITE, YEL, check_mark, config, darker, draw_block, draw_text,
                     fit_lines, icon, lighter, pill, prepared_options, sticker_options, subject_color, text_width, vgrad, grain)

W, H = 1080, 1920
M = 80

def _bg(col):
    c = vgrad((W, H), darker(col, .55), NAVY, (20, 18, 38))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    d.ellipse([-260, 1350, 420, 2030], fill=col + (60,)); d.ellipse([760, -120, 1300, 420], fill=col + (50,))
    c.alpha_composite(ov)
    return c

def _header(c, item, number, col, y, label):
    top = pill(label, 34, YEL, NAVY, padx=30, pady=16)
    c.alpha_composite(top, (M, y))
    sp = pill(f"{item['exam']} · {item['subject']}", 32, col, WHITE, padx=26, pady=16)
    c.alpha_composite(sp, (W - M - sp.width, y + 2))
    return y + top.height + 36

def _question_card(c, d, item, y, size=62):
    ql, qs = fit_lines(item["q"], "display", size, W - 2 * M - 80, 5, 38)
    qh = len(ql) * int(qs * 1.2) + 76
    d.rounded_rectangle([M, y, W - M, y + qh], 44, fill=WHITE)
    draw_block(d, M + 40, y + 38, ql, "display", qs, INK, 1.2)
    return y + qh + 30

def _options(c, item, col, y, reveal=False, four=False):
    opts, ans = sticker_options(item) if four else prepared_options(item)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    oh = 116
    for i, o in enumerate(opts):
        good = reveal and i == ans; dim = reveal and i != ans
        if good:
            d.rounded_rectangle([M, y, W - M, y + oh], 40, fill=GREEN + (255,))
        else:
            d.rounded_rectangle([M, y, W - M, y + oh], 40, fill=lighter(NAVY, .1) + ((150 if dim else 255),))
            d.rounded_rectangle([M + 3, y + 3, W - M - 3, y + oh - 3], 38, outline=lighter(col, .3) + ((90 if dim else 255),), width=3)
        d.ellipse([M + 20, y + 18, M + 98, y + 96], fill=(WHITE + (70,)) if good else (col + ((110 if dim else 255),)))
        draw_text(d, (M + 59 - text_width(LETTERS[i], "black", 40) / 2, y + 26), LETTERS[i], "black", 40, WHITE + (255,))
        os_ = 46
        while text_width(o, "bold", os_) > W - 2 * M - 220 and os_ > 26: os_ -= 2
        draw_text(d, (M + 124, y + (oh - os_ * 1.2) / 2), o, "bold", os_, WHITE + ((120 if dim else 255),))
        if good: check_mark(d, W - M - 92, y + 32, 50, WHITE, 10)
        y += oh + 18
    c.alpha_composite(ov)
    return y

def _footer_brand(c, d, y=1690):
    cfg = config()
    ic = icon(84); name = f"@{cfg['brand']['instagram_handle']}"
    tw = 84 + 20 + text_width(name, "bold", 40); x0 = (W - tw) / 2
    c.alpha_composite(ic, (int(x0), y)); draw_text(d, (x0 + 104, y + 20), name, "bold", 40, WHITE)

def render_question(item: dict, out_path: Path, number: int, today: dt.date | None = None) -> Path:
    col = subject_color(item["subject"])
    c = _bg(col); d = ImageDraw.Draw(c)
    y = _header(c, item, number, col, 250, f"GÜNÜN SORUSU {number}/4")
    y = _question_card(c, d, item, y)
    y = _options(c, item, col, y)
    cfg = config()
    if cfg.get("exam_date") and today:
        left = (dt.date.fromisoformat(str(cfg["exam_date"])) - today).days
        if left > 0:
            cd = pill(f"YKS'ye {left} gün", 32, PINK, WHITE, padx=26, pady=12)
            c.alpha_composite(cd, ((W - cd.width) // 2, y + 6))
    # tap-to-reveal cue
    cue = pill("Cevap için dokun  →", 48, YEL, NAVY, padx=46, pady=26)
    c.alpha_composite(cue, ((W - cue.width) // 2, 1530))
    _footer_brand(c, d)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    grain(c, 0.02, number).save(out_path, "JPEG", quality=92)
    return out_path

def render_answer(item: dict, out_path: Path, number: int, four: bool = False) -> Path:
    col = subject_color(item["subject"])
    c = _bg(col); d = ImageDraw.Draw(c)
    y = _header(c, item, number, col, 250, "CEVAP")
    y = _question_card(c, d, item, y, size=50)
    y = _options(c, item, col, y, reveal=True, four=four)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    el, es = fit_lines(item.get("explain", ""), "body", 42, W - 2 * M - 60, 3, 28)
    bh = len(el) * int(es * 1.3) + 50
    od.rounded_rectangle([M, y + 6, W - M, y + 6 + bh], 30, fill=(255, 255, 255, 30))
    draw_block(od, M + 30, y + 30, el, "body", es, lighter(YEL, .35) + (255,), 1.3)
    c.alpha_composite(ov); d = ImageDraw.Draw(c)
    b = config()["brand"]
    msg = f"Her gün yeni sorular {b['app_name']}'da. {b['cta']}"
    ml, ms = fit_lines(msg, "bold", 38, W - 2 * M, 2, 28)
    draw_block(d, M, 1560, ml, "bold", ms, lighter(col, .55), 1.25, align="center", width=W - 2 * M)
    _footer_brand(c, d)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    grain(c, 0.02, number + 10).save(out_path, "JPEG", quality=92)
    return out_path


def _dashed_rect(d, box, col, dash=26, gap=16, width=6, r=48):
    x0, y0, x1, y1 = box
    def hline(y, a, b):
        x = a
        while x < b:
            d.line([(x, y), (min(x + dash, b), y)], fill=col, width=width); x += dash + gap
    def vline(x, a, b):
        y = a
        while y < b:
            d.line([(x, y), (x, min(y + dash, b))], fill=col, width=width); y += dash + gap
    hline(y0, x0 + r, x1 - r); hline(y1, x0 + r, x1 - r)
    vline(x0, y0 + r, y1 - r); vline(x1, y0 + r, y1 - r)
    for (cx, cy, a0) in ((x0, y0, 180), (x1 - 2 * r, y0, 270), (x1 - 2 * r, y1 - 2 * r, 0), (x0, y1 - 2 * r, 90)):
        d.arc([cx, cy, cx + 2 * r, cy + 2 * r], a0, a0 + 90, fill=col, width=width)

def render_interactive(item: dict, out_path: Path, number: int, today: dt.date | None = None) -> Path:
    """Story image for a hand-posted story with Instagram's quiz sticker: the full question on top,
    a dashed area where the sticker goes (the sticker carries the 4 options)."""
    col = subject_color(item["subject"])
    c = _bg(col); d = ImageDraw.Draw(c)
    y = _header(c, item, number, col, 230, f"GÜNÜN SORUSU {number}/4")
    ql, qs = fit_lines(item["q"], "display", 66, W - 2 * M - 80, 7, 38)
    qh = len(ql) * int(qs * 1.2) + 84
    d.rounded_rectangle([M, y, W - M, y + qh], 44, fill=WHITE)
    draw_block(d, M + 40, y + 42, ql, "display", qs, INK, 1.2)
    y += qh + 40
    t = "Cevabını işaretle, doğru mu gör ↓"
    ts = 44
    while text_width(t, "bold", ts) > W - 2 * M and ts > 28: ts -= 2
    draw_text(d, ((W - text_width(t, "bold", ts)) / 2, y), t, "bold", ts, YEL)
    y += int(ts * 1.4) + 20
    box_h = max(420, min(620, 1640 - y))
    box = (M + 30, y, W - M - 30, y + box_h)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.rounded_rectangle(box, 48, fill=(255, 255, 255, 18))
    _dashed_rect(od, box, (255, 255, 255, 110))
    lab = "TEST ÇIKARTMASI BURAYA"
    draw_text(od, ((W - text_width(lab, "bold", 34)) / 2, box[1] + box_h / 2 - 22), lab, "bold", 34, (255, 255, 255, 90))
    c.alpha_composite(ov); d = ImageDraw.Draw(c)
    _footer_brand(c, d, y=max(1700, box[3] + 40) if box[3] + 40 < 1800 else 1790)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    grain(c, 0.02, number + 20).save(out_path, "JPEG", quality=92)
    return out_path
