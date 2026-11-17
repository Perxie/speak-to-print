"""Testlerde gerçek mikrofon, model ve ayar dosyası yerine kullanılan sahte nesneler."""

from PySide6.QtCore import QObject, Signal


class FakeRecorder(QObject):
    level = Signal(float)
    finished = Signal(object)
    failed = Signal(str)
    notice = Signal(str)

    def __init__(self):
        super().__init__()
        self.calls = []
        self.start_ok = True
        self.seconds = 0.0
        self.device_name = "Sahte mikrofon"
        self.preferred_device_id = ""

    def start(self):
        self.calls.append("start")
        if not self.start_ok:
            self.failed.emit("Mikrofon bulunamadı.")
        return self.start_ok

    def set_paused(self, paused):
        self.calls.append(f"paused={paused}")

    def stop(self):
        self.calls.append("stop")

    def cancel(self):
        self.calls.append("cancel")


class FakeTranscriber(QObject):
    ready = Signal(float, str)
    load_failed = Signal(str)
    done = Signal(object)
    failed = Signal(str)
    status = Signal(str)

    def __init__(self):
        super().__init__()
        self.requests = []
        self.gpu_error = ""

    def shutdown(self, timeout_ms=0):
        return True

    def load(self):
        self.requests.append("load")

    def transcribe(self, samples, use_prompt, vocabulary):
        self.requests.append(("transcribe", len(samples), use_prompt))
        self.vocabulary = vocabulary


class FakeSettings:
    auto_paste = True
    use_prompt = True
    vocabulary: list = []
