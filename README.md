# Netio Instagram Otomatik İçerik Pipeline'ı

Her gün kendiliğinden TYT/AYT içeriği üretir ve Netio'nun Instagram hesabından paylaşır.
Sunucu gerekmez; her şey ücretsiz **GitHub Actions** üzerinde çalışır.

## Günlük akış (Türkiye saati)

| Saat  | Çift günler          | Tek günler           |
|-------|----------------------|----------------------|
| 10:00 | Hikâye (soru 1/4)    | Hikâye (soru 1/4)    |
| 12:00 | **Kaydırmalı post**  | **Soru videosu (Reels)** |
| 14:00 | Hikâye (soru 2/4)    | Hikâye (soru 2/4)    |
| 16:00 | **Soru videosu (Reels)** | **Kaydırmalı post** |
| 19:00 | Hikâye (soru 3/4)    | Hikâye (soru 3/4)    |
| 21:30 | Hikâye (soru 4/4)    | Hikâye (soru 4/4)    |

* Pazar günleri o günün video slotunda soru videosu yerine `assets/ads/` içindeki marka reklamı paylaşılır.
* Her hikâyenin üstünde bir önceki hikâyedeki sorunun cevabı yazar; cevap merak ettirir, takipçi geri döner.
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
  Bu yüzden hikâyeler A/B/C/D şıklı görsel soru olarak paylaşılır ve cevap bir sonraki hikâyede açıklanır.
  İstersen bazı hikâyelere telefondan elle anket çıkartması ekleyebilirsin.
* GitHub zamanlanmış görevleri yoğunlukta birkaç dakika gecikebilir. Görevler 20 dk erken başlayıp tam saati beklediği için bu genelde fark edilmez.
* Instagram API ile 24 saatte en fazla 100 paylaşım yapılabilir; bu pipeline günde 6 paylaşım yapar.

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
