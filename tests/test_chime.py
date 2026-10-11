import wave

from pomodoro import chime


def test_chime_wav_valid(tmp_path):
    path = tmp_path / "c.wav"
    chime.render_wav(path)
    with wave.open(str(path)) as w:
        assert w.getnchannels() == 1
        assert w.getframerate() == 44100
        assert w.getsampwidth() == 2
        assert 1.3 <= w.getnframes() / 44100 <= 1.5
        frames = w.readframes(w.getnframes())
    samples = memoryview(frames).cast("h")
    peak = max(abs(s) for s in samples)
    assert 0.2 * 32767 < peak < 0.4 * 32767


def test_play_without_player_is_silent(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    chime.play(tmp_path / "missing.wav")   # must not raise
