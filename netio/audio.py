"""Procedural music + sound design for quiz reels. Every video gets its own seed, so
tempo, chords, instrument and effect timbres differ from video to video."""
from __future__ import annotations

import wave

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 44100

class Mix:
    def __init__(self, dur: float, seed: int):
        self.n = int(dur * SR)
        self.mus = np.zeros((self.n, 2)); self.fx = np.zeros((self.n, 2)); self.send = np.zeros((self.n, 2))
        self.rng = np.random.default_rng(seed)

    def put(self, buf, sig, t0, pan=0.0, rev=0.0):
        i = int(t0 * SR); j = min(self.n, i + len(sig))
        if i >= self.n or i < 0: return
        l = np.cos((pan + 1) * np.pi / 4) * 1.41; r = np.sin((pan + 1) * np.pi / 4) * 1.41
        buf[i:j, 0] += sig[:j - i] * l; buf[i:j, 1] += sig[:j - i] * r
        if rev:
            self.send[i:j, 0] += sig[:j - i] * l * rev; self.send[i:j, 1] += sig[:j - i] * r * rev

def X(d): return np.arange(int(d * SR)) / SR
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, min(hi, 20000)], "bandpass", fs=SR, output="sos"), x)
def hp(x, f): return sosfilt(butter(2, f, "highpass", fs=SR, output="sos"), x)
def lp(x, f, o=2): return sosfilt(butter(o, f, "lowpass", fs=SR, output="sos"), x)

PROGS = [
    [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (261.63, 329.63, 392.0), (196.0, 246.94, 293.66)],
    [(261.63, 329.63, 392.0), (220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (196.0, 246.94, 293.66)],
    [(293.66, 349.23, 440.0), (233.08, 293.66, 349.23), (261.63, 329.63, 392.0), (220.0, 277.18, 329.63)],
    [(246.94, 293.66, 369.99), (196.0, 246.94, 293.66), (220.0, 277.18, 329.63), (164.81, 207.65, 246.94)],
]

def _music(m: Mix, dur: float):
    r = m.rng
    style = int(r.integers(3)); prog = PROGS[int(r.integers(len(PROGS)))]
    bpm = float(r.uniform(108, 128)); b = 60 / bpm; s16 = b / 4
    trans = float(r.choice([1.0, 1.0595, 0.9439]))
    def saw(f, x, det): return sum(2 * ((x * f * (1 + d)) % 1) - 1 for d in det) / len(det)
    def pluck(f, L, v):
        x = X(L); return v * (np.sin(2 * np.pi * f * x) + .4 * np.sin(2 * np.pi * f * 2 * x) * np.exp(-x * 8)) * np.exp(-x * 6) * np.minimum(x / .003, 1)
    for s in range(int((dur - .3) / s16)):
        t = s * s16; bar = (s // 16) % 4; p = s % 16
        ch = [f * trans for f in prog[bar]]
        if p % 4 == 0 and (style != 1 or p in (0, 10)):
            x = X(.28); fr = 48 + 90 * np.exp(-x * 30)
            m.put(m.mus, .45 * np.tanh(1.4 * np.sin(2 * np.pi * np.cumsum(fr) / SR)) * np.exp(-x * 10), t)
        if p in (4, 12):
            x = X(.18); m.put(m.mus, .14 * bp(r.standard_normal(len(x)), 1000, 6000) * np.exp(-x * 25), t, 0, .2)
        if p % 2 == 1 or (style == 1 and p % 2 == 0):
            x = X(.04); m.put(m.mus, .035 * hp(r.standard_normal(len(x)), 7500) * np.exp(-x * 110), t, .4)
        if p in (0, 6, 10):
            x = X(.35); f = ch[0] / 2
            m.put(m.mus, .2 * np.tanh(2 * np.sin(2 * np.pi * f * x)) * np.exp(-x * 7) * np.minimum(x / .004, 1), t)
        if style == 0 and p in (2, 6, 10, 14):
            for k, f in enumerate(ch): m.put(m.mus, pluck(f, .3, .035), t + k * .004, -.3 + k * .3, .2)
        if style == 1 and p in (0, 8):
            for k, f in enumerate(ch):
                x = X(b * 2.2); m.put(m.mus, .03 * np.sin(2 * np.pi * f * x + .8 * np.sin(2 * np.pi * f * 14 * x) * np.exp(-x * 8)) * np.exp(-x * 1.5), t + k * .01, -.3 + k * .3, .35)
        if style == 2 and p % 4 == 2:
            for k, f in enumerate(ch):
                x = X(b * .5); m.put(m.mus, .018 * lp(saw(f, x, (-.008, .006)), 2400) * np.minimum(x / .02, 1) * np.exp(-x * 4), t, -.3 + k * .3, .1)
        if p in (0, 3, 7, 10) and (s // 16) % 2 == 1:
            f = ch[[0, 1, 2, 1][[0, 3, 7, 10].index(p)]] * 2
            m.put(m.mus, pluck(f, .4, .03), t, .35, .35)

def build(path, dur: float, seed: int, events: dict):
    """events: {'slams': [t], 'whoosh': [t], 'pops': [t], 'ticks': (t0, t1), 'reveal': t, 'xp': t, 'cta': t}"""
    m = Mix(dur, seed); r = m.rng
    _music(m, dur)
    J = lambda s=.06: 1 + r.uniform(-s, s)
    # ---- sfx with per-video variation
    for t in events.get("slams", []):
        x = X(.7); f = 55 * J(.15) * (1 + 1.8 * np.exp(-x * 28))
        m.put(m.fx, .45 * (np.tanh(2 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-x * 6) + .5 * bp(r.standard_normal(len(x)), 1500 * J(.3), 8000) * np.exp(-x * 16)), t, 0, .3)
    for t in events.get("whoosh", []):
        d_ = .4 * J(.2); x = X(d_); z = r.standard_normal(len(x)); out = np.zeros(len(x)); f0, f1 = 300 * J(.3), 6000 * J(.3)
        for k in range(0, len(x), 1024):
            fc = f0 * (f1 / f0) ** (k / len(x)); out[k:k + 1024] = bp(z[k:k + 1324], fc * .7, fc * 1.5)[:len(out[k:k + 1024])]
        m.put(m.fx, .12 * out * np.sin(np.pi * x / d_) ** 2, t, r.uniform(-.3, .3), .2)
    for i, t in enumerate(events.get("pops", [])):
        x = X(.09); f = (400 + i * 90) * J() + 700 * (x / .09) ** .5
        m.put(m.fx, .12 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 30), t, -.4 + i * .2, .1)
    if "ticks" in events:
        t0, t1 = events["ticks"]; base = r.uniform(1800, 2600)
        for k in range(int(t1 - t0)):
            urgent = k >= int(t1 - t0) - 3
            x = X(.05); f = base * (1.25 if urgent else 1) * (1 if k % 2 else .84)
            m.put(m.fx, (.12 if urgent else .07) * (np.sin(2 * np.pi * f * x) * np.exp(-x * 120) + .3 * bp(r.standard_normal(len(x)), 3000, 9000) * np.exp(-x * 200)), t0 + k, .2, .05)
    if "reveal" in events:
        t = events["reveal"]; root = r.choice([523.25, 587.33, 659.25])
        for k, mul in enumerate((1, 1.25, 1.5, 2)):
            x = X(1.1); f = root * mul
            m.put(m.fx, .08 * (np.sin(2 * np.pi * f * x) + .3 * np.sin(2 * np.pi * f * 2.76 * x) * np.exp(-x * 6)) * np.exp(-x * 3), t + k * .07, -.2 + k * .13, .35)
        x = X(.8); f = 60 * (1 + 1.5 * np.exp(-x * 25))
        m.put(m.fx, .3 * np.tanh(2 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-x * 7), t)
    if "xp" in events:
        t = events["xp"]
        for k, f in enumerate((1975.5 * J(.03), 2637.0 * J(.03))):
            x = X(.3); m.put(m.fx, .07 * np.sign(np.sin(2 * np.pi * f * x)) * .5 * np.exp(-x * 12), t + k * .07, .4, .1)
    if "cta" in events:
        t = events["cta"]; x = X(.15); f = 250 + 800 * (x / .15) ** .5
        m.put(m.fx, .16 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 18), t, 0, .15)
        x = X(1.3)
        sh = sum(np.sin(2 * np.pi * f * x + r.uniform(0, 6)) * (.5 + .5 * np.sin(2 * np.pi * r.uniform(4, 8) * x)) for f in (1568, 2093, 2637))
        m.put(m.fx, .03 * sh * np.sin(np.pi * x / 1.3), t + .2, 0, .5)
    # ---- music filter: muffled during countdown, opens on reveal
    mus = m.mus / (np.abs(m.mus).max() + 1e-9) * .5
    if "ticks" in events:
        t0, t1 = events["ticks"]
        muff = np.stack([lp(mus[:, 0], 700), lp(mus[:, 1], 700)], 1)
        tt = np.arange(m.n) / SR
        k = np.clip((tt - t0) / .4, 0, 1) * np.clip((t1 - tt) / .15, 0, 1)
        mus = mus * (1 - k[:, None]) + muff * k[:, None] * 1.2
    ir = lambda seed: np.random.default_rng(seed).standard_normal(int(1.4 * SR)) * np.exp(-X(1.4) * 4.5) * .02
    rev = np.stack([fftconvolve(m.send[:, 0], ir(1))[:m.n], fftconvolve(m.send[:, 1], ir(2))[:m.n]], 1)
    rev = np.stack([lp(rev[:, 0], 5000), lp(rev[:, 1], 5000)], 1)
    mix = mus + m.fx + rev * .8
    fi = int(.08 * SR); mix[:fi] *= np.linspace(0, 1, fi)[:, None]
    fo = int(.5 * SR); mix[-fo:] *= np.linspace(1, 0, fo)[:, None]
    mix = np.tanh(mix / (np.abs(mix).max() + 1e-9) * 1.5) / np.tanh(1.5) * .9
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(np.int16(mix * 32767).tobytes())
    return path
