"""Optional: top up the content bank with Claude when it runs low.

Two passes: (1) generate new items as strict JSON, (2) an independent verification pass
that rejects any item whose answer or facts are doubtful. Only items that pass schema
checks AND verification are appended. Requires ANTHROPIC_API_KEY.
"""
from __future__ import annotations

import json
import os
import re

import requests

from .common import CONTENT, config, load_json, save_json

API = "https://api.anthropic.com/v1/messages"

SUBJECTS_TYT = ["Matematik", "Geometri", "Türkçe", "Fizik", "Kimya", "Biyoloji", "Tarih", "Coğrafya", "Felsefe"]
SUBJECTS_AYT = ["Matematik", "Fizik", "Kimya", "Biyoloji", "Edebiyat", "Tarih", "Coğrafya"]

def _call(prompt: str, max_tokens=16000) -> str:
    cfg = config()["content"]
    r = requests.post(API, timeout=600, headers={
        "x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": cfg.get("model", "claude-sonnet-5-5"), "max_tokens": max_tokens,
              "messages": [{"role": "user", "content": prompt}]})
    r.raise_for_status()
    return "".join(b.get("text", "") for b in r.json()["content"])

def _json(text: str):
    m = re.search(r"\[.*\]", text, re.S)
    return json.loads(m.group(0)) if m else []

RULES = """Kurallar:
- Türkçe, YKS (TYT/AYT) müfredatına uygun, ÖSYM soru tarzında ve %100 doğru olmalı.
- Tartışmalı, güncelliğini yitirebilecek ya da kaynağa göre değişen bilgileri KULLANMA.
- Sadece ², ³, √, π, ×, ÷, −, ° gibi yaygın semboller kullan; karmaşık formül yazımı kullanma.
- Şıklar kısa olsun (en fazla ~40 karakter). Tek bir doğru cevap olsun.
- Doğru cevabın yerini (answer indeksi) dengeli dağıt.
- Sadece JSON dizisi döndür, başka açıklama yazma."""

def _existing_questions():
    qs = []
    for f in ("carousels.json", "quiz_videos.json", "stories.json"):
        for it in load_json(CONTENT / f, []):
            qs.append(it.get("title") or it.get("q"))
    return qs[-200:]

def _next_id(items, prefix):
    n = max([int(re.sub(r"\D", "", it["id"]) or 0) for it in items] + [0])
    return lambda k: f"{prefix}{n + k + 1:03d}"

def _valid(it, kind):
    try:
        if kind == "carousel":
            q = it["quiz"]
            return (it["exam"] in ("TYT", "AYT") and 4 <= len(it["slides"]) <= 6 and len(q["options"]) == 5
                    and 0 <= q["answer"] < 5 and all(s.get("h") for s in it["slides"]) and it["title"])
        n = 5
        return it["exam"] in ("TYT", "AYT") and len(it["options"]) == n and 0 <= it["answer"] < n and it["q"]
    except (KeyError, TypeError):
        return False

def _verify(items, kind):
    if not items: return []
    prompt = (f"Aşağıdaki YKS içeriklerini bağımsız bir öğretmen gibi tek tek kontrol et. Her öğe için doğru cevap "
              f"indeksi gerçekten doğru mu, birden fazla doğru şık var mı, bilgi hatası var mı?\n"
              f"Sorunlu olanların id'lerini JSON dizisi olarak döndür (ör. [\"x001\"]). Sorun yoksa [] döndür.\n\n"
              f"{json.dumps(items, ensure_ascii=False)}")
    bad = set(_json(_call(prompt, 4000)))
    return [it for it in items if it["id"] not in bad]

def generate(kind: str, count: int):
    files = {"carousel": "carousels.json", "video": "quiz_videos.json", "story": "stories.json"}
    bank = load_json(CONTENT / files[kind], [])
    nid = _next_id(bank, {"carousel": "c", "video": "v", "story": "s"}[kind])
    example = json.dumps(bank[0], ensure_ascii=False) if bank else ""
    what = {"carousel": "kaydırmalı Instagram postu (konu özeti: 5 bilgi slaytı + 5 şıklı bir soru)",
            "video": "10 saniyelik soru videosu için 5 şıklı soru",
            "story": "Instagram hikâyesi için 5 şıklı (A–E) kısa soru (soru en fazla ~90 karakter)"}[kind]
    prompt = (f"{count} adet {what} üret. Dersleri dengeli dağıt (TYT: {', '.join(SUBJECTS_TYT)}; "
              f"AYT: {', '.join(SUBJECTS_AYT)}). Şu konulardan/sorulardan farklı olsun:\n"
              f"{json.dumps(_existing_questions(), ensure_ascii=False)}\n\nŞema örneği:\n{example}\n\n{RULES}")
    items = [it for it in _json(_call(prompt)) if _valid(it, kind)]
    for k, it in enumerate(items): it["id"] = nid(k)
    ok = _verify(items, kind)
    bank.extend(ok)
    save_json(CONTENT / files[kind], bank)
    print(f"{kind}: {len(ok)}/{count} yeni içerik eklendi")

def topup(days_left: int):
    cfg = config()["content"]
    if not cfg.get("auto_generate") or not os.environ.get("ANTHROPIC_API_KEY"):
        print("Otomatik üretim kapalı ya da ANTHROPIC_API_KEY yok; atlandı."); return
    if days_left >= cfg.get("min_days_left", 7):
        print(f"{days_left} günlük içerik var, üretime gerek yok."); return
    n = cfg.get("generate_days", 14)
    generate("carousel", n); generate("video", n); generate("story", n * 4)
