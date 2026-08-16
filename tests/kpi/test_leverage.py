from src.analytics.ratios import (
    debt_to_equity,
    interest_coverage,
    interest_coverage_label,
    interest_coverage_warning,
    net_debt,
    asset_turnover,
    high_leverage_flag,
)


def test_debt_to_equity_normal():
    assert debt_to_equity(50, 50, 50) == 0.5


def test_debt_to_equity_debt_free():
    assert debt_to_equity(0, 50, 50) == 0


def test_debt_to_equity_negative_equity():
    assert debt_to_equity(50, -100, 20) is None


def test_interest_coverage_normal():
    assert interest_coverage(100, 20, 10) == 12.0


def test_interest_coverage_zero_interest():
    assert interest_coverage(100, 20, 0) is None


def test_interest_coverage_debt_free_label():
    icr = interest_coverage(100, 20, 0)

    assert interest_coverage_label(icr) == "Debt Free"


def test_high_leverage_flag():
    assert high_leverage_flag(6.0, "Technology") is True
    assert high_leverage_flag(4.0, "Technology") is False


def test_financials_high_leverage_suppressed():
    assert high_leverage_flag(10.0, "Financials") is False


def test_interest_coverage_warning():
    assert interest_coverage_warning(1.2) is True
    assert interest_coverage_warning(2.0) is False


def test_net_debt():
    assert net_debt(100, 30) == 70


def test_asset_turnover():
    assert asset_turnover(200, 100) == 2.0


def test_asset_turnover_zero_assets():
    assert asset_turnover(200, 0) is None