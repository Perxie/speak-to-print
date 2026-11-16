"""Kullanıcı ayarları: ~/.config/speak-to-print/speak-to-print.conf (QSettings).

QSettings, Java'daki java.util.prefs.Preferences gibi: anahtar-değer saklar.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QSettings, Signal


class Settings(QObject):
    changed = Signal()

    def __init__(self, parent: QObject | None = None, store: QSettings | None = None) -> None:
        super().__init__(parent)
        self._store = store or QSettings("speak-to-print", "speak-to-print")

    def _bool(self, key: str, default: bool) -> bool:
        value = self._store.value(key, default)
        return value if isinstance(value, bool) else str(value).lower() == "true"

    def _set(self, key: str, value: bool) -> None:
        if self._bool(key, not value) != value:
            self._store.setValue(key, value)
            self._store.sync()
            self.changed.emit()

    @property
    def auto_paste(self) -> bool:
        """Çevrilen metin imlecin olduğu yere kendiliğinden yazılsın mı?"""
        return self._bool("auto_paste", True)

    @auto_paste.setter
    def auto_paste(self, value: bool) -> None:
        self._set("auto_paste", value)

    @property
    def use_prompt(self) -> bool:
        """Modele noktalama için örnek metin (ipucu) verilsin mi?"""
        return self._bool("use_prompt", True)

    @use_prompt.setter
    def use_prompt(self, value: bool) -> None:
        self._set("use_prompt", value)
