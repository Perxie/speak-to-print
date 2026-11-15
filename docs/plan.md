# speak-to-print — Plan

> **Durum:** Kullanıcı bu planı 15 Kasım 2026'da onayladı. Metindeki "onaylanana kadar kod yazılmaz" ifadesi artık geçerli değil. İlerleme için `PROGRESS.md`'ye bakın.

## İnceleme sonucu (ikinci model, 15 Kasım 2026)

Planı baştan sona okudum ve birkaç iddiasını sistemde ve kaynağında yeniden kontrol ettim. **Kararlarını değiştirecek bir hata bulmadım.** Dört değişiklik yaptım:

1. **Model karşılaştırması öne alındı (Faz 0.4).** Yalnızca GPU ve mikrofon denemelerine dayanıyor. "Karışık dil mi, yalnızca Türkçe mi" sorusu, Wayland işlerine girmeden yanıtlanacak.
2. **Kickoff'tan açılış ayrıca sınanacak (Faz 0.5).** Önceki hâlinde GPU denemesi yalnızca terminalden yapılıyordu. Kickoff'tan açılan programlar terminaldeki ortamı görmez; GPU kütüphanelerinin bulunması bundan etkilenebilir.
3. **Qwen3-ASR koşullu oldu.** Ayrı ve ağır bir ortam gerektiriyor; kendi sayfalarında karışık dil ya da sözlük desteği yok. Yalnızca üç Whisper adayı İngilizce terimlerde yetersiz kalırsa denenecek.
4. **Küçük pencere için bir yedek daha eklendi:** Plasma'nın kendi panellerinin kullandığı "layer-shell" yöntemi. Denenmedi; bedeli aşağıda yazıyor.

Bugün ek olarak doğruladıklarım:
- Sistemdeki libei başlık dosyalarında metin gönderme arayüzü var; kwin-type'ın derlenmesi için gereken bu. KWin'in metni doğru yazdığını göstermez, o deneme duruyor.
- faster-whisper'ın bağımlılık listesinde torch yok (`ctranslate2>=4.0,<5`, onnxruntime, av, tokenizers, huggingface-hub).
- `hotwords` parametresi faster-whisper'ın güncel kaynak kodunda var.
- `wl-copy`'de `--sensitive` seçeneği var; pano yönteminde metnin Klipper geçmişine düşmesini önleyebilir.
- kwin-type AUR'da da var (0.2-1), ama paket yeni ve 1 oylu.
- pacman deposunda `pyside6` 6.12.0 var; `layer-shell-qt` 6.8.2 ve QML modülü kurulu.

## Bağlam

KDE Plasma 6 (Wayland) üzerinde tamamen yerel çalışan bir dikte uygulaması yapılacak. Konuşma çoğunlukla Türkçe olacak, cümlelerin içinde İngilizce terimler geçecek. Türkçe karakterler ve noktalama doğru olmalı. Konuşma tanıma RTX 4070 üzerinde çalışacak.

Kullanım şekli:
- Uygulama arka planda sürekli çalışan bir servis değil. Kickoff menüsünde "Speak to Print" diye aratılıp açılır, işi bitince kapatılır.
- Uygulama açıkken bir kısayolla dinleme başlatılıp durdurulur.
- Dinleme sırasında küçük bir pencere görünür. Bu pencerede dinlendiğini gösteren bir gösterge, **Beklet** ve **Bitir** düğmeleri olur. Konuşma bitince pencere biraz genişler ve metni gösterir.
- Metin, imlecin olduğu yere yazılır. Ana pencerede düzenlenebilir ve geçmişte saklanır.

Bu plan prompt'un 1. adımıdır. Onaylanana kadar kod yazılmaz.

## Sistemde doğruladıklarım

Hepsini komut çıktılarından kontrol ettim.

- **Ekran kartı:**
  - RTX 4070, 12 282 MiB bellek. Masaüstü şu an yaklaşık 1,5 GB'ını kullanıyor.
  - Sürücü 620.70.06, CUDA 13.5'i destekliyor.
  - Sistemde CUDA araç seti yok. Gerekmiyor; kütüphaneler pip paketleriyle gelecek.
- **Masaüstü:**
  - KWin ve Plasma 6.8.2, xdg-desktop-portal 1.22.1 (+ KDE arka ucu 6.8.2), libei 1.6.0 (başlık dosyalarıyla).
  - Kısayol portalı (`GlobalShortcuts`) sürüm 2 çalışıyor. `CreateSession`, `BindShortcuts`, `ListShortcuts`, `ConfigureShortcuts` yöntemleri ile `Activated` ve `Deactivated` sinyalleri var.
  - Flatpak dışı uygulamaların kendini tanıtmasını sağlayan `org.freedesktop.host.portal.Registry` arayüzü de mevcut.
  - kwin-type'ın kullandığı `org.kde.KWin /org/kde/KWin/EIS/RemoteDesktop` (`connectToEIS`) arayüzü mevcut.
- **Klavye:**
  - KDE'de şu an yalnızca Türkçe Q (`tr`) tanımlı.
  - Bir İngilizce düzeni (hangi varyant olduğunu Faz 0.6'da birlikte belirleriz) ve Türkçe F düzenini de kullanabileceğinizi söylediniz. Bu yüzden metni yazma yolu ve kısayol klavye düzeninden bağımsız olmalı.
  - O anki düzen KDE'den D-Bus ile okunabiliyor (`org.kde.keyboard /Layouts`).
- **`/dev/uinput`:** udev'deki `TAG+="uaccess"` kuralı sayesinde oturum kullanıcısı yazabiliyor. sudo ya da `input` grubu gerekmiyor.
- **Kurulu araçlar:**
  - Kurulu: `wl-clipboard`, `libpulse`, `base-devel` (gcc dahil), `libxkbcommon`, uv 0.13.8, git 2.56.1, sistem Python'u 3.14.10.
  - Kurulu değil: `ydotool`, `dotool`, `wtype`, `kdotool`.
- **Mikrofon:**
  - BTD 700 "Analog Stereo Output + Mono Input" profilindeyken "Headset Microphone" görünüyor. Şu an profil "Analog Stereo Output" ve hiç giriş kaynağı yok.
  - Bu durumda sistemin varsayılan kaynağı bir *monitor*, yani hoparlöre giden sesin kopyası. Uygulama bunu mikrofon sanmamalı ve uyarı vermeli.
- **PyCharm:** Sürüm 2026.3. Projede henüz bir yorumlayıcı (interpreter) tanımlı değil; aldığınız uyarı bu yüzden.

## Prompt'ta önerdiğim değişiklikler

1. **Klasör boş değil.**
   - `main.py`, PyCharm'ın oluşturduğu örnek dosya; silinecek.
   - `CLAUDE.md` ve `PROGRESS.md` zaten var. Yeni bir `CLAUDE.md` yazılmayacak, bu ikisi güncellenecek. Aşamalar `PROGRESS.md`'ye işlenecek.
2. **Ad:**
   - Kodda `speak-to-print` (paket `speak_to_print`).
   - Kickoff'ta ve pencere başlıklarında "Speak to Print".
3. **Servis yok.** Uygulama açılıp kapanan normal bir program olacak:
   - Kickoff'tan açılacak.
   - Pencere kapatılınca tamamen kapanacak; arka planda hiçbir şey kalmayacak ve ekran kartı belleği de boşalacak. Bu benim seçimim; isterseniz "pencereyi kapatınca tepside kalsın, Çık'la kapansın" şeklinde değiştirebiliriz.
   - Oturum açılışında otomatik başlama olmayacak.
   - Tepsi simgesi yalnızca uygulama açıkken görünecek.
4. **Model seçimi:**
   - Türkçe-İngilizce karışık konuşma için özel eğitilmiş, açık bir model bulamadım (ayrıntılar aşağıda).
   - Bu yüzden model, sizin kendi kayıtlarınızla yapılacak bir karşılaştırmayla seçilecek.
   - Hiçbiri İngilizce terimleri güvenilir yazamazsa, sizin önerdiğiniz gibi uygulama "yalnızca Türkçe" kipine indirilecek.
5. **Metni yazma yöntemi:** İki yöntem denenecek, kazanan varsayılan olacak, diğeri otomatik yedek olacak.
6. **Mikrofon:**
   - Varsayılan olarak sistemin varsayılan mikrofonu kullanılacak; KDE'de varsayılan değişirse uygulama onu izleyecek.
   - Ayarlardan belirli bir mikrofon da seçilebilecek.
7. **Kısayol davranışı:** Varsayılan, sizin tarif ettiğiniz gibi "bas başlat, tekrar bas bitir" olacak. "Basılı tut, konuş" seçeneği ayarlardan açılabilecek.
8. **Benim önerim:** Küçük pencereye **İptal** düğmesi de ekleyelim; söylenenler hiç yazılmadan atılsın.

Prompt'un geri kalanını aynen uygulayacağım:
- Riskli parçalar önce küçük denemelerle doğrulanacak.
- Her aşamanın sonunda size bir test tarifi vereceğim. Siz onaylayınca commit edeceğim ve onayınızı bekleyeceğim.

## Wayland: seçenekler, artıları ve eksileri

### 1. Global kısayol

| Seçenek | Artıları | Eksileri |
|---|---|---|
| **XDG GlobalShortcuts portalı** (öneri) | Wayland'in resmî yolu; bu sistemde sürüm 2 çalışıyor. Basma ve bırakma ayrı sinyal olarak geliyor, yani basılı tutup konuşmak mümkün. Kısayol KDE'nin Sistem Ayarları'nda görünüyor; `ConfigureShortcuts` ile uygulamadan da değiştirilebiliyor. | Uygulama kimliği, ilk portal çağrısından önce kaydedilmeli ve bir `.desktop` dosyasının adıyla eşleşmeli. KDE'de "eski kayıt kaldığı için sinyal gelmiyor" ve "portal oturumdan önce başlamış" gibi hatalar bildirilmiş. |
| KDE "Özel kısayol" ile `speak-to-print toggle` komutu (yedek) | En basit ve en sağlam yol. | Yalnızca aç/kapa çalışır, çünkü bırakma olayı gelmez. Kısayolu elle tanımlamak gerekir. |
| KGlobalAccel D-Bus'ını doğrudan kullanmak | Basma ve bırakma sinyalleri var. | Yalnızca KDE'de çalışıyor ve belgelenmemiş. Portal zaten bunun üstüne kurulu. |
| evdev ile klavyeyi doğrudan dinlemek | Her tuş kullanılabiliyor. | sudo ile `input` grubuna eklenmek gerekiyor. Uygulama **tüm** tuş vuruşlarını okuyabiliyor; güvenlik açısından kötü. |

**Karar:** Portalı kullanacağız.

**Klavye düzenleri için:** Kısayolun harf içermeyen bir tuş olmasını öneriyorum (ör. bir F tuşu, Pause, Insert ya da Meta ile bir F tuşu). Türkçe F'de harflerin yeri değiştiği için harfli bir kısayol, düzene göre başka bir fiziksel tuşa kayabilir.

### 2. Metni aktif pencereye yazma (Türkçe karakter ve klavye düzeni güvenliği öncelikli)

| Seçenek | Artıları | Eksileri |
|---|---|---|
| **kwin-type** (KWin 6.8'in EIS arayüzüyle doğrudan UTF-8 metin gönderiyor, Ekim 2026) | Metni tuş kodu olarak değil UTF-8 olarak gönderdiği için **klavye düzeninden bağımsız**. Panoya dokunmuyor. Terminallerde de çalışması beklenir. Gereken KWin arayüzü bu sistemde var. | Çok yeni: v0.2, 27 Ekim 2026. KWin'in *özel* D-Bus arayüzünü kullanıyor, ilerideki KWin sürümlerinde değişebilir. Türkçe karakterlerle ve izin penceresiyle davranışı **doğrulanmadı**. Yalnızca komut satırından çalışıyor (stdin). Yazarın kendi kaynağından derlenecek (`make`); AUR'daki paket yeni ve 1 oylu olduğu için onu kullanmıyorum. |
| **Pano + yapıştırma tuşu** (`wl-copy` ile panoya koymak, `python-evdev` ile kendi sanal klavyemizden yapıştırma tuşunu göndermek) | Her Unicode karakter kesin doğru çıkıyor. Ek araç ya da arka plan servisi gerekmiyor. Hızlı. | Panoyu geçici olarak eziyor; eski içerik geri yüklenecek. Yazılan metin Klipper geçmişine düşebiliyor; `wl-copy --sensitive` bunu önlemek için bir ipucu veriyor, Klipper'ın uyup uymadığı denemede görülecek. **Yapıştırma tuşu düzene bağlı:** Sistemin klavye tanımına (`/usr/share/X11/xkb/symbols/tr`, `f` varyantı) göre, ABD düzeninde V olan fiziksel tuş Türkçe F'de `c` yazıyor. Dolayısıyla "V tuşu + Ctrl" göndermek Türkçe F'de **Ctrl+C**'ye dönüşebilir. Çözüm adayları Faz 0.6'da denenecek: (a) düzenden bağımsız **Shift+Insert**; terminallerde de çalışsın diye metin hem panoya hem "seçim" panosuna konacak; (b) o anki düzen KDE'den okunarak doğru tuşla gönderilen Ctrl+V. |
| uinput ile karakter karakter tuş basmak (`dotool` benzeri) | Panoya dokunmuyor. | Her karakter o anki düzene göre eşlenmeli; Q, F ve ABD düzenleri arasında geçişte hata riski yüksek. Yavaş. Editörlerin otomatik tamamlaması araya girebiliyor. **Elendi.** |
| `ydotool` | Yaygın kullanılıyor. | Tuşları ABD düzenine göre gönderiyor. Türkçe Q'da `i` yerine `ı` çıkıyor, `ç ş ğ` hiç yazılamıyor. **Elendi.** |
| `wtype` | Basit. | KWin, gereken virtual-keyboard protokolünü desteklemiyor. **Elendi.** |
| RemoteDesktop portalı + libei (`eitype`) | Resmî yol. | Tuş kodu tabanlı ve düzene bağımlı. İlk seferde izin penceresi açılıyor. Python bağlantıları zayıf. |

**Karar kuralı:**
- kwin-type Türkçe testini Kate, Firefox, Konsole, PyCharm ve bir mesajlaşma uygulamasında geçerse varsayılan o olur, pano yöntemi yedek kalır.
- Geçmezse pano yöntemi varsayılan olur.
- Seçili yöntem bir dikte sırasında hata verirse uygulama o metni otomatik olarak diğer yöntemle yazar ve bunu küçük pencerede gösterir.

### 3. Kısayol davranışı

Portal, basma için `Activated`, bırakma için `Deactivated` sinyali veriyor. Bir geliştirici KDE Plasma 6'da bu iki sinyalin düzgün çiftler hâlinde geldiğini bildirmiş. Bu yüzden iki davranış da mümkün görünüyor:
- **Basılı tut, konuş:** kısa cümleler için.
- **Bas başlat, tekrar bas bitir:** uzun dikte için.

İkisi de ayar olacak.
- **Varsayılan "bas başlat, tekrar bas bitir".** Küçük penceredeki Beklet, Bitir ve İptal düğmeleri bu kipte anlamlı.
- **"Basılı tut" kipinde** tuşu bırakmak bitirir; bu yüzden Beklet ve Bitir düğmeleri gizlenir, yalnızca İptal kalır.

Bir Python uygulamasının bırakma sinyalini gerçekten alıp almadığı **doğrulanmadı**; Faz 0.5'te deneyeceğim. Alamazsa yalnızca varsayılan kip kalır.

## Arayüz ve uygulamanın yaşam döngüsü

**Açılış:**
- Kickoff'ta "Speak to Print" aratılıp açılır. Bunun için `~/.local/share/applications/` içine bir `.desktop` dosyası konacak; aynı dosya portalın uygulama kimliği için de gerekiyor.
- Model açılışta ekran kartına yüklenir. Bu birkaç saniye sürebilir (Faz 0.2'de ölçeceğim); bu sırada ana pencere "Model yükleniyor" gösterir.
- Uygulama zaten açıkken Kickoff'tan tekrar açılırsa ikinci bir kopya başlamaz, açık olan pencere öne gelir.

**Dinleme penceresi (küçük):**
- Kısayolla açılır.
- İçinde ses seviyesi göstergesi ve süre, ayrıca **Beklet/Devam**, **Bitir** ve **İptal** düğmeleri olur.
- Konuşma bitince "Çevriliyor…" gösterir, sonra biraz genişleyip metni gösterir.
- Birkaç saniye sonra kendiliğinden kapanır. Fare üstündeyse açık kalır.
- Metni düzeltmek için **Düzenle** düğmesi ana pencereyi o metinle açar.

**Ana pencere:**
- Durum alanı, son metnin düzenlenebildiği bir alan ("Kopyala" ve "Yeniden yapıştır" düğmeleriyle), son çevirilerin listesi ve ayarlar.
- Pencere küçültülüp dikte yapılabilir.
- Kapatılınca uygulama tamamen kapanır.

**Tepsi simgesi:**
- Yalnızca uygulama açıkken görünür ve durumu gösterir: hazır, dinliyor, çeviriyor.
- Menüsünde "Pencereyi göster" ve "Çık" bulunur.

**Wayland'e özgü iki sorun ve çözüm sırası:**

1. **Odak.** Küçük penceredeki bir düğmeye tıklamak pencereyi etkin yapabilir. O zaman metin hedef uygulamaya değil bizim pencereye yazılır.
   - Önce Qt'nin "odak almaz" bayrağı denenecek (`Qt.WindowDoesNotAcceptFocus`).
   - Yetmezse bir KWin pencere kuralı kullanılacak: "Odak kabul et: Hayır", "Her zaman üstte", "Görev çubuğunda gösterme". Bu kuralla tıklamaların düğmelere ulaşmaya devam etmesini bekliyorum; Faz 0.7'de doğrulanacak.
   - O da yetmezse: kayıt başlarken etkin pencere KWin betiğiyle hatırlanacak ve yazmadan önce yeniden etkinleştirilecek.
   - Son çare (denenmedi): küçük pencereyi "layer-shell" ile yapmak. Plasma'nın panelleri ve ekran bildirimleri bu yöntemi kullanır; pencere odak almaz ve ekranda istenen yere sabitlenir. Bedeli: pip'ten gelen PySide6 yerine pacman'daki `pyside6` (sudo ile kurulum) ve sistemin Python'u kullanılır, küçük pencere QML ile yazılır. Bu durumda "sudo gerekmiyor" ve "uv'nin kendi Python'u" kararları değişir; o noktaya gelirsek önce size sorarım.
2. **Konum.** Wayland'de uygulamalar kendi pencerelerini ekranda istedikleri yere koyamaz. Küçük pencereyi örneğin ekranın alt ortasına sabitlemek için yine KWin pencere kuralı kullanılacak.

## Mimari

```
Kısayol (portal, D-Bus) ─┐      Dinleme penceresi düğmeleri (Beklet / Bitir / İptal) ─┐
                         ▼                                                            ▼
             Denetleyici (durum makinesi: Hazır → Dinliyor ⇄ Beklemede → Çevriliyor → Yazılıyor → Hazır)
              │              │                     │
              ▼              ▼                     ▼
  Mikrofon (QtMultimedia)  Çeviri iş parçacığı     Çıktı
  16 kHz mono tampon       faster-whisper, GPU,    ├─ imlecin olduğu yere yazma (kwin-type | pano)
                           model bellekte hazır    ├─ dinleme penceresi (metni gösterir)
                                                   └─ geçmiş (SQLite) → ana pencere
```

**İş parçacıkları (Java karşılıklarıyla):**
- Qt ana iş parçacığı, Swing'deki EDT'ye karşılık gelir; arayüz yalnızca orada güncellenir.
- Çeviri bir `QThread` içinde çalışır (Java'daki `ExecutorService` gibi). ctranslate2 hesap yaparken Python'un GIL kilidini bıraktığı için arayüz donmaz. GIL, aynı anda yalnızca bir iş parçacığının Python kodu çalıştırmasına izin veren kilittir.
- Portal istemcisi kendi asyncio döngüsünde çalışır. asyncio, Python'un olay döngüsüdür; Java'daki `CompletableFuture` zincirlerine benzer.
- Bileşenler birbirine Qt sinyalleriyle bağlanır. Bu, Java'daki "listener + `invokeLater`" düzeninin karşılığıdır.

**Klasör yapısı (taslak):**
```
pyproject.toml  uv.lock  .python-version  .gitignore
src/speak_to_print/
  __main__.py  app.py  controller.py  audio.py  transcriber.py  hotkey.py
  output/  (kwin_type.py, clipboard_paste.py)
  history.py  settings.py
  ui/  (tray.py, listening_popup.py, main_window.py, settings_dialog.py)
spikes/        # Faz 0 deneme betikleri
packaging/speak-to-print.desktop
tests/
```

## Kütüphaneler ve sürümler

PyPI'dan 15 Kasım 2026 tarihinde kontrol ettim.

| Paket | Sürüm | Ne için |
|---|---|---|
| faster-whisper | 1.2.1 (Eki 2025) | Whisper modelini çalıştıran sarmalayıcı. Sessiz kısımları atlamak için Silero VAD içinde hazır geliyor. |
| ctranslate2 | 4.9.0 (10 Kas 2026, cp314 tekerleği var) | Modeli GPU'da çalıştıran motor. |
| nvidia-cublas-cu12, nvidia-cudnn-cu12 (9.x) | — | CUDA kütüphaneleri; sistem CUDA'sı gerekmiyor. |
| PySide6 | 6.12.0 | Qt 6 tabanlı arayüz, tepsi simgesi ve mikrofon (QtMultimedia). KDE ile aynı araç takımı. |
| dbus-fast | 5.2.0 | Portal ve KDE D-Bus çağrıları. `dbus-next` 2021'den beri güncellenmiyor. |
| evdev | 2.0.0 | Pano yönteminde yapıştırma tuşunu göndermek için sanal klavye. C eklentisi derlenecek; gcc kurulu. |
| pytest | — | Testler. |
| sqlite3, QSettings | Python ve Qt ile birlikte geliyor | Geçmiş ve ayarlar. |

**Neden PySide6?** Tepsi simgesi KDE'nin kullandığı StatusNotifierItem üzerinden çalışıyor. Mikrofon listesi KDE'deki adlarla (ör. "Headset Microphone") geliyor ve varsayılan mikrofon değişince haber veriyor.

**Yedek:** QtMultimedia sorun çıkarırsa `sounddevice` kullanılacak; mikrofon listesi `pactl` ile alınacak.

**Python sürümü:** uv'nin kendi indirdiği CPython 3.14, `.python-version` dosyasıyla sabitlenecek.
- ctranslate2, onnxruntime, av, tokenizers, numpy, dbus-fast ve PySide6'nın hepsinin 3.14 tekerlekleri var.
- uv'nin kendi Python'unu kullanmanın nedeni: CachyOS, pacman güncellemesiyle sistem Python'unu 3.15'e yükseltince `.venv` bozulmaz.

## Konuşma tanıma modeli

### Karışık dil için araştırma sonucu

- Türkçe-İngilizce karışık konuşma için özel eğitilmiş açık bir konuşma tanıma modeli **bulamadım**. Bu alanda bulabildiğim yalnızca metin tabanlı bir veri seti (TurEngMix) ve bir etiketleme aracı (TREN).
- Okuduğum Türkçe ince ayar modellerinin hepsi yalnızca Türkçe veriyle eğitilmiş. Hiçbirinin kartında İngilizce terimlere dair bir şey yok.
- Bir ASR firmasının belgesi, çok dilli bir modelin Türkçe cümle içindeki yabancı kelimeleri tek dilli bir modelden mutlaka daha iyi tanımadığını söylüyor. Önerdikleri çözüm, beklenen kelimeleri modele önceden vermek ("context biasing").
- faster-whisper'da bunun karşılığı `initial_prompt` ve `hotwords` parametreleri. (`hotwords` projenin güncel kaynak kodunda var; 1.2.1 sürümünde de olduğunu kurulumda doğrulayacağım.) Bu yüzden uygulamaya, sık kullandığınız İngilizce terimleri yazacağınız bir **sözlük** ekleyeceğiz.
- **Qwen3-ASR** (Ocak 2026, Apache-2.0, 1,7B ve 0,6B):
  - Resmî sayfasında Türkçe destekli diller arasında.
  - Karışık dil konusunda ne bir açıklama ne bir ölçüm var. Bunu iyi yaptığı iddiası yalnızca üçüncü taraf yazılarda geçiyor.
  - Beklenen kelimeleri önceden verme (sözlük) özelliği belgelenmemiş.
- Bağımsız tek bir FLEURS testinde Qwen3-ASR 1.7B, Türkçede whisper-large-v3-turbo'nun gerisinde kalmış: WER 8,34'e karşı 5,53. Yine de karışık dil için denemeye değer.

### Adaylar

Faz 0.4'te sizin sesinizle karşılaştırılacak. Önce üç Whisper adayı denenecek; Qwen3-ASR yalnızca gerekirse:

| Model | Lisans | Not |
|---|---|---|
| **whisper-large-v3** (başlangıç varsayılanı) | MIT | Çok dilli. Yaklaşık 1,54 milyar parametre; ağırlıklar float16'da yaklaşık 3 GB, 12 GB'lık karta rahatça sığar. Hazır CTranslate2 sürümü kullanılacak (ör. `Systran/faster-whisper-large-v3`; depo adını kurulumda doğrulayacağım). |
| whisper-large-v3-turbo | MIT | 809 milyon parametre, daha hızlı. Model kartına göre düşük kaynaklı dillerde doğruluk kaybı var. |
| BuzzASR/turkish | MIT | large-v3'ün Türkçe ince ayarı. Kartına göre FLEURS ve Common Voice birleşik setinde CER 4,0 (düz large-v3: 4,21). **Yalnızca Türkçe veriyle** eğitilmiş, bu yüzden İngilizce terimleri bozma riski yüksek. Noktalama koyup koymadığı yazmıyor. Tek seferlik CTranslate2 dönüşümü gerekiyor. |
| Qwen3-ASR-1.7B | Apache-2.0 | faster-whisper ile değil, kendi `qwen-asr` paketiyle (transformers/torch) çalışıyor; README ayrı bir Python 3.12 ortamı öneriyor. Yalnızca üç Whisper adayının hiçbiri İngilizce terimlerde yeterli olmazsa, ayrı bir deneme ortamında denenecek; kazanırsa uygulamaya eklenecek. |

**Kapsam dışı bıraktıklarım:**
- `kashgari-large`: ticari olmayan araştırma lisansı, erişim izne bağlı.
- `bitig-large`: "yayın öncesi değerlendirme" lisansı. Apache-2.0'a geçeceği belirtiliyor; o zaman tekrar bakmaya değer.

### Karşılaştırma yöntemi

- İngilizce terimler içeren 15–20 cümle kaydedeceksiniz.
- Her model `language="tr"` ile, sözlüklü ve sözlüksüz olarak çalıştırılacak.
- Ölçütler: Türkçe karakterler, İngilizce terimlerin doğru yazımı, noktalama ve süre.
- Sonucu tablo olarak sunacağım, seçimi siz yapacaksınız.
- Hiçbir model İngilizce terimleri güvenilir yazamazsa uygulama "yalnızca Türkçe" kipinde kalacak. Bu, kazananın yalnızca Türkçe ölçütlerle seçilmesi demek; o zaman Türkçe ince ayarlı model (BuzzASR) öne geçebilir. Sözlük yine elden geldiğince yardımcı olacak.

### Diğer notlar

- **Sessizlikte metin uydurma:** Whisper'ın sessiz kayıtlarda altyazı kalıplarına benzeyen metinler (ör. "Altyazı M.K.") ürettiği sık söylenir. Bunu bu araştırmadaki kaynaklarda doğrulamadım; Faz 0.4'te sessiz bir kayıtla deneyeceğim. Önlem olarak VAD açık olacak, boş ya da çok kısa kayıtlar atılacak.
- **İnternetsiz çalışma:** Model ilk seferde `~/.cache/huggingface` klasörüne iner (proje klasörünün dışında). Sonrasında uygulama `HF_HUB_OFFLINE=1` ile çalışır ve ağa hiç çıkmaz.

## Sudo ile kurulacak sistem paketleri

**Şu anki duruma göre hiçbiri gerekmiyor.**
- Gereken her şey zaten kurulu: `wl-clipboard`, `libpulse`, `base-devel`, `libei` (başlıklarıyla), `libxkbcommon`.
- `/dev/uinput` erişimi udev'deki `uaccess` kuralından geliyor. Bu kural kaldırılırsa sudo gerekir.
- kwin-type'ın derlenmesi ek bir paket isterse Faz 0.6'da sizden onay isteyeceğim.
- Küçük pencere için layer-shell yedeğine düşersek `sudo pacman -S pyside6` gerekir; o zaman ayrıca sorarım.

## Proje klasörünün dışına yazılacaklar

Bunları her biri ilgili aşamada, size söyleyerek oluşturacağım:

| Ne | Nereye | Ne zaman |
|---|---|---|
| Modeller (3 Whisper adayı, gerekirse Qwen3-ASR; her biri birkaç GB) | `~/.cache/huggingface/` | Faz 0.2 ve 0.4. Seçilmeyenler sonra silinebilir. |
| Kickoff kaydı ve uygulama kimliği (`.desktop`) | `~/.local/share/applications/` | Faz 0.5 |
| kwin-type kaynak kodu ve derlemesi | `~/.local/src/kwin-type` ve `~/.local/bin/kwin-type` | Faz 0.6 |
| Küçük pencere için KWin pencere kuralı (gerekirse) | `~/.config/kwinrulesrc`. Bu, KDE'nin mevcut bir ayar dosyası; değiştirmeden önce yedeği alınacak. | Faz 0.7 |
| Ayarlar ve geçmiş veritabanı | `~/.config/speak-to-print/`, `~/.local/share/speak-to-print/` | Faz 2–3 |

## Aşamalar

Her aşamanın sonunda bir test tarifi vereceğim. Siz deneyip onaylayınca commit edeceğim ve onayınızı bekleyeceğim.

### Faz 0 — Kurulum ve riskli parçaların denemeleri

Denemeler `spikes/` klasöründe küçük betikler olacak.

**0.1 Kurulum**
- `PROGRESS.md`'ye fazlar işlenecek.
- `CLAUDE.md`'ye komutlar, önemli kararlar ve sonraki oturumların da uyması gereken çalışma kuralları yazılacak:
  - Her aşamadan sonra test tarifi verilir; onaydan sonra commit edilir ve bir sonraki aşama için onay beklenir.
  - Python'a özgü kavramlar kısaca, Java karşılığıyla anlatılır.
  - Uygulama bir servis değildir; açılıp kapatılan bir programdır.
- `main.py` silinecek.
- `uv init` (src düzeni, Python 3.14) çalıştırılacak, `uv sync` ile `.venv` oluşturulacak, `git init` yapılacak.
- `.gitignore` şunları dışarıda tutacak: `.venv/`, `__pycache__/`, model dosyaları, ses kayıtları, `.idea/workspace.xml`.
- PyCharm yorumlayıcısı bağlanacak (aşağıdaki bölüm).
- **Test:** PyCharm'daki yorumlayıcı uyarısı kaybolmalı; `uv run python -c "print('ok')"` çalışmalı.

**0.2 GPU**
- faster-whisper ile large-v3 `cuda/float16` üzerinde yüklenip örnek bir WAV dosyası çevrilecek. Modelin yüklenme süresi de ölçülecek.
- Deneme `uv run` ile, kabukta `LD_LIBRARY_PATH` ayarlı olmadan yapılacak. Kickoff'tan açılışta da çalıştığı Faz 0.5'te ayrıca sınanacak.
- **Geçme ölçütü:** Model GPU'da çalışıyor (`nvidia-smi` gösteriyor) ve çeviri gerçek zamandan çok daha hızlı.
- **Yedekler:**
  - Python başlamadan önce `LD_LIBRARY_PATH`'i ayarlayan bir başlatıcı betik. faster-whisper belgesinin önerdiği yol bu.
  - ctranslate2'nin uyumlu bir sürümüne sabitlemek ya da CUDA 13 paketlerine geçmek.

**0.3 Mikrofon**
- QtMultimedia ile mikrofonlar listelenecek; monitor kaynakları ayıklanacak.
- Sistem varsayılanından 16 kHz mono kayıt alınacak.
- Deneme önce BTD 700'ün "+ Mono Input" profiliyle, sonra USB mikrofonla yapılacak.
- **Geçme ölçütü:** Kayıt temiz ve ilk kelime kesilmiyor.
- Mikrofonun yalnızca dinleme sırasında açılmasını istiyorum (Bluetooth kulaklıkta ses kalitesi için önemli). İlk kelime kesilirse mikrofon, uygulama açık olduğu sürece açık tutulacak.
- **Yedek:** `sounddevice` + `pactl`.

**0.4 Model karşılaştırması**
- Yalnızca GPU ve mikrofon denemelerine dayanıyor; bu yüzden Wayland işlerinden önce yapılacak.
- Siz cümleleri kaydedeceksiniz. Betik üç Whisper adayını çalıştırıp tablo üretecek, seçimi siz yapacaksınız.
- Üçü de İngilizce terimlerde yetersiz kalırsa Qwen3-ASR ayrı bir ortamda denenecek.
- Sonuca göre uygulama ya karışık dil hedefiyle ya da "yalnızca Türkçe" kipiyle devam edecek.
- Kayıtlar kişisel olduğu için git'e girmeyecek.

**0.5 Kısayol ve Kickoff'tan açılış**
- `.desktop` dosyası (Kickoff'ta "Speak to Print") ve ters alan adı biçiminde bir uygulama kimliği (ör. `io.github.speak_to_print`) oluşturulacak.
- `.desktop` dosyasındaki `Exec` satırı, `.venv` içindeki başlatma betiğini tam yoluyla gösterecek.
- Kimlik portala kaydedilecek, ardından `CreateSession` ve `BindShortcuts` çağrılacak. KDE'nin açtığı onay penceresinde kısayolu siz seçeceksiniz.
- Betik, basma ve bırakma olaylarını ekrana yazacak.
- **Geçme ölçütü:**
  - Başka bir uygulama öndeyken iki sinyal de geliyor.
  - Klavye düzeni değiştirildiğinde de çalışıyor.
  - Betik kapatılıp yeniden açıldığında kısayol, KDE'nin onay penceresi tekrar çıkmadan çalışıyor. Uygulama sık açılıp kapanacağı için bu önemli; kaynaklardan biri yeniden başlatmadan sonra sinyallerin kesildiğini bildiriyor.
  - Deneme hem PyCharm terminalinden hem Kickoff'tan başlatılarak yapılıyor. İkisinde de model GPU'ya yükleniyor ve kısayol çalışıyor. Kickoff'tan açılan programlar terminaldeki ortam değişkenlerini görmediği için bu ayrı bir sınama.
- **Yedek:** KDE Özel kısayolu ile `toggle` komutu.

**0.6 İmlecin olduğu yere yazma**
- Test cümlesi: `"Çığ düştü; İzmir'de ılık, şöyle güzel bir gün. Deploy ettik, pull request açtım."`
- Önce kwin-type, sonra pano yöntemi denenecek. Pano yönteminde Shift+Insert ve düzene göre seçilen Ctrl+V ayrı ayrı denenecek.
- kwin-type için ayrıca bakılacaklar: her çalıştırmada bir izin penceresi çıkıyor mu, ve bir çağrı ne kadar sürüyor.
- Pano yöntemi için ayrıca bakılacak: `wl-copy --sensitive` ile metin Klipper geçmişine düşüyor mu.
- Hedefler: Kate, Firefox, Konsole, PyCharm ve sizin kullandığınız bir mesajlaşma uygulaması.
- Denemeler Türkçe Q ile yapılacak. Siz KDE'ye İngilizce (ABD) ve Türkçe F düzenlerini eklerseniz onlarla da tekrarlanacak.
- **Geçme ölçütü:**
  - Metin birebir aynı çıkıyor.
  - Pano yönteminde panodaki önceki içerik geri geliyor.
- Varsayılan yöntem, yukarıdaki karar kuralına göre seçilecek.

**0.7 Dinleme penceresi**
- Düğmeli küçük bir deneme penceresi yapılacak.
- **Geçme ölçütü:**
  - Kate'te imleç bir satırdayken kısayolla küçük pencere açılıyor. Pencerenin **Bitir** düğmesine fareyle tıklanınca, Faz 0.6'da seçilen yöntemle gönderilen test metni Kate'teki imlecin yerine yazılıyor; küçük pencereye yazılmıyor.
  - Pencere istenen yerde (ör. alt ortada) ve her zaman üstte duruyor.
- **Yedek:** Yukarıdaki çözüm sırası: KWin pencere kuralı, sonra etkin pencereyi hatırlayıp geri getirmek, en son layer-shell.

### Faz 1 — Çalışan çekirdek

- Kickoff'ta "Speak to Print" görünecek. Açılınca model yüklenecek; basit bir ana pencere (durum + Çık) ve tepsi simgesi olacak.
- Kısayolla dinleme penceresi açılacak, Beklet/Bitir/İptal çalışacak. Metin imlecin olduğu yere yazılacak ve küçük pencerede gösterilecek.
- Pencere kapatılınca uygulama tamamen kapanacak.
- Ayarlar bu fazda koda sabit yazılı olacak.
- **Test:**
  - Kickoff'tan açın, Kate'te kısayolla bir cümle söyleyin; metin imlece gelmeli.
  - Beklet/Devam ve İptal'i deneyin.
  - Uygulamayı kapatın; `nvidia-smi`'de bellek boşalmış olmalı.

### Faz 2 — Ana pencere ve geçmiş

- Son metnin düzenlenebildiği alan, "Kopyala" ve "Yeniden yapıştır" düğmeleri.
- Son çevirilerin listesi; uygulama kapanıp açılınca da kalacak (SQLite).
- Küçük penceredeki **Düzenle** düğmesi ana pencereyi o metinle açacak.
- **Test:**
  - Üç dikte yapın, uygulamayı kapatıp açın; liste korunmuş olmalı.
  - Bir metni düzeltip yeniden yapıştırın.

### Faz 3 — Ayarlar

- **Kısayol:** portalın `ConfigureShortcuts` çağrısıyla değiştirilecek.
- **Kısayol davranışı:** basılı tut ya da aç/kapa.
- **Mikrofon:**
  - "Sistem varsayılanı" ya da listeden belirli bir mikrofon.
  - Mikrofon takılıp çıkarılınca liste güncellenecek.
  - Mikrofon yoksa uyarı verilecek.
- **Model:** model seçimi ve indirme; indirme bittikten sonra çevrimdışı çalışma.
- **Yazma yöntemi:** kwin-type ya da pano.
- **Sözlük:** sık kullandığınız İngilizce terimler.
- **Test:**
  - Her ayarı değiştirip dikte yapın.
  - BTD 700 profilini değiştirin; "Sistem varsayılanı" seçiliyken yeni mikrofon kullanılmalı.

### Faz 4 — Sağlamlaştırma

- Dinleme başlarken ve biterken kısa bir ses.
- Hata durumları:
  - GPU yoksa CPU'ya geçilecek ve uyarı verilecek.
  - Model eksikse yönlendirme yapılacak.
  - Mikrofon kaybolursa uyarı verilecek.
- İnternet kapalıyken tam bir deneme yapılacak.
- **Test:** İnterneti kapatıp uygulamayı açın ve dikte yapın. Mikrofonu dikte sırasında çıkarın; uyarı gelmeli.

## PyCharm'ın projenin `.venv` ortamını kullanması

### "PyCharm ile değil, uv ile kur" ne demek?

- **Sanal ortam (`.venv`):** Projenin kendi Python kopyası ve kütüphane klasörü. Java'da projeye özel JDK ile classpath'in birleşimi gibi düşünebilirsiniz.
- Bu klasörü PyCharm da oluşturabilir, uv de. Bu projede kütüphaneleri `pyproject.toml` ve `uv.lock` dosyaları tanımlıyor (Maven'daki `pom.xml` ve kilit dosyası gibi) ve bunları **uv** yönetiyor.
- PyCharm kendi ortamını yaratırsa uv'nin kurduğu kütüphaneleri görmez; iki ayrı ortam oluşur. Doğrusu şu: ortamı **uv kurar**, PyCharm yalnızca **var olanı kullanır**.

### Nasıl yapacağız?

Faz 0.1'de `.venv`'i `uv sync` ile ben oluşturacağım. Sizin yapacağınız tek şey PyCharm'da onu seçmek. Bildiğim kadarıyla PyCharm yorumlayıcı tanımını kendi genel ayar dosyalarında tutuyor; PyCharm açıkken bunları dışarıdan değiştirmek güvenli olmadığı için bu adımı elle yapmak daha doğru.

1. Çoğu zaman PyCharm `.venv`'i kendisi bulur ve üstte bir uyarı çubuğuyla önerir; o zaman kabul etmeniz yeter.
2. Bulmazsa:
   - **Settings** (Ctrl+Alt+S) → **Python** → **Interpreter** ("Project: speak-to-print → Python Interpreter" adıyla da görünebilir).
   - **Add Interpreter → Add Local Interpreter**.
   - **Type: uv**, **Select existing** seçin. Yol: `/home/perxie/myProjects/speak-to-print/.venv/bin/python`.
3. `src` klasörüne sağ tıklayın → **Mark Directory as → Sources Root**.

Menü adları sürüme göre biraz farklı olabilir; o adıma gelince ekranınızdakine göre birlikte ilerleriz.

**Kısa sözlük:**
- `uv` ≈ Maven/Gradle + SDKMAN bir arada
- `pyproject.toml` ≈ `pom.xml`
- `uv.lock` ≈ bağımlılıkların kilit dosyası
- `uv run komut` ≈ ortamı etkinleştirmeden çalıştırma

**fish kabuğunda:** Ortamı elle etkinleştirmek gerekirse `source .venv/bin/activate.fish` kullanılır.

## Doğrulanmamış noktalar

Bunları Faz 0'da doğrulayacağım:

- ctranslate2 4.9.0'ın pip tekerleklerinin CUDA 12 mi CUDA 13 mü istediği. faster-whisper'ın belgesi "CUDA 12 + cuDNN 9" diyor ama bu not eski olabilir.
- faster-whisper 1.2.1'in (Ekim 2025) ctranslate2 4.9.0 ile sorunsuz çalışıp çalışmadığı. Bağımlılık listesi buna izin veriyor (`ctranslate2>=4.0,<5`), ama birlikte denenmedi.
- Python'dan çalışan, Flatpak dışı bir uygulamanın portaldan `Deactivated` sinyalini alıp alamadığı.
- kwin-type'ın Türkçe karakterlerle ve farklı klavye düzenleriyle davranışı, ve izin isteyip istemediği.
- Shift+Insert'in hedef uygulamaların hepsinde yapıştırma olarak çalışıp çalışmadığı.
- Küçük pencerenin Wayland'de odak almadan tıklanabilmesi; layer-shell yedeğinin PySide6 ile çalışıp çalışmadığı.
- Kickoff'tan açıldığında GPU kütüphanelerinin bulunup bulunmadığı.
- pip'ten gelen PySide6'nın KDE'nin Breeze görünümünü alıp almadığı. Almazsa görünüm biraz farklı olur, işlev etkilenmez.
- QtMultimedia'nın PipeWire'daki mikrofon adlarını ve varsayılan mikrofon değişikliğini doğru göstermesi.
- BTD 700'ün profili ekran görüntüsünden birkaç dakika sonra yeniden "yalnızca çıkış"a dönmüştü. Bunu siz mi değiştirdiniz, kendiliğinden mi döndü, bilmiyorum. Kendiliğinden dönüyorsa "Sistem varsayılanı" bu mikrofonu göremez. Faz 0.3'te birlikte bakacağız.
- Qwen3-ASR'nin Türkçe-İngilizce karışık konuşmadaki gerçek başarısı, noktalama koyup koymadığı ve ne kadar ekran kartı belleği kullandığı.

## Onaydan sonraki ilk adım

Faz 0.1:
1. `PROGRESS.md` ve `CLAUDE.md`'yi bu plana göre güncellemek.
2. `main.py`'yi silmek; uv ve git kurulumunu yapmak.
3. PyCharm yorumlayıcısını birlikte bağlamak.
4. Size test tarifini verip onayınızı beklemek.

## Kaynaklar

- python-global-shortcut-portal: https://github.com/marvin1099/python-global-shortcut-portal
- Portal ile basılı tutup konuşma (KDE'de Activated/Deactivated): https://github.com/mikeallisonJS/cadent/issues/35, https://github.com/wispr-flow-linux/helper/issues/4
- KDE portal sorunları: https://github.com/anomalyco/hex/issues/875, https://github.com/dewzor/claude-desktop-fedora/issues/11
- Portal Registry (Flatpak dışı uygulamalar): https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.host.portal.Registry.html, https://develop.kde.org/docs/administration/portal-permissions/
- voxtype SSS ve sorun giderme (KDE'de wtype/dotool/ydotool/pano, düzen sorunları): https://github.com/peteonrails/voxtype/blob/main/docs/FAQ.md
- wtype'ın KWin'de çalışmaması: https://bugs.kde.org/show_bug.cgi?id=497774, https://gist.github.com/danielrosehill/d3913d4c8cc69acaf3ee7772771c2f1d
- kwin-type: https://git.zx2c4.com/kwin-type/ · KWtype: https://github.com/Sporif/KWtype · eitype: https://docs.rs/crate/eitype/0.2.0
- libei'nin Unicode sınırları: https://perrette.github.io/scribe/roadmap-libei/
- faster-whisper (GPU gereksinimleri): https://github.com/SYSTRAN/faster-whisper · CTranslate2 sürümleri: https://github.com/OpenNMT/CTranslate2/releases
- Modeller: https://huggingface.co/openai/whisper-large-v3-turbo, https://huggingface.co/BuzzASR/turkish, https://huggingface.co/turkish-sa-asr/kashgari-large-v1.0, https://huggingface.co/turkish-sa-asr/bitig-large-v1.0
- Qwen3-ASR: https://github.com/QwenLM/Qwen3-ASR, https://huggingface.co/Qwen/Qwen3-ASR-0.6B, https://arxiv.org/html/2601.21337 · Türkçe FLEURS karşılaştırması: https://whispernotes.app/blog/qwen3-asr-vs-whisper
- Karışık dil ve bağlam ipuçları: https://docs.sestek.com/docs/sr-supported-languages-and-models, https://arxiv.org/html/2406.05806v2 · TurEngMix: https://arxiv.org/pdf/2609.06963
- PyPI sürüm bilgileri: pypi.org/pypi/<paket>/json (ctranslate2, faster-whisper, PySide6, dbus-fast, evdev, onnxruntime, av, tokenizers, numpy, torch)
