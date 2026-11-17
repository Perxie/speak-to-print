"""Model çıktısının işlenmesi: gerçek model yerine sabit metin döndüren sahte bir model kullanılır."""

from types import SimpleNamespace

import numpy as np

from speak_to_print.config import SAMPLE_RATE
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
