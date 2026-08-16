
"""
Sprint 2 - Days 08-09
Profitability, leverage and efficiency ratio engine
for the NIFTY 100 Financial Intelligence Platform.
"""


# ----------------------------------------------------------------------
# PROFITABILITY RATIOS
# ----------------------------------------------------------------------

def net_profit_margin(net_profit, sales):
    """
    Net Profit Margin = Net Profit / Sales * 100

    Returns None when either value is unavailable
    or sales is zero.
    """
    if net_profit is None:
        return None

    if sales is None or sales == 0:
        return None

    return (net_profit / sales) * 100


def operating_profit_margin(operating_profit, sales):
    """
    Operating Profit Margin = Operating Profit / Sales * 100

    Returns None when either value is unavailable
    or sales is zero.
    """
    if operating_profit is None:
        return None

    if sales is None or sales == 0:
        return None

    return (operating_profit / sales) * 100


def opm_cross_check(computed_opm, source_opm, tolerance=1.0):
    """
    Compare computed OPM against the source OPM percentage.

    Returns True when the absolute difference is greater
    than the supplied tolerance.
    """
    if computed_opm is None or source_opm is None:
        return False

    return abs(computed_opm - source_opm) > tolerance


def return_on_equity(
    net_profit,
    equity_capital,
    reserves,
):
    """
    ROE = Net Profit / (Equity Capital + Reserves) * 100

    Returns None when:
        - net profit is unavailable
        - equity is zero
        - equity is negative
    """
    if net_profit is None:
        return None

    equity = (
        (equity_capital or 0)
        + (reserves or 0)
    )

    if equity <= 0:
        return None

    return (net_profit / equity) * 100


def return_on_capital_employed(
    ebit,
    equity_capital,
    reserves,
    borrowings,
):
    """
    ROCE = EBIT /
           (Equity Capital + Reserves + Borrowings) * 100

    Returns None when EBIT is unavailable or
    capital employed is zero/negative.
    """
    if ebit is None:
        return None

    capital_employed = (
        (equity_capital or 0)
        + (reserves or 0)
        + (borrowings or 0)
    )

    if capital_employed <= 0:
        return None

    return (ebit / capital_employed) * 100


def return_on_assets(
    net_profit,
    total_assets,
):
    """
    ROA = Net Profit / Total Assets * 100

    Returns None when net profit is unavailable
    or total assets is zero/unavailable.
    """
    if net_profit is None:
        return None

    if total_assets is None or total_assets == 0:
        return None

    return (net_profit / total_assets) * 100


# ----------------------------------------------------------------------
# LEVERAGE RATIOS
# ----------------------------------------------------------------------

def debt_to_equity(
    borrowings,
    equity_capital,
    reserves,
):
    """
    D/E = Borrowings / (Equity Capital + Reserves)

    Rules:
        - Debt-free company -> 0
        - Negative/zero equity with debt -> None
        - Missing borrowings -> treated as zero
    """
    borrowings = borrowings or 0

    equity = (
        (equity_capital or 0)
        + (reserves or 0)
    )

    if borrowings == 0:
        return 0

    if equity <= 0:
        return None

    return borrowings / equity


def interest_coverage(
    operating_profit,
    other_income,
    interest,
):
    """
    Interest Coverage Ratio =
        (Operating Profit + Other Income) / Interest

    Returns None when interest is zero/unavailable.
    """
    if interest is None or interest == 0:
        return None

    numerator = (
        (operating_profit or 0)
        + (other_income or 0)
    )

    return numerator / interest


def interest_coverage_label(icr):
    """
    Display label for interest coverage.

    None -> Debt Free
    """
    if icr is None:
        return "Debt Free"

    return None


def interest_coverage_warning(
    icr,
    threshold=1.5,
):
    """
    Return True when ICR is below the warning threshold.
    """
    if icr is None:
        return False

    return icr < threshold


def net_debt(
    borrowings,
    investments,
):
    """
    Net Debt = Borrowings - Investments

    Investments are used as the liquid-asset proxy.
    """
    return (
        (borrowings or 0)
        - (investments or 0)
    )


def high_leverage_flag(
    debt_to_equity_value,
    broad_sector,
    threshold=5.0,
):
    """
    Flag high leverage when D/E > 5.

    Companies in Financials are excluded because
    structurally high leverage is normal for banks,
    NBFCs and insurers.
    """
    if debt_to_equity_value is None:
        return False

    if (
        broad_sector
        and broad_sector.strip().lower() == "financials"
    ):
        return False

    return debt_to_equity_value > threshold


# ----------------------------------------------------------------------
# EFFICIENCY RATIOS
# ----------------------------------------------------------------------

def asset_turnover(
    sales,
    total_assets,
):
    """
    Asset Turnover = Sales / Total Assets

    Returns None when sales is unavailable or
    total assets is zero/unavailable.
    """
    if sales is None:
        return None

    if total_assets is None or total_assets == 0:
        return None

    return sales / total_assets


# ----------------------------------------------------------------------
# OPTIONAL SAFE NUMERIC HELPERS
# ----------------------------------------------------------------------

def safe_add(*values):
    """
    Safely add numeric values.

    None values are treated as zero.
    Returns None when every value is None.
    """
    if all(value is None for value in values):
        return None

    return sum(
        value or 0
        for value in values
    )


def safe_subtract(left, right):
    """
    Safely subtract two values.

    None is treated as zero.
    """
    if left is None and right is None:
        return None

    return (left or 0) - (right or 0)