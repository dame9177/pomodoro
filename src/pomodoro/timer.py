"""Pomodoro state machine. Qt-free; time comes from an injected clock."""

import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable


class Phase(StrEnum):
    IDLE = "idle"
    FOCUS = "focus"
    AWAITING_BREAK = "awaiting_break"
    BREAK = "break"
    AWAITING_FOCUS = "awaiting_focus"


RUNNING = (Phase.FOCUS, Phase.BREAK)


@dataclass(frozen=True)
class PhaseEnded:
    phase: Phase
    seconds: float


def boottime() -> float:
    """Monotonic clock that keeps counting while the machine is suspended."""
    return time.clock_gettime(time.CLOCK_BOOTTIME)


class Timer:
    def __init__(self, focus_seconds: float, break_seconds: float,
                 clock: Callable[[], float] = boottime):
        self.focus_seconds = focus_seconds
        self.break_seconds = break_seconds
        self._clock = clock
        self.phase = Phase.IDLE
        self.paused = False
        self._started_at = 0.0       # clock value when the current run segment began
        self._elapsed_before = 0.0   # time accumulated before the last pause

    # -- queries --

    def duration(self) -> float:
        """Length of the current phase, or of the next one while waiting."""
        if self.phase in (Phase.BREAK, Phase.AWAITING_BREAK):
            return self.break_seconds
        return self.focus_seconds

    def elapsed(self) -> float:
        if self.phase not in RUNNING:
            return 0.0
        if self.paused:
            return self._elapsed_before
        return self._elapsed_before + self._clock() - self._started_at

    def remaining(self) -> float:
        return max(0.0, self.duration() - self.elapsed())

    def progress(self) -> float:
        return min(1.0, self.elapsed() / self.duration()) if self.duration() else 1.0

    # -- actions --

    def start(self) -> None:
        if self.phase in (Phase.IDLE, Phase.AWAITING_FOCUS):
            self._begin(Phase.FOCUS)
        elif self.phase is Phase.AWAITING_BREAK:
            self._begin(Phase.BREAK)

    def pause(self) -> None:
        if self.phase in RUNNING and not self.paused:
            self._elapsed_before = self.elapsed()
            self.paused = True

    def resume(self) -> None:
        if self.phase in RUNNING and self.paused:
            self._started_at = self._clock()
            self.paused = False

    def toggle_pause(self) -> None:
        if self.paused:
            self.resume()
        else:
            self.pause()

    def restart_phase(self) -> None:
        if self.phase in RUNNING:
            self._begin(self.phase)

    def skip(self) -> None:
        if self.phase is Phase.FOCUS:
            self._wait(Phase.AWAITING_BREAK)
        elif self.phase is Phase.BREAK:
            self._wait(Phase.AWAITING_FOCUS)

    def reset(self) -> None:
        self._wait(Phase.IDLE)

    def poll(self) -> PhaseEnded | None:
        """Move to the waiting state when the phase is over; report it once."""
        if self.phase not in RUNNING or self.paused or self.remaining() > 0:
            return None
        ended = PhaseEnded(self.phase, self.duration())
        self._wait(Phase.AWAITING_BREAK if self.phase is Phase.FOCUS else Phase.AWAITING_FOCUS)
        return ended

    def _begin(self, phase: Phase) -> None:
        self.phase = phase
        self.paused = False
        self._elapsed_before = 0.0
        self._started_at = self._clock()

    def _wait(self, phase: Phase) -> None:
        self.phase = phase
        self.paused = False
        self._elapsed_before = 0.0
