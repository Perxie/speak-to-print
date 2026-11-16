"""Faz 0.7 — Dinleme penceresi denemesi.

Sınanan risk: dinleme sırasında görünen küçük pencere odağı çalarsa, metin
yazı yazdığınız uygulamaya değil bu pencereye gider (yani kaybolur).

Nasıl çalışır?
  - Küçük bir denetim penceresi açılır (gerçek uygulamadaki ana pencere gibi).
  - Kısayola (Shift+Pause) basınca dinleme penceresi görünür / kaybolur.
  - "Bitir"e fareyle tıklayınca kısa bir test metni kwin-type ile o an etkin
    olan pencereye yazılır. Metin, tıklamadan önce yazı yazdığınız uygulamada
    çıkmalıdır.

Olan her şey spikes/data/popup_check.log dosyasına yazılır.

Çalıştırma (proje klasöründe):
  uv run python spikes/popup_check.py                 # etkileşimli deneme
  uv run python spikes/popup_check.py --probe         # pencereyi 2 sn gösterip odağı ölçer
  uv run python spikes/popup_check.py --install-rule  # KWin pencere kuralını yaz
  uv run python spikes/popup_check.py --remove-rule   # KWin pencere kuralını sil
"""

from __future__ import annotations

import argparse
import secrets
import sys
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from speak_to_print import desktop_entry, kwin_rules
from speak_to_print.hotkey import PortalHotkeys, Shortcut
from speak_to_print.output import OutputError, kwin_type

LOG_FILE = Path(__file__).resolve().parent / "data" / "popup_check.log"
POPUP_TITLE = "Speak to Print — Dinleme"
POPUP_SIZE = (420, 96)


def log(text: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{time.strftime('%H:%M:%S')}] {text}"
    print(line, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(line + "\n")


class Popup(QWidget):
    """Dinleme penceresi: çerçevesiz, her zaman üstte, odak istemeyen küçük pencere."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(POPUP_TITLE)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(*POPUP_SIZE)
        self.setStyleSheet("QWidget { background: #232629; color: #eff0f1; } "
                           "QPushButton { padding: 6px 14px; background: #31363b; border: 1px solid #5f6265; border-radius: 4px; } "
                           "QPushButton:hover { background: #3daee9; }")

        self.status = QLabel("● Dinliyor (deneme)")
        self.status.setStyleSheet("font-size: 13pt; color: #ed1515;")
        self.pause_button = QPushButton("Beklet")
        self.finish_button = QPushButton("Bitir")
        self.cancel_button = QPushButton("İptal")
        buttons = QHBoxLayout()
        for button in (self.pause_button, self.finish_button, self.cancel_button):
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            buttons.addWidget(button)
        layout = QVBoxLayout(self)
        layout.addWidget(self.status)
        layout.addLayout(buttons)

        self.pause_button.clicked.connect(self.on_pause)
        self.finish_button.clicked.connect(self.on_finish)
        self.cancel_button.clicked.connect(self.on_cancel)
        self._paused = False

    def focus_state(self) -> str:
        return "ODAK BU PENCEREDE" if self.isActiveWindow() else "odak başka pencerede"

    def on_pause(self) -> None:
        self._paused = not self._paused
        self.pause_button.setText("Devam" if self._paused else "Beklet")
        self.status.setText("❚❚ Beklemede" if self._paused else "● Dinliyor (deneme)")
        log(f"Beklet/Devam tıklandı ({self.focus_state()})")

    def on_finish(self) -> None:
        log(f"Bitir tıklandı ({self.focus_state()})")
        self.status.setText("Yazılıyor…")
        # Gerçek uygulamada burada çeviri olur; kısa bir beklemeden sonra yazıyoruz.
        QTimer.singleShot(300, self.type_and_hide)

    def type_and_hide(self) -> None:
        text = f"speak-to-print odak denemesi [{secrets.randbelow(9000) + 1000}] "
        state = self.focus_state()
        try:
            kwin_type.type_text(text)
            log(f"Yazıldı: {text!r} (yazma anında {state})")
        except OutputError as error:
            log(f"YAZMA HATASI: {error}")
        self.hide()
        self.status.setText("● Dinliyor (deneme)")

    def on_cancel(self) -> None:
        log(f"İptal tıklandı ({self.focus_state()})")
        self.hide()


class Control(QWidget):
    """Denetim penceresi: gerçek uygulamadaki ana pencerenin yerini tutar."""

    def __init__(self, popup: Popup, use_hotkey: bool) -> None:
        super().__init__()
        self.popup = popup
        self.setWindowTitle(f"{desktop_entry.APP_NAME} — dinleme penceresi denemesi")
        self.resize(520, 160)
        self.info = QLabel("Kısayol bekleniyor…")
        self.info.setWordWrap(True)
        show_button = QPushButton("Dinleme penceresini göster / gizle")
        show_button.clicked.connect(self.toggle)
        layout = QVBoxLayout(self)
        layout.addWidget(self.info)
        layout.addWidget(show_button)

        self.hotkeys = PortalHotkeys(desktop_entry.APP_ID, [Shortcut("dictate", "Dikteyi başlat / durdur")], parent=self)
        self.hotkeys.activated.connect(lambda _id: self.toggle())
        self.hotkeys.bound.connect(self.on_bound)
        self.hotkeys.failed.connect(self.on_failed)
        if use_hotkey:
            self.hotkeys.start()

    def on_bound(self, triggers: dict) -> None:
        trigger = triggers.get("dictate") or "(atanmamış)"
        log(f"Kısayol hazır: {trigger}")
        self.info.setText(f"Başka bir uygulamada (ör. Kate) yazı alanına tıklayın, sonra {trigger} tuşuna basın. "
                          "Dinleme penceresi açılınca Bitir'e fareyle tıklayın.")

    def on_failed(self, text: str) -> None:
        log(f"KISAYOL HATASI: {text}")
        self.info.setText(f"Kısayol hatası: {text}")

    def toggle(self) -> None:
        if self.popup.isVisible():
            self.popup.hide()
            log("Dinleme penceresi gizlendi")
        else:
            self.popup.show()
            QTimer.singleShot(400, lambda: log(
                f"Dinleme penceresi gösterildi ({self.popup.focus_state()}; konum {self.popup.geometry().x()},{self.popup.geometry().y()})"))

    def closeEvent(self, event) -> None:  # noqa: N802 — Qt'nin yöntem adı
        log("Kapanıyor.")
        self.hotkeys.stop()
        self.popup.close()
        QApplication.quit()
        super().closeEvent(event)


def popup_position() -> tuple[int, int]:
    """Ana ekranın alt ortası. Wayland'de Qt görev çubuğunun yerini bilmediği için pay bırakılır."""
    area = QGuiApplication.primaryScreen().availableGeometry()
    return area.x() + (area.width() - POPUP_SIZE[0]) // 2, area.y() + area.height() - POPUP_SIZE[1] - 90


def main() -> int:
    parser = argparse.ArgumentParser(description="Dinleme penceresinin odağı çalıp çalmadığını dener.")
    parser.add_argument("--probe", action="store_true", help="Pencereyi 2 sn gösterip odak durumunu yaz ve çık")
    parser.add_argument("--install-rule", action="store_true", help="KWin pencere kuralını yaz ve çık")
    parser.add_argument("--remove-rule", action="store_true", help="KWin pencere kuralını sil ve çık")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    QGuiApplication.setDesktopFileName(desktop_entry.APP_ID)
    app.setQuitOnLastWindowClosed(False)

    if args.install_rule:
        x, y = popup_position()
        backup = kwin_rules.install_popup_rule(desktop_entry.APP_ID, POPUP_TITLE, x, y)
        print(f"KWin kuralı yazıldı (konum {x},{y})." + (f" Yedek: {backup}" if backup else ""))
        return 0
    if args.remove_rule:
        print("KWin kuralı silindi." if kwin_rules.remove_popup_rule() else "KWin kuralı zaten yok.")
        return 0

    log("=" * 60)
    log(f"Başladı. KWin kuralı: {'var' if kwin_rules.popup_rule_installed() else 'yok'}; "
        f"Qt platformu: {QGuiApplication.platformName()}")
    app.applicationStateChanged.connect(lambda state: log(f"Uygulama durumu: {state.name}"))
    popup = Popup()

    if args.probe:
        popup.show()
        QTimer.singleShot(1000, lambda: log(
            f"Sonda: {popup.focus_state()}; konum {popup.geometry().x()},{popup.geometry().y()}; "
            f"uygulama {app.applicationState().name}"))
        QTimer.singleShot(2000, app.quit)
        return app.exec()

    control = Control(popup, use_hotkey=True)
    control.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
