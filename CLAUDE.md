# speak-to-print

Kişisel kullanım için, KDE Plasma 6 (Wayland) üzerinde tamamen yerel çalışan bir dikte uygulaması: konuşmayı yazıya çevirir, ses hiçbir bulut servisine gönderilmez. Konuşma çoğunlukla Türkçedir ama cümle ortalarında İngilizce terimler geçer; Türkçe karakterler ve noktalama doğru olmalıdır. Kickoff'tan "Speak to Print" diye açılır, kısayolla dinler, metni imlecin olduğu yere yazar ve kendi penceresinde düzenlenebilir gösterir.

## Komutlar
- `uv sync`: `.venv`'i `pyproject.toml` ve `uv.lock`'a göre kurar ya da günceller.
- `uv run speak-to-print`: uygulamayı çalıştırır. Günlüğü: `~/.local/state/speak-to-print/speak-to-print.log` (durumlar, süreler, yazma yöntemi; dikte edilen metin yazılmaz). Kullanıcı denemelerinden sonra sonucu buradan oku.
- `uv add <paket>`: bağımlılık ekler. `pip install` kullanma.
- `uv run speak-to-print --uninstall`: Kickoff kaydını, simgeyi ve KWin pencere kurallarını kaldırır (ayarlar, geçmiş, günlük ve model kalır).
- `uv run pytest`: birim testleri (durum makinesi, uydurma metin önlemi); ekran, mikrofon ve model gerektirmez.

## Nerede ne var
- `README.md`: yeni bir bilgisayara kurulum, güncelleme ve kaldırma adımları (kullanıcı için). Kurulum adımları değişirse burayı da güncelle.
- `docs/tasarim.md`: görsel dil (matbaa fikri, renkler, yazı tipleri, ilkeler). Arayüze dokunmadan önce oku.
- `docs/model-karsilastirma.md`: Faz 0.4 sonuçları, model kararı ve açık konular (ipucu metni, sözlük, uydurma metin).
- `docs/plan.md`: onaylanmış plan. Kararların gerekçeleri, fazlar ve her denemenin geçme ölçütü burada.
- `src/speak_to_print/`: uygulama kodu. `tests/`: birim testleri. Faz 0'ın deneme betikleri (`spikes/`: GPU, mikrofon, model karşılaştırma, kısayol, yazma, pencere odağı) kullanıcının isteğiyle silindi; gerekirse git geçmişinden geri gelir: `git checkout a21d4f1 -- spikes`.
- `src/speak_to_print/app.py`: giriş noktası; parçaları oluşturup bağlar, tek kopya denetimi yapar (soket `/run/user/<kimlik>/<APP_ID>`, yalnızca bu hesap bağlanabilir; `/tmp`'ye taşıma: orada başka bir hesap aynı adı önceden alıp uygulamanın açılmasını engelleyebilir), açılışta Kickoff kaydını ve KWin kuralını günceller, kişisel veri klasörlerini (geçmiş, günlük, ayarlar) yalnızca bu kullanıcıya açar (`_private_dir`: klasör 0700, dosyalar 0600, sembolik bağlara dokunmaz).
- `src/speak_to_print/controller.py`: durum makinesi (`State`, `Outcome`); bağımlılıkları dışarıdan alır, `tests/test_controller.py` sahte nesnelerle sınar. Yeni davranış eklerken önce buraya ve teste bak.
- `src/speak_to_print/audio.py` (`Recorder`), `transcriber.py` (`Transcriber`, ayrı QThread), `textguard.py` (uydurma metin kalıpları; `single_line`: model çıktısındaki satır sonu ve denetim karakterlerini boşluğa çevirir, terminalde Enter gibi davranmasın; düzenleyiciden gelen metne uygulanmaz), `settings.py` (QSettings), `sounds.py` (başlama/bitiş sesleri; dosyalar `/run/user/<kimlik>/speak-to-print` altında üretilir, oturum klasörü yoksa adı rastgele ve yalnızca bu kullanıcıya açık bir geçici klasörde; `/tmp`'de sabit adlı klasör kullanma; `pw-play` ile çalınır), `history.py` (`History`: SQLite geçmişi, `~/.local/share/speak-to-print/history.db`), `config.py` (sabitler; `POPUP_TITLE`/`POPUP_SIZE` KWin kuralıyla eşleşmek zorunda).
- `src/speak_to_print/ui/`: `listening_popup.py` (odak almayan, sabit boyutlu küçük pencere), `editor_window.py` (odak alan düzenleme penceresi; küçük pencerenin üstünde açılır), `main_window.py`, `tray.py`, `settings_dialog.py` (ayarlar; değişiklikler anında `Settings`'e yazılır).
- `src/speak_to_print/ui/theme.py` (renkler, `ui_font`/`text_font`, ortak stil) ve `ui/widgets.py` (`Waveform`, `PrintedText`, `CropFrame`, `Switch`, `Card`, `Keycap`, `Rule`, `HistoryDelegate`). Uygulama simgesi `assets/icon.svg`; tepsi simgesi `ui/tray.py`'de aynı biçim kodla, durum rengiyle çizilir. Yazı tipleri `assets/fonts/` altında (OFL). Arayüz sınıflarının sinyal, yöntem ve bileşen adları `tests/test_app_wiring.py` ile sabitlenmiştir; tasarımı değiştirirken bu adları koru.
- `src/speak_to_print/hotkey.py`: `PortalHotkeys` (QObject), XDG GlobalShortcuts portalını ayrı bir asyncio iş parçacığında dinler; `activated`/`deactivated`/`bound`/`failed` Qt sinyalleri verir.
- `src/speak_to_print/desktop_entry.py`: `APP_ID` (`io.github.perxie.SpeakToPrint`) ve Kickoff kaydını yazan `install()`/`ensure()`. Portal, kimliği bu `.desktop` dosyasının adından tanır. Simge, temaya (`~/.local/share/icons/hicolor/scalable/apps/<APP_ID>.svg`) kopyalanır ve kayıtta adıyla (`Icon=<APP_ID>`) verilir: dosya yolu verilirse Kickoff'taki kısayol listesi gibi yerler simgeyi bulamıyor.
- `src/speak_to_print/output/`: `kwin_type.type_text()` ve `clipboard_paste.ClipboardPaster` (panoyu saklar, `--sensitive` ile ayarlar, sanal klavyeden yapıştırma tuşuna basar, geri yükler). Sanal klavyeyi oluşturmak ~2 sn sürer; bir kez oluşturup yeniden kullan.
- `src/speak_to_print/kwin_rules.py`: dinleme penceresi (odak almaz) ve düzenleme penceresi (odak alır) için KWin pencere kurallarını (her zaman üstte, konum) `~/.config/kwinrulesrc`'ye yazar/siler. Pencere, uygulama kimliği ve tam başlıkla eşleşir. KDE araçları (`kwriteconfig6`, `qdbus6`) zaman aşımıyla çağrılır; yanıt vermezlerse ya da hata verirlerse `RuntimeError` döner, açılış bunu günlüğe yazıp devam eder.
- `src/speak_to_print/cuda_libs.py`: `preload_cuda_libraries()`, pip'ten gelen cuBLAS'ı `LD_LIBRARY_PATH` olmadan yükler. GPU'da model oluşturmadan önce çağrılmalı.

## Önemli kararlar (ayrıntı: `docs/plan.md`)
- Python 3.14, uv'nin kendi kopyası (`[tool.uv] python-preference = "only-managed"`). Sistem Python'u kullanılmaz; pacman güncellemesi `.venv`'i bozmasın.
- Konuşma tanıma: faster-whisper + ctranslate2, GPU'da (RTX 4070, 12 GB). Varsayılan model `large-v3` (`float16`, `language="tr"`), kullanıcı seçti. Daha hızlı ama daha az doğru modeller (turbo gibi) istenmiyor; yalnızca daha doğru bir model çıkarsa eklenir. Gerekçe ve ölçümler: `docs/model-karsilastirma.md`.
- Arayüz ve mikrofon: PySide6 (Qt 6, QtMultimedia). Bağımlılık `pyside6-addons`; `pyside6` üst paketi gereksiz WebEngine'i de indiriyor. D-Bus: dbus-fast.
- Global kısayol: XDG GlobalShortcuts portalı (kullanıcının tuşu Shift+Pause).
- Metni yazma: varsayılan `kwin-type` (1–2 ms, panoya dokunmaz, izin penceresi yok). Hata verirse otomatik yedek pano + Shift+Insert (~0,5 sn). İkisi de Türkçe Q, Türkçe F ve İngilizce (US) düzenlerinde denendi ve doğru çalıştı; pano + Ctrl+V ise Türkçe F'de çalışmıyor.
- Pano yönteminde eski pano yapıştırmadan 0,4 sn sonra geri konur; parola yöneticisinin işaretlediği (`x-kde-passwordManagerHint`) içerik ise hiç geri konmaz, pano boşaltılır. Geri konsa, panoyu geç okuyan yavaş bir uygulama dikte yerine parolayı yapıştırır ve parola işaretsiz kalıp Klipper geçmişine düşerdi. Geri yükleme hata yolunda da (`finally`) yapılır.
- Uygulama servis değildir: otomatik başlama yok, pencere kapanınca tamamen kapanır.
- Küçük (dinleme) penceresi odak almadığı için içine klavyeyle yazılamaz: metin orada yalnızca gösterilir. Metne ya da Düzenle'ye tıklanınca odak alan düzenleme penceresi açılır; oradaki Yapıştır pencereyi kapatır ve odak önceki uygulamaya dönünce yazar (`Application._paste_from_editor`).
- Sözlük, ipucu metninin başına "Terimler: a, b, c." satırı olarak verilir (`config.build_prompt`); `hotwords` parametresi kullanılmaz (ölçümde işe yaramadı). Kısa listede etkili, uzun listede etkisiz.
- Kayıt `config.MAX_RECORDING_SECONDS` (10 dk, kullanıcı seçti) süresine ulaşınca dinleme Bitir'e basılmış gibi bitirilir ve çevrilir; kayıt atılmaz, sonuç notunun başında neden bittiği yazar. Amaç gizlilik (açık unutulan dinleme); ekran kartı belleği kayıt uzunluğuyla büyümez (faster-whisper sesi 30 sn'lik parçalarla sırayla işler).
- Otomatik yapıştırma kullanıcı ayarıdır (varsayılan açık). Kapalıyken metin yalnızca gösterilir; küçük pencere metin alınana kadar kendiliğinden kapanmaz.

## Dikkat
- ctranslate2 4.9.0 cuBLAS'ı CUDA 12 olarak (`libcublas.so.12`) çalışma anında açıyor; cuDNN gerekmiyor. Bu yüzden bağımlılık `nvidia-cublas-cu12`.
- `av` 19'dan küçük sürüme sabit: faster-whisper 1.2.1'in ses okuma kodu PyAV 19'da kaldırılan `metadata_errors` parametresini kullanıyor. faster-whisper yeni sürüm çıkarınca sınır kalkabilir.
- Wayland'de X11 araçları (`xdotool`) çalışmaz; `wtype` KWin'de çalışmaz; `ydotool` Türkçe Q'da yanlış harf yazar.
- Kullanıcı Türkçe Q, Türkçe F ve bir İngilizce düzen kullanabilir. Tuş koduna dayalı her şey düzenden bağımsız olmalı (Türkçe F'de ABD'deki V tuşu `c` yazar).
- Kickoff'tan açılan program terminaldeki ortam değişkenlerini görmez. (Faz 0.5'te denendi: Kickoff'tan açılışta model GPU'ya yükleniyor, kısayol çalışıyor.)
- Portal kısayolu: `BindShortcuts` ilk seferde tuş atanmamış (`''`) dönebiliyor; tuş `ConfigureShortcuts` penceresinden atanıyor ve `ShortcutsChanged` ile geliyor. Ctrl+Pause seçilince KDE yalnızca "Control" kaydetti ve bozuk çalıştı (klavyede Ctrl+Pause ayrı bir "Break" tuşu); kullanıcının kısayolu Shift+Pause.
- Wayland'de Qt'nin `WindowDoesNotAcceptFocus` ve `WA_ShowWithoutActivating` ayarları tek başına işe yaramıyor: pencere açılınca odağı alıyor. Odak almayan pencere için KWin pencere kuralı gerekiyor. Qt pencerenin ekrandaki yerini de bilmiyor (konum hep 0,0 görünür).
- KWin 6.8, `kwinrulesrc`'de kural listesini `[General] Order=` anahtarında tutuyor (eski `count=`/`rules=` biçimini yüklerken çeviriyor); `kreadconfig6` bu dosyanın `[General]` bölümünü boş döndürüyor.
- Dışarıdan gelen metni (model çıktısı, mikrofon adı, hata iletisi) gösteren `QLabel`'lara `setTextFormat(Qt.TextFormat.PlainText)` ver; Qt'nin varsayılanı HTML'ye benzeyen metni biçimli gösterir. İpucu balonu için `main_window._literal_tooltip`. Hangi etiketlerin düz metin olduğu `tests/test_app_wiring.py`'de sabit.
- Uygulama KDE temasını kullanmaz; kendi koyu temasını uygular (`theme.apply`). Yazı tipleri değişken (variable) olduğu için ağırlık `QFont.setVariableAxis("wght", …)` ile verilir; stil sayfasına `font-*` yazma, yoksa kodla atanan yazı tipini ezer.
- Mikrofon yokken sistemin varsayılan ses kaynağı bir *monitor* olabilir; mikrofon sanılmamalı.
- Mikrofon kayıt sırasında çıkarılınca `QAudioSource` hata bildirmiyor (ses sistemi akışı sessizce başka aygıta taşıyor); kayıp, `QMediaDevices.audioInputsChanged` ile aygıt listesinden izleniyor (`Recorder._on_inputs_changed`). `QAudioSource.stateChanged` sinyaline Python işlevi bağlama: bu PySide sürümünde `QAudio::State` çevrilemiyor ve her durum değişiminde TypeError basıyor.
- Uygulama seslerini `QSoundEffect` ile çalma: Qt bu akışları `media.role=event` (bildirim) olarak işaretliyor ve kullanıcının KDE'sinde bildirim sesleri sessizde, hiç duyulmuyor. `sounds.py` sesleri `pw-play` ile çalar. Ses denemelerinde çıkışın monitörünü dinleyip tepe seviyesine bakma (kullanıcının o an dinlediği ses de karışır); akışın kendi özelliklerine bak: `pactl -f json list sink-inputs` (rol, sessiz, hedef).
- Kullanıcının sayı biçimi Türkçe (`LC_NUMERIC=tr_TR`, ondalık virgül): dış programlara ondalıklı sayı argümanı verme; ses yüksekliği bu yüzden dosyanın içine işleniyor.
- Bir süredir ses çalmayan çıkış aygıtı (özellikle Bluetooth) sesin ilk anını yutabilir; `sounds.py` her sesin başına 0,25 sn sessizlik koyuyor.
- BTD 700 (Bluetooth) mikrofonu açıldıktan sonraki ilk yaklaşık yarım saniyeyi kaçırabiliyor; kayıt sırasında kulaklığın ses kalitesi de düşüyor. Kullanıcı ikisini de kabul etti: mikrofonu sürekli açık tutma ya da bu gecikmeyi gidermeye uğraşma.
- Whisper kısık ya da uzak seste metin uydurabiliyor: bilinen altyazı kalıpları ("Altyazı M.K.") ya da kendisine verilen ipucu metninin karışık bir tekrarı. İkisi de `textguard.py`'de yakalanıp yazılmıyor; modelin güven değerleri bunları ayırt etmiyor. İpucu metnini değiştirirsen yankı önlemini gerçek kayıtlarla yeniden sına.
- `language="tr"` ile tamamı İngilizce bir cümle Türkçeye çevriliyor; cümle içindeki İngilizce terimler ve kısa İngilizce cümleler ise korunuyor.
- Modeller `~/.cache/huggingface`'ta durur; model dosyaları ve ses kayıtları git'e girmez.
- `uv` komutlarını `XDG_DATA_HOME` değiştirilmiş bir ortamda çalıştırma: uv kendi Python'unu orada arar, bulamayınca yenisini indirip `.venv`'i ona bağlayarak yeniden kurar. Denemelerde uygulamanın klasörlerini ayırmak gerekiyorsa `.venv/bin/python` ya da `.venv/bin/speak-to-print` ile çalıştır.
- Ekran kartı kullanılamazsa model işlemciye (`int8`) yüklenir: 8 sn ses yaklaşık 4 sn'de çevrilir. Model önbellekte yoksa bir kez indirilir; `download_model(local_files_only=True)` ağa çıkmaz, bu yüzden `HF_HUB_OFFLINE` kullanılmıyor.
- Kullanıcının kabuğu fish: ortamı elle etkinleştirmek için `source .venv/bin/activate.fish`.

## Sürümler
- `v1.0.0` (17 Kasım 2026): bütün fazları (0–5) tamamlanmış, kullanıcının onayladığı kararlı sürüm. Bir şey bozulursa dönülecek nokta bu etiket.
- Bir dosyayı bu sürümdeki hâline döndürmek: `git checkout v1.0.0 -- <dosya>`. Bu sürümden sonraki bütün değişiklikleri görmek: `git diff v1.0.0`.
- Kurulumda inen üç şey denenmiş sürüme sabit; kendiliğinden güncellenmez, bilerek değiştirilir:
  - Model: `config.MODEL_REVISION` (Hugging Face `Systran/faster-whisper-large-v3` commit'i). Yenisine geçmek için modeli o commit'le indirip dene, sonra kimliği değiştir.
  - kwin-type: README'deki `git checkout <commit>` satırı (şu an v0.2, `0bc344b`). Yenisi için `git -C ~/.local/src/kwin-type fetch`, değişikliklere bak, derleyip dene, sonra README'yi güncelle.
  - Python paketleri: `uv.lock`. README'de `uv sync --locked` (kilit `pyproject.toml` ile uyuşmazsa hata verir). Geliştirirken `uv add`/`uv lock` kilidi günceller.
- Projenin tamamını bu sürüme döndürmek (`git reset --hard v1.0.0`) sonraki commit'leri siler; yalnızca kullanıcı açıkça isterse yap. Geri dönüşte `uv sync` çalıştır.

## Çalışma kuralları
- Her aşamanın sonunda kullanıcıya test tarifi ver. Kullanıcı deneyip onaylayınca commit et, `git push` ile GitHub'a gönder (herkese açık repo `Perxie/speak-to-print`, remote `origin`; kullanıcı bilerek açtı) ve bir sonraki aşamaya geçmeden onay bekle.
- Kullanıcı Java biliyor, Python ve Linux'ta yeni: Python'a özgü kavramları kısaca, Java karşılığıyla anlat.
- Depo herkese açık: kişisel veriyi (ses kayıtları, dikte geçmişi, ekran görüntüleri, gerçek e-posta, ad) commit etme. Commit kimliği GitHub'ın gizli adresi (`…@users.noreply.github.com`).
- sudo gerektiren bir adımdan ve proje klasörü dışına yazmadan önce kullanıcıya söyle. Proje dışına yazılan ve yeniden başlatınca silinmeyen her şeyi `docs/proje-disi-dosyalar.md`'ye ekle; kullanıcı iş bitince bunları silmek istiyor.
- Kullanıcı GitHub'ı hiç kullanmadı: GitHub'la ilgili her adımı, hiçbir şey bilmiyormuş gibi, neyin ne olduğunu ve neden yapıldığını anlatarak açıkla. Parola ya da token isteme; giriş `gh auth login` ile kullanıcının kendi tarayıcısında yapılır.

## İlerleme
- Geliştirme işine başlamadan önce `PROGRESS.md`'yi oku.
- Bir iş parçası biter bitmez `PROGRESS.md`'deki "Şu an" bölümünü güncelle (ekleme, üstüne yaz) ve biten maddeyi `[x]` yap. Yazmadan hemen önce dosyayı yeniden oku; başka bir oturum değiştirmiş olabilir.
