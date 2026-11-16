# Proje klasörü dışına yazılanlar

Bu proje için bilgisayarda proje klasörü dışında oluşan, yeniden başlatınca **silinmeyen** her şey
burada listelenir. Amaç: iş bitince ya da proje bırakılırsa neyin silinebileceğini bilmek.
Proje dışına yeni bir şey yazıldığında bu liste güncellenir.

`/tmp` altındaki geçici dosyalar bellekte tutulur (tmpfs) ve bilgisayar kapanınca kendiliğinden silinir;
onlar listede yok. `~/.cache` ise adına rağmen diskte durur ve kendiliğinden silinmez.

## Uygulama çalıştığı sürece gerekli olanlar

| Ne | Nerede | Boyut | Silmek için |
|---|---|---|---|
| Konuşma tanıma modeli (large-v3) | `~/.cache/huggingface/hub/models--Systran--faster-whisper-large-v3` ve `~/.cache/huggingface/hub/blobs` | 3,1 GB | `uv run hf cache rm model/Systran/faster-whisper-large-v3` |
| Kickoff menü kaydı ve portal uygulama kimliği | `~/.local/share/applications/io.github.perxie.SpeakToPrint.desktop` | küçük | dosyayı silin (uygulama her açılışta yeniden yazar) |
| KDE'de bu uygulamaya atanmış global kısayol (Shift+Pause) | KDE Sistem Ayarları → Klavye → Kısayollar → "Speak to Print" (`~/.config/kglobalshortcutsrc`) | küçük | Sistem Ayarları'ndan kısayolu kaldırın |
| kwin-type programı (metni pencereye yazar) | `~/.local/bin/kwin-type` | 22 KB | dosyayı silin |
| Dinleme penceresi için KWin pencere kuralı | `~/.config/kwinrulesrc` içindeki `speak-to-print-dinleme` bölümü (dosyanın ilk hâli: `kwinrulesrc.speak-to-print.yedek`, boştu) | küçük | `uv run python spikes/popup_check.py --remove-rule`, sonra yedek dosyası silinebilir |
| Uygulamanın ayarları (otomatik yapıştırma, noktalama ipucu) | `~/.config/speak-to-print/speak-to-print.conf` | küçük | klasörü silin |
| Uygulamanın günlüğü (durumlar ve süreler; dikte edilen metin yazılmaz) | `~/.local/state/speak-to-print/speak-to-print.log` (en çok 2 × 512 KB) | küçük | klasörü silin |
| uv'nin kurduğu Python 3.14 (`.venv` bunu kullanır) | `~/.local/share/uv/python/` ve `~/.local/bin/python3.14` bağlantısı | 117 MB | `uv python uninstall 3.14` |

## Geliştirme için gerekli olanlar

| Ne | Nerede | Boyut | Silmek için |
|---|---|---|---|
| GitHub komut satırı aracı (kullanıcı kurdu) | pacman paketi `github-cli` | küçük | `sudo pacman -Rs github-cli` |
| GitHub giriş bilgisi | `~/.config/gh/` ve KDE cüzdanı (keyring) | küçük | `gh auth logout` |
| GitHub için git kimlik yardımcısı ayarı | `~/.gitconfig` içindeki `credential.https://github.com.helper` satırları | — | `gh auth logout` sonrası satırlar elle silinebilir |

## İstenince silinebilenler (yeniden oluşur)

| Ne | Nerede | Boyut | Silmek için |
|---|---|---|---|
| kwin-type kaynak kodu (derleme için indirildi) | `~/.local/src/kwin-type/` | küçük | klasörü silin |
| uv'nin paket önbelleği | `~/.cache/uv/` | değişir (16 Kasım'da temizlendi) | `uv cache clean` |
| Hugging Face'in yardımcı önbelleği | `~/.cache/huggingface/xet/` | küçük | klasör silinebilir |

## Silinmiş olanlar

- BuzzASR/turkish modeli (HF önbelleği ve `models/`), 16 Kasım 2026.
- large-v3-turbo modeli (HF önbelleği), 16 Kasım 2026.

## Proje klasörünün içinde olup git'e girmeyenler

Bunlar proje klasörü silinince gider: `.venv/` (yaklaşık 2 GB), `recordings/` (ses kayıtları ve rapor),
`spikes/data/` (deneme kayıtları).
