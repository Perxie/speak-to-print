# speak-to-print — ilerleme

<!-- Bu dosya kısa kalır: "Şu an" bölümünün üstüne yazılır, biten maddeler birikince tek satırlık özete indirilir. -->

## Şu an
- Son yapılan: Faz 3 (ayarlar) tamamlandı, kullanıcı gerçek ekranda deneyip onayladı; commit edilip GitHub'a gönderildi: ayarlar penceresi, basılı tut kipi, mikrofon seçimi, yazma yöntemi, geçmişi saklama, sözlük ("Terimler: …" satırıyla; `docs/model-karsilastirma.md` eki) ve ipucu yankısı önlemi.
- Yarım kalan: Faz 4 (sağlamlaştırma) başladı, kullanıcı onay verdi: başlama/bitiş sesi, GPU yoksa CPU'ya geçiş, model yoksa/indirilemiyorsa anlaşılır mesaj, mikrofon dikte sırasında kaybolursa uyarı, internetsiz deneme, `--uninstall`.
- Sıradaki: Faz 4'ü bitirip test tarifini vermek.

## Yapılacaklar

### Faz 0 — Kurulum ve riskli parçaların denemeleri
- [x] Hepsi geçti (0.1–0.7): uv projesi, GPU'da large-v3, mikrofon (QtMultimedia), model seçimi (`docs/model-karsilastirma.md`), portal kısayolu (Shift+Pause), kwin-type ile yazma (yedek pano + Shift+Insert; Türkçe Q/F ve US düzenlerinde), odak almayan dinleme penceresi (KWin kuralı). Ayrıntılar `CLAUDE.md`'de; denenmeyenler: PyCharm editörüne ve ayrı bir Firefox alanına kwin-type ile yazma.

### Faz 1 — Çalışan çekirdek
- [x] Kickoff'tan açılıyor; kısayolla dinliyor, Beklet/Bitir/İptal çalışıyor, metin imlece yazılıyor ve küçük pencerede gösteriliyor (Kopyala, Yapıştır, otomatik yapıştırma aç/kapa); kapanınca GPU belleği boşalıyor. Uydurma metin önlemi, son hece payı, "ses bekleniyor" göstergesi ve günlük dosyası dahil.

### Faz 2 — Düzenleme ve geçmiş
- [x] Düzenleme penceresi (Kopyala, Yapıştır, içine dikte), dinlemeyi başlatma düğmeleri (ana pencere, tepsi menüsü, küçük pencere, düzenleyici) ve geçmiş listesi (SQLite; Kopyala, Düzenle, Sil, Temizle).

### Faz 3 — Ayarlar
- [x] Kısayol, kısayol davranışı (aç/kapa, basılı tut), mikrofon, yazma yöntemi, sözlük, noktalama ipucu ve geçmişi saklama "Ayarlar" penceresinden değiştirilebiliyor. Tek model: large-v3.

### Faz 4 — Sağlamlaştırma
- [ ] İnternet kapalıyken baştan sona çalışıyor; GPU, model ya da mikrofon yoksa anlaşılır uyarı veriyor.

## Fikirler
- `bitig-large` Türkçe modeli Apache-2.0 lisansına geçerse karşılaştırmaya eklenebilir.
- Pencere kapatılınca tepside kalma seçeneği (şimdilik pencere kapanınca uygulama tamamen kapanıyor).
