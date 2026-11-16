"""Uygulamanın giriş noktası: parçaları oluşturur ve birbirine bağlar."""

from __future__ import annotations

import argparse
import logging
import logging.handlers
import os
import sys
import time
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from . import desktop_entry, kwin_rules
from .audio import Recorder
from .config import (EDITOR_GAP, EDITOR_SIZE, EDITOR_TITLE, POPUP_BOTTOM_MARGIN, POPUP_SIZE, POPUP_TITLE,
                     SHORTCUT_DESCRIPTION, SHORTCUT_ID)
from .controller import Controller, Outcome, State
from .history import History
from .hotkey import PortalHotkeys, Shortcut
from .output import OutputError, clipboard_paste
from .output.writer import TextWriter
from .settings import Settings
from .transcriber import Transcriber, Transcript
from .ui.editor_window import EditorWindow
from .ui.listening_popup import ListeningPopup
from .ui.main_window import MainWindow
from .ui.settings_dialog import SettingsDialog
from .ui.tray import Tray

log = logging.getLogger("speak_to_print")


def log_file_path() -> Path:
    state_home = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    return state_home / "speak-to-print" / "speak-to-print.log"


def _setup_logging() -> None:
    """Günlüğü hem terminale hem dosyaya yazar. Dikte edilen metin günlüğe yazılmaz."""
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:
        path = log_file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        # Dosya 512 KB'ı geçince eskisi .1 uzantısıyla saklanır; daha fazlası tutulmaz.
        handlers.append(logging.handlers.RotatingFileHandler(path, maxBytes=512_000, backupCount=1, encoding="utf-8"))
    except OSError:
        pass
    for handler in handlers:
        handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=handlers)
    logging.getLogger("faster_whisper").setLevel(logging.WARNING)  # kütüphanenin ayrıntı satırları günlüğü doldurmasın


def _already_running() -> bool:
    """Başka bir kopya açıksa ona "pencereni göster" der ve True döner."""
    socket = QLocalSocket()
    socket.connectToServer(desktop_entry.APP_ID)
    if not socket.waitForConnected(300):
        return False
    socket.write(b"show")
    socket.waitForBytesWritten(300)
    socket.disconnectFromServer()
    return True


def _popup_position() -> tuple[int, int]:
    """Dinleme penceresinin yeri: ana ekranın alt ortası."""
    area = QGuiApplication.primaryScreen().geometry()
    return (area.x() + (area.width() - POPUP_SIZE[0]) // 2,
            area.y() + area.height() - POPUP_SIZE[1] - POPUP_BOTTOM_MARGIN)


def _prepare_system_integration() -> None:
    """Kickoff kaydını ve KWin pencere kuralını günceller (proje dışına yazar)."""
    launcher = Path(sys.prefix) / "bin" / "speak-to-print"
    if launcher.exists() and desktop_entry.ensure([str(launcher)]):
        log.info("Kickoff kaydı güncellendi: %s", desktop_entry.desktop_file_path())
    if QGuiApplication.platformName() != "wayland":
        return  # ekran boyutu ve pencere kuralları yalnızca gerçek Wayland oturumunda anlamlı
    try:
        x, y = _popup_position()
        if kwin_rules.ensure_popup_rule(desktop_entry.APP_ID, POPUP_TITLE, x, y):
            log.info("KWin pencere kuralı güncellendi (konum %d,%d).", x, y)
        # Düzenleme penceresi dinleme penceresinin hemen üstünde durur.
        editor_y = y - EDITOR_SIZE[1] - EDITOR_GAP
        if kwin_rules.ensure_editor_rule(desktop_entry.APP_ID, EDITOR_TITLE, x, editor_y):
            log.info("KWin düzenleme penceresi kuralı güncellendi (konum %d,%d).", x, editor_y)
    except (OSError, RuntimeError) as error:
        log.warning("KWin pencere kuralı yazılamadı: %s", error)


class Application(QObject):
    """Uygulamanın parçalarını tutar ve aralarındaki bağlantıları kurar.

    Bağımlılıklar (ayarlar, metin yazıcı, "penceremiz önde mi" sorusu) dışarıdan
    verilebilir; böylece gerçek bağlantılar ekransız denemede de sınanabilir.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        write_text: Callable[[str], str] | None = None,
        app_has_focus: Callable[[], bool] | None = None,
        history: History | None = None,
        on_quit: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        # "Pencerelerimizden biri klavye odağında mı?" sorusu.
        self._app_has_focus = app_has_focus or (
            lambda: QGuiApplication.applicationState() == Qt.ApplicationState.ApplicationActive)
        self.editor = EditorWindow()
        self.history = history or History()
        self._on_quit = on_quit or (lambda: None)
        self._quitting = False
        self.settings = settings or Settings()
        self._writer = TextWriter(lambda: self.settings.output_method) if write_text is None else None
        self.recorder = Recorder()
        self.transcriber = Transcriber()
        self.controller = Controller(
            self.recorder, self.transcriber,
            write_text or self._writer.write,  # type: ignore[union-attr]
            self.settings,
            # Düzenleme penceresi odaktaysa yazmak serbesttir: dikte, düzenlenen metnin içine girer.
            is_app_active=lambda: self._app_has_focus() and not self.editor.isActiveWindow(),
        )
        self._pending_paste = ""
        self._focus_wait_started = 0.0
        self._focus_timer = QTimer(self)  # düzenleyiciden yapıştırırken odağın geri dönmesini bekler
        self._focus_timer.setInterval(40)
        self._focus_timer.timeout.connect(self._paste_when_focus_released)
        self.window = MainWindow()
        self.settings_dialog = SettingsDialog(self.settings)
        self.popup = ListeningPopup(seconds_recorded=lambda: self.recorder.seconds)
        self.tray = Tray()
        self.hotkeys = PortalHotkeys(desktop_entry.APP_ID, [Shortcut(SHORTCUT_ID, SHORTCUT_DESCRIPTION)])
        self.server = QLocalServer()
        self._connect()
        self._sync_options()
        self.window.set_history(self.history.recent())

    def _connect(self) -> None:
        self.settings.changed.connect(self._sync_options)
        self.controller.state_changed.connect(self._on_state)
        self.controller.outcome.connect(self._on_outcome)
        self.controller.notice.connect(self._on_notice)
        self.recorder.level.connect(self.popup.set_level)
        self.recorder.notice.connect(self._on_notice)
        self.transcriber.ready.connect(self._on_model_ready)
        self.transcriber.done.connect(self._on_transcript)

        self.popup.pause_clicked.connect(self.controller.pause_resume)
        self.popup.finish_clicked.connect(self.controller.finish)
        self.popup.cancel_clicked.connect(self.controller.cancel)
        self.popup.paste_clicked.connect(self.controller.paste_last)
        self.popup.copy_clicked.connect(self._copy)
        self.popup.auto_paste_toggled.connect(self._set_auto_paste)
        self.popup.edit_requested.connect(self._open_editor)
        self.popup.listen_clicked.connect(lambda: self._toggle_from("küçük pencere"))

        self.editor.copy_clicked.connect(self._copy_from_editor)
        self.editor.listen_clicked.connect(lambda: self._toggle_from("düzenleme penceresi"))
        self.editor.paste_clicked.connect(self._paste_from_editor)
        self.editor.text_edited.connect(self._on_text_edited)

        self.window.copy_clicked.connect(self._copy)
        self.window.edit_clicked.connect(self._open_editor)
        self.window.delete_clicked.connect(self._delete_history)
        self.window.clear_clicked.connect(self._clear_history)
        self.window.auto_paste_toggled.connect(self._set_auto_paste)
        self.window.configure_shortcut_clicked.connect(self.hotkeys.configure)
        self.window.settings_clicked.connect(self.settings_dialog.open)
        self.settings_dialog.configure_shortcut_clicked.connect(self.hotkeys.configure)
        self.window.listen_clicked.connect(lambda: self._toggle_from("ana pencere"))
        self.window.closed.connect(self.shutdown)
        self.tray.listen_clicked.connect(lambda: self._toggle_from("tepsi menüsü"))
        self.tray.show_window_clicked.connect(self.show_window)
        self.tray.quit_clicked.connect(self.window.close)

        self.hotkeys.activated.connect(self._on_shortcut)
        self.hotkeys.deactivated.connect(self._on_shortcut_released)
        self.hotkeys.bound.connect(self._on_bound)
        self.hotkeys.failed.connect(self._on_shortcut_failed)
        self.server.newConnection.connect(self._on_new_instance)

    def start(self, listen_for_instances: bool = True, use_hotkeys: bool = True) -> None:
        if listen_for_instances:
            QLocalServer.removeServer(desktop_entry.APP_ID)
            self.server.listen(desktop_entry.APP_ID)
        self.window.show()
        if use_hotkeys:
            self.hotkeys.start()
        self.controller.start()

    # ------------------------------------------------------------ olaylar

    def _sync_options(self) -> None:
        """Ayarlar değişince ilgili parçaları günceller."""
        hold_mode = self.settings.hotkey_mode == "hold"
        self.window.set_options(self.settings.auto_paste, hold_mode)
        self.popup.set_auto_paste(self.settings.auto_paste)
        self.popup.set_hold_mode(hold_mode)
        self.recorder.preferred_device_id = self.settings.microphone_id
        summary = (f"otomatik yapıştırma={self.settings.auto_paste}, ipucu={self.settings.use_prompt}, "
                   f"kısayol kipi={self.settings.hotkey_mode}, yazma={self.settings.output_method}, "
                   f"mikrofon={'seçili' if self.settings.microphone_id else 'varsayılan'}, "
                   f"sözlük={len(self.settings.vocabulary)} terim, geçmiş={self.settings.keep_history}")
        if summary != getattr(self, "_last_summary", ""):
            self._last_summary = summary
            log.info("Ayarlar: %s", summary)

    def _set_auto_paste(self, enabled: bool) -> None:
        self.settings.auto_paste = enabled

    def _copy(self, text: str) -> None:
        if not text:
            return
        try:
            clipboard_paste.copy_text(text)
            log.info("Metin panoya kopyalandı (%d karakter).", len(text))
            self.popup.show_copied()
            self.editor.show_note("Panoya kopyalandı.")
            self.window.show_notice("Panoya kopyalandı.")
        except OutputError as error:
            log.warning("Kopyalanamadı: %s", error)
            self.window.show_notice(str(error))

    def _toggle_from(self, source: str) -> None:
        log.info("Dinleme düğmesi: %s (durum: %s).", source, self.controller.state.name)
        self.controller.toggle()

    # ------------------------------------------------------------ düzenleme penceresi

    def _open_editor(self, text: str) -> None:
        log.info("Düzenleme penceresi açıldı (%d karakter).", len(text))
        self.popup.hide()
        self.editor.open_with(text)

    def _on_text_edited(self, text: str) -> None:
        self.controller.last_text = text

    def _copy_from_editor(self, text: str) -> None:
        self._copy(text)
        self._remember(text)  # düzenlenmiş hâli de geçmişe girsin

    # ------------------------------------------------------------ geçmiş

    def _remember(self, text: str) -> None:
        if not self.settings.keep_history:
            return
        entry = self.history.add(text)
        if entry is not None:
            log.info("Geçmişe eklendi (%d karakter).", len(entry.text))
            self.window.add_history(entry)

    def _delete_history(self, entry_id: int) -> None:
        self.history.delete(entry_id)
        log.info("Geçmişten bir kayıt silindi.")

    def _clear_history(self) -> None:
        self.history.clear()
        log.info("Geçmiş temizlendi.")

    def _paste_from_editor(self, text: str) -> None:
        """Düzenleme penceresini kapatır; odak önceki uygulamaya dönünce metni oraya yazar."""
        if not text.strip():
            return
        self._pending_paste = text
        self._focus_wait_started = time.monotonic()
        self.editor.hide()
        self._focus_timer.start()

    def _paste_when_focus_released(self) -> None:
        waited = time.monotonic() - self._focus_wait_started
        released = not self._app_has_focus()
        if not released and waited < 1.5:
            return
        self._focus_timer.stop()
        text, self._pending_paste = self._pending_paste, ""
        if released:
            log.info("Düzenleyiciden yapıştır: odak %.0f ms'de önceki pencereye döndü.", waited * 1000)
            # Önceki pencere klavyeyi almaya hazır olsun diye kısa bir pay bırak.
            QTimer.singleShot(120, lambda: self.controller.paste_text(text))
        else:
            log.info("Düzenleyiciden yapıştır: odak %.0f ms içinde başka pencereye geçmedi; yazılmadı.", waited * 1000)
            self.editor.open_with(text)
            self.editor.show_note("Yazılacak pencere bulunamadı. Kopyala'yı kullanın.")

    def show_window(self) -> None:
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def _on_shortcut(self, shortcut_id: str) -> None:
        if shortcut_id != SHORTCUT_ID:
            return
        log.info("Kısayola basıldı (durum: %s, kip: %s).", self.controller.state.name, self.settings.hotkey_mode)
        if self.settings.hotkey_mode == "hold":
            self.controller.start_listening()
        else:
            self.controller.toggle()

    def _on_shortcut_released(self, shortcut_id: str) -> None:
        # "Basılı tut" kipinde tuşu bırakmak dinlemeyi bitirir.
        if shortcut_id == SHORTCUT_ID and self.settings.hotkey_mode == "hold":
            log.info("Kısayol bırakıldı (durum: %s).", self.controller.state.name)
            self.controller.finish()

    def _on_state(self, state: State) -> None:
        if state is State.LISTENING and self.recorder.device_name:
            log.info("Durum: %s (mikrofon: %s)", state.name, self.recorder.device_name)
        elif state is State.FAILED:
            log.error("Durum: %s (%s)", state.name, self.controller.failure)
        else:
            log.info("Durum: %s", state.name)
        self.popup.set_state(state)
        self.editor.set_state(state)
        self.window.set_state(state, self.controller.failure)
        self.tray.set_state(state)

    def _on_model_ready(self, seconds: float, device: str) -> None:
        log.info("Model yüklendi: %.1f sn (%s)", seconds, device)
        self.window.set_model_info(seconds, device)

    def _on_transcript(self, transcript: Transcript) -> None:
        log.info("Çeviri: %.1f sn ses %.2f sn'de çevrildi; %d karakter%s", transcript.audio_seconds,
                 transcript.seconds, len(transcript.text), " (uydurma metin alıkondu)" if transcript.withheld else "")

    def _on_outcome(self, outcome: Outcome) -> None:
        log.info("Sonuç: %s — %s", "yazıldı" if outcome.pasted else "yazılmadı", outcome.note.split("“")[0])
        self.popup.show_outcome(outcome)
        self.window.show_outcome(outcome)
        self._remember(outcome.text)

    def _on_notice(self, text: str) -> None:
        log.info("Bilgi: %s", text)
        self.popup.show_notice(text)
        self.window.show_notice(text)

    def _on_bound(self, triggers: dict) -> None:
        trigger = triggers.get(SHORTCUT_ID, "")
        log.info("Kısayol: %s", trigger or "(atanmamış)")
        self.window.set_shortcut(trigger)
        self.settings_dialog.set_shortcut(trigger)

    def _on_shortcut_failed(self, message: str) -> None:
        log.error("Kısayol hatası: %s", message)
        self.window.set_shortcut_error(message)

    def _on_new_instance(self) -> None:
        connection = self.server.nextPendingConnection()
        if connection is not None:
            connection.close()
        log.info("İkinci kez açılmak istendi; pencere gösteriliyor.")
        self.show_window()

    def shutdown(self) -> None:
        """Her şeyi kapatır. Arka planda süren bir iş bitmezse süreci zorla sonlandırır."""
        if self._quitting:
            return
        self._quitting = True
        log.info("Kapanıyor.")
        self.hotkeys.stop()
        self.recorder.cancel()
        self._focus_timer.stop()
        self.popup.hide()
        self.editor.hide()
        self.settings_dialog.hide()
        self.tray.hide()
        if self._writer is not None:
            self._writer.close()
        self.server.close()
        self.history.close()
        if not self.transcriber.shutdown():
            # Model yüklemesi ya da çeviri sürüyor; beklemek yerine süreci sonlandır
            # (ekran kartı belleği süreç bitince serbest kalır).
            log.info("Arka plandaki iş bitmedi; süreç sonlandırılıyor.")
            logging.shutdown()
            os._exit(0)
        self._on_quit()


def main() -> int:
    parser = argparse.ArgumentParser(prog="speak-to-print", description="Yerel dikte uygulaması.")
    parser.add_argument("--quit-after", type=float, help=argparse.SUPPRESS)  # yalnızca otomatik denemeler için
    args = parser.parse_args()
    _setup_logging()

    app = QApplication(sys.argv)
    app.setApplicationName(desktop_entry.APP_NAME)
    QGuiApplication.setDesktopFileName(desktop_entry.APP_ID)  # pencereleri .desktop kaydıyla eşleştirir
    app.setQuitOnLastWindowClosed(False)  # küçük pencere gizlenince uygulama kapanmasın

    if _already_running():
        log.info("Uygulama zaten açık; açık olan pencere gösterildi.")
        return 0

    log.info("Başlıyor (Qt platformu: %s).", QGuiApplication.platformName())
    _prepare_system_integration()
    application = Application(on_quit=app.quit)
    application.start()
    if args.quit_after:
        QTimer.singleShot(int(args.quit_after * 1000), application.window.close)
    return app.exec()
