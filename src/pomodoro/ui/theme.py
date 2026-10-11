"""Colors, fonts and sizes. Warm cream, clay and sage; serif numerals."""

from pathlib import Path

from PySide6.QtGui import QColor, QFont, QFontDatabase

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

CREAM = QColor("#F5F1E8")
INK = QColor("#1F1E1C")
MUTED = QColor("#7D776C")
BORDER = QColor("#E3DCCB")
TRACK = QColor("#E9E2D3")
CLAY = QColor("#CC785C")
CLAY_DARK = QColor("#B8664B")
SAGE = QColor("#7A9A82")
SAGE_DARK = QColor("#66866E")
HOVER = QColor(31, 30, 28, 14)

PILL_SIZE = (128, 34)
CARD_SIZE = (348, 180)
SHADOW = 10           # transparent margin around the content for the soft shadow
REST_OPACITY = 0.78

_families = {"serif": "Serif", "sans": "Sans"}


def load_fonts() -> None:
    for key, file in (("serif", "SourceSerif4-Variable.ttf"), ("sans", "Inter-Variable.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(FONTS_DIR / file))
        families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
        if families:
            _families[key] = families[0]


def font(kind: str, px: float, weight: int = 400, spacing: float = 0.0) -> QFont:
    f = QFont(_families[kind])
    f.setPixelSize(round(px))
    f.setWeight(QFont.Weight(weight))
    if hasattr(f, "setVariableAxis"):     # Qt >= 6.7: drive the variable font axes directly
        f.setVariableAxis(QFont.Tag("wght"), float(weight))
        if kind == "serif":
            f.setVariableAxis(QFont.Tag("opsz"), float(min(60, max(8, px * 0.75))))
    if spacing:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return f


def accent(break_phase: bool) -> QColor:
    return SAGE if break_phase else CLAY


def accent_dark(break_phase: bool) -> QColor:
    return SAGE_DARK if break_phase else CLAY_DARK
