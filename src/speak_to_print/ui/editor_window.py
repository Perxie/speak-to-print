"""Düzenleme penceresi: çevrilen metnin düzenlenebildiği, odak alan küçük pencere.

Dinleme penceresi odak almadığı için içine yazı yazılamaz. Kullanıcı oradaki
metne (ya da Düzenle'ye) tıklayınca bu pencere, dinleme penceresinin hemen
üstünde açılır ve klavye odağını alır. Yeri ve "her zaman üstte" olması KWin
pencere kuralıyla sağlanır (kwin_rules.ensure_editor_rule).

Bu pencere odaktayken yapılan yeni bir dikte, metnin içine, imlecin olduğu
yere yazılır.

Görsel dil için bkz. docs/tasarim.md.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from ..config import EDITOR_SIZE, EDITOR_TITLE
from ..controller import State
from . import theme
from .widgets import Card, CropFrame, PrintedText

HINT = "Ctrl+Enter yapıştırır, Esc kapatır"


class EditorWindow(Card):
    listen_clicked = Signal()  # dikteyi başlat / bitir; metin bu pencereye, imlecin olduğu yere yazılır
    paste_clicked = Signal(str)  # düzenlenmiş metin, önceki uygulamaya yazılsın
    copy_clicked = Signal(str)
    text_edited = Signal(str)  # metin değişti (son metin güncel kalsın diye)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(EDITOR_TITLE)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint)
        theme.prepare_frameless(self)
        self.setFixedSize(*EDITOR_SIZE)

        title = QLabel("Metni düzenle")
        title.setFont(theme.ui_font(15, 600))
        self.note = QLabel(HINT)
        self.note.setTextFormat(Qt.TextFormat.PlainText)  # dışarıdan gelen metin: HTML gibi yorumlanmasın
        self.note.setFont(theme.ui_font(12, 400))
        self.note.setStyleSheet(f"color: {theme.LEAD};")
        self.note.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.text = PrintedText()
        self.text.setPlaceholderText("Yazın ya da “Dinlemeyi başlat”a basıp konuşun.")
        self._crop = CropFrame()
        self._crop.set_mark_color(theme.YELLOW)  # düzenlenebilir alan: eylem rengi
        crop_layout = QVBoxLayout(self._crop)
        crop_layout.setContentsMargins(12, 6, 6, 6)
        crop_layout.addWidget(self.text)

        self.listen_button = QPushButton("Dinlemeyi başlat")
        self.listen_button.setToolTip("Konuştuklarınız bu metnin içine, imlecin olduğu yere yazılır.")
        # Düğme klavye odağını almasın: odak metin alanında kalmalı ki dikte oraya yazılsın.
        self.listen_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.copy_button = QPushButton("Kopyala")
        self.paste_button = QPushButton("Yapıştır")
        self.paste_button.setToolTip("Bu pencereyi kapatır ve metni önceki uygulamada imlecin olduğu yere yazar.")
        self.close_button = QPushButton("Kapat")
        theme.set_kind(self.paste_button, "primary")
        theme.set_kind(self.close_button, "quiet")
        for button in (self.listen_button, self.copy_button, self.paste_button, self.close_button):
            button.setFont(theme.ui_font(13, 600))
            button.setCursor(Qt.CursorShape.PointingHandCursor)

        top = QHBoxLayout()
        top.addWidget(title)
        top.addWidget(self.note, 1)
        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        buttons.addWidget(self.listen_button)
        buttons.addStretch(1)
        for button in (self.copy_button, self.paste_button, self.close_button):
            buttons.addWidget(button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 13, 18, 14)
        layout.setSpacing(9)
        layout.addLayout(top)
        layout.addWidget(self._crop, 1)
        layout.addLayout(buttons)

        self.text.textChanged.connect(lambda: self.text_edited.emit(self.text.toPlainText()))
        self.text.textChanged.connect(lambda: self.note.setText(HINT))  # eski uyarı kalmasın
        self.listen_button.clicked.connect(self.listen_clicked)
        self.copy_button.clicked.connect(lambda: self.copy_clicked.emit(self.text.toPlainText()))
        self.paste_button.clicked.connect(self._paste)
        self.close_button.clicked.connect(self.hide)
        for keys, action in (("Ctrl+Return", self._paste), ("Ctrl+Enter", self._paste), ("Escape", self.hide)):
            QShortcut(QKeySequence(keys), self).activated.connect(action)

    def open_with(self, text: str) -> None:
        """Pencereyi verilen metinle açar ve imleci metnin sonuna koyar."""
        if not self.isVisible() or self.text.toPlainText() != text:
            self.text.blockSignals(True)
            self.text.setPlainText(text)
            self.text.blockSignals(False)
        self.text.moveCursor(QTextCursor.MoveOperation.End)
        self.note.setText(HINT)
        self.show()
        self.raise_()
        self.activateWindow()
        self.text.setFocus()

    def set_state(self, state: State) -> None:
        self.listen_button.setText(state.listen_label)
        self.listen_button.setEnabled(state.can_toggle_listening)

    def show_note(self, text: str) -> None:
        self.note.setText(text)

    def _paste(self) -> None:
        self.paste_clicked.emit(self.text.toPlainText())
