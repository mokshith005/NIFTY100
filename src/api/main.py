import logging
import sqlite3
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import (
    companies,
    documents,
    health,
    peers,
    portfolio,
    screener,
    sectors,
    valuation,
)

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

DB_PATH = "db/nifty100.db"

APP_VERSION = "1.0.0"

# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)

START_TIME = time.time()

# ---------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------

app = FastAPI(
    title="Nifty100 Analytics API",
    description="REST API for Nifty100 financial analytics",
    version=APP_VERSION,
)

# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------


@app.middleware("http")
async def request_logging(request: Request, call_next):
    start = time.time()

    response = await call_next(request)

    elapsed = time.time() - start

    logger.info(
        "%s %s -> %s (%.3fs)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )

    return response


# ---------------------------------------------------------
# Database health helper
# ---------------------------------------------------------


def get_db_row_counts():
    """Return row counts for the required project tables."""

    tables = [
        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "financial_ratios",
        "market_cap",
        "peer_groups",
        "peer_percentiles",
        "prosandcons",
        "documents",
    ]

    conn = sqlite3.connect(DB_PATH)

    try:
        counts = {}

        for table in tables:
            row = conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()

            counts[table] = row[0]

        return counts

    finally:
        conn.close()


# ---------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------


@app.get("/")
def root():
    return {
        "name": "Nifty100 Analytics API",
        "version": APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


# ---------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
        "db_row_counts": get_db_row_counts(),
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "version": APP_VERSION,
    }


# ---------------------------------------------------------
# API Routers
# ---------------------------------------------------------

API_PREFIX = "/api/v1"

app.include_router(
    companies.router,
    prefix=API_PREFIX,
    tags=["Companies"],
)

app.include_router(
    screener.router,
    prefix=API_PREFIX,
    tags=["Screener"],
)

app.include_router(
    sectors.router,
    prefix=API_PREFIX,
    tags=["Sectors"],
)

app.include_router(
    peers.router,
    prefix=API_PREFIX,
    tags=["Peers"],
)

app.include_router(
    valuation.router,
    prefix=API_PREFIX,
    tags=["Valuation"],
)

app.include_router(
    portfolio.router,
    prefix=API_PREFIX,
    tags=["Portfolio"],
)

app.include_router(
    documents.router,
    prefix=API_PREFIX,
    tags=["Documents"],
)

app.include_router(
    health.router,
    prefix=API_PREFIX,
    tags=["Health"],
)