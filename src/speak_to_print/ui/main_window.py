"""Ana pencere (Faz 1: durum, kısayol, iki ayar ve son metin).

Bu pencere kapatılınca uygulama tamamen kapanır.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QCheckBox, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget)

from ..controller import Outcome, State
from ..desktop_entry import APP_NAME


class MainWindow(QWidget):
    configure_shortcut_clicked = Signal()
    listen_clicked = Signal()
    copy_clicked = Signal(str)
    auto_paste_toggled = Signal(bool)
    use_prompt_toggled = Signal(bool)
    closed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(560, 380)
        self._trigger = ""

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

        self.last_text = QPlainTextEdit(readOnly=True)
        self.last_text.setPlaceholderText("Son çevrilen metin burada görünecek.")
        self.copy_button = QPushButton("Kopyala")
        self.copy_button.setEnabled(False)
        self.quit_button = QPushButton("Çık")

        shortcut_row = QHBoxLayout()
        shortcut_row.addWidget(self.shortcut, 1)
        shortcut_row.addWidget(self.shortcut_button)
        bottom = QHBoxLayout()
        bottom.addWidget(self.copy_button)
        bottom.addStretch(1)
        bottom.addWidget(self.quit_button)

        layout = QVBoxLayout(self)
        status_row = QHBoxLayout()
        status_row.addWidget(self.status, 1)
        status_row.addWidget(self.listen_button)
        layout.addLayout(status_row)
        layout.addWidget(self.detail)
        layout.addLayout(shortcut_row)
        layout.addWidget(self.auto_paste)
        layout.addWidget(self.use_prompt)
        layout.addWidget(QLabel("Son metin:"))
        layout.addWidget(self.last_text, 1)
        layout.addLayout(bottom)

        self.shortcut_button.clicked.connect(self.configure_shortcut_clicked)
        self.listen_button.clicked.connect(self.listen_clicked)
        self.copy_button.clicked.connect(lambda: self.copy_clicked.emit(self.last_text.toPlainText()))
        self.quit_button.clicked.connect(self.close)
        self.auto_paste.toggled.connect(self.auto_paste_toggled)
        self.use_prompt.toggled.connect(self.use_prompt_toggled)

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
        if outcome.text:
            self.last_text.setPlainText(outcome.text)
            self.copy_button.setEnabled(True)
        self.detail.setText(outcome.note)

    def set_last_text(self, text: str) -> None:
        """Düzenleme penceresinde değişen metni buraya da yansıtır."""
        if self.last_text.toPlainText() != text:
            self.last_text.setPlainText(text)
            self.copy_button.setEnabled(bool(text))

    def show_notice(self, text: str) -> None:
        self.detail.setText(text)

    def _show_hint(self) -> None:
        info = getattr(self, "_model_info", "")
        if self._trigger:
            self.detail.setText(f"{info} Başka bir uygulamada yazı alanına tıklayın ve {self._trigger} tuşuna basın.".strip())
        elif info:
            self.detail.setText(info)

    def closeEvent(self, event) -> None:  # noqa: N802 — Qt'nin yöntem adı
        self.closed.emit()
        super().closeEvent(event)
