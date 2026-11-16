"""Kickoff menü kaydı (.desktop dosyası).

Bu dosya iki işe yarar:
  - Uygulama Kickoff'ta "Speak to Print" adıyla görünür.
  - Portal, kısayolların hangi uygulamaya ait olduğunu bu dosyanın adından
    (uygulama kimliği) anlar; dosya yoksa Registry.Register reddedilir.

Dosya proje klasörünün dışına yazılır: ~/.local/share/applications/
(bkz. docs/proje-disi-dosyalar.md).
"""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

APP_ID = "io.github.perxie.SpeakToPrint"
APP_NAME = "Speak to Print"


def desktop_file_path() -> Path:
    data_home = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return data_home / "applications" / f"{APP_ID}.desktop"


def install(command: list[str], comment: str = "Yerel dikte uygulaması") -> Path:
    """Menü kaydını yazar. `command`, uygulamayı başlatan komuttur (tam yollarla)."""
    path = desktop_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        f"Comment={comment}\n"
        f"Exec={shlex.join(command)}\n"
        "Icon=audio-input-microphone\n"
        "Terminal=false\n"
        "Categories=Utility;\n",
        encoding="utf-8",
    )
    _refresh_menu()
    return path


def ensure(command: list[str]) -> bool:
    """Menü kaydı yoksa ya da başka bir komutu gösteriyorsa yeniden yazar. Değiştiyse True döner."""
    path = desktop_file_path()
    expected = f"Exec={shlex.join(command)}"
    if path.exists() and expected in path.read_text(encoding="utf-8").splitlines():
        return False
    install(command)
    return True


def uninstall() -> bool:
    path = desktop_file_path()
    if not path.exists():
        return False
    path.unlink()
    _refresh_menu()
    return True


def _refresh_menu() -> None:
    """KDE'nin menü önbelleğini yeniler (yoksa sessizce geçer)."""
    try:
        subprocess.run(["kbuildsycoca6"], capture_output=True, check=False, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
