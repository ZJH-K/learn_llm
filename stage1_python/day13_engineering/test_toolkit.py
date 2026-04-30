from toolkit import clamp


def test_value_in_range():
    assert clamp(1, 0, 2) == 1


def test_value_low_range():
    assert clamp(0, 1, 2) == 1


def test_value_high_range():
    assert clamp(2, 0, 1) == 1
