import pytest
from PySide6.QtCore import QByteArray

from speak_to_print import audio
from speak_to_print.audio import Recorder, choose_microphone
from speak_to_print.config import SAMPLE_RATE

MICS = {"usb": "USB mikrofon", "bt": "Kulaklık"}


def test_empty_preference_uses_system_default():
    assert choose_microphone("", MICS, "Kulaklık") == ("Kulaklık", False)


def test_preferred_microphone_is_used_when_connected():
    assert choose_microphone("usb", MICS, "Kulaklık") == ("USB mikrofon", False)


def test_missing_preferred_microphone_falls_back_to_default():
    assert choose_microphone("yok", MICS, "Kulaklık") == ("Kulaklık", True)


def test_no_microphone_at_all():
    assert choose_microphone("", {}, None) == (None, False)
    assert choose_microphone("usb", {}, None) == (None, True)


class FakeStream:
    """Mikrofon akışı yerine: `pending` içindeki ham ses bir sonraki okumada gelir."""

    def __init__(self):
        self.pending = b""

    def readAll(self):
        data, self.pending = self.pending, b""
        return QByteArray(data)


@pytest.fixture
def recorder(monkeypatch):
    monkeypatch.setattr(audio, "MAX_RECORDING_SECONDS", 1)
    r = Recorder()
    r._io = FakeStream()
    return r


def feed(r, seconds):
    r._io.pending = bytes(int(seconds * SAMPLE_RATE) * 2)  # 16 bit = 2 bayt/örnek
    r._read()


def test_recorded_seconds_are_counted(recorder):
    feed(recorder, 0.25)
    feed(recorder, 0.5)
    assert recorder.seconds == 0.75


def test_paused_audio_is_not_counted(recorder):
    recorder.set_paused(True)
    feed(recorder, 2)
    assert recorder.seconds == 0


def test_limit_is_reported_once_when_reached(recorder):
    hits = []
    recorder.limit_reached.connect(lambda: hits.append(recorder.seconds))
    feed(recorder, 0.6)
    assert hits == []
    feed(recorder, 0.6)
    feed(recorder, 0.6)
    assert hits == [1.2]


class FakeSource:
    def stop(self):
        pass

    def deleteLater(self):
        pass


def test_finished_recording_is_converted_to_floats_between_minus_one_and_one(recorder):
    import numpy as np

    recorder._source = FakeSource()  # kayıt sürüyormuş gibi
    recorder._io.pending = np.array([-32768, -16384, 0, 16384], dtype=np.int16).tobytes()
    results = []
    recorder.finished.connect(results.append)
    recorder._finish()
    assert results[0].dtype == np.float32 and results[0].tolist() == [-1.0, -0.5, 0.0, 0.5]
