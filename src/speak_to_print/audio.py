"""Mikrofondan kayıt (QtMultimedia).

Mikrofon yalnızca dinleme sırasında açılır (Bluetooth kulaklıkta ses kalitesi
bunun dışında düşmesin). Bekletme sırasında mikrofon açık kalır ama gelen ses
atılır; böylece devam edince mikrofonun yeniden açılmasını beklemek gerekmez.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtMultimedia import QAudioDevice, QAudioFormat, QAudioSource, QMediaDevices

from .config import MAX_RECORDING_SECONDS, SAMPLE_RATE, STOP_TAIL_MS


def is_monitor(device: QAudioDevice) -> bool:
    """Hoparlöre giden sesin kopyası olan 'monitor' kaynakları mikrofon değildir."""
    return device_id(device).endswith(".monitor")


def device_id(device: QAudioDevice) -> str:
    return bytes(device.id().data()).decode(errors="replace")


def default_microphone() -> QAudioDevice | None:
    device = QMediaDevices.defaultAudioInput()
    return None if device.isNull() or is_monitor(device) else device


def microphones() -> list[QAudioDevice]:
    """Bağlı mikrofonlar (monitor kaynakları hariç)."""
    return [device for device in QMediaDevices.audioInputs() if not is_monitor(device)]


def choose_microphone(preferred_id: str, available: dict[str, object], default: object | None) -> tuple[object | None, bool]:
    """Kullanılacak mikrofonu seçer: (aygıt, seçili olan bulunamadığı için varsayılana mı düşüldü).

    `preferred_id` boşsa sistem varsayılanı kullanılır.
    """
    if not preferred_id:
        return default, False
    if preferred_id in available:
        return available[preferred_id], False
    return default, True


class Recorder(QObject):
    """Sistemin varsayılan mikrofonundan 16 kHz mono kayıt alır."""

    level = Signal(float)  # son ses paketinin tepe seviyesi, 0..1
    notice = Signal(str)  # kullanıcıya gösterilecek kısa bilgi
    finished = Signal(object)  # kayıt bitti: float32 numpy dizisi (-1..1)
    failed = Signal(str)
    limit_reached = Signal()  # kayıt MAX_RECORDING_SECONDS'a ulaştı (bir kez); bitirmek denetleyicinin işi

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._source: QAudioSource | None = None
        self._io = None
        self._chunks: list[bytes] = []
        self._bytes = 0  # kaydedilen sesin toplam boyu; süre göstergesi her seferinde toplamasın
        self._paused = False
        self._stopping = False
        self.device_name = ""
        self.preferred_device_id = ""  # boş: sistem varsayılanı (ayarlardan gelir)
        self._device_id = ""  # kayıt alınan aygıtın kimliği
        # Aygıt takılıp çıkarılınca haber verir. Mikrofon çıkarılınca ses sistemi kaydı sessizce başka bir
        # aygıta taşıyabiliyor ve hata bildirmiyor; bu yüzden listeyi kendimiz izliyoruz.
        self._devices = QMediaDevices(self)
        self._devices.audioInputsChanged.connect(self._on_inputs_changed)

    @property
    def seconds(self) -> float:
        """Şimdiye kadar kaydedilen (bekletilmemiş) sesin süresi."""
        return self._bytes / 2 / SAMPLE_RATE  # 16 bit = 2 bayt/örnek

    def start(self) -> bool:
        if self._source is not None:
            return True
        device, fell_back = choose_microphone(
            self.preferred_device_id, {device_id(mic): mic for mic in microphones()}, default_microphone())
        if fell_back and device is not None:
            self.notice.emit("Seçili mikrofon bağlı değil; sistemin varsayılan mikrofonu kullanılıyor.")
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
        self._device_id = device_id(device)
        self._chunks = []
        self._bytes = 0
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

    def _on_inputs_changed(self) -> None:
        """Kayıt alınan mikrofon listeden kaybolduysa (çıkarıldıysa) kaydı bırakır ve haber verir."""
        if self._source is None or self._stopping:
            return
        if self._device_id not in {device_id(mic) for mic in microphones()}:
            name = self.device_name
            self._cleanup()
            self.failed.emit(f"Mikrofon kayboldu ({name}); dinleme durduruldu.")

    def _read(self) -> None:
        if self._io is None:
            return
        data = self._io.readAll().data()
        if not data or self._paused:
            return
        self._chunks.append(bytes(data))
        reached_before = self.seconds >= MAX_RECORDING_SECONDS
        self._bytes += len(data)
        if not reached_before and self.seconds >= MAX_RECORDING_SECONDS:
            self.limit_reached.emit()
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
        self._bytes = 0
        self._paused = False
        self._stopping = False
        self.level.emit(0.0)
