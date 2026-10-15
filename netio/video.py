"""Quiz Reels renderer: 20 s, 1080x1920, H.264 (High@4.0) + AAC — safe for Instagram and phones."""
from __future__ import annotations

import math
import shutil
import subprocess
import zlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from . import audio
from .common import (CREAM, GREEN, INK, LETTERS, NAVY, PINK, WHITE, YEL, check_mark, config, darker, draw_block,
                     draw_text, fit_lines, icon, lighter, paste_center, pill, prepared_options, shadowed,
                     subject_color, text_width, vgrad)
from .phone import phone_image

W, H, FPS, DUR = 1080, 1920, 30, 20.0
X0, X1 = 70, 950          # keep clear of Instagram's right-side buttons
T_Q, T_C0, T_C1, T_CTA = 2.6, 3.4, 13.4, 16.4

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, s, d): return clamp((t - s) / d)
def eo(x): return 1 - 2 ** (-10 * x) if x < 1 else 1.0
def back(x, s=1.7):
    x -= 1; return x * x * ((s + 1) * x + s) + 1

class QuizReel:
    def __init__(self, item):
        self.item = item
        self.col = subject_color(item["subject"])
        self.opts, self.ans = prepared_options(item)
        self.bg = vgrad((W, H), lighter(self.col, .15), darker(self.col, .5), NAVY)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        d.ellipse([-300, 1300, 500, 2100], fill=WHITE + (18,)); d.ellipse([700, -200, 1350, 450], fill=WHITE + (22,))
        self.bg.alpha_composite(ov)
        self.cream = Image.new("RGBA", (W, H), CREAM + (255,))
        # hook texts
        self.h1 = self._txt("Bu soruyu", 104, WHITE)
        self.h2 = self._txt("10 saniyede", 150, YEL)
        self.h3 = self._txt("çözebilir misin?", 104, WHITE)
        self.tag = pill(f"{item['exam']} · {item['subject']}", 40, WHITE, self.col, padx=32, pady=16)
        # question card
        ql, qs = fit_lines(item["q"], "display", 60, X1 - X0 - 80, 5, 38)
        ch = len(ql) * int(qs * 1.2) + 84
        card = Image.new("RGBA", (X1 - X0, ch), (0, 0, 0, 0)); d = ImageDraw.Draw(card)
        d.rounded_rectangle([0, 0, card.width - 1, ch - 1], 44, fill=WHITE)
        draw_block(d, 40, 42, ql, "display", qs, INK, 1.2)
        self.card = shadowed(card, 20, (0, 14), 80)
        self.card_h = ch
        self.rows = [self._row(i, "normal") for i in range(len(self.opts))]
        self.rows_good = self._row(self.ans, "good")
        self.rows_dim = [self._row(i, "dim") for i in range(len(self.opts))]
        el, es = fit_lines(item.get("explain", ""), "body", 42, X1 - X0 - 70, 3, 28)
        eh = len(el) * int(es * 1.3) + 60
        ex = Image.new("RGBA", (X1 - X0, eh), (0, 0, 0, 0)); d = ImageDraw.Draw(ex)
        d.rounded_rectangle([0, 0, ex.width - 1, eh - 1], 32, fill=NAVY + (235,))
        draw_block(d, 34, 30, el, "body", es, lighter(YEL, .3), 1.3)
        self.explain = ex
        cfg = config()["brand"]
        self.cta1 = self._txt("Böyle sorular", 88, INK)
        self.cta2 = self._txt(f"{cfg['app_name']}'da oyun gibi!", 88, PINK)
        self.cta_pill = shadowed(pill(cfg["cta"], 40, NAVY, WHITE, padx=40, pady=24), 14, (0, 10), 80)
        self.handle = self._txt("@" + cfg["instagram_handle"], 46, self.col, kind="bold")
        self.phone = phone_image("screen_map.png", width=400, rot=-4)
        self.icon = icon(120)
        self.layout()

    def _txt(self, s, size, col, kind="display"):
        w = int(text_width(s, kind, size)) + 20
        im = Image.new("RGBA", (w, int(size * 1.35)), (0, 0, 0, 0))
        draw_text(ImageDraw.Draw(im), (10, 0), s, kind, size, col)
        return im

    def _row(self, i, state):
        oh = 118
        im = Image.new("RGBA", (X1 - X0, oh), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        if state == "good":
            d.rounded_rectangle([0, 0, im.width - 1, oh - 1], 38, fill=GREEN)
            cc, tc = WHITE + (80,), WHITE
        elif state == "dim":
            d.rounded_rectangle([0, 0, im.width - 1, oh - 1], 38, fill=(255, 255, 255, 40))
            cc, tc = (255, 255, 255, 50), (255, 255, 255, 130)
        else:
            d.rounded_rectangle([0, 0, im.width - 1, oh - 1], 38, fill=WHITE)
            cc, tc = self.col + (255,), INK
        d.ellipse([20, 20, 98, 98], fill=cc)
        draw_text(d, (59 - text_width(LETTERS[i], "black", 42) / 2, 26), LETTERS[i], "black", 42, WHITE)
        o = self.opts[i]; os_ = 46
        while text_width(o, "bold", os_) > im.width - 200 and os_ > 26: os_ -= 2
        draw_text(d, (122, (oh - os_ * 1.2) / 2), o, "bold", os_, tc)
        if state == "good": check_mark(d, im.width - 92, 34, 48, WHITE, 10)
        return im

    def layout(self):
        top = 470
        self.card_y = top
        self.rows_y = [top + self.card_h + 30 + i * 136 for i in range(len(self.opts))]
        self.explain_y = self.rows_y[-1] + 136 + 10

    # ---------------- frame
    def frame(self, t):
        if t < T_CTA:
            c = self.bg.copy()
        else:
            c = self.cream.copy()
        if t < T_Q + 0.3:
            out = eo(prog(t, T_Q - 0.25, 0.4))
            paste_center(c, self.tag, W / 2, 420 - out * 300, opacity=eo(prog(t, .05, .3)) * (1 - out))
            for im, t0, y in ((self.h1, .15, 760), (self.h2, .5, 900), (self.h3, .85, 1040)):
                if t >= t0:
                    p = clamp((t - t0) / .14); sc = 1.7 - .7 * (1 - (1 - p) ** 3)
                    paste_center(c, im, W / 2, y - out * 600, scale=sc, opacity=clamp(p * 2) * (1 - out))
        if T_Q <= t < T_CTA + 0.3:
            fade = 1 - eo(prog(t, T_CTA - 0.1, 0.35))
            p = eo(prog(t, T_Q, .5))
            cx = X0 + (X1 - X0) / 2
            paste_center(c, self.card, cx, self.card_y + self.card_h / 2 + (1 - p) * 900, opacity=fade)
            reveal = t >= T_C1
            for i, ry in enumerate(self.rows_y):
                pi = eo(prog(t, T_Q + .35 + i * .08, .45))
                if pi <= 0: continue
                if reveal:
                    im = self.rows_good if i == self.ans else self.rows_dim[i]
                    sc = 1 + .05 * math.sin(math.pi * clamp((t - T_C1) / .25)) if i == self.ans else 1
                else:
                    im, sc = self.rows[i], 1
                paste_center(c, im, cx + (1 - pi) * 120, ry + 59, scale=sc, opacity=pi * fade)
            # countdown ring
            if T_C0 - .3 < t < T_C1 + .4:
                self._ring(c, t)
            if reveal:
                pe = eo(prog(t, T_C1 + .3, .45))
                paste_center(c, self.explain, cx, self.explain_y + self.explain.height / 2 + (1 - pe) * 60, opacity=pe * fade)
                xp = prog(t, T_C1 + .2, 1.0)
                if 0 < xp < 1:
                    chip = pill("+10 XP", 54, (255, 150, 60), WHITE, padx=30, pady=16)
                    e = eo(xp)
                    paste_center(c, chip, 830, self.rows_y[self.ans] - e * 200, scale=.6 + .4 * eo(clamp(xp * 3)), opacity=1 - clamp((xp - .7) / .3), rot=-7)
        if t >= T_CTA:
            u = t - T_CTA
            p = eo(prog(u, 0, .6))
            c.alpha_composite(self.phone, (int(W - self.phone.width + 90), int(600 + (1 - p) * 1200)))
            for im, t0, y in ((self.cta1, .2, 380), (self.cta2, .4, 490)):
                pp = eo(prog(u, t0, .45))
                paste_center(c, im, W / 2, y + (1 - pp) * 40, opacity=pp)
            ip = back(clamp((u - .3) / .5))
            paste_center(c, self.icon, 250, 900, scale=max(.01, ip), rot=-6)
            bp_ = back(clamp((u - .8) / .45))
            pulse = 1 + .04 * math.sin(max(0, u - 1.3) * 7) * (u > 1.3)
            paste_center(c, self.cta_pill, W / 2, 1600, scale=max(.01, (.4 + .6 * bp_) * pulse), opacity=clamp(bp_))
            paste_center(c, self.handle, W / 2, 1730, opacity=eo(prog(u, 1.1, .4)))
        k = min(clamp(t / .15), clamp((DUR - t) / .4))
        if k < 1:
            c.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - k)))))
        return c.convert("RGB")

    def _ring(self, c, t):
        left = clamp(1 - (t - T_C0) / (T_C1 - T_C0))
        n = max(0, math.ceil((T_C1 - t))) if t < T_C1 else 0
        n = min(10, n)
        urgent = n <= 3
        R = 110; cx, cy = W / 2, 300
        ov = Image.new("RGBA", (R * 2 + 40, R * 2 + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        d.ellipse([20, 20, 20 + R * 2, 20 + R * 2], fill=NAVY + (220,))
        d.arc([28, 28, 12 + R * 2, 12 + R * 2], 0, 360, fill=(255, 255, 255, 50), width=14)
        if left > 0:
            d.arc([28, 28, 12 + R * 2, 12 + R * 2], -90, -90 + 360 * left, fill=PINK if urgent else YEL, width=14)
        s = str(n)
        draw_text(d, (20 + R - text_width(s, "display", 110) / 2, 20 + R - 78), s, "display", 110, WHITE)
        beat = 1 + .08 * math.exp(-((t - T_C0) % 1) * 8) if T_C0 <= t < T_C1 else 1
        a = eo(prog(t, T_C0 - .3, .3)) * (1 - eo(prog(t, T_C1 + .1, .3)))
        paste_center(c, ov, cx, cy, scale=beat, opacity=a)

def render(item: dict, out_path: Path, workdir: Path) -> Path:
    workdir.mkdir(parents=True, exist_ok=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    reel = QuizReel(item)
    seed = zlib.crc32(item["id"].encode())
    wav = workdir / f"{item['id']}.wav"
    n_opts = len(reel.opts)
    audio.build(wav, DUR, seed, {
        "slams": [.15, .5, .85], "whoosh": [T_Q - .15, T_CTA - .2],
        "pops": [T_Q + .35 + i * .08 for i in range(n_opts)],
        "ticks": (T_C0, T_C1), "reveal": T_C1, "xp": T_C1 + .25, "cta": T_CTA + .3})
    ff = shutil.which("ffmpeg") or "ffmpeg"
    p = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-i", str(wav),
                          "-c:v", "libx264", "-profile:v", "high", "-level:v", "4.0", "-preset", "medium",
                          "-b:v", "4500k", "-maxrate", "5500k", "-bufsize", "9000k", "-pix_fmt", "yuv420p",
                          "-tag:v", "avc1", "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
                          "-shortest", "-movflags", "+faststart", str(out_path)], stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        p.stdin.write(reel.frame(i / FPS).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("ffmpeg failed")
    return out_path

def thumbnail(item: dict, out_path: Path) -> Path:
    reel = QuizReel(item)
    reel.frame(9.0).save(out_path, "JPEG", quality=90)
    return out_path
