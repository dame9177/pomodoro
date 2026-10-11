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
    area = app.primaryScreen().availableGeometry()
    pill = window.pill_rect()
    assert pill.y == area.y() + 12
    assert abs((pill.x + pill.w / 2) - (area.x() + area.width() / 2)) <= 1
