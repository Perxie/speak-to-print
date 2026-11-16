"""Ayarlar penceresi. Değişiklikler anında uygulanır ve kaydedilir; ayrı bir "Kaydet" düğmesi yoktur."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
                               QRadioButton, QVBoxLayout, QWidget)

from ..audio import default_microphone, device_id, microphones
from ..desktop_entry import APP_NAME
from ..settings import Settings


class SettingsDialog(QWidget):
    configure_shortcut_clicked = Signal()

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._settings = settings
        self._refreshing = False
        self.setWindowTitle(f"{APP_NAME} — Ayarlar")
        self.resize(560, 560)

        # Kısayol
        self.shortcut = QLabel("bekleniyor…")
        self.shortcut_button = QPushButton("Değiştir…")
        shortcut_row = QHBoxLayout()
        shortcut_row.addWidget(self.shortcut, 1)
        shortcut_row.addWidget(self.shortcut_button)
        self.mode_toggle = QRadioButton("Bas başlat, tekrar bas bitir")
        self.mode_hold = QRadioButton("Basılı tutarken dinle, bırakınca bitir")
        mode_box = QVBoxLayout()
        mode_box.addWidget(self.mode_toggle)
        mode_box.addWidget(self.mode_hold)

        # Mikrofon ve yazma yöntemi
        self.microphone = QComboBox()
        self.output_method = QComboBox()
        self.output_method.addItem("kwin-type (önerilen; çalışmazsa panoya geçer)", "auto")
        self.output_method.addItem("Pano + Shift+Insert (her zaman)", "clipboard")

        # Seçenekler
        self.auto_paste = QCheckBox("Çevrilen metni imlecin olduğu yere kendiliğinden yaz")
        self.use_prompt = QCheckBox("Noktalama ipucu: modele noktalı bir örnek metin ver")
        self.keep_history = QCheckBox("Dikte edilen metinleri geçmişe kaydet")
        self.keep_history.setToolTip("Kapalıyken yeni dikteler kaydedilmez; var olan kayıtlar silinmez.")

        # Sözlük
        self.vocabulary = QPlainTextEdit()
        self.vocabulary.setPlaceholderText("Her satıra bir terim. Örnek:\ncommit\nrefactor\npull request")
        vocabulary_help = QLabel("Yanlış yazıldığını gördüğünüz terimleri buraya ekleyin; model bu yazımları önceden "
                                 "görür ve onlara yönelir. Liste kısa kaldıkça işe yarıyor: denemede 3 terim hepsini "
                                 "düzeltti, 31 terimlik liste hiçbirini düzeltmedi.")
        vocabulary_help.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Kısayol:", shortcut_row)
        form.addRow("Kısayol davranışı:", mode_box)
        form.addRow("Mikrofon:", self.microphone)
        form.addRow("Yazma yöntemi:", self.output_method)
        close_button = QPushButton("Kapat")
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        bottom.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.auto_paste)
        layout.addWidget(self.use_prompt)
        layout.addWidget(self.keep_history)
        layout.addWidget(QLabel("Sözlük:"))
        layout.addWidget(vocabulary_help)
        layout.addWidget(self.vocabulary, 1)
        layout.addLayout(bottom)

        self.shortcut_button.clicked.connect(self.configure_shortcut_clicked)
        self.mode_toggle.toggled.connect(self._on_mode_changed)
        self.microphone.activated.connect(self._on_microphone_chosen)
        self.output_method.activated.connect(
            lambda _index: setattr(self._settings, "output_method", self.output_method.currentData()))
        self.auto_paste.toggled.connect(lambda value: setattr(self._settings, "auto_paste", value))
        self.use_prompt.toggled.connect(lambda value: setattr(self._settings, "use_prompt", value))
        self.keep_history.toggled.connect(lambda value: setattr(self._settings, "keep_history", value))
        self.vocabulary.textChanged.connect(self._on_vocabulary_changed)
        close_button.clicked.connect(self.hide)

        # Mikrofon takılıp çıkarılınca listeyi güncelle.
        self._devices = QMediaDevices(self)
        self._devices.audioInputsChanged.connect(self.refresh)
        settings.changed.connect(self.refresh)
        self.refresh()

    def set_shortcut(self, trigger: str) -> None:
        self.shortcut.setText(trigger or "atanmamış")

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

    def _on_microphone_chosen(self, _index: int) -> None:
        self._settings.microphone_id = self.microphone.currentData() or ""

    def _on_vocabulary_changed(self) -> None:
        if not self._refreshing:
            self._settings.vocabulary = self._vocabulary_terms()
