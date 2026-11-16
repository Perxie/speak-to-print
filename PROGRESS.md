# speak-to-print — ilerleme

<!-- Bu dosya kısa kalır: "Şu an" bölümünün üstüne yazılır, biten maddeler birikince tek satırlık özete indirilir. -->

## Şu an
- Son yapılan: Düzenleme penceresi ve "Dinlemeyi başlat" düğmeleri (ana pencere, tepsi menüsü) kullanıcı tarafından gerçek ekranda denendi ve onaylandı; commit edilip GitHub'a gönderildi. Düzenleyiciden Yapıştır'da odak önceki uygulamaya ~40 ms'de dönüyor; dikte ana pencereden başlatıldıysa dönecek uygulama olmadığı için yazılmıyor ve düzenleyici geri açılıyor (beklenen davranış).
- Yarım kalan: Küçük pencereye "Dinlemeyi başlat" düğmesi eklendi (dinleme bitince seviye çubuğunun yerinde görünür); düzenleyicideki eski uyarının kalması düzeltildi. Ekransız denendi, commit edilmedi; kullanıcı testi bekliyor.
- Sıradaki: Küçük penceredeki düğmenin kullanıcı testi; sonra Faz 2'nin kalan maddesi (geçmiş listesi).

## Yapılacaklar

### Faz 0 — Kurulum ve riskli parçaların denemeleri
- [x] Hepsi geçti (0.1–0.7): uv projesi, GPU'da large-v3, mikrofon (QtMultimedia), model seçimi (`docs/model-karsilastirma.md`), portal kısayolu (Shift+Pause), kwin-type ile yazma (yedek pano + Shift+Insert; Türkçe Q/F ve US düzenlerinde), odak almayan dinleme penceresi (KWin kuralı). Ayrıntılar `CLAUDE.md`'de; denenmeyenler: PyCharm editörüne ve ayrı bir Firefox alanına kwin-type ile yazma.

### Faz 1 — Çalışan çekirdek
- [x] Kickoff'tan açılıyor; kısayolla dinliyor, Beklet/Bitir/İptal çalışıyor, metin imlece yazılıyor ve küçük pencerede gösteriliyor (Kopyala, Yapıştır, otomatik yapıştırma aç/kapa); kapanınca GPU belleği boşalıyor. Uydurma metin önlemi, son hece payı, "ses bekleniyor" göstergesi ve günlük dosyası dahil.

### Faz 2 — Düzenleme ve geçmiş
- [x] Çevrilen metin düzenleme penceresinde düzenlenip önceki uygulamaya yapıştırılabiliyor; dinleme düğmeyle de (ana pencere, tepsi menüsü) başlatılabiliyor.
- [ ] "Dinlemeyi başlat" düğmesi küçük pencerede de var.
- [ ] Son çevirilerin listesi; uygulama yeniden açılınca da duruyor (SQLite).

### Faz 3 — Ayarlar
- [ ] Kısayol, kısayol davranışı, mikrofon, yazma yöntemi ve sözlük ayarlardan değiştirilebiliyor. (Model seçimi yok: tek model large-v3.)

### Faz 4 — Sağlamlaştırma
- [ ] İnternet kapalıyken baştan sona çalışıyor; GPU, model ya da mikrofon yoksa anlaşılır uyarı veriyor.

## Fikirler
- `bitig-large` Türkçe modeli Apache-2.0 lisansına geçerse karşılaştırmaya eklenebilir.
- Pencere kapatılınca tepside kalma seçeneği (şimdilik pencere kapanınca uygulama tamamen kapanıyor).
