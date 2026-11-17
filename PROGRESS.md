# speak-to-print — ilerleme

<!-- Bu dosya kısa kalır: "Şu an" bölümünün üstüne yazılır, biten maddeler birikince tek satırlık özete indirilir. -->

## Şu an
- Son yapılan: Güvenlik düzeltmelerinin hepsi bitti ve kullanıcı denedi (1–8, 9a, 9c; 9b'yi kullanıcı istemedi): pano yöntemi, geçmiş dosyası (`secure_delete`), tek kopya soketi oturum klasöründe, etiketler düz metin, model çıktısı tek satır, sürümler sabit, kayıt 10 dk sınırı, ses dosyaları özel klasörde, KWin araçlarına zaman aşımı, kişisel veri klasörleri 0700. Öncesinde v1.0.0 etiketlendi. Kullanıcı tasarım için önerdiğim iyileştirmeleri (eski kalan açıklama satırı, sessizlikte noktalı ses çizgisi, ses çizgisi → metin geçişi, boş önizleme alanı, geçmişte gün başlıkları) istemedi: "böyle kalsın". Bunları yeniden önerme.
- Yarım kalan: Yok. Güvenlik düzeltmelerinin ayrıntısı git dışındaki `SECURITY_AUDIT_claude.md`'nin sonunda.
- Sıradaki: Bu hâl `v1.1.0` olarak etiketlendi. Kullanıcının planı (güvenlikte yaptığı gibi): (1) kendi optimizasyon skill'ini çalıştıracak, (2) sonra skill'siz benden optimizasyon incelemesi isteyecek, (3) ikisini kıyaslayıp skill'ini geliştireceğiz, (4) ardından uygulamayı iyileştireceğiz. Kullanıcının istemesini bekle; skill'in raporunu görmeden kendi incelemene başlama. Dönülecek nokta `v1.1.0`.

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
