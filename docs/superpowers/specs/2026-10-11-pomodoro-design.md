# Pomodoro — design

Date: 2026-10-11. Status: approved in chat, pending review of this written spec.

## Goal

A desktop Pomodoro timer for studying (medical residency prep) on Ubuntu GNOME (X11).
It stays out of the way while the user reads and only becomes a full UI when clicked.
Fixed cycle: **25 min focus, 5 min break**. Visual language inspired by Anthropic's
style: warm cream, clay accent, serif numerals, minimal chrome.

Success: the user forgets it is there while studying, but notices every phase change,
and it never covers the GNOME top bar (clock/date) or the `leitor-voz` mini-player
(bottom-right corner, 24 px margin, ~325 px wide).

Will be published as open source (MIT) on the user's GitHub after the user approves the
finished app. Code, identifiers and comments in English; UI strings and README in pt-BR.

## Requirements

### What the user asked for
- Desktop app, Anthropic-like look, subtle until clicked, good UX.
- 25 min focus / 5 min break.
- Must not overlap the voice reader (bottom-right) nor GNOME's top bar.
- Collapsed position: top-center, draggable.
- At the end of a phase: notify and **wait for a click** before starting the next phase.

### Assumptions (approved)
- Always on top; never steals keyboard focus from the window being studied.
- Soft sound + GNOME notification on phase end.
- Same stack as `leitor-voz`: Python + uv + PySide6.

## Visual and interaction

- **Palette:** background cream `#F5F1E8`, text graphite `#1F1E1C`, focus accent clay
  `#CC785C`, break accent sage `#7A9A82`, hairline border `#E3DCCB`, very soft shadow.
- **Type:** Source Serif 4 for the timer numerals, Inter for labels. Both SIL OFL 1.1,
  bundled under `src/pomodoro/assets/fonts/` with their license files and loaded with
  `QFontDatabase` (neither is installed on the system).
- **Collapsed (pill):** ~120×34 logical px. Small circular progress dot, remaining time
  (`18:42`), phase shown by color only. ~75% opacity at rest, 100% on hover. With nothing
  running it shows `Pomodoro ▸`.
- **Expanded (card):** on click the pill animates (~220 ms, ease-out) into a ~300×200 card:
  - large progress ring with the time in serif;
  - label `Foco` / `Descanso`;
  - quiet buttons: play/pause, restart phase, skip phase;
  - today's pomodoros as dots (`●●●○`) plus total focused minutes.

  It collapses on outside click, Esc, or after ~6 s without the mouse over it (never while
  waiting for the user to start the next phase).
- **Phase end:** a short soft chime, a GNOME notification, and the card opens on its own
  with `Hora do descanso` / `Hora de focar` and a **Começar** button. While waiting, the
  collapsed pill pulses slowly in the next phase's color.
- **Drag:** press and drag the pill. Position persists. Right-click → menu with
  `Voltar ao topo` (reset position) and `Sair`.
- **Keys while the card is open:** Space = pause/resume, Esc = collapse.
- HiDPI: all sizes are logical pixels; Qt handles the device pixel ratio.

## Placement

- Default: horizontally centered on the primary screen, top edge at
  `availableGeometry().top() + 12`. On GNOME/X11 the available geometry already excludes
  the top bar (it sets a strut), so the pill sits just below the clock.
- Card expansion grows **downward** from the pill's top edge and stays horizontally
  centered on the pill, clamped to the available geometry.
- A saved position is used only if the whole pill fits inside some screen's available
  geometry; otherwise fall back to the default.

## Architecture

Package `src/pomodoro/`, small units with one job each. The Qt-free units are fully unit
tested.

| Module | Responsibility | Qt |
|---|---|---|
| `timer.py` | Pure state machine. States: `idle`, `focus`, `awaiting_break`, `break`, `awaiting_focus`; plus `paused` flag. Actions: start, pause, resume, restart phase, skip phase. Remaining time computed from an injected monotonic clock (no tick counting). `poll()` returns a phase-end event exactly once. | No |
| `stats.py` | Completed pomodoros and focused minutes per local date in `~/.local/share/pomodoro/history.json`. Counts only completed focus phases (not skipped). Corrupt/missing file → empty history. | No |
| `settings.py` | Window position and durations (default 25/5) in `~/.config/pomodoro/settings.json`. Corrupt/missing → defaults. Writes are atomic (temp file + rename). | No |
| `placement.py` | Default position and saved-position validation from plain rectangles. | No |
| `sound.py` | Generates the chime in memory (sine partials with an exponential envelope, WAV in a temp file) and plays it with `QSoundEffect`. No audio device → silent, no crash. | Yes |
| `notify.py` | `notify-send` via `subprocess`; missing binary → ignored. | No |
| `ui/ring.py` | Paints progress ring/dot. | Yes |
| `ui/window.py` | The single frameless window: pill and card states, animations, drag, menu, keys. | Yes |
| `app.py`, `cli.py` | Wiring; `uv run pomodoro`. Single instance via `QLocalServer`: a second launch asks the running one to expand and exits. | Yes |

Window flags (same as `leitor-voz`): `Tool | FramelessWindowHint | WindowStaysOnTopHint`,
`WA_ShowWithoutActivating`, `WA_TranslucentBackground`. The card takes keyboard focus only
after an explicit click on it, so Space/Esc work then and never steal focus otherwise.

### Data flow

A 250 ms `QTimer` calls `timer.poll(now)` and repaints. When `poll` reports a phase end,
`app` plays the chime, sends the notification, records the pomodoro in `stats` (for focus
phases), and asks the window to expand into the waiting state.

Durations are 25/5 by default and read from settings, so tests and a future option can
change them; there is no settings UI.

## Integration

- `pomodoro.desktop` for the apps menu (with an SVG icon in the clay color).
- Optional autostart (`~/.config/autostart/pomodoro.desktop`) installed by a script only
  if the user asks.

## Testing

- `pytest` for `timer` (fake clock: full cycle, pause/resume keeps remaining time, skip and
  restart, phase-end event emitted once), `stats` (date rollover, corrupt file),
  `settings` (defaults, round trip, corrupt file), `placement` (default position below the
  available area top, saved position off-screen → default).
- UI smoke test with `QT_QPA_PLATFORM=offscreen`: window builds, expands, collapses.
- Manual check on the real desktop with screenshots: look, top-center placement below the
  clock, no overlap with the voice reader, drag + persistence, phase transition (with
  short durations via an env var such as `POMODORO_FOCUS_SECONDS`).

## Out of scope

Long break every 4 cycles, tasks/tags, charts, sync, settings UI, Wayland-specific work.
