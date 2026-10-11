"""User settings: phase durations and the saved window position."""

from dataclasses import asdict, dataclass
from pathlib import Path

from .paths import read_json, write_json_atomic


@dataclass
class Settings:
    focus_seconds: int = 1500
    break_seconds: int = 300
    position: tuple[int, int] | None = None
    notifications: bool = False   # GNOME banners show up right where the card opens


def _positive_int(value, default: int) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else default


def load_settings(path: Path) -> Settings:
    data = read_json(path)
    if not isinstance(data, dict):
        return Settings()
    pos = data.get("position")
    valid_pos = (isinstance(pos, list) and len(pos) == 2
                 and all(isinstance(v, int) and not isinstance(v, bool) for v in pos))
    return Settings(
        focus_seconds=_positive_int(data.get("focus_seconds"), Settings.focus_seconds),
        break_seconds=_positive_int(data.get("break_seconds"), Settings.break_seconds),
        position=tuple(pos) if valid_pos else None,
        notifications=data.get("notifications") is True,
    )


def save_settings(path: Path, settings: Settings) -> None:
    data = asdict(settings)
    data["position"] = list(settings.position) if settings.position else None
    write_json_atomic(path, data)
