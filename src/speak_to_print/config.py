"""Uygulamanın sabitleri: tek yerde dursun ki modüller arasında tutarsızlık olmasın."""

from __future__ import annotations

SAMPLE_RATE = 16_000  # Whisper 16 kHz mono ses bekler

# Konuşma tanıma (gerekçe: docs/model-karsilastirma.md)
MODEL_NAME = "large-v3"
COMPUTE_TYPE = "float16"
LANGUAGE = "tr"
# Modele verilen örnek metin: noktalama ve büyük harf kullanımını sabitlemeye yardım eder.
STYLE_PROMPT = ("Merhaba, bugün yaptıklarımı not alıyorum. Önce toplantıya katıldım, "
                "sonra e-postaları yanıtladım. Yarın ne yapacağıma henüz karar vermedim.")

# Kayıt
STOP_TAIL_MS = 250  # durdurduktan sonra bu kadar daha kaydet: son hece kesilmesin
MIN_RECORDING_SECONDS = 0.4  # bundan kısa kayıtlar çevrilmez

# Dinleme penceresi. Başlık ve boyut, KWin pencere kuralıyla (kwin_rules.py) eşleşmek zorunda:
# kural pencereyi başlığından tanır ve sol üst köşesini sabitler.
POPUP_TITLE = "Speak to Print — Dinleme"
POPUP_SIZE = (560, 214)
POPUP_BOTTOM_MARGIN = 90  # ekranın altından boşluk (Qt, Wayland'de görev çubuğunun yerini bilmez)
# Düzenleme penceresi: odak alabilen ayrı bir pencere, dinleme penceresinin hemen üstünde durur.
EDITOR_TITLE = "Speak to Print — Düzenle"
EDITOR_SIZE = (560, 250)
EDITOR_GAP = 8  # iki pencere arasındaki boşluk
RESULT_HIDE_SECONDS = 6  # metin yazıldıktan sonra pencerenin kendiliğinden kapanma süresi

SHORTCUT_ID = "dictate"
SHORTCUT_DESCRIPTION = "Dikteyi başlat / durdur"
