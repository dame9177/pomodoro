"""Where the window goes. Plain rectangles in logical pixels, no Qt."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int

    def contains(self, other: "Rect") -> bool:
        return (other.x >= self.x and other.y >= self.y
                and other.x + other.w <= self.x + self.w
                and other.y + other.h <= self.y + self.h)


def default_position(area: Rect, size: tuple[int, int], margin: int = 12) -> tuple[int, int]:
    """Centered horizontally, just below the top of the usable area (under the top bar)."""
    return area.x + (area.w - size[0]) // 2, area.y + margin


def choose_position(saved: tuple[int, int] | None, size: tuple[int, int],
                    areas: list[Rect], primary: Rect) -> tuple[int, int]:
    """The saved position if the whole window fits on some screen, else the default."""
    if saved is not None:
        window = Rect(saved[0], saved[1], *size)
        if any(area.contains(window) for area in areas):
            return saved
    return default_position(primary, size)


def card_geometry(pill: Rect, card_size: tuple[int, int], area: Rect) -> Rect:
    """The expanded card grows down from the pill's top, centered on it, kept on screen."""
    w, h = card_size
    x = pill.x + pill.w // 2 - w // 2
    x = max(area.x, min(x, area.x + area.w - w))
    y = max(area.y, min(pill.y, area.y + area.h - h))
    return Rect(x, y, w, h)
