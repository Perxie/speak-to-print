"""Dinleme penceresi: ekranın alt ortasında duran, odak almayan küçük pencere.

Odak almaması KWin pencere kuralıyla sağlanır (kwin_rules.py); bu sayede
düğmelere tıklansa bile klavye odağı yazı yazılan uygulamada kalır. Aynı
nedenle bu pencereye klavyeyle yazı yazılamaz: metin burada yalnızca
gösterilir, düzenleme ayrı bir pencerede yapılır.

Kural pencerenin sol üst köşesini sabitlediği için pencerenin boyutu sabittir.
Ortadaki alan duruma göre üç şeyden birini gösterir: ses çizgisi (dinlerken),
dizilmiş metin (bittiğinde) ya da kısa bir ileti (yazılacak metin yokken).

Görsel dil için bkz. docs/tasarim.md.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget

from ..config import POPUP_SIZE, POPUP_TITLE, RESULT_HIDE_SECONDS
from ..controller import Outcome, State
from . import theme
from .widgets import Card, CropFrame, PrintedText, Switch, Waveform


class ListeningPopup(Card):
    pause_clicked = Signal()
    finish_clicked = Signal()
    cancel_clicked = Signal()
    paste_clicked = Signal()
    copy_clicked = Signal(str)
    auto_paste_toggled = Signal(bool)
    listen_clicked = Signal()  # yeni bir dikte başlat
    edit_requested = Signal(str)  # kullanıcı metne ya da Düzenle'ye tıkladı

    def __init__(self, seconds_recorded) -> None:
        """`seconds_recorded`: o ana kadar kaydedilen süreyi döndüren işlev."""
        super().__init__()
        self._seconds_recorded = seconds_recorded
        self._state = State.IDLE
        self._heard_sound = False
        self._hold_mode = False

        self.setWindowTitle(POPUP_TITLE)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        theme.prepare_frameless(self)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(*POPUP_SIZE)

        # Üst satır: durum, süre, kısa not ve "Dinlemeyi başlat".
        self._dot = QLabel()
        self._dot.setFixedSize(9, 9)
        self.status = QLabel()
        self.status.setFont(theme.ui_font(15, 600))
        self._time = QLabel()
        self._time.setFont(theme.ui_font(15, 500))
        self._time.setStyleSheet(f"color: {theme.LEAD};")
        self.note = QLabel()
        self.note.setTextFormat(Qt.TextFormat.PlainText)  # dışarıdan gelen metin: HTML gibi yorumlanmasın
        self.note.setFont(theme.ui_font(12, 400))
        self.note.setStyleSheet(f"color: {theme.LEAD};")
        self.note.setWordWrap(True)
        self.listen_button = QPushButton("Dinlemeyi başlat")
        self.listen_button.setToolTip("Yeni bir dikte başlatır. Metin, o an yazı yazdığınız uygulamaya gider.")
        self.listen_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # Orta alan: ses çizgisi / dizilmiş metin / ileti.
        self.waveform = Waveform()
        self.text = PrintedText(read_only=True)
        self.text.setToolTip("Düzenlemek için metne tıklayın.")
        self.text.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        self.text.viewport().installEventFilter(self)
        self._crop = CropFrame()
        crop_layout = QVBoxLayout(self._crop)
        crop_layout.setContentsMargins(12, 6, 6, 6)
        crop_layout.addWidget(self.text)
        self._message = QLabel()
        self._message.setTextFormat(Qt.TextFormat.PlainText)  # dışarıdan gelen metin: HTML gibi yorumlanmasın
        self._message.setFont(theme.ui_font(15, 500))
        self._message.setWordWrap(True)
        self._message.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self._middle = QStackedWidget()
        for page in (self.waveform, self._crop, self._message):
            self._middle.addWidget(page)

        # Alt satır: otomatik yapıştırma anahtarı ve duruma göre düğmeler.
        self.auto_paste = Switch("Otomatik yapıştır")
        self.auto_paste.setToolTip("Açıkken çevrilen metin imlecin olduğu yere kendiliğinden yazılır.")
        self.pause_button = QPushButton("Beklet")
        self.cancel_button = QPushButton("İptal")
        self.finish_button = QPushButton("Bitir")
        self.edit_button = QPushButton("Düzenle")
        self.copy_button = QPushButton("Kopyala")
        self.paste_button = QPushButton("Yapıştır")
        self.close_button = QPushButton("Kapat")
        theme.set_kind(self.finish_button, "primary")
        theme.set_kind(self.cancel_button, "quiet")
        theme.set_kind(self.close_button, "quiet")
        self._listening_buttons = (self.pause_button, self.cancel_button, self.finish_button)
        self._result_buttons = (self.edit_button, self.copy_button, self.paste_button, self.close_button)
        buttons = (self.listen_button, *self._listening_buttons, *self._result_buttons)
        for button in buttons:
            button.setFont(theme.ui_font(13, 600))
            button.setCursor(Qt.CursorShape.PointingHandCursor)

        # Üst satırın yüksekliği sabit: düğme görünse de görünmese de durum yazısı yerinden oynamaz.
        top_row = QWidget()
        top_row.setFixedHeight(34)
        top = QHBoxLayout(top_row)
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(8)
        top.addWidget(self._dot)
        top.addWidget(self.status)
        top.addWidget(self._time)
        top.addSpacing(8)
        top.addWidget(self.note, 1)
        top.addStretch(0)
        top.addWidget(self.listen_button)
        bottom = QHBoxLayout()
        bottom.setSpacing(6)
        bottom.addWidget(self.auto_paste)
        bottom.addStretch(1)
        for button in (*self._listening_buttons, *self._result_buttons):
            bottom.addWidget(button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 13, 18, 14)
        layout.setSpacing(9)
        layout.addWidget(top_row)
        layout.addWidget(self._middle, 1)
        layout.addLayout(bottom)

        # Hiçbir bileşen klavye odağı istemesin.
        for widget in (self.text, self.auto_paste, self.waveform, *buttons):
            widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.pause_button.clicked.connect(self.pause_clicked)
        self.finish_button.clicked.connect(self.finish_clicked)
        self.cancel_button.clicked.connect(self.cancel_clicked)
        self.listen_button.clicked.connect(self.listen_clicked)
        self.paste_button.clicked.connect(self.paste_clicked)
        self.copy_button.clicked.connect(lambda: self.copy_clicked.emit(self.text.toPlainText()))
        self.edit_button.clicked.connect(self._request_edit)
        self.close_button.clicked.connect(self.hide)
        self.auto_paste.toggled.connect(self.auto_paste_toggled)

        self._shown_status: tuple[str, str, bool] | None = None
        self._clock = QTimer(self)  # dinlerken süreyi güncel tutar
        self._clock.setInterval(200)
        self._clock.timeout.connect(self._refresh_status)
        self._hide_timer = QTimer(self)  # sonuç gösterildikten sonra kendiliğinden kapanma
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._hide_unless_hovered)
        self._show_buttons(listening=True)
        self._set_status("", theme.LEAD)

    # ------------------------------------------------------------ dışarıdan çağrılanlar

    def set_auto_paste(self, enabled: bool) -> None:
        if self.auto_paste.isChecked() != enabled:
            self.auto_paste.blockSignals(True)
            self.auto_paste.setChecked(enabled)
            self.auto_paste.blockSignals(False)

    def set_hold_mode(self, enabled: bool) -> None:
        """"Basılı tut" kipinde tuşu bırakmak bitirir; Beklet ve Bitir düğmeleri gizlenir."""
        self._hold_mode = enabled

    def set_state(self, state: State) -> None:
        self._state = state
        if state is State.LISTENING:
            self._hide_timer.stop()
            if not self.isVisible() or not self._clock.isActive():  # yeni bir dikte başlıyor
                self._heard_sound = False
                self.text.clear()
                self.note.clear()
                self.waveform.clear()
            self.pause_button.setText("Beklet")
            self._show_buttons(listening=True)
            self._middle.setCurrentWidget(self.waveform)
            self.waveform.set_mode("live")
            self._clock.start()
            self.show()
        elif state is State.PAUSED:
            self.pause_button.setText("Devam")
            self.waveform.set_mode("paused")
        elif state is State.TRANSCRIBING:
            self._clock.stop()
            self.waveform.set_mode("processing")
            for button in self._listening_buttons:
                button.setEnabled(False)
        elif state is State.IDLE:
            self._clock.stop()
            self.waveform.set_mode("paused")
        self._refresh_status()

    def set_level(self, level: float) -> None:
        if level > 0.02:
            self._heard_sound = True
        self.waveform.push(level)

    def show_outcome(self, outcome: Outcome) -> None:
        self.note.setText(outcome.shown_note)
        self._show_buttons(listening=False)
        self.edit_button.setEnabled(bool(outcome.text))
        self.copy_button.setEnabled(bool(outcome.text))
        self.paste_button.setEnabled(bool(outcome.text))
        self.paste_button.setText("Yeniden yapıştır" if outcome.pasted else "Yapıştır")
        self.text.setPlainText(outcome.text)
        if outcome.text:
            self._middle.setCurrentWidget(self._crop)
            # Not, durum yazısını yinelemekten başka bir şey söylemiyorsa gösterilmez.
            self.note.setVisible(outcome.note.strip(". ") != ("Yazıldı" if outcome.pasted else ""))
            if outcome.pasted:
                self._set_status("Yazıldı", theme.CYAN)
                self._crop.set_mark_color(theme.CYAN)
            else:
                self._set_status("Metin hazır", theme.PAPER)
                self._crop.set_mark_color(theme.LEAD)
            # Sarı, sıradaki en olası eyleme verilir: yazılmadıysa Yapıştır, yazıldıysa yeni dikte.
            theme.set_kind(self.paste_button, "" if outcome.pasted else "primary")
            theme.set_kind(self.listen_button, "primary" if outcome.pasted else "")
        else:
            self._show_message("Metin yok", theme.LEAD, outcome.shown_note)
        self.show()
        # Metin yazıldıysa pencere kendiliğinden kapanır. Yazılmadıysa metnin tek durduğu
        # yer burasıdır; kullanıcı Kapat'a basana kadar açık kalır.
        if outcome.pasted or not outcome.text:
            self._hide_timer.start(RESULT_HIDE_SECONDS * 1000)
        else:
            self._hide_timer.stop()

    def show_notice(self, text: str, problem: bool = False) -> None:
        """Dinleme dışındaki kısa bilgiler (ör. iptal, çok kısa kayıt, mikrofonun kaybolması)."""
        self.note.setText(text)
        if self._state in (State.LISTENING, State.PAUSED, State.TRANSCRIBING):
            return  # dinleme sürüyor: not üst satırda görünür, ekran değişmez
        self.text.clear()
        self._show_buttons(listening=False)
        for button in (self.edit_button, self.copy_button, self.paste_button):
            button.setEnabled(False)
        self._show_message("Sorun" if problem else "Bilgi", theme.RED if problem else theme.PAPER, text)
        self.show()
        self._hide_timer.start(6000 if problem else 4000)

    def show_copied(self) -> None:
        self.note.setText("Panoya kopyalandı.")
        self.note.setVisible(True)

    # ------------------------------------------------------------ iç işler

    def _show_message(self, status: str, color: str, message: str) -> None:
        """Orta alanda dizilmiş metin yerine kısa bir ileti gösterir."""
        self._set_status(status, color)
        self._message.setText(message)
        self._message.setStyleSheet(f"color: {theme.LEAD if color == theme.LEAD else theme.PAPER};")
        self._middle.setCurrentWidget(self._message)
        self.note.setVisible(False)  # aynı metin ortada büyük yazıyor
        for button in (self.edit_button, self.copy_button, self.paste_button):
            button.setVisible(False)  # yazılacak metin yok: yalnızca Kapat kalır
        theme.set_kind(self.paste_button, "")
        theme.set_kind(self.listen_button, "primary")

    def _set_status(self, text: str, color: str, hollow: bool = False) -> None:
        # Saat bunu dinlerken saniyede beş kez çağırıyor; durum değişmediyse stil yeniden hesaplanmasın.
        if (text, color, hollow) == self._shown_status:
            return
        self._shown_status = (text, color, hollow)
        self.status.setText(text)
        self.status.setStyleSheet(f"color: {color};")
        fill = "transparent" if hollow else color
        self._dot.setStyleSheet(f"background: {fill}; border: 1.5px solid {color}; border-radius: 4px;")
        self._dot.setVisible(bool(text))

    def _request_edit(self) -> None:
        if self.edit_button.isVisible() and self.edit_button.isEnabled():
            self.edit_requested.emit(self.text.toPlainText())

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 — Qt'nin yöntem adı
        # Metin alanına tıklanınca düzenleme penceresi açılır (bu pencere odak alamadığı için).
        if watched is self.text.viewport() and event.type() == QEvent.Type.MouseButtonRelease:
            self._request_edit()
        return super().eventFilter(watched, event)

    def _show_buttons(self, listening: bool) -> None:
        for button in self._listening_buttons:
            hidden_in_hold_mode = self._hold_mode and button is not self.cancel_button
            button.setVisible(listening and not hidden_in_hold_mode)
            button.setEnabled(True)
        for button in self._result_buttons:
            button.setVisible(not listening)
        self.listen_button.setVisible(not listening)
        self._time.setVisible(listening)
        self.note.setVisible(True)

    def _refresh_status(self) -> None:
        seconds = int(self._seconds_recorded())
        self._time.setText(f"{seconds // 60}:{seconds % 60:02d}")
        if self._state is State.LISTENING:
            if self._heard_sound:
                self._set_status("Dinliyor", theme.MAGENTA)
            else:
                self._set_status("Ses bekleniyor", theme.LEAD, hollow=True)
        elif self._state is State.PAUSED:
            self._set_status("Beklemede", theme.LEAD, hollow=True)
        elif self._state is State.TRANSCRIBING:
            self._set_status("Çevriliyor", theme.CYAN)

    def _hide_unless_hovered(self) -> None:
        if self.underMouse():
            self._hide_timer.start(2000)  # fare üstündeyken kapanma
        else:
            self.hide()
