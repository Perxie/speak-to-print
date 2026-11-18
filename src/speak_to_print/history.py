"""Çeviri geçmişi: son dikteler SQLite veritabanında saklanır.

Dosya: ~/.local/share/speak-to-print/history.db (proje dışı; bkz.
docs/proje-disi-dosyalar.md). Metinler şifrelenmeden, düz hâlde durur ve
hiçbir yere gönderilmez. En yeni `MAX_ENTRIES` kayıt tutulur. Silinen
kayıtların dosyadaki yerine sıfır yazılır (`secure_delete`); "Sil" ile ya da
sınır yüzünden atılan bir metin dosyada okunabilir kalmaz.

SQLite, Python'la birlikte gelen dosya tabanlı bir veritabanıdır; ayrı bir
sunucu gerekmez (Java'da H2 ya da SQLite JDBC kullanmak gibi).
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

MAX_ENTRIES = 30  # kullanıcı seçti (önceden 200); fazlası bir sonraki eklemede silinir

# Dosya biçiminin sürümü, dosyanın içinde `PRAGMA user_version` olarak durur.
# 1: silinen metinler sıfırlanıyor ve bundan önce silinenlerin kalıntıları bir
# kez temizlendi.
FILE_VERSION = 1


@dataclass(frozen=True)
class Entry:
    id: int
    created_at: datetime
    text: str


def default_path() -> Path:
    data_home = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return data_home / "speak-to-print" / "history.db"


class History:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path)
        # Bu ayar her bağlantıda yeniden verilir; dosyaya kaydedilmez.
        self._db.execute("PRAGMA secure_delete = ON")
        self._db.execute("CREATE TABLE IF NOT EXISTS entries ("
                         "id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, text TEXT NOT NULL)")
        self._db.commit()
        if self._db.execute("PRAGMA user_version").fetchone()[0] < FILE_VERSION:
            # Bu sürümden önce silinmiş metinler dosyada kalmış olabilir: dosyayı bir kez baştan yaz.
            self._db.execute("VACUUM")
            self._db.execute(f"PRAGMA user_version = {FILE_VERSION}")

    def add(self, text: str) -> Entry | None:
        """Metni geçmişe ekler. Boşsa ya da en son kayıtla aynıysa eklemez ve None döner."""
        text = text.strip()
        if not text:
            return None
        latest = self.recent(1)
        if latest and latest[0].text == text:
            return None
        now = datetime.now().replace(microsecond=0)
        cursor = self._db.execute("INSERT INTO entries (created_at, text) VALUES (?, ?)", (now.isoformat(), text))
        # En yeni MAX_ENTRIES kayıt dışındakileri sil.
        self._db.execute("DELETE FROM entries WHERE id NOT IN (SELECT id FROM entries ORDER BY id DESC LIMIT ?)",
                         (MAX_ENTRIES,))
        self._db.commit()
        assert cursor.lastrowid is not None
        return Entry(cursor.lastrowid, now, text)

    def recent(self, limit: int = MAX_ENTRIES) -> list[Entry]:
        """En yeniden eskiye doğru kayıtlar."""
        rows = self._db.execute("SELECT id, created_at, text FROM entries ORDER BY id DESC LIMIT ?", (limit,))
        return [Entry(row[0], datetime.fromisoformat(row[1]), row[2]) for row in rows]

    def delete(self, entry_id: int) -> None:
        self._db.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        self._db.commit()

    def clear(self) -> None:
        self._db.execute("DELETE FROM entries")
        self._db.commit()
        self._db.execute("VACUUM")  # silinen metinler dosyada kalmasın

    def close(self) -> None:
        self._db.close()
