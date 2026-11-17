"""Sistem tepsisi simgesi: durumu renkle gösterir, yalnızca uygulama açıkken görünür."""

from __future__ import annotations

from PySide6.QtCore import QObject, QRectF, Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from ..controller import State
from ..desktop_entry import APP_NAME
from . import theme

COLORS = {
    State.LOADING: theme.LEAD,
    State.IDLE: theme.PAPER,
    State.LISTENING: theme.MAGENTA,
    State.PAUSED: theme.LEAD,
    State.TRANSCRIBING: theme.CYAN,
    State.FAILED: theme.RED,
}

# Uygulamanın işareti: ses çizgisinden beş çizgi (x, yükseklik); 64×64'lük bir karede.
BARS = ((10, 12), (20, 28), (30, 42), (40, 22), (50, 10))


def state_icon(state: State) -> QIcon:
    """Durum rengine boyanmış ses çizgisi simgesi (simge temasına bağlı kalmamak için kodla çizilir)."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(COLORS[state]))
    for x, height in BARS:
        painter.drawRoundedRect(QRectF(x - 1, 32 - height / 2, 8, height), 4, 4)
    painter.end()
    return QIcon(pixmap)


class Tray(QObject):
    show_window_clicked = Signal()
    listen_clicked = Signal()
    quit_clicked = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._icon = QSystemTrayIcon(state_icon(State.LOADING), self)
        self._menu = QMenu()
        self._listen_action = QAction("Dinlemeyi başlat", self._menu)
        self._listen_action.triggered.connect(self.listen_clicked)
        self._menu.addAction(self._listen_action)
        show_action = QAction("Pencereyi göster", self._menu)
        quit_action = QAction("Çık", self._menu)
        show_action.triggered.connect(self.show_window_clicked)
        quit_action.triggered.connect(self.quit_clicked)
        self._menu.addAction(show_action)
        self._menu.addAction(quit_action)
        self._icon.setContextMenu(self._menu)
        self._icon.activated.connect(self._on_activated)
        self.set_state(State.LOADING)
        self._icon.show()

    def set_state(self, state: State) -> None:
        self._icon.setIcon(state_icon(state))
        self._icon.setToolTip(f"{APP_NAME}: {state.value}")
        self._listen_action.setText("Bitir" if state in (State.LISTENING, State.PAUSED) else "Dinlemeyi başlat")
        self._listen_action.setEnabled(state in (State.IDLE, State.LISTENING, State.PAUSED))

    def hide(self) -> None:
        self._icon.hide()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:  # sol tık
            self.show_window_clicked.emit()
