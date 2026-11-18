"""Kişisel veri klasörleri (geçmiş, günlük, ayarlar) yalnızca bu kullanıcıya açık olmalı."""

import os
import stat
from pathlib import Path

from speak_to_print import app as app_module
from speak_to_print.history import default_path as history_path


def mode(path):
    return stat.S_IMODE(os.stat(path, follow_symlinks=False).st_mode)


def test_new_folder_is_only_for_me(tmp_path):
    folder = app_module._private_dir(tmp_path / "a" / "speak-to-print")
    assert mode(folder) == 0o700


def test_existing_open_folder_and_its_files_are_closed(tmp_path):
    folder = tmp_path / "speak-to-print"
    folder.mkdir(mode=0o755)
    (folder / "history.db").write_text("")
    os.chmod(folder / "history.db", 0o644)
    app_module._private_dir(folder)
    assert (mode(folder), mode(folder / "history.db")) == (0o700, 0o600)


def test_a_link_inside_does_not_change_the_file_it_points_to(tmp_path):
    outside = tmp_path / "baska-bir-dosya"
    outside.write_text("")
    os.chmod(outside, 0o644)
    folder = tmp_path / "speak-to-print"
    folder.mkdir()
    (folder / "baglanti").symlink_to(outside)
    app_module._private_dir(folder)
    assert mode(outside) == 0o644


def test_personal_data_folders_are_the_ones_the_app_writes_to():
    folders = app_module._personal_data_dirs()
    assert app_module.log_file_path().parent in folders
    assert history_path().parent in folders
    assert any(folder.name == "speak-to-print" and folder.parent.name.endswith("config") for folder in folders)


def test_xdg_folders_follow_the_environment_with_a_fallback(monkeypatch, tmp_path):
    from speak_to_print.config import xdg_home

    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert xdg_home("XDG_DATA_HOME", ".local/share") == tmp_path
    monkeypatch.delenv("XDG_DATA_HOME")
    assert xdg_home("XDG_DATA_HOME", ".local/share") == Path.home() / ".local" / "share"


def test_uninstall_shows_where_the_history_really_is(monkeypatch, tmp_path, capsys):
    # Kaldırma çıktısı ayar ve geçmiş klasörünü sabit ~/.config ve ~/.local/share yollarıyla yazıyordu.
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "veri"))
    monkeypatch.setattr(app_module.desktop_entry, "uninstall", lambda: False)  # gerçek kayıtlar silinmesin
    monkeypatch.setattr(app_module.kwin_rules, "remove_popup_rule", lambda: False)
    monkeypatch.setattr(app_module.kwin_rules, "remove_editor_rule", lambda: False)
    app_module._uninstall()
    assert str(tmp_path / "veri" / "speak-to-print") in capsys.readouterr().out
