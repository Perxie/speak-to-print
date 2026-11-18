# speak-to-print — ilerleme

<!-- Bu dosya kısa kalır: "Şu an" bölümünün üstüne yazılır, biten maddeler birikince tek satırlık özete indirilir. -->

## Şu an
- Son yapılan: Optimizasyon turu bitti ve `v1.2.0` olarak etiketlendi (GitHub sürüm sayfası açıldı). Kullanıcının `mia-optimization-check` skill'i iyileştirildi ve kuruldu. Çalışma notları, raporlar ve ekran görüntüleri iş bitince silindi (kullanıcı isteği, 18 Kasım). Kullanıcı kararları: pano yolundaki donma düzeltilmeyecek (güvenlik kodunu bozmasın), işlemci yedeği kaldırıldı (yalnızca ekran kartı), geçmiş 30 kayıt, yer tutucular italik, "dikteden önceki pencereyi hatırlama" istenmedi. Kullanıcı tasarım için önerdiğim iyileştirmeleri (eski kalan açıklama satırı, sessizlikte noktalı ses çizgisi, ses çizgisi → metin geçişi, boş önizleme alanı, geçmişte gün başlıkları) istemedi: "böyle kalsın". Bunları yeniden önerme.
- Yarım kalan: Yok.
- Sıradaki: Yok. Kullanıcı geliştirmeyi noktaladı (18 Kasım 2026, `v1.2.0`); ileride özellik ekleyip çıkarabilir. Yeni bir bilgisayara kurulum README'den yapılır (GitHub'dan temiz kopya 18 Kasım'da denendi: kilitli ortam kuruldu, 167 test geçti; kwin-type v0.2 ve model sürümü kaynaklarında duruyor). Kullanıcı ayarların, geçmişin, `recordings/` ve skill'lerin ayrıca yedeklenmesini istemedi (kolayca yeniden ayarlanır). Dönülecek nokta `v1.2.0`.

## Yapılacaklar
- [x] Faz 0 — Riskli parçaların denemeleri (GPU, mikrofon, model seçimi, kısayol, yazma yöntemi, odak almayan pencere).
- [x] Faz 1 — Çalışan çekirdek (dinleme, çeviri, imlece yazma, küçük pencere, tepsi, günlük).
- [x] Faz 2 — Düzenleme penceresi, dinlemeyi başlatma düğmeleri, geçmiş listesi.
- [x] Faz 3 — Ayarlar (kısayol davranışı, mikrofon, yazma yöntemi, sözlük, geçmişi saklama).
- [x] Faz 4 — Sağlamlaştırma (başlama/bitiş sesi ve yüksekliği, GPU yoksa CPU, model indirme/hata mesajı, mikrofon kaybı uyarısı, internetsiz çalışma, `--uninstall`).
- [x] Faz 5 — Arayüzün yeniden tasarımı (`docs/tasarim.md`): küçük pencere, düzenleyici, ana pencere, ayarlar, tepsi ve uygulama simgesi.

## Fikirler
- `bitig-large` Türkçe modeli Apache-2.0 lisansına geçerse karşılaştırmaya eklenebilir.
- Pencere kapatılınca tepside kalma seçeneği (şimdilik pencere kapanınca uygulama tamamen kapanıyor).
- Tamamı İngilizce dikte için bir "İngilizce kipi" (şu an `language="tr"` ile İngilizce cümle Türkçeye çevriliyor).
- Geçmişteki bir kaydı doğrudan başka uygulamaya yapıştırma (şu an Kopyala + Ctrl+V gerekiyor).
