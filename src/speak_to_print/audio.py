"""Mikrofondan kayıt (QtMultimedia).

Mikrofon yalnızca dinleme sırasında açılır (Bluetooth kulaklıkta ses kalitesi
bunun dışında düşmesin). Bekletme sırasında mikrofon açık kalır ama gelen ses
atılır; böylece devam edince mikrofonun yeniden açılmasını beklemek gerekmez.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtMultimedia import QAudioDevice, QAudioFormat, QAudioSource, QMediaDevices

from .config import SAMPLE_RATE, STOP_TAIL_MS


def is_monitor(device: QAudioDevice) -> bool:
    """Hoparlöre giden sesin kopyası olan 'monitor' kaynakları mikrofon değildir."""
    return bytes(device.id().data()).decode(errors="replace").endswith(".monitor")


def default_microphone() -> QAudioDevice | None:
    device = QMediaDevices.defaultAudioInput()
    return None if device.isNull() or is_monitor(device) else device


class Recorder(QObject):
    """Sistemin varsayılan mikrofonundan 16 kHz mono kayıt alır."""

    level = Signal(float)  # son ses paketinin tepe seviyesi, 0..1
    finished = Signal(object)  # kayıt bitti: float32 numpy dizisi (-1..1)
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._source: QAudioSource | None = None
        self._io = None
        self._chunks: list[bytes] = []
        self._paused = False
        self._stopping = False
        self.device_name = ""

    @property
    def is_recording(self) -> bool:
        return self._source is not None

    @property
    def seconds(self) -> float:
        """Şimdiye kadar kaydedilen (bekletilmemiş) sesin süresi."""
        return sum(len(chunk) for chunk in self._chunks) / 2 / SAMPLE_RATE

    def start(self) -> bool:
        if self._source is not None:
            return True
        device = default_microphone()
        if device is None:
            self.failed.emit("Mikrofon bulunamadı. KDE'nin ses ayarlarından bir giriş aygıtı seçin.")
            return False
        fmt = QAudioFormat()
        fmt.setSampleRate(SAMPLE_RATE)
        fmt.setChannelCount(1)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if not device.isFormatSupported(fmt):
            self.failed.emit(f"{device.description()} 16 kHz mono kaydı desteklemiyor.")
            return False
        self.device_name = device.description()
        self._chunks = []
        self._paused = False
        self._stopping = False
        self._source = QAudioSource(device, fmt, self)
        self._io = self._source.start()
        if self._io is None:
            self._cleanup()
            self.failed.emit(f"{self.device_name} açılamadı.")
            return False
        self._io.readyRead.connect(self._read)
        return True

    def set_paused(self, paused: bool) -> None:
        self._paused = paused
        if paused:
            self.level.emit(0.0)

    def stop(self) -> None:
        """Kaydı bitirir; kısa bir kuyruk süresinden sonra `finished` yayılır."""
        if self._source is None or self._stopping:
            return
        self._stopping = True
        # Bekletilmişken durdurulduysa kuyruk kaydetmeye gerek yok.
        QTimer.singleShot(0 if self._paused else STOP_TAIL_MS, self._finish)

    def cancel(self) -> None:
        """Kaydı atar; `finished` yayılmaz."""
        self._cleanup()

    def _read(self) -> None:
        if self._io is None:
            return
        data = self._io.readAll().data()
        if not data or self._paused:
            return
        self._chunks.append(bytes(data))
        samples = np.frombuffer(data, dtype=np.int16)
        if samples.size:
            self.level.emit(float(np.max(np.abs(samples.astype(np.int32)))) / 32768.0)

    def _finish(self) -> None:
        if self._source is None:
            return
        self._read()
        samples = np.frombuffer(b"".join(self._chunks), dtype=np.int16).astype(np.float32) / 32768.0
        self._cleanup()
        self.finished.emit(samples)

    def _cleanup(self) -> None:
        if self._source is not None:
            self._source.stop()
            self._source.deleteLater()
        self._source = None
        self._io = None
        self._chunks = []
        self._paused = False
        self._stopping = False
        self.level.emit(0.0)
