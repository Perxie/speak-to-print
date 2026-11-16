"""Metni imlecin olduğu yere yazan yöntemler.

  kwin_type        : KWin'in EIS arayüzüyle metni doğrudan karakter olarak gönderir.
  clipboard_paste  : metni panoya koyar ve yapıştırma tuşuna basar.
"""


class OutputError(RuntimeError):
    """Metin hedef pencereye yazılamadı."""
