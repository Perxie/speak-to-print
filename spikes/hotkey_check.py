"""Faz 0.5 — Global kısayol ve Kickoff'tan açılış denemesi.

Küçük bir pencere açar ve şunları sınar:
  1. Model ekran kartına yükleniyor mu (özellikle Kickoff'tan açıldığında)?
  2. Portal kısayolu çalışıyor mu: basma ve bırakma ayrı ayrı geliyor mu?

Olan her şey pencerede ve spikes/data/hotkey_check.log dosyasında görünür.

Çalıştırma (proje klasöründe):
  uv run python spikes/hotkey_check.py --install-desktop    # Kickoff kaydını yaz (bir kez)
  uv run python spikes/hotkey_check.py                      # terminalden aç
  (sonra Kickoff'ta "Speak to Print" aratıp oradan da açın)
  uv run python spikes/hotkey_check.py --uninstall-desktop  # Kickoff kaydını sil
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from speak_to_print import desktop_entry
from speak_to_print.hotkey import PortalHotkeys, Shortcut

SPIKES_DIR = Path(__file__).resolve().parent
LOG_FILE = SPIKES_DIR / "data" / "hotkey_check.log"
SAMPLE = SPIKES_DIR / "data" / "jfk.flac"
SHORTCUT_ID = "dictate"


def launch_context() -> str:
    """Nereden açıldığımızı tahmin eder: systemd kapsamının adı bunu gösterir."""
    try:
        cgroup = Path("/proc/self/cgroup").read_text().strip().rsplit("/", 1)[-1]
    except OSError:
        cgroup = "?"
    return cgroup


def gpu_memory_mib() -> str:
    result = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, check=False,
    )
    for line in result.stdout.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 2 and parts[0] == str(os.getpid()):
            return f"{parts[1]} MiB"
    return "bilinmiyor"


class Window(QWidget):
    # Arka plan iş parçacıklarından ana iş parçacığına metin taşımak için sinyal.
    message = Signal(str)

    def __init__(self, load_model: bool, use_hotkey: bool = True) -> None:
        super().__init__()
        self.setWindowTitle(f"{desktop_entry.APP_NAME} — kısayol denemesi")
        self.resize(760, 460)

        self.status = QLabel("Kısayol bekleniyor…")
        self.status.setStyleSheet("font-size: 16pt; padding: 8px;")
        self.log_view = QPlainTextEdit(readOnly=True)
        self.configure_button = QPushButton("Kısayolu değiştir…")
        self.configure_button.setEnabled(False)

        layout = QVBoxLayout(self)
        layout.addWidget(self.status)
        layout.addWidget(self.log_view)
        layout.addWidget(self.configure_button)

        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._log_file = LOG_FILE.open("a", encoding="utf-8")
        self._pressed_at: float | None = None
        self._presses = 0
        self._releases = 0
        self.message.connect(self.log)

        self.log("=" * 60)
        self.log(f"Başladı. Kapsam (cgroup): {launch_context()}")
        self.log(f"Terminale bağlı mı: {'evet' if sys.stdin and sys.stdin.isatty() else 'hayır'}; "
                 f"LD_LIBRARY_PATH: {os.environ.get('LD_LIBRARY_PATH') or '(ayarlı değil)'}")
        self.log(f"Qt platformu: {QGuiApplication.platformName()}; görünüm: {QApplication.style().objectName()}")
        self.log(f"Kickoff kaydı: {'var' if desktop_entry.desktop_file_path().exists() else 'YOK'} "
                 f"({desktop_entry.desktop_file_path()})")

        self.hotkeys = PortalHotkeys(
            desktop_entry.APP_ID,
            [Shortcut(SHORTCUT_ID, "Dikteyi başlat / durdur", "LOGO+F9")],
            parent=self,
        )
        self.hotkeys.activated.connect(self.on_activated)
        self.hotkeys.deactivated.connect(self.on_deactivated)
        self.hotkeys.bound.connect(self.on_bound)
        self.hotkeys.failed.connect(self.on_failed)
        self.configure_button.clicked.connect(self.hotkeys.configure)
        if use_hotkey:
            self.log("Portal: kısayol isteniyor (ilk seferde KDE bir onay penceresi açar)…")
            self.hotkeys.start()

        if load_model:
            threading.Thread(target=self.load_model, daemon=True).start()

    def log(self, text: str) -> None:
        line = f"[{time.strftime('%H:%M:%S')}] {text}"
        self.log_view.appendPlainText(line)
        self._log_file.write(line + "\n")
        self._log_file.flush()

    def load_model(self) -> None:
        """Modeli yükler ve örnek kaydı çevirir (arka plan iş parçacığında)."""
        try:
            from speak_to_print.cuda_libs import preload_cuda_libraries

            loaded = preload_cuda_libraries()
            os.environ.setdefault("HF_HUB_OFFLINE", "1")  # model önbellekte; ağa çıkma (import'tan önce)
            from faster_whisper import WhisperModel, decode_audio

            start = time.perf_counter()
            model = WhisperModel("large-v3", device="cuda", compute_type="float16")
            self.message.emit(f"Model: ekran kartına yüklendi ({time.perf_counter() - start:.1f} sn, "
                              f"{len(loaded)} CUDA kütüphanesi önden yüklendi).")
            if SAMPLE.exists():
                audio = decode_audio(str(SAMPLE), sampling_rate=16_000)
                assert not isinstance(audio, tuple)
                start = time.perf_counter()
                segments, _info = model.transcribe(audio, language="en")
                text = " ".join(s.text.strip() for s in segments)
                self.message.emit(f"Model: örnek kayıt {time.perf_counter() - start:.2f} sn'de çevrildi: {text[:60]}…")
            self.message.emit(f"Model: ekran kartı belleği {gpu_memory_mib()}. GPU DENEMESİ GEÇTİ.")
            self._model = model  # pencere açıkken bellekte kalsın
        except Exception as error:  # noqa: BLE001
            self.message.emit(f"MODEL HATASI: {type(error).__name__}: {error}")

    def on_failed(self, text: str) -> None:
        self.log(f"KISAYOL HATASI: {text}")
        self.status.setText("Kısayol hatası — günlüğe bakın")

    def on_bound(self, triggers: dict) -> None:
        trigger = triggers.get(SHORTCUT_ID) or "(atanmamış)"
        self.log(f"Portal: kısayol hazır → {trigger}   (ham yanıt: {triggers})")
        self.status.setText(f"Kısayol: {trigger} — basıp deneyin")
        self.configure_button.setEnabled(True)

    def on_activated(self, shortcut_id: str) -> None:
        self._presses += 1
        self._pressed_at = time.perf_counter()
        focused = "bu pencere önde" if self.isActiveWindow() else "başka pencere önde"
        self.log(f"BASILDI   #{self._presses} ({shortcut_id}; {focused})")
        self.status.setText("● BASILI")
        self.status.setStyleSheet("font-size: 16pt; padding: 8px; background: #c0392b; color: white;")

    def on_deactivated(self, shortcut_id: str) -> None:
        self._releases += 1
        held = f"{(time.perf_counter() - self._pressed_at) * 1000:.0f} ms basılı kaldı" if self._pressed_at else "?"
        self.log(f"BIRAKILDI #{self._releases} ({shortcut_id}; {held})")
        self.status.setText(f"Bırakıldı — basma {self._presses}, bırakma {self._releases}")
        self.status.setStyleSheet("font-size: 16pt; padding: 8px;")

    def closeEvent(self, event) -> None:  # noqa: N802 — Qt'nin yöntem adı
        self.log(f"Kapanıyor. Toplam basma {self._presses}, bırakma {self._releases}.")
        self.hotkeys.stop()
        self._log_file.close()
        super().closeEvent(event)


def main() -> int:
    parser = argparse.ArgumentParser(description="Global kısayolu ve Kickoff'tan açılışı dener.")
    parser.add_argument("--install-desktop", action="store_true", help="Kickoff kaydını yaz ve çık")
    parser.add_argument("--uninstall-desktop", action="store_true", help="Kickoff kaydını sil ve çık")
    parser.add_argument("--no-model", action="store_true", help="Modeli yükleme")
    parser.add_argument("--no-hotkey", action="store_true", help="Kısayolu isteme (yalnızca model denemesi)")
    parser.add_argument("--quit-after", type=float, help="Bu kadar saniye sonra kendiliğinden kapan")
    args = parser.parse_args()

    if args.install_desktop:
        python = Path(sys.prefix) / "bin" / "python"  # .venv içindeki Python, tam yoluyla
        path = desktop_entry.install([str(python), str(Path(__file__).resolve())],
                                     comment="Yerel dikte uygulaması (kısayol denemesi)")
        print(f"Kickoff kaydı yazıldı: {path}")
        return 0
    if args.uninstall_desktop:
        print("Kickoff kaydı silindi." if desktop_entry.uninstall() else "Kickoff kaydı zaten yok.")
        return 0

    app = QApplication(sys.argv)
    # Pencereyi .desktop dosyasıyla eşleştirir (görev çubuğu simgesi ve adı için).
    QGuiApplication.setDesktopFileName(desktop_entry.APP_ID)
    window = Window(load_model=not args.no_model, use_hotkey=not args.no_hotkey)
    window.show()
    if args.quit_after:
        QTimer.singleShot(int(args.quit_after * 1000), window.close)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
