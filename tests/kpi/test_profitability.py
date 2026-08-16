import pytest

from src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    opm_cross_check,
    return_on_equity,
    return_on_capital_employed,
    return_on_assets,
)


def test_npm_normal_case():
    assert net_profit_margin(20, 100) == 20.0


def test_npm_zero_sales():
    assert net_profit_margin(20, 0) is None


def test_opm_normal_case():
    assert operating_profit_margin(30, 100) == 30.0


def test_opm_cross_check_mismatch():
    computed = operating_profit_margin(30, 100)

    assert opm_cross_check(computed, 25.0) is True


def test_opm_cross_check_within_tolerance():
    computed = operating_profit_margin(30, 100)

    assert opm_cross_check(computed, 30.5) is False


def test_roe_normal_case():
    assert return_on_equity(20, 50, 50) == 20.0


def test_roe_negative_equity():
    assert return_on_equity(20, -100, 20) is None


def test_roa_zero_assets():
    assert return_on_assets(20, 0) is None


def test_roce_normal_case():
    assert return_on_capital_employed(30, 50, 50, 100) == 15.0