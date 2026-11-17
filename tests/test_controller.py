"""Durum makinesinin testleri: gerçek mikrofon, model ve klavye yerine sahte nesneler kullanılır."""

import numpy as np
import pytest
from speak_to_print.config import SAMPLE_RATE
from speak_to_print.controller import Controller, State
from speak_to_print.output import OutputError
from speak_to_print.transcriber import Transcript

from fakes import FakeRecorder, FakeSettings, FakeTranscriber

ONE_SECOND = np.zeros(SAMPLE_RATE, dtype=np.float32)


class Harness:
    def __init__(self):
        self.recorder = FakeRecorder()
        self.transcriber = FakeTranscriber()
        self.settings = FakeSettings()
        self.written = []
        self.write_error = None
        self.method = "kwin-type"
        self.app_active = False
        self.controller = Controller(self.recorder, self.transcriber, self.write, self.settings, lambda: self.app_active)
        self.states, self.outcomes, self.notices = [], [], []
        self.controller.state_changed.connect(self.states.append)
        self.controller.outcome.connect(self.outcomes.append)
        self.controller.notice.connect(self.notices.append)
        self.controller.start()

    def write(self, text):
        if self.write_error:
            raise OutputError(self.write_error)
        self.written.append(text)
        return self.method

    def ready(self):
        self.transcriber.ready.emit(1.5, "cuda")
        return self

    def dictate(self, text="Merhaba dünya.", withheld=""):
        """Kısayol → kayıt → kısayol → çeviri sonucu."""
        self.controller.toggle()
        self.controller.toggle()
        self.recorder.finished.emit(ONE_SECOND)
        self.transcriber.done.emit(Transcript(text, withheld, 0.3, 1.0))


@pytest.fixture
def h():
    return Harness()


def test_starts_loading_and_becomes_idle(h):
    assert h.controller.state is State.LOADING and h.transcriber.requests == ["load"]
    h.ready()
    assert h.controller.state is State.IDLE


def test_shortcut_during_model_load_does_not_record(h):
    h.controller.toggle()
    assert h.controller.state is State.LOADING and h.recorder.calls == []
    assert "yükleniyor" in h.notices[-1]


def test_full_dictation_types_text_with_trailing_space(h):
    h.ready().dictate("Merhaba dünya.")
    assert h.states == [State.IDLE, State.LISTENING, State.TRANSCRIBING, State.IDLE]
    assert h.recorder.calls == ["start", "stop"]
    assert h.transcriber.requests[-1] == ("transcribe", SAMPLE_RATE, True)
    assert h.written == ["Merhaba dünya. "]
    assert h.outcomes[-1].pasted and h.outcomes[-1].text == "Merhaba dünya."
    assert h.controller.last_text == "Merhaba dünya."


def test_shortcut_during_transcription_is_ignored(h):
    h.ready()
    h.controller.toggle()
    h.controller.toggle()
    h.controller.toggle()  # çeviri sürerken
    assert h.controller.state is State.TRANSCRIBING and h.recorder.calls == ["start", "stop"]
    assert "çevriliyor" in h.notices[-1]


def test_shortcut_after_result_starts_new_dictation(h):
    h.ready().dictate("Bir.")
    h.dictate("İki.")
    assert h.written == ["Bir. ", "İki. "] and h.controller.state is State.IDLE


def test_pause_and_resume(h):
    h.ready()
    h.controller.toggle()
    h.controller.pause_resume()
    assert h.controller.state is State.PAUSED
    h.controller.pause_resume()
    assert h.controller.state is State.LISTENING
    assert h.recorder.calls == ["start", "paused=True", "paused=False"]


def test_finish_while_paused(h):
    h.ready()
    h.controller.toggle()
    h.controller.pause_resume()
    h.controller.toggle()
    assert h.controller.state is State.TRANSCRIBING and h.recorder.calls[-1] == "stop"


def test_cancel_discards_recording(h):
    h.ready()
    h.controller.toggle()
    h.controller.cancel()
    assert h.controller.state is State.IDLE and h.recorder.calls == ["start", "cancel"]
    # İptalden sonra gecikmiş bir kayıt ya da çeviri sonucu gelse bile yazılmaz.
    h.recorder.finished.emit(ONE_SECOND)
    h.transcriber.done.emit(Transcript("Yazılmamalı.", "", 0.1, 1.0))
    assert h.written == [] and h.outcomes == []


def test_too_short_recording_is_not_transcribed(h):
    h.ready()
    h.controller.toggle()
    h.controller.toggle()
    h.recorder.finished.emit(np.zeros(1000, dtype=np.float32))
    assert h.controller.state is State.IDLE and h.transcriber.requests == ["load"]
    assert "kısa" in h.notices[-1]


def test_auto_paste_off_shows_text_without_typing(h):
    h.settings.auto_paste = False
    h.ready().dictate("Yalnızca göster.")
    assert h.written == []
    assert h.outcomes[-1].text == "Yalnızca göster." and not h.outcomes[-1].pasted
    h.controller.paste_last()  # kullanıcı Yapıştır'a bastı
    assert h.written == ["Yalnızca göster. "] and h.outcomes[-1].pasted


def test_does_not_type_into_own_window(h):
    h.app_active = True
    h.ready().dictate("Kaybolmamalı.")
    assert h.written == []
    assert h.outcomes[-1].text == "Kaybolmamalı." and not h.outcomes[-1].pasted


def test_empty_transcript_types_nothing(h):
    h.ready().dictate("")
    assert h.written == [] and h.outcomes[-1].text == "" and "algılanmadı" in h.outcomes[-1].note


def test_invented_text_is_withheld_but_shown(h):
    h.ready().dictate("", withheld="Altyazı M.K.")
    assert h.written == [] and "Altyazı M.K." in h.outcomes[-1].note


def test_fallback_method_is_reported(h):
    h.method = "pano"
    h.ready().dictate("Yedekle yazıldı.")
    assert h.outcomes[-1].pasted and "yedek" in h.outcomes[-1].note


def test_output_failure_keeps_text_available(h):
    h.write_error = "kwin-type yok; pano da olmadı"
    h.ready().dictate("Yazılamadı ama duruyor.")
    assert not h.outcomes[-1].pasted and h.outcomes[-1].text == "Yazılamadı ama duruyor."
    assert h.controller.last_text == "Yazılamadı ama duruyor."


def test_microphone_missing(h):
    h.recorder.start_ok = False
    h.ready()
    h.controller.toggle()
    assert h.controller.state is State.IDLE and "Mikrofon" in h.notices[-1]


def test_model_load_failure(h):
    h.transcriber.load_failed.emit("CUDA yok")
    assert h.controller.state is State.FAILED
    h.controller.toggle()
    assert h.recorder.calls == [] and "CUDA yok" in h.notices[-1]


def test_transcription_error_returns_to_idle(h):
    h.ready()
    h.controller.toggle()
    h.controller.toggle()
    h.recorder.finished.emit(ONE_SECOND)
    h.transcriber.failed.emit("RuntimeError: bellek")
    assert h.controller.state is State.IDLE and "bellek" in h.notices[-1]


def test_prompt_setting_is_passed_to_transcriber(h):
    h.settings.use_prompt = False
    h.ready()
    h.controller.toggle()
    h.controller.toggle()
    h.recorder.finished.emit(ONE_SECOND)
    assert h.transcriber.requests[-1] == ("transcribe", SAMPLE_RATE, False)


def test_paste_text_types_edited_text_and_remembers_it(h):
    h.ready().dictate("İlk hâli.")
    h.controller.paste_text("Düzeltilmiş hâli.")
    assert h.written == ["İlk hâli. ", "Düzeltilmiş hâli. "]
    assert h.controller.last_text == "Düzeltilmiş hâli." and h.outcomes[-1].pasted


def test_paste_text_ignores_blank_text(h):
    h.ready()
    h.controller.paste_text("   ")
    assert h.written == [] and h.outcomes == []


def test_vocabulary_is_passed_to_transcriber(h):
    h.settings.vocabulary = ["commit", "pull request"]
    h.ready()
    h.controller.toggle()
    h.controller.toggle()
    h.recorder.finished.emit(ONE_SECOND)
    assert h.transcriber.vocabulary == ["commit", "pull request"]


def test_start_listening_never_stops(h):
    """"Basılı tut" kipi: basınca başlar, tuş tekrarı gelse de durmaz; bırakınca finish çağrılır."""
    h.ready()
    h.controller.start_listening()
    h.controller.start_listening()
    assert h.controller.state is State.LISTENING and h.recorder.calls == ["start"]
    h.controller.finish()
    assert h.controller.state is State.TRANSCRIBING


def test_start_listening_while_loading_only_notifies(h):
    h.controller.start_listening()
    assert h.recorder.calls == [] and "yükleniyor" in h.notices[-1]


def test_chosen_clipboard_method_note(h):
    h.method = "pano-seçili"
    h.ready().dictate("Panoyla.")
    assert h.outcomes[-1].pasted and h.outcomes[-1].note == "Yazıldı (pano)."


def test_paste_text_keeps_line_breaks_typed_in_the_editor(h):
    h.ready().dictate("İlk hâli.")
    h.controller.paste_text("Birinci satır.\nİkinci satır.")
    assert h.written[-1] == "Birinci satır.\nİkinci satır. "


def test_recording_limit_finishes_listening_and_transcribes(h):
    h.ready().controller.toggle()
    h.recorder.limit_reached.emit()
    assert h.controller.state is State.TRANSCRIBING and h.recorder.calls[-1] == "stop"
    assert "Kayıt 10 dakikaya ulaştı; dinleme bitirildi." in h.notices


def test_outcome_after_the_limit_says_why_listening_stopped(h):
    h.ready().controller.toggle()
    h.recorder.limit_reached.emit()
    h.recorder.finished.emit(ONE_SECOND)
    h.transcriber.done.emit(Transcript("Uzun bir konuşma.", "", 12.0, 600.0))
    assert h.written == ["Uzun bir konuşma. "]
    assert "10 dakikaya ulaştı" in h.outcomes[-1].note


def test_note_about_the_limit_does_not_carry_over_to_the_next_dictation(h):
    h.ready().controller.toggle()
    h.recorder.limit_reached.emit()
    h.recorder.finished.emit(ONE_SECOND)
    h.transcriber.done.emit(Transcript("Uzun bir konuşma.", "", 12.0, 600.0))
    h.dictate("İkinci.")
    assert "10 dakika" not in h.outcomes[-1].note


def test_limit_signal_while_not_listening_is_ignored(h):
    h.ready()
    h.recorder.limit_reached.emit()
    assert h.controller.state is State.IDLE and h.recorder.calls == []
