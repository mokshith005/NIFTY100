\# Sprint 1 Retrospective — NIFTY 100 Data Foundation



\## Sprint



Sprint 1 — Data Foundation



\## Goal



Build a reliable NIFTY 100 data foundation by ingesting 12 source Excel files, normalising the data, validating 16 data-quality rules, loading the data into SQLite, and preparing the foundation for downstream analytics.



\## Completed Work



\- Set up Python virtual environment and project structure.

\- Loaded 12 source Excel files:

&#x20; - 7 core datasets

&#x20; - 5 supplementary datasets

\- Implemented ETL loading and normalisation.

\- Implemented year and ticker normalisation.

\- Implemented 16 data-quality validation rules.

\- Generated validation reports.

\- Resolved all CRITICAL foreign-key/reference failures during ETL.

\- Created and validated SQLite schema.

\- Loaded all processed datasets into SQLite.

\- Enabled SQLite foreign-key enforcement.

\- Verified zero foreign-key violations.

\- Created analytics SQL queries.

\- Created exploratory SQL deliverable.

\- Completed a manual review of five representative companies.

\- Created the data dictionary.

\- Generated load-audit and validation reports.

\- Added processed datasets and outputs to GitHub.

\- Verified 78 ETL/unit tests with zero failures.



\## Final Database Metrics



| Metric | Result |

|---|---:|

| Source files | 12 |

| Database tables | 12 |

| Companies | 92 |

| Total loaded rows | 12,320 |

| Unit tests passed | 78 |

| Critical DQ failures | 0 |

| Foreign-key violations | 0 |

| Analytics queries validated | 21 |



\## Data Quality



All 16 DQ rules were executed.



The final validation run reported:



\- CRITICAL failures: 0

\- WARNING findings: 723



Warnings were retained in the validation report for transparency and further analysis. No CRITICAL failures remained after ETL reference cleaning.



\## Manual Review



Five companies were reviewed:



\- RELIANCE

\- TCS

\- HDFCBANK

\- INFY

\- ITC



The reviewed companies had consistent 2013–2024 coverage across the major historical financial datasets.



\## What Went Well



\- The ETL pipeline successfully converted the raw Excel datasets into structured processed CSV files.

\- Foreign-key integrity was successfully established after removing invalid raw references.

\- SQLite loading completed successfully with 12,320 rows.

\- Automated tests provided strong validation of the ETL components.

\- Analytics queries were tested directly against the SQLite database.

\- Project artifacts were version-controlled and pushed to GitHub.



\## Issues Encountered



\- Raw source files contained invalid company references.

\- Several datasets contained duplicate company/year combinations.

\- Some financial and market-quality rules produced WARNING-level findings.

\- The database initially used `database.db`; it was renamed to `nifty100.db` to match the Sprint specification.

\- Generated files were initially excluded by `.gitignore`; the configuration was updated so required processed datasets and validation outputs could be version-controlled.



\## Improvements for Next Sprint



\- Investigate remaining WARNING-level data-quality findings where business interpretation requires it.

\- Add stronger database constraints for natural keys where appropriate.

\- Expand automated validation coverage.

\- Build downstream analytics and reporting modules on top of the validated database.

\- Keep generated artifacts and source data clearly separated.



\## Sprint Outcome



Sprint 1 successfully established the core NIFTY 100 data foundation.



The database is loaded, foreign-key integrity is validated, all 16 DQ rules have been executed, CRITICAL failures have been resolved, and the ETL test suite passes with zero failures.



\*\*Sprint 1 status: Ready for review/sign-off.\*\*

