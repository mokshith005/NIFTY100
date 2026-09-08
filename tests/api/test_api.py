
import pytest
from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


# ============================================================
# ROOT + HEALTH
# ============================================================

def test_root():
    response = client.get("/")

    assert response.status_code == 200


def test_health():
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert "db_row_counts" in data
    assert "version" in data
    assert "uptime_seconds" in data

    assert data["db_row_counts"]["companies"] == 92


# ============================================================
# COMPANIES
# ============================================================

def test_companies():
    response = client.get("/api/v1/companies")

    assert response.status_code == 200

    data = response.json()

    assert "count" in data
    assert data["count"] == 92


def test_company_tcs():
    response = client.get("/api/v1/companies/TCS")

    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "TCS"
    assert "company_name" in data


def test_company_invalid():
    response = client.get("/api/v1/companies/INVALID")

    assert response.status_code == 404


# ============================================================
# COMPANY FINANCIAL ENDPOINTS
# ============================================================

def test_company_pl():
    response = client.get("/api/v1/companies/TCS/pl")

    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "TCS"
    assert data["count"] > 0
    assert "data" in data
    assert len(data["data"]) == data["count"]


def test_company_bs():
    response = client.get("/api/v1/companies/TCS/bs")

    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "TCS"
    assert data["count"] > 0
    assert "data" in data
    assert len(data["data"]) == data["count"]


def test_company_cashflow():
    response = client.get("/api/v1/companies/TCS/cashflow")

    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "TCS"
    assert data["count"] > 0
    assert "data" in data
    assert len(data["data"]) == data["count"]


def test_company_ratios():
    response = client.get("/api/v1/companies/TCS/ratios")

    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "TCS"
    assert data["count"] > 0
    assert "data" in data
    assert len(data["data"]) == data["count"]


def test_company_tearsheet():
    response = client.get("/api/v1/companies/TCS/tearsheet")

    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "TCS"
    assert data["count"] == 16
    assert "documents" in data
    assert len(data["documents"]) == data["count"]

    years = [doc["year"] for doc in data["documents"]]

    assert "2024" in years
    assert "2009" in years


# ============================================================
# SCREENER
# ============================================================

def test_screener():
    response = client.get("/api/v1/screener")

    assert response.status_code == 200

    data = response.json()

    assert "count" in data
    assert data["count"] > 0
    assert "data" in data
    assert len(data["data"]) == data["count"]


def test_screener_filters():
    response = client.get(
        "/api/v1/screener"
        "?min_roe=20"
        "&max_debt_to_equity=1"
    )

    assert response.status_code == 200

    data = response.json()

    assert "count" in data
    assert data["count"] > 0
    assert "data" in data

    for company in data["data"]:
        if company.get("return_on_equity_pct") is not None:
            assert company["return_on_equity_pct"] >= 20

        if company.get("debt_to_equity") is not None:
            assert company["debt_to_equity"] <= 1


def test_screener_quality_score():
    response = client.get(
        "/api/v1/screener?min_quality_score=15"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] > 0
    assert "data" in data


# ============================================================
# SECTORS
# ============================================================

def test_sectors():
    response = client.get("/api/v1/sectors")

    assert response.status_code == 200

    data = response.json()

    assert "count" in data
    assert data["count"] > 0
    assert "data" in data


def test_sector_companies():
    response = client.get(
        "/api/v1/sectors/Industrials/companies"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 10
    assert "data" in data
    assert len(data["data"]) == data["count"]


def test_invalid_sector():
    response = client.get(
        "/api/v1/sectors/DoesNotExist/companies"
    )

    assert response.status_code == 404


# ============================================================
# PEERS
# ============================================================

def test_peer_group():
    response = client.get(
        "/api/v1/peers/Private%20Banks"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 5
    assert "data" in data
    assert len(data["data"]) == 5


def test_invalid_peer_group():
    response = client.get(
        "/api/v1/peers/DoesNotExist"
    )

    assert response.status_code == 404


def test_peer_comparison():
    response = client.get(
        "/api/v1/companies/HDFCBANK/peers/compare"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "HDFCBANK"
    assert data["peer_count"] == 5
    assert "peer_groups" in data
    assert "data" in data

    assert len(data["data"]) == data["peer_count"]

    benchmark = [
        peer
        for peer in data["data"]
        if peer["is_benchmark"] is True
    ]

    assert len(benchmark) == 1
    assert benchmark[0]["company_id"] == "HDFCBANK"


def test_peer_comparison_tcs():
    response = client.get(
        "/api/v1/companies/TCS/peers/compare"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "TCS"
    assert data["peer_count"] > 0
    assert "peer_groups" in data
    assert "data" in data

    assert len(data["data"]) == data["peer_count"]

    benchmark = [
        peer
        for peer in data["data"]
        if peer["is_benchmark"] is True
    ]

    assert len(benchmark) == 1
    assert benchmark[0]["company_id"] == "TCS"


# ============================================================
# VALUATION / MARKET CAP
# ============================================================

def test_market_cap():
    response = client.get(
        "/api/v1/market-cap/TCS"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "TCS"
    assert "data" in data

    market_data = data["data"]

    assert market_data["year"] == "2024"
    assert market_data["market_cap_crore"] is not None


def test_market_cap_invalid():
    response = client.get(
        "/api/v1/market-cap/INVALID"
    )

    assert response.status_code == 404


# ============================================================
# PORTFOLIO
# ============================================================

def test_portfolio_stats():
    response = client.get(
        "/api/v1/portfolio/stats"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["company_count"] == 90
    assert data["avg_roe"] is not None
    assert data["avg_debt_to_equity"] is not None
    assert data["avg_revenue_cagr_5yr"] is not None
    assert data["avg_quality_score"] is not None


# ============================================================
# DOCUMENTS
# ============================================================

def test_company_documents():
    response = client.get(
        "/api/v1/companies/TCS/documents"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "TCS"
    assert data["count"] == 16
    assert "data" in data

    assert len(data["data"]) == data["count"]


def test_company_documents_invalid():
    response = client.get(
        "/api/v1/companies/INVALID/documents"
    )

    assert response.status_code == 404


# ============================================================
# PARAMETERIZED COMPANY DATA TESTS
# ============================================================

@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/v1/companies/TCS/pl",
        "/api/v1/companies/TCS/bs",
        "/api/v1/companies/TCS/cashflow",
        "/api/v1/companies/TCS/ratios",
    ],
)
def test_company_data_endpoints(endpoint):
    response = client.get(endpoint)

    assert response.status_code == 200

    data = response.json()

    assert "company_id" in data
    assert data["company_id"] == "TCS"
    assert "count" in data
    assert data["count"] > 0
    assert "data" in data
    assert isinstance(data["data"], list)


def test_tearsheet_endpoint():
    response = client.get(
        "/api/v1/companies/TCS/tearsheet"
    )

    assert response.status_code == 200

    data = response.json()

    assert "company_id" in data
    assert "count" in data
    assert "documents" in data

    assert isinstance(data["documents"], list)
    assert len(data["documents"]) == data["count"]


# ============================================================
# STATUS CODE TESTS
# ============================================================

@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/v1/companies/TCS",
        "/api/v1/companies/TCS/pl",
        "/api/v1/companies/TCS/bs",
        "/api/v1/companies/TCS/cashflow",
        "/api/v1/companies/TCS/ratios",
        "/api/v1/companies/TCS/tearsheet",
        "/api/v1/companies/TCS/documents",
        "/api/v1/market-cap/TCS",
        "/api/v1/companies/HDFCBANK/peers/compare",
        "/api/v1/companies/TCS/peers/compare",
    ],
)
def test_valid_endpoints_return_200(endpoint):
    response = client.get(endpoint)

    assert response.status_code == 200


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/v1/companies/INVALID",
        "/api/v1/companies/INVALID/documents",
        "/api/v1/market-cap/INVALID",
        "/api/v1/sectors/DoesNotExist/companies",
        "/api/v1/peers/DoesNotExist",
    ],
)
def test_invalid_endpoints_return_404(endpoint):
    response = client.get(endpoint)

    assert response.status_code == 404
