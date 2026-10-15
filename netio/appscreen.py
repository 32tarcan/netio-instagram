"""Draws a Netio in-app question screen (846x1839) for any question — used inside phone mockups."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from .common import INK, LETTERS, WHITE, draw_block, draw_text, fit_lines, subject_color, text_width

SW, SH = 846, 1839

def _bg():
    g = np.linspace(0, 1, SH)[:, None]
    c1, c2, c3 = np.array([196, 234, 247]), np.array([176, 228, 186]), np.array([128, 206, 98])
    arr = np.where(g < .5, c1 * (1 - g * 2) + c2 * (g * 2), c2 * (1 - (g * 2 - 1)) + c3 * (g * 2 - 1))
    return Image.fromarray(np.repeat(arr[:, None, :], SW, 1).astype(np.uint8), "RGB").convert("RGBA")

def _heart(d, x, y, s, col):
    d.ellipse([x, y, x + s * .55, y + s * .55], fill=col); d.ellipse([x + s * .45, y, x + s, y + s * .55], fill=col)
    d.polygon([(x + s * .03, y + s * .36), (x + s * .97, y + s * .36), (x + s * .5, y + s * .95)], fill=col)

def question_screen(exam: str, subject: str, question: str, options: list[str], progress=0.4, time="09:41") -> Image.Image:
    s = _bg(); d = ImageDraw.Draw(s)
    col = subject_color(subject)
    draw_text(d, (86, 46), time, "display", 46, INK)
    d.rounded_rectangle([300, 30, 546, 106], 38, fill=(0, 0, 0))
    d.rounded_rectangle([690, 58, 752, 88], 9, outline=INK, width=4); d.rectangle([696, 64, 740, 82], fill=INK)
    d.ellipse([56, 168, 156, 268], fill=WHITE)
    d.line([(118, 196), (94, 218), (118, 240)], fill=INK, width=10, joint="curve")
    d.rounded_rectangle([186, 202, 600, 234], 16, fill=(255, 255, 255))
    d.rounded_rectangle([186, 202, 186 + int(414 * progress), 234], 16, fill=(255, 150, 60))
    d.rounded_rectangle([630, 176, 790, 260], 42, fill=WHITE)
    _heart(d, 654, 196, 46, (238, 64, 74)); draw_text(d, (714, 188), "10", "display", 46, INK)
    tag = f"{exam} · {subject}"
    tw = text_width(tag, "display", 38)
    d.rounded_rectangle([56, 320, 56 + tw + 56, 384], 32, fill=col)
    draw_text(d, (84, 326), tag, "display", 38, WHITE)
    ql, qs = fit_lines(question, "display", 54, SW - 112, 5, 34)
    y = draw_block(d, 56, 430, ql, "display", qs, INK, 1.22) + 50
    oh = 124
    for i, o in enumerate(options):
        d.rounded_rectangle([56, y, SW - 56, y + oh], 38, fill=WHITE, outline=(226, 224, 236), width=3)
        d.ellipse([80, y + 24, 156, y + 100], fill=(238, 236, 246))
        draw_text(d, (118 - text_width(LETTERS[i], "display", 40) / 2, y + 34), LETTERS[i], "display", 40, INK)
        os_ = 44
        while text_width(o, "bold", os_) > SW - 300 and os_ > 26: os_ -= 2
        draw_text(d, (186, y + (oh - os_ * 1.2) / 2), o, "bold", os_, INK)
        y += oh + 22
    by = max(y + 30, SH - 260)
    d.rounded_rectangle([56, by, SW - 56, by + 120], 60, fill=(190, 196, 206))
    t = "KONTROL ET"; draw_text(d, (SW / 2 - text_width(t, "display", 46) / 2, by + 30), t, "display", 46, WHITE)
    return s
