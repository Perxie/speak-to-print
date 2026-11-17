# speak-to-print — ilerleme

<!-- Bu dosya kısa kalır: "Şu an" bölümünün üstüne yazılır, biten maddeler birikince tek satırlık özete indirilir. -->

## Şu an
- Son yapılan: Güvenlik 1–3. adımlar bitti ve kullanıcı denedi: pano yöntemi (`tests/test_clipboard_paste.py`), geçmiş dosyası (`secure_delete`, bir kerelik `VACUUM`), tek kopya soketi oturum klasöründe (`tests/test_single_instance.py`). Öncesinde v1.0.0 etiketlendi. Kullanıcı tasarım için önerdiğim iyileştirmeleri (eski kalan açıklama satırı, sessizlikte noktalı ses çizgisi, ses çizgisi → metin geçişi, boş önizleme alanı, geçmişte gün başlıkları) istemedi: "böyle kalsın". Bunları yeniden önerme.
- Yarım kalan: Güvenlik düzeltmeleri. Sıra, ayrıntılar ve her adımın durumu git dışındaki `SECURITY_AUDIT_claude.md`'nin sonundaki "Düzeltme sırası ve durumu" bölümünde (depo herkese açık: giderilmemiş açıkları buraya ya da commit'lere yazma). Kullanıcının `mia-security-check` skill'i iyileştirildi ve kuruldu.
- Sıradaki: Kullanıcının onayıyla 4. adım. Sonra optimizasyon. Dönülecek nokta `v1.0.0`.

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
