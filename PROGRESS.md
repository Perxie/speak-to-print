# speak-to-print — ilerleme

<!-- Bu dosya kısa kalır: "Şu an" bölümünün üstüne yazılır, biten maddeler birikince tek satırlık özete indirilir. -->

## Şu an
- Son yapılan: Faz 0.7 ve böylece Faz 0'ın tamamı bitti; kullanıcı deneyip onayladı, commit edilip GitHub'a gönderildi. Dinleme penceresi KWin pencere kuralıyla odağı almıyor: düğmelere fareyle tıklanınca da odak hedef pencerede kalıyor ve metin oraya yazılıyor; pencere ekranın alt ortasında, üstte duruyor.
- Yarım kalan: Yok.
- Sıradaki: Faz 1 — çalışan çekirdek. Başlamadan önce kullanıcının onayı beklenir. Faz 0'da yazılan modüller (`hotkey.py`, `output/`, `kwin_rules.py`, `desktop_entry.py`, `cuda_libs.py`) ve `spikes/` içindeki kayıt/çeviri kodu yeniden kullanılacak.

## Yapılacaklar

### Faz 0 — Kurulum ve riskli parçaların denemeleri
- [x] Hepsi geçti (0.1–0.7): uv projesi, GPU'da large-v3, mikrofon (QtMultimedia), model seçimi (`docs/model-karsilastirma.md`), portal kısayolu (Shift+Pause), kwin-type ile yazma (yedek pano + Shift+Insert; Türkçe Q/F ve US düzenlerinde), odak almayan dinleme penceresi (KWin kuralı). Ayrıntılar `CLAUDE.md`'de; denenmeyenler: PyCharm editörüne ve ayrı bir Firefox alanına kwin-type ile yazma.

### Faz 1 — Çalışan çekirdek
- [ ] Kickoff'tan açılıyor; kısayolla dinliyor, Beklet/Bitir/İptal çalışıyor, metin imlece yazılıyor; kapanınca GPU belleği boşalıyor. Not: dinleme penceresi mikrofondan ses gelmeye başladığını göstersin (BTD 700 geç açılıyor); durdurunca son hece kesilmesin diye kısa bir süre daha kayıt alınsın. Kısayol atanmamışsa (ilk açılışta boş gelebiliyor) kullanıcıya söylenip ayar penceresi açtırılsın. Uydurma metne karşı önlem ("Altyazı M.K.") ve ipucu metninin açık/kapalı olması burada denenecek.

### Faz 2 — Ana pencere ve geçmiş
- [ ] Son metin düzenlenip yeniden yapıştırılabiliyor; geçmiş uygulama yeniden açılınca da duruyor.

### Faz 3 — Ayarlar
- [ ] Kısayol, kısayol davranışı, mikrofon, yazma yöntemi ve sözlük ayarlardan değiştirilebiliyor. (Model seçimi yok: tek model large-v3.)

### Faz 4 — Sağlamlaştırma
- [ ] İnternet kapalıyken baştan sona çalışıyor; GPU, model ya da mikrofon yoksa anlaşılır uyarı veriyor.

## Fikirler
- `bitig-large` Türkçe modeli Apache-2.0 lisansına geçerse karşılaştırmaya eklenebilir.
- Pencere kapatılınca tepside kalma seçeneği (şimdilik pencere kapanınca uygulama tamamen kapanıyor).
