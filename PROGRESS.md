# speak-to-print — ilerleme

<!-- Bu dosya kısa kalır: "Şu an" bölümünün üstüne yazılır, biten maddeler birikince tek satırlık özete indirilir. -->

## Şu an
- Son yapılan: Faz 0.3 tamamlandı, kullanıcı iki mikrofonla (BTD 700, USB PnP) deneyip onayladı; commit edilip GitHub'a gönderildi. Seçilen mikrofon kullanılıyor, varsayılan değişince `--list` işareti taşınıyor, Türkçe cümle ("pull request" dahil) doğru yazıya çevrildi.
- Yarım kalan: Yok.
- Sıradaki: Faz 0.4 — model karşılaştırması. Başlamadan önce kullanıcının onayı beklenir.

## Yapılacaklar

### Faz 0 — Kurulum ve riskli parçaların denemeleri
- [x] 0.1 Kurulum: `uv run speak-to-print` çalışıyor, PyCharm `.venv`'i kullanıyor.
- [x] 0.2 GPU: large-v3 ekran kartında örnek bir kaydı gerçek zamandan çok hızlı çeviriyor.
- [x] 0.3 Mikrofon: sistem varsayılanından temiz kayıt alınıyor. BTD 700'de Enter'a basar basmaz konuşunca ilk hece kesildi ("Portakal" → "Kalsuyu", kayıt 0,4 sn kısa geldi); kullanıcı ~0,5 sn beklemeyi kabul etti.
- [ ] 0.4 Model karşılaştırması: kullanıcının kayıtlarıyla tablo çıktı, model seçildi (karışık dil ya da yalnızca Türkçe). Not: 45–60 sn'lik gerçek bir kayıt da olsun ve segmentlerin `temperature` değerleri kaydedilsin (Faz 0.2'de tekrarlı örnek kayıtta yeniden denemeler yavaşlattı); her model ~3,9 GB, tek tek yüklensin. Faz 0.3 gözlemleri de sınansın: uzak/kısık seste "Altyazı M.K." uyduruldu; noktalama ve büyük harf kayıttan kayda değişti (`initial_prompt` ile denenecek); sette tamamı İngilizce bir cümle ve gerçek oda sessizliği olsun.
- [ ] 0.5 Kısayol: portal kısayolu Kickoff'tan açılışta da, yeniden açılıştan sonra da çalışıyor.
- [ ] 0.6 Yazma: Türkçe test cümlesi Kate, Firefox, Konsole, PyCharm'da birebir çıkıyor; yöntem seçildi.
- [ ] 0.7 Dinleme penceresi: Bitir'e tıklayınca metin Kate'e gidiyor, pencere odağı çalmıyor.

### Faz 1 — Çalışan çekirdek
- [ ] Kickoff'tan açılıyor; kısayolla dinliyor, Beklet/Bitir/İptal çalışıyor, metin imlece yazılıyor; kapanınca GPU belleği boşalıyor. Not: dinleme penceresi mikrofondan ses gelmeye başladığını göstersin (BTD 700 geç açılıyor); durdurunca son hece kesilmesin diye kısa bir süre daha kayıt alınsın.

### Faz 2 — Ana pencere ve geçmiş
- [ ] Son metin düzenlenip yeniden yapıştırılabiliyor; geçmiş uygulama yeniden açılınca da duruyor.

### Faz 3 — Ayarlar
- [ ] Kısayol, kısayol davranışı, mikrofon, model, yazma yöntemi ve sözlük ayarlardan değiştirilebiliyor.

### Faz 4 — Sağlamlaştırma
- [ ] İnternet kapalıyken baştan sona çalışıyor; GPU, model ya da mikrofon yoksa anlaşılır uyarı veriyor.

## Fikirler
- `bitig-large` Türkçe modeli Apache-2.0 lisansına geçerse karşılaştırmaya eklenebilir.
- Pencere kapatılınca tepside kalma seçeneği (şimdilik pencere kapanınca uygulama tamamen kapanıyor).
