"""Metni etkin pencereye yazar: önce kwin-type, olmazsa pano + Shift+Insert."""

from __future__ import annotations

from . import OutputError, clipboard_paste, kwin_type


class TextWriter:
    def __init__(self) -> None:
        self._paster: clipboard_paste.ClipboardPaster | None = None

    def write(self, text: str) -> str:
        """Metni yazar ve kullanılan yöntemin adını döndürür. İkisi de olmazsa OutputError."""
        try:
            kwin_type.type_text(text)
            return "kwin-type"
        except OutputError as first_error:
            try:
                if self._paster is None:
                    self._paster = clipboard_paste.ClipboardPaster("shift+insert")
                self._paster.paste(text)
                return "pano"
            except OutputError as second_error:
                raise OutputError(f"kwin-type: {first_error}; pano: {second_error}") from second_error

    def close(self) -> None:
        if self._paster is not None:
            self._paster.close()
            self._paster = None
