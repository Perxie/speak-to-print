"""Kullanıcı ayarları: ~/.config/speak-to-print/speak-to-print.conf (QSettings).

QSettings, Java'daki java.util.prefs.Preferences gibi: anahtar-değer saklar.
Her ayar bir `property`'dir (Java'daki getter/setter çifti); değeri değişince
`changed` sinyali yayılır.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QSettings, Signal

HOTKEY_MODES = ("toggle", "hold")  # bas başlat/bas bitir · basılı tut, konuş
OUTPUT_METHODS = ("auto", "clipboard")  # kwin-type (olmazsa pano) · her zaman pano


class Settings(QObject):
    changed = Signal()

    def __init__(self, parent: QObject | None = None, store: QSettings | None = None) -> None:
        super().__init__(parent)
        self._store = store or QSettings("speak-to-print", "speak-to-print")

    # ------------------------------------------------------------ okuma / yazma

    def _bool(self, key: str, default: bool) -> bool:
        value = self._store.value(key, default)
        return value if isinstance(value, bool) else str(value).lower() == "true"

    def _str(self, key: str, default: str) -> str:
        value = self._store.value(key, default)
        return default if value is None else str(value)

    def _set(self, key: str, value: bool | str, current: bool | str) -> None:
        if current != value:
            self._store.setValue(key, value)
            self._store.sync()
            self.changed.emit()

    # ------------------------------------------------------------ ayarlar

    @property
    def auto_paste(self) -> bool:
        """Çevrilen metin imlecin olduğu yere kendiliğinden yazılsın mı?"""
        return self._bool("auto_paste", True)

    @auto_paste.setter
    def auto_paste(self, value: bool) -> None:
        self._set("auto_paste", value, self.auto_paste)

    @property
    def use_prompt(self) -> bool:
        """Modele noktalama için örnek metin (ipucu) verilsin mi?"""
        return self._bool("use_prompt", True)

    @use_prompt.setter
    def use_prompt(self, value: bool) -> None:
        self._set("use_prompt", value, self.use_prompt)

    @property
    def keep_history(self) -> bool:
        """Dikte edilen metinler geçmişe kaydedilsin mi?"""
        return self._bool("keep_history", True)

    @keep_history.setter
    def keep_history(self, value: bool) -> None:
        self._set("keep_history", value, self.keep_history)

    @property
    def hotkey_mode(self) -> str:
        """"toggle": bas başlat, tekrar bas bitir. "hold": basılı tutarken dinle."""
        value = self._str("hotkey_mode", "toggle")
        return value if value in HOTKEY_MODES else "toggle"

    @hotkey_mode.setter
    def hotkey_mode(self, value: str) -> None:
        if value in HOTKEY_MODES:
            self._set("hotkey_mode", value, self.hotkey_mode)

    @property
    def output_method(self) -> str:
        """"auto": kwin-type, olmazsa pano. "clipboard": her zaman pano + Shift+Insert."""
        value = self._str("output_method", "auto")
        return value if value in OUTPUT_METHODS else "auto"

    @output_method.setter
    def output_method(self, value: str) -> None:
        if value in OUTPUT_METHODS:
            self._set("output_method", value, self.output_method)

    @property
    def microphone_id(self) -> str:
        """Seçili mikrofonun kimliği; boşsa sistemin varsayılan mikrofonu kullanılır."""
        return self._str("microphone_id", "")

    @microphone_id.setter
    def microphone_id(self, value: str) -> None:
        self._set("microphone_id", value, self.microphone_id)

    @property
    def vocabulary(self) -> list[str]:
        """Sözlük: modele önceden verilen terimler (her biri ayrı satırda saklanır)."""
        return [line.strip() for line in self._str("vocabulary", "").splitlines() if line.strip()]

    @vocabulary.setter
    def vocabulary(self, terms: list[str]) -> None:
        cleaned = "\n".join(term.strip() for term in terms if term.strip())
        self._set("vocabulary", cleaned, "\n".join(self.vocabulary))
