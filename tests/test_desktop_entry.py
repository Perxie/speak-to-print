from speak_to_print import desktop_entry


def test_install_writes_entry_and_theme_icon(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setattr(desktop_entry, "_refresh_menu", lambda: None)
    assert desktop_entry.ensure(["/bin/uygulama"]) is True
    lines = desktop_entry.desktop_file_path().read_text(encoding="utf-8").splitlines()
    assert f"Icon={desktop_entry.APP_ID}" in lines and "Exec=/bin/uygulama" in lines
    assert desktop_entry.theme_icon_path().read_bytes() == desktop_entry.ICON_PATH.read_bytes()
    assert desktop_entry.ensure(["/bin/uygulama"]) is False  # değişiklik yoksa yeniden yazmaz


def test_missing_icon_or_changed_command_is_rewritten(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setattr(desktop_entry, "_refresh_menu", lambda: None)
    desktop_entry.ensure(["/bin/uygulama"])
    desktop_entry.theme_icon_path().unlink()
    assert desktop_entry.ensure(["/bin/uygulama"]) is True and desktop_entry.theme_icon_path().exists()
    assert desktop_entry.ensure(["/bin/baska"]) is True


def test_uninstall_removes_entry_and_icon(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setattr(desktop_entry, "_refresh_menu", lambda: None)
    desktop_entry.ensure(["/bin/uygulama"])
    assert desktop_entry.uninstall() is True
    assert not desktop_entry.desktop_file_path().exists() and not desktop_entry.theme_icon_path().exists()
    assert desktop_entry.uninstall() is False
