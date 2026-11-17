import os

import pytest

# Testlerde ekran gerekmesin diye Qt'yi ekransız kipte çalıştır.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session", autouse=True)
def qt_app():
    # Arayüz testleri pencere bileşenleri oluşturduğu için QApplication gerekir.
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])
