"""'Senin sıran' panel: a mobile page on GitHub Pages (…/panel/) listing today's and tomorrow's
quiz-sticker stories. Instagram's API cannot add stickers, so these are posted by hand (~1 min):
save image -> Instagram story -> TEST (quiz) sticker -> paste question & 4 options -> share.
The pipeline then sees the story through the API and posts the answer frame automatically;
if nothing is posted within the grace period, the sticker-less version is posted instead."""
from __future__ import annotations

import datetime as dt
import html
import json
from pathlib import Path

from . import story
from .common import LETTERS, config, sticker_options

STICKER_Q = "Doğru cevap hangisi?"

def settings() -> dict:
    s = config().get("stories_interactive") or {}
    return {"enabled": bool(s.get("enabled", False)), "grace_min": int(s.get("grace_min", 45)),
            "lookback_min": int(s.get("lookback_min", 90))}

def upcoming(state, now: dt.datetime, slot_time, bank_items, late_hours=5):
    """[(date, slot, n, item, status)] for today + tomorrow. Items follow the story pointer in slot order,
    exactly the way the posting job will consume them."""
    out, k = [], 0
    ptr = state["pointers"]["story"]
    for d in (now.date(), now.date() + dt.timedelta(days=1)):
        for n in range(1, 5):
            slot = f"story{n}"
            done = state.get("posted", {}).get(d.isoformat(), {}).get(slot)
            t = slot_time(d, slot)
            if done:
                status = "manual" if done.get("mode") == "manual" else "auto"
                it = next((x for x in bank_items if x["id"] == done.get("item")), None)
                if d == now.date() and it: out.append((d, slot, n, it, status))
                continue
            if now > t + dt.timedelta(hours=late_hours):
                continue          # missed, the job will skip it (pointer not consumed)
            it = bank_items[(ptr + k) % len(bank_items)]; k += 1
            out.append((d, slot, n, it, "todo"))
    return out

def build(site: Path, state, now: dt.datetime, slot_time, bank_items) -> Path:
    cfg = settings()
    folder = site / "panel"; folder.mkdir(parents=True, exist_ok=True)
    cards = []
    for d, slot, n, it, status in upcoming(state, now, slot_time, bank_items):
        img = f"{d.isoformat()}_{slot}_{it['id']}.jpg"
        story.render_interactive(it, folder / img, n, today=d)
        opts, ans = sticker_options(it)
        t = slot_time(d, slot)
        cards.append({"date": d.isoformat(), "day": "Bugün" if d == now.date() else "Yarın", "time": f"{t:%H:%M}",
                      "deadline": f"{t + dt.timedelta(minutes=cfg['grace_min']):%H:%M}",
                      "from": f"{t - dt.timedelta(minutes=cfg['lookback_min']):%H:%M}",
                      "status": status, "img": img, "q": it["q"], "subject": f"{it['exam']} · {it['subject']}",
                      "opts": opts, "ans": ans})
    (folder / "index.html").write_text(_page(cards, now), encoding="utf-8")
    return folder

def _esc(s): return html.escape(str(s), quote=True)

def _card(c):
    badge = {"todo": ("Sıra sende", "todo"), "manual": ("Sen attın ✓", "ok"), "auto": ("Otomatik gitti", "auto")}[c["status"]]
    copies = [("Çıkartma sorusu", STICKER_Q)] + [(f"Şık {LETTERS[i]}" + ("  ✓ doğru" if i == c["ans"] else ""), o)
                                                  for i, o in enumerate(c["opts"])]
    rows = "".join(
        f'<div class="cp{" good" if "doğru" in lab else ""}"><div><small>{_esc(lab)}</small><b>{_esc(val)}</b></div>'
        f'<button data-copy="{_esc(val)}">Kopyala</button></div>' for lab, val in copies)
    steps = "" if c["status"] != "todo" else f"""
      <ol>
        <li><b>Görseli kaydet</b>'e bas (Fotoğraflar'a gider).</li>
        <li><b>Instagram'ı aç</b> → Hikâye → kaydettiğin görseli seç.</li>
        <li>Çıkartma simgesi → <b>TEST</b> (Quiz) çıkartması.</li>
        <li>Soruyu ve 4 şıkkı aşağıdan kopyalayıp yapıştır. <b>Doğru şıkkı ({LETTERS[c['ans']]}) işaretle.</b></li>
        <li>Çıkartmayı kesik çizgili kutunun üstüne koy. Müzik ekleme. <b>Paylaş.</b></li>
        <li>Bu kadar. Sistem hikâyeni görür, arkasından cevap + açıklama karesini kendisi atar.</li>
      </ol>
      <p class="note">{c['from']}–{c['deadline']} arasında at. {c['deadline']}'e kadar atmazsan çıkartmasız sürüm otomatik gider.</p>"""
    acts = "" if c["status"] != "todo" else f"""
      <div class="acts"><button class="pri" data-save="{_esc(c['img'])}">Görseli kaydet</button>
      <a class="sec" href="instagram://story-camera">Instagram'ı aç</a></div>"""
    return f"""
    <section class="card {badge[1]}" id="{_esc(c['date'] + c['time'])}">
      <header><div><span class="when">{c['day']} {c['time']}</span><span class="subj">{_esc(c['subject'])}</span></div>
      <span class="badge {badge[1]}">{badge[0]}</span></header>
      <p class="q">{_esc(c['q'])}</p>
      {"" if c["status"] != "todo" else f'<img src="{_esc(c["img"])}" alt="Hikâye görseli" loading="lazy">'}
      {acts}{steps}
      {"" if c["status"] != "todo" else f'<div class="copies">{rows}</div>'}
    </section>"""

def _page(cards, now):
    todo = sum(1 for c in cards if c["status"] == "todo" and c["day"] == "Bugün")
    body = "".join(_card(c) for c in cards) or "<p class='empty'>Şu an bekleyen hikâye yok.</p>"
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Netio · Senin sıran</title>
<meta name="robots" content="noindex">
<style>
:root{{--bg:#14121f;--card:#1f1c30;--line:#2f2b47;--ink:#f4f2ff;--mute:#a49fc4;--acc:#ffce40;--good:#3aaa58;--pri:#7c5cff}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.45 -apple-system,system-ui,Segoe UI,Roboto,sans-serif}}
main{{max-width:560px;margin:0 auto;padding:20px 16px 60px}}
h1{{font-size:22px;margin:4px 0 2px}}.sub{{color:var(--mute);margin:0 0 18px;font-size:14px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:16px;margin:0 0 18px}}
.card.todo{{border-color:var(--pri)}}.card.ok,.card.auto{{opacity:.7}}
header{{display:flex;justify-content:space-between;align-items:center;gap:8px}}
.when{{font-weight:700;font-size:18px;margin-right:8px}}.subj{{color:var(--mute);font-size:13px}}
.badge{{font-size:12px;font-weight:700;padding:4px 10px;border-radius:99px;white-space:nowrap}}
.badge.todo{{background:var(--pri)}}.badge.ok{{background:var(--good)}}.badge.auto{{background:var(--line)}}
.q{{margin:10px 0;font-weight:600}}img{{width:100%;max-width:300px;display:block;margin:6px auto 12px;border-radius:14px}}
.acts{{display:flex;gap:10px;margin:0 0 10px}}.acts>*{{flex:1;text-align:center;padding:13px;border-radius:14px;font-weight:700;font-size:15px;border:0;text-decoration:none}}
.pri{{background:var(--pri);color:#fff}}.sec{{background:var(--line);color:var(--ink)}}
ol{{padding-left:20px;margin:8px 0;color:#d9d5f2;font-size:14.5px}}li{{margin:4px 0}}
.note{{font-size:13px;color:var(--acc);margin:6px 0 12px}}
.cp{{display:flex;justify-content:space-between;align-items:center;gap:10px;background:#272340;border-radius:12px;padding:9px 10px 9px 12px;margin:6px 0}}
.cp.good{{outline:2px solid var(--good)}}.cp small{{display:block;color:var(--mute);font-size:11.5px}}.cp b{{font-size:15px;word-break:break-word}}
.cp button{{background:#3a355c;color:var(--ink);border:0;border-radius:10px;padding:8px 12px;font-weight:600;flex:none}}
.cp button.done{{background:var(--good)}}.empty{{color:var(--mute)}}
</style></head><body><main>
<h1>Senin sıran</h1>
<p class="sub">Bugün {todo} anketli hikâye bekliyor · güncellendi {now:%d.%m %H:%M}</p>
{body}
</main><script>
document.addEventListener('click',async e=>{{
  const c=e.target.closest('[data-copy]');
  if(c){{try{{await navigator.clipboard.writeText(c.dataset.copy);c.textContent='Kopyalandı';c.classList.add('done');
    setTimeout(()=>{{c.textContent='Kopyala';c.classList.remove('done')}},1500)}}catch(_){{prompt('Kopyala:',c.dataset.copy)}}return}}
  const s=e.target.closest('[data-save]');
  if(s){{const url=s.dataset.save;
    try{{const b=await (await fetch(url)).blob();const f=new File([b],url,{{type:'image/jpeg'}});
      if(navigator.canShare&&navigator.canShare({{files:[f]}})){{await navigator.share({{files:[f]}});return}}}}catch(_){{}}
    const a=document.createElement('a');a.href=url;a.download=url;document.body.appendChild(a);a.click();a.remove();}}
}});
</script></body></html>"""
