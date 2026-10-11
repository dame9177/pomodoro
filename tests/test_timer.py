import pytest

from pomodoro.timer import Phase, PhaseEnded, Timer


@pytest.fixture
def clock():
    t = [0.0]
    return t


@pytest.fixture
def timer(clock):
    return Timer(1500, 300, clock=lambda: clock[0])


def test_idle_shows_next_focus(timer):
    assert timer.phase is Phase.IDLE
    assert timer.remaining() == 1500
    assert timer.progress() == 0
    assert timer.poll() is None


def test_full_cycle(timer, clock):
    timer.start()
    assert timer.phase is Phase.FOCUS
    clock[0] += 1500
    assert timer.poll() == PhaseEnded(Phase.FOCUS, 1500)
    assert timer.phase is Phase.AWAITING_BREAK
    assert timer.poll() is None
    assert timer.remaining() == 300

    timer.start()
    assert timer.phase is Phase.BREAK
    clock[0] += 299
    assert timer.poll() is None
    assert timer.remaining() == pytest.approx(1)
    clock[0] += 1
    assert timer.poll() == PhaseEnded(Phase.BREAK, 300)
    assert timer.phase is Phase.AWAITING_FOCUS

    timer.start()
    assert timer.phase is Phase.FOCUS


def test_progress(timer, clock):
    timer.start()
    clock[0] += 750
    assert timer.progress() == pytest.approx(0.5)


def test_pause_freezes_remaining(timer, clock):
    timer.start()
    clock[0] += 100
    timer.pause()
    assert timer.paused
    clock[0] += 1000
    assert timer.remaining() == pytest.approx(1400)
    assert timer.poll() is None
    timer.resume()
    assert not timer.paused
    clock[0] += 1399
    assert timer.poll() is None
    clock[0] += 1
    assert timer.poll() == PhaseEnded(Phase.FOCUS, 1500)


def test_toggle_pause(timer, clock):
    timer.start()
    timer.toggle_pause()
    assert timer.paused
    timer.toggle_pause()
    assert not timer.paused


def test_pause_ignored_when_not_running(timer):
    timer.pause()
    assert not timer.paused


def test_skip_no_event(timer, clock):
    timer.start()
    clock[0] += 10
    timer.skip()
    assert timer.phase is Phase.AWAITING_BREAK
    assert timer.poll() is None
    timer.start()
    timer.skip()
    assert timer.phase is Phase.AWAITING_FOCUS
    assert timer.poll() is None


def test_skip_while_paused_clears_pause(timer, clock):
    timer.start()
    timer.pause()
    timer.skip()
    assert not timer.paused
    timer.start()
    clock[0] += 300
    assert timer.poll() == PhaseEnded(Phase.BREAK, 300)


def test_restart_phase(timer, clock):
    timer.start()
    clock[0] += 600
    timer.restart_phase()
    assert timer.remaining() == 1500
    assert timer.phase is Phase.FOCUS


def test_poll_once_after_long_gap(timer, clock):
    timer.start()
    clock[0] += 10_000
    assert timer.poll() == PhaseEnded(Phase.FOCUS, 1500)
    assert timer.poll() is None
    assert timer.phase is Phase.AWAITING_BREAK


def test_start_noop_while_running(timer, clock):
    timer.start()
    clock[0] += 100
    timer.start()
    assert timer.remaining() == pytest.approx(1400)


def test_reset(timer, clock):
    timer.start()
    clock[0] += 100
    timer.reset()
    assert timer.phase is Phase.IDLE
    assert timer.remaining() == 1500
