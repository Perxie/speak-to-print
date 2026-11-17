# speak-to-print — ilerleme

<!-- Bu dosya kısa kalır: "Şu an" bölümünün üstüne yazılır, biten maddeler birikince tek satırlık özete indirilir. -->

## Şu an
- Son yapılan: Faz 5 (yeniden tasarım) tamamlandı, kullanıcı gerçek ekranda denedi ve onayladı; commit edilip GitHub'a gönderildi. Bütün pencereler `docs/tasarim.md`'deki dille yeniden çizildi; uygulama simgesi temaya kopyalanıyor (Kickoff'taki kısayol satırı oturum yeniden açılınca yenilendi). `CLAUDE.md`'deki "Ajan kullanımı" bölümü kullanıcının isteğiyle kaldırıldı.
- Yarım kalan: Yok.
- Sıradaki: Planlı iş yok. Kullanıcı isterse "Fikirler" bölümünden biri ya da günlük kullanımda çıkan sorunlar.

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
