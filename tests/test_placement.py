from pomodoro.placement import Rect, card_geometry, choose_position, default_position

PRIMARY = Rect(0, 32, 2560, 1568)   # below a 32 px GNOME top bar
SIZE = (120, 34)


def test_default_below_top_bar():
    assert default_position(PRIMARY, SIZE) == (1220, 44)


def test_no_saved_uses_default():
    assert choose_position(None, SIZE, [PRIMARY], PRIMARY) == (1220, 44)


def test_saved_on_screen_kept():
    assert choose_position((100, 500), SIZE, [PRIMARY], PRIMARY) == (100, 500)


def test_saved_on_second_screen_kept():
    second = Rect(2560, 0, 1920, 1080)
    assert choose_position((3000, 50), SIZE, [PRIMARY, second], PRIMARY) == (3000, 50)


def test_saved_off_screen_falls_back():
    assert choose_position((3000, 50), SIZE, [PRIMARY], PRIMARY) == (1220, 44)


def test_saved_partially_off_falls_back():
    assert choose_position((2500, 50), SIZE, [PRIMARY], PRIMARY) == (1220, 44)


def test_saved_over_top_bar_falls_back():
    assert choose_position((500, 10), SIZE, [PRIMARY], PRIMARY) == (1220, 44)


def test_card_centered_on_pill():
    pill = Rect(1220, 44, 120, 34)
    assert card_geometry(pill, (300, 200), PRIMARY) == Rect(1130, 44, 300, 200)


def test_card_clamped_at_right_edge():
    pill = Rect(2430, 44, 120, 34)
    assert card_geometry(pill, (300, 200), PRIMARY) == Rect(2260, 44, 300, 200)


def test_card_clamped_at_bottom_edge():
    pill = Rect(500, 1560, 120, 34)
    assert card_geometry(pill, (300, 200), PRIMARY) == Rect(410, 1400, 300, 200)
