"""iPhone-style mockup built around app screenshots."""
from __future__ import annotations

from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw

from .common import asset, shadowed

SW, SH = 846, 1839
BZ = 24
PW, PH = SW + BZ * 2 + 12, SH + BZ * 2

@lru_cache(maxsize=1)
def _body():
    b = Image.new("RGBA", (PW, PH), (0, 0, 0, 0)); d = ImageDraw.Draw(b)
    d.rounded_rectangle([6, 0, PW - 7, PH - 1], 140, fill=(28, 26, 34), outline=(92, 90, 104), width=4)
    d.rounded_rectangle([12, 6, PW - 13, PH - 7], 134, outline=(46, 44, 54), width=3)
    for (y0, y1) in [(300, 380), (430, 560), (590, 720)]:
        d.rounded_rectangle([0, y0, 8, y1], 3, fill=(60, 58, 70))
    d.rounded_rectangle([PW - 8, 460, PW, 640], 3, fill=(60, 58, 70))
    return b

@lru_cache(maxsize=1)
def _mask():
    m = Image.new("L", (SW, SH), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, SW - 1, SH - 1], 118, fill=255)
    return m

def build_phone(screen: Image.Image) -> Image.Image:
    ph = _body().copy()
    sc = screen.convert("RGBA").resize((SW, SH), Image.LANCZOS) if screen.size != (SW, SH) else screen.copy()
    sc.putalpha(ImageChops.multiply(sc.getchannel("A"), _mask()))
    ph.alpha_composite(sc, (BZ + 6, BZ))
    gl = Image.new("RGBA", ph.size, (0, 0, 0, 0))
    ImageDraw.Draw(gl).polygon([(PW * .55, 0), (PW, 0), (PW, PH * .35), (PW * .1, PH * .62)], fill=(255, 255, 255, 14))
    m = Image.new("L", ph.size, 0); ImageDraw.Draw(m).rounded_rectangle([BZ + 6, BZ, BZ + 6 + SW, BZ + SH], 118, fill=255)
    gl.putalpha(ImageChops.multiply(gl.getchannel("A"), m))
    ph.alpha_composite(gl)
    return ph

@lru_cache(maxsize=16)
def phone_image(screen_name: str, width: int = 480, rot: float = 0.0, shadow: bool = True) -> Image.Image:
    ph = build_phone(asset(screen_name))
    ph = ph.resize((width, int(width * PH / PW)), Image.LANCZOS)
    if rot:
        ph = ph.rotate(rot, Image.BICUBIC, expand=True)
    return shadowed(ph, 30, (0, 24), 110) if shadow else ph
