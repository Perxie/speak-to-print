from PySide6.QtCore import QSettings

from speak_to_print.settings import Settings


def make(tmp_path):
    return Settings(store=QSettings(str(tmp_path / "s.conf"), QSettings.Format.IniFormat))


def test_defaults(tmp_path):
    s = make(tmp_path)
    assert s.auto_paste and s.use_prompt and s.keep_history and s.sounds
    assert s.hotkey_mode == "toggle" and s.output_method == "auto"
    assert s.microphone_id == "" and s.vocabulary == []


def test_values_survive_reload_and_emit_changed(tmp_path):
    s = make(tmp_path)
    changes = []
    s.changed.connect(lambda: changes.append(1))
    s.auto_paste = False
    s.hotkey_mode = "hold"
    s.output_method = "clipboard"
    s.microphone_id = "alsa_input.usb-test"
    s.keep_history = False
    s.vocabulary = ["commit", " pull request ", "", "İzmir"]
    assert len(changes) == 6
    again = make(tmp_path)
    assert not again.auto_paste and not again.keep_history
    assert again.hotkey_mode == "hold" and again.output_method == "clipboard"
    assert again.microphone_id == "alsa_input.usb-test"
    assert again.vocabulary == ["commit", "pull request", "İzmir"]


def test_same_value_does_not_emit_and_invalid_is_ignored(tmp_path):
    s = make(tmp_path)
    changes = []
    s.changed.connect(lambda: changes.append(1))
    s.auto_paste = True
    s.hotkey_mode = "toggle"
    s.hotkey_mode = "olmayan-kip"
    s.output_method = "bilinmeyen"
    s.vocabulary = []
    assert changes == [] and s.hotkey_mode == "toggle" and s.output_method == "auto"


def test_sounds_setting_persists(tmp_path):
    s = make(tmp_path)
    s.sounds = False
    assert make(tmp_path).sounds is False


def test_sound_volume_is_clamped_and_persists(tmp_path):
    s = make(tmp_path)
    assert s.sound_volume == 50
    s.sound_volume = 250
    assert s.sound_volume == 100
    s.sound_volume = 20
    assert make(tmp_path).sound_volume == 20


def test_vocabulary_text_is_split_into_terms_in_one_place():
    from speak_to_print.settings import parse_terms

    assert parse_terms("  commit \n\n pull request\n ") == ["commit", "pull request"]
