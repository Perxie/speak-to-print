import pytest

from speak_to_print.textguard import is_invented, single_line


@pytest.mark.parametrize("text", [
    "Altyazı M.K.", "altyazı m.k", " Altyazı M.K. ", "İzlediğiniz için teşekkür ederim.",
    "İzlediğiniz için teşekkürler!", "ALTYAZI M.K.",
])
def test_known_phrases_are_invented(text):
    assert is_invented(text)


@pytest.mark.parametrize("text", [
    "", "Portakal suyu içtim.", "Yardımın için teşekkür ederim.",
    "Videoyu izlediğiniz için teşekkür ederim, şimdi sorulara geçelim.",
    "Altyazı dosyasını projeye ekledim.", "Hazır içti.",
])
def test_real_sentences_are_kept(text):
    assert not is_invented(text)


from speak_to_print.config import STYLE_PROMPT, build_prompt  # noqa: E402
from speak_to_print.textguard import is_prompt_echo  # noqa: E402

PROMPT = build_prompt(True, ["commit", "refactor"])


def test_build_prompt_combinations():
    assert build_prompt(False, []) == ""
    assert build_prompt(True, []) == STYLE_PROMPT
    assert build_prompt(False, ["commit", "pull request"]) == "Terimler: commit, pull request."
    assert build_prompt(True, ["commit"]).startswith("Terimler: commit. Merhaba")


@pytest.mark.parametrize("text", [
    "Merhaba, bugün ne yapacağıma henüz karar vermedim. Önce toplantıya katıldım, sonra e-postaları yanıtladım.",
    "Terimler: commit, refactor. Merhaba, bugün yaptıklarımı not alıyorum.",
    STYLE_PROMPT,
])
def test_prompt_echo_is_detected(text):
    assert is_prompt_echo(text, PROMPT)


@pytest.mark.parametrize("text", [
    "Kodu commit etmeden önce testleri çalıştırmayı unutma.",
    "Bugün toplantıya katıldım, sonra projeyi GitHub'a yükledim.",
    "Yarın sabah erken kalkıp spora gideceğim, akşam da arkadaşlarımla buluşacağım.",
    "Merhaba, nasılsın?",  # kısa: yankı sayılmaz
    "",
])
def test_real_sentences_are_not_echo(text):
    assert not is_prompt_echo(text, PROMPT)


def test_no_prompt_means_no_echo():
    assert not is_prompt_echo(STYLE_PROMPT, "")


def test_line_breaks_and_tabs_become_single_spaces():
    assert single_line("Bir\nİki\r\n\tÜç Dört") == "Bir İki Üç Dört"


def test_other_control_characters_are_removed():
    assert single_line("a\x1bb\x07c\x00d\x85e") == "a b c d e"


def test_ordinary_dictation_is_unchanged():
    text = "Çığ düştü; İzmir'de ılık, şöyle güzel bir gün. Deploy ettik, pull request açtım."
    assert single_line(text) == text
