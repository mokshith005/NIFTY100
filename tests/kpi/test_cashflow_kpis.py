from src.analytics.cashflow_kpis import (
    free_cash_flow,
    cfo_quality_score,
    cfo_quality_label,
    capex_intensity,
    capex_intensity_label,
    fcf_conversion_rate,
    capital_allocation_pattern,
    calculate_cfo_pat_5yr,
    classify_capital_allocation,
)


def test_free_cash_flow():
    assert free_cash_flow(100, -40) == 60


def test_negative_free_cash_flow_allowed():
    assert free_cash_flow(50, -100) == -50


def test_cfo_quality():
    assert cfo_quality_score(120, 100) == 1.2


def test_cfo_quality_zero_pat():
    assert cfo_quality_score(100, 0) is None


def test_cfo_quality_label():
    assert cfo_quality_label(1.2) == "High Quality"
    assert cfo_quality_label(0.7) == "Moderate"
    assert cfo_quality_label(0.3) == "Accrual Risk"


def test_capex_intensity():
    assert capex_intensity(-5, 100) == 5.0


def test_capex_labels():
    assert capex_intensity_label(2.0) == "Asset Light"
    assert capex_intensity_label(5.0) == "Moderate"
    assert capex_intensity_label(10.0) == "Capital Intensive"


def test_fcf_conversion():
    assert fcf_conversion_rate(50, 100) == 50.0


def test_fcf_conversion_zero_op():
    assert fcf_conversion_rate(50, 0) is None


def test_reinvestor_pattern():
    assert capital_allocation_pattern(100, -50, -20, 0.8) == "Reinvestor"


def test_shareholder_returns_pattern():
    assert capital_allocation_pattern(100, -50, -20, 1.2) == "Shareholder Returns"


def test_liquidating_assets_pattern():
    assert capital_allocation_pattern(100, 50, -20) == "Liquidating Assets"


def test_distress_pattern():
    assert capital_allocation_pattern(-100, 50, 20) == "Distress Signal"


def test_debt_funded_growth_pattern():
    assert capital_allocation_pattern(-100, -50, 100) == "Growth Funded by Debt"


def test_cash_accumulator_pattern():
    assert capital_allocation_pattern(100, 50, 20) == "Cash Accumulator"


def test_pre_revenue_pattern():
    assert capital_allocation_pattern(-100, -50, -20) == "Pre-Revenue"


def test_mixed_pattern():
    assert capital_allocation_pattern(100, -50, 20) == "Mixed"
    from src.analytics.cashflow_kpis import (
    calculate_cfo_pat_5yr,
    classify_capital_allocation,
)


def test_cfo_pat_5yr_average():
    cashflow_rows = [
        ("2020", 120),
        ("2021", 130),
        ("2022", 140),
        ("2023", 150),
        ("2024", 160),
    ]

    pat_rows = [
        ("2020", 100),
        ("2021", 100),
        ("2022", 100),
        ("2023", 100),
        ("2024", 100),
    ]

    result = calculate_cfo_pat_5yr(
        cashflow_rows,
        pat_rows,
    )

    assert result == 1.4


def test_cfo_pat_5yr_zero_pat():
    cashflow_rows = [
        ("2020", 100),
        ("2021", 100),
    ]

    pat_rows = [
        ("2020", 0),
        ("2021", 0),
    ]

    result = calculate_cfo_pat_5yr(
        cashflow_rows,
        pat_rows,
    )

    assert result is None


def test_shareholder_returns_from_high_cfo_pat():
    result = classify_capital_allocation(
        150,
        -50,
        -100,
        1.2,
    )

    assert result == "Shareholder Returns"


def test_reinvestor_from_low_cfo_pat():
    result = classify_capital_allocation(
        80,
        -50,
        -100,
        0.8,
    )

    assert result == "Reinvestor"