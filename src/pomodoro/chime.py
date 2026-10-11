"""A soft bell-like chime, synthesized at startup and played through PipeWire/ALSA."""

import math
import shutil
import struct
import subprocess
import wave
from pathlib import Path

# (frequency Hz, relative amplitude): E5 with a fifth and an octave above, like a small bell.
PARTIALS = [(659.25, 1.0), (987.77, 0.5), (1318.51, 0.2)]
DURATION = 1.4
ATTACK = 0.008
DECAY = 0.45
PEAK = 0.35

PLAYERS = (["pw-play"], ["paplay"], ["aplay", "-q"])


def render_wav(path: Path, sample_rate: int = 44100) -> None:
    total = sum(a for _, a in PARTIALS)
    frames = bytearray()
    for i in range(int(DURATION * sample_rate)):
        t = i / sample_rate
        envelope = min(1.0, t / ATTACK) * math.exp(-t / DECAY)
        value = sum(a * math.sin(2 * math.pi * f * t) for f, a in PARTIALS) / total
        frames += struct.pack("<h", int(PEAK * envelope * value * 32767))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(bytes(frames))


def play(path: Path) -> None:
    """Fire and forget; no audio player or device means no sound, never an error."""
    for cmd in PLAYERS:
        if shutil.which(cmd[0]):
            try:
                subprocess.Popen([*cmd, str(path)], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, start_new_session=True)
            except OSError:
                continue
            return
