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
