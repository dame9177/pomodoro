# pomodoro

Pomodoro desktop discreto (estilo Anthropic) para estudar: pílula no topo que expande ao clicar, 25/5

Created 2026-10-11. Workspace-level rules live in `../AGENTS.md`. User-facing docs: `README.md`.
Design: `docs/superpowers/specs/2026-10-11-pomodoro-design.md`.

## Setup / run / test

```bash
uv sync
uv run pytest                                                   # core + offscreen UI smoke tests
uv run pomodoro                                                 # the app
POMODORO_FOCUS_SECONDS=20 POMODORO_BREAK_SECONDS=10 uv run pomodoro   # quick cycle
./scripts/install-desktop.sh [--autostart]                      # GNOME menu entry (+ login)
```

## Project rules

- Stack: Python 3.12 + `pyside6-essentials` (not full `pyside6`: it pulls WebEngine). So no
  QtMultimedia: the chime is synthesized to `~/.cache/pomodoro/chime.wav` and played with
  `pw-play`/`paplay`/`aplay`.
- Qt-free core (`timer`, `stats`, `settings`, `placement`, `paths`) is unit tested; keep Qt
  out of it.
- Timer uses `CLOCK_BOOTTIME` so suspended time counts.
- Window must stay non-activating until clicked (`WA_ShowWithoutActivating`) and never cover
  the GNOME top bar: default y = `availableGeometry().top + 12`; x centered on the full screen
  (Ubuntu's left dock shrinks the available area by 66 px).
- The user also runs `leitor-voz`, whose mini-player sits in the bottom-right corner. Keep clear.
- Code/comments in English; UI strings and docs in pt-BR. MIT; bundled fonts OFL.
- Testing on the real desktop: screenshot with `QScreen.grabWindow(0)`; synthetic clicks via
  XTest (ctypes `libXtst`) only when the user is not using the machine.

## Status / next steps

- 2026-10-11: v0.1.0 implemented (spec + plan in `docs/superpowers/`). Verified on the real
  desktop: placement under the clock, expand, start, phase end → chime + auto-open card,
  second launch expands the running instance.
- GNOME notification banners appear exactly where the card opens, so notifications are off by
  default (`"notifications": true` in settings turns them on).
- Next: user review; then publish to GitHub (`dame9177/pomodoro`, public, MIT).
