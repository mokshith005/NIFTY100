from pathlib import Path
import sqlite3
import pandas as pd
import numpy as np


# =========================================================
# PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"
MARKET_CAP_PATH = PROJECT_ROOT / "market_cap.xlsx"

OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

SUMMARY_PATH = OUTPUT_DIR / "valuation_summary.xlsx"
FLAGS_PATH = OUTPUT_DIR / "valuation_flags.csv"


# =========================================================
# LOAD DATABASE DATA
# =========================================================

def load_database_data():
    conn = sqlite3.connect(DB_PATH)

    companies = pd.read_sql_query(
        """
        SELECT
            id AS company_id,
            company_name
        FROM companies
        """,
        conn,
    )

    sectors = pd.read_sql_query(
        """
        SELECT
            company_id,
            broad_sector AS sector
        FROM sectors
        """,
        conn,
    )

    market_data = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            market_cap_crore,
            pe_ratio,
            pb_ratio,
            ev_ebitda,
            dividend_yield_pct
        FROM market_cap
        """,
        conn,
    )

    ratios = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            free_cash_flow_cr
        FROM financial_ratios
        """,
        conn,
    )

    conn.close()

    return companies, sectors, market_data, ratios


# =========================================================
# LOAD MARKET CAP EXCEL
# =========================================================

def load_market_cap_excel():
    if not MARKET_CAP_PATH.exists():
        print(
            f"WARNING: {MARKET_CAP_PATH} not found. "
            "Using database market-cap data."
        )
        return None

    try:
        excel = pd.read_excel(MARKET_CAP_PATH)
        excel.columns = [
            str(c).strip()
            for c in excel.columns
        ]
        return excel
    except Exception as e:
        print(
            f"WARNING: Could not read market_cap.xlsx: {e}"
        )
        return None


# =========================================================
# CLEAN MARKET DATA
# =========================================================

def prepare_market_data(market_data):
    df = market_data.copy()

    df["year_num"] = pd.to_numeric(
        df["year"],
        errors="coerce",
    )

    # Keep latest available market record
    df = (
        df.sort_values(
            ["company_id", "year_num"],
            ascending=[True, False],
            na_position="last",
        )
        .drop_duplicates(
            "company_id",
            keep="first",
        )
    )

    return df


# =========================================================
# CLEAN FCF DATA
# =========================================================

def prepare_fcf_data(ratios):
    df = ratios.copy()

    df["year_num"] = pd.to_numeric(
        df["year"],
        errors="coerce",
    )

    df["free_cash_flow_cr"] = pd.to_numeric(
        df["free_cash_flow_cr"],
        errors="coerce",
    )

    df = (
        df.sort_values(
            ["company_id", "year_num"],
            ascending=[True, False],
            na_position="last",
        )
        .drop_duplicates(
            "company_id",
            keep="first",
        )
    )

    return df[
        [
            "company_id",
            "year_num",
            "free_cash_flow_cr",
        ]
    ]


# =========================================================
# PREPARE SECTORS
# =========================================================

def prepare_sectors(sectors):
    df = sectors.copy()

    df["sector"] = (
        df["sector"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
    )

    # One sector per company
    df = df.drop_duplicates(
        "company_id",
        keep="first",
    )

    return df


# =========================================================
# BUILD VALUATION DATA
# =========================================================

def build_valuation_data():
    (
        companies,
        sectors,
        market_data,
        ratios,
    ) = load_database_data()

    # ---------------------------------------------
    # Clean datasets
    # ---------------------------------------------

    market_latest = prepare_market_data(
        market_data
    )

    fcf_latest = prepare_fcf_data(
        ratios
    )

    sectors_clean = prepare_sectors(
        sectors
    )

    # ---------------------------------------------
    # Merge
    # ---------------------------------------------

    df = companies.merge(
        sectors_clean,
        on="company_id",
        how="left",
    )

    df = df.merge(
        market_latest[
            [
                "company_id",
                "year_num",
                "market_cap_crore",
                "pe_ratio",
                "pb_ratio",
                "ev_ebitda",
            ]
        ],
        on="company_id",
        how="left",
    )

    df = df.merge(
        fcf_latest[
            [
                "company_id",
                "free_cash_flow_cr",
            ]
        ],
        on="company_id",
        how="left",
    )

    # ---------------------------------------------
    # Rename
    # ---------------------------------------------

    df = df.rename(
        columns={
            "pe_ratio": "P/E",
            "pb_ratio": "P/B",
            "ev_ebitda": "EV/EBITDA",
        }
    )

    # ---------------------------------------------
    # Numeric conversion
    # ---------------------------------------------

    numeric_columns = [
        "market_cap_crore",
        "free_cash_flow_cr",
        "P/E",
        "P/B",
        "EV/EBITDA",
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        )

    # ---------------------------------------------
    # FCF Yield
    #
    # FCF Yield = FCF / Market Cap × 100
    # ---------------------------------------------

    df["FCF_yield_pct"] = np.where(
        (
            df["market_cap_crore"].notna()
            & (df["market_cap_crore"] > 0)
            & df["free_cash_flow_cr"].notna()
        ),
        (
            df["free_cash_flow_cr"]
            / df["market_cap_crore"]
            * 100
        ),
        np.nan,
    )

    # ---------------------------------------------
    # Sector median P/E
    # ---------------------------------------------

    valid_pe = df[
        df["P/E"].notna()
        & (df["P/E"] > 0)
        & np.isfinite(df["P/E"])
    ].copy()

    sector_medians = (
        valid_pe
        .groupby("sector")["P/E"]
        .median()
        .rename("5yr_median_PE")
        .reset_index()
    )

    df = df.merge(
        sector_medians,
        on="sector",
        how="left",
    )

    # ---------------------------------------------
    # PE vs sector median
    # ---------------------------------------------

    df["PE_vs_sector_median_pct"] = np.where(
        (
            df["P/E"].notna()
            & df["5yr_median_PE"].notna()
            & (df["5yr_median_PE"] > 0)
        ),
        (
            (
                df["P/E"]
                / df["5yr_median_PE"]
            ) - 1
        ) * 100,
        np.nan,
    )

    # ---------------------------------------------
    # Valuation flags
    #
    # > 1.5 × median = Caution
    # < 0.7 × median = Discount
    # otherwise Fair
    # ---------------------------------------------

    def valuation_flag(row):

        pe = row["P/E"]
        median = row["5yr_median_PE"]

        if (
            pd.isna(pe)
            or pd.isna(median)
            or median <= 0
            or pe <= 0
        ):
            return "N/A"

        if pe > median * 1.5:
            return "Caution"

        if pe < median * 0.7:
            return "Discount"

        return "Fair"

    df["flag"] = df.apply(
        valuation_flag,
        axis=1,
    )

    # ---------------------------------------------
    # Final columns
    # ---------------------------------------------

    final_columns = [
        "company_id",
        "company_name",
        "sector",
        "P/E",
        "P/B",
        "EV/EBITDA",
        "FCF_yield_pct",
        "5yr_median_PE",
        "PE_vs_sector_median_pct",
        "flag",
    ]

    for col in final_columns:
        if col not in df.columns:
            df[col] = np.nan

    return df[final_columns]


# =========================================================
# SAVE OUTPUTS
# =========================================================

def save_outputs(df):

    # ---------------------------------------------
    # Excel summary
    # ---------------------------------------------

    df.to_excel(
        SUMMARY_PATH,
        index=False,
    )

    # ---------------------------------------------
    # Flags CSV
    # ---------------------------------------------

    flags = df[
        df["flag"].isin(
            ["Caution", "Discount"]
        )
    ].copy()

    flags.to_csv(
        FLAGS_PATH,
        index=False,
    )

    return flags


# =========================================================
# MAIN
# =========================================================

def main():

    print("=" * 60)
    print("NIFTY 100 VALUATION ANALYSIS")
    print("=" * 60)

    print("\nLoading valuation data...")

    df = build_valuation_data()

    print(
        f"Companies analysed: {len(df)}"
    )

    print(
        f"Companies with FCF yield: "
        f"{df['FCF_yield_pct'].notna().sum()}"
    )

    print(
        f"Caution flags: "
        f"{(df['flag'] == 'Caution').sum()}"
    )

    print(
        f"Discount flags: "
        f"{(df['flag'] == 'Discount').sum()}"
    )

    print(
        f"Fair valuations: "
        f"{(df['flag'] == 'Fair').sum()}"
    )

    print(
        f"N/A valuations: "
        f"{(df['flag'] == 'N/A').sum()}"
    )

    flags = save_outputs(df)

    print("\nOutputs created:")
    print(
        f"  {SUMMARY_PATH}"
    )
    print(
        f"  {FLAGS_PATH}"
    )

    print("\nSample:")
    print(
        df.head(10).to_string(
            index=False
        )
    )

    print("\n" + "=" * 60)
    print("VALUATION ANALYSIS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()