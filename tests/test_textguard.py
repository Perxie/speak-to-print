import pytest

from speak_to_print.textguard import is_invented


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
