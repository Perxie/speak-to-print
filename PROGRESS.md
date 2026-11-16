# speak-to-print — ilerleme

<!-- Bu dosya kısa kalır: "Şu an" bölümünün üstüne yazılır, biten maddeler birikince tek satırlık özete indirilir. -->

## Şu an
- Son yapılan: Faz 0.4 tamamlandı, kullanıcı onayladı; commit edilip GitHub'a gönderildi. Kullanıcı varsayılan model olarak large-v3'ü seçti (turbo ayarlardan seçilebilir kalacak); uygulama karışık dil hedefiyle devam ediyor. Özet ve açık konular `docs/model-karsilastirma.md`'de. BuzzASR silindi (HF önbelleği ve `models/`).
- Yarım kalan: Yok.
- Sıradaki: Faz 0.5 — kısayol portalı ve Kickoff'tan açılış denemesi. Başlamadan önce kullanıcının onayı beklenir.

## Yapılacaklar

### Faz 0 — Kurulum ve riskli parçaların denemeleri
- [x] 0.1 Kurulum: `uv run speak-to-print` çalışıyor, PyCharm `.venv`'i kullanıyor.
- [x] 0.2 GPU: large-v3 ekran kartında örnek bir kaydı gerçek zamandan çok hızlı çeviriyor.
- [x] 0.3 Mikrofon: sistem varsayılanından temiz kayıt alınıyor. BTD 700'de Enter'a basar basmaz konuşunca ilk hece kesildi ("Portakal" → "Kalsuyu", kayıt 0,4 sn kısa geldi); kullanıcı ~0,5 sn beklemeyi kabul etti.
- [x] 0.4 Model karşılaştırması: kullanıcının kayıtlarıyla tablo çıktı, large-v3 seçildi, karışık dil hedefi sürüyor (`docs/model-karsilastirma.md`).
- [ ] 0.5 Kısayol: portal kısayolu Kickoff'tan açılışta da, yeniden açılıştan sonra da çalışıyor.
- [ ] 0.6 Yazma: Türkçe test cümlesi Kate, Firefox, Konsole, PyCharm'da birebir çıkıyor; yöntem seçildi.
- [ ] 0.7 Dinleme penceresi: Bitir'e tıklayınca metin Kate'e gidiyor, pencere odağı çalmıyor.

### Faz 1 — Çalışan çekirdek
- [ ] Kickoff'tan açılıyor; kısayolla dinliyor, Beklet/Bitir/İptal çalışıyor, metin imlece yazılıyor; kapanınca GPU belleği boşalıyor. Not: dinleme penceresi mikrofondan ses gelmeye başladığını göstersin (BTD 700 geç açılıyor); durdurunca son hece kesilmesin diye kısa bir süre daha kayıt alınsın. Uydurma metne karşı önlem ("Altyazı M.K.") ve ipucu metninin açık/kapalı olması burada denenecek.

### Faz 2 — Ana pencere ve geçmiş
- [ ] Son metin düzenlenip yeniden yapıştırılabiliyor; geçmiş uygulama yeniden açılınca da duruyor.

### Faz 3 — Ayarlar
- [ ] Kısayol, kısayol davranışı, mikrofon, model, yazma yöntemi ve sözlük ayarlardan değiştirilebiliyor.

### Faz 4 — Sağlamlaştırma
- [ ] İnternet kapalıyken baştan sona çalışıyor; GPU, model ya da mikrofon yoksa anlaşılır uyarı veriyor.

## Fikirler
- `bitig-large` Türkçe modeli Apache-2.0 lisansına geçerse karşılaştırmaya eklenebilir.
- Pencere kapatılınca tepside kalma seçeneği (şimdilik pencere kapanınca uygulama tamamen kapanıyor).
