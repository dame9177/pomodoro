import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import date

import pytest
from PySide6.QtWidgets import QApplication

from pomodoro import app as app_module
from pomodoro.app import Controller, durations
from pomodoro.settings import Settings, load_settings
from pomodoro.stats import Stats
from pomodoro.timer import Phase, Timer


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_durations_default():
    assert durations(Settings(), {}) == (1500, 300)


def test_durations_env_override():
    env = {"POMODORO_FOCUS_SECONDS": "8", "POMODORO_BREAK_SECONDS": "5"}
    assert durations(Settings(), env) == (8, 5)


def test_durations_bad_env_ignored():
    env = {"POMODORO_FOCUS_SECONDS": "abc", "POMODORO_BREAK_SECONDS": "-3"}
    assert durations(Settings(focus_seconds=600), env) == (600, 300)


@pytest.fixture
def controller(qapp, tmp_path, monkeypatch):
    played, notified = [], []
    monkeypatch.setattr(app_module.chime, "play", lambda path: played.append(path))
    monkeypatch.setattr(app_module, "notify", lambda *a, **k: notified.append(a))
    clock = [0.0]
    timer = Timer(1500, 300, clock=lambda: clock[0])
    stats = Stats(tmp_path / "h.json", today=lambda: date(2026, 10, 11))
    c = Controller(timer, stats, Settings(), tmp_path / "s.json", tmp_path / "chime.wav")
    c.clock, c.played, c.notified = clock, played, notified
    yield c
    c.window.close()


def test_phase_end_chimes_notifies_records_and_expands(controller):
    controller.window.start_requested.emit()
    assert controller.timer.phase is Phase.FOCUS
    controller.clock[0] += 1500
    controller.tick()
    assert controller.timer.phase is Phase.AWAITING_BREAK
    assert len(controller.played) == 1
    assert controller.notified == []          # off by default: the card is the notification
    assert controller.stats.today_count() == 1
    assert controller.window._target == 1.0
    controller.tick()
    assert len(controller.played) == 1      # once only


def test_break_end_not_recorded(controller):
    controller.timer.start()
    controller.timer.skip()
    controller.window.start_requested.emit()
    controller.clock[0] += 300
    controller.tick()
    assert controller.timer.phase is Phase.AWAITING_FOCUS
    assert controller.stats.today_count() == 0
    assert len(controller.played) == 1


def test_moved_saves_position(controller, tmp_path):
    controller.window.moved.emit((100, 200))
    assert load_settings(tmp_path / "s.json").position == (100, 200)
    controller.window.moved.emit(None)
    assert load_settings(tmp_path / "s.json").position is None


def test_notification_only_when_enabled(controller):
    controller.settings.notifications = True
    controller.timer.start()
    controller.clock[0] += 1500
    controller.tick()
    assert len(controller.notified) == 1


def test_human_duration():
    from pomodoro.ui.window import human_duration
    assert human_duration(1500) == "25 min"
    assert human_duration(20) == "20 s"
    assert human_duration(90) == "2 min"
