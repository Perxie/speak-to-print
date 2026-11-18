"""Model çıktısının işlenmesi: gerçek model yerine sabit metin döndüren sahte bir model kullanılır."""

import sys
import time
import types
from types import SimpleNamespace

import numpy as np
import pytest
from PySide6.QtCore import QCoreApplication

from speak_to_print.config import MODEL_REVISION, SAMPLE_RATE
from speak_to_print import transcriber as transcriber_module
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


class LoadingWorld:
    """`_Worker.load` için sahte faster-whisper: olayları sırayla `events`'e yazar; ekran kartı ve ağ kullanılmaz."""

    def __init__(self, monkeypatch, gpu_works=True, warm_up_fails=False):
        self.events = []
        world = self

        class WhisperModel:
            def __init__(self, path, device, compute_type):
                if device == "cuda" and not gpu_works:
                    raise RuntimeError("CUDA yok")
                world.events.append(("yüklendi", device))

            def transcribe(self, samples, **kwargs):
                world.events.append(("çeviri", kwargs.get("vad_filter")))
                if warm_up_fails:
                    raise RuntimeError("ısınma hatası")
                return (SimpleNamespace(text=" Altyazı M.K.") for _ in range(1)), None

        main = types.ModuleType("faster_whisper")
        main.WhisperModel = WhisperModel
        main.download_model = lambda name, **kwargs: "/sahte/model"
        vad = types.ModuleType("faster_whisper.vad")
        vad.get_vad_model = lambda: world.events.append(("vad",))
        monkeypatch.setitem(sys.modules, "faster_whisper", main)
        monkeypatch.setitem(sys.modules, "faster_whisper.vad", vad)
        monkeypatch.setattr(transcriber_module, "preload_cuda_libraries", lambda: None)

        self.worker = _Worker()
        self.worker.ready.connect(lambda seconds, device: self.events.append(("hazır", device)))
        self.worker.done.connect(lambda transcript: self.events.append(("sonuç", transcript.text)))
        self.worker.failed.connect(lambda message: self.events.append(("hata", message)))
        self.worker.load_failed.connect(lambda message: self.events.append(("yükleme hatası", message)))


def test_model_is_warmed_up_once_after_loading_on_the_gpu(monkeypatch):
    world = LoadingWorld(monkeypatch)
    world.worker.load()
    assert world.events.count(("vad",)) == 1
    assert [e for e in world.events if e[0] == "çeviri"] == [("çeviri", False)]


def test_warm_up_comes_after_ready_so_startup_is_not_delayed(monkeypatch):
    world = LoadingWorld(monkeypatch)
    world.worker.load()
    names = [e[0] for e in world.events]
    assert names.index("hazır") < names.index("çeviri")


def test_warm_up_output_goes_nowhere(monkeypatch, caplog):
    world = LoadingWorld(monkeypatch)
    caplog.set_level("DEBUG")
    world.worker.load()
    assert not [e for e in world.events if e[0] in ("sonuç", "hata")]
    assert "Altyazı" not in caplog.text


def test_without_a_usable_gpu_the_model_is_not_loaded_at_all(monkeypatch):
    # Kullanıcı kararı (18 Kasım): yalnızca ekran kartı; işlemci yedeği yok.
    world = LoadingWorld(monkeypatch, gpu_works=False)
    world.worker.load()
    failures = [message for name, *rest in world.events if name == "yükleme hatası" for message in rest]
    assert failures and "Ekran kartı" in failures[0]
    assert not [e for e in world.events if e[0] in ("hazır", "yüklendi", "çeviri", "vad")]


def test_failed_warm_up_leaves_the_model_usable(monkeypatch):
    world = LoadingWorld(monkeypatch, warm_up_fails=True)
    world.worker.load()
    assert ("hazır", "cuda") in world.events
    assert not [e for e in world.events if e[0] == "yükleme hatası"]
    assert world.worker._model is not None


def wait_until(condition, seconds=3.0):
    """Arka plan iş parçacığından gelen kuyruklu sinyaller teslim edilsin diye olay döngüsünü döndürür."""
    deadline = time.monotonic() + seconds
    while not condition() and time.monotonic() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.005)
    return condition()


@pytest.fixture
def facade(monkeypatch):
    """Gerçek Transcriber ve iş parçacığı; yalnızca model yüklemesi sahte (anında biter, kaç kez çağrıldığını sayar)."""
    state = SimpleNamespace(loads=0, fail=False, ready=[], failed=[])

    def fake_load(self):
        state.loads += 1
        if state.fail:
            self.load_failed.emit("Model yüklenemedi.")
        else:
            self.ready.emit(0.1, "cuda")

    monkeypatch.setattr(transcriber_module._Worker, "load", fake_load)
    t = transcriber_module.Transcriber()
    t.ready.connect(lambda seconds, device: state.ready.append(device))
    t.load_failed.connect(state.failed.append)
    state.t = t
    yield state
    t.shutdown()


def test_model_is_loaded_once_even_if_loading_is_requested_twice(facade):
    # Açılışta yükleme erken başlatılıyor; Controller.start() da yüklemeyi istiyor. Model iki kez yüklenmemeli.
    facade.t.load()
    facade.t.load()
    assert wait_until(lambda: facade.ready)
    wait_until(lambda: False, seconds=0.1)
    assert facade.loads == 1


def test_asking_to_load_after_the_model_is_ready_reports_ready_again(facade):
    # "Hazır" haberi dinleyiciler bağlanmadan teslim edilmiş olsa bile, yüklemeyi isteyen haberi alır.
    facade.t.load()
    assert wait_until(lambda: facade.ready)
    facade.t.load()
    assert wait_until(lambda: len(facade.ready) == 2)
    assert facade.loads == 1


def test_asking_to_load_after_a_failed_load_reports_the_failure_again(facade):
    facade.fail = True
    facade.t.load()
    assert wait_until(lambda: facade.failed)
    facade.t.load()
    assert wait_until(lambda: len(facade.failed) == 2)
    assert facade.loads == 1
