import os

import pytest

# Testlerde ekran gerekmesin diye Qt'yi ekransız kipte çalıştır.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session", autouse=True)
def qt_app():
    # Arayüz testleri pencere bileşenleri oluşturduğu için QApplication gerekir.
    from PySide6.QtWidgets import QApplication

    from speak_to_print.ui import theme

    app = QApplication.instance() or QApplication([])
    # Gerçek uygulama gibi temayla: stil sayfası bazı bileşenlerin yazı tipini gösterilirken
    # değiştiriyor (ör. yer tutucunun italiği); temasız testler bunu göremez.
    theme.apply(app)
    return app
