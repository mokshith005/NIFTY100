"""
Sprint 2 - Day 11
Cash Flow KPIs and Capital Allocation Engine.

Implements:
- Free Cash Flow
- CFO Quality Score
- CFO Quality Label
- CapEx Intensity
- CapEx Intensity Label
- FCF Conversion Rate
- 8-pattern Capital Allocation Classifier
- 5-year CFO/PAT average
"""

from __future__ import annotations

from typing import Iterable, Optional


def free_cash_flow(
    operating_activity: Optional[float],
    investing_activity: Optional[float],
) -> Optional[float]:
    """
    Free Cash Flow = Operating Activity + Investing Activity.

    Negative FCF is allowed.
    """

    if operating_activity is None and investing_activity is None:
        return None

    return (operating_activity or 0) + (investing_activity or 0)


def cfo_quality_score(
    cfo: Optional[float],
    pat: Optional[float],
) -> Optional[float]:
    """
    CFO Quality Score = CFO / PAT.

    Returns None when PAT is zero or unavailable.
    """

    if cfo is None or pat is None or pat == 0:
        return None

    return cfo / pat


def cfo_quality_label(
    score: Optional[float],
) -> Optional[str]:
    """
    Classify CFO quality.

    > 1.0       = High Quality
    0.5 - 1.0   = Moderate
    < 0.5       = Accrual Risk
    """

    if score is None:
        return None

    if score > 1.0:
        return "High Quality"

    if score >= 0.5:
        return "Moderate"

    return "Accrual Risk"


def capex_intensity(
    investing_activity: Optional[float],
    sales: Optional[float],
) -> Optional[float]:
    """
    CapEx Intensity = abs(Investing Activity) / Sales * 100.

    Returns None when sales is zero or unavailable.
    """

    if sales is None or sales == 0:
        return None

    return abs(investing_activity or 0) / sales * 100


def capex_intensity_label(
    intensity: Optional[float],
) -> Optional[str]:
    """
    Classify CapEx intensity.

    < 3%       = Asset Light
    3% - 8%    = Moderate
    > 8%       = Capital Intensive
    """

    if intensity is None:
        return None

    if intensity < 3:
        return "Asset Light"

    if intensity <= 8:
        return "Moderate"

    return "Capital Intensive"


def fcf_conversion_rate(
    fcf: Optional[float],
    operating_profit: Optional[float],
) -> Optional[float]:
    """
    FCF Conversion Rate = FCF / Operating Profit * 100.

    Returns None when operating profit is zero or unavailable.
    """

    if fcf is None or operating_profit is None:
        return None

    if operating_profit == 0:
        return None

    return fcf / operating_profit * 100


def sign(value: Optional[float]) -> str:
    """
    Convert a cash-flow value into its sign.

    Positive = +
    Negative = -
    Zero/None = 0
    """

    if value is None or value == 0:
        return "0"

    if value > 0:
        return "+"

    return "-"


def calculate_cfo_pat_5yr(
    cashflow_rows: Iterable[tuple],
    pat_rows: Iterable[tuple],
) -> Optional[float]:
    """
    Calculate the average CFO/PAT ratio over the latest
    5 common available years.

    cashflow_rows:
        Iterable of (year, CFO)

    pat_rows:
        Iterable of (year, PAT)

    Years with PAT = 0 are ignored because the ratio
    cannot be calculated.

    Returns None when no valid ratio exists.
    """

    cfo_by_year = {}

    for year, cfo in cashflow_rows:
        if year is None or cfo is None:
            continue

        cfo_by_year[str(year)] = cfo

    pat_by_year = {}

    for year, pat in pat_rows:
        if year is None or pat is None:
            continue

        pat_by_year[str(year)] = pat

    common_years = sorted(
        set(cfo_by_year) & set(pat_by_year),
        key=lambda value: float(value),
    )

    latest_years = common_years[-5:]

    ratios = []

    for year in latest_years:
        cfo = cfo_by_year[year]
        pat = pat_by_year[year]

        if pat == 0:
            continue

        ratios.append(cfo / pat)

    if not ratios:
        return None

    return sum(ratios) / len(ratios)


def capital_allocation_pattern(
    cfo: Optional[float],
    cfi: Optional[float],
    cff: Optional[float],
    cfo_quality: Optional[float] = None,
) -> str:
    """
    Classify capital allocation based on CFO, CFI and CFF.

    Patterns:

        (+,-,-) = Reinvestor
        (+,-,-) with high CFO/PAT = Shareholder Returns
        (+,+,-) = Liquidating Assets
        (-,+,+) = Distress Signal
        (-,-,+) = Growth Funded by Debt
        (+,+,+) = Cash Accumulator
        (-,-,-) = Pre-Revenue
        (+,-,+) = Mixed

    Special rule:
        (+,-,-) with CFO/PAT > 1.0
        becomes Shareholder Returns.
    """

    cfo_sign = sign(cfo)
    cfi_sign = sign(cfi)
    cff_sign = sign(cff)

    pattern = (
        cfo_sign,
        cfi_sign,
        cff_sign,
    )

    # Reinvestor / Shareholder Returns
    if pattern == ("+", "-", "-"):

        if cfo_quality is not None and cfo_quality > 1.0:
            return "Shareholder Returns"

        return "Reinvestor"

    # Liquidating Assets
    if pattern == ("+", "+", "-"):
        return "Liquidating Assets"

    # Distress Signal
    if pattern == ("-", "+", "+"):
        return "Distress Signal"

    # Growth Funded by Debt
    if pattern == ("-", "-", "+"):
        return "Growth Funded by Debt"

    # Cash Accumulator
    if pattern == ("+", "+", "+"):
        return "Cash Accumulator"

    # Pre-Revenue
    if pattern == ("-", "-", "-"):
        return "Pre-Revenue"

    # Mixed
    if pattern == ("+", "-", "+"):
        return "Mixed"

    # Additional mixed case
    if pattern == ("-", "+", "-"):
        return "Mixed"

    # Zero-sign combinations are also treated as Mixed.
    return "Mixed"


def classify_capital_allocation(
    cfo: Optional[float],
    cfi: Optional[float],
    cff: Optional[float],
    cfo_pat_ratio: Optional[float] = None,
) -> str:
    """
    Backward-compatible alias for capital_allocation_pattern().

    The CFO/PAT ratio can be supplied directly.
    """

    return capital_allocation_pattern(
        cfo=cfo,
        cfi=cfi,
        cff=cff,
        cfo_quality=cfo_pat_ratio,
    )