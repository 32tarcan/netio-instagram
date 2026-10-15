"""Carousel (kaydırmalı post) renderer: 1080x1350 JPEG slides."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .common import (CREAM, GREEN, GREY, INK, LETTERS, NAVY, PINK, WHITE, YEL, asset, check_mark, config, font,
                     darker, draw_block, draw_text, fit_lines, icon, lighter, paste_center, pill, prepared_options,
                     rounded, shadowed, subject_color, text_width, wrap, grain)
from .phone import phone_image

W, H = 1080, 1350
M = 84  # side margin

def _base(item, idx, total, dark=False):
    col = subject_color(item["subject"])
    if dark:
        c = Image.new("RGBA", (W, H), NAVY + (255,))
    else:
        c = Image.new("RGBA", (W, H), CREAM + (255,))
    d = ImageDraw.Draw(c)
    # header: logo + name + exam/subject pill
    c.alpha_composite(icon(64), (M, 56))
    draw_text(d, (M + 80, 64), config()["brand"]["app_name"], "display", 40, WHITE if dark else INK)
    tag = pill(f"{item['exam']} · {item['subject']}", 30, col, WHITE, padx=26, pady=12)
    c.alpha_composite(tag, (W - M - tag.width, 60))
    # footer: page dots + swipe hint
    y = H - 74
    dw = 14; gap = 10; x0 = M
    for k in range(total):
        fill = col if k == idx else ((86, 80, 120) if dark else (214, 206, 196))
        w_ = dw * 2.4 if k == idx else dw
        d.rounded_rectangle([x0, y, x0 + w_, y + dw], dw // 2, fill=fill)
        x0 += w_ + gap
    if idx < total - 1:
        hint = "Kaydır  →"
        draw_text(d, (W - M - text_width(hint, "bold", 32), y - 12), hint, "bold", 32, (lighter(col, .3) if dark else GREY))
    return c, d, col

def cover(item, total):
    c, d, col = _base(item, 0, total)
    # accent blob
    blob = Image.new("RGBA", (W, H), (0, 0, 0, 0)); bd = ImageDraw.Draw(blob)
    bd.ellipse([W - 520, H - 640, W + 260, H + 120], fill=lighter(col, .78) + (255,))
    bd.ellipse([-220, 180, 260, 640], fill=lighter(col, .86) + (255,))
    c.alpha_composite(blob)
    d = ImageDraw.Draw(c)
    lines, size = fit_lines(item["title"], "display", 104, W - 2 * M, 4, 64)
    y = draw_block(d, M, 230, lines, "display", size, INK, 1.08)
    d.rounded_rectangle([M, y + 26, M + 150, y + 40], 7, fill=col)
    hl, hs = fit_lines(item.get("hook", ""), "body", 46, W - 2 * M - 40, 3, 34)
    draw_block(d, M, y + 80, hl, "body", hs, GREY, 1.25)
    cat = asset("cat.png"); cat = cat.resize((int(cat.width * 1.45), int(cat.height * 1.45)), Image.LANCZOS)
    c.alpha_composite(shadowed(cat, 18, (0, 16), 60), (W - cat.width - 40, H - cat.height - 200))
    sw = pill("Kaydır, sonunda soru var →", 34, INK, WHITE, padx=34, pady=18)
    c.alpha_composite(sw, (M, H - 220))
    return c

def content_slide(item, slide, idx, total):
    c, d, col = _base(item, idx, total)
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(L)
    ld.text((M, 0), f"{idx:02d}", font=font("display", 130), fill=lighter(col, .55))
    lines, size = fit_lines(slide["h"], "display", 84, W - 2 * M, 3, 54)
    y = draw_block(ld, M, 170, lines, "display", size, INK, 1.1) + 46
    if slide.get("formula"):
        f = slide["formula"]; fs = 80
        while text_width(f, "display", fs) > W - 2 * M - 100 and fs > 36: fs -= 2
        bh = int(fs * 1.6) + 60
        ld.rounded_rectangle([M, y, W - M, y + bh], 40, fill=NAVY)
        draw_text(ld, ((W - text_width(f, "display", fs)) / 2, y + (bh - fs * 1.25) / 2), f, "display", fs, YEL)
        y += bh + 56
    for b in slide.get("body", []):
        bl, bs = fit_lines(b, "body", 52, W - 2 * M - 60, 4, 36)
        ld.ellipse([M + 4, y + bs * 0.36, M + 26, y + bs * 0.36 + 22], fill=col)
        y = draw_block(ld, M + 54, y, bl, "body", bs, INK, 1.3) + 34
    bb = L.getbbox()
    top, bottom = 170, H - 130
    h = bb[3]
    oy = int(top + max(0, (bottom - top - h) / 2) * 0.8)
    c.alpha_composite(L, (0, oy))
    return c

def quiz_slide(item, idx, total, reveal=False):
    c, d, col = _base(item, idx, total, dark=True)
    q = item["quiz"]
    opts, ans = prepared_options(item, q)
    t = pill("CEVAP" if reveal else "KENDİNİ DENE", 32, GREEN if reveal else YEL, WHITE if reveal else NAVY, padx=28, pady=14)
    c.alpha_composite(t, (M, 170))
    ql, qs = fit_lines(q["q"], "display", 60, W - 2 * M, 5, 38)
    y = draw_block(d, M, 270, ql, "display", qs, WHITE, 1.18) + 46
    oh = 112
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    for i, o in enumerate(opts):
        good = reveal and i == ans
        dim = reveal and i != ans
        fill = GREEN + (255,) if good else ((255, 255, 255, 34) if dim else (255, 255, 255, 255))
        od.rounded_rectangle([M, y, W - M, y + oh - 20], 30, fill=fill)
        cfill = (255, 255, 255, 70) if good else ((255, 255, 255, 50) if dim else col + (255,))
        od.ellipse([M + 18, y + 14, M + 18 + oh - 48, y + oh - 34], fill=cfill)
        lw_ = text_width(LETTERS[i], "black", 36)
        draw_text(od, (M + 18 + (oh - 48) / 2 - lw_ / 2, y + 20), LETTERS[i], "black", 36, WHITE)
        os_ = 42
        while text_width(o, "bold", os_) > W - 2 * M - 220 and os_ > 26: os_ -= 2
        tc = WHITE + (255,) if good else ((255, 255, 255, 120) if dim else INK + (255,))
        draw_text(od, (M + oh + 8, y + (oh - 20 - os_ * 1.2) / 2), o, "bold", os_, tc)
        if good: check_mark(od, W - M - 84, y + 28, 40, WHITE, 9)
        y += oh
    if reveal:
        el, es = fit_lines(q.get("explain", ""), "body", 42, W - 2 * M - 60, 4, 28)
        bh = len(el) * int(es * 1.3) + 54
        od.rounded_rectangle([M, y + 16, W - M, y + 16 + bh], 28, fill=(255, 255, 255, 26))
        draw_block(od, M + 30, y + 42, el, "body", es, lighter(YEL, .35) + (255,), 1.3)
    else:
        draw_text(od, (M, y + 22), "Cevabını yorumlara yaz, sonraki slaytta açıklıyoruz.", "body", 34, (190, 186, 214, 255))
    c.alpha_composite(ov)
    return c

def cta_slide(item, idx, total):
    c, d, col = _base(item, idx, total)
    cfg = config()["brand"]
    ph = phone_image("screen_map.png", width=380, rot=-6)
    c.alpha_composite(ph, (W - ph.width + 70, 190))
    lines = ["Bu konuyu", "oyun gibi", "çalış."]
    y = 250
    for i, ln in enumerate(lines):
        draw_text(d, (M, y), ln, "display", 92, PINK if i == 1 else INK); y += 108
    bl, bs = fit_lines("Netio'da her konu bir ada. Soru çöz, XP kazan, serini koru.", "body", 40, 500, 5, 30)
    y = draw_block(d, M, y + 30, bl, "body", bs, GREY, 1.3)
    b = pill(cfg["cta"], 36, NAVY, WHITE, padx=34, pady=22)
    c.alpha_composite(b, (M, H - 300))
    draw_text(d, (M, H - 180), "@" + cfg["instagram_handle"], "bold", 38, col)
    return c

def render(item: dict, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    slides = item["slides"]
    total = 1 + len(slides) + 2 + 1
    imgs = [cover(item, total)]
    for i, s in enumerate(slides):
        imgs.append(content_slide(item, s, i + 1, total))
    imgs.append(quiz_slide(item, len(imgs), total, reveal=False))
    imgs.append(quiz_slide(item, len(imgs), total, reveal=True))
    imgs.append(cta_slide(item, len(imgs), total))
    paths = []
    for i, im in enumerate(imgs):
        p = out_dir / f"{item['id']}_{i + 1:02d}.jpg"
        grain(im, 0.02, i).save(p, "JPEG", quality=92, optimize=True, progressive=False)
        paths.append(p)
    return paths
