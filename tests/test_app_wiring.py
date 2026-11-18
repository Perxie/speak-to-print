"""Arayüz bağlantılarının testleri: gerçek pencereler (ekransız), sahte mikrofon ve model.

Bu testler pencerelerin görünümünü değil davranışını sınar; tasarım değişse de geçmeleri gerekir.
Dayandıkları adlar (ör. `popup.pause_button`, `popup.text`) arayüz sınıflarının sabit yüzeyidir.
"""

import time

import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, QSettings, Qt
from PySide6 import QtGui
from PySide6.QtGui import QMouseEvent, QTextDocument, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from fakes import FakeRecorder, FakeTranscriber
from speak_to_print.app import Application
from speak_to_print.config import SAMPLE_RATE, SHORTCUT_ID
from speak_to_print.controller import State
from speak_to_print import history as history_module
from speak_to_print.history import History
from speak_to_print.settings import Settings
from speak_to_print.transcriber import Transcript

AUDIO = np.zeros(SAMPLE_RATE, dtype=np.float32)


class Env:
    def __init__(self, tmp_path):
        self.written, self.copied, self.focus = [], [], False
        self.recorder, self.transcriber = FakeRecorder(), FakeTranscriber()
        self.settings = Settings(store=QSettings(str(tmp_path / "s.conf"), QSettings.Format.IniFormat))
        self.settings.sounds = False  # testte ses çalma
        self.app = Application(
            settings=self.settings, write_text=self.write, app_has_focus=lambda: self.focus,
            history=History(tmp_path / "h.db"), recorder=self.recorder, transcriber=self.transcriber,
            copy_text=self.copied.append,
        )
        self.app.start(listen_for_instances=False, use_hotkeys=False)
        self.transcriber.ready.emit(1.0, "cuda")

    def write(self, text):
        self.written.append(text)
        return "kwin-type"

    def press(self):
        self.app.hotkeys.activated.emit(SHORTCUT_ID)

    def release(self):
        self.app.hotkeys.deactivated.emit(SHORTCUT_ID)

    def result(self, text="Merhaba dünya.", withheld=""):
        self.recorder.finished.emit(AUDIO)
        self.transcriber.done.emit(Transcript(text, withheld, 0.2, 1.0))

    def dictate(self, text="Merhaba dünya."):
        self.press()
        self.press()
        self.result(text)


@pytest.fixture
def env(tmp_path):
    e = Env(tmp_path)
    yield e
    e.app.shutdown()


def test_shortcut_shows_popup_with_listening_buttons(env):
    env.press()
    popup = env.app.popup
    assert env.app.controller.state is State.LISTENING and popup.isVisible()
    assert popup.pause_button.isVisible() and popup.finish_button.isVisible() and popup.cancel_button.isVisible()
    assert not popup.copy_button.isVisible() and not popup.listen_button.isVisible()


def test_popup_buttons_pause_resume_finish_cancel(env):
    popup = env.app.popup
    env.press()
    popup.pause_button.click()
    assert env.app.controller.state is State.PAUSED and popup.pause_button.text() == "Devam"
    popup.pause_button.click()
    assert env.app.controller.state is State.LISTENING and popup.pause_button.text() == "Beklet"
    popup.finish_button.click()
    assert env.app.controller.state is State.TRANSCRIBING
    env.result("Bitti.")
    env.press()
    popup.cancel_button.click()
    assert env.app.controller.state is State.IDLE and env.written == ["Bitti. "]


def test_result_is_typed_shown_and_popup_hides_by_itself(env):
    env.dictate("Yazılan metin.")
    popup = env.app.popup
    assert env.written == ["Yazılan metin. "] and popup.text.toPlainText() == "Yazılan metin."
    assert popup.copy_button.isVisible() and popup.edit_button.isVisible() and popup.listen_button.isVisible()
    assert popup.paste_button.text() == "Yeniden yapıştır" and popup._hide_timer.isActive()


def test_auto_paste_off_keeps_text_on_screen(env):
    env.app.popup.auto_paste.click()
    assert env.settings.auto_paste is False and not env.app.window.auto_paste.isChecked()
    env.dictate("Yalnızca göster.")
    popup = env.app.popup
    assert env.written == [] and popup.text.toPlainText() == "Yalnızca göster."
    assert popup.paste_button.text() == "Yapıştır" and not popup._hide_timer.isActive() and popup.isVisible()
    popup.paste_button.click()
    assert env.written == ["Yalnızca göster. "]
    popup.copy_button.click()
    assert env.copied == ["Yalnızca göster."]


def test_own_window_in_front_does_not_type(env):
    env.focus = True
    env.dictate("Kaybolmasın.")
    assert env.written == [] and env.app.popup.text.toPlainText() == "Kaybolmasın."


def test_popup_widgets_never_take_keyboard_focus(env):
    popup = env.app.popup
    assert popup.focusPolicy() == Qt.FocusPolicy.NoFocus
    for widget in (popup.text, popup.auto_paste, popup.listen_button, popup.pause_button, popup.finish_button,
                   popup.cancel_button, popup.edit_button, popup.copy_button, popup.paste_button, popup.close_button):
        assert widget.focusPolicy() == Qt.FocusPolicy.NoFocus, widget
    assert popup.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus


def test_hold_mode_hides_pause_and_finish_and_release_finishes(env):
    env.settings.hotkey_mode = "hold"
    env.press()
    popup = env.app.popup
    assert not popup.pause_button.isVisible() and not popup.finish_button.isVisible() and popup.cancel_button.isVisible()
    env.release()
    assert env.app.controller.state is State.TRANSCRIBING


def test_release_does_nothing_in_toggle_mode(env):
    env.press()
    env.release()
    assert env.app.controller.state is State.LISTENING


def test_clicking_text_opens_editor_and_editor_pastes_after_focus_returns(env, qt_app):
    env.dictate("İlk hâli.")
    popup, editor = env.app.popup, env.app.editor
    click = QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(5, 5), QPointF(5, 5), Qt.MouseButton.LeftButton,
                        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(popup.text.viewport(), click)
    assert editor.isVisible() and not popup.isVisible() and editor.text.toPlainText() == "İlk hâli."
    assert not editor.text.isReadOnly() and editor.listen_button.focusPolicy() == Qt.FocusPolicy.NoFocus
    editor.text.setPlainText("Düzeltilmiş hâli.")
    assert env.app.controller.last_text == "Düzeltilmiş hâli."
    env.focus = True
    editor.paste_button.click()
    assert not editor.isVisible() and len(env.written) == 1  # odak dönmeden yazılmaz
    env.focus = False
    env.app._paste_when_focus_released()
    for _ in range(40):  # yazmadan önceki kısa bekleme
        qt_app.processEvents()
        if len(env.written) == 2:
            break
        import time; time.sleep(0.01)
    assert env.written[-1] == "Düzeltilmiş hâli. "


def test_listen_buttons_everywhere(env):
    app = env.app
    app.window.listen_button.click()
    assert app.controller.state is State.LISTENING and app.window.listen_button.text() == "Bitir"
    app.window.listen_button.click()
    env.result("Bir.")
    app.popup.listen_button.click()
    assert app.controller.state is State.LISTENING
    app.popup.cancel_button.click()
    app.tray._listen_action.trigger()
    assert app.controller.state is State.LISTENING
    app.popup.cancel_button.click()
    app.editor.open_with("x")
    app.editor.listen_button.click()
    assert app.controller.state is State.LISTENING and app.editor.listen_button.text() == "Bitir"


def test_history_list_and_keep_history_setting(env):
    env.dictate("Birinci.")
    env.dictate("İkinci.")
    window = env.app.window
    assert window.history.count() == 2 and window.preview.toPlainText() == "İkinci."
    env.settings.keep_history = False
    env.dictate("Kaydedilmez.")
    assert window.history.count() == 2
    window.history.setCurrentRow(1)
    window.delete_button.click()
    assert window.history.count() == 1 and [e.text for e in env.app.history.recent()] == ["İkinci."]


def test_withheld_and_empty_results_type_nothing(env):
    env.dictate("")
    assert env.written == [] and not env.app.popup.copy_button.isEnabled()
    env.press()
    env.press()
    env.result("", withheld="Altyazı M.K.")
    assert env.written == [] and "Altyazı M.K." in env.app.popup.note.text()


def test_notice_while_idle_is_shown_in_popup(env):
    env.press()
    env.recorder.failed.emit("Mikrofon kayboldu (Sahte mikrofon); dinleme durduruldu.")
    assert env.app.controller.state is State.IDLE and "Mikrofon kayboldu" in env.app.popup.note.text()
    assert env.app.popup.isVisible()


def test_settings_dialog_writes_settings(env):
    dialog = env.app.settings_dialog
    env.app.window.settings_button.click()
    assert dialog.isVisible()
    dialog.mode_hold.click()
    dialog.vocabulary.setPlainText("commit\n\nrefactor")
    dialog.keep_history.click()
    _run_event_loop_for(0.8)  # sözlük kısa bir beklemeden sonra kaydedilir
    assert env.settings.hotkey_mode == "hold" and env.settings.vocabulary == ["commit", "refactor"]
    assert env.settings.keep_history is False
    env.press()  # basılı tut kipi: bırakınca biter
    env.release()
    env.result("Sözlükle.")
    assert env.transcriber.vocabulary == ["commit", "refactor"]


MARKUP = '<b>Kalın</b> <a href="https://ornek.invalid">bağlantı</a>'


def _labels_with_outside_text(app):
    """Dışarıdan gelen metni (model çıktısı, aygıt adı, hata iletisi) gösteren etiketler."""
    return {
        "ana pencere açıklama": app.window.detail,
        "ana pencere kısayol": app.window.shortcut,
        "küçük pencere not": app.popup.note,
        "küçük pencere ileti": app.popup._message,
        "düzenleyici not": app.editor.note,
    }


def test_labels_with_outside_text_show_markup_literally(env):
    env.press()
    env.press()
    env.recorder.finished.emit(AUDIO)
    env.transcriber.done.emit(Transcript("", MARKUP, 0.2, 1.0))  # uydurma metin alıkondu
    env.app.window.set_shortcut_error(MARKUP)
    env.app.editor.show_note(MARKUP)
    for name, label in _labels_with_outside_text(env.app).items():
        assert label.textFormat() == Qt.TextFormat.PlainText, name


def _tooltip_as_shown(tooltip):
    # QToolTip, HTML'ye benzeyen metni biçimli, ötekini düz gösterir.
    document = QTextDocument()
    if QtGui.Qt.mightBeRichText(tooltip):
        document.setHtml(tooltip)
    else:
        document.setPlainText(tooltip)
    return document.toPlainText()


def test_history_tooltip_shows_markup_literally(env):
    env.dictate(MARKUP)
    assert _tooltip_as_shown(env.app.window.history.item(0).toolTip()) == MARKUP


def test_history_tooltip_of_plain_text_is_unchanged(env):
    env.dictate("Düz bir cümle, 3 < 5.")
    assert env.app.window.history.item(0).toolTip() == "Düz bir cümle, 3 < 5."


def test_history_list_never_shows_more_than_the_database_keeps(env, monkeypatch):
    # Veritabanı en yeni MAX_ENTRIES kaydı tutuyor; liste de fazlasını göstermemeli
    # (yoksa silinmiş kayıtlar listede kalır ve onlarda "Sil" boşa çalışır).
    monkeypatch.setattr(history_module, "MAX_ENTRIES", 3)
    for n in range(5):
        env.dictate(f"Dikte {n}.")
    window = env.app.window
    shown = [window.history.item(row).data(Qt.ItemDataRole.UserRole).text for row in range(window.history.count())]
    assert shown == [entry.text for entry in env.app.history.recent()] == ["Dikte 4.", "Dikte 3.", "Dikte 2."]


def test_invented_text_is_shown_but_never_written_to_the_log(env, caplog):
    caplog.set_level("INFO", logger="speak_to_print")
    env.press()
    env.press()
    env.result("", withheld='Uydurma 4711 "düz tırnaklı"')
    assert "Uydurma 4711" in env.app.popup._message.text() and "Uydurma 4711" in env.app.window.detail.text()
    assert "Uydurma 4711" not in caplog.text and "Sonuç:" in caplog.text


def _run_event_loop_for(seconds):
    """Zamanlayıcılar (ör. ayarların gecikmeli kaydı) çalışsın diye olay döngüsünü kısa süre döndürür."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QApplication.processEvents()
        time.sleep(0.01)


def _count_saves(env):
    saves = []
    env.settings.changed.connect(lambda: saves.append(1))
    return saves


def test_typing_in_the_vocabulary_saves_once_after_a_short_pause(env):
    dialog = env.app.settings_dialog
    dialog.open()
    saves = _count_saves(env)
    for letter in "kubernetes":
        dialog.vocabulary.insertPlainText(letter)
    assert saves == []  # her harfte diske yazılmıyor
    _run_event_loop_for(0.8)
    assert saves == [1] and env.settings.vocabulary == ["kubernetes"]


def test_moving_the_volume_slider_saves_once(env):
    dialog = env.app.settings_dialog
    dialog.open()
    saves = _count_saves(env)
    for value in range(10, 60, 5):
        dialog.sound_volume.setValue(value)
    assert saves == []
    _run_event_loop_for(0.8)
    assert saves == [1] and env.settings.sound_volume == 55


def test_closing_the_settings_window_saves_a_pending_change_at_once(env):
    dialog = env.app.settings_dialog
    dialog.open()
    dialog.vocabulary.setPlainText("kubernetes")
    dialog.hide()
    assert env.settings.vocabulary == ["kubernetes"]


def test_sound_test_button_uses_the_volume_on_the_slider(env, monkeypatch):
    played_at = []
    monkeypatch.setattr(env.app.sounds, "play", lambda name, force=False: played_at.append(env.settings.sound_volume))
    dialog = env.app.settings_dialog
    dialog.open()
    dialog.sound_volume.setValue(80)
    dialog.test_sound_button.click()
    assert played_at == [80]


def test_hidden_settings_window_does_not_rebuild_the_microphone_list(env, monkeypatch):
    dialog = env.app.settings_dialog
    rebuilds = []
    monkeypatch.setattr(dialog, "_fill_microphones", lambda: rebuilds.append(1))
    env.app.popup.auto_paste.click()  # küçük penceredeki anahtar ayarı değiştirir
    assert rebuilds == []


def test_open_settings_window_keeps_its_microphone_list_on_unrelated_changes(env, monkeypatch):
    dialog = env.app.settings_dialog
    dialog.open()
    rebuilds = []
    monkeypatch.setattr(dialog, "_fill_microphones", lambda: rebuilds.append(1))
    dialog.keep_history.click()
    assert rebuilds == [] and env.settings.keep_history is False


def test_saving_with_nothing_pending_does_not_overwrite_settings_with_stale_values(env):
    # Kapalı pencere bileşenlerini güncellemiyor; bekleyen bir değişiklik yoksa kaydetme bir şey yazmamalı.
    env.settings.vocabulary = ["başka yerden"]
    env.app.settings_dialog.flush()
    assert env.settings.vocabulary == ["başka yerden"]


def _wheel(widget):
    """Bileşenin üstünde bir tık aşağı fare tekerleği."""
    event = QWheelEvent(QPointF(5, 5), QPointF(widget.mapToGlobal(QPoint(5, 5))), QPoint(), QPoint(0, -120),
                        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(widget, event)


def _settings_with_two_microphones(env):
    dialog = env.app.settings_dialog
    dialog.open()
    dialog.microphone.addItem("İkinci mikrofon", "ikinci-mikrofon")
    return dialog


def test_wheel_over_a_box_in_settings_does_not_change_the_setting(env):
    # Pencerede gezinirken tekerlek ayarları sessizce değiştiriyordu (18 Kasım: mikrofon böyle değişti).
    dialog = _settings_with_two_microphones(env)
    microphone, method = env.settings.microphone_id, env.settings.output_method
    _wheel(dialog.microphone)
    _wheel(dialog.output_method)
    assert (env.settings.microphone_id, env.settings.output_method) == (microphone, method)


def test_wheel_over_the_volume_slider_does_not_move_it(env):
    dialog = env.app.settings_dialog
    dialog.open()
    before = dialog.sound_volume.value()
    _wheel(dialog.sound_volume)
    assert dialog.sound_volume.value() == before


def test_wheel_still_works_on_a_box_the_user_selected(env):
    dialog = _settings_with_two_microphones(env)
    dialog.activateWindow()
    QTest.qWaitForWindowActive(dialog, 1000)
    dialog.microphone.setFocus()
    assert dialog.microphone.hasFocus()
    before = env.settings.microphone_id
    _wheel(dialog.microphone)
    assert env.settings.microphone_id != before
