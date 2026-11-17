"""Pano + yapıştırma tuşu yöntemi: gerçek pano ve sanal klavye yerine sahteleri kullanılır."""

import subprocess

import pytest
from evdev import ecodes as e

from speak_to_print.output import OutputError, clipboard_paste
from speak_to_print.output.clipboard_paste import ClipboardPaster

TEXT = "text/plain;charset=utf-8"
HINT = "x-kde-passwordManagerHint"  # parola yöneticilerinin ve `wl-copy --sensitive`'in koyduğu işaret


class FakeClipboard:
    """`wl-copy` ve `wl-paste` gibi davranır; iki seçim tutar: pano (False) ve seçim panosu (True)."""

    def __init__(self):
        self.selections: dict[bool, tuple[list[str], dict[str, bytes]] | None] = {False: None, True: None}
        self.copies = []  # her wl-copy çağrısı: (seçim panosu mu, veri, --sensitive var mı)
        self.fail_copy_at = None  # bu sıradaki wl-copy çağrısı hata verir

    def offer(self, data: bytes, primary=False, secret=False):
        types = [TEXT, "text/plain"]
        offers = dict.fromkeys(types, data)
        if secret:
            types.append(HINT)
            offers[HINT] = b"secret"
        self.selections[primary] = (types, offers)

    def text(self, primary=False):
        entry = self.selections[primary]
        return None if entry is None else entry[1].get(TEXT)

    def run(self, command, input=None, **kwargs):
        primary = "--primary" in command
        if command[0] == "wl-paste":
            entry = self.selections[primary]
            if entry is None:
                return subprocess.CompletedProcess(command, 1, b"", b"Nothing is copied\n")
            if "--list-types" in command:
                return subprocess.CompletedProcess(command, 0, "\n".join(entry[0]).encode() + b"\n", b"")
            mime = command[command.index("--type") + 1]
            return subprocess.CompletedProcess(command, 0 if mime in entry[1] else 1, entry[1].get(mime, b""), b"")
        if command[0] == "wl-copy":
            sensitive = "--sensitive" in command
            index = len(self.copies)
            self.copies.append((primary, input, sensitive))
            if index == self.fail_copy_at:
                return subprocess.CompletedProcess(command, 1)
            if "--clear" in command:
                self.selections[primary] = None
            else:
                mime = command[command.index("--type") + 1]
                types = [mime] + ([HINT] if sensitive else [])
                offers = {mime: input} | ({HINT: b"secret"} if sensitive else {})
                self.selections[primary] = (types, offers)
            return subprocess.CompletedProcess(command, 0)
        raise AssertionError(f"beklenmeyen komut: {command}")


class FakeKeyboard:
    """Sanal klavye: tuşa basıldığı anda panoda ne olduğunu ve basılı kalan tuşları kaydeder."""

    def __init__(self, clipboard):
        self.clipboard = clipboard
        self.writes = 0
        self.fail_on = set()  # bu sıradaki write çağrıları OSError verir
        self.held = set()
        self.pasted = []  # Insert'e basıldığı anda panodaki metin

    def write(self, event_type, code, value):
        index = self.writes
        self.writes += 1
        if index in self.fail_on:
            raise OSError(5, "Input/output error")
        if value:
            self.held.add(code)
        else:
            self.held.discard(code)
        if code == e.KEY_INSERT and value == 1:
            self.pasted.append(self.clipboard.text())

    def syn(self):
        pass

    def close(self):
        pass


@pytest.fixture
def board(monkeypatch):
    fake = FakeClipboard()
    monkeypatch.setattr(clipboard_paste.subprocess, "run", fake.run)
    monkeypatch.setattr(clipboard_paste.time, "sleep", lambda seconds: None)
    return fake


@pytest.fixture
def keyboard(monkeypatch, board):
    fake = FakeKeyboard(board)
    monkeypatch.setattr(clipboard_paste, "UInput", lambda *args, **kwargs: fake)
    return fake


def test_pastes_the_dictation(board, keyboard):
    ClipboardPaster().paste("Çığ düştü.")
    assert keyboard.pasted == ["Çığ düştü.".encode()]


def test_dictation_is_offered_only_with_the_password_manager_hint(board, keyboard):
    ClipboardPaster().paste("Gizli dikte.")
    assert [sensitive for _, data, sensitive in board.copies if data == "Gizli dikte.".encode()] == [True, True]


def test_previous_plain_text_comes_back_after_paste(board, keyboard):
    board.offer(b"eski metin")
    board.offer(b"eski secim", primary=True)
    ClipboardPaster().paste("Yeni.")
    assert (board.text(), board.text(primary=True)) == (b"eski metin", b"eski secim")


def test_password_from_password_manager_is_not_put_back(board, keyboard):
    # Yavaş bir uygulama panoyu geri yüklemeden sonra okursa parolayı yapıştırırdı.
    board.offer(b"hunter2", secret=True)
    ClipboardPaster().paste("Merhaba.")
    assert board.text() != b"hunter2"


def test_password_is_never_offered_without_the_hint(board, keyboard):
    # İşaretsiz sunulan parola Klipper geçmişine ve diske düşer.
    board.offer(b"hunter2", secret=True)
    ClipboardPaster().paste("Merhaba.")
    assert all(sensitive for _, data, sensitive in board.copies if data == b"hunter2")


def test_keyboard_error_is_reported_as_output_error(board, keyboard):
    keyboard.fail_on = {1}
    with pytest.raises(OutputError):
        ClipboardPaster().paste("Merhaba.")


def test_previous_clipboard_comes_back_when_the_keyboard_fails(board, keyboard):
    board.offer(b"eski metin")
    keyboard.fail_on = {1}
    with pytest.raises(OutputError):
        ClipboardPaster().paste("Merhaba.")
    assert board.text() == b"eski metin"


def test_no_key_stays_held_when_the_keyboard_fails(board, keyboard):
    keyboard.fail_on = {1}  # Shift basıldı, Insert'e basılamadı
    with pytest.raises(OutputError):
        ClipboardPaster().paste("Merhaba.")
    assert keyboard.held == set()


def test_previous_clipboard_comes_back_when_setting_the_primary_selection_fails(board, keyboard):
    board.offer(b"eski metin")
    board.fail_copy_at = 1  # 0: pano (olur), 1: seçim panosu (hata)
    with pytest.raises(OutputError):
        ClipboardPaster().paste("Merhaba.")
    assert board.text() == b"eski metin"


def test_failed_restore_does_not_turn_a_done_paste_into_an_error(board, keyboard):
    board.offer(b"eski metin")
    board.fail_copy_at = 2  # 0 ve 1: dikte, 2: eski panoyu geri yükleme
    ClipboardPaster().paste("Merhaba.")
    assert keyboard.pasted == [b"Merhaba."]


def test_unresponsive_clipboard_tool_is_reported_as_output_error(board, keyboard, monkeypatch):
    def hang(command, **kwargs):
        raise subprocess.TimeoutExpired(command, 5)

    monkeypatch.setattr(clipboard_paste.subprocess, "run", hang)
    with pytest.raises(OutputError):
        ClipboardPaster().paste("Merhaba.")


def test_copy_without_the_clipboard_tool_is_reported_as_output_error(monkeypatch):
    def missing(command, **kwargs):
        raise FileNotFoundError(2, "No such file or directory", command[0])

    monkeypatch.setattr(clipboard_paste.subprocess, "run", missing)
    with pytest.raises(OutputError):
        clipboard_paste.copy_text("Merhaba.")


def test_paste_without_the_clipboard_tools_is_reported_as_output_error(board, keyboard, monkeypatch):
    def missing(command, **kwargs):
        raise FileNotFoundError(2, "No such file or directory", command[0])

    monkeypatch.setattr(clipboard_paste.subprocess, "run", missing)
    with pytest.raises(OutputError):
        ClipboardPaster().paste("Merhaba.")
