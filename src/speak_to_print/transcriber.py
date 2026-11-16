"""Konuşmayı yazıya çevirme (faster-whisper, GPU).

Model yükleme ve çeviri uzun süren işlerdir; arayüz donmasın diye ayrı bir
iş parçacığında çalışırlar. Kalıp şöyle: `_Worker` nesnesi bir QThread'e
taşınır; ona iş, Qt sinyaliyle gönderilir ve sonuç yine sinyalle döner.
Java karşılığı: tek iş parçacıklı bir ExecutorService'e görev vermek ve
sonucu SwingUtilities.invokeLater ile arayüze taşımak.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QObject, QThread, Signal, Slot

from . import textguard
from .config import COMPUTE_TYPE, LANGUAGE, MODEL_NAME, SAMPLE_RATE, STYLE_PROMPT
from .cuda_libs import preload_cuda_libraries


@dataclass(frozen=True)
class Transcript:
    text: str  # yazılacak metin (alıkonduysa boş)
    withheld: str  # uydurma sayılıp alıkonan metin (yoksa boş)
    seconds: float  # çevirinin süresi
    audio_seconds: float  # kaydın süresi


class _Worker(QObject):
    ready = Signal(float, str)  # yükleme süresi, aygıt ("cuda" ya da "cpu")
    load_failed = Signal(str)
    done = Signal(object)  # Transcript
    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._model = None

    @Slot()
    def load(self) -> None:
        try:
            start = time.perf_counter()
            preload_cuda_libraries()
            # Model önbellekteyse ağa hiç çıkma; kütüphane bu değişkeni içe aktarılırken okur.
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            from faster_whisper import WhisperModel

            try:
                self._model = WhisperModel(MODEL_NAME, device="cuda", compute_type=COMPUTE_TYPE, local_files_only=True)
            except Exception as offline_error:  # noqa: BLE001 — model önbellekte yoksa indirmeyi dene
                if "cuda" in str(offline_error).lower() or "cublas" in str(offline_error).lower():
                    raise
                os.environ["HF_HUB_OFFLINE"] = "0"
                self._model = WhisperModel(MODEL_NAME, device="cuda", compute_type=COMPUTE_TYPE)
            self.ready.emit(time.perf_counter() - start, "cuda")
        except Exception as error:  # noqa: BLE001 — hatayı arayüze taşıyoruz
            self.load_failed.emit(f"{type(error).__name__}: {error}")

    @Slot(object, bool)
    def transcribe(self, samples: np.ndarray, use_prompt: bool) -> None:
        if self._model is None:
            self.failed.emit("Model yüklü değil.")
            return
        try:
            start = time.perf_counter()
            segments, _info = self._model.transcribe(
                samples, language=LANGUAGE, beam_size=5, vad_filter=True,
                initial_prompt=STYLE_PROMPT if use_prompt else None,
            )
            # `segments` tembel bir üreteçtir; çeviri, elemanlar tüketilirken yapılır.
            text = " ".join(segment.text.strip() for segment in segments).strip()
            withheld = ""
            if textguard.is_invented(text):
                text, withheld = "", text
            self.done.emit(Transcript(text, withheld, time.perf_counter() - start, len(samples) / SAMPLE_RATE))
        except Exception as error:  # noqa: BLE001
            self.failed.emit(f"{type(error).__name__}: {error}")


class Transcriber(QObject):
    """Arayüz iş parçacığından kullanılan yüz: işi arka plandaki `_Worker`'a iletir."""

    ready = Signal(float, str)
    load_failed = Signal(str)
    done = Signal(object)  # Transcript
    failed = Signal(str)

    _load_requested = Signal()
    _transcribe_requested = Signal(object, bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread = QThread(self)
        self._thread.setObjectName("transcriber")
        self._worker = _Worker()
        self._worker.moveToThread(self._thread)
        # Farklı iş parçacıkları arasındaki sinyaller kuyruğa alınır ve alıcının iş parçacığında çalışır.
        self._load_requested.connect(self._worker.load)
        self._transcribe_requested.connect(self._worker.transcribe)
        self._worker.ready.connect(self.ready)
        self._worker.load_failed.connect(self.load_failed)
        self._worker.done.connect(self.done)
        self._worker.failed.connect(self.failed)
        self._thread.start()

    def load(self) -> None:
        self._load_requested.emit()

    def transcribe(self, samples: np.ndarray, use_prompt: bool) -> None:
        self._transcribe_requested.emit(samples, use_prompt)

    def shutdown(self, timeout_ms: int = 1500) -> bool:
        """İş parçacığını durdurur. Süre içinde bitmezse False döner (iş hâlâ sürüyordur)."""
        self._thread.quit()
        return self._thread.wait(timeout_ms)
