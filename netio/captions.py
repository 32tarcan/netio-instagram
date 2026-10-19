"""Instagram caption builder."""
from __future__ import annotations

import random

from .common import config

def _tags(subject: str, exam: str, seed: str) -> str:
    h = config()["hashtags"]
    tags = list(h["base"]) + list(h["per_subject"].get(subject, []))
    tags.append("#" + exam.lower())
    seen, out = set(), []
    for t in tags:
        if t not in seen:
            seen.add(t); out.append(t)
    random.Random(seed).shuffle(out)
    return " ".join(out[:15])

def _cta() -> str:
    b = config()["brand"]
    return f"{b['cta']} 👉 @{b['instagram_handle']}"

def carousel(item: dict) -> str:
    hooks = ["Notları kaydır, 4. sayfadaki soruyu çözebilecek misin? 👉 Cevap son sayfada.",
             "Konuyu 1 dakikada tekrar et 👉 4. sayfada bir soru var, cevabı son sayfada!",
             "Kaydır ve kendini dene 👉 Soru 4. sayfada, çözüm son sayfada."]
    h = random.Random(item["id"]).choice(hooks)
    return (f"📌 {item['title']}\n\n{item.get('hook', '')}\n\n{h}\n"
            f"Cevabını yorumlara yaz, kaydetmeyi unutma! 🔖\n\n{_cta()}\n.\n.\n"
            f"{_tags(item['subject'], item['exam'], item['id'])}")

def quiz_video(item: dict) -> str:
    hooks = ["Bu soruyu 10 saniyede çözebilir misin? ⏱️", "10 saniye, tek soru. Hazır mısın? ⏱️",
             "Süre başladı! 10 saniyede çöz bakalım ⏱️"]
    h = random.Random(item["id"]).choice(hooks)
    return (f"{h} ({item['exam']} · {item['subject']})\n\nCevabın ne? Videonun sonundan önce yorumlara yaz 👇\n"
            f"Arkadaşını etiketle, o da denesin!\n\n{_cta()}\n.\n.\n{_tags(item['subject'], item['exam'], item['id'])}")

def ad(name: str) -> str:
    b = config()["brand"]
    return (f"Sıkıcı test kitaplarını unut. TYT ve AYT'ye oyun gibi hazırlan! 🎮📚\n\n"
            f"{b['app_name']}: her konu bir ada, her ada bir zafer.\n\n{_cta()}\n.\n.\n"
            + " ".join(config()["hashtags"]["base"]))


# ------------------------------------------------------------------ TikTok
def _tt_tags(item, n=6) -> str:
    c = config().get("tiktok") or {}
    base = list(c.get("hashtags") or ["#yks", "#tyt", "#ayt", "#yks2027", "#keşfet", "#öğrenci"])
    extra = list(config()["hashtags"]["per_subject"].get(item["subject"], []))[:2]
    tags = list(dict.fromkeys(extra + base))
    return " ".join(tags[: n + len(extra)])

def tiktok_video(item: dict) -> str:
    hooks = ["10 saniyen var, çözebilir misin? ⏱️", "Bu soruyu yanlış yapan çok 👀 Sen?",
             "Süre başladı! Cevabını yorumlara yaz 👇", "YKS'de çıkabilecek tarzda bir soru, 10 saniye ⏱️"]
    h = random.Random(item["id"] + "tt").choice(hooks)
    b = config()["brand"]
    return f"{h} ({item['exam']} {item['subject']}) Her gün yeni soru: {b['app_name']} 🎯 {_tt_tags(item)}"

def tiktok_photos(item: dict) -> tuple[str, str]:
    title = f"{item['title']} 📌"[:88]
    b = config()["brand"]
    desc = (f"{item.get('hook', '')}\n\nKaydır 👉 4. fotoğraftaki soruyu çöz, cevap son fotoğrafta. "
            f"Cevabını yorumlara yaz, kaydetmeyi unutma! 🔖\n\n{b['app_name']} ile TYT-AYT'ye oyun gibi hazırlan. "
            f"{_tt_tags(item)}")
    return title, desc
