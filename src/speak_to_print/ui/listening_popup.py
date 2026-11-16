"""Dinleme penceresi: ekranın alt ortasında duran, odak almayan küçük pencere.

Odak almaması KWin pencere kuralıyla sağlanır (kwin_rules.py); bu sayede
düğmelere tıklansa bile klavye odağı yazı yazılan uygulamada kalır. Aynı
nedenle bu pencereye klavyeyle yazı yazılamaz: metin burada yalnızca
gösterilir, düzenleme ayrı bir pencerede yapılır.

Kural pencerenin sol üst köşesini sabitlediği için pencerenin boyutu sabittir.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QCheckBox, QHBoxLayout, QLabel, QPlainTextEdit, QProgressBar, QPushButton,
                               QVBoxLayout, QWidget)

from ..config import POPUP_SIZE, POPUP_TITLE, RESULT_HIDE_SECONDS
from ..controller import Outcome, State

STYLE = """
QWidget#popup { background: #232629; border: 1px solid #5f6265; border-radius: 8px; }
QLabel, QCheckBox { color: #eff0f1; }
QLabel#status { font-size: 13pt; font-weight: bold; }
QLabel#note { color: #bdc3c7; }
QPlainTextEdit { background: #1b1e20; color: #eff0f1; border: 1px solid #44484c; border-radius: 4px; }
QPushButton { padding: 5px 12px; background: #31363b; color: #eff0f1; border: 1px solid #5f6265; border-radius: 4px; }
QPushButton:hover { background: #3daee9; }
QPushButton:disabled { color: #7f8c8d; }
QProgressBar { background: #1b1e20; border: 1px solid #44484c; border-radius: 3px; max-height: 8px; }
QProgressBar::chunk { background: #27ae60; border-radius: 2px; }
"""


class ListeningPopup(QWidget):
    pause_clicked = Signal()
    finish_clicked = Signal()
    cancel_clicked = Signal()
    paste_clicked = Signal()
    copy_clicked = Signal(str)
    auto_paste_toggled = Signal(bool)

    def __init__(self, seconds_recorded) -> None:
        """`seconds_recorded`: o ana kadar kaydedilen süreyi döndüren işlev."""
        super().__init__()
        self._seconds_recorded = seconds_recorded
        self._state = State.IDLE
        self._heard_sound = False

        self.setObjectName("popup")
        self.setWindowTitle(POPUP_TITLE)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(*POPUP_SIZE)
        self.setStyleSheet(STYLE)

        self.status = QLabel()
        self.status.setObjectName("status")
        self.meter = QProgressBar()
        self.meter.setRange(0, 100)
        self.meter.setTextVisible(False)
        self.meter.setFixedWidth(150)
        self.auto_paste = QCheckBox("Otomatik yapıştır")
        self.auto_paste.setToolTip("Açıkken çevrilen metin imlecin olduğu yere kendiliğinden yazılır.")

        self.text = QPlainTextEdit(readOnly=True)
        self.text.setPlaceholderText("Çevrilen metin burada görünecek.")
        self.note = QLabel()
        self.note.setObjectName("note")
        self.note.setWordWrap(True)

        self.pause_button = QPushButton("Beklet")
        self.finish_button = QPushButton("Bitir")
        self.cancel_button = QPushButton("İptal")
        self.copy_button = QPushButton("Kopyala")
        self.paste_button = QPushButton("Yapıştır")
        self.close_button = QPushButton("Kapat")
        self._listening_buttons = (self.pause_button, self.finish_button, self.cancel_button)
        self._result_buttons = (self.copy_button, self.paste_button, self.close_button)

        top = QHBoxLayout()
        top.addWidget(self.status, 1)
        top.addWidget(self.meter)
        top.addWidget(self.auto_paste)
        buttons = QHBoxLayout()
        buttons.addWidget(self.note, 1)
        for widget in (*self._listening_buttons, *self._result_buttons):
            buttons.addWidget(widget)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.addLayout(top)
        layout.addWidget(self.text, 1)
        layout.addLayout(buttons)

        # Hiçbir bileşen klavye odağı istemesin.
        for widget in (self.text, self.auto_paste, self.meter, *self._listening_buttons, *self._result_buttons):
            widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.pause_button.clicked.connect(self.pause_clicked)
        self.finish_button.clicked.connect(self.finish_clicked)
        self.cancel_button.clicked.connect(self.cancel_clicked)
        self.paste_button.clicked.connect(self.paste_clicked)
        self.copy_button.clicked.connect(lambda: self.copy_clicked.emit(self.text.toPlainText()))
        self.close_button.clicked.connect(self.hide)
        self.auto_paste.toggled.connect(self.auto_paste_toggled)

        self._clock = QTimer(self)  # dinlerken süreyi güncel tutar
        self._clock.setInterval(200)
        self._clock.timeout.connect(self._refresh_status)
        self._hide_timer = QTimer(self)  # sonuç gösterildikten sonra kendiliğinden kapanma
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._hide_unless_hovered)
        self._show_buttons(listening=True)

    # ------------------------------------------------------------ dışarıdan çağrılanlar

    def set_auto_paste(self, enabled: bool) -> None:
        if self.auto_paste.isChecked() != enabled:
            self.auto_paste.blockSignals(True)
            self.auto_paste.setChecked(enabled)
            self.auto_paste.blockSignals(False)

    def set_state(self, state: State) -> None:
        self._state = state
        if state is State.LISTENING:
            self._hide_timer.stop()
            if not self.isVisible() or not self._clock.isActive():
                self._heard_sound = False
                self.text.clear()
                self.note.clear()
            self.pause_button.setText("Beklet")
            self._show_buttons(listening=True)
            self._clock.start()
            self.show()
        elif state is State.PAUSED:
            self.pause_button.setText("Devam")
        elif state is State.TRANSCRIBING:
            self._clock.stop()
            self.meter.setValue(0)
            for button in self._listening_buttons:
                button.setEnabled(False)
        elif state is State.IDLE:
            self._clock.stop()
            self.meter.setValue(0)
        self._refresh_status()

    def set_level(self, level: float) -> None:
        if level > 0.02:
            self._heard_sound = True
        # Konuşma seviyeleri küçük sayılardır; göstergede görünür olsun diye karekök alınır.
        self.meter.setValue(min(100, int(100 * level ** 0.5)))

    def show_outcome(self, outcome: Outcome) -> None:
        self.text.setPlainText(outcome.text)
        self.note.setText(outcome.note)
        self.status.setText("✓ Yazıldı" if outcome.pasted else ("Metin hazır" if outcome.text else "Yazılacak metin yok"))
        self.status.setStyleSheet("color: #27ae60;" if outcome.pasted else "color: #f39c12;")
        self._show_buttons(listening=False)
        self.copy_button.setEnabled(bool(outcome.text))
        self.paste_button.setEnabled(bool(outcome.text))
        self.paste_button.setText("Yeniden yapıştır" if outcome.pasted else "Yapıştır")
        self.show()
        # Metin yazıldıysa pencere kendiliğinden kapanır. Yazılmadıysa metnin tek durduğu
        # yer burasıdır; kullanıcı Kapat'a basana kadar açık kalır.
        if outcome.pasted or not outcome.text:
            self._hide_timer.start(RESULT_HIDE_SECONDS * 1000)
        else:
            self._hide_timer.stop()

    def show_notice(self, text: str) -> None:
        """Dinleme dışındaki kısa bilgiler (ör. iptal, çok kısa kayıt)."""
        if self._state in (State.LISTENING, State.PAUSED, State.TRANSCRIBING):
            self.note.setText(text)
            return
        self.text.clear()
        self.note.setText(text)
        self.status.setText("Bilgi")
        self.status.setStyleSheet("color: #f39c12;")
        self._show_buttons(listening=False)
        self.copy_button.setEnabled(False)
        self.paste_button.setEnabled(False)
        self.show()
        self._hide_timer.start(4000)

    def show_copied(self) -> None:
        self.note.setText("Panoya kopyalandı.")

    # ------------------------------------------------------------ iç işler

    def _show_buttons(self, listening: bool) -> None:
        for button in self._listening_buttons:
            button.setVisible(listening)
            button.setEnabled(True)
        for button in self._result_buttons:
            button.setVisible(not listening)

    def _refresh_status(self) -> None:
        seconds = int(self._seconds_recorded())
        clock = f"{seconds // 60}:{seconds % 60:02d}"
        if self._state is State.LISTENING:
            if self._heard_sound:
                self.status.setText(f"● Dinliyor  {clock}")
                self.status.setStyleSheet("color: #ed1515;")
            else:
                self.status.setText(f"● Mikrofon açık, ses bekleniyor  {clock}")
                self.status.setStyleSheet("color: #f39c12;")
        elif self._state is State.PAUSED:
            self.status.setText(f"❚❚ Beklemede  {clock}")
            self.status.setStyleSheet("color: #f39c12;")
        elif self._state is State.TRANSCRIBING:
            self.status.setText("Çevriliyor…")
            self.status.setStyleSheet("color: #3daee9;")

    def _hide_unless_hovered(self) -> None:
        if self.underMouse():
            self._hide_timer.start(2000)  # fare üstündeyken kapanma
        else:
            self.hide()
