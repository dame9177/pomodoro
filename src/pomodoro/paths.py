"""XDG locations and safe JSON writes."""

import json
import os
import tempfile
from pathlib import Path


def _xdg(var: str, fallback: str) -> Path:
    base = os.environ.get(var) or str(Path(os.environ.get("HOME", "~")).expanduser() / fallback)
    return Path(base) / "pomodoro"


def config_dir() -> Path:
    return _xdg("XDG_CONFIG_HOME", ".config")


def data_dir() -> Path:
    return _xdg("XDG_DATA_HOME", ".local/share")


def read_json(path: Path):
    """Parsed JSON, or None when the file is missing or unreadable."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_json_atomic(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def cache_dir() -> Path:
    return _xdg("XDG_CACHE_HOME", ".cache")
