from speak_to_print.audio import choose_microphone

MICS = {"usb": "USB mikrofon", "bt": "Kulaklık"}


def test_empty_preference_uses_system_default():
    assert choose_microphone("", MICS, "Kulaklık") == ("Kulaklık", False)


def test_preferred_microphone_is_used_when_connected():
    assert choose_microphone("usb", MICS, "Kulaklık") == ("USB mikrofon", False)


def test_missing_preferred_microphone_falls_back_to_default():
    assert choose_microphone("yok", MICS, "Kulaklık") == ("Kulaklık", True)


def test_no_microphone_at_all():
    assert choose_microphone("", {}, None) == (None, False)
    assert choose_microphone("usb", {}, None) == (None, True)
