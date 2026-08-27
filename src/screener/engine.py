"""
Sprint 3 - Day 16
Financial Screener Engine

Implemented:
- YAML configuration
- 18 filter definitions
- 6 preset screeners
- Financials sector D/E exception
- Debt Free -> ICR = infinity
- Revenue CAGR 3yr calculation from profitandloss.sales
- YoY D/E declining calculation
- Custom threshold screening
- Composite score column preservation
"""

from pathlib import Path
import operator
import sqlite3

import pandas as pd
import yaml


# =====================================================================
# PATHS
# =====================================================================

ROOT_DIR = Path(__file__).resolve().parents[2]

DB_PATH = ROOT_DIR / "db" / "nifty100.db"
CONFIG_PATH = ROOT_DIR / "config" / "screener_config.yaml"


# =====================================================================
# OPERATORS
# =====================================================================

OPERATORS = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
}


# =====================================================================
# SCREENER ENGINE
# =====================================================================

class ScreenerEngine:
    """Financial screener engine for Sprint 3."""

    def __init__(
        self,
        db_path=DB_PATH,
        config_path=CONFIG_PATH,
    ):
        self.db_path = Path(db_path)
        self.config_path = Path(config_path)

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Database not found: {self.db_path}"
            )

        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration not found: {self.config_path}"
            )

        self.config = self._load_config()

    # =================================================================
    # CONFIGURATION
    # =================================================================

    def _load_config(self):
        """Load screener configuration from YAML."""

        with self.config_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            config = yaml.safe_load(file) or {}

        if "filters" not in config:
            raise ValueError(
                "Configuration must contain 'filters'."
            )

        if "presets" not in config:
            raise ValueError(
                "Configuration must contain 'presets'."
            )

        return config

    # =================================================================
    # HELPERS
    # =================================================================

    @staticmethod
    def _numeric(series):
        """Safely convert a pandas Series to numeric."""

        return pd.to_numeric(
            series,
            errors="coerce",
        )

    @staticmethod
    def _find_column(df, candidates):
        """Return the first available column."""

        for column in candidates:
            if column in df.columns:
                return column

        return None

    # =================================================================
    # LOAD DATA
    # =================================================================

    def load_data(self):
        """
        Load the latest available data for each company.

        Sources:
        - financial_ratios
        - market_cap
        - profitandloss
        - sectors

        Additional calculated fields:
        - previous_debt_to_equity
        - debt_to_equity_declining
        - revenue_cagr_3yr
        - effective_interest_coverage
        """

        query = """
        WITH ranked_ratios AS (
            SELECT
                fr.*,

                ROW_NUMBER() OVER (
                    PARTITION BY fr.company_id
                    ORDER BY CAST(fr.year AS REAL) DESC
                ) AS rn,

                LAG(fr.debt_to_equity) OVER (
                    PARTITION BY fr.company_id
                    ORDER BY CAST(fr.year AS REAL)
                ) AS previous_debt_to_equity

            FROM financial_ratios fr
        ),

        ranked_market AS (
            SELECT
                mc.*,

                ROW_NUMBER() OVER (
                    PARTITION BY mc.company_id
                    ORDER BY CAST(mc.year AS REAL) DESC
                ) AS rn

            FROM market_cap mc
        ),

        ranked_pnl AS (
            SELECT
                pl.*,

                ROW_NUMBER() OVER (
                    PARTITION BY pl.company_id
                    ORDER BY CAST(pl.year AS REAL) DESC
                ) AS rn

            FROM profitandloss pl
        ),

        latest_sales AS (
            SELECT
                company_id,
                CAST(year AS REAL) AS latest_sales_year,
                CAST(sales AS REAL) AS latest_sales

            FROM (
                SELECT
                    company_id,
                    year,
                    sales,

                    ROW_NUMBER() OVER (
                        PARTITION BY company_id
                        ORDER BY CAST(year AS REAL) DESC
                    ) AS rn

                FROM profitandloss
            )

            WHERE rn = 1
        ),

        historical_sales AS (
            SELECT
                company_id,
                CAST(year AS REAL) AS sales_year,
                CAST(sales AS REAL) AS sales

            FROM profitandloss
        ),

        sales_3yr AS (
            SELECT
                ls.company_id,
                ls.latest_sales,
                ls.latest_sales_year,
                old.sales AS sales_3yr_ago

            FROM latest_sales ls

            LEFT JOIN historical_sales old
                ON old.company_id = ls.company_id

                AND old.sales_year = (
                    SELECT MAX(h.sales_year)

                    FROM historical_sales h

                    WHERE h.company_id = ls.company_id

                    AND h.sales_year <=
                        ls.latest_sales_year - 3
                )
        )

        SELECT
            fr.*,

            mc.market_cap_crore,
            mc.pe_ratio,
            mc.pb_ratio,
            mc.dividend_yield_pct,

            pl.sales AS sales_cr,
            pl.net_profit AS pnl_net_profit_cr,
            pl.eps AS pnl_eps,
            pl.dividend_payout AS dividend_payout_ratio,

            ss.latest_sales,
            ss.sales_3yr_ago,

            s.broad_sector,
            s.sub_sector

        FROM ranked_ratios fr

        LEFT JOIN ranked_market mc
            ON fr.company_id = mc.company_id
            AND mc.rn = 1

        LEFT JOIN ranked_pnl pl
            ON fr.company_id = pl.company_id
            AND pl.rn = 1

        LEFT JOIN sales_3yr ss
            ON fr.company_id = ss.company_id

        LEFT JOIN sectors s
            ON fr.company_id = s.company_id

        WHERE fr.rn = 1
        """

        with sqlite3.connect(self.db_path) as connection:
            df = pd.read_sql_query(
                query,
                connection,
            )

        if df.empty:
            raise ValueError(
                "No financial ratio records found."
            )

        # =============================================================
        # D/E DECLINING YOY
        # =============================================================

        current_de = self._numeric(
            df["debt_to_equity"]
        )

        previous_de = self._numeric(
            df["previous_debt_to_equity"]
        )

        df["debt_to_equity_declining"] = (
            current_de < previous_de
        )

        # =============================================================
        # REVENUE CAGR 3 YEAR
        # =============================================================

        latest_sales = self._numeric(
            df["latest_sales"]
        )

        sales_3yr_ago = self._numeric(
            df["sales_3yr_ago"]
        )

        df["revenue_cagr_3yr"] = float("nan")

        valid_sales = (
            (latest_sales > 0)
            &
            (sales_3yr_ago > 0)
        )

        df.loc[
            valid_sales,
            "revenue_cagr_3yr",
        ] = (
            (
                latest_sales[valid_sales]
                /
                sales_3yr_ago[valid_sales]
            )
            ** (1 / 3)
            - 1
        ) * 100

        # =============================================================
        # EFFECTIVE INTEREST COVERAGE
        # =============================================================

        df["effective_interest_coverage"] = (
            self._numeric(
                df["interest_coverage"]
            )
        )

        # Debt Free companies get infinite ICR.
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

        return df

    # =================================================================
    # COLUMN RESOLUTION
    # =================================================================

    def _resolve_column(
        self,
        df,
        filter_name,
        configured_column,
    ):
        """
        Resolve YAML column names against the actual database schema.
        """

        # ICR uses the special effective ICR field.
        if filter_name == "icr_min":
            return "effective_interest_coverage"

        aliases = {

            "revenue_cagr_5yr": [
                "revenue_cagr_5yr",
            ],

            "pat_cagr_5yr": [
                "pat_cagr_5yr",
            ],

            "eps_cagr_5yr": [
                "eps_cagr_5yr",
            ],

            "revenue_cagr_3yr": [
                "revenue_cagr_3yr",
            ],

            "dividend_payout_ratio_pct": [
                "dividend_payout_ratio_pct",
                "dividend_payout_ratio",
            ],

            "sales_cr": [
                "sales_cr",
            ],

            "net_profit_cr": [
                "net_profit_cr",
                "pnl_net_profit_cr",
            ],
        }

        candidates = aliases.get(
            configured_column,
            [configured_column],
        )

        return self._find_column(
            df,
            candidates,
        )

    # =================================================================
    # SINGLE FILTER
    # =================================================================

    def _apply_single_filter(
        self,
        df,
        filter_name,
        threshold,
    ):
        """Apply one configured filter."""

        definition = self.config["filters"].get(
            filter_name
        )

        if definition is None:
            raise KeyError(
                f"Unknown filter: {filter_name}"
            )

        configured_column = definition["column"]
        operator_symbol = definition["operator"]

        if operator_symbol not in OPERATORS:
            raise ValueError(
                f"Unsupported operator: "
                f"{operator_symbol}"
            )

        # =============================================================
        # D/E DECLINING SPECIAL FILTER
        # =============================================================

        if filter_name == "de_declining":

            if "debt_to_equity_declining" not in df.columns:
                raise KeyError(
                    "debt_to_equity_declining column missing."
                )

            return df.loc[
                df["debt_to_equity_declining"]
                .fillna(False)
                .astype(bool)
            ].copy()

        # =============================================================
        # RESOLVE COLUMN
        # =============================================================

        column = self._resolve_column(
            df,
            filter_name,
            configured_column,
        )

        if column is None:
            raise KeyError(
                f"Required column "
                f"'{configured_column}' for filter "
                f"'{filter_name}' was not found."
            )

        # =============================================================
        # NUMERIC COMPARISON
        # =============================================================

        values = self._numeric(
            df[column]
        )

        condition = OPERATORS[
            operator_symbol
        ](
            values,
            threshold,
        )

        condition = condition.fillna(False)

        # =============================================================
        # FINANCIALS D/E EXCEPTION
        # =============================================================

        if filter_name == "de_max":

            if "broad_sector" not in df.columns:
                raise KeyError(
                    "broad_sector column required "
                    "for D/E filter."
                )

            financials = (
                df["broad_sector"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
                .eq("financials")
            )

            # Financial-sector companies automatically
            # pass the D/E threshold.
            condition = (
                condition
                |
                financials
            )

        return df.loc[
            condition
        ].copy()

    # =================================================================
    # APPLY MULTIPLE FILTERS
    # =================================================================

    def apply_filters(
        self,
        df,
        thresholds,
    ):
        """
        Apply all supplied filters using AND logic.
        """

        if thresholds is None:
            return df.copy()

        if not isinstance(
            thresholds,
            dict,
        ):
            raise TypeError(
                "thresholds must be a dictionary."
            )

        result = df.copy()

        for filter_name, threshold in thresholds.items():

            if threshold is None:
                continue

            result = self._apply_single_filter(
                result,
                filter_name,
                threshold,
            )

            if result.empty:
                break

        return result

    # =================================================================
    # COMPOSITE SCORE
    # =================================================================

    def add_composite_score(self, df):
        """
        Preserve the Sprint 2 composite score.

        Full Sprint 3 Day 17 scoring will implement:
        - P10/P90 winsorisation
        - 0-100 normalisation
        - sector-relative scoring
        - 35/30/20/15 weighting
        """

        result = df.copy()

        if "composite_quality_score" not in result.columns:
            result[
                "composite_quality_score"
            ] = 0.0

        result[
            "composite_quality_score"
        ] = self._numeric(
            result[
                "composite_quality_score"
            ]
        ).fillna(0.0)

        return result

    # =================================================================
    # CUSTOM SCREEN
    # =================================================================

    def screen(
        self,
        thresholds=None,
    ):
        """Run a custom screener."""

        df = self.load_data()

        if thresholds:
            df = self.apply_filters(
                df,
                thresholds,
            )

        df = self.add_composite_score(
            df
        )

        return df.sort_values(
            by="composite_quality_score",
            ascending=False,
            na_position="last",
        ).reset_index(
            drop=True
        )

    # =================================================================
    # PRESET
    # =================================================================

    def preset(
        self,
        preset_name,
    ):
        """Run one configured preset."""

        presets = self.config[
            "presets"
        ]

        if preset_name not in presets:
            raise KeyError(
                f"Unknown preset '{preset_name}'. "
                f"Available presets: "
                f"{list(presets.keys())}"
            )

        return self.screen(
            presets[preset_name]
        )

    # =================================================================
    # ALL PRESETS
    # =================================================================

    def run_all_presets(self):
        """Run all configured presets."""

        results = {}

        for preset_name in self.config[
            "presets"
        ]:
            results[
                preset_name
            ] = self.preset(
                preset_name
            )

        return results


# =====================================================================
# MAIN
# =====================================================================

def main():

    print("=" * 70)
    print(
        "SPRINT 3 - DAY 16 SCREENER ENGINE"
    )
    print("=" * 70)

    engine = ScreenerEngine()

    data = engine.load_data()

    print(
        f"Database                 : "
        f"{engine.db_path}"
    )

    print(
        f"Latest company records   : "
        f"{len(data)}"
    )

    print(
        f"Configured filters       : "
        f"{len(engine.config['filters'])}"
    )

    print(
        f"Configured presets       : "
        f"{len(engine.config['presets'])}"
    )

    # ================================================================
    # PRESET RESULTS
    # ================================================================

    print("\n" + "=" * 70)
    print("PRESET RESULTS")
    print("=" * 70)

    results = engine.run_all_presets()

    all_valid = True

    for name, result in results.items():

        count = len(result)

        if 5 <= count <= 50:
            status = "PASS"
        else:
            status = "CHECK"
            all_valid = False

        print(
            f"{name:30} "
            f"{count:3} companies   "
            f"[{status}]"
        )

    # ================================================================
    # QUALITY COMPOUNDER TOP 5
    # ================================================================

    print("\n" + "=" * 70)
    print("QUALITY COMPOUNDER - TOP 5")
    print("=" * 70)

    quality = results[
        "quality_compounder"
    ]

    quality_columns = [
        "company_id",
        "year",
        "return_on_equity_pct",
        "debt_to_equity",
        "free_cash_flow_cr",
        "revenue_cagr_5yr",
        "composite_quality_score",
    ]

    available_columns = [
        column
        for column in quality_columns
        if column in quality.columns
    ]

    if not quality.empty:

        print(
            quality[
                available_columns
            ]
            .head(5)
            .to_string(
                index=False
            )
        )

    else:
        print(
            "No companies returned."
        )

    # ================================================================
    # TURNAROUND CHECK
    # ================================================================

    print("\n" + "=" * 70)
    print("TURNAROUND WATCH - SAMPLE")
    print("=" * 70)

    turnaround = results[
        "turnaround_watch"
    ]

    turnaround_columns = [
        "company_id",
        "revenue_cagr_3yr",
        "free_cash_flow_cr",
        "debt_to_equity",
        "previous_debt_to_equity",
        "debt_to_equity_declining",
    ]

    available_turnaround = [
        column
        for column in turnaround_columns
        if column in turnaround.columns
    ]

    if not turnaround.empty:

        print(
            turnaround[
                available_turnaround
            ]
            .head(10)
            .to_string(
                index=False
            )
        )

    else:
        print(
            "No companies returned."
        )

    # ================================================================
    # FINAL STATUS
    # ================================================================

    print("\n" + "=" * 70)

    if all_valid:
        print(
            "DAY 16 PRESET VALIDATION: PASS"
        )
    else:
        print(
            "DAY 16 PRESET VALIDATION: CHECK"
        )

    print("=" * 70)


# =====================================================================
# ENTRY POINT
# =====================================================================

if __name__ == "__main__":
    main()