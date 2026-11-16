# speak-to-print

Kişisel kullanım için, KDE Plasma 6 (Wayland) üzerinde tamamen yerel çalışan bir dikte uygulaması: konuşmayı yazıya çevirir, ses hiçbir bulut servisine gönderilmez. Konuşma çoğunlukla Türkçedir ama cümle ortalarında İngilizce terimler geçer; Türkçe karakterler ve noktalama doğru olmalıdır. Kickoff'tan "Speak to Print" diye açılır, kısayolla dinler, metni imlecin olduğu yere yazar ve kendi penceresinde düzenlenebilir gösterir.

## Komutlar
- `uv sync`: `.venv`'i `pyproject.toml` ve `uv.lock`'a göre kurar ya da günceller.
- `uv run speak-to-print`: uygulamayı çalıştırır.
- `uv add <paket>`: bağımlılık ekler. `pip install` kullanma.
- `uv run python spikes/gpu_check.py [--model large-v3-turbo]`: modeli GPU'da dener, hızı ve bellek kullanımını ölçer.
- `uv run python spikes/mic_check.py [--list] [--device "USB PnP"] [--seconds 10]`: mikrofondan kayıt alır, seviyeyi ölçer, Türkçe yazıya çevirir.
- `uv run python spikes/record_set.py [--device "USB PnP"] [--redo 5] [--status]`: `spikes/sentences_tr.txt` cümlelerini `recordings/set/` altına kaydeder.
- `uv run python spikes/model_compare.py [--models large-v3 ...]`: kayıtları aday modellerle çevirir, `recordings/set/report.md` raporunu yazar.
- `uv run python spikes/hotkey_check.py [--install-desktop | --uninstall-desktop] [--no-model]`: portal kısayolunu ve Kickoff'tan açılışı deneyen pencere; günlüğü `spikes/data/hotkey_check.log`.
- `uv run python spikes/type_check.py`: test cümlesini seçilen yöntemle etkin pencereye yazar (etkileşimli); günlüğü `spikes/data/type_check.log`.
- `uv run python spikes/popup_check.py [--probe | --install-rule | --remove-rule]`: dinleme penceresinin odağı çalıp çalmadığını dener; günlüğü `spikes/data/popup_check.log`.

## Nerede ne var
- `docs/model-karsilastirma.md`: Faz 0.4 sonuçları, model kararı ve açık konular (ipucu metni, sözlük, uydurma metin).
- `docs/plan.md`: onaylanmış plan. Kararların gerekçeleri, fazlar ve her denemenin geçme ölçütü burada.
- `src/speak_to_print/`: uygulama kodu. `spikes/`: Faz 0 deneme betikleri (uygulamaya dahil değil); `spikes/data/` git dışı.
- `src/speak_to_print/hotkey.py`: `PortalHotkeys` (QObject), XDG GlobalShortcuts portalını ayrı bir asyncio iş parçacığında dinler; `activated`/`deactivated`/`bound`/`failed` Qt sinyalleri verir.
- `src/speak_to_print/desktop_entry.py`: `APP_ID` (`io.github.perxie.SpeakToPrint`) ve Kickoff kaydını yazan `install()`. Portal, kimliği bu `.desktop` dosyasının adından tanır.
- `src/speak_to_print/output/`: `kwin_type.type_text()` ve `clipboard_paste.ClipboardPaster` (panoyu saklar, `--sensitive` ile ayarlar, sanal klavyeden yapıştırma tuşuna basar, geri yükler). Sanal klavyeyi oluşturmak ~2 sn sürer; bir kez oluşturup yeniden kullan.
- `src/speak_to_print/kwin_rules.py`: dinleme penceresi için KWin pencere kuralını (odak alma, her zaman üstte, konum) `~/.config/kwinrulesrc`'ye yazar/siler. Pencere, uygulama kimliği ve tam başlıkla eşleşir.
- `src/speak_to_print/cuda_libs.py`: `preload_cuda_libraries()`, pip'ten gelen cuBLAS'ı `LD_LIBRARY_PATH` olmadan yükler. GPU'da model oluşturmadan önce çağrılmalı.

## Önemli kararlar (ayrıntı: `docs/plan.md`)
- Python 3.14, uv'nin kendi kopyası (`[tool.uv] python-preference = "only-managed"`). Sistem Python'u kullanılmaz; pacman güncellemesi `.venv`'i bozmasın.
- Konuşma tanıma: faster-whisper + ctranslate2, GPU'da (RTX 4070, 12 GB). Varsayılan model `large-v3` (`float16`, `language="tr"`), kullanıcı seçti. Daha hızlı ama daha az doğru modeller (turbo gibi) istenmiyor; yalnızca daha doğru bir model çıkarsa eklenir. Gerekçe ve ölçümler: `docs/model-karsilastirma.md`.
- Arayüz ve mikrofon: PySide6 (Qt 6, QtMultimedia). Bağımlılık `pyside6-addons`; `pyside6` üst paketi gereksiz WebEngine'i de indiriyor. D-Bus: dbus-fast.
- Global kısayol: XDG GlobalShortcuts portalı (kullanıcının tuşu Shift+Pause).
- Metni yazma: varsayılan `kwin-type` (1–2 ms, panoya dokunmaz, izin penceresi yok). Hata verirse otomatik yedek pano + Shift+Insert (~0,5 sn). İkisi de Türkçe Q, Türkçe F ve İngilizce (US) düzenlerinde denendi ve doğru çalıştı; pano + Ctrl+V ise Türkçe F'de çalışmıyor.
- Uygulama servis değildir: otomatik başlama yok, pencere kapanınca tamamen kapanır.

## Dikkat
- ctranslate2 4.9.0 cuBLAS'ı CUDA 12 olarak (`libcublas.so.12`) çalışma anında açıyor; cuDNN gerekmiyor. Bu yüzden bağımlılık `nvidia-cublas-cu12`.
- `av` 19'dan küçük sürüme sabit: faster-whisper 1.2.1'in ses okuma kodu PyAV 19'da kaldırılan `metadata_errors` parametresini kullanıyor. faster-whisper yeni sürüm çıkarınca sınır kalkabilir.
- Wayland'de X11 araçları (`xdotool`) çalışmaz; `wtype` KWin'de çalışmaz; `ydotool` Türkçe Q'da yanlış harf yazar.
- Kullanıcı Türkçe Q, Türkçe F ve bir İngilizce düzen kullanabilir. Tuş koduna dayalı her şey düzenden bağımsız olmalı (Türkçe F'de ABD'deki V tuşu `c` yazar).
- Kickoff'tan açılan program terminaldeki ortam değişkenlerini görmez. (Faz 0.5'te denendi: Kickoff'tan açılışta model GPU'ya yükleniyor, kısayol çalışıyor.)
- Portal kısayolu: `BindShortcuts` ilk seferde tuş atanmamış (`''`) dönebiliyor; tuş `ConfigureShortcuts` penceresinden atanıyor ve `ShortcutsChanged` ile geliyor. Ctrl+Pause seçilince KDE yalnızca "Control" kaydetti ve bozuk çalıştı (klavyede Ctrl+Pause ayrı bir "Break" tuşu); kullanıcının kısayolu Shift+Pause.
- Wayland'de Qt'nin `WindowDoesNotAcceptFocus` ve `WA_ShowWithoutActivating` ayarları tek başına işe yaramıyor: pencere açılınca odağı alıyor. Odak almayan pencere için KWin pencere kuralı gerekiyor. Qt pencerenin ekrandaki yerini de bilmiyor (konum hep 0,0 görünür).
- KWin 6.8, `kwinrulesrc`'de kural listesini `[General] Order=` anahtarında tutuyor (eski `count=`/`rules=` biçimini yüklerken çeviriyor); `kreadconfig6` bu dosyanın `[General]` bölümünü boş döndürüyor.
- pip'ten gelen PySide6, KDE'nin Breeze görünümünü almıyor (görünüm `fusion`); yalnızca görsel fark.
- Mikrofon yokken sistemin varsayılan ses kaynağı bir *monitor* olabilir; mikrofon sanılmamalı.
- BTD 700 (Bluetooth) mikrofonu açıldıktan sonraki ilk yaklaşık yarım saniyeyi kaçırabiliyor; kayıt sırasında kulaklığın ses kalitesi de düşüyor. Kullanıcı ikisini de kabul etti: mikrofonu sürekli açık tutma ya da bu gecikmeyi gidermeye uğraşma.
- Whisper kısık ya da uzak seste metin uydurabiliyor ("Altyazı M.K." gözlendi); boş sayılması gereken kayıtlar için önlem gerekli. Modelin güven değerleri bunu ayırt etmiyor.
- `language="tr"` ile tamamı İngilizce bir cümle Türkçeye çevriliyor; cümle içindeki İngilizce terimler ve kısa İngilizce cümleler ise korunuyor.
- Modeller `~/.cache/huggingface`'ta durur; model dosyaları ve ses kayıtları git'e girmez.
- Kullanıcının kabuğu fish: ortamı elle etkinleştirmek için `source .venv/bin/activate.fish`.

## Çalışma kuralları
- Her aşamanın sonunda kullanıcıya test tarifi ver. Kullanıcı deneyip onaylayınca commit et, `git push` ile GitHub'a gönder (gizli repo `Perxie/speak-to-print`, remote `origin`) ve bir sonraki aşamaya geçmeden onay bekle.
- Kullanıcı Java biliyor, Python ve Linux'ta yeni: Python'a özgü kavramları kısaca, Java karşılığıyla anlat.
- sudo gerektiren bir adımdan ve proje klasörü dışına yazmadan önce kullanıcıya söyle. Proje dışına yazılan ve yeniden başlatınca silinmeyen her şeyi `docs/proje-disi-dosyalar.md`'ye ekle; kullanıcı iş bitince bunları silmek istiyor.
- Kullanıcı GitHub'ı hiç kullanmadı: GitHub'la ilgili her adımı, hiçbir şey bilmiyormuş gibi, neyin ne olduğunu ve neden yapıldığını anlatarak açıkla. Parola ya da token isteme; giriş `gh auth login` ile kullanıcının kendi tarayıcısında yapılır.

## Ajan kullanımı
- Planlamayı ve kritik kodu kendin yap.
- Ajanlara (Opus 5.5) sadece birbirinden bağımsız ve eksiksiz tarif edebildiğin işleri ver; tarife gerekli tüm bağlamı yaz.
- Ajanlardan dönen her işi kabul etmeden önce gözden geçir ve test et.

## İlerleme
- Geliştirme işine başlamadan önce `PROGRESS.md`'yi oku.
- Bir iş parçası biter bitmez `PROGRESS.md`'deki "Şu an" bölümünü güncelle (ekleme, üstüne yaz) ve biten maddeyi `[x]` yap. Yazmadan hemen önce dosyayı yeniden oku; başka bir oturum değiştirmiş olabilir.
