"""Dinleme başlarken ve biterken çalınan kısa sesler.

Ses dosyaları uygulamayla birlikte gelmez; açılışta üretilip geçici çalışma
klasörüne (/run/user/<kimlik>/speak-to-print) yazılır. Bu klasör bellekte
tutulur ve oturum kapanınca kendiliğinden silinir.

Sesler PipeWire'ın `pw-play` aracıyla çalınır, Qt'nin QSoundEffect'iyle değil:
Qt bu sesleri "bildirim sesi" (media.role=event) olarak işaretliyor ve
kullanıcı KDE'de bildirim seslerini kapattıysa hiç duyulmuyorlar. `pw-play`
her çalışta sistemin o anki varsayılan çıkış aygıtını kullanır.

Her sesin başında kısa bir sessizlik vardır: bir süredir ses çalmayan aygıt
(özellikle Bluetooth) uyanırken sesin ilk anını yutabilir.
"""

from __future__ import annotations

import shutil
import subprocess
import wave
from collections.abc import Callable
from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, QStandardPaths

RATE = 44_100
LEAD_IN_SECONDS = 0.25  # aygıtın uyanması için baştaki sessizlik
NOTE_SECONDS = 0.11
PLAYER = "pw-play"


TONES = {"start": (660.0, 880.0), "stop": (880.0, 660.0)}  # yükselen / alçalan


def _tone(frequencies: tuple[float, ...], volume: int = 50) -> np.ndarray:
    """Baştaki sessizlik ve art arda çalınan notalar; tıkırtı olmasın diye notaların başı ve sonu yumuşatılır.

    Ses yüksekliği dosyanın içine işlenir (0–100). Kulağın algısına uysun diye karesel ölçek
    kullanılır: sürgünün ortası, en yüksek sesin dörtte biri kadar genliktir.
    """
    parts = [np.zeros(int(RATE * LEAD_IN_SECONDS))]
    for frequency in frequencies:
        t = np.arange(int(RATE * NOTE_SECONDS)) / RATE
        envelope = np.minimum(1.0, np.minimum(t, NOTE_SECONDS - t) / 0.012)
        parts.append(np.sin(2 * np.pi * frequency * t) * envelope)
    amplitude = 0.9 * (max(0, min(100, volume)) / 100) ** 2
    return (np.concatenate(parts) * amplitude * 32767).astype(np.int16)


def _write(path: Path, samples: np.ndarray) -> None:
    with wave.open(str(path), "wb") as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(RATE)
        file.writeframes(samples.tobytes())


class Sounds(QObject):
    """`enabled`: ses açık mı; `volume`: 0–100 arası ses yüksekliği (ayarlardan okunur)."""

    def __init__(self, enabled: Callable[[], bool], volume: Callable[[], int] = lambda: 50,
                 parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._enabled = enabled
        self._volume = volume
        self._files: dict[str, Path] = {}
        self._written_volume = -1
        self._player = shutil.which(PLAYER)
        runtime = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.RuntimeLocation)
        self._folder = Path(runtime or "/tmp") / "speak-to-print"
        self._write_files(self._volume())

    def _write_files(self, volume: int) -> None:
        """Ses dosyalarını verilen yükseklikte (yeniden) üretir."""
        try:
            self._folder.mkdir(parents=True, exist_ok=True)
            for name, frequencies in TONES.items():
                path = self._folder / f"{name}.wav"
                _write(path, _tone(frequencies, volume))
                self._files[name] = path
            self._written_volume = volume
        except OSError:
            self._files = {}  # ses dosyası yazılamazsa uygulama sessizce devam eder

    @property
    def available(self) -> bool:
        return self._player is not None and bool(self._files)

    def play(self, name: str, force: bool = False) -> None:
        """Sesi çalar ve beklemeden döner. `force`: ayar kapalı olsa da çal ("Sesi dene" düğmesi için)."""
        if self._player is None or not (force or self._enabled()):
            return
        volume = max(0, min(100, self._volume()))
        if volume != self._written_volume:
            self._write_files(volume)
        path = self._files.get(name)
        if path is None or volume <= 0:
            return
        try:
            # Popen: çalma bitene kadar beklemeden devam eder (Java'daki ProcessBuilder.start gibi).
            subprocess.Popen([self._player, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass
