import json
from datetime import date

from pomodoro.stats import Stats


def test_record_and_read_today(tmp_path):
    stats = Stats(tmp_path / "h.json", today=lambda: date(2026, 10, 11))
    assert stats.today_count() == 0
    stats.record_focus(1500)
    stats.record_focus(1500)
    assert stats.today_count() == 2
    assert stats.today_minutes() == 50
    # persisted
    again = Stats(tmp_path / "h.json", today=lambda: date(2026, 10, 11))
    assert again.today_count() == 2


def test_rollover(tmp_path):
    day = [date(2026, 10, 11)]
    stats = Stats(tmp_path / "h.json", today=lambda: day[0])
    stats.record_focus(1500)
    day[0] = date(2026, 10, 12)
    assert stats.today_count() == 0
    stats.record_focus(1500)
    data = json.loads((tmp_path / "h.json").read_text())
    assert data["2026-10-11"]["pomodoros"] == 1
    assert data["2026-10-12"]["pomodoros"] == 1


def test_corrupt_history_is_empty(tmp_path):
    path = tmp_path / "h.json"
    path.write_text("{not json")
    stats = Stats(path, today=lambda: date(2026, 10, 11))
    assert stats.today_count() == 0
    stats.record_focus(1500)
    assert stats.today_count() == 1


def test_creates_missing_directory(tmp_path):
    stats = Stats(tmp_path / "a" / "b" / "h.json", today=lambda: date(2026, 10, 11))
    stats.record_focus(60)
    assert stats.today_minutes() == 1
