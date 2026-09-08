import json
import sqlite3
from pathlib import Path

import pandas as pd
import requests


BASE_URL = "http://127.0.0.1:8001"
ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "nifty100.db"

passed = 0
failed = 0


def gate(number, name, condition):
    global passed, failed

    if condition:
        print(f"[PASS] Gate {number:02d} - {name}")
        passed += 1
    else:
        print(f"[FAIL] Gate {number:02d} - {name}")
        failed += 1


def get(path):
    return requests.get(BASE_URL + path, timeout=10)


print("=" * 70)
print("SPRINT 6 FINAL ACCEPTANCE GATES")
print("=" * 70)

# ------------------------------------------------------------------
# Gate 01 - Database exists
# ------------------------------------------------------------------
gate(
    1,
    "Production database exists",
    DB_PATH.exists(),
)

# ------------------------------------------------------------------
# Database checks
# ------------------------------------------------------------------
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM companies")
company_count = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM financial_ratios")
ratio_count = cur.fetchone()[0]

conn.close()

# ------------------------------------------------------------------
# Gate 02 - 92 companies
# ------------------------------------------------------------------
gate(
    2,
    "92 companies present",
    company_count == 92,
)

# ------------------------------------------------------------------
# Gate 03 - Financial ratios
# ------------------------------------------------------------------
gate(
    3,
    "Financial ratios populated",
    ratio_count > 1000,
)

# ------------------------------------------------------------------
# Gate 04 - Cluster labels
# ------------------------------------------------------------------
cluster_file = ROOT / "output" / "cluster_labels.csv"

gate(
    4,
    "Cluster labels generated",
    cluster_file.exists(),
)

# ------------------------------------------------------------------
# Gate 05 - Cluster profiles
# ------------------------------------------------------------------
cluster_mean = ROOT / "output" / "cluster_profiles_mean.csv"
cluster_median = ROOT / "output" / "cluster_profiles_median.csv"

gate(
    5,
    "Cluster profiles generated",
    cluster_mean.exists() and cluster_median.exists(),
)

# ------------------------------------------------------------------
# Gate 06 - Five clusters
# ------------------------------------------------------------------
unique_clusters = 0

if cluster_file.exists():
    try:
        clusters = pd.read_csv(cluster_file)

        if "cluster" in clusters.columns:
            unique_clusters = clusters["cluster"].nunique()
        elif "cluster_id" in clusters.columns:
            unique_clusters = clusters["cluster_id"].nunique()

    except Exception:
        unique_clusters = 0

gate(
    6,
    "Five KMeans clusters generated",
    unique_clusters == 5,
)

# ------------------------------------------------------------------
# Gate 07 - Elbow plot
# ------------------------------------------------------------------
gate(
    7,
    "Elbow plot generated",
    (ROOT / "reports" / "elbow_plot.png").exists(),
)

# ------------------------------------------------------------------
# Gate 08 - Correlation heatmap
# ------------------------------------------------------------------
gate(
    8,
    "Correlation heatmap generated",
    (ROOT / "reports" / "correlation_heatmap.png").exists(),
)

# ------------------------------------------------------------------
# Gate 09 - OpenAPI specification
# ------------------------------------------------------------------
openapi_file = ROOT / "docs" / "openapi.json"

openapi_valid = False
openapi = {}

try:
    with open(openapi_file, encoding="utf-8") as f:
        openapi = json.load(f)

    openapi_valid = True

except Exception:
    openapi_valid = False

gate(
    9,
    "OpenAPI specification valid",
    openapi_valid,
)

# ------------------------------------------------------------------
# Gate 10 - API endpoint count
# ------------------------------------------------------------------
paths = openapi.get("paths", {})

# 17 paths includes the root "/" endpoint.
# The project requirement is 16 API endpoints under /api/v1.
gate(
    10,
    "16 API endpoints documented",
    len(paths) == 17,
)

# ------------------------------------------------------------------
# Gate 11 - Root endpoint
# ------------------------------------------------------------------
try:
    response = get("/")
    root_ok = response.status_code == 200
except Exception:
    root_ok = False

gate(
    11,
    "Root endpoint responds",
    root_ok,
)

# ------------------------------------------------------------------
# Gate 12 - Health endpoint
# ------------------------------------------------------------------
try:
    response = get("/api/v1/health")

    health_data = response.json()

    health_ok = (
        response.status_code == 200
        and health_data.get("status") is not None
        and health_data.get("db_row_counts", {}).get("companies") == 92
    )

except Exception:
    health_ok = False

gate(
    12,
    "Health endpoint reports healthy database",
    health_ok,
)

# ------------------------------------------------------------------
# Gate 13 - Company endpoint
# ------------------------------------------------------------------
try:
    response = get("/api/v1/companies/TCS")
    company_api_ok = response.status_code == 200
except Exception:
    company_api_ok = False

gate(
    13,
    "Company endpoint works",
    company_api_ok,
)

# ------------------------------------------------------------------
# Gate 14 - Financial ratios endpoint
# ------------------------------------------------------------------
try:
    response = get("/api/v1/companies/TCS/ratios")
    ratios_api_ok = response.status_code == 200
except Exception:
    ratios_api_ok = False

gate(
    14,
    "Financial ratios endpoint works",
    ratios_api_ok,
)

# ------------------------------------------------------------------
# Gate 15 - Screener
# ------------------------------------------------------------------
try:
    response = get("/api/v1/screener")

    screener_data = response.json()

    screener_ok = (
        response.status_code == 200
        and screener_data.get("count", 0) > 0
    )

except Exception:
    screener_ok = False

gate(
    15,
    "Screener endpoint works",
    screener_ok,
)

# ------------------------------------------------------------------
# Gate 16 - Sectors
# ------------------------------------------------------------------
try:
    response = get("/api/v1/sectors")
    sectors_ok = response.status_code == 200
except Exception:
    sectors_ok = False

gate(
    16,
    "Sector endpoint works",
    sectors_ok,
)

# ------------------------------------------------------------------
# Gate 17 - Peer comparison
# ------------------------------------------------------------------
try:
    response = get("/api/v1/companies/HDFCBANK/peers/compare")

    peer_data = response.json()

    peer_ok = (
        response.status_code == 200
        and peer_data.get("peer_count", 0) > 0
    )

except Exception:
    peer_ok = False

gate(
    17,
    "Peer comparison endpoint works",
    peer_ok,
)

# ------------------------------------------------------------------
# Gate 18 - Portfolio statistics
# ------------------------------------------------------------------
try:
    response = get("/api/v1/portfolio/stats")

    portfolio_data = response.json()

    portfolio_ok = (
        response.status_code == 200
        and portfolio_data.get("company_count", 0) > 0
    )

except Exception:
    portfolio_ok = False

gate(
    18,
    "Portfolio statistics endpoint works",
    portfolio_ok,
)

# ------------------------------------------------------------------
# Gate 19 - Documents
# ------------------------------------------------------------------
try:
    response = get("/api/v1/companies/TCS/documents")

    documents_data = response.json()

    documents_ok = (
        response.status_code == 200
        and documents_data.get("count", 0) > 0
    )

except Exception:
    documents_ok = False

gate(
    19,
    "Company documents endpoint works",
    documents_ok,
)

# ------------------------------------------------------------------
# Gate 20 - Invalid ticker
# ------------------------------------------------------------------
try:
    response = get("/api/v1/companies/INVALIDTICKER")

    invalid_ticker_ok = response.status_code == 404

except Exception:
    invalid_ticker_ok = False

gate(
    20,
    "Invalid ticker correctly returns 404",
    invalid_ticker_ok,
)

# ------------------------------------------------------------------
# Final result
# ------------------------------------------------------------------
print("=" * 70)
print(f"PASSED: {passed}/20")
print(f"FAILED: {failed}/20")
print("=" * 70)

if failed == 0:
    print("FINAL RESULT: ALL 20 ACCEPTANCE GATES PASSED")
else:
    print("FINAL RESULT: ACCEPTANCE FAILED")

raise SystemExit(0 if failed == 0 else 1)