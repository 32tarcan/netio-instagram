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
    hooks = ["Kaydır, son slaytta seni bir soru bekliyor 👉", "Kaydır ve sonunda kendini dene 👉",
             "Kaydır, son slayttaki soruyu çözebilecek misin? 👉"]
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
