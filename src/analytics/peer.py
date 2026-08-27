"""
Sprint 3 - Day 18
Peer Percentile Ranking Engine

Requirements:
- 11 peer groups
- 10 metrics
- PERCENT_RANK within each peer group
- D/E inverted: lower D/E = higher percentile
- Populate SQLite peer_percentiles table
- Companies without peer groups are reported, not treated as errors
"""

from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd


# =====================================================================
# PATHS
# =====================================================================

ROOT_DIR = Path(__file__).resolve().parents[2]

DB_PATH = ROOT_DIR / "db" / "nifty100.db"


# =====================================================================
# PEER ENGINE
# =====================================================================

class PeerPercentileEngine:

    def __init__(self, db_path=DB_PATH):

        self.db_path = Path(db_path)

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Database not found: {self.db_path}"
            )

    # =================================================================
    # LOAD PEER GROUPS
    # =================================================================

    def load_peer_groups(self):

        query = """
        SELECT
            peer_group_name,
            company_id,
            is_benchmark
        FROM peer_groups
        ORDER BY
            peer_group_name,
            company_id
        """

        with sqlite3.connect(self.db_path) as connection:

            df = pd.read_sql_query(
                query,
                connection,
            )

        return df

    # =================================================================
    # LOAD FINANCIAL DATA
    # =================================================================

    def load_financial_data(self):

        query = """
        WITH ranked_ratios AS (

            SELECT
                fr.*,

                ROW_NUMBER() OVER (
                    PARTITION BY fr.company_id
                    ORDER BY CAST(fr.year AS REAL) DESC
                ) AS rn

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
        )

        SELECT

            fr.company_id,
            fr.year,

            fr.return_on_equity_pct,
            fr.roce_pct,
            fr.net_profit_margin_pct,
            fr.debt_to_equity,
            fr.free_cash_flow_cr,
            fr.pat_cagr_5yr,
            fr.revenue_cagr_5yr,
            fr.eps_cagr_5yr,
            fr.interest_coverage,
            fr.asset_turnover,

            fr.icr_label,

            mc.market_cap_crore

        FROM ranked_ratios fr

        LEFT JOIN ranked_market mc
            ON fr.company_id = mc.company_id
            AND mc.rn = 1

        WHERE fr.rn = 1
        """

        with sqlite3.connect(self.db_path) as connection:

            df = pd.read_sql_query(
                query,
                connection,
            )

        return df

    # =================================================================
    # PREPARE DATA
    # =================================================================

    def prepare_data(self):

        peer_groups = self.load_peer_groups()

        financial = self.load_financial_data()

        merged = peer_groups.merge(
            financial,
            on="company_id",
            how="left",
        )

        # Debt-free companies get infinite ICR.
        if "icr_label" in merged.columns:

            debt_free = (
                merged["icr_label"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
                .eq("debt free")
            )

            merged.loc[
                debt_free,
                "interest_coverage",
            ] = float("inf")

        return merged

    # =================================================================
    # METRIC DEFINITIONS
    # =================================================================

    @staticmethod
    def metric_definitions():

        return {
            "ROE": {
                "column": "return_on_equity_pct",
                "higher_is_better": True,
            },

            "ROCE": {
                "column": "roce_pct",
                "higher_is_better": True,
            },

            "Net Profit Margin": {
                "column": "net_profit_margin_pct",
                "higher_is_better": True,
            },

            "D/E": {
                "column": "debt_to_equity",
                "higher_is_better": False,
            },

            "FCF": {
                "column": "free_cash_flow_cr",
                "higher_is_better": True,
            },

            "PAT CAGR 5yr": {
                "column": "pat_cagr_5yr",
                "higher_is_better": True,
            },

            "Revenue CAGR 5yr": {
                "column": "revenue_cagr_5yr",
                "higher_is_better": True,
            },

            "EPS CAGR 5yr": {
                "column": "eps_cagr_5yr",
                "higher_is_better": True,
            },

            "Interest Coverage": {
                "column": "interest_coverage",
                "higher_is_better": True,
            },

            "Asset Turnover": {
                "column": "asset_turnover",
                "higher_is_better": True,
            },
        }

    # =================================================================
    # PERCENT RANK
    # =================================================================

    @staticmethod
    def percent_rank(series):

        values = pd.to_numeric(
            series,
            errors="coerce",
        )

        result = pd.Series(
            np.nan,
            index=series.index,
            dtype=float,
        )

        valid = values.notna()

        if valid.sum() == 0:
            return result

        valid_values = values.loc[valid]

        # One company / all equal values.
        if len(valid_values) == 1:

            result.loc[valid] = 1.0

            return result

        minimum = valid_values.min()
        maximum = valid_values.max()

        # SQL PERCENT_RANK:
        #
        # (rank - 1) / (rows - 1)
        #
        # pandas rank(method='min') reproduces SQL RANK()
        # behaviour for ties.

        ranks = (
            valid_values.rank(
                method="min"
            )
            - 1
        ) / (
            len(valid_values) - 1
        )

        result.loc[valid] = ranks

        return result

    # =================================================================
    # CALCULATE
    # =================================================================

    def calculate(self):

        data = self.prepare_data()

        definitions = (
            self.metric_definitions()
        )

        records = []

        peer_groups = data[
            "peer_group_name"
        ].dropna().unique()

        for peer_group in sorted(
            peer_groups
        ):

            group = data[
                data["peer_group_name"]
                == peer_group
            ].copy()

            for metric_name, definition in definitions.items():

                column = definition[
                    "column"
                ]

                higher_is_better = definition[
                    "higher_is_better"
                ]

                if column not in group.columns:
                    continue

                values = pd.to_numeric(
                    group[column],
                    errors="coerce",
                )

                percentile = self.percent_rank(
                    values
                )

                # =====================================================
                # D/E INVERSION
                # =====================================================

                if not higher_is_better:

                    percentile = (
                        1.0 - percentile
                    )

                for index in group.index:

                    value = values.loc[
                        index
                    ]

                    rank = percentile.loc[
                        index
                    ]

                    if pd.isna(value):
                        continue

                    records.append(
                        {
                            "company_id": group.loc[
                                index,
                                "company_id",
                            ],

                            "peer_group_name": peer_group,

                            "metric": metric_name,

                            "value": value,

                            "percentile_rank": rank,

                            "year": group.loc[
                                index,
                                "year",
                            ],
                        }
                    )

        result = pd.DataFrame(
            records,
            columns=[
                "company_id",
                "peer_group_name",
                "metric",
                "value",
                "percentile_rank",
                "year",
            ],
        )

        return result

    # =================================================================
    # CREATE TABLE
    # =================================================================

    def create_table(self):

        query = """
        CREATE TABLE IF NOT EXISTS peer_percentiles (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            company_id TEXT NOT NULL,

            peer_group_name TEXT NOT NULL,

            metric TEXT NOT NULL,

            value REAL,

            percentile_rank REAL,

            year TEXT
        )
        """

        with sqlite3.connect(
            self.db_path
        ) as connection:

            connection.execute(
                query
            )

            connection.commit()

    # =================================================================
    # SAVE RESULTS
    # =================================================================

    def save(self, result):

        self.create_table()

        with sqlite3.connect(
            self.db_path
        ) as connection:

            # Remove previous Sprint 3 results
            # so rerunning the script does not
            # create duplicates.

            connection.execute(
                "DELETE FROM peer_percentiles"
            )

            result.to_sql(
                "peer_percentiles",
                connection,
                if_exists="append",
                index=False,
            )

            connection.commit()

    # =================================================================
    # FIND COMPANIES WITHOUT PEER GROUP
    # =================================================================

    def companies_without_peer_group(self):

        peer_query = """
        SELECT DISTINCT company_id
        FROM peer_groups
        """

        company_query = """
        SELECT DISTINCT company_id
        FROM financial_ratios
        """

        with sqlite3.connect(
            self.db_path
        ) as connection:

            peer_ids = {
                row[0]
                for row in connection.execute(
                    peer_query
                ).fetchall()
            }

            company_ids = {
                row[0]
                for row in connection.execute(
                    company_query
                ).fetchall()
            }

        return sorted(
            company_ids - peer_ids
        )

    # =================================================================
    # VALIDATION
    # =================================================================

    def validate(self, result):

        print("\n" + "=" * 70)
        print("DAY 18 PEER PERCENTILE VALIDATION")
        print("=" * 70)

        print(
            f"Peer groups              : "
            f"{result['peer_group_name'].nunique()}"
        )

        print(
            f"Metrics                  : "
            f"{result['metric'].nunique()}"
        )

        print(
            f"Percentile records      : "
            f"{len(result)}"
        )

        print(
            f"Companies ranked        : "
            f"{result['company_id'].nunique()}"
        )

        print("\nPeer groups:")
        for group in sorted(
            result[
                "peer_group_name"
            ].unique()
        ):

            count = result[
                result[
                    "peer_group_name"
                ]
                == group
            ]["company_id"].nunique()

            print(
                f"  {group:30} "
                f"{count:3} companies"
            )

        # =============================================================
        # PERCENTILE RANGE
        # =============================================================

        ranks = pd.to_numeric(
            result["percentile_rank"],
            errors="coerce",
        )

        invalid = (
            (ranks < 0)
            |
            (ranks > 1)
        ).sum()

        print(
            "\nInvalid percentile values : "
            f"{invalid}"
        )

        # =============================================================
        # D/E CHECK
        # =============================================================

        de = result[
            result["metric"]
            == "D/E"
        ].copy()

        print(
            "\nD/E records              : "
            f"{len(de)}"
        )

        # =============================================================
        # IT SERVICES ROE CHECK
        # =============================================================

        it = result[
            result["peer_group_name"]
            == "IT Services"
        ]

        it_roe = it[
            it["metric"]
            == "ROE"
        ].copy()

        if not it_roe.empty:

            top = it_roe.sort_values(
                "value",
                ascending=False,
            ).iloc[0]

            top_rank = it_roe[
                it_roe[
                    "percentile_rank"
                ]
                ==
                it_roe[
                    "percentile_rank"
                ].max()
            ].iloc[0]

            print(
                "\nIT Services highest ROE:"
            )

            print(
                f"  Company   : "
                f"{top['company_id']}"
            )

            print(
                f"  ROE       : "
                f"{top['value']}"
            )

            print(
                f"  Percentile: "
                f"{top['percentile_rank']}"
            )

            if (
                top["company_id"]
                ==
                top_rank["company_id"]
            ):
                print(
                    "  ROE ranking check: PASS"
                )
            else:
                print(
                    "  ROE ranking check: FAIL"
                )

        # =============================================================
        # NO PEER GROUP
        # =============================================================

        missing = (
            self.companies_without_peer_group()
        )

        print(
            "\nCompanies without peer group:"
        )

        if missing:

            print(
                "  No peer group assigned"
            )

            print(
                f"  Count: {len(missing)}"
            )

            print(
                "  Companies: "
                + ", ".join(missing)
            )

        else:

            print(
                "  None"
            )

        # =============================================================
        # FINAL STATUS
        # =============================================================

        expected_metrics = 10

        if (
            result["peer_group_name"].nunique()
            == 11
            and
            result["metric"].nunique()
            == expected_metrics
            and
            invalid == 0
        ):

            print(
                "\nDAY 18 VALIDATION: PASS"
            )

        else:

            print(
                "\nDAY 18 VALIDATION: CHECK"
            )

        print("=" * 70)


# =====================================================================
# MAIN
# =====================================================================

def main():

    print("=" * 70)
    print(
        "SPRINT 3 - DAY 18"
    )
    print(
        "PEER PERCENTILE RANKING ENGINE"
    )
    print("=" * 70)

    engine = PeerPercentileEngine()

    print(
        f"\nDatabase: {engine.db_path}"
    )

    peer_groups = (
        engine.load_peer_groups()
    )

    print(
        f"Peer-group assignments: "
        f"{len(peer_groups)}"
    )

    print(
        f"Peer groups: "
        f"{peer_groups['peer_group_name'].nunique()}"
    )

    result = engine.calculate()

    if result.empty:

        raise RuntimeError(
            "No peer percentile records generated."
        )

    engine.save(
        result
    )

    engine.validate(
        result
    )

    # ================================================================
    # DATABASE VERIFICATION
    # ================================================================

    with sqlite3.connect(
        engine.db_path
    ) as connection:

        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM peer_percentiles
            """
        ).fetchone()[0]

    print(
        f"\nSQLite peer_percentiles rows: "
        f"{count}"
    )


if __name__ == "__main__":
    main()