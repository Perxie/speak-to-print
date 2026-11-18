"""kwin-type ile yazma: metin UTF-8 olarak KWin'e gönderilir.

Klavye düzeninden bağımsızdır ve panoya dokunmaz. `kwin-type` ayrı bir
programdır (https://git.zx2c4.com/kwin-type), KWin 6.8+ ister ve PATH'te
olmalıdır; bkz. docs/proje-disi-dosyalar.md.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from . import OutputError

PROGRAM = "kwin-type"


def _executable() -> str | None:
    """Programın tam yolu. PATH'te yoksa kurulduğu varsayılan yere de bakar."""
    found = shutil.which(PROGRAM)
    if found:
        return found
    fallback = Path.home() / ".local" / "bin" / PROGRAM
    return str(fallback) if fallback.exists() else None


def type_text(text: str, timeout: float = 15.0) -> None:
    """Metni o an etkin olan pencereye yazar."""
    if not text:
        return
    if "\0" in text:
        raise OutputError("Metin NUL karakteri içeremez.")
    executable = _executable()
    if executable is None:
        raise OutputError(f"{PROGRAM} bulunamadı.")
    try:
        result = subprocess.run([executable], input=text.encode("utf-8"), capture_output=True,
                                timeout=timeout, check=False)
    except FileNotFoundError as error:
        raise OutputError(f"{PROGRAM} bulunamadı.") from error
    except subprocess.TimeoutExpired as error:
        raise OutputError(f"{PROGRAM} {timeout:.0f} saniyede bitmedi.") from error
    if result.returncode != 0:
        raise OutputError(f"{PROGRAM} hata verdi: {result.stderr.decode(errors='replace').strip()}")
