# speak-to-print

Kişisel kullanım için, KDE Plasma 6 (Wayland) üzerinde tamamen yerel çalışan bir dikte uygulaması: konuşmayı yazıya çevirir, ses hiçbir bulut servisine gönderilmez. Konuşma çoğunlukla Türkçedir ama cümle ortalarında İngilizce terimler geçer; Türkçe karakterler ve noktalama doğru olmalıdır. Kickoff'tan "Speak to Print" diye açılır, kısayolla dinler, metni imlecin olduğu yere yazar ve kendi penceresinde düzenlenebilir gösterir.

## Komutlar
- `uv sync`: `.venv`'i `pyproject.toml` ve `uv.lock`'a göre kurar ya da günceller.
- `uv run speak-to-print`: uygulamayı çalıştırır.
- `uv add <paket>`: bağımlılık ekler. `pip install` kullanma.
- `uv run python spikes/gpu_check.py [--model large-v3-turbo]`: modeli GPU'da dener, hızı ve bellek kullanımını ölçer.
- `uv run python spikes/mic_check.py [--list] [--device "USB PnP"] [--seconds 10]`: mikrofondan kayıt alır, seviyeyi ölçer, Türkçe yazıya çevirir.

## Nerede ne var
- `docs/plan.md`: onaylanmış plan. Kararların gerekçeleri, fazlar ve her denemenin geçme ölçütü burada.
- `src/speak_to_print/`: uygulama kodu. `spikes/`: Faz 0 deneme betikleri (uygulamaya dahil değil); `spikes/data/` git dışı.
- `src/speak_to_print/cuda_libs.py`: `preload_cuda_libraries()`, pip'ten gelen cuBLAS'ı `LD_LIBRARY_PATH` olmadan yükler. GPU'da model oluşturmadan önce çağrılmalı.

## Önemli kararlar (ayrıntı: `docs/plan.md`)
- Python 3.14, uv'nin kendi kopyası (`[tool.uv] python-preference = "only-managed"`). Sistem Python'u kullanılmaz; pacman güncellemesi `.venv`'i bozmasın.
- Konuşma tanıma: faster-whisper + ctranslate2, GPU'da (RTX 4070, 12 GB). Model, Faz 0.4'teki karşılaştırmayla seçilir.
- Arayüz ve mikrofon: PySide6 (Qt 6, QtMultimedia). Bağımlılık `pyside6-addons`; `pyside6` üst paketi gereksiz WebEngine'i de indiriyor. D-Bus: dbus-fast.
- Global kısayol: XDG GlobalShortcuts portalı. Metni yazma: kwin-type ya da pano + yapıştırma tuşu (Faz 0.6'da seçilir).
- Uygulama servis değildir: otomatik başlama yok, pencere kapanınca tamamen kapanır.

## Dikkat
- ctranslate2 4.9.0 cuBLAS'ı CUDA 12 olarak (`libcublas.so.12`) çalışma anında açıyor; cuDNN gerekmiyor. Bu yüzden bağımlılık `nvidia-cublas-cu12`.
- `av` 19'dan küçük sürüme sabit: faster-whisper 1.2.1'in ses okuma kodu PyAV 19'da kaldırılan `metadata_errors` parametresini kullanıyor. faster-whisper yeni sürüm çıkarınca sınır kalkabilir.
- Wayland'de X11 araçları (`xdotool`) çalışmaz; `wtype` KWin'de çalışmaz; `ydotool` Türkçe Q'da yanlış harf yazar.
- Kullanıcı Türkçe Q, Türkçe F ve bir İngilizce düzen kullanabilir. Tuş koduna dayalı her şey düzenden bağımsız olmalı (Türkçe F'de ABD'deki V tuşu `c` yazar).
- Kickoff'tan açılan program terminaldeki ortam değişkenlerini görmez.
- Mikrofon yokken sistemin varsayılan ses kaynağı bir *monitor* olabilir; mikrofon sanılmamalı.
- BTD 700 (Bluetooth) mikrofonu açıldıktan sonraki ilk yaklaşık yarım saniyeyi kaçırabiliyor; kayıt sırasında kulaklığın ses kalitesi de düşüyor. Kullanıcı ikisini de kabul etti: mikrofonu sürekli açık tutma ya da bu gecikmeyi gidermeye uğraşma.
- Whisper kısık ya da uzak seste metin uydurabiliyor ("Altyazı M.K." gözlendi); boş sayılması gereken kayıtlar için önlem gerekli.
- Modeller `~/.cache/huggingface`'ta durur; model dosyaları ve ses kayıtları git'e girmez.
- Kullanıcının kabuğu fish: ortamı elle etkinleştirmek için `source .venv/bin/activate.fish`.

## Çalışma kuralları
- Her aşamanın sonunda kullanıcıya test tarifi ver. Kullanıcı deneyip onaylayınca commit et, `git push` ile GitHub'a gönder (gizli repo `Perxie/speak-to-print`, remote `origin`) ve bir sonraki aşamaya geçmeden onay bekle.
- Kullanıcı Java biliyor, Python ve Linux'ta yeni: Python'a özgü kavramları kısaca, Java karşılığıyla anlat.
- sudo gerektiren bir adımdan ve proje klasörü dışına yazmadan önce kullanıcıya söyle.
- Kullanıcı GitHub'ı hiç kullanmadı: GitHub'la ilgili her adımı, hiçbir şey bilmiyormuş gibi, neyin ne olduğunu ve neden yapıldığını anlatarak açıkla. Parola ya da token isteme; giriş `gh auth login` ile kullanıcının kendi tarayıcısında yapılır.

## Ajan kullanımı
- Planlamayı ve kritik kodu kendin yap.
- Ajanlara (Opus 5.5) sadece birbirinden bağımsız ve eksiksiz tarif edebildiğin işleri ver; tarife gerekli tüm bağlamı yaz.
- Ajanlardan dönen her işi kabul etmeden önce gözden geçir ve test et.

## İlerleme
- Geliştirme işine başlamadan önce `PROGRESS.md`'yi oku.
- Bir iş parçası biter bitmez `PROGRESS.md`'deki "Şu an" bölümünü güncelle (ekleme, üstüne yaz) ve biten maddeyi `[x]` yap. Yazmadan hemen önce dosyayı yeniden oku; başka bir oturum değiştirmiş olabilir.
