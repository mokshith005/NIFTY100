# 📊 Nifty 100 Analytics Dashboard

> **An end-to-end financial analytics platform for fundamental analysis, valuation, screening, peer comparison, cash-flow intelligence, NLP-based signals, and company clustering across the Nifty 100 universe.**

---

## 🚀 Overview

The **Nifty 100 Analytics Dashboard** is a comprehensive financial analytics platform designed to transform raw financial datasets into structured, interactive, and analyst-friendly insights.

The project combines **data engineering, financial analytics, database management, machine learning, natural language processing, interactive visualization, and API development** into a single workflow.

The platform currently represents **92 Nifty 100 companies** in the project database and provides tools for:

* 📈 Financial ratio analysis
* 🔎 Company screening
* 🤝 Peer comparison
* 💰 Valuation analysis
* 💵 Cash-flow intelligence
* 🧠 NLP-based pros/cons extraction
* 🔬 KMeans company clustering
* 📊 Interactive Streamlit dashboard
* ⚡ FastAPI analytical endpoints
* 🧪 Automated testing with pytest
* 📑 Excel, CSV, HTML and PDF reporting

The objective is to provide a **reproducible analytical workflow** that helps users move from raw financial data to structured company-level analysis.

---

## 🎯 Project Objectives

The major objectives of the project are:

1. Build a reliable financial-data ingestion and processing pipeline.
2. Store structured financial information in a centralized SQLite database.
3. Calculate and analyze fundamental financial ratios.
4. Develop configurable company screening capabilities.
5. Provide peer-based comparative analysis.
6. Generate valuation summaries and analytical flags.
7. Analyze cash-flow characteristics.
8. Extract structured pros and cons from company-analysis text using NLP.
9. Identify groups of similar companies using KMeans clustering.
10. Provide an interactive Streamlit dashboard.
11. Expose selected analytics through a FastAPI layer.
12. Validate the system using automated tests and QA reports.

---

## 🏗️ System Architecture

```text
                    ┌─────────────────────┐
                    │    Raw Excel Data   │
                    │      CSV / Files     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    ETL Pipeline     │
                    │ Cleaning & Transform │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    SQLite Database  │
                    │   nifty100.db       │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼─────────────────┐
              │                │                 │
              ▼                ▼                 ▼
       ┌────────────┐   ┌────────────┐   ┌────────────┐
       │ Ratio      │   │ Screener   │   │ Peer       │
       │ Engine     │   │ Engine     │   │ Engine     │
       └─────┬──────┘   └─────┬──────┘   └─────┬──────┘
             │                │                 │
             └────────────────┼─────────────────┘
                              ▼
                    ┌─────────────────────┐
                    │ Advanced Analytics  │
                    │ Valuation / Cashflow│
                    │ NLP / Clustering    │
                    └──────────┬──────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
                ▼                             ▼
       ┌─────────────────┐          ┌─────────────────┐
       │ Streamlit       │          │ FastAPI         │
       │ Dashboard       │          │ API Layer       │
       └─────────────────┘          └─────────────────┘
                │                             │
                └──────────────┬──────────────┘
                               ▼
                    ┌─────────────────────┐
                    │ Reports & Exports   │
                    │ CSV / XLSX / HTML   │
                    │ PDF                 │
                    └─────────────────────┘
```

---

## ✨ Key Features

### 1. 📥 Data Engineering & ETL

The project processes multiple financial source files and converts them into structured, analysis-ready datasets.

The ETL workflow includes:

* Source-file loading
* Data cleaning
* Column standardization
* Data transformation
* Validation
* Database insertion
* Processed-data generation

Processed datasets are maintained separately from raw data to improve reproducibility.

---

### 2. 🗄️ SQLite Financial Database

The project uses **SQLite** as the central analytical database.

Database:

```text
db/nifty100.db
```

Major database areas include:

| Table              | Purpose                         |
| ------------------ | ------------------------------- |
| `companies`        | Company master information      |
| `sectors`          | Sector classification           |
| `analysis`         | Company analysis content        |
| `balancesheet`     | Balance-sheet information       |
| `profitandloss`    | Profit and loss information     |
| `cashflow`         | Cash-flow information           |
| `financial_ratios` | Calculated financial ratios     |
| `market_cap`       | Market capitalization           |
| `stock_prices`     | Stock-price information         |
| `peer_groups`      | Peer relationships              |
| `peer_percentiles` | Relative peer metrics           |
| `documents`        | Supporting document information |
| `prosandcons`      | NLP-generated signals           |

---

### 3. 📊 Financial Ratio Engine

The ratio engine calculates fundamental financial indicators across the company universe.

Ratio categories include:

* Profitability
* Liquidity
* Leverage
* Efficiency
* Valuation
* Coverage metrics

The project generated approximately **1,160 financial-ratio records** during the validation cycle.

The ratio engine also includes handling for:

* Missing values
* Zero denominators
* Edge cases
* Invalid financial inputs
* Data-quality exceptions

---

### 4. 🔎 Stock Screener

The screener allows users to filter companies based on financial conditions.

Implemented analytical presets include:

| Preset              | Observed Companies |
| ------------------- | -----------------: |
| Quality Compounder  |                 23 |
| Value Pick          |                  1 |
| Growth Accelerator  |                 18 |
| Dividend Champion   |                 30 |
| Debt Free Blue Chip |                 18 |
| Turnaround Watch    |                 33 |

Users can combine financial conditions to create customized screening workflows.

> Preset names describe analytical filters implemented in the project and should not be interpreted as investment recommendations.

---

### 5. 🤝 Peer Comparison Engine

The peer-analysis module compares companies against relevant peer groups.

It supports analysis of:

* Profitability
* Leverage
* Efficiency
* Valuation
* Financial ratios
* Percentile positioning

Generated output:

```text
output/peer_comparison.xlsx
```

Peer analysis provides additional context for interpreting individual company metrics.

---

### 6. 💰 Valuation Analytics

The valuation module consolidates valuation-related metrics and generates structured valuation outputs.

Key outputs:

```text
output/valuation_summary.xlsx
output/valuation_flags.csv
```

The valuation module supports analysis of:

* Market-based multiples
* Relative valuation
* Company-level valuation metrics
* Valuation observations
* Outlier identification

Valuation metrics should always be interpreted with profitability, growth, leverage, cash flow and sector context.

---

### 7. 💵 Cash-Flow Intelligence

The project includes a dedicated cash-flow analytics layer.

The module analyzes:

* Operating cash flow
* Investing cash flow
* Financing cash flow
* Cash-flow KPIs
* Earnings versus cash-generation patterns

Implementation includes:

```text
src/analytics/cashflow_kpis.py
```

The purpose is to provide an additional perspective beyond accounting profitability.

---

### 8. 🧠 NLP-Based Pros & Cons Analysis

The project includes an NLP pipeline for extracting structured signals from company-analysis text.

Workflow:

```text
analysis.xlsx
      ↓
Text Parsing
      ↓
analysis_parsed.csv
      ↓
NLP Signal Extraction
      ↓
pros_cons_generated.csv
```

Observed project output:

| Metric             | Value |
| ------------------ | ----: |
| Total signals      |   874 |
| Pros               |   562 |
| Cons               |   312 |
| Minimum confidence |    65 |

NLP signals are designed to assist analysts in identifying textual themes and should be validated against the original source content.

---

### 9. 🔬 KMeans Company Clustering

The project uses **KMeans clustering** to group companies according to selected financial and analytical characteristics.

Five project-defined clusters were generated:

| Cluster                   | Companies |
| ------------------------- | --------: |
| Value Cyclicals           |        45 |
| Emerging Growth           |        19 |
| High-Quality Compounders  |        15 |
| Defensive Dividend Payers |        11 |
| Distressed or Turnaround  |         2 |

The clustering module helps identify companies with similar analytical profiles.

Cluster labels are descriptive and depend on the selected features, preprocessing and model configuration.

---

## 📊 Dashboard

The project includes an interactive **Streamlit dashboard** for exploring the analytical results.

Major dashboard areas include:

```text
Home
Company Analysis
Financial Ratios
Screener
Peer Comparison
Valuation
Cash Flow
NLP / Pros & Cons
Clustering
Reports
```

The dashboard allows users to interact with the dataset rather than relying only on static reports.

---

## ⚡ FastAPI

The project also contains a FastAPI layer for programmatic access to selected analytics.

The API supports functionality such as:

* Sector information
* Peer-related queries
* Analytical data retrieval

API validation was performed during the project QA cycle using endpoint checks.

---

## 🧪 Testing & Quality Assurance

The project uses **pytest** for automated testing.

Testing covers areas such as:

* Data validation
* Database integrity
* Financial-ratio calculations
* Edge cases
* Screener logic
* Peer analysis
* Valuation outputs
* Clustering
* API endpoints
* Regression checks

Generate the HTML test report using:

```bash
pytest --html=reports/pytest_report.html --self-contained-html
```

The generated report is stored at:

```text
reports/pytest_report.html
```

---

## 📁 Project Structure

```text
nifty100/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── db/
│   └── nifty100.db
│
├── src/
│   ├── analytics/
│   ├── api/
│   ├── dashboard/
│   ├── data/
│   └── ...
│
├── tests/
│
├── notebooks/
│
├── output/
│   ├── screener_output.xlsx
│   ├── peer_comparison.xlsx
│   ├── valuation_summary.xlsx
│   ├── valuation_flags.csv
│   ├── cluster_labels.csv
│   └── pros_cons_generated.csv
│
├── reports/
│   └── pytest_report.html
│
├── docs/
│   └── analyst_guide.pdf
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 🛠️ Technology Stack

| Category         | Technology          |
| ---------------- | ------------------- |
| Programming      | Python              |
| Data Processing  | Pandas, NumPy       |
| Database         | SQLite              |
| Visualization    | Plotly              |
| Dashboard        | Streamlit           |
| API              | FastAPI             |
| Machine Learning | Scikit-learn        |
| NLP              | Python NLP pipeline |
| Testing          | pytest              |
| Data Files       | Excel, CSV          |
| Documentation    | PDF, Markdown       |
| Version Control  | Git & GitHub        |

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd nifty100
```

### 2. Create a virtual environment

Windows:

```bash
python -m venv venv
```

Activate it:

```bash
venv\Scripts\activate
```

Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## ▶️ Running the Dashboard

From the project root:

```bash
streamlit run src/dashboard/app.py
```

The Streamlit interface will open in the browser.

---

## ⚡ Running the API

Run the FastAPI application according to the project's API entry point.

Example:

```bash
uvicorn src.api.main:app --reload
```

The API can then be accessed through the local server.

---

## 🧪 Running Tests

Run the complete test suite:

```bash
pytest -v
```

Generate the HTML report:

```bash
pytest --html=reports/pytest_report.html --self-contained-html
```

---

## 🧹 Project Cleanup

Python cache files should not be committed to GitHub.

The project `.gitignore` should contain:

```gitignore
# Virtual environment
venv/
.venv/

# Python cache
__pycache__/
*.py[cod]
*.pyo

# Pytest
.pytest_cache/

# Jupyter
.ipynb_checkpoints/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Environment variables
.env
```

---

## 📑 Documentation

The project includes a detailed professional analyst guide:

```text
docs/analyst_guide.pdf
```

The guide covers:

* Platform architecture
* Data flow
* Database structure
* Financial ratios
* Screener
* Peer comparison
* Valuation
* Cash-flow analytics
* NLP signals
* Clustering
* API
* Testing
* QA
* Analyst workflow
* Best practices
* Limitations

---

## 📈 Project Outputs

Major generated outputs include:

```text
output/
├── screener_output.xlsx
├── peer_comparison.xlsx
├── valuation_summary.xlsx
├── valuation_flags.csv
├── cluster_labels.csv
├── pros_cons_generated.csv
├── capital_allocation.csv
├── final_analytics_summary.xlsx
└── ...
```

These files provide reusable analytical results for further reporting and review.

---

## 🔍 Data Quality

Data quality is treated as an important part of the pipeline.

The project includes checks for:

* Missing records
* Invalid values
* Duplicate records
* Ratio calculation errors
* Edge cases
* Incomplete company coverage
* API response issues
* Dashboard regression issues

During validation, **ATGL** and **SBIN** were identified as companies without corresponding ratio records.

These are retained as explicit data-quality exceptions rather than being filled with fabricated values.

---

## 🧠 Analytical Workflow

The recommended workflow is:

```text
Data Validation
      ↓
Company Overview
      ↓
Financial Ratios
      ↓
Screener
      ↓
Peer Comparison
      ↓
Valuation
      ↓
Cash-Flow Analysis
      ↓
NLP Signals
      ↓
Clustering
      ↓
Export & Reporting
```

This workflow encourages analysts to validate data before interpreting results.

---

## 📌 Key Project Metrics

| Metric                      |                Value |
| --------------------------- | -------------------: |
| Companies                   |                   92 |
| Financial Ratio Rows        |                1,160 |
| NLP Signals                 |                  874 |
| NLP Pros                    |                  562 |
| NLP Cons                    |                  312 |
| Clusters                    |                    5 |
| Largest Cluster             | Value Cyclicals — 45 |
| Ratio Exceptions Identified |                    2 |

---

## ⚠️ Limitations

This project is an analytical and educational platform. Results depend on:

* Source-data quality
* Reporting periods
* Data completeness
* Financial definitions
* Market-data availability
* Feature engineering
* Model configuration
* NLP extraction quality

Automated screeners, valuation flags, NLP signals and clustering results should be treated as **decision-support outputs requiring human review**.

---

## 🔮 Future Enhancements

Potential future improvements include:

* Real-time market-data integration
* Automated scheduled data refresh
* Additional valuation models
* Historical time-series dashboards
* Advanced portfolio optimization
* More sophisticated NLP models
* Explainable clustering
* User authentication
* Cloud deployment
* Docker containerization
* CI/CD testing with GitHub Actions
* Automated report generation
* Expanded Nifty universe coverage

---

## 👨‍💻 Development & Contribution

A typical development workflow is:

```bash
git pull
```

Make changes, test them, then:

```bash
pytest -v
```

Review the results and commit:

```bash
git add .
git commit -m "Update analytics module"
git push origin master
```

Before pushing, ensure that:

* Tests pass
* No Python cache files are included
* No credentials or `.env` files are committed
* Generated documentation is updated when necessary
* Database changes are documented

---

## 📄 License

This project can be distributed under the license selected by the project owner.

If this repository is intended for academic/internship submission, add the institution's required license or project-use statement here.

---

## ⭐ Project Summary

**Nifty 100 Analytics Dashboard** demonstrates an end-to-end approach to financial data analytics by combining:

```text
Data Engineering
       +
Financial Analytics
       +
Machine Learning
       +
Natural Language Processing
       +
Interactive Visualization
       +
API Development
       +
Automated Testing
       =
End-to-End Financial Analytics Platform
```

The project is designed to make financial analysis **structured, reproducible, interactive and easier to investigate** while keeping data quality and analytical context at the center of the workflow.

---

### 📬 Documentation

For detailed usage instructions and analytical methodology, refer to:

```text
docs/analyst_guide.pdf
```

For automated QA results:

```text
reports/pytest_report.html
```

---

**Built as an internship capstone project for Nifty 100 financial analytics.**


