"""Story renderer: 1080x1920 quiz story (A–D), showing the previous story's answer at the top."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from PIL import Image, ImageDraw

from .common import (GREEN, INK, LETTERS, NAVY, PINK, WHITE, YEL, check_mark, config, darker, draw_block, draw_text,
                     fit_lines, icon, lighter, pill, prepared_options, subject_color, text_width, vgrad, grain)

W, H = 1080, 1920
M = 80

def render(item: dict, out_path: Path, number: int, prev: dict | None = None, today: dt.date | None = None) -> Path:
    col = subject_color(item["subject"])
    c = vgrad((W, H), darker(col, .55), NAVY, (20, 18, 38))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    # soft decorative circles
    d.ellipse([-260, 1350, 420, 2030], fill=col + (60,))
    d.ellipse([760, -120, 1300, 420], fill=col + (50,))
    c.alpha_composite(ov); d = ImageDraw.Draw(c)
    y = 230
    # previous answer strip
    if prev:
        popts, pans = prepared_options(prev)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        el, es = fit_lines(prev.get("explain", ""), "body", 32, W - 2 * M - 150, 2, 24)
        bh = 120 + len(el) * int(es * 1.3)
        od.rounded_rectangle([M, y, W - M, y + bh], 34, fill=(255, 255, 255, 30))
        od.ellipse([M + 26, y + 26, M + 96, y + 96], fill=GREEN + (255,))
        check_mark(od, M + 44, y + 44, 34, WHITE, 8)
        draw_text(od, (M + 120, y + 26), f"Önceki sorunun cevabı: {LETTERS[pans]}) {popts[pans]}", "bold", 36, WHITE + (255,))
        draw_block(od, M + 120, y + 82, el, "body", es, (210, 206, 230, 255), 1.3)
        c.alpha_composite(ov)
        y += bh + 50
    else:
        y += 100
    d = ImageDraw.Draw(c)
    top = pill(f"GÜNÜN SORUSU {number}/4", 34, YEL, NAVY, padx=30, pady=16)
    c.alpha_composite(top, (M, y))
    sp = pill(f"{item['exam']} · {item['subject']}", 32, col, WHITE, padx=26, pady=16)
    c.alpha_composite(sp, (W - M - sp.width, y + 2))
    y += top.height + 40
    # question card
    opts, ans = prepared_options(item)
    ql, qs = fit_lines(item["q"], "display", 64, W - 2 * M - 80, 5, 40)
    qh = len(ql) * int(qs * 1.2) + 80
    d.rounded_rectangle([M, y, W - M, y + qh], 44, fill=WHITE)
    draw_block(d, M + 40, y + 40, ql, "display", qs, INK, 1.2)
    y += qh + 34
    for i, o in enumerate(opts):
        oh = 124
        d.rounded_rectangle([M, y, W - M, y + oh], 40, fill=lighter(NAVY, .1))
        d.rounded_rectangle([M + 3, y + 3, W - M - 3, y + oh - 3], 38, outline=lighter(col, .3), width=3)
        d.ellipse([M + 22, y + 22, M + 102, y + 102], fill=col)
        draw_text(d, (M + 62 - text_width(LETTERS[i], "black", 42) / 2, y + 30), LETTERS[i], "black", 42, WHITE)
        os_ = 48
        while text_width(o, "bold", os_) > W - 2 * M - 170 and os_ > 28: os_ -= 2
        draw_text(d, (M + 128, y + (oh - os_ * 1.2) / 2), o, "bold", os_, WHITE)
        y += oh + 22
    # footer
    cfg = config()
    y = max(y + 30, 1520)
    msg = "Cevabını DM'den yaz!  Doğru cevap bir sonraki hikâyede."
    ml, ms = fit_lines(msg, "bold", 40, W - 2 * M, 2, 30)
    draw_block(d, M, y, ml, "bold", ms, lighter(col, .55), 1.25, align="center", width=W - 2 * M)
    if cfg.get("exam_date") and today:
        left = (dt.date.fromisoformat(str(cfg["exam_date"])) - today).days
        if left > 0:
            cd = pill(f"YKS'ye {left} gün", 34, PINK, WHITE, padx=28, pady=14)
            c.alpha_composite(cd, ((W - cd.width) // 2, 1450 - cd.height))
    ic = icon(84)
    name = f"@{cfg['brand']['instagram_handle']}"
    tw = 84 + 20 + text_width(name, "bold", 40)
    x0 = (W - tw) / 2
    c.alpha_composite(ic, (int(x0), 1680))
    draw_text(d, (x0 + 104, 1700), name, "bold", 40, WHITE)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    grain(c, 0.02, number).save(out_path, "JPEG", quality=92)
    return out_path
