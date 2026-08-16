"""
Sprint 2 - Day 10
CAGR engine with required edge-case handling.
"""


def calculate_cagr(start, end, years):
    """
    Calculate CAGR as a percentage.

    Returns:
        (value, flag)

    Flags:
        None
        DECLINE_TO_LOSS
        TURNAROUND
        BOTH_NEGATIVE
        ZERO_BASE
        INSUFFICIENT
    """

    if years is None or years <= 0:
        return None, "INSUFFICIENT"

    if start is None or end is None:
        return None, "INSUFFICIENT"

    if start == 0:
        return None, "ZERO_BASE"

    if start > 0 and end > 0:
        value = ((end / start) ** (1 / years) - 1) * 100
        return value, None

    if start > 0 and end < 0:
        return None, "DECLINE_TO_LOSS"

    if start < 0 and end > 0:
        return None, "TURNAROUND"

    if start < 0 and end < 0:
        return None, "BOTH_NEGATIVE"

    return None, "INSUFFICIENT"


def get_cagr_window(values, years):
    """
    Calculate CAGR using a historical series.

    The supplied list must contain chronological observations.
    """

    if values is None:
        return None, "INSUFFICIENT"

    if len(values) < years + 1:
        return None, "INSUFFICIENT"

    start = values[-(years + 1)]
    end = values[-1]

    return calculate_cagr(start, end, years)