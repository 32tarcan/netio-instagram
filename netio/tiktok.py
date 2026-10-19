"""TikTok Content Posting API (official API, OAuth — no password login).

Docs: https://developers.tiktok.com/doc/content-posting-api-get-started
Auth: Login Kit (web). Access tokens live 24 h, refresh tokens 365 days and may rotate:
every run refreshes, and if TikTok returns a new refresh token it is written to
$TIKTOK_NEW_REFRESH_FILE so the workflow can store it back into GitHub Secrets.

Modes (config tiktok.mode):
  draft  -> video goes to the creator's TikTok inbox / photo to drafts (MEDIA_UPLOAD);
            the creator finishes and posts it in the TikTok app (adds a sound, taps Post).
  direct -> posted straight to the profile (needs an audited app to be public).
"""
from __future__ import annotations

import math
import os
import time
from pathlib import Path

import requests

from .common import config

API = "https://open.tiktokapis.com/v2"
AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
SCOPES = "user.info.basic,video.upload,video.publish"

class TTError(RuntimeError):
    pass

def cfg() -> dict:
    c = config().get("tiktok") or {}
    return {"enabled": bool(c.get("enabled", False)), "mode": c.get("mode", "draft"),
            "privacy": c.get("privacy", "PUBLIC_TO_EVERYONE"),
            "redirect_uri": c.get("redirect_uri", "https://studio.netio-app.com/tiktok/callback/"),
            "slots": c.get("slots", {}), "hashtags": c.get("hashtags", [])}

def _keys():
    k, s = os.environ.get("TIKTOK_CLIENT_KEY", "").strip(), os.environ.get("TIKTOK_CLIENT_SECRET", "").strip()
    if not k or not s:
        raise TTError("TIKTOK_CLIENT_KEY ve TIKTOK_CLIENT_SECRET GitHub Secrets'ta olmalı.")
    return k, s

def _token_call(**params) -> dict:
    k, s = _keys()
    r = requests.post(f"{API}/oauth/token/", data={"client_key": k, "client_secret": s, **params},
                      headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=60)
    d = r.json()
    if "access_token" not in d:
        raise TTError(f"Token alınamadı: {d.get('error')} {d.get('error_description')} (log {d.get('log_id')})")
    return d

def exchange_code(code: str, redirect_uri: str | None = None) -> dict:
    return _token_call(code=code.strip(), grant_type="authorization_code",
                       redirect_uri=redirect_uri or cfg()["redirect_uri"])

def refresh(refresh_token: str | None = None) -> dict:
    rt = (refresh_token or os.environ.get("TIKTOK_REFRESH_TOKEN", "")).strip()
    if not rt:
        raise TTError("TIKTOK_REFRESH_TOKEN yok: önce TikTok'u bağla (studio sayfası → TikTok'a bağlan).")
    d = _token_call(grant_type="refresh_token", refresh_token=rt)
    if d.get("refresh_token") and d["refresh_token"] != rt:
        out = os.environ.get("TIKTOK_NEW_REFRESH_FILE")
        if out: Path(out).write_text(d["refresh_token"])
    return d

class TikTok:
    def __init__(self, access_token: str | None = None, dry_run: bool = False):
        self.dry = dry_run
        self.token = access_token or ("dry" if dry_run else refresh()["access_token"])

    def _post(self, path, body=None):
        if self.dry:
            print(f"[dry-run] POST {path} {body}")
            return {"publish_id": f"dry_{int(time.time() * 1000)}", "upload_url": None, "status": "PUBLISH_COMPLETE"}
        for attempt in range(4):
            r = requests.post(f"{API}/{path}", json=body or {}, timeout=60,
                              headers={"Authorization": f"Bearer {self.token}",
                                       "Content-Type": "application/json; charset=UTF-8"})
            d = r.json() if r.content else {}
            err = d.get("error", {})
            if err.get("code") in (None, "ok"):
                return d.get("data", {})
            if err.get("code") == "rate_limit_exceeded" or r.status_code >= 500:
                time.sleep(20 * (attempt + 1)); continue
            raise TTError(f"{path}: {err.get('code')} — {err.get('message')} (log {err.get('log_id') or err.get('logid')})")
        raise TTError(f"{path}: tekrar denemeler başarısız ({r.status_code})")

    # ------------------------------------------------------------ info
    def creator_info(self):
        return self._post("post/publish/creator_info/query/")

    def user_info(self):
        if self.dry: return {"display_name": "dry"}
        r = requests.get(f"{API}/user/info/", params={"fields": "open_id,display_name,avatar_url"},
                         headers={"Authorization": f"Bearer {self.token}"}, timeout=60)
        return r.json().get("data", {}).get("user", {})

    def status(self, publish_id):
        return self._post("post/publish/status/fetch/", {"publish_id": publish_id})

    def wait(self, publish_id, timeout=600):
        if self.dry: return "PUBLISH_COMPLETE"
        t0 = time.time()
        while True:
            st = self.status(publish_id)
            s = st.get("status")
            if s in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"): return s
            if s == "FAILED": raise TTError(f"TikTok paylaşımı başarısız: {st.get('fail_reason')}")
            if time.time() - t0 > timeout: raise TTError(f"TikTok {timeout} sn içinde bitirmedi (durum: {s})")
            time.sleep(10)

    def _privacy(self):
        want = cfg()["privacy"]
        opts = self.creator_info().get("privacy_level_options", []) if not self.dry else [want]
        if want in opts: return want
        return "SELF_ONLY" if "SELF_ONLY" in opts else (opts[0] if opts else want)

    # ------------------------------------------------------------ video
    def post_video(self, path: Path, caption: str, cover_ms=9000, mode: str | None = None):
        mode = mode or cfg()["mode"]
        size = path.stat().st_size
        chunk = size if size <= 64 * 1024 * 1024 else 10 * 1024 * 1024
        n = 1 if chunk == size else size // chunk          # TikTok: last chunk absorbs the remainder
        src = {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": chunk, "total_chunk_count": n}
        if mode == "direct":
            info = {"title": caption[:2200], "privacy_level": self._privacy(), "disable_duet": False,
                    "disable_comment": False, "disable_stitch": False, "video_cover_timestamp_ms": cover_ms,
                    "brand_content_toggle": False, "brand_organic_toggle": True}
            d = self._post("post/publish/video/init/", {"post_info": info, "source_info": src})
        else:
            d = self._post("post/publish/inbox/video/init/", {"source_info": src})
        if not self.dry:
            data = path.read_bytes()
            for i in range(n):
                a = i * chunk; b = size if i == n - 1 else a + chunk
                r = requests.put(d["upload_url"], data=data[a:b], timeout=300,
                                 headers={"Content-Type": "video/mp4", "Content-Length": str(b - a),
                                          "Content-Range": f"bytes {a}-{b - 1}/{size}"})
                if r.status_code not in (200, 201, 206):
                    raise TTError(f"Video yüklenemedi: {r.status_code} {r.text[:200]}")
        st = self.wait(d["publish_id"])
        return d["publish_id"], st

    # ------------------------------------------------------------ photos
    def post_photos(self, urls: list[str], title: str, description: str, mode: str | None = None, cover=0):
        mode = mode or cfg()["mode"]
        info = {"title": title[:90], "description": description[:4000]}
        if mode == "direct":
            info.update(privacy_level=self._privacy(), disable_comment=False, auto_add_music=True,
                        brand_content_toggle=False, brand_organic_toggle=True)
        body = {"post_info": info, "source_info": {"source": "PULL_FROM_URL", "photo_cover_index": cover,
                                                   "photo_images": urls[:35]},
                "post_mode": "DIRECT_POST" if mode == "direct" else "MEDIA_UPLOAD", "media_type": "PHOTO"}
        d = self._post("post/publish/content/init/", body)
        st = self.wait(d["publish_id"])
        return d["publish_id"], st

def authorize_url(client_key: str, state: str = "netio") -> str:
    from urllib.parse import urlencode
    return AUTH_URL + "?" + urlencode({"client_key": client_key, "scope": SCOPES, "response_type": "code",
                                       "redirect_uri": cfg()["redirect_uri"], "state": state})

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if cmd == "connect":                       # exchange the code from the callback page
            d = exchange_code(sys.argv[2])
            Path(os.environ.get("TIKTOK_NEW_REFRESH_FILE", "tt_refresh.txt")).write_text(d["refresh_token"])
            print(f"::add-mask::{d['refresh_token']}")
            t = TikTok(access_token=d["access_token"])
            u = t.user_info()
            print(f"::notice title=tiktok::Bağlandı: {u.get('display_name')} (izinler: {d.get('scope')})")
            try:
                ci = t.creator_info()
                print(f"::notice title=tiktok::@{ci.get('creator_username')} gizlilik seçenekleri: "
                      f"{ci.get('privacy_level_options')}, maks video: {ci.get('max_video_post_duration_sec')} sn")
            except Exception as e:
                print(f"::warning title=tiktok::creator_info: {e}")
        elif cmd == "whoami":
            t = TikTok()
            ci = t.creator_info()
            print(f"::notice title=tiktok::{ci.get('creator_nickname')} @{ci.get('creator_username')} "
                  f"gizlilik seçenekleri: {ci.get('privacy_level_options')}, maks video: {ci.get('max_video_post_duration_sec')} sn")
        else:
            print("kullanım: python -m netio.tiktok connect CODE | whoami")
    except Exception as e:
        print(f"::error title=tiktok::{type(e).__name__}: {str(e)[:800]}")
        raise
