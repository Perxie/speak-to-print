"""Ana pencere: durum, kısayol, ayarlar ve çeviri geçmişi.

Bu pencere kapatılınca uygulama tamamen kapanır.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox,
                               QPlainTextEdit, QPushButton, QVBoxLayout, QWidget)

from ..controller import Outcome, State
from ..desktop_entry import APP_NAME
from ..history import Entry

PREVIEW_LENGTH = 90  # listede gösterilen metnin en fazla uzunluğu


def _summary(entry: Entry) -> str:
    text = " ".join(entry.text.split())
    if len(text) > PREVIEW_LENGTH:
        text = text[: PREVIEW_LENGTH - 1] + "…"
    return f"{entry.created_at:%d.%m %H:%M}  {text}"


class MainWindow(QWidget):
    configure_shortcut_clicked = Signal()
    listen_clicked = Signal()
    copy_clicked = Signal(str)
    edit_clicked = Signal(str)  # seçili metni düzenleme penceresinde aç
    delete_clicked = Signal(int)  # geçmiş kaydının kimliği
    clear_clicked = Signal()
    auto_paste_toggled = Signal(bool)
    use_prompt_toggled = Signal(bool)
    closed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(620, 600)
        self._trigger = ""
        self._model_info = ""

        self.status = QLabel("Model yükleniyor…")
        self.status.setStyleSheet("font-size: 15pt; font-weight: bold; padding: 4px;")
        self.detail = QLabel()
        self.detail.setWordWrap(True)
        self.listen_button = QPushButton("Dinlemeyi başlat")
        self.listen_button.setEnabled(False)
        self.listen_button.setToolTip("Bu düğmeyle başlatınca bu pencere önde olduğu için metin başka uygulamaya yazılmaz; "
                                      "küçük pencerede gösterilir, oradan kopyalayabilir, düzenleyebilir ya da yapıştırabilirsiniz.")

        self.shortcut = QLabel("Kısayol: bekleniyor…")
        self.shortcut_button = QPushButton("Kısayolu ayarla…")
        self.shortcut_button.setEnabled(False)

        self.auto_paste = QCheckBox("Otomatik yapıştır: çevrilen metni imlecin olduğu yere kendiliğinden yaz")
        self.use_prompt = QCheckBox("Noktalama ipucu: modele noktalı bir örnek metin ver")
        self.use_prompt.setToolTip("Açıkken noktalama ve büyük harf daha tutarlı olur; nadiren bir kelimeyi değiştirebilir.")

        self.history = QListWidget()
        self.history.setToolTip("Son dikteleriniz. Yalnızca bu bilgisayarda saklanır.")
        self.preview = QPlainTextEdit(readOnly=True)
        self.preview.setPlaceholderText("Listeden bir kayıt seçince metnin tamamı burada görünür.")
        self.preview.setMaximumHeight(110)
        self.copy_button = QPushButton("Kopyala")
        self.edit_button = QPushButton("Düzenle")
        self.delete_button = QPushButton("Sil")
        self.clear_button = QPushButton("Geçmişi temizle")
        self.quit_button = QPushButton("Çık")

        status_row = QHBoxLayout()
        status_row.addWidget(self.status, 1)
        status_row.addWidget(self.listen_button)
        shortcut_row = QHBoxLayout()
        shortcut_row.addWidget(self.shortcut, 1)
        shortcut_row.addWidget(self.shortcut_button)
        bottom = QHBoxLayout()
        for button in (self.copy_button, self.edit_button, self.delete_button):
            bottom.addWidget(button)
        bottom.addStretch(1)
        bottom.addWidget(self.clear_button)
        bottom.addWidget(self.quit_button)

        layout = QVBoxLayout(self)
        layout.addLayout(status_row)
        layout.addWidget(self.detail)
        layout.addLayout(shortcut_row)
        layout.addWidget(self.auto_paste)
        layout.addWidget(self.use_prompt)
        layout.addWidget(QLabel("Geçmiş:"))
        layout.addWidget(self.history, 1)
        layout.addWidget(self.preview)
        layout.addLayout(bottom)

        self.shortcut_button.clicked.connect(self.configure_shortcut_clicked)
        self.listen_button.clicked.connect(self.listen_clicked)
        self.history.currentItemChanged.connect(self._on_selection_changed)
        self.history.itemDoubleClicked.connect(lambda _item: self._edit_selected())
        self.copy_button.clicked.connect(lambda: self.copy_clicked.emit(self.preview.toPlainText()))
        self.edit_button.clicked.connect(self._edit_selected)
        self.delete_button.clicked.connect(self._delete_selected)
        self.clear_button.clicked.connect(self._confirm_clear)
        self.quit_button.clicked.connect(self.close)
        self.auto_paste.toggled.connect(self.auto_paste_toggled)
        self.use_prompt.toggled.connect(self.use_prompt_toggled)
        self._on_selection_changed()

    # ------------------------------------------------------------ ayarlar ve durum

    def set_options(self, auto_paste: bool, use_prompt: bool) -> None:
        for box, value in ((self.auto_paste, auto_paste), (self.use_prompt, use_prompt)):
            if box.isChecked() != value:
                box.blockSignals(True)
                box.setChecked(value)
                box.blockSignals(False)

    def set_state(self, state: State, failure: str = "") -> None:
        self.status.setText({State.LOADING: "Model yükleniyor…", State.IDLE: "Hazır",
                             State.LISTENING: "● Dinliyor", State.PAUSED: "❚❚ Beklemede",
                             State.TRANSCRIBING: "Çevriliyor…", State.FAILED: "Model yüklenemedi"}[state])
        self.listen_button.setText("Bitir" if state in (State.LISTENING, State.PAUSED) else "Dinlemeyi başlat")
        self.listen_button.setEnabled(state in (State.IDLE, State.LISTENING, State.PAUSED))
        if state is State.FAILED:
            self.detail.setText(failure)
        elif state is State.IDLE:
            self._show_hint()
        elif state is State.LISTENING:
            self.detail.setText("Konuşun. Bitirmek için kısayola ya da Bitir'e basın.")

    def set_model_info(self, seconds: float, device: str) -> None:
        self._model_info = f"Model {seconds:.1f} sn'de yüklendi ({'ekran kartı' if device == 'cuda' else device})."
        self._show_hint()

    def set_shortcut(self, trigger: str) -> None:
        self._trigger = trigger
        self.shortcut_button.setEnabled(True)
        if trigger:
            self.shortcut.setText(f"Kısayol: {trigger}")
            self.shortcut.setStyleSheet("")
        else:
            self.shortcut.setText("Kısayol atanmamış. Dikte için bir tuş seçin →")
            self.shortcut.setStyleSheet("color: #f39c12; font-weight: bold;")
        self._show_hint()

    def set_shortcut_error(self, message: str) -> None:
        self.shortcut.setText(f"Kısayol hatası: {message}")
        self.shortcut.setStyleSheet("color: #ed1515;")

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
        """Yeni kaydı en üste ekler ve seçer."""
        self.history.insertItem(0, self._item(entry))
        self.history.setCurrentRow(0)

    def _item(self, entry: Entry) -> QListWidgetItem:
        item = QListWidgetItem(_summary(entry))
        item.setData(Qt.ItemDataRole.UserRole, entry)
        item.setToolTip(entry.text)
        return item

    def _selected(self) -> Entry | None:
        item = self.history.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _on_selection_changed(self, *_args) -> None:
        entry = self._selected()
        self.preview.setPlainText(entry.text if entry else "")
        for button in (self.copy_button, self.edit_button, self.delete_button):
            button.setEnabled(entry is not None)
        self.clear_button.setEnabled(self.history.count() > 0)

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

    def _show_hint(self) -> None:
        if self._trigger:
            self.detail.setText(f"{self._model_info} Başka bir uygulamada yazı alanına tıklayın ve {self._trigger} tuşuna basın.".strip())
        elif self._model_info:
            self.detail.setText(self._model_info)

    def closeEvent(self, event) -> None:  # noqa: N802 — Qt'nin yöntem adı
        self.closed.emit()
        super().closeEvent(event)
