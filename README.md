# Netio Instagram Otomatik İçerik Pipeline'ı

Her gün kendiliğinden TYT/AYT içeriği üretir ve Netio'nun Instagram hesabından paylaşır.
Sunucu gerekmez; her şey ücretsiz **GitHub Actions** üzerinde çalışır.

## Günlük akış (Türkiye saati)

| Saat  | Çift günler          | Tek günler           |
|-------|----------------------|----------------------|
| 10:00 | Hikâye (soru 1/4 + cevap) | Hikâye (soru 1/4 + cevap) |
| 12:00 | **Kaydırmalı post**  | **Soru videosu (Reels)** |
| 14:00 | Hikâye (soru 2/4 + cevap) | Hikâye (soru 2/4 + cevap) |
| 16:00 | **Soru videosu (Reels)** | **Kaydırmalı post** |
| 19:00 | Hikâye (soru 3/4 + cevap) | Hikâye (soru 3/4 + cevap) |
| 21:30 | Hikâye (soru 4/4 + cevap) | Hikâye (soru 4/4 + cevap) |

* Pazar günleri o günün video slotunda soru videosu yerine `assets/ads/` içindeki marka reklamı paylaşılır.
* Her hikâye saatinde iki kare paylaşılır: A–E şıklı soru ("Cevap için dokun →") ve hemen ardından cevap karesi. Takipçi dokunarak cevabı görür.
* **Kaydırmalı post (8 slayt, doğal defter görünümü):** masadaki bir ders defterine el yazısıyla alınmış notlar. Kapak → 2 not sayfası → **4. sayfada masadaki telefonda Netio açık ve o konunun sorusu ekranda** (doğal reklam) → 3 not sayfası → son sayfada kırmızı kalemle çözüm.
* **Soru videosu (20 sn):** "Bu soruyu 10 saniyede çözebilir misin?" → geri sayım → cevap → Netio tanıtımı.
  Her videonun müziği ve efekt sesleri farklıdır (içeriğe göre değişen tohumla üretilir).

## Nasıl çalışır?

1. Paylaşım saatinden ~20 dk önce GitHub Actions uyanır.
2. Sıradaki içeriği `content/` bankasından alır, görseli/videoyu üretir.
3. Dosyaları GitHub Pages'e yükler (Instagram medyayı herkese açık bir adresten çeker).
4. Tam saatinde **Instagram Graph API** (resmî API) ile paylaşır.
5. Ne paylaşıldığını `state/state.json` dosyasına yazar; aynı içerik iki kez paylaşılmaz.

Şifre ile giriş yapan bot **kullanılmaz**; bu yöntem Instagram kurallarına aykırıdır ve hesabı riske atar.
Sadece Meta'nın verdiği erişim token'ı kullanılır.

## Kurulum (bir kez, ~20 dk)

### 1) Instagram hesabını profesyonel yap
Instagram → Ayarlar → Hesap türü ve araçlar → **Profesyonel hesaba geç** (İşletme ya da İçerik Üreticisi).

### 2) GitHub deposu
1. github.com'da yeni bir depo aç (ör. `netio-instagram`). **Public** olmalı: GitHub Pages ücretsiz planda yalnızca açık depolarda çalışır.
   Kodlar herkese açık olur ama token'lar **Secrets** içinde gizli kalır.
2. Bu klasördeki tüm dosyaları depoya yükle.
3. Depo → **Settings → Pages → Build and deployment → Source: GitHub Actions**.

### 3) Meta (Instagram API) erişim token'ı
1. https://developers.facebook.com → **My Apps → Create App** → kullanım amacı olarak Instagram'ı ya da "Other → Business" seç.
2. Uygulamaya **Instagram** ürününü ekle → **API setup with Instagram login**.
3. "Generate access tokens" bölümünde Instagram hesabını ekle ve izin ver.
   Gerekli izinler: `instagram_business_basic`, `instagram_business_content_publish`.
4. Çıkan **access token**'ı kopyala. Bu 60 gün geçerli uzun ömürlü bir token'dır; pipeline onu her hafta otomatik yeniler.
5. Aynı ekranda görünen **Instagram User ID**'yi not al. Göremezsen önce sadece `IG_ACCESS_TOKEN` secret'ını ekle,
   sonra **Actions → Bağlantıyı kontrol et → Run workflow** çalıştır; çıktıda kaydetmen gereken ID yazar.

> Uygulama "Development" modunda kalabilir. Kendi hesabın uygulamada rol sahibi olduğu sürece paylaşım çalışır.

### 4) GitHub Secrets
Depo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret              | Ne?                                                                 | Zorunlu |
|---------------------|----------------------------------------------------------------------|---------|
| `IG_ACCESS_TOKEN`   | 3. adımdaki token                                                    | Evet    |
| `IG_USER_ID`        | Instagram User ID                                                    | Evet    |
| `GH_PAT`            | GitHub → Settings → Developer settings → Fine-grained token, bu depo için **Secrets: Read and write** izinli. Token'ı haftalık yenileyip kaydetmek için. | Evet |
| `ANTHROPIC_API_KEY` | Claude API anahtarı; içerik bankası azalınca yenisini otomatik üretir | Hayır   |

### 5) `config.yaml`
* `brand.instagram_handle`: Instagram kullanıcı adın.
* `schedule.start_date`: ilk paylaşım günü.
* `brand.cta`: uygulama yayınlanınca "Netio App Store'da! Link profilde." gibi değiştir.
* `exam_date`: YKS tarihi açıklanınca yaz; hikâyelerde geri sayım çıkar.

### 6) Test
1. **Actions → Günü önizle → Run workflow**: bir günün tüm görsellerini ve videosunu üretir, "Artifacts" kısmından indirip bakabilirsin. Hiçbir şey paylaşılmaz.
2. **Actions → Instagram paylaşımı → Run workflow** (`dry_run` işaretli): her şey çalışır ama Instagram'a gönderilmez.
3. Aynısını `dry_run` işaretsiz çalıştırırsan seçtiğin slot hemen paylaşılır.

Bundan sonra hiçbir şey yapman gerekmez; zamanlanmış görevler her gün kendiliğinden çalışır.
Bir paylaşım hata verirse GitHub sana e-posta gönderir.

## İçerik bankası

`content/` klasöründe 14 günlük elle hazırlanmış içerik var: 14 kaydırmalı post, 14 soru videosu, 56 hikâye sorusu.

* `ANTHROPIC_API_KEY` tanımlıysa, banka 7 günün altına düşünce her pazartesi Claude ile 14 günlük yeni içerik üretilir.
  Her içerik ikinci bir kontrol turundan geçer; şüpheli cevaplar elenir.
  Yapay zekâ üretimi olduğu için ara sıra `content/*.json` dosyalarına göz atman önerilir.
* Anahtar yoksa banka bitince eski içerikler başa dönerek yeniden kullanılır.
* Kendi içeriğini eklemek için JSON dosyalarına aynı yapıda yeni öğeler ekle.
* Yeni reklam videosu eklemek için `assets/ads/` içine `.mp4` koy; pazarları sırayla paylaşılır.

## Bilinen sınırlar

* **Etkileşimli anket/test çıkartmaları** (story poll/quiz sticker) Instagram API ile eklenemez.
  Bu yüzden hikâyeler A–E şıklı görsel soru + dokununca açılan cevap karesi olarak paylaşılır.
  (Instagram'ın kendi test çıkartması zaten en fazla 4 şık alır.)
* GitHub zamanlanmış görevleri yoğunlukta birkaç dakika gecikebilir. Görevler 20 dk erken başlayıp tam saati beklediği için bu genelde fark edilmez.
* Instagram API ile 24 saatte en fazla 100 paylaşım yapılabilir; bu pipeline günde 10 paylaşım yapar (8 hikâye karesi + 2 gönderi).

## Klasör yapısı

```
config.yaml              ayarlar
content/                 içerik bankası (JSON)
assets/                  fontlar, logo, uygulama ekran görüntüleri, reklam videoları
netio/                   üreticiler (carousel, story, video, audio) + yayıncı + zamanlayıcı
state/state.json         ne paylaşıldı, sıradaki içerik
.github/workflows/       zamanlanmış görevler
```

Yerelde deneme: `pip install -r requirements.txt` (ffmpeg gerekir) → `python -m netio.main preview --date 2026-10-16`

Fontlar: Poppins, Inter, Kalam, Patrick Hand, Caveat (SIL Open Font License), DejaVu Sans (serbest lisans).

## Anketli (TEST çıkartmalı) hikâyeler

Instagram'ın API'si hikâyeye anket/test çıkartması **ekleyemiyor** (Meta bunu hiçbir uygulamaya açmıyor).
Bu yüzden hikâyeler yarı otomatik:

1. Her çalışmada **Senin sıran** paneli güncellenir: `https://32tarcan.github.io/netio-instagram/panel/`
   (telefonda aç, ana ekrana ekle). Bugünün ve yarının 4'er hikâyesi hazır bekler.
2. Hikâye saatinde: **Görseli kaydet** → **Instagram'ı aç** → hikâye → görseli seç → çıkartma → **TEST** →
   soruyu ve 4 şıkkı Kopyala düğmeleriyle yapıştır, doğru şıkkı işaretle → kesik çizgili kutuya koy → paylaş (~1 dk).
3. Sistem hikâyeni API'den görür ve arkasından **cevap + açıklama** karesini kendisi atar.
4. Saatinden sonraki 45 dk içinde atmazsan çıkartmasız sürüm (soru + "dokun" + cevap) otomatik gider; hiçbir gün boş kalmaz.

Saatin geldiğini telefonuna bildirim olarak almak istersen: **ntfy** uygulamasını kur, tahmin edilmesi zor bir
konu adı seç (örn. `netio-7f3k9q`), uygulamada o konuya abone ol ve aynı adı GitHub'da `NTFY_TOPIC` secret'ı olarak ekle.
Kapatmak için `config.yaml` → `stories_interactive.enabled: false`.
