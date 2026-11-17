"""Ayarlar penceresi. Değişiklikler anında uygulanır ve kaydedilir; ayrı bir "Kaydet" düğmesi yoktur.

Dört bölüm: kısayol, ses, metin ve sözlük. Görsel dil için bkz. docs/tasarim.md.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import (QComboBox, QGridLayout, QHBoxLayout, QLabel, QPushButton, QRadioButton, QSlider,
                               QVBoxLayout, QWidget)

from ..audio import default_microphone, device_id, microphones
from ..desktop_entry import APP_NAME
from ..settings import Settings
from . import theme
from .widgets import CropFrame, Keycap, PrintedText, Rule, Switch


def _title(text: str) -> QLabel:
    label = QLabel(text)
    label.setFont(theme.ui_font(15, 600))
    return label


def _label(text: str) -> QLabel:
    label = QLabel(text)
    label.setFont(theme.ui_font(13, 500))
    label.setStyleSheet(f"color: {theme.LEAD};")
    return label


def _help(text: str) -> QLabel:
    label = QLabel(text)
    label.setFont(theme.ui_font(12, 400))
    label.setStyleSheet(f"color: {theme.LEAD};")
    label.setWordWrap(True)
    return label


class SettingsDialog(QWidget):
    configure_shortcut_clicked = Signal()
    test_sound_clicked = Signal()

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._settings = settings
        self._refreshing = False
        self.setWindowTitle(f"{APP_NAME} — Ayarlar")
        self.resize(600, 790)
        self.setMinimumSize(520, 760)

        # Kısayol
        self.shortcut = Keycap("bekleniyor")
        self.shortcut_button = QPushButton("Değiştir")
        self.mode_toggle = QRadioButton("Bas başlat, tekrar bas bitir")
        self.mode_hold = QRadioButton("Basılı tutarken dinle, bırakınca bitir")

        # Ses
        self.microphone = QComboBox()
        self.sounds = Switch("Dinleme başlarken ve biterken kısa bir ses çal")
        self.sound_volume = QSlider(Qt.Orientation.Horizontal)
        self.sound_volume.setRange(5, 100)
        self.sound_volume.setFixedWidth(160)
        self.sound_volume.setToolTip("Ses yüksekliği")
        self.test_sound_button = QPushButton("Sesi dene")

        # Metin
        self.output_method = QComboBox()
        self.output_method.addItem("kwin-type (önerilen; çalışmazsa panoya geçer)", "auto")
        self.output_method.addItem("Pano + Shift+Insert (her zaman)", "clipboard")
        self.auto_paste = Switch("Çevrilen metni imlecin olduğu yere kendiliğinden yaz")
        self.use_prompt = Switch("Noktalama ipucu: modele noktalı bir örnek metin ver")
        self.keep_history = Switch("Dikte edilen metinleri geçmişe kaydet")
        self.keep_history.setToolTip("Kapalıyken yeni dikteler kaydedilmez; var olan kayıtlar silinmez.")

        # Sözlük
        self.vocabulary = PrintedText()
        self.vocabulary.setPlaceholderText("Her satıra bir terim: commit, refactor, pull request…")
        vocabulary_frame = CropFrame()
        vocabulary_frame.set_mark_color(theme.YELLOW)
        vocabulary_frame.setMinimumHeight(110)
        frame_layout = QVBoxLayout(vocabulary_frame)
        frame_layout.setContentsMargins(12, 6, 6, 6)
        frame_layout.addWidget(self.vocabulary)

        close_button = QPushButton("Kapat")
        for button in (self.shortcut_button, self.test_sound_button, close_button):
            button.setFont(theme.ui_font(13, 600))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        for widget in (self.mode_toggle, self.mode_hold, self.microphone, self.output_method):
            widget.setFont(theme.ui_font(13, 500))
        for combo in (self.microphone, self.output_method):
            combo.setMinimumHeight(34)  # pencere daralınca açılır kutular ezilmesin

        shortcut_row = QHBoxLayout()
        shortcut_row.setSpacing(8)
        shortcut_row.addWidget(self.shortcut)
        shortcut_row.addWidget(self.shortcut_button)
        shortcut_row.addStretch(1)
        modes = QVBoxLayout()
        modes.setSpacing(6)
        modes.addWidget(self.mode_toggle)
        modes.addWidget(self.mode_hold)
        volume_row = QHBoxLayout()
        volume_row.setSpacing(10)
        volume_row.addWidget(self.sound_volume)
        volume_row.addWidget(self.test_sound_button)
        volume_row.addStretch(1)

        def section(title: str, rows: list[tuple[str, object]]) -> QVBoxLayout:
            """Başlık ve altında "etiket: bileşen" satırları. Etiketi boş olan satır tam genişlikte durur."""
            box = QVBoxLayout()
            box.setSpacing(10)
            box.addWidget(_title(title))
            grid = QGridLayout()
            grid.setHorizontalSpacing(16)
            grid.setVerticalSpacing(10)
            grid.setColumnMinimumWidth(0, 120)
            grid.setColumnStretch(1, 1)
            for row, (label, content) in enumerate(rows):
                if label:
                    grid.addWidget(_label(label), row, 0, Qt.AlignmentFlag.AlignTop)
                column, span = (1, 1) if label else (0, 2)
                if isinstance(content, QWidget):
                    grid.addWidget(content, row, column, 1, span)
                else:
                    grid.addLayout(content, row, column, 1, span)
            box.addLayout(grid)
            return box

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 18)
        layout.setSpacing(14)
        layout.addLayout(section("Kısayol", [("Tuş", shortcut_row), ("Davranış", modes)]))
        layout.addWidget(Rule())
        layout.addLayout(section("Ses", [("Mikrofon", self.microphone), ("", self.sounds), ("Yükseklik", volume_row)]))
        layout.addWidget(Rule())
        layout.addLayout(section("Metin", [("Yazma yöntemi", self.output_method), ("", self.auto_paste),
                                           ("", self.use_prompt), ("", self.keep_history)]))
        layout.addWidget(Rule())
        layout.addWidget(_title("Sözlük"))
        layout.addWidget(_help("Yanlış yazıldığını gördüğünüz terimleri buraya ekleyin; model bu yazımları önceden görür "
                               "ve onlara yönelir. Liste kısa kaldıkça işe yarıyor: denemede 3 terim hepsini düzeltti, "
                               "31 terimlik liste hiçbirini düzeltmedi."))
        layout.addWidget(vocabulary_frame, 1)
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        bottom.addWidget(close_button)
        layout.addLayout(bottom)

        self.shortcut_button.clicked.connect(self.configure_shortcut_clicked)
        self.test_sound_button.clicked.connect(self.test_sound_clicked)
        self.mode_toggle.toggled.connect(self._on_mode_changed)
        self.microphone.activated.connect(self._on_microphone_chosen)
        self.output_method.activated.connect(
            lambda _index: setattr(self._settings, "output_method", self.output_method.currentData()))
        self.auto_paste.toggled.connect(lambda value: setattr(self._settings, "auto_paste", value))
        self.use_prompt.toggled.connect(lambda value: setattr(self._settings, "use_prompt", value))
        self.keep_history.toggled.connect(lambda value: setattr(self._settings, "keep_history", value))
        self.sounds.toggled.connect(lambda value: setattr(self._settings, "sounds", value))
        self.sound_volume.valueChanged.connect(self._on_volume_changed)
        self.vocabulary.textChanged.connect(self._on_vocabulary_changed)
        close_button.clicked.connect(self.hide)

        # Mikrofon takılıp çıkarılınca listeyi güncelle.
        self._devices = QMediaDevices(self)
        self._devices.audioInputsChanged.connect(self.refresh)
        settings.changed.connect(self.refresh)
        self.refresh()

    def set_shortcut(self, trigger: str) -> None:
        self.shortcut.set_text(trigger or "atanmamış", muted=not trigger)

    def open(self) -> None:
        self.refresh()
        self.show()
        self.raise_()
        self.activateWindow()

    def refresh(self) -> None:
        """Bileşenleri ayarların güncel değerleriyle doldurur (sinyal döngüsü oluşturmadan)."""
        self._refreshing = True
        try:
            settings = self._settings
            self.mode_hold.setChecked(settings.hotkey_mode == "hold")
            self.mode_toggle.setChecked(settings.hotkey_mode != "hold")
            self.output_method.setCurrentIndex(max(0, self.output_method.findData(settings.output_method)))
            self.auto_paste.setChecked(settings.auto_paste)
            self.use_prompt.setChecked(settings.use_prompt)
            self.keep_history.setChecked(settings.keep_history)
            self.sounds.setChecked(settings.sounds)
            self.sound_volume.setValue(settings.sound_volume)
            if self._vocabulary_terms() != settings.vocabulary:
                self.vocabulary.setPlainText("\n".join(settings.vocabulary))
            self._fill_microphones()
        finally:
            self._refreshing = False

    def _fill_microphones(self) -> None:
        default = default_microphone()
        default_name = default.description() if default is not None else "mikrofon yok"
        self.microphone.clear()
        self.microphone.addItem(f"Sistem varsayılanı ({default_name})", "")
        connected = {device_id(mic): mic.description() for mic in microphones()}
        for identifier, name in connected.items():
            self.microphone.addItem(name, identifier)
        chosen = self._settings.microphone_id
        if chosen and chosen not in connected:
            self.microphone.addItem("Seçili mikrofon bağlı değil (varsayılan kullanılır)", chosen)
        self.microphone.setCurrentIndex(max(0, self.microphone.findData(chosen)))

    def _vocabulary_terms(self) -> list[str]:
        return [line.strip() for line in self.vocabulary.toPlainText().splitlines() if line.strip()]

    def _on_mode_changed(self, _checked: bool) -> None:
        if not self._refreshing:
            self._settings.hotkey_mode = "hold" if self.mode_hold.isChecked() else "toggle"

    def _on_volume_changed(self, value: int) -> None:
        if not self._refreshing:
            self._settings.sound_volume = value

    def _on_microphone_chosen(self, _index: int) -> None:
        self._settings.microphone_id = self.microphone.currentData() or ""

    def _on_vocabulary_changed(self) -> None:
        if not self._refreshing:
            self._settings.vocabulary = self._vocabulary_terms()
