import sqlite3

from speak_to_print import history as history_module
from speak_to_print.history import History


def test_add_and_list_newest_first(tmp_path):
    h = History(tmp_path / "h.db")
    h.add("Bir.")
    h.add("İki, ığüşöç.")
    assert [e.text for e in h.recent()] == ["İki, ığüşöç.", "Bir."]


def test_blank_and_repeated_text_is_not_added(tmp_path):
    h = History(tmp_path / "h.db")
    assert h.add("   ") is None
    assert h.add("Aynı.") is not None
    assert h.add("Aynı.") is None and h.add(" Aynı. ") is None
    assert len(h.recent()) == 1


def test_entries_survive_reopen(tmp_path):
    h = History(tmp_path / "h.db")
    h.add("Kalıcı.")
    h.close()
    assert [e.text for e in History(tmp_path / "h.db").recent()] == ["Kalıcı."]


def test_delete_and_clear(tmp_path):
    h = History(tmp_path / "h.db")
    first = h.add("Bir.")
    h.add("İki.")
    h.delete(first.id)
    assert [e.text for e in h.recent()] == ["İki."]
    h.clear()
    assert h.recent() == []


def test_only_newest_entries_are_kept(tmp_path, monkeypatch):
    monkeypatch.setattr(history_module, "MAX_ENTRIES", 3)
    h = History(tmp_path / "h.db")
    for n in range(5):
        h.add(f"Metin {n}")
    assert [e.text for e in h.recent(10)] == ["Metin 4", "Metin 3", "Metin 2"]


def test_deleted_text_does_not_remain_in_the_file(tmp_path):
    h = History(tmp_path / "h.db")
    secret = h.add("Gizli dikte 4711.")
    assert secret is not None
    h.add("Kalan.")
    h.delete(secret.id)
    h.close()
    assert "Gizli dikte 4711.".encode() not in (tmp_path / "h.db").read_bytes()


def test_text_dropped_by_the_limit_does_not_remain_in_the_file(tmp_path, monkeypatch):
    monkeypatch.setattr(history_module, "MAX_ENTRIES", 3)
    h = History(tmp_path / "h.db")
    # Uzun bir dikte, ardından kısa olanlar: boşalan yerin hepsi yeniden kullanılmaz.
    h.add("Gizli uzun dikte 4711. " + "Devamı olan uzun bir cümle. " * 10)
    for n in range(4):
        h.add(f"Kısa {n}.")
    h.close()
    assert b"Gizli uzun dikte 4711." not in (tmp_path / "h.db").read_bytes()


def test_leftovers_of_earlier_deletes_are_removed_when_opened(tmp_path):
    # Bu düzeltmeden önce oluşmuş bir dosya: silinen metin dosyada kalmış.
    path = tmp_path / "h.db"
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE entries (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, text TEXT NOT NULL)")
    db.execute("INSERT INTO entries (created_at, text) VALUES ('2026-11-01T10:00:00', 'Eski gizli 4711.')")
    db.execute("INSERT INTO entries (created_at, text) VALUES ('2026-11-01T10:01:00', 'Kalan.')")
    db.execute("DELETE FROM entries WHERE text = 'Eski gizli 4711.'")
    db.commit()
    db.close()
    assert "Eski gizli 4711.".encode() in path.read_bytes()  # ön koşul: kalıntı gerçekten var

    History(path).close()
    assert "Eski gizli 4711.".encode() not in path.read_bytes()
    assert [e.text for e in History(path).recent()] == ["Kalan."]
