"""Denetleyici: uygulamanın durum makinesi.

    YÜKLENİYOR → HAZIR → DİNLİYOR ⇄ BEKLEMEDE → ÇEVRİLİYOR → HAZIR

Kısayol, düğmeler, mikrofon, çevirici ve metin yazıcı burada birbirine
bağlanır. Arayüz bu sınıfın sinyallerini dinler; kendisi karar vermez.
Bağımlılıklar dışarıdan verildiği için (kayıtçı, çevirici, yazıcı) sınıf
sahte nesnelerle test edilebilir (tests/test_controller.py).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from PySide6.QtCore import QObject, Signal, SignalInstance

from .config import MIN_RECORDING_SECONDS, SAMPLE_RATE
from .output import OutputError


class State(Enum):
    LOADING = "Model yükleniyor"
    IDLE = "Hazır"
    LISTENING = "Dinliyor"
    PAUSED = "Beklemede"
    TRANSCRIBING = "Çevriliyor"
    FAILED = "Model yüklenemedi"


@dataclass(frozen=True)
class Outcome:
    """Bir diktenin sonucu; arayüz bunu gösterir."""

    text: str  # çevrilen metin (boş olabilir)
    pasted: bool  # imlecin olduğu yere yazıldı mı
    note: str  # kullanıcıya gösterilecek kısa açıklama


# Protocol: Java'daki interface gibi; aynı yöntemlere sahip her nesne kabul edilir.
class RecorderLike(Protocol):
    finished: SignalInstance
    failed: SignalInstance
    level: SignalInstance

    def start(self) -> bool: ...
    def set_paused(self, paused: bool) -> None: ...
    def stop(self) -> None: ...
    def cancel(self) -> None: ...


class TranscriberLike(Protocol):
    ready: SignalInstance
    load_failed: SignalInstance
    done: SignalInstance
    failed: SignalInstance

    def load(self) -> None: ...
    def transcribe(self, samples, use_prompt: bool) -> None: ...


class SettingsLike(Protocol):
    auto_paste: bool
    use_prompt: bool


class Controller(QObject):
    state_changed = Signal(object)  # State
    outcome = Signal(object)  # Outcome
    notice = Signal(str)  # kısa bilgi (ör. "Kayıt çok kısaydı")

    def __init__(
        self,
        recorder: RecorderLike,
        transcriber: TranscriberLike,
        write_text: Callable[[str], str],
        settings: SettingsLike,
        is_app_active: Callable[[], bool],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._recorder = recorder
        self._transcriber = transcriber
        self._write_text = write_text
        self._settings = settings
        self._is_app_active = is_app_active
        self.state = State.LOADING
        self.last_text = ""
        self.failure = ""

        recorder.finished.connect(self._on_recorded)
        recorder.failed.connect(self._on_recorder_failed)
        transcriber.ready.connect(self._on_model_ready)
        transcriber.load_failed.connect(self._on_model_failed)
        transcriber.done.connect(self._on_transcribed)
        transcriber.failed.connect(self._on_transcribe_failed)

    def start(self) -> None:
        """Modeli yüklemeye başlar."""
        self._transcriber.load()

    # ------------------------------------------------------------ kullanıcı eylemleri

    def toggle(self) -> None:
        """Kısayola basıldı: hazırsa dinlemeyi başlatır, dinliyorsa bitirir."""
        if self.state is State.IDLE:
            self._begin()
        elif self.state in (State.LISTENING, State.PAUSED):
            self.finish()
        elif self.state is State.LOADING:
            self.notice.emit("Model hâlâ yükleniyor; birkaç saniye sonra yeniden deneyin.")
        elif self.state is State.TRANSCRIBING:
            self.notice.emit("Önceki konuşma hâlâ çevriliyor.")
        else:
            self.notice.emit(f"Model yüklenemediği için dinlenemiyor: {self.failure}")

    def pause_resume(self) -> None:
        if self.state is State.LISTENING:
            self._recorder.set_paused(True)
            self._set_state(State.PAUSED)
        elif self.state is State.PAUSED:
            self._recorder.set_paused(False)
            self._set_state(State.LISTENING)

    def finish(self) -> None:
        if self.state in (State.LISTENING, State.PAUSED):
            self._set_state(State.TRANSCRIBING)
            self._recorder.stop()  # kayıt hazır olunca _on_recorded çağrılır

    def cancel(self) -> None:
        if self.state in (State.LISTENING, State.PAUSED):
            self._recorder.cancel()
            self._set_state(State.IDLE)
            self.notice.emit("İptal edildi; hiçbir şey yazılmadı.")

    def paste_last(self) -> None:
        """Son metni imlecin olduğu yere yazar (otomatik yapıştırma kapalıyken ya da yeniden)."""
        if self.last_text:
            pasted, note = self._paste(self.last_text)
            self.outcome.emit(Outcome(self.last_text, pasted, note))

    # ------------------------------------------------------------ olaylar

    def _begin(self) -> None:
        if self._recorder.start():
            self._set_state(State.LISTENING)

    def _on_model_ready(self, _seconds: float, _device: str) -> None:
        if self.state is State.LOADING:
            self._set_state(State.IDLE)

    def _on_model_failed(self, message: str) -> None:
        self.failure = message
        self._set_state(State.FAILED)

    def _on_recorder_failed(self, message: str) -> None:
        if self.state in (State.LISTENING, State.PAUSED, State.TRANSCRIBING):
            self._set_state(State.IDLE)
        self.notice.emit(message)

    def _on_recorded(self, samples) -> None:
        if self.state is not State.TRANSCRIBING:
            return
        if len(samples) < MIN_RECORDING_SECONDS * SAMPLE_RATE:
            self._set_state(State.IDLE)
            self.notice.emit("Kayıt çok kısaydı; hiçbir şey yazılmadı.")
            return
        self._transcriber.transcribe(samples, self._settings.use_prompt)

    def _on_transcribe_failed(self, message: str) -> None:
        if self.state is State.TRANSCRIBING:
            self._set_state(State.IDLE)
        self.notice.emit(f"Çeviri hatası: {message}")

    def _on_transcribed(self, transcript) -> None:
        if self.state is not State.TRANSCRIBING:
            return
        self._set_state(State.IDLE)
        if not transcript.text:
            if transcript.withheld:
                self.outcome.emit(Outcome("", False, f"Konuşma anlaşılamadı (model şunu uydurdu, yazılmadı: “{transcript.withheld}”)."))
            else:
                self.outcome.emit(Outcome("", False, "Konuşma algılanmadı; hiçbir şey yazılmadı."))
            return
        self.last_text = transcript.text
        if not self._settings.auto_paste:
            self.outcome.emit(Outcome(transcript.text, False, "Otomatik yapıştırma kapalı; metin yazılmadı."))
            return
        pasted, note = self._paste(transcript.text)
        self.outcome.emit(Outcome(transcript.text, pasted, note))

    # ------------------------------------------------------------ yardımcılar

    def _paste(self, text: str) -> tuple[bool, str]:
        # Kendi penceremiz öndeyse yazmayız: metin başka uygulamaya gitmez, kaybolurdu.
        if self._is_app_active():
            return False, "Speak to Print penceresi önde olduğu için metin yazılmadı; Kopyala ile alabilirsiniz."
        try:
            # Sona boşluk: arka arkaya yapılan dikteler birbirine yapışmasın.
            method = self._write_text(text + " ")
        except OutputError as error:
            return False, f"Metin yazılamadı: {error}"
        return True, "Yazıldı." if method == "kwin-type" else "Yazıldı (yedek yöntem: pano)."

    def _set_state(self, state: State) -> None:
        if state is not self.state:
            self.state = state
            self.state_changed.emit(state)
