"""Instagram Graph API content publishing (official API — no password login, no scraping).

Docs: https://developers.facebook.com/docs/instagram-platform/content-publishing/
Flow: create container(s) -> wait until FINISHED -> media_publish.
"""
from __future__ import annotations

import os
import time

import requests

from .common import config

class IGError(RuntimeError):
    pass

class Instagram:
    def __init__(self, token: str | None = None, user_id: str | None = None, dry_run: bool = False):
        cfg = config()["instagram"]
        host = "graph.instagram.com" if cfg.get("login_type", "instagram") == "instagram" else "graph.facebook.com"
        self.base = f"https://{host}/{cfg.get('api_version', 'v25.0')}"
        self.token = token or os.environ.get("IG_ACCESS_TOKEN", "")
        self.user_id = user_id or os.environ.get("IG_USER_ID", "")
        self.dry = dry_run
        if not self.dry and (not self.token or not self.user_id):
            raise IGError("IG_ACCESS_TOKEN ve IG_USER_ID tanımlı olmalı (GitHub Secrets).")

    # ------------------------------------------------------------ http
    def _req(self, method, path, **params):
        if self.dry:
            print(f"[dry-run] {method} {path} {({k: v for k, v in params.items() if k != 'access_token'})}")
            return {"id": f"dry_{int(time.time() * 1000)}", "status_code": "FINISHED"}
        params["access_token"] = self.token
        url = f"{self.base}/{path}"
        for attempt in range(5):
            r = requests.request(method, url, data=params if method == "POST" else None,
                                 params=params if method == "GET" else None, timeout=60)
            if r.status_code < 500 and r.status_code != 429:
                data = r.json()
                if "error" in data:
                    err = data["error"]
                    if err.get("is_transient") or err.get("code") in (1, 2, 4, 17, 32, 613):
                        time.sleep(10 * (attempt + 1)); continue
                    raise IGError(f"{err.get('type')}: {err.get('message')} (code {err.get('code')}, sub {err.get('error_subcode')})")
                return data
            time.sleep(10 * (attempt + 1))
        raise IGError(f"{method} {path} başarısız: {r.status_code} {r.text[:300]}")

    # ------------------------------------------------------------ containers
    def image_container(self, image_url, caption=None, carousel_item=False, story=False):
        p = {"image_url": image_url}
        if carousel_item: p["is_carousel_item"] = "true"
        if story: p["media_type"] = "STORIES"
        if caption: p["caption"] = caption
        return self._req("POST", f"{self.user_id}/media", **p)["id"]

    def reel_container(self, video_url, caption, thumb_offset_ms=9000, share_to_feed=True):
        p = {"media_type": "REELS", "video_url": video_url, "caption": caption,
             "share_to_feed": "true" if share_to_feed else "false", "thumb_offset": str(thumb_offset_ms)}
        return self._req("POST", f"{self.user_id}/media", **p)["id"]

    def carousel_container(self, children, caption):
        return self._req("POST", f"{self.user_id}/media", media_type="CAROUSEL",
                         children=",".join(children), caption=caption)["id"]

    def wait(self, container_id, timeout=600, every=10):
        t0 = time.time()
        while True:
            st = self._req("GET", container_id, fields="status_code,status").get("status_code")
            if st == "FINISHED": return
            if st in ("ERROR", "EXPIRED"):
                info = self._req("GET", container_id, fields="status")
                raise IGError(f"Container {container_id} {st}: {info.get('status')}")
            if time.time() - t0 > timeout:
                raise IGError(f"Container {container_id} {timeout} sn içinde hazır olmadı (durum: {st}).")
            time.sleep(every)

    def publish(self, container_id):
        return self._req("POST", f"{self.user_id}/media_publish", creation_id=container_id)["id"]

    # ------------------------------------------------------------ high level
    def post_carousel(self, image_urls, caption):
        kids = [self.image_container(u, carousel_item=True) for u in image_urls]
        for k in kids: self.wait(k, timeout=180, every=5)
        cid = self.carousel_container(kids, caption)
        self.wait(cid, timeout=180, every=5)
        return self.publish(cid)

    def post_reel(self, video_url, caption, thumb_offset_ms=9000):
        cid = self.reel_container(video_url, caption, thumb_offset_ms)
        self.wait(cid, timeout=900, every=15)
        return self.publish(cid)

    def post_story_image(self, image_url):
        cid = self.image_container(image_url, story=True)
        self.wait(cid, timeout=180, every=5)
        return self.publish(cid)

    def publishing_limit(self):
        return self._req("GET", f"{self.user_id}/content_publishing_limit", fields="quota_usage,config")

    def live_stories(self):
        """Stories currently live on the account (24 h). Used to detect stories posted by hand."""
        return self._req("GET", f"{self.user_id}/stories", fields="id,timestamp,media_type").get("data", [])

    def whoami(self):
        return self._req("GET", "me", fields="user_id,username,account_type")

def refresh_long_lived_token(token: str) -> dict:
    """Instagram Login tokens live 60 days; refresh weekly (token must be >24h old)."""
    r = requests.get("https://graph.instagram.com/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": token}, timeout=60)
    data = r.json()
    if "access_token" not in data:
        raise IGError(f"Token yenilenemedi: {data}")
    return data
