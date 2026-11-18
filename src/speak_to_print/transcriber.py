"""Konuşmayı yazıya çevirme (faster-whisper, GPU).

Model yükleme ve çeviri uzun süren işlerdir; arayüz donmasın diye ayrı bir
iş parçacığında çalışırlar. Kalıp şöyle: `_Worker` nesnesi bir QThread'e
taşınır; ona iş, Qt sinyaliyle gönderilir ve sonuç yine sinyalle döner.
Java karşılığı: tek iş parçacıklı bir ExecutorService'e görev vermek ve
sonucu SwingUtilities.invokeLater ile arayüze taşımak.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QObject, QThread, Signal, Slot

from . import textguard
from .config import COMPUTE_TYPE, LANGUAGE, MODEL_NAME, MODEL_REVISION, SAMPLE_RATE, build_prompt
from .cuda_libs import preload_cuda_libraries

log = logging.getLogger(__name__)


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
    status = Signal(str)  # yükleme sırasındaki ara bilgiler

    def __init__(self) -> None:
        super().__init__()
        self._model = None
        self.gpu_error = ""  # ekran kartı kullanılamadıysa nedeni

    def _model_path(self) -> str:
        """Modelin diskteki yolu. Bilgisayarda yoksa bir kez indirir; indiremezse anlaşılır bir hata verir."""
        from faster_whisper import download_model

        try:
            # local_files_only: ağa hiç çıkmadan yalnızca önbelleğe bakar.
            return download_model(MODEL_NAME, local_files_only=True, revision=MODEL_REVISION)
        except Exception:  # noqa: BLE001 — model önbellekte yok
            self.status.emit("Model ilk kez indiriliyor (yaklaşık 3 GB); bu birkaç dakika sürebilir…")
            try:
                return download_model(MODEL_NAME, revision=MODEL_REVISION)
            except Exception as error:  # noqa: BLE001
                raise RuntimeError("Konuşma tanıma modeli bu bilgisayarda yok ve indirilemedi. İnternet "
                                   "bağlantınızı kontrol edip uygulamayı yeniden açın.") from error

    @Slot()
    def load(self) -> None:
        try:
            start = time.perf_counter()
            preload_cuda_libraries()
            from faster_whisper import WhisperModel

            path = self._model_path()
            try:
                self._model = WhisperModel(path, device="cuda", compute_type=COMPUTE_TYPE)
                device = "cuda"
            except Exception as gpu_error:  # noqa: BLE001 — ekran kartı yok ya da kullanılamıyor
                self.status.emit("Ekran kartı kullanılamadı; model işlemciye yükleniyor…")
                self.gpu_error = f"{type(gpu_error).__name__}: {gpu_error}"
                # İşlemcide 8 bitlik hesap: daha yavaş ama ekran kartı olmadan da çalışır.
                self._model = WhisperModel(path, device="cpu", compute_type="int8")
                device = "cpu"
            self.ready.emit(time.perf_counter() - start, device)
        except Exception as error:  # noqa: BLE001 — hatayı arayüze taşıyoruz
            self.load_failed.emit(str(error) if isinstance(error, RuntimeError) else f"{type(error).__name__}: {error}")
            return
        if device == "cuda":
            self._warm_up()

    def _warm_up(self) -> None:
        """Sonucu atılan kısa bir çeviri: ilk diktenin ekran kartı hazırlığını beklememesi için.

        Ekran kartındaki ilk çeviri, CUDA ve cuBLAS'ın hazırlığı ile sessizlik ayıklayıcının (VAD)
        yüklenmesi yüzünden ~0,15–0,3 sn daha uzun sürüyor. Bu bedeli "hazır"dan hemen sonra bu
        çeviri öder; o sırada gelen bir dikte kuyrukta bekler. Çıktı hiçbir yere gitmez (sessizlikten
        uydurulan metin ne yazılır ne günlüğe girer). İşlemcide yapılmaz: orada saniyeler sürer.
        """
        try:
            start = time.perf_counter()
            from faster_whisper.vad import get_vad_model

            get_vad_model()  # bir kez yüklenir, sonra önbellekten gelir
            segments, _info = self._model.transcribe(
                np.zeros(SAMPLE_RATE, dtype=np.float32), language=LANGUAGE, beam_size=5, vad_filter=False,
                initial_prompt=build_prompt(True, []), temperature=0.0,
            )
            for _segment in segments:  # üreteç tüketilince çeviri yapılır; sonuç atılır
                pass
            log.info("Model ısıtıldı (%.0f ms).", (time.perf_counter() - start) * 1000)
        except Exception as error:  # noqa: BLE001 — ısınma olmazsa model yine çalışır
            log.warning("Model ısıtılamadı: %s", type(error).__name__)

    @Slot(object, bool, list)
    def transcribe(self, samples: np.ndarray, use_prompt: bool, vocabulary: list) -> None:
        if self._model is None:
            self.failed.emit("Model yüklü değil.")
            return
        try:
            start = time.perf_counter()
            prompt = build_prompt(use_prompt, vocabulary)
            segments, _info = self._model.transcribe(
                samples, language=LANGUAGE, beam_size=5, vad_filter=True,
                initial_prompt=prompt or None,
            )
            # `segments` tembel bir üreteçtir; çeviri, elemanlar tüketilirken yapılır.
            # Model çıktısı tek satır olur: satır sonu ya da başka bir denetim karakteri
            # imlece tuş gibi gider ve terminalde satırı çalıştırabilirdi.
            text = textguard.single_line(" ".join(segment.text for segment in segments))
            withheld = ""
            if textguard.is_invented(text) or textguard.is_prompt_echo(text, prompt):
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
    status = Signal(str)

    _load_requested = Signal()
    _transcribe_requested = Signal(object, bool, list)

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
        self._worker.status.connect(self.status)
        self._load_started = False
        self._load_result: tuple[str, tuple] | None = None  # ("ready", (sn, aygıt)) ya da ("load_failed", (ileti,))
        self.ready.connect(lambda seconds, device: self._remember("ready", seconds, device))
        self.load_failed.connect(lambda message: self._remember("load_failed", message))
        self._thread.start()

    @property
    def gpu_error(self) -> str:
        return self._worker.gpu_error

    def load(self) -> None:
        """Modeli yükler. Kaç kez çağrılırsa çağrılsın model bir kez yüklenir.

        Açılış yüklemeyi erken başlatır, `Controller.start()` da ister; ikinci istek yeni bir
        yükleme başlatmaz. Yükleme bitmişse sonuç (`ready` ya da `load_failed`) yeniden
        bildirilir: haber dinleyiciler bağlanmadan teslim edilmiş olsa bile isteyen onu alır.
        """
        if self._load_result is not None:
            name, args = self._load_result
            getattr(self, name).emit(*args)
        elif not self._load_started:
            self._load_started = True
            self._load_requested.emit()

    def _remember(self, name: str, *args) -> None:
        self._load_result = (name, args)

    def transcribe(self, samples: np.ndarray, use_prompt: bool, vocabulary: list[str] | None = None) -> None:
        self._transcribe_requested.emit(samples, use_prompt, list(vocabulary or []))

    def shutdown(self, timeout_ms: int = 1500) -> bool:
        """İş parçacığını durdurur. Süre içinde bitmezse False döner (iş hâlâ sürüyordur)."""
        self._thread.quit()
        return self._thread.wait(timeout_ms)
