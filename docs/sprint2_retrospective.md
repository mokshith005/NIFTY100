\# SPRINT 2 RETROSPECTIVE



\## Epic

Epic 02 — Financial Ratio Engine



\## Sprint

Sprint 2 — Days 08–14



\## Sprint Goal



Implement and validate the financial ratio engine for the NIFTY 100

financial intelligence platform, including profitability, leverage,

efficiency, CAGR, cash-flow KPIs, capital allocation and edge-case

handling.



\## Completed Work



\### Profitability Ratios

\- Net Profit Margin

\- Operating Profit Margin

\- ROE

\- ROCE

\- ROA

\- OPM source cross-check



\### Leverage \& Efficiency

\- Debt-to-Equity

\- Interest Coverage Ratio

\- Interest Coverage warning

\- Debt Free label

\- Net Debt

\- Asset Turnover

\- High leverage flag



\### CAGR Engine

\- Revenue CAGR

\- PAT CAGR

\- EPS CAGR

\- 3/5/10-year CAGR framework

\- Zero-base handling

\- Turnaround handling

\- Decline-to-loss handling

\- Both-negative handling

\- Insufficient-history handling



\### Cash Flow KPIs

\- Free Cash Flow

\- CFO/PAT quality score

\- CapEx intensity

\- FCF conversion

\- Capital allocation classification



\### Database

\- Financial ratio KPI columns added

\- Ratio engine populated the database

\- Duplicate company/year records identified

\- Duplicate records removed

\- Backup table created

\- Final database contains one row per company/year



\### Edge Cases

\- Financial-sector leverage carve-out implemented

\- ROE source anomalies documented

\- ROCE source anomalies documented

\- TCS source anomaly documented

\- Ratio-engine values retained for analytics



\## Validation Results



\- Unit tests: 130 passed

\- Final financial ratio rows: 1,029

\- Distinct company/year pairs: 1,029

\- Duplicate pairs: 0

\- Foreign-key errors: 0

\- Financial-sector companies: 23

\- Financial-sector high-leverage flags: 0

\- Financial-sector carve-out: PASS

\- Manual ROE spot-check: 3/3 PASS

\- Manual 5-year Revenue CAGR spot-check: 3/3 PASS

\- Screener result: 29 companies

\- Screener requirement: 15–50

\- Screener status: PASS



\## Data Volume Note



The source data contains:

\- P\&L unique company/year records: 1,061

\- Balance Sheet unique company/year records: 1,046

\- Cash Flow unique company/year records: 1,044

\- Financial ratio unique company/year records: 1,029



The 1,100+ ratio-row target cannot be achieved from the available

unique source company/year records without introducing duplicate

records. Duplicate records were therefore removed to preserve

data integrity.



\## Key Formula Decisions



\- ROE returns None for zero or negative equity.

\- Debt-free companies receive D/E = 0.

\- Zero-interest companies receive ICR = None and "Debt Free" label.

\- Financial-sector high leverage warnings are suppressed.

\- CAGR edge cases return explicit flags.

\- Ratio-engine calculations are used for analytics when source

&#x20; ratio values conflict.

\- Source ratio values are retained for display/comparison.



\## Files Created/Updated



\- src/analytics/ratios.py

\- src/analytics/cagr.py

\- src/analytics/cashflow\_kpis.py

\- src/analytics/capital\_allocation.py

\- src/analytics/populate\_ratios.py

\- src/analytics/ratio\_edge\_cases.py

\- src/analytics/anomaly\_summary.py

\- tests/kpi/

\- output/capital\_allocation.csv

\- output/ratio\_edge\_cases.log

\- output/anomaly\_summary.log

\- cleanup\_ratio\_duplicates.py



\## Sprint Outcome



Sprint 2 technical implementation and validation are complete.



The ratio engine, KPI calculations, edge-case handling, database

integrity checks and screener validation have passed.



The only unmet numeric specification is the 1,100+ ratio-row target,

which is constrained by the available unique source data. No

duplicate or fabricated records were introduced to satisfy the

target.



\## Status



SPRINT 2 — COMPLETE

