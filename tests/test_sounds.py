"""Başlama/bitiş sesleri: dosyaların yazıldığı klasör. Ses çalınmaz."""

import os
import stat
import tempfile

import pytest
from PySide6.QtCore import QStandardPaths

from speak_to_print import sounds as sounds_module
from speak_to_print.sounds import Sounds


class NoRuntimeDir:
    """Qt'nin oturum klasörünü bulamadığı durum."""

    StandardLocation = QStandardPaths.StandardLocation

    @staticmethod
    def writableLocation(location):
        return ""


@pytest.fixture
def runtime_dir(monkeypatch, tmp_path):
    folder = tmp_path / "run"
    folder.mkdir(mode=0o700)
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(folder))
    return folder


def test_sound_files_are_written_in_the_runtime_dir(runtime_dir):
    s = Sounds(enabled=lambda: True)
    assert {path.parent for path in s._files.values()} == {runtime_dir / "speak-to-print"}


def test_without_a_runtime_dir_sounds_go_to_a_private_new_folder_not_a_shared_one(monkeypatch, tmp_path):
    # /tmp gibi herkesin yazabildiği bir yerde sabit adlı klasöre başka bir hesap önceden
    # bir sembolik bağ koyup kullanıcının bir dosyasının üzerine yazdırabilirdi.
    monkeypatch.setattr(sounds_module, "QStandardPaths", NoRuntimeDir)
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    s = Sounds(enabled=lambda: True)
    folder = next(iter(s._files.values())).parent
    assert folder.parent == tmp_path and folder.name != "speak-to-print"
    assert stat.S_IMODE(os.stat(folder).st_mode) == 0o700


def test_if_no_folder_can_be_made_sounds_are_off_instead_of_crashing(monkeypatch):
    def fail(**kwargs):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(sounds_module, "QStandardPaths", NoRuntimeDir)
    monkeypatch.setattr(tempfile, "mkdtemp", fail)
    assert not Sounds(enabled=lambda: True).available
