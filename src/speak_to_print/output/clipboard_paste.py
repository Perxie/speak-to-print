"""Pano + yapıştırma tuşu ile yazma.

Adımlar: panodaki metni sakla → metnimizi panoya koy → sanal klavyeden
yapıştırma tuşuna bas → kısa bir süre bekle → eski panoyu geri yükle.
Geri yükleme, arada bir hata çıksa da yapılır.

Geri yükleme sabit bir beklemeden sonra yapılır; panoyu bundan geç okuyan
yavaş bir uygulama dikte yerine eski içeriği yapıştırır. Bu yüzden parola
yöneticisinden gelen gizli içerik (`x-kde-passwordManagerHint`) hiç geri
yüklenmez, pano boşaltılır: yavaş bir uygulama en kötü ihtimalle boş yapıştırır.
Parola yöneticisi o içeriği zaten birkaç saniye içinde temizleyecekti.

Her Unicode karakter doğru çıkar, çünkü karakterler tuş olarak değil pano
üzerinden gider. Düzene bağlı tek şey yapıştırma tuşudur:
  - "shift+insert": harf içermez, klavye düzeninden bağımsızdır.
  - "ctrl+v": ABD/Türkçe Q düzeninde V'nin olduğu fiziksel tuşu kullanır;
    Türkçe F'de o tuş `c` yazdığı için Ctrl+C'ye dönüşür.

Sanal klavye /dev/uinput üzerinden oluşturulur (python-evdev). Oturum
kullanıcısının buna yazma izni udev'deki `uaccess` kuralından gelir.
"""

from __future__ import annotations

import logging
import subprocess
import time

from evdev import UInput
from evdev import ecodes as e

from . import OutputError

log = logging.getLogger(__name__)

PASTE_KEYS: dict[str, tuple[int, int]] = {
    "shift+insert": (e.KEY_LEFTSHIFT, e.KEY_INSERT),
    "ctrl+v": (e.KEY_LEFTCTRL, e.KEY_V),
}


TEXT_TYPES = ("text/plain;charset=utf-8", "text/plain", "UTF8_STRING", "STRING", "TEXT")

# Parola yöneticilerinin ve `wl-copy --sensitive`'in koyduğu işaret; Klipper
# bu işareti taşıyan içeriği geçmişine almaz.
SECRET_HINT = "x-kde-passwordManagerHint"


def _get(primary: bool) -> tuple[str, bytes] | None:
    """Geri yüklenecek pano içeriğini (tür, veri) olarak döndürür.

    Metin varsa metni, yoksa (ör. kopyalanmış bir resim) ilk türü saklar;
    böylece geri yüklerken içerik bozulmaz. Pano boşsa ya da içerik parola
    yöneticisinden gelen gizli bir içerikse None döner: pano boş bırakılır.
    """
    selection = ["--primary"] if primary else []
    listing = subprocess.run(["wl-paste", "--list-types", *selection], capture_output=True, timeout=5, check=False)
    types = listing.stdout.decode(errors="replace").split()
    if listing.returncode != 0 or not types or SECRET_HINT in types:
        return None
    mime = next((t for t in TEXT_TYPES if t in types), types[0])
    result = subprocess.run(["wl-paste", "--no-newline", "--type", mime, *selection],
                            capture_output=True, timeout=5, check=False)
    return (mime, result.stdout) if result.returncode == 0 else None


def _set(content: tuple[str, bytes] | None, primary: bool, sensitive: bool = False) -> None:
    command = ["wl-copy"] + (["--primary"] if primary else [])
    if content is None:
        command.append("--clear")
    else:
        command += ["--type", content[0]]
        if sensitive:
            command.append("--sensitive")  # pano geçmişine (Klipper) alınmasın diye ipucu
    # wl-copy panoyu sunmak için arka planda çalışmaya devam eder. Çıktısını
    # yakalarsak o süreç bitene kadar bekleriz; bu yüzden çıktı yok sayılır.
    result = subprocess.run(command, input=content[1] if content is not None else None,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5, check=False)
    if result.returncode != 0:
        raise OutputError("Pano ayarlanamadı (wl-copy hata verdi).")


def _restore(saved: dict[bool, tuple[str, bytes] | None]) -> None:
    """Saklanan panoyu geri koyar. Hata yalnızca günlüğe yazılır: metin zaten yapıştırılmış olabilir."""
    for primary, old in saved.items():
        try:
            _set(old, primary)
        except (OutputError, subprocess.TimeoutExpired, OSError) as error:
            log.warning("Eski pano geri yüklenemedi: %s", error)


class ClipboardPaster:
    """Sanal klavyeyi bir kez oluşturur ve her yapıştırmada yeniden kullanır."""

    def __init__(self, keys: str = "shift+insert", restore_delay: float = 0.4) -> None:
        if keys not in PASTE_KEYS:
            raise ValueError(f"Bilinmeyen yapıştırma tuşu: {keys}")
        self._keys = PASTE_KEYS[keys]
        self._restore_delay = restore_delay
        try:
            self._device = UInput({e.EV_KEY: [code for pair in PASTE_KEYS.values() for code in pair]},
                                  name="speak-to-print sanal klavye")
        except OSError as error:
            raise OutputError(f"Sanal klavye oluşturulamadı (/dev/uinput): {error}") from error
        self._created_at = time.monotonic()

    def close(self) -> None:
        self._device.close()

    def _press_paste(self) -> None:
        # Yeni oluşan klavyeyi masaüstünün tanıması biraz sürer; ilk kullanımda bekle.
        wait = 0.5 - (time.monotonic() - self._created_at)
        if wait > 0:
            time.sleep(wait)
        pressed: list[int] = []
        try:
            for code in self._keys:
                self._send(code, 1)
                pressed.append(code)
        finally:
            # Arada hata olsa da basılan tuşları bırak; yoksa Shift basılı kalır.
            release_error: OSError | None = None
            for code in reversed(pressed):
                try:
                    self._send(code, 0)
                except OSError as error:
                    release_error = release_error or error
            if release_error is not None:
                raise release_error

    def _send(self, code: int, value: int) -> None:
        self._device.write(e.EV_KEY, code, value)
        self._device.syn()
        time.sleep(0.01)

    def paste(self, text: str) -> None:
        """Metni o an etkin olan pencereye yapıştırır ve eski panoyu geri yükler."""
        if not text:
            return
        try:
            saved = {primary: _get(primary) for primary in (False, True)}
        except subprocess.TimeoutExpired as error:
            raise OutputError("Pano araçları (wl-copy/wl-paste) yanıt vermedi.") from error
        except OSError as error:
            raise OutputError(f"Pano okunamadı: {error}") from error
        content = ("text/plain;charset=utf-8", text.encode("utf-8"))
        try:
            # Shift+Insert bazı uygulamalarda "seçim" panosundan yapıştırır; ikisini de ayarla.
            for primary in (False, True):
                _set(content, primary, sensitive=True)
            time.sleep(0.05)
            self._press_paste()
            time.sleep(self._restore_delay)  # hedef uygulama panoyu okusun
        except subprocess.TimeoutExpired as error:
            raise OutputError("Pano araçları (wl-copy/wl-paste) yanıt vermedi.") from error
        except OSError as error:
            raise OutputError(f"Yapıştırılamadı (pano ya da sanal klavye): {error}") from error
        finally:
            _restore(saved)


def copy_text(text: str) -> None:
    """Metni panoya kopyalar (kullanıcı Kopyala'ya bastığında).

    wl-copy, penceremiz odakta olmasa da çalışır; Qt'nin kendi panosu Wayland'de
    yalnızca odaktaki pencereden yazabilir.
    """
    try:
        _set(("text/plain;charset=utf-8", text.encode("utf-8")), primary=False)
    except subprocess.TimeoutExpired as error:
        raise OutputError("Pano aracı (wl-copy) yanıt vermedi.") from error
    except OSError as error:
        raise OutputError(f"Pano aracı (wl-copy) çalıştırılamadı: {error}") from error
