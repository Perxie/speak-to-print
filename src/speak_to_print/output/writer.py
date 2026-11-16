"""Metni etkin pencereye yazar: önce kwin-type, olmazsa pano + Shift+Insert."""

from __future__ import annotations

from collections.abc import Callable

from . import OutputError, clipboard_paste, kwin_type


class TextWriter:
    """`method`, kullanıcının seçtiği yöntemi döndüren işlevdir: "auto" ya da "clipboard"."""

    def __init__(self, method: Callable[[], str] = lambda: "auto") -> None:
        self._method = method
        self._paster: clipboard_paste.ClipboardPaster | None = None

    def _paste(self, text: str) -> None:
        if self._paster is None:
            self._paster = clipboard_paste.ClipboardPaster("shift+insert")
        self._paster.paste(text)

    def write(self, text: str) -> str:
        """Metni yazar ve kullanılan yöntemin adını döndürür. Yazılamazsa OutputError."""
        if self._method() == "clipboard":
            self._paste(text)
            return "pano-seçili"
        try:
            kwin_type.type_text(text)
            return "kwin-type"
        except OutputError as first_error:
            try:
                self._paste(text)
                return "pano"
            except OutputError as second_error:
                raise OutputError(f"kwin-type: {first_error}; pano: {second_error}") from second_error

    def close(self) -> None:
        if self._paster is not None:
            self._paster.close()
            self._paster = None
