"""Ana pencere: durum, kısayol ve çeviri geçmişi.

Bir defter gibi düzenlenmiştir: üstte durum ve tek ana düğme, ortada geçmiş
(solda saat, sağda dizili metin), altta seçili kaydın tamamı ve ayarlar.
Bu pencere kapatılınca uygulama tamamen kapanır.

Görsel dil için bkz. docs/tasarim.md.
"""

from __future__ import annotations

from PySide6 import QtGui
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
                               QVBoxLayout, QWidget)

from ..controller import Outcome, State
from ..desktop_entry import APP_NAME
from .. import history
from ..history import Entry
from . import theme
from .widgets import CropFrame, HistoryDelegate, Keycap, PrintedText, Rule, Switch

PREVIEW_LENGTH = 90  # listede gösterilen metnin en fazla uzunluğu

STATUS = {  # durum → (yazı, renk)
    State.LOADING: ("Model yükleniyor", theme.LEAD),
    State.IDLE: ("Hazır", theme.PAPER),
    State.LISTENING: ("Dinliyor", theme.MAGENTA),
    State.PAUSED: ("Beklemede", theme.LEAD),
    State.TRANSCRIBING: ("Çevriliyor", theme.CYAN),
    State.FAILED: ("Model yüklenemedi", theme.RED),
}


def _summary(entry: Entry) -> str:
    text = " ".join(entry.text.split())
    if len(text) > PREVIEW_LENGTH:
        text = text[: PREVIEW_LENGTH - 1] + "…"
    return f"{entry.created_at:%d.%m %H:%M}  {text}"


def _literal_tooltip(text: str) -> str:
    """İpucu balonu HTML'ye benzeyen metni biçimli gösterir; dikte yazıldığı gibi görünsün.

    Benzemeyen metin zaten düz gösterildiği için olduğu gibi bırakılır.
    """
    return QtGui.Qt.convertFromPlainText(text) if QtGui.Qt.mightBeRichText(text) else text


class MainWindow(QWidget):
    configure_shortcut_clicked = Signal()
    settings_clicked = Signal()
    listen_clicked = Signal()
    copy_clicked = Signal(str)
    edit_clicked = Signal(str)  # seçili metni düzenleme penceresinde aç
    delete_clicked = Signal(int)  # geçmiş kaydının kimliği
    clear_clicked = Signal()
    auto_paste_toggled = Signal(bool)
    closed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(660, 680)
        self.setMinimumSize(520, 520)
        self._trigger = ""
        self._model_info = ""
        self._hold_mode = False

        # Üst bölüm: durum ve ana düğme.
        self.status = QLabel("Model yükleniyor")
        self.status.setFont(theme.ui_font(24, 600))
        self.listen_button = QPushButton("Dinlemeyi başlat")
        self.listen_button.setEnabled(False)
        self.listen_button.setToolTip("Bu düğmeyle başlatınca bu pencere önde olduğu için metin başka uygulamaya yazılmaz; "
                                      "küçük pencerede gösterilir, oradan kopyalayabilir, düzenleyebilir ya da yapıştırabilirsiniz.")
        theme.set_kind(self.listen_button, "primary")
        self.detail = QLabel()
        self.detail.setTextFormat(Qt.TextFormat.PlainText)  # dışarıdan gelen metin: HTML gibi yorumlanmasın
        self.detail.setWordWrap(True)
        self.detail.setFont(theme.ui_font(13, 400))
        self.detail.setStyleSheet(f"color: {theme.LEAD};")
        self.detail.setMinimumHeight(34)
        self.detail.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # Kısayol satırı.
        self.shortcut = QLabel("Kısayol")
        self.shortcut.setTextFormat(Qt.TextFormat.PlainText)  # dışarıdan gelen metin: HTML gibi yorumlanmasın
        self.shortcut.setFont(theme.ui_font(13, 500))
        self.shortcut.setStyleSheet(f"color: {theme.LEAD};")
        self._keycap = Keycap("bekleniyor")
        self.shortcut_button = QPushButton("Değiştir")
        self.shortcut_button.setEnabled(False)
        theme.set_kind(self.shortcut_button, "quiet")
        self.settings_button = QPushButton("Ayarlar")

        # Geçmiş.
        history_title = QLabel("Geçmiş")
        history_title.setFont(theme.ui_font(15, 600))
        self.clear_button = QPushButton("Geçmişi temizle")
        theme.set_kind(self.clear_button, "quiet")
        self.history = QListWidget()
        self.history.setItemDelegate(HistoryDelegate(self.history))
        self.history.setMouseTracking(True)
        self.history.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.history.setToolTip("Son dikteleriniz. Yalnızca bu bilgisayarda saklanır.")
        self._empty = QLabel("Henüz dikte yok. Bir uygulamada yazı alanına tıklayıp kısayola basın; söyledikleriniz burada birikir.")
        self._empty.setFont(theme.ui_font(13, 400))
        self._empty.setStyleSheet(f"color: {theme.LEAD};")
        self._empty.setWordWrap(True)

        # Seçili kaydın tamamı.
        self.preview = PrintedText(read_only=True)
        self.preview.setPlaceholderText("Listeden bir kayıt seçin; metnin tamamı burada görünür.")
        self._crop = CropFrame()
        self._crop.setFixedHeight(128)
        crop_layout = QVBoxLayout(self._crop)
        crop_layout.setContentsMargins(12, 6, 6, 6)
        crop_layout.addWidget(self.preview)
        self.copy_button = QPushButton("Kopyala")
        self.edit_button = QPushButton("Düzenle")
        self.delete_button = QPushButton("Sil")
        theme.set_kind(self.delete_button, "quiet")

        # Alt bölüm.
        self.auto_paste = Switch("Otomatik yapıştır")
        self.auto_paste.setToolTip("Açıkken çevrilen metin imlecin olduğu yere kendiliğinden yazılır.")
        self.quit_button = QPushButton("Çık")
        theme.set_kind(self.quit_button, "quiet")

        for button in (self.listen_button, self.shortcut_button, self.settings_button, self.clear_button,
                       self.copy_button, self.edit_button, self.delete_button, self.quit_button):
            button.setFont(theme.ui_font(13, 600))
            button.setCursor(Qt.CursorShape.PointingHandCursor)

        header = QHBoxLayout()
        header.addWidget(self.status, 1)
        header.addWidget(self.listen_button)
        shortcut_row = QHBoxLayout()
        shortcut_row.setSpacing(8)
        shortcut_row.addWidget(self.shortcut)
        shortcut_row.addWidget(self._keycap)
        shortcut_row.addWidget(self.shortcut_button)
        shortcut_row.addStretch(1)
        history_header = QHBoxLayout()
        history_header.addWidget(history_title, 1)
        history_header.addWidget(self.clear_button)
        actions = QHBoxLayout()
        actions.setSpacing(6)
        actions.addWidget(self.copy_button)
        actions.addWidget(self.edit_button)
        actions.addWidget(self.delete_button)
        actions.addStretch(1)
        footer = QHBoxLayout()
        footer.setSpacing(6)
        footer.addWidget(self.auto_paste)
        footer.addStretch(1)
        footer.addWidget(self.settings_button)
        footer.addWidget(self.quit_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 18)
        layout.setSpacing(10)
        layout.addLayout(header)
        layout.addWidget(self.detail)
        layout.addLayout(shortcut_row)
        layout.addSpacing(6)
        layout.addWidget(Rule())
        layout.addSpacing(4)
        layout.addLayout(history_header)
        layout.addWidget(self._empty)
        layout.addWidget(self.history, 1)
        layout.addSpacing(6)
        layout.addWidget(self._crop)
        layout.addLayout(actions)
        layout.addSpacing(4)
        layout.addWidget(Rule())
        layout.addLayout(footer)

        self.shortcut_button.clicked.connect(self.configure_shortcut_clicked)
        self.settings_button.clicked.connect(self.settings_clicked)
        self.listen_button.clicked.connect(self.listen_clicked)
        self.history.currentItemChanged.connect(self._on_selection_changed)
        self.history.itemDoubleClicked.connect(lambda _item: self._edit_selected())
        self.copy_button.clicked.connect(lambda: self.copy_clicked.emit(self.preview.toPlainText()))
        self.edit_button.clicked.connect(self._edit_selected)
        self.delete_button.clicked.connect(self._delete_selected)
        self.clear_button.clicked.connect(self._confirm_clear)
        self.quit_button.clicked.connect(self.close)
        self.auto_paste.toggled.connect(self.auto_paste_toggled)
        self._set_status(State.LOADING)
        self._on_selection_changed()

    # ------------------------------------------------------------ ayarlar ve durum

    def set_options(self, auto_paste: bool, hold_mode: bool) -> None:
        if self.auto_paste.isChecked() != auto_paste:
            self.auto_paste.blockSignals(True)
            self.auto_paste.setChecked(auto_paste)
            self.auto_paste.blockSignals(False)
        if self._hold_mode != hold_mode:
            self._hold_mode = hold_mode
            self._show_hint()

    def set_state(self, state: State, failure: str = "") -> None:
        self._set_status(state)
        listening = state in (State.LISTENING, State.PAUSED)
        self.listen_button.setText("Bitir" if listening else "Dinlemeyi başlat")
        self.listen_button.setEnabled(state in (State.IDLE, State.LISTENING, State.PAUSED))
        if state is State.FAILED:
            self.detail.setText(failure)
        elif state is State.IDLE:
            self._show_hint()
        elif state is State.LISTENING:
            self.detail.setText("Konuşun. Bitirmek için tuşu bırakın." if self._hold_mode
                                else "Konuşun. Bitirmek için kısayola ya da Bitir'e basın.")

    def set_model_info(self, seconds: float, device: str) -> None:
        if device == "cuda":
            self._model_info = f"Model {seconds:.1f} sn'de yüklendi (ekran kartı)."
        else:
            self._model_info = "Ekran kartı kullanılamadı; model işlemcide çalışıyor, çeviri daha yavaş olacak."
        self._show_hint()

    def show_loading_status(self, text: str) -> None:
        """Model yüklenirken ara bilgiler (ör. ilk indirme)."""
        self.detail.setText(text)

    def set_shortcut(self, trigger: str) -> None:
        self._trigger = trigger
        self.shortcut_button.setEnabled(True)
        if trigger:
            self.shortcut.setText("Kısayol")
            self.shortcut.setStyleSheet(f"color: {theme.LEAD};")
            self._keycap.set_text(trigger)
            self._keycap.setVisible(True)
            self.shortcut_button.setText("Değiştir")
            theme.set_kind(self.shortcut_button, "quiet")
        else:
            self.shortcut.setText("Kısayol atanmamış. Dikte için bir tuş seçin.")
            self.shortcut.setStyleSheet(f"color: {theme.YELLOW};")
            self._keycap.setVisible(False)
            self.shortcut_button.setText("Tuş seç")
            theme.set_kind(self.shortcut_button, "primary")
        self._show_hint()

    def set_shortcut_error(self, message: str) -> None:
        self.shortcut.setText(f"Kısayol hatası: {message}")
        self.shortcut.setStyleSheet(f"color: {theme.RED};")

    def show_outcome(self, outcome: Outcome) -> None:
        self.detail.setText(outcome.note)

    def show_notice(self, text: str) -> None:
        self.detail.setText(text)

    # ------------------------------------------------------------ geçmiş

    def set_history(self, entries: list[Entry]) -> None:
        """Listeyi baştan doldurur (en yeni kayıt en üstte)."""
        self.history.clear()
        for entry in entries:
            self.history.addItem(self._item(entry))
        self._on_selection_changed()

    def add_history(self, entry: Entry) -> None:
        """Yeni kaydı en üste ekler ve seçer.

        Veritabanı en yeni `history.MAX_ENTRIES` kaydı tutar; liste de fazlasını göstermez,
        yoksa veritabanından silinmiş kayıtlar listede kalırdı.
        """
        self.history.insertItem(0, self._item(entry))
        while self.history.count() > history.MAX_ENTRIES:
            self.history.takeItem(self.history.count() - 1)
        self.history.setCurrentRow(0)

    def _item(self, entry: Entry) -> QListWidgetItem:
        item = QListWidgetItem(_summary(entry))
        item.setData(Qt.ItemDataRole.UserRole, entry)
        item.setToolTip(_literal_tooltip(entry.text))
        return item

    def _selected(self) -> Entry | None:
        item = self.history.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _on_selection_changed(self, *_args) -> None:
        entry = self._selected()
        self.preview.setPlainText(entry.text if entry else "")
        for button in (self.copy_button, self.edit_button, self.delete_button):
            button.setEnabled(entry is not None)
        has_entries = self.history.count() > 0
        self.clear_button.setEnabled(has_entries)
        self._empty.setVisible(not has_entries)
        self._crop.set_mark_color(theme.CYAN if entry else theme.RULE)

    def _edit_selected(self) -> None:
        entry = self._selected()
        if entry is not None:
            self.edit_clicked.emit(entry.text)

    def _delete_selected(self) -> None:
        entry = self._selected()
        if entry is not None:
            self.history.takeItem(self.history.currentRow())
            self.delete_clicked.emit(entry.id)
            self._on_selection_changed()

    def _confirm_clear(self) -> None:
        answer = QMessageBox.question(self, APP_NAME, "Geçmişteki bütün metinler silinsin mi? Bu geri alınamaz.")
        if answer == QMessageBox.StandardButton.Yes:
            self.history.clear()
            self._on_selection_changed()
            self.clear_clicked.emit()

    # ------------------------------------------------------------ iç işler

    def _set_status(self, state: State) -> None:
        text, color = STATUS[state]
        self.status.setText(text)
        self.status.setStyleSheet(f"color: {color};")

    def _show_hint(self) -> None:
        if self._trigger:
            action = "tuşunu basılı tutup konuşun" if self._hold_mode else "tuşuna basın"
            self.detail.setText(f"{self._model_info} Başka bir uygulamada yazı alanına tıklayın ve {self._trigger} {action}.".strip())
        elif self._model_info:
            self.detail.setText(self._model_info)

    def closeEvent(self, event) -> None:  # noqa: N802 — Qt'nin yöntem adı
        self.closed.emit()
        super().closeEvent(event)
