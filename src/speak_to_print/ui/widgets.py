"""Tasarıma özgü küçük bileşenler: ses çizgisi, anahtar, kesim işaretli alan ve yuvarlak köşeli zemin."""

from __future__ import annotations

from collections import deque

from PySide6.QtCore import QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QFontMetrics, QPainter, QPainterPath, QPen, QTextBlockFormat, QTextCursor
from PySide6.QtWidgets import QAbstractButton, QSizePolicy, QStyle, QStyledItemDelegate, QTextEdit, QWidget

from . import theme


class PrintedText(QTextEdit):
    """Dizilen metnin alanı: Newsreader ile, satır arası açılmış düz metin.

    QPlainTextEdit satır aralığı ayarlamaya izin vermediği için QTextEdit kullanılır; biçimli
    metin kabul etmez, yani davranışı düz metin kutusuyla aynıdır.
    """

    LINE_HEIGHT = 128  # yüzde

    def __init__(self, read_only: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptRichText(False)
        self.setReadOnly(read_only)
        self.setFrameShape(QTextEdit.Shape.NoFrame)
        self.setFont(theme.text_font(17))
        self._apply_leading()

    def setPlainText(self, text: str) -> None:  # noqa: N802 — Qt'nin yöntem adı
        super().setPlainText(text)
        self._apply_leading()

    def clear(self) -> None:
        super().clear()
        self._apply_leading()

    def _apply_leading(self) -> None:
        """Bütün paragraflara satır aralığını uygular (yeni yazılan paragraflar bunu devralır)."""
        block_format = QTextBlockFormat()
        block_format.setLineHeight(self.LINE_HEIGHT, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
        was_blocked = self.blockSignals(True)  # biçim değişikliği "metin değişti" sayılmasın
        cursor = QTextCursor(self.document())
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.mergeBlockFormat(block_format)
        self.blockSignals(was_blocked)


class Waveform(QWidget):
    """Ses çizgisi: konuşurken sağdan sola akan, taban çizgisine oturmuş dikey çizgiler.

    Yalnızca sesi gösterir; ses yokken hareket etmez. Zamanlayıcı pencere gizliyken durur.
    """

    BAR = 3  # çizgi kalınlığı
    GAP = 3  # çizgiler arası boşluk
    TICK_MS = 55  # yeni çizginin eklenme aralığı

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(56)
        self._levels: deque[float] = deque(maxlen=400)
        self._pending = 0.0
        self._mode = "idle"  # "live" | "paused" | "idle"
        self._color = theme.MAGENTA
        self._timer = QTimer(self)
        self._timer.setInterval(self.TICK_MS)
        self._timer.timeout.connect(self._tick)

    def set_mode(self, mode: str) -> None:
        """"live": akar; "paused": olduğu yerde soluk durur; "processing": durur ve sonuç rengine döner.

        Başlangıç durumu "idle"dır (henüz dinlenmedi: yalnızca taban çizgisi).
        """
        self._mode = mode
        if mode == "live" and self.isVisible():
            self._timer.start()
        else:
            self._timer.stop()
        self.update()

    def clear(self) -> None:
        self._levels.clear()
        self._pending = 0.0
        self.update()

    def push(self, level: float) -> None:
        """Mikrofondan gelen son seviyeyi (0..1) bildirir; çizgiye bir sonraki adımda eklenir."""
        self._pending = max(self._pending, level)

    def _tick(self) -> None:
        # Konuşma seviyeleri küçük sayılardır; görünür olsun diye karekök alınır.
        self._levels.append(min(1.0, self._pending ** 0.5))
        self._pending = 0.0
        self.update()

    def showEvent(self, event) -> None:  # noqa: N802 — Qt'nin yöntem adı
        if self._mode == "live":
            self._timer.start()
        super().showEvent(event)

    def hideEvent(self, event) -> None:  # noqa: N802
        self._timer.stop()
        super().hideEvent(event)

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width, height = self.width(), self.height()
        middle = height / 2
        # Taban çizgisi: metin dizildiğinde üzerine oturacağı çizgi.
        painter.setPen(QPen(theme.color(theme.RULE), 1))
        painter.drawLine(0, int(middle), width, int(middle))
        if not self._levels:
            return
        base = {"paused": theme.LEAD, "processing": theme.CYAN}.get(self._mode, self._color)
        step = self.BAR + self.GAP
        capacity = width // step
        painter.setPen(Qt.PenStyle.NoPen)
        for index, level in enumerate(reversed(self._levels)):
            if index >= capacity:
                break
            x = width - (index + 1) * step
            half = max(1.5, level * (height / 2 - 3))
            # Eskidikçe solar: sağdaki yeni ses belirgin, soldaki geçmiş silik.
            painter.setBrush(theme.color(base, 1.0 - 0.75 * index / max(1, capacity)))
            painter.drawRoundedRect(QRectF(x, middle - half, self.BAR, half * 2), 1.5, 1.5)


class Switch(QAbstractButton):
    """Aç/kapa anahtarı (etiketiyle birlikte). QCheckBox gibi kullanılır: isChecked, setChecked, toggled."""

    TRACK = QSize(30, 16)

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(theme.ui_font(13, 500))

    def sizeHint(self) -> QSize:  # noqa: N802
        metrics = self.fontMetrics()
        return QSize(self.TRACK.width() + 8 + metrics.horizontalAdvance(self.text()) + 2,
                     max(self.TRACK.height(), metrics.height()) + 6)

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        track = QRectF(0, (self.height() - self.TRACK.height()) / 2, self.TRACK.width(), self.TRACK.height())
        on = self.isChecked()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(theme.color(theme.CYAN if on else theme.RULE))
        painter.drawRoundedRect(track, track.height() / 2, track.height() / 2)
        knob = track.height() - 4
        x = track.right() - knob - 2 if on else track.left() + 2
        painter.setBrush(theme.color(theme.INK if on else theme.LEAD))
        painter.drawEllipse(QRectF(x, track.top() + 2, knob, knob))
        painter.setPen(theme.color(theme.PAPER if on else theme.LEAD))
        painter.setFont(self.font())
        painter.drawText(QRectF(track.right() + 8, 0, self.width(), self.height()),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())


class CropFrame(QWidget):
    """İçeriğinin köşelerine kesim işaretleri çizen alan: "basılan" metnin durduğu yer.

    Kutu çizmek yerine, matbaa provalarındaki gibi yalnızca köşeler işaretlenir.
    """

    MARK = 9  # işaretin kol uzunluğu
    INSET = 1  # kenardan içeri pay: kesirli ekran ölçeğinde (%150) kenardaki çizgi kırpılabiliyor

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = theme.RULE

    def set_mark_color(self, hex_value: str) -> None:
        self._color = hex_value
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setPen(QPen(theme.color(self._color), 1))
        left, top = self.INSET, self.INSET
        right, bottom = self.width() - 1 - self.INSET, self.height() - 1 - self.INSET
        m = self.MARK
        for x, y, dx, dy in ((left, top, 1, 1), (right, top, -1, 1), (left, bottom, 1, -1), (right, bottom, -1, -1)):
            painter.drawLine(x, y, x + dx * m, y)
            painter.drawLine(x, y, x, y + dy * m)


class Card(QWidget):
    """Çerçevesiz küçük pencerelerin zemini: mürekkep rengi, ince kenarlıklı, yuvarlak köşeli."""

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = theme.RADIUS if theme.ROUNDED_WINDOWS else 0
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        painter.fillPath(path, theme.color(theme.INK))
        painter.setPen(QPen(theme.color(theme.RULE), 1))
        painter.drawPath(path)


class Keycap(QWidget):
    """Klavye tuşu görünümünde küçük etiket (kısayolu göstermek için)."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._text = text
        self._muted = False
        self.setFont(theme.ui_font(12, 600))
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def set_text(self, text: str, muted: bool = False) -> None:
        self._text, self._muted = text, muted
        self.updateGeometry()
        self.update()

    def text(self) -> str:
        return self._text

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self.fontMetrics().horizontalAdvance(self._text) + 18, 24)

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -1.5)
        painter.setPen(QPen(theme.color(theme.RULE), 1))
        painter.setBrush(theme.color(theme.LAYER))
        painter.drawRoundedRect(rect, 5, 5)
        # Tuşun alt kenarı biraz kalın: basılabilir bir tuş hissi.
        painter.drawLine(int(rect.left() + 5), int(rect.bottom() + 1), int(rect.right() - 5), int(rect.bottom() + 1))
        painter.setPen(theme.color(theme.LEAD if self._muted else theme.PAPER))
        painter.setFont(self.font())
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._text)


class Rule(QWidget):
    """Bölümleri ayıran ince yatay çizgi."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(1)

    def paintEvent(self, _event) -> None:  # noqa: N802
        QPainter(self).fillRect(self.rect(), theme.color(theme.RULE))


class HistoryDelegate(QStyledItemDelegate):
    """Geçmiş listesinin satırı: solda saat (arayüz yazısı), sağda metin (dizgi yazısı), tek satır.

    Seçili satır bir kat açık zeminle ve solunda camgöbeği bir çizgiyle gösterilir.
    """

    ROW_HEIGHT = 36
    TIME_WIDTH = 92

    def sizeHint(self, option, index) -> QSize:  # noqa: N802
        return QSize(option.rect.width(), self.ROW_HEIGHT)

    def paint(self, painter: QPainter, option, index) -> None:
        entry = index.data(Qt.ItemDataRole.UserRole)
        rect = QRectF(option.rect)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        if selected or hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(theme.color(theme.LAYER, 1.0 if selected else 0.55))
            painter.drawRoundedRect(rect.adjusted(0, 1, 0, -1), 6, 6)
        if selected:
            painter.setBrush(theme.color(theme.CYAN))
            painter.drawRoundedRect(QRectF(rect.left(), rect.top() + 8, 3, rect.height() - 16), 1.5, 1.5)
        if entry is not None:
            painter.setFont(theme.ui_font(12, 500))
            painter.setPen(theme.color(theme.LEAD))
            painter.drawText(QRectF(rect.left() + 14, rect.top(), self.TIME_WIDTH, rect.height()),
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                             f"{entry.created_at:%d.%m  %H:%M}")
            font = theme.text_font(15)
            painter.setFont(font)
            painter.setPen(theme.color(theme.PAPER))
            text_rect = QRectF(rect.left() + 14 + self.TIME_WIDTH, rect.top(), rect.width() - self.TIME_WIDTH - 26, rect.height())
            text = " ".join(entry.text.split())
            elided = QFontMetrics(font).elidedText(text, Qt.TextElideMode.ElideRight, int(text_rect.width()))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided)
        painter.restore()
