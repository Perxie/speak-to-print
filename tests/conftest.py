import os

import pytest

# Testlerde ekran gerekmesin diye Qt'yi ekransız kipte çalıştır.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session", autouse=True)
def qt_app():
    from PySide6.QtCore import QCoreApplication

    return QCoreApplication.instance() or QCoreApplication([])
