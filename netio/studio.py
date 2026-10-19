"""Netio Studio pages on GitHub Pages (studio.netio-app.com):
  /                  -> landing (what this tool is)
  /tiktok/           -> "TikTok'a bağlan" (Login Kit authorize link)
  /tiktok/callback/  -> shows the one-time code to finish the connection in GitHub Actions
The client key is public (it appears in every TikTok login URL); the secret never leaves GitHub Secrets."""
from __future__ import annotations

import html
import os
from pathlib import Path

from .tiktok import authorize_url

REPO = "32tarcan/netio-instagram"

CSS = """:root{--bg:#14121f;--card:#1f1c30;--line:#2f2b47;--ink:#f4f2ff;--mute:#a49fc4;--acc:#ffce40;--good:#3aaa58;--pri:#7c5cff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 -apple-system,system-ui,Segoe UI,Roboto,sans-serif}
main{max-width:560px;margin:0 auto;padding:32px 16px 60px}h1{font-size:26px;margin:0 0 6px}p{color:#d9d5f2}
.sub{color:var(--mute);margin:0 0 22px}.card{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:20px;margin:0 0 16px}
.btn{display:block;text-align:center;padding:15px;border-radius:14px;font-weight:700;font-size:16px;text-decoration:none;border:0;width:100%;cursor:pointer}
.pri{background:var(--pri);color:#fff}.sec{background:var(--line);color:var(--ink)}
code{display:block;background:#272340;border-radius:12px;padding:14px;word-break:break-all;font-size:14px;margin:10px 0}
ol{padding-left:20px;color:#d9d5f2}li{margin:6px 0}a{color:var(--acc)}.foot{color:var(--mute);font-size:13px;margin-top:24px}
.err{color:#ff8a8a}"""

def _page(title, body):
    return (f'<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>'
            f'<meta name="robots" content="noindex"><style>{CSS}</style></head><body><main>{body}'
            f'<p class="foot">Netio · <a href="https://netio-app.com/gizlilik-politikasi/">Gizlilik</a> · '
            f'<a href="https://netio-app.com/kullanim-kosullari/">Kullanım koşulları</a></p></main></body></html>')

def build(site: Path) -> None:
    key = os.environ.get("TIKTOK_CLIENT_KEY", "").strip()
    (site / "tiktok" / "callback").mkdir(parents=True, exist_ok=True)
    (site / "index.html").write_text(_page("Netio Studio", """
<h1>Netio Studio</h1><p class="sub">Netio'nun kendi sosyal medya hesapları için içerik aracı.</p>
<div class="card"><p>Netio, TYT-AYT'ye oyun gibi hazırlatan bir soru çözme uygulaması. Bu araç, Netio'nun eğitim
içeriklerini (soru videoları ve konu özetleri) yalnızca Netio'nun kendi Instagram ve TikTok hesaplarında paylaşmak için kullanılır.</p>
<a class="btn sec" href="panel/">Hikâye paneli</a><br><a class="btn pri" href="tiktok/">TikTok bağlantısı</a></div>"""), encoding="utf-8")
    if key:
        link = html.escape(authorize_url(key))
        connect = f'<a class="btn pri" href="{link}">TikTok\'a bağlan</a>'
    else:
        connect = '<p class="err">TikTok anahtarı henüz eklenmemiş (TIKTOK_CLIENT_KEY).</p>'
    (site / "tiktok" / "index.html").write_text(_page("Netio · TikTok", f"""
<h1>TikTok bağlantısı</h1><p class="sub">Netio'nun TikTok hesabını içerik aracına bağlar.</p>
<div class="card"><ol><li>Aşağıdaki düğmeye bas, TikTok'ta Netio hesabınla giriş yap ve <b>izin ver</b>.</li>
<li>Açılan sayfadaki <b>kodu kopyala</b> ve oradaki adımı izle (1 dakika).</li></ol>{connect}
<p class="sub" style="margin-top:14px">İstenen izinler: profil bilgisi (ad, avatar), TikTok'a video/fotoğraf yükleme ve paylaşma.
Şifren bu araçla paylaşılmaz; bağlantıyı istediğin an TikTok → Ayarlar → Güvenlik → İzinler'den kaldırabilirsin.</p></div>"""), encoding="utf-8")
    wf = f"https://github.com/{REPO}/actions/workflows/tiktok-connect.yml"
    (site / "tiktok" / "callback" / "index.html").write_text(_page("Netio · TikTok bağlandı", f"""
<h1 id="h">TikTok'tan dönüş</h1><div class="card" id="ok" hidden>
<p>İzin verildi. Bağlantıyı bitirmek için bu kodu sisteme gir (kod birkaç dakika geçerli):</p>
<code id="code"></code><button class="btn pri" id="copy">Kodu kopyala</button>
<ol><li><a href="{wf}" target="_blank">Bu sayfayı aç</a> → sağdaki <b>Run workflow</b>.</li>
<li>Kodu kutuya yapıştır → yeşil <b>Run workflow</b>.</li><li>Bitti. 1 dk sonra TikTok bağlanmış olur.</li></ol></div>
<div class="card" id="bad" hidden><p class="err" id="msg"></p><a class="btn sec" href="../">Tekrar dene</a></div>
<script>
const q=new URLSearchParams(location.search),c=q.get('code'),e=q.get('error');
if(c){{document.getElementById('ok').hidden=false;document.getElementById('code').textContent=c;
 document.getElementById('h').textContent='Neredeyse bitti';
 document.getElementById('copy').onclick=async ev=>{{try{{await navigator.clipboard.writeText(c);ev.target.textContent='Kopyalandı ✓'}}catch(_){{prompt('Kopyala:',c)}}}};}}
else{{document.getElementById('bad').hidden=false;document.getElementById('msg').textContent=
 e?('TikTok izin vermedi: '+e+' '+(q.get('error_description')||'')):'Kod bulunamadı. TikTok bağlantısına baştan başla.';}}
</script>"""), encoding="utf-8")
