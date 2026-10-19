"""Lightweight 'is anything due?' check (stdlib only — runs before dependencies are installed).

Prints the earliest slot of today that is not yet posted and whose time window is open:
  opens  EARLY_MIN minutes before the slot time (media is prepared, then publish waits),
  closes LATE_HOURS hours after it (a late post is better than a missed one).
Prints nothing if there is nothing to do.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
EARLY_MIN = 25
LATE_HOURS = 5
ORDER = ["story1", "noon", "story2", "afternoon", "story3", "story4"]

def _config():
    txt = (ROOT / "config.yaml").read_text(encoding="utf-8")
    tz = re.search(r'timezone:\s*"([^"]+)"', txt).group(1)
    noon = re.search(r'noon:\s*"(\d\d:\d\d)"', txt).group(1)
    aft = re.search(r'afternoon:\s*"(\d\d:\d\d)"', txt).group(1)
    stories = re.findall(r'"(\d\d:\d\d)"', re.search(r'stories:\s*\[([^\]]*)\]', txt).group(1))
    times = {"noon": noon, "afternoon": aft, **{f"story{i + 1}": s for i, s in enumerate(stories)}}
    tt = re.search(r'^tiktok:\s*\n((?:[ #].*\n?)+)', txt, re.M)
    if tt and re.search(r'^\s+enabled:\s*true', tt.group(1), re.M):
        times.update(dict(re.findall(r'^\s+(tt\d):\s*"(\d\d:\d\d)"', tt.group(1), re.M)))
    return tz, times

def due_all(now: dt.datetime | None = None) -> list[str]:
    """Every unposted slot of today whose window is open, in time order. One run handles them all,
    so a missed trigger is caught up by the next one."""
    tzname, times = _config()
    tz = ZoneInfo(tzname)
    now = now or dt.datetime.now(tz)
    state = json.loads((ROOT / "state" / "state.json").read_text(encoding="utf-8"))
    posted = state.get("posted", {}).get(now.date().isoformat(), {})
    out = []
    for slot in sorted(times, key=lambda s: times[s]):
        if slot in posted:
            continue
        h, m = map(int, times[slot].split(":"))
        t = dt.datetime(now.year, now.month, now.day, h, m, tzinfo=tz)
        if t - dt.timedelta(minutes=EARLY_MIN) <= now <= t + dt.timedelta(hours=LATE_HOURS):
            out.append(slot)
    return out

def due(now: dt.datetime | None = None) -> str:
    d = due_all(now)
    return d[0] if d else ""

if __name__ == "__main__":
    print(" ".join(due_all()))
