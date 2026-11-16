# speak-to-print — ilerleme

<!-- Bu dosya kısa kalır: "Şu an" bölümünün üstüne yazılır, biten maddeler birikince tek satırlık özete indirilir. -->

## Şu an
- Son yapılan: Faz 1 tamamlandı, kullanıcı gerçek ekranda deneyip onayladı ("çok iyi çalışıyor"); commit edilip GitHub'a gönderildi. 34 gerçek dikte yapıldı (USB ve BTD 700), metin imlece yazıldı; düğmeler, otomatik yapıştırma ayarı, ikinci açılış ve kapanış çalıştı. Ayrıca doğrulandı: dinlerken ve çevirirken kapatınca süreç bitiyor, ekran kartı belleği ve mikrofon serbest kalıyor. Noktalama ipucu kullanıcıya göre fark yaratmıyor (açık bırakıldı).
- Yarım kalan: Kullanıcının iki yeni isteği (onay verildi sayılır, kendisi istedi): (1) çevrilen metnin gösterildiği yerde düzenlenebilmesi, (2) dinlemeyi kısayol dışında bir düğmeyle başlatabilmek.
- Sıradaki: (1) için odak alabilen ayrı bir sonuç penceresi (küçük pencere odak alamıyor); (2) için ana pencerede ve tepsi menüsünde "Dinlemeyi başlat".

## Yapılacaklar

### Faz 0 — Kurulum ve riskli parçaların denemeleri
- [x] Hepsi geçti (0.1–0.7): uv projesi, GPU'da large-v3, mikrofon (QtMultimedia), model seçimi (`docs/model-karsilastirma.md`), portal kısayolu (Shift+Pause), kwin-type ile yazma (yedek pano + Shift+Insert; Türkçe Q/F ve US düzenlerinde), odak almayan dinleme penceresi (KWin kuralı). Ayrıntılar `CLAUDE.md`'de; denenmeyenler: PyCharm editörüne ve ayrı bir Firefox alanına kwin-type ile yazma.

### Faz 1 — Çalışan çekirdek
- [x] Kickoff'tan açılıyor; kısayolla dinliyor, Beklet/Bitir/İptal çalışıyor, metin imlece yazılıyor ve küçük pencerede gösteriliyor (Kopyala, Yapıştır, otomatik yapıştırma aç/kapa); kapanınca GPU belleği boşalıyor. Uydurma metin önlemi, son hece payı, "ses bekleniyor" göstergesi ve günlük dosyası dahil.

### Faz 2 — Ana pencere ve geçmiş
- [ ] Küçük penceredeki Düzenle düğmesi metni odak alan bir düzenleme penceresinde açıyor; son metin düzenlenip yeniden yapıştırılabiliyor (odağın eski pencereye dönmesi önce denenmeli); geçmiş uygulama yeniden açılınca da duruyor.

### Faz 3 — Ayarlar
- [ ] Kısayol, kısayol davranışı, mikrofon, yazma yöntemi ve sözlük ayarlardan değiştirilebiliyor. (Model seçimi yok: tek model large-v3.)

### Faz 4 — Sağlamlaştırma
- [ ] İnternet kapalıyken baştan sona çalışıyor; GPU, model ya da mikrofon yoksa anlaşılır uyarı veriyor.

## Fikirler
- `bitig-large` Türkçe modeli Apache-2.0 lisansına geçerse karşılaştırmaya eklenebilir.
- Pencere kapatılınca tepside kalma seçeneği (şimdilik pencere kapanınca uygulama tamamen kapanıyor).
