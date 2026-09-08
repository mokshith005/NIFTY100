\# Sprint 6 Retrospective



\## Sprint Overview



Sprint 6 completed the advanced analytics, clustering, REST API, automated testing,

performance validation, and documentation requirements for the Nifty100 Analytics project.



\## Completed Work



\### Day 36 — KMeans Clustering

\- Applied KMeans clustering to 92 Nifty100 companies.

\- Identified 5 company archetypes.

\- Generated cluster labels and supporting analysis.

\- Created elbow plot for cluster selection.



\### Day 37 — Cluster Analysis

\- Generated cluster mean and median profiles.

\- Created correlation heatmap.

\- Identified 3 statistical outliers.

\- Generated portfolio statistics.



\### Day 38 — API Foundation

\- Implemented FastAPI application.

\- Added API versioning under `/api/v1`.

\- Added CORS and request logging.

\- Added health monitoring endpoint.



\### Day 39 — Company Endpoints

Implemented company-level endpoints for:

\- Company listing and details

\- Profit \& Loss

\- Balance Sheet

\- Cash Flow

\- Financial Ratios

\- Company tearsheet



\### Day 40 — Remaining API Endpoints

Implemented:

\- Screener

\- Sectors

\- Sector companies

\- Peer groups

\- Peer comparison

\- Market capitalization

\- Portfolio statistics

\- Company documents



Total API coverage: 16 API endpoints.



\### Day 41 — Automated Testing

\- Existing project tests verified.

\- Test suite expanded with API coverage.

\- Full test suite successfully executed.



\### Day 42 — API / Integration Testing

\- Added 45 API tests.

\- Validated successful responses, error handling, filters,

&#x20; company data, peers, sectors, documents, and portfolio statistics.



\### Day 43 — Performance Testing

\- Tested all 16 API endpoints.

\- Single-request average latency: approximately 11 ms.

\- Maximum single-request latency: approximately 22 ms.

\- Concurrent load test: 80/80 successful requests.

\- Throughput: approximately 442 requests/second.



\### Day 44 — Documentation \& Quality

\- OpenAPI specification generated.

\- Postman collection generated.

\- Clustering outputs and visual reports archived.

\- API and performance test suites included.

\- Full automated test suite verified with 179 passing tests.



\## Final Sprint Metrics



| Metric | Result |

|---|---:|

| Companies analyzed | 92 |

| KMeans clusters | 5 |

| API endpoints | 16 |

| Total pytest tests | 179 |

| API tests | 45 |

| Performance tests | 4 |

| Test failures | 0 |

| Concurrent requests tested | 80 |

| Concurrent success rate | 100% |

| Approx. throughput | 442 req/s |



\## Known Warning



The test suite currently reports one Starlette/AnyIO deprecation warning.

It does not cause test failures and does not affect application functionality.



\## Sprint Outcome



Sprint 6 successfully delivered the planned advanced analytics and API layer,

with automated validation and performance verification completed.



The project is ready for final acceptance-gate verification and Sprint 6 sign-off.

