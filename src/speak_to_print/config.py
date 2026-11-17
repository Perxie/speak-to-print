"""Uygulamanın sabitleri: tek yerde dursun ki modüller arasında tutarsızlık olmasın."""

from __future__ import annotations

SAMPLE_RATE = 16_000  # Whisper 16 kHz mono ses bekler

# Konuşma tanıma (gerekçe: docs/model-karsilastirma.md)
MODEL_NAME = "large-v3"
# Hugging Face'teki Systran/faster-whisper-large-v3 deposunun denenmiş commit'i. Yeni
# kurulumda bu sürüm iner; depo sonradan değişse ya da ele geçirilse de aynı model
# gelir. Güncellemek için: yeni commit'i denedikten sonra bu kimliği değiştir.
MODEL_REVISION = "edaa852ec7e145841d8ffdb056a99866b5f0a478"
COMPUTE_TYPE = "float16"
LANGUAGE = "tr"
# Modele verilen örnek metin: noktalama ve büyük harf kullanımını sabitlemeye yardım eder.
STYLE_PROMPT = ("Merhaba, bugün yaptıklarımı not alıyorum. Önce toplantıya katıldım, "
                "sonra e-postaları yanıtladım. Yarın ne yapacağıma henüz karar vermedim.")
# Sözlükteki terimler ipucunun başına bu kalıpla eklenir. Faz 3'te ölçüldü: bu yol "commit" ve
# "refactor"ı düzeltti (31/31 terim), `hotwords` parametresi ise düzeltmedi; uzun listede etki kayboluyor.
VOCABULARY_PREFIX = "Terimler: {terms}. "


def build_prompt(use_prompt: bool, vocabulary: list[str]) -> str:
    """Modele verilecek ipucu metni: önce sözlük terimleri, sonra noktalama örneği."""
    parts = []
    if vocabulary:
        parts.append(VOCABULARY_PREFIX.format(terms=", ".join(vocabulary)))
    if use_prompt:
        parts.append(STYLE_PROMPT)
    return "".join(parts).strip()

# Kayıt
STOP_TAIL_MS = 250  # durdurduktan sonra bu kadar daha kaydet: son hece kesilmesin
MIN_RECORDING_SECONDS = 0.4  # bundan kısa kayıtlar çevrilmez
# Kayıt bu süreye ulaşınca dinleme kendiliğinden bitirilir ve çevrilir: açık unutulan bir dinleme
# odadaki konuşmaları saatlerce toplayıp sonunda o an öndeki pencereye yazmasın.
MAX_RECORDING_SECONDS = 10 * 60

# Dinleme penceresi. Başlık ve boyut, KWin pencere kuralıyla (kwin_rules.py) eşleşmek zorunda:
# kural pencereyi başlığından tanır ve sol üst köşesini sabitler.
POPUP_TITLE = "Speak to Print — Dinleme"
POPUP_SIZE = (620, 196)
POPUP_BOTTOM_MARGIN = 90  # ekranın altından boşluk (Qt, Wayland'de görev çubuğunun yerini bilmez)
# Düzenleme penceresi: odak alabilen ayrı bir pencere, dinleme penceresinin hemen üstünde durur.
EDITOR_TITLE = "Speak to Print — Düzenle"
EDITOR_SIZE = (620, 250)
EDITOR_GAP = 8  # iki pencere arasındaki boşluk
RESULT_HIDE_SECONDS = 6  # metin yazıldıktan sonra pencerenin kendiliğinden kapanma süresi

SHORTCUT_ID = "dictate"
SHORTCUT_DESCRIPTION = "Dikteyi başlat / durdur"
