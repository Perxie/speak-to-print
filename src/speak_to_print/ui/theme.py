"""Görsel dil: renkler, yazı tipleri ve ortak stil (ayrıntı ve gerekçe: docs/tasarim.md).

Fikir matbaadan geliyor: mürekkep rengi zemin, kâğıt rengi metin ve durum bilgisi
taşıyan üç baskı rengi (macenta: canlı ses, camgöbeği: sonuç, sarı: ana eylem).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication, QPushButton, QWidget

# ------------------------------------------------------------ renkler
INK = "#141B27"  # Mürekkep: pencere zemini
LAYER = "#1D2635"  # Tabaka: bir kat yukarıdaki yüzeyler
RULE = "#2D394C"  # Cetvel: ince çizgiler, kenarlıklar
PAPER = "#EEF1F5"  # Kâğıt: ana metin
LEAD = "#8E9BB0"  # Kurşun: ikincil metin
MAGENTA = "#F2559B"  # canlı ses
CYAN = "#3CC8E6"  # sonuç ve işlem
YELLOW = "#FFD257"  # ana eylem
RED = "#F2705A"  # sorun (baskıda macenta + sarının üst üste gelmesi)

RADIUS = 12  # pencere köşeleri
# Küçük pencereler yuvarlak köşeli ve saydam zeminli çizilir. Bir masaüstünde köşeler
# bozuk görünürse bunu False yapmak yeter: pencereler düz köşeli ve opak olur.
ROUNDED_WINDOWS = True

_FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
_UI_FAMILY = "Instrument Sans"
_TEXT_FAMILY = "Newsreader"
_loaded = False


def load_fonts() -> None:
    """Uygulamayla gelen yazı tiplerini yükler; bulunamazsa sistemdeki Noto ailesine düşülür."""
    global _loaded, _UI_FAMILY, _TEXT_FAMILY
    if _loaded:
        return
    _loaded = True
    for name in ("InstrumentSans.ttf", "Newsreader.ttf", "Newsreader-Italic.ttf"):
        QFontDatabase.addApplicationFont(str(_FONT_DIR / name))
    families = set(QFontDatabase.families())
    if _UI_FAMILY not in families:
        _UI_FAMILY = "Noto Sans"
    if _TEXT_FAMILY not in families:
        _TEXT_FAMILY = "Noto Serif"


def _font(family: str, pixels: int, weight: int, italic: bool = False) -> QFont:
    font = QFont(family)
    font.setPixelSize(pixels)
    font.setItalic(italic)
    # Bu yazı tipleri "değişken": ağırlık bir eksen olarak verilir. setWeight tek başına
    # ara ağırlıkları (500, 600) üretmiyor, bu yüzden ikisi birlikte ayarlanır.
    font.setWeight(QFont.Weight(weight))
    font.setVariableAxis(QFont.Tag("wght"), float(weight))
    return font


def ui_font(pixels: int = 13, weight: int = 500) -> QFont:
    """Arayüzün yazı tipi (Instrument Sans): düğmeler, etiketler, durum, sayılar."""
    load_fonts()
    font = _font(_UI_FAMILY, pixels, weight)
    font.setFeature(QFont.Tag("tnum"), 1)  # eşit genişlikli rakamlar: süre sayacı oynamasın
    return font


def text_font(pixels: int = 17, weight: int = 400, italic: bool = False) -> QFont:
    """Dizilen metnin yazı tipi (Newsreader): kullanıcının söylediği her şey."""
    load_fonts()
    return _font(_TEXT_FAMILY, pixels, weight, italic)


def set_kind(button: QPushButton, kind: str) -> None:
    """Düğmenin türünü değiştirir: "primary" (sarı, ana eylem), "quiet" (çerçevesiz) ya da "" (olağan)."""
    if button.property("kind") != kind:
        button.setProperty("kind", kind)
        button.style().unpolish(button)
        button.style().polish(button)


def color(hex_value: str, alpha: float = 1.0) -> QColor:
    result = QColor(hex_value)
    result.setAlphaF(alpha)
    return result


STYLE = f"""
QWidget {{ color: {PAPER}; }}
QToolTip {{ background: {LAYER}; color: {PAPER}; border: 1px solid {RULE}; padding: 5px 8px; }}

QPushButton {{
    background: transparent; color: {PAPER};
    border: 1px solid {RULE}; border-radius: 7px; padding: 6px 14px;
}}
QPushButton:hover {{ border-color: {LEAD}; }}
QPushButton:pressed {{ background: {LAYER}; }}
QPushButton:disabled {{ color: #56627A; border-color: #232D3D; }}
QPushButton[kind="primary"] {{ background: {YELLOW}; color: {INK}; border: 1px solid {YELLOW}; }}
QPushButton[kind="primary"]:hover {{ background: #FFDF85; border-color: #FFDF85; }}
QPushButton[kind="primary"]:pressed {{ background: #E9BB3F; border-color: #E9BB3F; }}
QPushButton[kind="primary"]:disabled {{ background: #5A5236; color: {INK}; border-color: #5A5236; }}
QPushButton[kind="quiet"] {{ border-color: transparent; color: {LEAD}; padding: 6px 10px; }}
QPushButton[kind="quiet"]:hover {{ color: {PAPER}; border-color: transparent; }}
QPushButton[kind="quiet"]:disabled {{ color: #56627A; }}

QPlainTextEdit, QTextEdit, QLineEdit {{
    background: transparent; color: {PAPER}; border: none;
    selection-background-color: {CYAN}; selection-color: {INK};
}}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px 0; }}
QScrollBar::handle:vertical {{ background: {RULE}; border-radius: 3px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: {LEAD}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{ height: 0; }}

QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ border: none; }}

QComboBox {{
    background: {LAYER}; color: {PAPER}; border: 1px solid {RULE}; border-radius: 7px; padding: 6px 10px;
}}
QComboBox:hover {{ border-color: {LEAD}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {LAYER}; color: {PAPER}; border: 1px solid {RULE}; outline: none;
    selection-background-color: {RULE}; selection-color: {PAPER};
}}

QRadioButton {{ spacing: 8px; color: {PAPER}; }}
QRadioButton::indicator {{
    width: 14px; height: 14px; border-radius: 8px; border: 1.5px solid {LEAD}; background: transparent;
}}
QRadioButton::indicator:checked {{ border: 4.5px solid {CYAN}; background: {INK}; width: 8px; height: 8px; }}

QSlider::groove:horizontal {{ height: 4px; border-radius: 2px; background: {RULE}; }}
QSlider::sub-page:horizontal {{ height: 4px; border-radius: 2px; background: {CYAN}; }}
QSlider::handle:horizontal {{ width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; background: {PAPER}; }}

QMessageBox {{ background: {INK}; }}

QMenu {{ background: {LAYER}; border: 1px solid {RULE}; padding: 5px; }}
QMenu::item {{ padding: 6px 22px 6px 12px; border-radius: 5px; }}
QMenu::item:selected {{ background: {RULE}; }}
QMenu::item:disabled {{ color: #56627A; }}
"""


def apply(app: QApplication) -> None:
    """Uygulamanın tamamına koyu paleti, temel yazı tipini ve ortak stili uygular."""
    load_fonts()
    app.setStyle("Fusion")
    palette = QPalette()
    roles = {
        QPalette.ColorRole.Window: INK, QPalette.ColorRole.Base: INK, QPalette.ColorRole.AlternateBase: LAYER,
        QPalette.ColorRole.Button: LAYER, QPalette.ColorRole.ToolTipBase: LAYER,
        QPalette.ColorRole.WindowText: PAPER, QPalette.ColorRole.Text: PAPER, QPalette.ColorRole.ButtonText: PAPER,
        QPalette.ColorRole.ToolTipText: PAPER, QPalette.ColorRole.BrightText: PAPER,
        QPalette.ColorRole.PlaceholderText: LEAD, QPalette.ColorRole.Highlight: CYAN,
        QPalette.ColorRole.HighlightedText: INK, QPalette.ColorRole.Link: CYAN,
        QPalette.ColorRole.Mid: RULE, QPalette.ColorRole.Dark: INK, QPalette.ColorRole.Shadow: "#000000",
    }
    for role, value in roles.items():
        palette.setColor(role, QColor(value))
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor("#56627A"))
    app.setPalette(palette)
    app.setFont(ui_font(13, 500))
    app.setStyleSheet(STYLE)


def prepare_frameless(window: QWidget) -> None:
    """Çerçevesiz küçük pencereyi yuvarlak köşe çizimine hazırlar (zemini pencerenin kendisi boyar)."""
    from PySide6.QtCore import Qt

    if ROUNDED_WINDOWS:
        window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
