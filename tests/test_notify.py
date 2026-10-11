from pomodoro.notify import notify


def test_notify_missing_binary_is_silent(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path))
    notify("Hora do descanso", "5 minutos")   # must not raise
