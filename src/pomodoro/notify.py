"""Desktop notifications through notify-send (libnotify)."""

import subprocess


def notify(title: str, body: str, icon: str | None = None) -> None:
    cmd = ["notify-send", "-a", "Pomodoro", "-u", "normal"]
    if icon:
        cmd += ["-i", icon]
    try:
        subprocess.Popen([*cmd, title, body], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        pass
