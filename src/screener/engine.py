
"""
Financial Screener Engine for the NIFTY 100 data foundation.

Sprint 3 Screener

Provides:
- Data loading from SQLite
- Latest financial data per company
- Financial filtering
- Valuation filtering
- Growth filtering
- Debt / leverage filtering
- Financial-sector D/E exception
- Preset screeners
- Ranking and scoring
- CAGR calculations
- Quality scoring
- One-row-per-company output
"""

from pathlib import Path
import sqlite3

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    ROOT_DIR
    / "db"
    / "nifty100.db"
)


class ScreenerEngine:
    """Financial screener engine for Sprint 3."""

    def __init__(
        self,
        db_path: str | Path = DATABASE_PATH,
    ):
        self.db_path = Path(db_path)

    # ============================================================
    # BASIC HELPERS
    # ============================================================

    @staticmethod
    def _numeric(series):
        """Convert a pandas Series to numeric safely."""

        return pd.to_numeric(
            series,
            errors="coerce",
        )

    @staticmethod
    def _safe_divide(numerator, denominator):
        """Safely divide two numeric Series."""

        numerator = pd.to_numeric(
            numerator,
            errors="coerce",
        )

        denominator = pd.to_numeric(
            denominator,
            errors="coerce",
        )

        result = numerator / denominator

        result = result.replace(
            [float("inf"), float("-inf")],
            float("nan"),
        )

        return result

    # ============================================================
    # LOAD DATA
    # ============================================================

    def load_data(self):
        """
        Load the latest available financial data for each company.

        Sources:
        - financial_ratios
        - market_cap
        - profitandloss
        - balancesheet
        - sectors

        Calculated fields:
        - previous_debt_to_equity
        - debt_to_equity_declining
        - revenue_cagr_3yr
        - revenue_cagr_5yr
        - pat_cagr_5yr
        - eps_cagr_5yr
        - effective_interest_coverage
        - roce_pct
        - composite_quality_score
        """

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Database not found: {self.db_path}"
            )

        # ========================================================
        # LOAD LATEST FINANCIAL RATIOS
        # ========================================================

        with sqlite3.connect(self.db_path) as connection:

            ratios_query = """
                SELECT
                    fr.*
                FROM financial_ratios fr
                INNER JOIN (
                    SELECT
                        company_id,
                        MAX(CAST(year AS REAL)) AS latest_year
                    FROM financial_ratios
                    GROUP BY company_id
                ) latest
                    ON fr.company_id = latest.company_id
                    AND CAST(fr.year AS REAL) = latest.latest_year
            """

            ratios = pd.read_sql_query(
                ratios_query,
                connection,
            )

        if ratios.empty:
            raise ValueError(
                "No financial ratio records found."
            )

        # ========================================================
        # IMPORTANT:
        # Some source files contain multiple records for the same
        # company/year. Keep exactly one latest record per company.
        # ========================================================

        ratios["year"] = pd.to_numeric(
            ratios["year"],
            errors="coerce",
        )

        ratios = (
            ratios
            .sort_values(
                ["company_id", "year", "id"],
                ascending=[True, False, True],
                na_position="last",
            )
            .drop_duplicates(
                subset=["company_id"],
                keep="first",
            )
            .reset_index(drop=True)
        )

        # ========================================================
        # LOAD MARKET CAP
        # ========================================================

        with sqlite3.connect(self.db_path) as connection:

            market_query = """
                SELECT
                    mc.*
                FROM market_cap mc
                INNER JOIN (
                    SELECT
                        company_id,
                        MAX(CAST(year AS REAL)) AS latest_year
                    FROM market_cap
                    GROUP BY company_id
                ) latest
                    ON mc.company_id = latest.company_id
                    AND CAST(mc.year AS REAL) = latest.latest_year
            """

            market = pd.read_sql_query(
                market_query,
                connection,
            )

        market["year"] = pd.to_numeric(
            market["year"],
            errors="coerce",
        )

        market = (
            market
            .sort_values(
                ["company_id", "year", "id"],
                ascending=[True, False, True],
                na_position="last",
            )
            .drop_duplicates(
                subset=["company_id"],
                keep="first",
            )
            .reset_index(drop=True)
        )

        # ========================================================
        # LOAD LATEST P&L
        # ========================================================

        with sqlite3.connect(self.db_path) as connection:

            pnl_latest_query = """
                SELECT
                    pl.*
                FROM profitandloss pl
                INNER JOIN (
                    SELECT
                        company_id,
                        MAX(CAST(year AS REAL)) AS latest_year
                    FROM profitandloss
                    GROUP BY company_id
                ) latest
                    ON pl.company_id = latest.company_id
                    AND CAST(pl.year AS REAL) = latest.latest_year
            """

            pnl_latest = pd.read_sql_query(
                pnl_latest_query,
                connection,
            )

        pnl_latest["year"] = pd.to_numeric(
            pnl_latest["year"],
            errors="coerce",
        )

        pnl_latest = (
            pnl_latest
            .sort_values(
                ["company_id", "year", "id"],
                ascending=[True, False, True],
                na_position="last",
            )
            .drop_duplicates(
                subset=["company_id"],
                keep="first",
            )
            .reset_index(drop=True)
        )

        # ========================================================
        # LOAD HISTORICAL P&L
        # ========================================================

        with sqlite3.connect(self.db_path) as connection:

            pnl_history = pd.read_sql_query(
                """
                SELECT
                    company_id,
                    CAST(year AS REAL) AS year,
                    sales,
                    net_profit,
                    eps
                FROM profitandloss
                """,
                connection,
            )

        if not pnl_history.empty:

            pnl_history["year"] = pd.to_numeric(
                pnl_history["year"],
                errors="coerce",
            )

            pnl_history["sales"] = pd.to_numeric(
                pnl_history["sales"],
                errors="coerce",
            )

            pnl_history["net_profit"] = pd.to_numeric(
                pnl_history["net_profit"],
                errors="coerce",
            )

            pnl_history["eps"] = pd.to_numeric(
                pnl_history["eps"],
                errors="coerce",
            )

            pnl_history = (
                pnl_history
                .dropna(
                    subset=[
                        "company_id",
                        "year",
                    ]
                )
                .sort_values(
                    [
                        "company_id",
                        "year",
                    ]
                )
                .drop_duplicates(
                    subset=[
                        "company_id",
                        "year",
                    ],
                    keep="last",
                )
                .reset_index(drop=True)
            )

        # ========================================================
        # LOAD BALANCE SHEET
        # ========================================================

        with sqlite3.connect(self.db_path) as connection:

            bs_query = """
                SELECT *
                FROM balancesheet
            """

            balancesheet = pd.read_sql_query(
                bs_query,
                connection,
            )

        if not balancesheet.empty:

            balancesheet["year"] = pd.to_numeric(
                balancesheet["year"],
                errors="coerce",
            )

            balancesheet = (
                balancesheet
                .sort_values(
                    [
                        "company_id",
                        "year",
                        "id",
                    ],
                    ascending=[
                        True,
                        False,
                        True,
                    ],
                    na_position="last",
                )
                .drop_duplicates(
                    subset=["company_id"],
                    keep="first",
                )
                .reset_index(drop=True)
            )

        # ========================================================
        # LOAD SECTORS
        # ========================================================

        with sqlite3.connect(self.db_path) as connection:

            sectors = pd.read_sql_query(
                """
                SELECT
                    company_id,
                    broad_sector,
                    sub_sector,
                    index_weight_pct,
                    market_cap_category
                FROM sectors
                """,
                connection,
            )

        sectors = (
            sectors
            .drop_duplicates(
                subset=["company_id"],
                keep="first",
            )
            .reset_index(drop=True)
        )

        # ========================================================
        # MERGE DATA
        # ========================================================

        df = ratios.copy()

        market_columns = [
            "company_id",
            "market_cap_crore",
            "pe_ratio",
            "pb_ratio",
            "ev_ebitda",
            "dividend_yield_pct",
        ]

        market_columns = [
            column
            for column in market_columns
            if column in market.columns
        ]

        if len(market_columns) > 1:

            df = df.merge(
                market[market_columns],
                on="company_id",
                how="left",
                suffixes=("", "_market"),
            )

        pnl_columns = [
            "company_id",
            "sales",
            "net_profit",
            "eps",
            "dividend_payout",
        ]

        pnl_columns = [
            column
            for column in pnl_columns
            if column in pnl_latest.columns
        ]

        if len(pnl_columns) > 1:

            pnl_latest_small = pnl_latest[
                pnl_columns
            ].copy()

            pnl_latest_small = pnl_latest_small.rename(
                columns={
                    "sales": "sales_cr",
                    "net_profit": "pnl_net_profit_cr",
                    "eps": "pnl_eps",
                    "dividend_payout":
                        "dividend_payout_ratio",
                }
            )

            df = df.merge(
                pnl_latest_small,
                on="company_id",
                how="left",
            )

        if not balancesheet.empty:

            bs_columns = [
                "company_id",
                "total_assets",
                "total_debt",
                "equity_capital",
                "reserves",
            ]

            bs_columns = [
                column
                for column in bs_columns
                if column in balancesheet.columns
            ]

            if len(bs_columns) > 1:

                bs_small = balancesheet[
                    bs_columns
                ].copy()

                df = df.merge(
                    bs_small,
                    on="company_id",
                    how="left",
                    suffixes=("", "_bs"),
                )

        sector_columns = [
            "company_id",
            "broad_sector",
            "sub_sector",
            "index_weight_pct",
            "market_cap_category",
        ]

        sector_columns = [
            column
            for column in sector_columns
            if column in sectors.columns
        ]

        if len(sector_columns) > 1:

            df = df.merge(
                sectors[sector_columns],
                on="company_id",
                how="left",
            )

        # ========================================================
        # REMOVE ANY MERGE-CAUSED DUPLICATES
        # ========================================================

        df = (
            df
            .sort_values(
                [
                    "company_id",
                    "year",
                ],
                ascending=[
                    True,
                    False,
                ],
                na_position="last",
            )
            .drop_duplicates(
                subset=["company_id"],
                keep="first",
            )
            .reset_index(drop=True)
        )

        # ========================================================
        # PREVIOUS DEBT TO EQUITY
        # ========================================================

        with sqlite3.connect(self.db_path) as connection:

            debt_history = pd.read_sql_query(
                """
                SELECT
                    company_id,
                    CAST(year AS REAL) AS year,
                    debt_to_equity
                FROM financial_ratios
                """,
                connection,
            )

        if not debt_history.empty:

            debt_history["year"] = pd.to_numeric(
                debt_history["year"],
                errors="coerce",
            )

            debt_history["debt_to_equity"] = (
                pd.to_numeric(
                    debt_history["debt_to_equity"],
                    errors="coerce",
                )
            )

            debt_history = (
                debt_history
                .sort_values(
                    [
                        "company_id",
                        "year",
                    ]
                )
                .drop_duplicates(
                    subset=[
                        "company_id",
                        "year",
                    ],
                    keep="last",
                )
            )

            previous_de = (
                debt_history
                .groupby("company_id")[
                    "debt_to_equity"
                ]
                .shift(1)
            )

            latest_de = (
                debt_history
                .sort_values(
                    [
                        "company_id",
                        "year",
                    ]
                )
                .groupby("company_id")
                .tail(1)
                .set_index("company_id")[
                    "debt_to_equity"
                ]
            )

            previous_map = {}

            for company_id, group in (
                debt_history
                .groupby("company_id")
            ):

                group = group.sort_values(
                    "year"
                )

                if len(group) >= 2:

                    previous_map[
                        company_id
                    ] = group.iloc[-2][
                        "debt_to_equity"
                    ]

            df["previous_debt_to_equity"] = (
                df["company_id"]
                .map(previous_map)
            )

        else:

            df["previous_debt_to_equity"] = (
                float("nan")
            )

        current_de = self._numeric(
            df["debt_to_equity"]
        )

        previous_de = self._numeric(
            df["previous_debt_to_equity"]
        )

        df["debt_to_equity_declining"] = (
            current_de < previous_de
        )

        # ========================================================
        # CAGR CALCULATOR
        # ========================================================

        def calculate_cagr(
            company_id,
            latest_year,
            value_column,
            years=5,
        ):
            """
            Calculate CAGR from historical P&L data.

            Uses the latest available positive value and the
            closest available positive value at least N years earlier.
            """

            if pnl_history.empty:
                return float("nan")

            company_data = pnl_history[
                pnl_history["company_id"]
                == company_id
            ].sort_values(
                "year"
            )

            if company_data.empty:
                return float("nan")

            latest_rows = company_data[
                company_data["year"]
                <= latest_year
            ]

            if latest_rows.empty:
                return float("nan")

            latest_row = latest_rows.iloc[-1]

            latest_value = pd.to_numeric(
                latest_row[value_column],
                errors="coerce",
            )

            actual_latest_year = (
                latest_row["year"]
            )

            if pd.isna(latest_value):
                return float("nan")

            if latest_value <= 0:
                return float("nan")

            historical_rows = company_data[
                company_data["year"]
                <= actual_latest_year - years
            ].copy()

            historical_rows = historical_rows[
                pd.to_numeric(
                    historical_rows[value_column],
                    errors="coerce",
                ) > 0
            ]

            if historical_rows.empty:
                return float("nan")

            historical_row = (
                historical_rows.iloc[-1]
            )

            old_value = pd.to_numeric(
                historical_row[value_column],
                errors="coerce",
            )

            if pd.isna(old_value):
                return float("nan")

            historical_year = (
                historical_row["year"]
            )

            actual_years = (
                actual_latest_year
                - historical_year
            )

            if actual_years <= 0:
                return float("nan")

            return (
                (
                    latest_value
                    / old_value
                )
                ** (1 / actual_years)
                - 1
            ) * 100

        # ========================================================
        # REVENUE CAGR - 3 YEAR
        # ========================================================

        df["revenue_cagr_3yr"] = float(
            "nan"
        )

        for index, row in df.iterrows():

            company_id = row[
                "company_id"
            ]

            latest_year = pd.to_numeric(
                row["year"],
                errors="coerce",
            )

            if pd.isna(latest_year):
                continue

            df.loc[
                index,
                "revenue_cagr_3yr",
            ] = calculate_cagr(
                company_id,
                latest_year,
                "sales",
                3,
            )

        # ========================================================
        # 5-YEAR CAGR COLUMNS
        # ========================================================

        df["revenue_cagr_5yr"] = float(
            "nan"
        )

        df["pat_cagr_5yr"] = float(
            "nan"
        )

        df["eps_cagr_5yr"] = float(
            "nan"
        )

        for index, row in df.iterrows():

            company_id = row[
                "company_id"
            ]

            latest_year = pd.to_numeric(
                row["year"],
                errors="coerce",
            )

            if pd.isna(latest_year):
                continue

            df.loc[
                index,
                "revenue_cagr_5yr",
            ] = calculate_cagr(
                company_id,
                latest_year,
                "sales",
                5,
            )

            df.loc[
                index,
                "pat_cagr_5yr",
            ] = calculate_cagr(
                company_id,
                latest_year,
                "net_profit",
                5,
            )

            df.loc[
                index,
                "eps_cagr_5yr",
            ] = calculate_cagr(
                company_id,
                latest_year,
                "eps",
                5,
            )

        # ========================================================
        # EFFECTIVE INTEREST COVERAGE
        # ========================================================

        if "interest_coverage" in df.columns:

            df["effective_interest_coverage"] = (
                self._numeric(
                    df["interest_coverage"]
                )
            )

        else:

            df["effective_interest_coverage"] = (
                float("nan")
            )

        if "icr_label" in df.columns:

            debt_free = (
                df["icr_label"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
                .eq("debt free")
            )

            df.loc[
                debt_free,
                "effective_interest_coverage",
            ] = float("inf")

        # ========================================================
        # ROCE
        # ========================================================

        if "roce_pct" in df.columns:

            df["roce_pct"] = self._numeric(
                df["roce_pct"]
            )

        elif "roce_percentage" in df.columns:

            df["roce_pct"] = self._numeric(
                df["roce_percentage"]
            )

        else:

            # Calculate ROCE from available fields where possible.
            #
            # EBIT = operating profit
            # Capital employed = total assets - current liabilities
            #
            # If those source fields are unavailable, use ROE as a
            # conservative fallback so the screener remains usable.

            df["roce_pct"] = float("nan")

            if (
                "operating_profit_margin_pct"
                in df.columns
                and "sales_cr"
                in df.columns
                and "total_assets"
                in df.columns
            ):

                operating_margin = (
                    self._numeric(
                        df[
                            "operating_profit_margin_pct"
                        ]
                    )
                )

                sales = self._numeric(
                    df["sales_cr"]
                )

                assets = self._numeric(
                    df["total_assets"]
                )

                ebit = (
                    sales
                    * operating_margin
                    / 100
                )

                roce = (
                    ebit
                    / assets
                    * 100
                )

                roce = roce.replace(
                    [
                        float("inf"),
                        float("-inf"),
                    ],
                    float("nan"),
                )

                df["roce_pct"] = roce

            if "return_on_equity_pct" in df.columns:

                fallback = self._numeric(
                    df[
                        "return_on_equity_pct"
                    ]
                )

                df["roce_pct"] = (
                    df["roce_pct"]
                    .fillna(fallback)
                )

        # ========================================================
        # COMPOSITE QUALITY SCORE
        # ========================================================

        roe = self._numeric(
            df.get(
                "return_on_equity_pct",
                pd.Series(
                    index=df.index,
                    dtype=float,
                ),
            )
        )

        roce = self._numeric(
            df["roce_pct"]
        )

        debt = self._numeric(
            df["debt_to_equity"]
        )

        icr = self._numeric(
            df[
                "effective_interest_coverage"
            ]
        )

        # Component 1: ROE score
        roe_score = (
            roe.clip(
                lower=0,
                upper=30,
            )
            / 30
            * 100
        )

        # Component 2: ROCE score
        roce_score = (
            roce.clip(
                lower=0,
                upper=30,
            )
            / 30
            * 100
        )

        # Component 3: leverage score
        debt_score = (
            100
            - (
                debt.clip(
                    lower=0,
                    upper=5,
                )
                / 5
                * 100
            )
        )

        # Component 4: interest coverage score
        icr_score = (
            icr.clip(
                lower=0,
                upper=10,
            )
            / 10
            * 100
        )

        df["composite_quality_score"] = (
            roe_score * 0.30
            + roce_score * 0.30
            + debt_score * 0.20
            + icr_score * 0.20
        )

        # ========================================================
        # FINAL CLEANUP
        # ========================================================

        df = (
            df
            .sort_values(
                "company_id"
            )
            .drop_duplicates(
                subset=["company_id"],
                keep="first",
            )
            .reset_index(drop=True)
        )

        return df

    # ============================================================
    # FILTER CONFIGURATION
    # ============================================================

    FILTER_COLUMNS = {

        "pe_max":
            "pe_ratio",

        "pe_min":
            "pe_ratio",

        "pb_max":
            "pb_ratio",

        "pb_min":
            "pb_ratio",

        "dividend_yield_min":
            "dividend_yield_pct",

        "roe_min":
            "return_on_equity_pct",

        "roce_min":
            "roce_pct",

        "de_max":
            "debt_to_equity",

        "de_min":
            "debt_to_equity",

        "interest_coverage_min":
            "effective_interest_coverage",

        "revenue_cagr_3yr_min":
            "revenue_cagr_3yr",

        "revenue_cagr_5yr_min":
            "revenue_cagr_5yr",

        "pat_cagr_5yr_min":
            "pat_cagr_5yr",

        "eps_cagr_5yr_min":
            "eps_cagr_5yr",

        "market_cap_min":
            "market_cap_crore",

        "market_cap_max":
            "market_cap_crore",

        "fcf_min":
            "free_cash_flow_cr",

        "asset_turnover_min":
            "asset_turnover",

        "debt_declining":
            "debt_to_equity_declining",
    }

    # ============================================================
    # APPLY SINGLE FILTER
    # ============================================================

    def _apply_single_filter(
        self,
        df: pd.DataFrame,
        filter_name: str,
        threshold,
    ) -> pd.DataFrame:
        """Apply one configured filter."""

        # ========================================================
        # BOOLEAN FILTER
        # ========================================================

        if filter_name == "debt_declining":

            if (
                "debt_to_equity_declining"
                not in df.columns
            ):
                raise KeyError(
                    "Required column "
                    "'debt_to_equity_declining' "
                    "was not found."
                )

            return df[
                df[
                    "debt_to_equity_declining"
                ]
                == bool(threshold)
            ].copy()

        # ========================================================
        # FINANCIALS D/E EXCEPTION
        # ========================================================

        if filter_name == "de_max":

            required_column = (
                "debt_to_equity"
            )

            if required_column not in df.columns:

                raise KeyError(
                    f"Required column "
                    f"'{required_column}' "
                    f"for filter "
                    f"'{filter_name}' "
                    f"was not found."
                )

            de = self._numeric(
                df[required_column]
            )

            threshold = float(
                threshold
            )

            financials = (
                df[
                    "broad_sector"
                ]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
                .eq("financials")
            )

            result = df[
                (de <= threshold)
                | financials
            ].copy()

            return result

        # ========================================================
        # NORMAL FILTERS
        # ========================================================

        if filter_name not in self.FILTER_COLUMNS:

            raise KeyError(
                f"Unknown filter: "
                f"{filter_name}"
            )

        required_column = (
            self.FILTER_COLUMNS[
                filter_name
            ]
        )

        if required_column not in df.columns:

            raise KeyError(
                f"Required column "
                f"'{required_column}' "
                f"for filter "
                f"'{filter_name}' "
                f"was not found."
            )

        series = df[
            required_column
        ]

        # ========================================================
        # MIN FILTER
        # ========================================================

        if filter_name.endswith(
            "_min"
        ):

            numeric = self._numeric(
                series
            )

            return df[
                numeric >= float(threshold)
            ].copy()

        # ========================================================
        # MAX FILTER
        # ========================================================

        if filter_name.endswith(
            "_max"
        ):

            numeric = self._numeric(
                series
            )

            return df[
                numeric <= float(threshold)
            ].copy()

        # ========================================================
        # EXACT / BOOLEAN
        # ========================================================

        return df[
            series == threshold
        ].copy()

    # ============================================================
    # APPLY MULTIPLE FILTERS
    # ============================================================

    def apply_filters(
        self,
        df: pd.DataFrame,
        filters: dict,
    ) -> pd.DataFrame:
        """
        Apply all supplied filters using AND logic.
        """

        result = df.copy()

        for filter_name, threshold in filters.items():

            result = self._apply_single_filter(
                result,
                filter_name,
                threshold,
            )

            if result.empty:
                break

        return result

    # ============================================================
    # SCREEN
    # ============================================================

    def screen(
        self,
        thresholds: dict,
        sort_by: str | None = None,
        ascending: bool = False,
    ) -> pd.DataFrame:
        """
        Execute a screening configuration.
        """

        df = self.load_data()

        df = self.apply_filters(
            df,
            thresholds,
        )

        if sort_by is not None:

            if sort_by not in df.columns:

                raise KeyError(
                    f"Sort column "
                    f"'{sort_by}' "
                    f"was not found."
                )

            df = df.sort_values(
                by=sort_by,
                ascending=ascending,
                na_position="last",
            )

        return df.reset_index(
            drop=True
        )

    # ============================================================
    # PRESETS
    # ============================================================

    def preset(
        self,
        preset_name: str,
    ) -> pd.DataFrame:
        """
        Run one predefined screener.
        """

        presets = {

            # ----------------------------------------------------
            # VALUE PICK
            # ----------------------------------------------------

            "value_pick": {

                "filters": {

                    "pe_max": 20,

                    "pb_max": 4,

                    "dividend_yield_min": 1,

                    "de_max": 2,

                },

                "sort_by":
                    "dividend_yield_pct",

                "ascending":
                    False,
            },

            # ----------------------------------------------------
            # QUALITY COMPOUNDER
            # ----------------------------------------------------

            "quality_compounder": {

                "filters": {

                    "roe_min": 15,

                    "roce_min": 15,

                    "de_max": 2,

                    "interest_coverage_min": 3,

                },

                "sort_by":
                    "composite_quality_score",

                "ascending":
                    False,
            },

            # ----------------------------------------------------
            # GROWTH ACCELERATOR
            # ----------------------------------------------------

            "growth_accelerator": {

                "filters": {

                    "revenue_cagr_5yr_min": 10,

                    "pat_cagr_5yr_min": 10,

                    "eps_cagr_5yr_min": 10,

                },

                "sort_by":
                    "revenue_cagr_5yr",

                "ascending":
                    False,
            },

            # ----------------------------------------------------
            # DEBT REDUCER
            # ----------------------------------------------------

            "debt_reducer": {

                "filters": {

                    "de_max": 2,

                    "debt_declining": True,

                },

                "sort_by":
                    "debt_to_equity",

                "ascending":
                    True,
            },

            # ----------------------------------------------------
            # CASH FLOW QUALITY
            # ----------------------------------------------------

            "cash_flow_quality": {

                "filters": {

                    "fcf_min": 0,

                    "asset_turnover_min": 0.5,

                },

                "sort_by":
                    "free_cash_flow_cr",

                "ascending":
                    False,
            },

            # ----------------------------------------------------
            # DIVIDEND INCOME
            # ----------------------------------------------------

            "dividend_income": {

                "filters": {

                    "dividend_yield_min": 2,

                },

                "sort_by":
                    "dividend_yield_pct",

                "ascending":
                    False,
            },
        }

        if preset_name not in presets:

            raise ValueError(
                f"Unknown preset "
                f"'{preset_name}'. "
                f"Available presets: "
                f"{sorted(presets)}"
            )

        configuration = presets[
            preset_name
        ]

        return self.screen(
            configuration["filters"],
            sort_by=configuration.get(
                "sort_by"
            ),
            ascending=configuration.get(
                "ascending",
                False,
            ),
        )

    # ============================================================
    # RUN ALL PRESETS
    # ============================================================

    def run_all_presets(
        self,
    ) -> dict[str, pd.DataFrame]:
        """
        Run every predefined screener.
        """

        preset_names = [

            "value_pick",

            "quality_compounder",

            "growth_accelerator",

            "debt_reducer",

            "cash_flow_quality",

            "dividend_income",

        ]

        results = {}

        for preset_name in preset_names:

            results[
                preset_name
            ] = self.preset(
                preset_name
            )

        return results


# ================================================================
# COMMAND-LINE TEST
# ================================================================

if __name__ == "__main__":

    engine = ScreenerEngine()

    print("=" * 70)
    print("NIFTY 100 FINANCIAL SCREENER")
    print("=" * 70)

    data = engine.load_data()

    print(
        f"\nRows loaded: "
        f"{len(data)}"
    )

    print(
        f"Unique companies: "
        f"{data['company_id'].nunique()}"
    )

    print(
        f"M&M records: "
        f"{len(data[data.company_id == 'M&M'])}"
    )

    print(
        f"ADANIPORTS records: "
        f"{len(data[data.company_id == 'ADANIPORTS'])}"
    )

    print(
        "\nCalculated columns:"
    )

    calculated_columns = [

        "debt_to_equity_declining",

        "revenue_cagr_3yr",

        "revenue_cagr_5yr",

        "pat_cagr_5yr",

        "eps_cagr_5yr",

        "effective_interest_coverage",

        "roce_pct",

        "composite_quality_score",

    ]

    for column in calculated_columns:

        print(
            f"  {column:<35}"
            f"{column in data.columns}"
        )

    print(
        "\nPreset results:"
    )

    results = engine.run_all_presets()

    for name, result in results.items():

        print(
            f"  {name:<25}"
            f"{len(result):>5} companies"
        )

    print(
        "\n" + "=" * 70
    )

    print(
        "SCREENER TEST COMPLETE"
    )

    print(
        "=" * 70
    )
