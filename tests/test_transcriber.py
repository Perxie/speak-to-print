"""Model çıktısının işlenmesi: gerçek model yerine sabit metin döndüren sahte bir model kullanılır."""

import sys
import types
from types import SimpleNamespace

import numpy as np

from speak_to_print.config import MODEL_REVISION, SAMPLE_RATE
from speak_to_print.transcriber import _Worker


class FakeModel:
    def __init__(self, *texts):
        self.texts = texts

    def transcribe(self, samples, **kwargs):
        return (SimpleNamespace(text=text) for text in self.texts), None


def transcribe(*texts):
    worker = _Worker()
    worker._model = FakeModel(*texts)
    results = []
    worker.done.connect(results.append)
    worker.transcribe(np.zeros(SAMPLE_RATE, dtype=np.float32), False, [])
    return results[0]


def test_segments_are_joined_with_spaces():
    assert transcribe(" Merhaba.", " Nasılsın?").text == "Merhaba. Nasılsın?"


def test_line_break_from_the_model_is_not_typed_as_enter():
    # Terminal odaktayken satır sonu Enter gibi davranıp satırı çalıştırabilirdi.
    assert transcribe(" echo merhaba\n", "ls\r\nİkinci\tsatır").text == "echo merhaba ls İkinci satır"


def _fake_faster_whisper(monkeypatch, missing_locally=False):
    """`faster_whisper.download_model` yerine çağrıları kaydeden bir sahte koyar; ağa çıkılmaz."""
    calls = []

    def download_model(name, **kwargs):
        calls.append(kwargs)
        if missing_locally and kwargs.get("local_files_only"):
            raise FileNotFoundError("önbellekte yok")
        return "/sahte/model"

    module = types.ModuleType("faster_whisper")
    module.download_model = download_model
    monkeypatch.setitem(sys.modules, "faster_whisper", module)
    return calls


def test_model_is_looked_up_at_the_pinned_revision(monkeypatch):
    calls = _fake_faster_whisper(monkeypatch)
    assert _Worker()._model_path() == "/sahte/model"
    assert calls == [{"local_files_only": True, "revision": MODEL_REVISION}]


def test_missing_model_is_downloaded_at_the_pinned_revision(monkeypatch):
    calls = _fake_faster_whisper(monkeypatch, missing_locally=True)
    _Worker()._model_path()
    assert calls[-1] == {"revision": MODEL_REVISION}
