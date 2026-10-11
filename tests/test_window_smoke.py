import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QElapsedTimer
from PySide6.QtWidgets import QApplication

from pomodoro.timer import Phase
from pomodoro.ui.window import PomodoroWindow


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def wait_for(cond, ms=2000):
    timer = QElapsedTimer()
    timer.start()
    while not cond() and timer.elapsed() < ms:
        QCoreApplication.processEvents()
    return cond()


@pytest.fixture
def window(app):
    w = PomodoroWindow(1500, 300)
    w.place(None)
    w.show()
    yield w
    w.close()


@pytest.mark.parametrize("phase", list(Phase))
@pytest.mark.parametrize("paused", [False, True])
def test_paints_every_state(window, phase, paused):
    window.set_state(phase, paused, 754.2, 0.4, 3, 75)
    assert not window.grab().isNull()
    window.expand()
    assert wait_for(lambda: window.expansion == 1.0)
    assert not window.grab().isNull()


def test_expand_and_collapse_resize(window):
    window.set_state(Phase.FOCUS, False, 1500, 0, 0, 0)
    pill_width = window.width()
    window.expand()
    assert wait_for(lambda: window.expansion == 1.0)
    assert window.width() > pill_width
    window.collapse()
    assert wait_for(lambda: window.expansion == 0.0)
    assert window.width() == pill_width


def test_placed_below_available_top(window, app):
    screen = app.primaryScreen()
    pill = window.pill_rect()
    assert pill.y == screen.availableGeometry().y() + 12
    assert abs((pill.x + pill.w / 2) - screen.geometry().center().x()) <= 1


def _mouse(window, kind, local, buttons):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    pos = QPointF(local)
    glob = QPointF(window.mapToGlobal(local))
    button = Qt.MouseButton.LeftButton if kind != QMouseEvent.Type.MouseMove else Qt.MouseButton.NoButton
    ev = QMouseEvent(kind, pos, glob, button, buttons, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(window, ev)


def test_drag_moves_pill_and_emits(window):
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtGui import QMouseEvent
    window.set_state(Phase.AWAITING_BREAK, False, 300, 0, 0, 0)
    moved = []
    window.moved.connect(moved.append)
    start = window.pill_rect()
    held, none = Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton
    p = QPoint(30, 25)
    _mouse(window, QMouseEvent.Type.MouseButtonPress, p, held)
    for i in range(1, 11):
        _mouse(window, QMouseEvent.Type.MouseMove, QPoint(30 - 10 * i, 25 + 10 * i) + QPoint(10 * (i - 1), -10 * (i - 1)), held)
    _mouse(window, QMouseEvent.Type.MouseButtonRelease, QPoint(20, 35), none)
    assert moved, "drag did not emit moved"
    assert window.pill_rect() != start
    assert window.expansion == 0.0
