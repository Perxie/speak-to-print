# Speak to Print

KDE Plasma 6 (Wayland) için tamamen yerel çalışan dikte uygulaması. Konuşmanızı yazıya çevirir ve
imlecin olduğu yere yazar. Konuşma Türkçedir; cümle içindeki İngilizce terimler korunur. Ses hiçbir
yere gönderilmez; internet yalnızca ilk kurulumda (paketler ve model) gerekir.

## Gerekenler

- Arch tabanlı bir Linux (CachyOS'ta denendi), KDE Plasma 6.8 ya da yenisi, Wayland oturumu.
- NVIDIA ekran kartı (RTX 4070'te denendi). Ekran kartı yoksa uygulama işlemciyle, daha yavaş çalışır.
- Yaklaşık 6 GB boş disk: model 3 GB, Python ortamı 2 GB.

## Yeni bir bilgisayara kurulum

Bu depoda yalnızca kod ve belgeler var. Model, Python ortamı, ayarlarınız ve geçmişiniz depoda
**yok**; ilk ikisi kurulumda yeniden oluşur.

1. Araçları kurun:

   ```
   sudo pacman -S git github-cli uv wl-clipboard base-devel libei
   ```

2. GitHub'a giriş yapın (depo gizli olduğu için gerekli; tarayıcıda onaylarsınız):

   ```
   gh auth login --hostname github.com --git-protocol https --web
   ```

3. Depoyu indirin ("clone": deponun bütün geçmişiyle birlikte bir kopyasını alır):

   ```
   gh repo clone Perxie/speak-to-print ~/myProjects/speak-to-print
   cd ~/myProjects/speak-to-print
   ```

4. Python ortamını kurun (uv, gereken Python sürümünü ve paketleri indirir; yaklaşık 2 GB):

   ```
   uv sync
   ```

5. `kwin-type` aracını derleyin. Uygulama metni bununla yazar; yoksa kendiliğinden panoyla
   yapıştırma yöntemine geçer (çalışır ama yarım saniye daha yavaştır):

   ```
   git clone https://git.zx2c4.com/kwin-type ~/.local/src/kwin-type
   make -C ~/.local/src/kwin-type
   install -Dm755 ~/.local/src/kwin-type/kwin-type ~/.local/bin/kwin-type
   ```

6. Uygulamayı bir kez terminalden açın:

   ```
   uv run speak-to-print
   ```

   İlk açılışta uygulama:
   - konuşma tanıma modelini indirir (yaklaşık 3 GB, bir kez),
   - Kickoff menüsüne "Speak to Print" kaydını ve simgesini ekler,
   - küçük pencereler için iki KWin pencere kuralı yazar.

7. Kısayolu atayın: ana penceredeki **Tuş seç** (ya da **Ayarlar → Kısayol → Değiştir**). Harf içermeyen bir tuş seçin
   (ör. Shift+Pause); Ctrl+Pause çalışmaz.

Bundan sonra uygulamayı Kickoff'tan "Speak to Print" diye açabilirsiniz.

Ayarlar, sözlük ve geçmiş yeni bilgisayara taşınmaz. Taşımak isterseniz eski bilgisayardan şu iki
klasörü kopyalayın: `~/.config/speak-to-print/` ve `~/.local/share/speak-to-print/`.

## Güncelleme

Başka bir bilgisayarda yapılan değişiklikleri almak için:

```
cd ~/myProjects/speak-to-print
git pull
uv sync
```

## Kaldırma

```
uv run speak-to-print --uninstall
```

Kickoff kaydını, simgeyi ve KWin kurallarını kaldırır. Proje dışında kalan her şeyin (model, ayarlar,
geçmiş, günlük) listesi ve silme yolları: [docs/proje-disi-dosyalar.md](docs/proje-disi-dosyalar.md).

## Geliştirme

- `uv run pytest`: birim testleri.
- `CLAUDE.md`: projenin yapısı, kararlar ve bilinen tuzaklar.
- `PROGRESS.md`: işin durumu. `docs/plan.md`: özgün plan. `docs/model-karsilastirma.md`: model ölçümleri.
- Günlük: `~/.local/state/speak-to-print/speak-to-print.log` (dikte edilen metin yazılmaz).
