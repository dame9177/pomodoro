"""Wires the timer, stats and settings to the window; single-instance entry point."""

import os
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from . import chime, paths
from .notify import notify
from .settings import Settings, load_settings, save_settings
from .stats import Stats
from .timer import Phase, PhaseEnded, Timer
from .ui import theme
from .ui.window import PomodoroWindow, human_duration

ICON = Path(__file__).resolve().parent / "assets" / "pomodoro.svg"
TICK_MS = 250


def durations(settings: Settings, env) -> tuple[int, int]:
    """Phase lengths in seconds; POMODORO_*_SECONDS env vars override (for testing)."""
    def pick(var: str, default: int) -> int:
        try:
            value = int(env.get(var, ""))
        except ValueError:
            return default
        return value if value > 0 else default
    return (pick("POMODORO_FOCUS_SECONDS", settings.focus_seconds),
            pick("POMODORO_BREAK_SECONDS", settings.break_seconds))


class Controller:
    def __init__(self, timer: Timer, stats: Stats, settings: Settings,
                 settings_path: Path, chime_path: Path):
        self.timer, self.stats = timer, stats
        self.settings, self.settings_path = settings, settings_path
        self.chime_path = chime_path

        w = self.window = PomodoroWindow(timer.focus_seconds, timer.break_seconds)
        w.setWindowIcon(QIcon(str(ICON)))
        w.start_requested.connect(self._act(timer.start))
        w.toggle_requested.connect(self._act(timer.toggle_pause))
        w.restart_requested.connect(self._act(timer.restart_phase))
        w.skip_requested.connect(self._act(timer.skip))
        w.quit_requested.connect(QApplication.quit)
        w.moved.connect(self._save_position)
        w.place(settings.position)
        self.refresh()

        self._ticker = QTimer(interval=TICK_MS)
        self._ticker.timeout.connect(self.tick)

    def start(self) -> None:
        self.window.show()
        self._ticker.start()

    def _act(self, action):
        def run():
            action()
            self.refresh()
        return run

    def tick(self) -> None:
        ended = self.timer.poll()
        if ended:
            self._phase_ended(ended)
        self.refresh()

    def refresh(self) -> None:
        t = self.timer
        self.window.set_state(t.phase, t.paused, t.remaining(), t.progress(),
                              self.stats.today_count(), self.stats.today_minutes())

    def _phase_ended(self, ended: PhaseEnded) -> None:
        chime.play(self.chime_path)
        if ended.phase is Phase.FOCUS:
            self.stats.record_focus(ended.seconds)
        if self.settings.notifications:
            if ended.phase is Phase.FOCUS:
                notify("Hora do descanso",
                       f"{human_duration(ended.seconds)} de foco concluídos. Clique em Começar para a pausa.",
                       str(ICON))
            else:
                notify("Hora de voltar ao foco",
                       "A pausa acabou. Clique em Começar quando estiver pronto.", str(ICON))
        self.refresh()
        self.window.expand(auto=True)

    def _save_position(self, pos) -> None:
        self.settings.position = tuple(pos) if pos else None
        try:
            save_settings(self.settings_path, self.settings)
        except OSError:
            pass

    def show_from_other_instance(self) -> None:
        self.window.show()
        self.window.raise_()
        self.window.expand()


def _server_name() -> str:
    return f"pomodoro-{os.getuid()}"


def _ping_running_instance() -> bool:
    socket = QLocalSocket()
    socket.connectToServer(_server_name())
    if not socket.waitForConnected(300):
        return False
    socket.write(b"show")
    socket.waitForBytesWritten(300)
    socket.disconnectFromServer()
    return True


def run(argv: list[str] | None = None) -> int:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("Pomodoro")
    app.setDesktopFileName("pomodoro")
    app.setQuitOnLastWindowClosed(False)

    if _ping_running_instance():
        return 0
    QLocalServer.removeServer(_server_name())   # stale socket from a crash
    server = QLocalServer()
    server.listen(_server_name())

    theme.load_fonts()
    settings_path = paths.config_dir() / "settings.json"
    settings = load_settings(settings_path)
    focus, brk = durations(settings, os.environ)
    chime_path = paths.cache_dir() / "chime.wav"
    try:
        chime.render_wav(chime_path)
    except OSError:
        pass

    controller = Controller(Timer(focus, brk), Stats(paths.data_dir() / "history.json"),
                            settings, settings_path, chime_path)

    def on_connection():
        while server.hasPendingConnections():
            server.nextPendingConnection().deleteLater()
            controller.show_from_other_instance()
    server.newConnection.connect(on_connection)

    controller.start()
    return app.exec()
