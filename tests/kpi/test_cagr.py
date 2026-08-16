from src.analytics.cagr import calculate_cagr, get_cagr_window


def test_normal_cagr():
    value, flag = calculate_cagr(100, 121, 2)

    assert round(value, 2) == 10.0
    assert flag is None


def test_decline_to_loss():
    value, flag = calculate_cagr(100, -20, 5)

    assert value is None
    assert flag == "DECLINE_TO_LOSS"


def test_turnaround():
    value, flag = calculate_cagr(-100, 50, 5)

    assert value is None
    assert flag == "TURNAROUND"


def test_both_negative():
    value, flag = calculate_cagr(-100, -50, 5)

    assert value is None
    assert flag == "BOTH_NEGATIVE"


def test_zero_base():
    value, flag = calculate_cagr(0, 100, 5)

    assert value is None
    assert flag == "ZERO_BASE"


def test_insufficient_years():
    value, flag = get_cagr_window([100, 110, 120], 5)

    assert value is None
    assert flag == "INSUFFICIENT"


def test_three_year_window():
    value, flag = get_cagr_window([100, 110, 121, 133.1], 3)

    assert round(value, 2) == 10.0
    assert flag is None


def test_five_year_window():
    value, flag = get_cagr_window(
        [100, 110, 121, 133.1, 146.41, 161.051],
        5,
    )

    assert round(value, 2) == 10.0
    assert flag is None


def test_missing_start_value():
    value, flag = calculate_cagr(None, 100, 5)

    assert value is None
    assert flag == "INSUFFICIENT"


def test_missing_end_value():
    value, flag = calculate_cagr(100, None, 5)

    assert value is None
    assert flag == "INSUFFICIENT"