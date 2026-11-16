"""Sistem tepsisi simgesi: durumu renkle gösterir, yalnızca uygulama açıkken görünür."""

from __future__ import annotations

from PySide6.QtCore import QObject, QRectF, Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from ..controller import State
from ..desktop_entry import APP_NAME

COLORS = {
    State.LOADING: "#7f8c8d",
    State.IDLE: "#eff0f1",
    State.LISTENING: "#ed1515",
    State.PAUSED: "#f39c12",
    State.TRANSCRIBING: "#3daee9",
    State.FAILED: "#7f8c8d",
}


def state_icon(state: State) -> QIcon:
    """Durum rengine boyanmış basit bir mikrofon simgesi çizer (simge temasına bağlı kalmamak için)."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    color = QColor(COLORS[state])
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawRoundedRect(QRectF(22, 6, 20, 34), 10, 10)  # mikrofonun gövdesi
    pen = painter.pen()
    pen.setStyle(Qt.PenStyle.SolidLine)
    pen.setColor(color)
    pen.setWidth(5)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawArc(QRectF(13, 14, 38, 34), 180 * 16, 180 * 16)  # alttaki yay
    painter.drawLine(32, 48, 32, 58)  # sap
    painter.drawLine(22, 58, 42, 58)  # taban
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
