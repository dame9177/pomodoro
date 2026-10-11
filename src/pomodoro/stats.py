"""Completed pomodoros per local day."""

from datetime import date
from pathlib import Path
from typing import Callable

from .paths import read_json, write_json_atomic


class Stats:
    def __init__(self, path: Path, today: Callable[[], date] = date.today):
        self.path = path
        self._today = today
        data = read_json(path)
        self._days: dict = data if isinstance(data, dict) else {}

    def _entry(self) -> dict:
        entry = self._days.get(self._today().isoformat())
        return entry if isinstance(entry, dict) else {}

    def record_focus(self, seconds: float) -> None:
        entry = self._entry()
        self._days[self._today().isoformat()] = {
            "pomodoros": int(entry.get("pomodoros", 0)) + 1,
            "minutes": round(float(entry.get("minutes", 0)) + seconds / 60, 2),
        }
        try:
            write_json_atomic(self.path, self._days)
        except OSError:
            pass  # stats are a nicety; never break the timer over them

    def today_count(self) -> int:
        return int(self._entry().get("pomodoros", 0))

    def today_minutes(self) -> int:
        return round(float(self._entry().get("minutes", 0)))
