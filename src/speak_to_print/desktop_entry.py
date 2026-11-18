"""Kickoff menü kaydı (.desktop dosyası).

Bu dosya iki işe yarar:
  - Uygulama Kickoff'ta "Speak to Print" adıyla görünür.
  - Portal, kısayolların hangi uygulamaya ait olduğunu bu dosyanın adından
    (uygulama kimliği) anlar; dosya yoksa Registry.Register reddedilir.

Uygulamanın simgesi de kullanıcının simge temasına, uygulama kimliğiyle
kopyalanır (~/.local/share/icons/hicolor/scalable/apps/). Masaüstünün bazı
bölümleri (ör. Kickoff'taki kısayol listesi) simgeyi dosya yolundan değil,
yalnızca adıyla temadan arar.

Dosyalar proje klasörünün dışına yazılır (bkz. docs/proje-disi-dosyalar.md).
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path

APP_ID = "io.github.perxie.SpeakToPrint"
APP_NAME = "Speak to Print"
ICON_PATH = Path(__file__).resolve().parent / "assets" / "icon.svg"


def _data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")


def desktop_file_path() -> Path:
    return _data_home() / "applications" / f"{APP_ID}.desktop"


def theme_icon_path() -> Path:
    return _data_home() / "icons" / "hicolor" / "scalable" / "apps" / f"{APP_ID}.svg"


def _icon_installed() -> bool:
    target = theme_icon_path()
    return target.exists() and target.read_bytes() == ICON_PATH.read_bytes()


def _install_icon() -> None:
    target = theme_icon_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ICON_PATH, target)
    # Klasörün değişme zamanı güncellenince KDE simge önbelleğini yeniden tarar.
    os.utime(target.parent.parent.parent, None)


def install(command: list[str]) -> Path:
    """Menü kaydını yazar. `command`, uygulamayı başlatan komuttur (tam yollarla)."""
    _install_icon()
    path = desktop_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        "Comment=Yerel dikte uygulaması\n"
        f"Exec={shlex.join(command)}\n"
        f"Icon={APP_ID}\n"
        "Terminal=false\n"
        "Categories=Utility;\n",
        encoding="utf-8",
    )
    _refresh_menu()
    return path


def ensure(command: list[str]) -> bool:
    """Menü kaydı yoksa ya da başka bir komutu gösteriyorsa yeniden yazar. Değiştiyse True döner."""
    path = desktop_file_path()
    expected = {f"Exec={shlex.join(command)}", f"Icon={APP_ID}"}
    if path.exists() and _icon_installed() and expected <= set(path.read_text(encoding="utf-8").splitlines()):
        return False
    install(command)
    return True


def uninstall() -> bool:
    """Menü kaydını ve temadaki simgeyi kaldırır. Bir şey kaldırıldıysa True döner."""
    removed = False
    for path in (desktop_file_path(), theme_icon_path()):
        if path.exists():
            path.unlink()
            removed = True
    if removed:
        _refresh_menu()
    return removed


def _refresh_menu() -> None:
    """KDE'nin menü önbelleğini yeniler (yoksa sessizce geçer)."""
    try:
        subprocess.run(["kbuildsycoca6"], capture_output=True, check=False, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
