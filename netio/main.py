"""Netio Instagram pipeline CLI.

  python -m netio.main prepare --slot noon            # render media for a slot into site/ + manifest
  python -m netio.main publish --slot noon            # wait until slot time, publish via Graph API, update state
  python -m netio.main preview --date 2026-10-16      # render a whole day locally (nothing is posted)
  python -m netio.main status                         # what's next, how many days of content left
  python -m netio.main whoami                         # check token -> prints IG user id & username
  python -m netio.main refresh-token                  # print a refreshed long-lived token
  python -m netio.main topup                          # generate new content with Claude API if bank is low
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from . import captions, carousel, story, video
from .common import CONTENT, OUT, ROOT, STATE_DIR, config, load_json, save_json

SITE = ROOT / "site"
STATE = STATE_DIR / "state.json"
SLOTS = ["story1", "noon", "story2", "afternoon", "story3", "story4"]

def tz():
    return ZoneInfo(config()["schedule"]["timezone"])

def now_local():
    return dt.datetime.now(tz())

def slot_time(date: dt.date, slot: str) -> dt.datetime:
    sc = config()["schedule"]
    hhmm = sc["slots"][slot] if slot in ("noon", "afternoon") else sc["stories"][int(slot[-1]) - 1]
    h, m = map(int, hhmm.split(":"))
    return dt.datetime(date.year, date.month, date.day, h, m, tzinfo=tz())

# ------------------------------------------------------------------ state & bank
def load_state():
    return load_json(STATE, {"pointers": {"carousel": 0, "video": 0, "story": 0, "ad": 0},
                             "last_story": None, "posted": {}, "log": []})

def bank(kind):
    return load_json(CONTENT / {"carousel": "carousels.json", "video": "quiz_videos.json", "story": "stories.json"}[kind], [])

def pick(kind, state, peek=0):
    items = bank(kind)
    i = state["pointers"][kind] + peek
    if i >= len(items):
        if not config()["content"].get("recycle_when_empty", True):
            raise SystemExit(f"{kind} bankası bitti.")
        i %= len(items)
    return items[i]

def ads():
    return sorted((ROOT / "assets" / "ads").glob("*.mp4"))

def day_plan(date: dt.date) -> dict:
    sc = config()["schedule"]
    idx = (date - dt.date.fromisoformat(str(sc["start_date"]))).days
    noon, aft = ("carousel", "video") if idx % 2 == 0 else ("video", "carousel")
    plan = {"noon": noon, "afternoon": aft}
    if date.weekday() == sc.get("weekly_ad_weekday", 6) and ads():
        plan["noon" if noon == "video" else "afternoon"] = "ad"
    for k in range(1, 5): plan[f"story{k}"] = "story"
    return plan

def days_left(state) -> int:
    c = len(bank("carousel")) - state["pointers"]["carousel"]
    v = len(bank("video")) - state["pointers"]["video"]
    s = (len(bank("story")) - state["pointers"]["story"]) // 4
    return max(0, min(c, v, s))

def auto_slot(now=None):
    now = now or now_local()
    best = None
    for s in SLOTS:
        delta = (slot_time(now.date(), s) - now).total_seconds() / 60
        if -90 <= delta <= 40 and (best is None or abs(delta) < abs(best[1])):
            best = (s, delta)
    if not best:
        raise SystemExit(f"Şu an ({now:%H:%M}) için planlı bir slot yok.")
    return best[0]

# ------------------------------------------------------------------ prepare
def prepare(slot: str, date: dt.date, out_root: Path, state=None) -> dict:
    state = state or load_state()
    kind = day_plan(date)[slot]
    work = OUT / "work"
    folder = out_root / date.isoformat() / slot
    if folder.exists(): shutil.rmtree(folder)
    folder.mkdir(parents=True)
    m = {"date": date.isoformat(), "slot": slot, "kind": kind, "files": []}
    if kind == "carousel":
        it = pick("carousel", state)
        paths = carousel.render(it, folder)
        m.update(item_id=it["id"], caption=captions.carousel(it), files=[p.name for p in paths])
    elif kind == "video":
        it = pick("video", state)
        p = video.render(it, folder / f"{it['id']}.mp4", work)
        m.update(item_id=it["id"], caption=captions.quiz_video(it), files=[p.name], thumb_offset_ms=9000)
    elif kind == "ad":
        lst = ads(); a = lst[state["pointers"]["ad"] % len(lst)]
        shutil.copy(a, folder / a.name)
        m.update(item_id=a.stem, caption=captions.ad(a.stem), files=[a.name], thumb_offset_ms=3000)
    else:
        n = int(slot[-1])
        it = pick("story", state)
        q = story.render_question(it, folder / f"{it['id']}_1_soru.jpg", n, today=date)
        a = story.render_answer(it, folder / f"{it['id']}_2_cevap.jpg", n)
        m.update(item_id=it["id"], files=[q.name, a.name], story_item=it)
    save_json(folder / "manifest.json", m)
    return m

# ------------------------------------------------------------------ publish
def wait_public(urls, timeout=600):
    t0 = time.time()
    for u in urls:
        while True:
            try:
                r = requests.head(u, timeout=20, allow_redirects=True)
                if r.status_code == 200: break
            except requests.RequestException:
                pass
            if time.time() - t0 > timeout:
                raise SystemExit(f"Medya herkese açık olmadı: {u}")
            time.sleep(10)

def publish(slot: str, date: dt.date, base_url: str, dry_run=False, wait_until=True):
    from .publisher import Instagram
    folder = SITE / date.isoformat() / slot
    m = load_json(folder / "manifest.json")
    if not m: raise SystemExit("Manifest yok: önce 'prepare' çalıştır.")
    state = load_state()
    if state["posted"].get(m["date"], {}).get(slot):
        print(f"{m['date']} {slot} zaten paylaşılmış, atlanıyor."); return
    base = base_url.rstrip("/")
    urls = [f"{base}/{m['date']}/{slot}/{f}" for f in m["files"]]
    if not dry_run: wait_public(urls)
    if wait_until:
        target = slot_time(date, slot)
        secs = (target - now_local()).total_seconds()
        if 0 < secs < 3 * 3600:
            print(f"Paylaşım saatine {int(secs)} sn var, bekleniyor…"); time.sleep(secs)
    ig = Instagram(dry_run=dry_run)
    if m["kind"] == "carousel": mid = ig.post_carousel(urls, m["caption"])
    elif m["kind"] in ("video", "ad"): mid = ig.post_reel(urls[0], m["caption"], m.get("thumb_offset_ms", 9000))
    else:
        ids = []
        for k, u in enumerate(urls):          # question first, answer right after (tap to reveal)
            ids.append(ig.post_story_image(u))
            if k < len(urls) - 1 and not dry_run: time.sleep(8)
        mid = ",".join(ids)
    print(f"Paylaşıldı: {m['kind']} {m['item_id']} -> {mid}")
    if dry_run: return
    # advance state
    k = {"carousel": "carousel", "video": "video", "ad": "ad", "story": "story"}[m["kind"]]
    state["pointers"][k] += 1
    if m["kind"] == "story": state["last_story"] = m["story_item"]
    state["posted"].setdefault(m["date"], {})[slot] = {"kind": m["kind"], "item": m["item_id"], "media_id": mid,
                                                       "at": now_local().isoformat(timespec="seconds")}
    cutoff = (date - dt.timedelta(days=40)).isoformat()
    state["posted"] = {d: v for d, v in state["posted"].items() if d >= cutoff}
    save_json(STATE, state)

# ------------------------------------------------------------------ commands
def cmd_preview(date: dt.date):
    state = json.loads(json.dumps(load_state()))
    out = OUT / "preview"
    for slot in SLOTS:
        m = prepare(slot, date, out, state)
        k = {"carousel": "carousel", "video": "video", "ad": "ad", "story": "story"}[m["kind"]]
        state["pointers"][k] += 1
        if m["kind"] == "story": state["last_story"] = m["story_item"]
        print(f"{slot:10s} {slot_time(date, slot):%H:%M}  {m['kind']:8s} {m['item_id']}")
    print(f"Önizleme: {out / date.isoformat()}")

def cmd_status():
    st = load_state(); today = now_local().date()
    print(f"Kalan içerik: ~{days_left(st)} gün")
    for k in ("carousel", "video", "story"):
        print(f"  {k}: {st['pointers'][k]}/{len(bank(k))}")
    for d in range(3):
        date = today + dt.timedelta(days=d)
        print(date, day_plan(date))

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prepare", "publish", "preview", "status", "whoami", "refresh-token", "topup", "slot"])
    ap.add_argument("--slot", default="auto")
    ap.add_argument("--date", default=None)
    ap.add_argument("--base-url", default=os.environ.get("PAGES_URL") or config()["storage"].get("public_base_url"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-wait", action="store_true")
    a = ap.parse_args(argv)
    now = now_local()
    slot = date = None
    if a.cmd in ("prepare", "publish", "slot"):
        slot = auto_slot(now) if a.slot == "auto" else a.slot
        date = dt.date.fromisoformat(a.date) if a.date else now.date()
    if a.cmd == "slot":
        print(slot)
    elif a.cmd == "prepare":
        m = prepare(slot, date, SITE); print(json.dumps({k: v for k, v in m.items() if k != "story_item"}, ensure_ascii=False))
    elif a.cmd == "publish":
        if not a.base_url and not a.dry_run: raise SystemExit("PAGES_URL / --base-url gerekli.")
        publish(slot, date, a.base_url or "https://example.invalid", dry_run=a.dry_run, wait_until=not a.no_wait)
    elif a.cmd == "preview":
        cmd_preview(dt.date.fromisoformat(a.date) if a.date else now.date())
    elif a.cmd == "status":
        cmd_status()
    elif a.cmd == "whoami":
        from .publisher import Instagram
        ig = Instagram(user_id=os.environ.get("IG_USER_ID") or "me")
        me = ig.whoami(); print("Hesap:", me)
        if ig.user_id == "me" and me.get("user_id"): ig.user_id = str(me["user_id"])
        print("IG_USER_ID olarak bunu kaydet:", ig.user_id)
        print("Paylaşım kotası:", ig.publishing_limit())
    elif a.cmd == "refresh-token":
        from .publisher import refresh_long_lived_token
        tok = refresh_long_lived_token(os.environ["IG_ACCESS_TOKEN"])
        print(f"::add-mask::{tok['access_token']}")
        Path(os.environ.get("NEW_TOKEN_FILE", "new_token.txt")).write_text(tok["access_token"])
        print(f"Yeni token alındı, {tok.get('expires_in', 0) // 86400} gün geçerli.")
    elif a.cmd == "topup":
        from .generate_content import topup
        topup(days_left(load_state()))

if __name__ == "__main__":
    main()
