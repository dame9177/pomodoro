"""The single floating window: a quiet pill that opens into a card.

Everything is painted by hand. The window is resized while it animates, so in the
collapsed state it only covers the pill (plus a thin shadow margin) and never
swallows clicks meant for whatever is underneath.
"""

import math
from datetime import datetime, timedelta

from PySide6.QtCore import QEasingCurve, QPoint, QPointF, QRectF, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFontMetricsF, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QMenu, QWidget

from .. import placement
from ..placement import Rect
from ..timer import Phase
from . import theme

AWAITING = (Phase.AWAITING_BREAK, Phase.AWAITING_FOCUS)
DRAG_THRESHOLD = 4
AUTO_COLLAPSE_MS = 6000

MENU_STYLE = """
QMenu { background: #F5F1E8; color: #1F1E1C; border: 1px solid #E3DCCB;
        border-radius: 10px; padding: 6px; }
QMenu::item { padding: 6px 18px; border-radius: 6px; }
QMenu::item:selected { background: #EAE3D4; }
"""


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _with_alpha(color: QColor, alpha: float) -> QColor:
    c = QColor(color)
    c.setAlphaF(c.alphaF() * _clamp01(alpha))
    return c


def _mmss(seconds: float) -> str:
    s = max(0, math.ceil(seconds))
    return f"{s // 60:02d}:{s % 60:02d}"


class PomodoroWindow(QWidget):
    start_requested = Signal()
    toggle_requested = Signal()
    restart_requested = Signal()
    skip_requested = Signal()
    quit_requested = Signal()
    moved = Signal(object)          # (x, y) of the pill, or None when reset to default

    def __init__(self, focus_seconds: float, break_seconds: float):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setWindowTitle("Pomodoro")

        self.focus_seconds = focus_seconds
        self.break_seconds = break_seconds
        self.phase = Phase.IDLE
        self.paused = False
        self.remaining = float(focus_seconds)
        self.progress = 0.0
        self.today_count = 0
        self.today_minutes = 0

        self.expansion = 0.0
        self._target = 0.0
        self._pill_pos = QPoint(0, 0)
        self._hovered = False
        self._hover_button: str | None = None
        self._buttons: dict[str, QRectF] = {}
        self._press: QPoint | None = None
        self._press_pill = QPoint()
        self._dragging = False
        self._pulse = 0.0

        self._anim = QVariantAnimation(self, duration=220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._set_expansion)

        self._pulse_anim = QVariantAnimation(self, startValue=0.0, endValue=1.0,
                                             duration=2000, loopCount=-1)
        self._pulse_anim.valueChanged.connect(self._on_pulse)

        self._collapse_timer = QTimer(self, singleShot=True, interval=AUTO_COLLAPSE_MS)
        self._collapse_timer.timeout.connect(self._auto_collapse)

        self.setWindowOpacity(theme.REST_OPACITY)

    # ------------------------------------------------------------------ public API

    def set_state(self, phase: Phase, paused: bool, remaining: float, progress: float,
                  today_count: int, today_minutes: int) -> None:
        self.phase, self.paused = phase, paused
        self.remaining, self.progress = remaining, progress
        self.today_count, self.today_minutes = today_count, today_minutes
        self._update_pulse()
        self._update_opacity()
        self.update()

    def place(self, pos: tuple[int, int] | None) -> None:
        """Put the pill at a saved position, or top-center when missing/off-screen."""
        primary = QGuiApplication.primaryScreen().availableGeometry()
        x, y = placement.choose_position(pos, theme.PILL_SIZE, self._areas(), self._rect(primary))
        self._pill_pos = QPoint(x, y)
        self._apply_geometry()

    def pill_rect(self) -> Rect:
        return Rect(self._pill_pos.x(), self._pill_pos.y(), *theme.PILL_SIZE)

    def expand(self, auto: bool = False) -> None:
        if not auto:
            self.activateWindow()
            self.setFocus()
        self._animate_to(1.0)
        if not self.underMouse():
            self._restart_collapse_timer()

    def collapse(self) -> None:
        self._collapse_timer.stop()
        self._animate_to(0.0)

    # ------------------------------------------------------------------ geometry

    @staticmethod
    def _rect(qrect) -> Rect:
        return Rect(qrect.x(), qrect.y(), qrect.width(), qrect.height())

    def _areas(self) -> list[Rect]:
        return [self._rect(s.availableGeometry()) for s in QGuiApplication.screens()]

    def _area(self) -> Rect:
        center = self._pill_pos + QPoint(theme.PILL_SIZE[0] // 2, theme.PILL_SIZE[1] // 2)
        screen = QGuiApplication.screenAt(center) or QGuiApplication.primaryScreen()
        return self._rect(screen.availableGeometry())

    def _card_rect(self) -> Rect:
        return placement.card_geometry(self.pill_rect(), theme.CARD_SIZE, self._area())

    def _content_rect(self) -> Rect:
        pill, card, e = self.pill_rect(), self._card_rect(), self.expansion
        return Rect(round(_lerp(pill.x, card.x, e)), round(_lerp(pill.y, card.y, e)),
                    round(_lerp(pill.w, card.w, e)), round(_lerp(pill.h, card.h, e)))

    def _apply_geometry(self) -> None:
        r, m = self._content_rect(), theme.SHADOW
        self.setGeometry(r.x - m, r.y - m, r.w + 2 * m, r.h + 2 * m)
        self.update()

    def _local(self, rect: Rect) -> QPointF:
        """Top-left of a global content rect in this window's coordinates."""
        return QPointF(rect.x - self.x(), rect.y - self.y())

    # ------------------------------------------------------------------ animation

    def _animate_to(self, target: float) -> None:
        if target == self._target and (self._anim.state() == QVariantAnimation.State.Running
                                       or self.expansion == target):
            return
        self._target = target
        self._anim.stop()
        self._anim.setStartValue(float(self.expansion))
        self._anim.setEndValue(float(target))
        self._anim.start()
        self._update_opacity()
        self._update_pulse()

    def _set_expansion(self, value: float) -> None:
        self.expansion = float(value)
        self._apply_geometry()

    def _on_pulse(self, value: float) -> None:
        self._pulse = 0.5 - 0.5 * math.cos(2 * math.pi * value)
        self.update()

    def _update_pulse(self) -> None:
        want = self.phase in AWAITING and self._target == 0.0
        running = self._pulse_anim.state() == QVariantAnimation.State.Running
        if want and not running:
            self._pulse_anim.start()
        elif not want and running:
            self._pulse_anim.stop()
            self._pulse = 0.0

    def _update_opacity(self) -> None:
        calm = self._target == 0.0 and not self._hovered and self.phase not in AWAITING
        self.setWindowOpacity(theme.REST_OPACITY if calm else 1.0)

    def _restart_collapse_timer(self) -> None:
        if self._target == 1.0 and self.phase not in AWAITING:
            self._collapse_timer.start()

    def _auto_collapse(self) -> None:
        if not self.underMouse() and self.phase not in AWAITING:
            self.collapse()

    # ------------------------------------------------------------------ painting

    def _is_break(self) -> bool:
        """Color the UI for the break when in it or about to start it."""
        return self.phase in (Phase.BREAK, Phase.AWAITING_BREAK)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        m = theme.SHADOW
        r = QRectF(m, m, self.width() - 2 * m, self.height() - 2 * m)
        radius = _lerp(theme.PILL_SIZE[1] / 2, 20, self.expansion)

        # soft shadow: a few expanding, fading rounded rects
        p.setPen(Qt.PenStyle.NoPen)
        for i, alpha in enumerate((16, 10, 6, 3)):
            grow = i + 1
            p.setBrush(QColor(60, 45, 30, alpha))
            p.drawRoundedRect(r.adjusted(-grow, -grow + 2, grow, grow + 2), radius + grow, radius + grow)

        body = QPainterPath()
        body.addRoundedRect(r, radius, radius)
        p.fillPath(body, theme.CREAM)
        border = theme.BORDER
        if self.phase in AWAITING and self.expansion == 0.0:
            border = _with_alpha(theme.accent(self._is_break()), 0.35 + 0.65 * self._pulse)
        p.setPen(QPen(border, 1.2 if border is not theme.BORDER else 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)

        p.setClipPath(body)
        pill_alpha = _clamp01(1 - self.expansion * 2.5)
        card_alpha = _clamp01((self.expansion - 0.55) / 0.45)
        if pill_alpha > 0:
            p.save()
            p.translate(self._local(self.pill_rect()))
            p.setOpacity(pill_alpha)
            self._paint_pill(p)
            p.restore()
        self._buttons = {}
        if card_alpha > 0:
            p.save()
            origin = self._local(self._card_rect())
            p.translate(origin)
            p.setOpacity(card_alpha)
            self._paint_card(p)
            p.restore()
            self._buttons = {k: v.translated(origin) for k, v in self._buttons.items()}
        p.end()

    def _paint_ring(self, p: QPainter, center: QPointF, radius: float, width: float) -> None:
        rect = QRectF(center.x() - radius, center.y() - radius, 2 * radius, 2 * radius)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(theme.TRACK, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawEllipse(rect)
        if self.progress > 0:
            color = theme.accent(self._is_break())
            if self.paused:
                color = _with_alpha(color, 0.55)
            p.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(rect, 90 * 16, -round(self.progress * 360 * 16))

    def _paint_pill(self, p: QPainter) -> None:
        w, h = theme.PILL_SIZE
        accent = theme.accent(self._is_break())
        center = QPointF(19, h / 2)
        if self.phase in AWAITING or self.phase is Phase.IDLE:
            p.setPen(Qt.PenStyle.NoPen)
            dot = accent if self.phase is not Phase.IDLE else theme.CLAY
            p.setBrush(_with_alpha(dot, 0.55 + 0.45 * self._pulse) if self.phase in AWAITING else dot)
            p.drawEllipse(center, 4.5, 4.5)
        else:
            self._paint_ring(p, center, 7.5, 2.6)
            if self.paused:
                self._icon_pause(p, center, 5, theme.MUTED)

        text = {
            Phase.IDLE: "Pomodoro",
            Phase.AWAITING_BREAK: "Descanso",
            Phase.AWAITING_FOCUS: "Foco",
        }.get(self.phase, _mmss(self.remaining))
        is_time = self.phase not in AWAITING and self.phase is not Phase.IDLE
        f = theme.font("serif", 16 if is_time else 14.5, 600 if is_time else 500)
        p.setFont(f)
        p.setPen(theme.MUTED if self.paused else theme.INK)
        if is_time:
            p.drawText(QRectF(32, 0, w - 32 - 12, h), Qt.AlignmentFlag.AlignCenter, text)
            return
        # label + play triangle, centered together in the space right of the dot
        text_w = QFontMetricsF(f).horizontalAdvance(text)
        x = 32 + (w - 32 - 10 - (text_w + 14)) / 2
        p.drawText(QRectF(x, 0, text_w + 2, h), Qt.AlignmentFlag.AlignVCenter, text)
        self._icon_play(p, QPointF(x + text_w + 10, h / 2), 4, accent if self.phase in AWAITING else theme.MUTED)

    def _paint_card(self, p: QPainter) -> None:
        w, h = theme.CARD_SIZE
        brk = self._is_break()
        accent = theme.accent(brk)
        awaiting_or_idle = self.phase in AWAITING or self.phase is Phase.IDLE

        # ring + time
        center = QPointF(80, 92)
        self._paint_ring(p, center, 54, 7)
        p.setPen(theme.MUTED if self.paused else theme.INK)
        p.setFont(theme.font("serif", 30, 500))
        p.drawText(QRectF(center.x() - 50, center.y() - 26, 100, 38), Qt.AlignmentFlag.AlignCenter,
                   _mmss(self.remaining))
        label = {Phase.FOCUS: "FOCO", Phase.BREAK: "DESCANSO", Phase.IDLE: "FOCO",
                 Phase.AWAITING_BREAK: "DESCANSO", Phase.AWAITING_FOCUS: "FOCO"}[self.phase]
        if self.paused:
            label = "PAUSADO"
        p.setFont(theme.font("sans", 9.5, 600, spacing=1.4))
        p.setPen(accent if not self.paused else theme.MUTED)
        p.drawText(QRectF(center.x() - 50, center.y() + 12, 100, 16), Qt.AlignmentFlag.AlignCenter, label)

        # right column
        x0, col_w = 162.0, w - 162.0 - 20
        title, subtitle = self._texts()
        p.setPen(theme.INK)
        title_font = theme.font("serif", 19, 550)
        p.setFont(title_font)
        title = QFontMetricsF(title_font).elidedText(title, Qt.TextElideMode.ElideRight, col_w)
        p.drawText(QRectF(x0, 28, col_w, 26), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)
        p.setPen(theme.MUTED)
        p.setFont(theme.font("sans", 11.5, 400))
        p.drawText(QRectF(x0, 54, col_w, 34), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
                   | Qt.TextFlag.TextWordWrap, subtitle)

        if awaiting_or_idle:
            start = QRectF(x0, 96, 96, 34)
            self._buttons["start"] = start
            fill = theme.accent_dark(brk) if self._hover_button == "start" else accent
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(fill)
            p.drawRoundedRect(start, 17, 17)
            p.setPen(theme.CREAM)
            p.setFont(theme.font("sans", 12.5, 600))
            p.drawText(start, Qt.AlignmentFlag.AlignCenter, "Começar")
            if self.phase in AWAITING:
                later = QRectF(start.right() + 8, 96, 64, 34)
                self._buttons["later"] = later
                p.setPen(theme.INK if self._hover_button == "later" else theme.MUTED)
                p.setFont(theme.font("sans", 12, 500))
                p.drawText(later, Qt.AlignmentFlag.AlignCenter, "Depois")
        else:
            for i, name in enumerate(("restart", "toggle", "skip")):
                c = QPointF(x0 + 18 + i * 46, 113)
                self._buttons[name] = QRectF(c.x() - 18, c.y() - 18, 36, 36)
                if name == "toggle":
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(theme.accent_dark(brk) if self._hover_button == name else accent)
                    p.drawEllipse(c, 18, 18)
                    if self.paused:
                        self._icon_play(p, c + QPointF(1.5, 0), 6.5, theme.CREAM)
                    else:
                        self._icon_pause(p, c, 6.5, theme.CREAM)
                    continue
                if self._hover_button == name:
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(theme.HOVER)
                    p.drawEllipse(c, 18, 18)
                if name == "restart":
                    self._icon_restart(p, c, 7, theme.INK)
                else:
                    self._icon_skip(p, c, 6, theme.INK)

        # today
        y = 150.0
        shown = min(self.today_count, 6)
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(shown):
            p.setBrush(theme.CLAY)
            p.drawEllipse(QPointF(x0 + 4 + i * 10, y), 3.2, 3.2)
        tx = x0 + (shown * 10 + 6 if shown else 0)
        if self.today_count > shown:
            p.setPen(theme.MUTED)
            p.setFont(theme.font("sans", 10.5, 500))
            extra = f"+{self.today_count - shown}"
            p.drawText(QRectF(tx - 2, y - 8, 30, 16), Qt.AlignmentFlag.AlignVCenter, extra)
            tx += QFontMetricsF(p.font()).horizontalAdvance(extra) + 8
        p.setPen(theme.MUTED)
        p.setFont(theme.font("sans", 10.5, 400))
        summary = f"{self.today_minutes} min hoje" if self.today_count else "Nenhum pomodoro hoje"
        p.drawText(QRectF(tx, y - 8, w - tx - 12, 16), Qt.AlignmentFlag.AlignVCenter, summary)

        # collapse chevron
        chevron = QRectF(w - 34, 8, 26, 22)
        self._buttons["collapse"] = chevron
        p.setPen(QPen(theme.INK if self._hover_button == "collapse" else theme.MUTED, 1.6,
                      Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        c = chevron.center()
        p.drawPolyline([c + QPointF(-4.5, 2.5), c + QPointF(0, -2), c + QPointF(4.5, 2.5)])

    def _texts(self) -> tuple[str, str]:
        focus_min = round(self.focus_seconds / 60)
        break_min = round(self.break_seconds / 60)
        if self.phase is Phase.IDLE:
            return "Pronto para focar", f"{focus_min} min de foco, {break_min} de pausa."
        if self.phase is Phase.AWAITING_BREAK:
            return "Hora do descanso", f"Bom trabalho. {break_min} min para respirar."
        if self.phase is Phase.AWAITING_FOCUS:
            return "De volta ao foco", f"Mais {focus_min} min quando quiser."
        title = "Em foco" if self.phase is Phase.FOCUS else "Descansando"
        if self.paused:
            return "Pausado", f"Faltam {math.ceil(self.remaining / 60)} min."
        end = datetime.now() + timedelta(seconds=self.remaining)
        return title, f"Termina às {end:%H:%M}."

    # icons, drawn around a center point
    @staticmethod
    def _icon_play(p: QPainter, c: QPointF, s: float, color: QColor) -> None:
        path = QPainterPath()
        path.moveTo(c + QPointF(-s * 0.6, -s))
        path.lineTo(c + QPointF(s * 0.9, 0))
        path.lineTo(c + QPointF(-s * 0.6, s))
        path.closeSubpath()
        p.setPen(QPen(color, 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(color)
        p.drawPath(path)

    @staticmethod
    def _icon_pause(p: QPainter, c: QPointF, s: float, color: QColor) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        bw = s * 0.42
        for dx in (-s * 0.55, s * 0.55):
            p.drawRoundedRect(QRectF(c.x() + dx - bw / 2, c.y() - s, bw, 2 * s), bw / 2, bw / 2)

    @staticmethod
    def _icon_skip(p: QPainter, c: QPointF, s: float, color: QColor) -> None:
        PomodoroWindow._icon_play(p, c + QPointF(-s * 0.35, 0), s, color)
        p.setPen(QPen(color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(c + QPointF(s * 0.95, -s), c + QPointF(s * 0.95, s))

    @staticmethod
    def _icon_restart(p: QPainter, c: QPointF, s: float, color: QColor) -> None:
        rect = QRectF(c.x() - s, c.y() - s, 2 * s, 2 * s)
        p.setPen(QPen(color, 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(rect, 100 * 16, 280 * 16)
        # arrow head at the arc's start (top, pointing right)
        tip = c + QPointF(s * math.cos(math.radians(100)), -s * math.sin(math.radians(100)))
        p.setBrush(color)
        p.setPen(Qt.PenStyle.NoPen)
        head = QPainterPath()
        head.moveTo(tip + QPointF(3.6, 0))
        head.lineTo(tip + QPointF(-1.6, -3.2))
        head.lineTo(tip + QPointF(-1.6, 3.2))
        head.closeSubpath()
        p.drawPath(head)

    # ------------------------------------------------------------------ input

    def _button_at(self, pos: QPointF) -> str | None:
        if self.expansion < 1.0:
            return None
        return next((name for name, rect in self._buttons.items() if rect.contains(pos)), None)

    def enterEvent(self, event) -> None:
        self._hovered = True
        self._collapse_timer.stop()
        self._update_opacity()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self._hover_button = None
        self._update_opacity()
        self._restart_collapse_timer()
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press = event.globalPosition().toPoint()
            self._press_pill = QPoint(self._pill_pos)
            self._dragging = False

    def mouseMoveEvent(self, event) -> None:
        if self._press is not None and self._target == 0.0:
            delta = event.globalPosition().toPoint() - self._press
            if self._dragging or delta.manhattanLength() > DRAG_THRESHOLD:
                self._dragging = True
                self._pill_pos = self._press_pill + delta
                self._apply_geometry()
                return
        hover = self._button_at(event.position())
        if hover != self._hover_button:
            self._hover_button = hover
            self.setCursor(Qt.CursorShape.PointingHandCursor if hover or self._target == 0.0
                           else Qt.CursorShape.ArrowCursor)
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._press is None:
            return
        self._press = None
        if self._dragging:
            self._dragging = False
            self.moved.emit((self._pill_pos.x(), self._pill_pos.y()))
            return
        if self._target == 0.0:
            self.expand()
            return
        self._click(self._button_at(event.position()))

    def _click(self, button: str | None) -> None:
        if button == "start":
            self.start_requested.emit()
            QTimer.singleShot(450, self.collapse)
        elif button == "later":
            self.collapse()
        elif button == "collapse":
            self.collapse()
        elif button == "toggle":
            self.toggle_requested.emit()
        elif button == "restart":
            self.restart_requested.emit()
        elif button == "skip":
            self.skip_requested.emit()

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        reset = menu.addAction("Voltar ao topo")
        menu.addSeparator()
        quit_ = menu.addAction("Sair")
        chosen = menu.exec(event.globalPos())
        if chosen is reset:
            self.place(None)
            self.moved.emit(None)
        elif chosen is quit_:
            self.quit_requested.emit()

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.collapse()
        elif key in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.phase in AWAITING or self.phase is Phase.IDLE:
                self._click("start")
            else:
                self.toggle_requested.emit()
        else:
            super().keyPressEvent(event)

    def changeEvent(self, event) -> None:
        if event.type() == event.Type.ActivationChange and not self.isActiveWindow() and self._target == 1.0:
            self.collapse()
        super().changeEvent(event)
