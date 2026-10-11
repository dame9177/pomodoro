#!/usr/bin/env bash
# Adds Pomodoro to the GNOME app menu. With --autostart, also starts it at login.
set -euo pipefail
cd "$(dirname "$0")/.."
root="$(pwd)"
uv sync --quiet
exec_path="$root/.venv/bin/pomodoro"

apps="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
icons="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
mkdir -p "$apps" "$icons"
cp src/pomodoro/assets/pomodoro.svg "$icons/pomodoro.svg"
sed "s|@EXEC@|$exec_path|" packaging/pomodoro.desktop.in > "$apps/pomodoro.desktop"
echo "Menu: $apps/pomodoro.desktop"

if [[ "${1:-}" == "--autostart" ]]; then
  autostart="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
  mkdir -p "$autostart"
  cp "$apps/pomodoro.desktop" "$autostart/pomodoro.desktop"
  echo "Autostart: $autostart/pomodoro.desktop"
fi
