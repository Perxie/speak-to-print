# speak-to-print — ilerleme

<!-- Bu dosya kısa kalır: "Şu an" bölümünün üstüne yazılır, biten maddeler birikince tek satırlık özete indirilir. -->

## Şu an
- Son yapılan: Faz 4 tamamlandı, kullanıcı deneyip onayladı; commit edilip GitHub'a gönderildi. Onaylanan planın bütün fazları (0–4) bitti: uygulama Kickoff'tan açılıyor, kısayolla ya da düğmeyle dinliyor, metni imlece yazıyor, düzenleme penceresi, geçmiş, ayarlar, sesler ve hata durumları çalışıyor.
- Yarım kalan: Yok. (Sonradan: `spikes/` kullanıcının isteğiyle silindi; yeni bilgisayara kurulum adımları `README.md`'ye yazıldı ve temiz bir kopyada denendi.)
- Sıradaki: Planlı iş yok. Kullanıcı isterse aşağıdaki fikirlerden biri ya da günlük kullanımda çıkan sorunlar.

## Yapılacaklar
- [x] Faz 0 — Riskli parçaların denemeleri (GPU, mikrofon, model seçimi, kısayol, yazma yöntemi, odak almayan pencere).
- [x] Faz 1 — Çalışan çekirdek (dinleme, çeviri, imlece yazma, küçük pencere, tepsi, günlük).
- [x] Faz 2 — Düzenleme penceresi, dinlemeyi başlatma düğmeleri, geçmiş listesi.
- [x] Faz 3 — Ayarlar (kısayol davranışı, mikrofon, yazma yöntemi, sözlük, geçmişi saklama).
- [x] Faz 4 — Sağlamlaştırma (başlama/bitiş sesi ve yüksekliği, GPU yoksa CPU, model indirme/hata mesajı, mikrofon kaybı uyarısı, internetsiz çalışma, `--uninstall`).

## Fikirler
- `bitig-large` Türkçe modeli Apache-2.0 lisansına geçerse karşılaştırmaya eklenebilir.
- Pencere kapatılınca tepside kalma seçeneği (şimdilik pencere kapanınca uygulama tamamen kapanıyor).
- Tamamı İngilizce dikte için bir "İngilizce kipi" (şu an `language="tr"` ile İngilizce cümle Türkçeye çevriliyor).
- Geçmişteki bir kaydı doğrudan başka uygulamaya yapıştırma (şu an Kopyala + Ctrl+V gerekiyor).
- pip'ten gelen Qt, KDE'nin Breeze temasını almıyor; ana pencere ve ayarlar açık renkli görünüyor.
