"""Uydurma metne karşı önlem.

Whisper, kısık ya da uzak seste eğitim verisinden kalma altyazı kalıpları
uydurabiliyor ("Altyazı M.K.", "İzlediğiniz için teşekkür ederim."). Modelin
güven değerleri bunları gerçek cümlelerden ayırmıyor (docs/model-karsilastirma.md),
bu yüzden bilinen kalıpların listesine bakıyoruz.

Kural bilerek dar: yalnızca çıktının TAMAMI bilinen bir kalıpsa alıkonur. Bir
cümlenin içinde geçen "teşekkür ederim" gerçek konuşma olabilir, ona dokunulmaz.
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
