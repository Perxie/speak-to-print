"""Tek kopya denetimi: ikinci kopya, birincinin soketine bağlanıp onu öne getirir.

Soket gerçek oturum klasörü yerine her testin kendi geçici klasöründe açılır.
"""

import os
import tempfile
from pathlib import Path

import pytest
from PySide6.QtCore import QStandardPaths
from PySide6.QtNetwork import QLocalServer

from speak_to_print import app as app_module
from speak_to_print.desktop_entry import APP_ID


@pytest.fixture
def runtime_dir(monkeypatch):
    # Kısa bir yol: Unix soketinin tam yolu 108 karakteri geçemez.
    with tempfile.TemporaryDirectory(prefix="stp-") as directory:
        os.chmod(directory, 0o700)
        monkeypatch.setenv("XDG_RUNTIME_DIR", directory)
        yield Path(directory)


@pytest.fixture
def server():
    s = QLocalServer()
    yield s
    s.close()


def socket_path() -> str:
    path = app_module._instance_socket_path()
    assert path is not None
    return path


class NoRuntimeDir:
    """Qt'nin oturum klasörünü bulamadığı durum."""

    StandardLocation = QStandardPaths.StandardLocation

    @staticmethod
    def writableLocation(location):
        return ""


def test_socket_is_in_the_users_runtime_dir_not_in_tmp(runtime_dir):
    assert app_module._instance_socket_path() == str(runtime_dir / APP_ID)


def test_second_instance_reaches_the_first(runtime_dir, server):
    path = app_module._instance_socket_path()
    assert app_module._listen_for_instances(server, path)
    assert app_module._already_running(path)


def test_nothing_is_running_when_nobody_listens(runtime_dir):
    assert not app_module._already_running(app_module._instance_socket_path())


def test_only_my_account_can_reach_the_socket(runtime_dir, server):
    path = socket_path()
    app_module._listen_for_instances(server, path)
    assert os.stat(path).st_mode & 0o077 == 0


def test_file_left_from_a_crash_does_not_block_listening(runtime_dir, server):
    path = socket_path()
    Path(path).write_text("")
    assert app_module._listen_for_instances(server, path)


def test_failure_to_listen_is_logged(runtime_dir, server, caplog):
    assert not app_module._listen_for_instances(server, str(runtime_dir / "yok" / APP_ID))
    assert "Tek kopya soketi açılamadı" in caplog.text


def test_without_a_runtime_dir_the_check_is_skipped_and_logged(monkeypatch, server, caplog):
    monkeypatch.setattr(app_module, "QStandardPaths", NoRuntimeDir)
    path = app_module._instance_socket_path()
    assert path is None
    assert not app_module._already_running(path)
    assert not app_module._listen_for_instances(server, path)
    assert "tek kopya denetimi kapalı" in caplog.text
