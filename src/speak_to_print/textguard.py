"""Uydurma metne karşı önlem.

Whisper, kısık ya da uzak seste eğitim verisinden kalma altyazı kalıpları
uydurabiliyor ("Altyazı M.K.", "İzlediğiniz için teşekkür ederim."). Modelin
güven değerleri bunları gerçek cümlelerden ayırmıyor (docs/model-karsilastirma.md),
bu yüzden bilinen kalıpların listesine bakıyoruz.

Kural bilerek dar: yalnızca çıktının TAMAMI bilinen bir kalıpsa alıkonur. Bir
cümlenin içinde geçen "teşekkür ederim" gerçek konuşma olabilir, ona dokunulmaz.

`single_line` ise model çıktısını imlece yazılmadan önce tek satıra indirir:
satır sonu, terminal odaktayken Enter gibi davranıp satırı çalıştırabilirdi.
"""

from __future__ import annotations

import re

KNOWN_PHRASES = (
    "altyazı m.k.",
    "altyazı mk",
    "izlediğiniz için teşekkür ederim",
    "izlediğiniz için teşekkürler",
    "izlediğiniz için teşekkür ederiz",
    "bir sonraki videoda görüşmek üzere",
    "abone olmayı unutmayın",
)


# Denetim karakterleri (C0, DEL, C1) ve Unicode satır/paragraf ayırıcıları.
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]")


def single_line(text: str) -> str:
    """Satır sonu, sekme ve diğer denetim karakterlerini boşluğa çevirir; boşlukları teke indirir."""
    return " ".join(_CONTROL.sub(" ", text).split())


def _normalize(text: str) -> str:
    text = text.replace("İ", "i").replace("I", "ı").lower()
    return " ".join(re.sub(r"[^\w\s]", "", text).split())


_KNOWN = {_normalize(phrase) for phrase in KNOWN_PHRASES}


def is_prompt_echo(text: str, prompt: str) -> bool:
    """Model, kendisine verilen ipucu metnini mi geri söylüyor?

    Kısık seste Whisper bazen ipucundaki cümleleri (karıştırarak) çıktı diye
    verir. Çıktıdaki kelimelerin neredeyse tamamı ipucunda geçiyorsa bunu
    yankı sayarız. Kısa çıktılar (5 kelimeden az) bu yolla değerlendirilmez;
    gerçek bir cümle ipucuyla birkaç kelimeyi tesadüfen paylaşabilir.
    """
    words = _normalize(text).split()
    if len(words) < 5 or not prompt:
        return False
    known = set(_normalize(prompt).split())
    return sum(word in known for word in words) / len(words) >= 0.9


def is_invented(text: str) -> bool:
    """Metnin tamamı bilinen bir uydurma kalıbı mı?"""
    normalized = _normalize(text)
    return bool(normalized) and normalized in _KNOWN
