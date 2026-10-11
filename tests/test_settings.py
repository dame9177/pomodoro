from pomodoro import paths
from pomodoro.settings import Settings, load_settings, save_settings


def test_settings_defaults_when_missing(tmp_path):
    s = load_settings(tmp_path / "s.json")
    assert s == Settings(focus_seconds=1500, break_seconds=300, position=None)


def test_settings_round_trip_position(tmp_path):
    path = tmp_path / "x" / "s.json"
    save_settings(path, Settings(position=(10, 44)))
    assert load_settings(path).position == (10, 44)


def test_settings_corrupt_falls_back(tmp_path):
    path = tmp_path / "s.json"
    path.write_text("[[[")
    assert load_settings(path) == Settings()


def test_settings_ignores_bad_types(tmp_path):
    path = tmp_path / "s.json"
    path.write_text('{"focus_seconds": "x", "break_seconds": -5, "position": [1, "a"]}')
    assert load_settings(path) == Settings()


def test_xdg_dirs(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "c"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "d"))
    assert paths.config_dir() == tmp_path / "c" / "pomodoro"
    assert paths.data_dir() == tmp_path / "d" / "pomodoro"


def test_xdg_fallback(monkeypatch, tmp_path):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert paths.config_dir() == tmp_path / ".config" / "pomodoro"
