"""
Sprint 3 - Day 19
Peer Group Radar Charts

Generates radar/polar charts for:
- Companies assigned to a peer group
- Companies without a peer group

Peer-group charts compare:
    Company vs Peer Group Average

Standalone charts compare:
    Company vs Nifty 100 Average

Output:
    reports/radar_charts/<company_id>_radar.png
"""

from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ================================================================
# PATHS
# ================================================================

ROOT_DIR = Path(__file__).resolve().parents[2]

DB_PATH = ROOT_DIR / "db" / "nifty100.db"

OUTPUT_DIR = ROOT_DIR / "reports" / "radar_charts"

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ================================================================
# ENGINE
# ================================================================

class RadarChartEngine:

    def __init__(self, db_path=DB_PATH):

        self.db_path = Path(db_path)

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Database not found: {self.db_path}"
            )

    # ============================================================
    # LOAD DATA
    # ============================================================

    def load_data(self):

        query = """
        WITH latest_ratios AS (

            SELECT
                fr.*,

                ROW_NUMBER() OVER (
                    PARTITION BY fr.company_id
                    ORDER BY CAST(fr.year AS REAL) DESC
                ) AS rn

            FROM financial_ratios fr
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
            fr.composite_quality_score,

            fr.eps_cagr_5yr,
            fr.interest_coverage,
            fr.asset_turnover

        FROM latest_ratios fr

        WHERE fr.rn = 1
        """

        with sqlite3.connect(
            self.db_path
        ) as connection:

            return pd.read_sql_query(
                query,
                connection,
            )

    # ============================================================
    # LOAD PEER GROUPS
    # ============================================================

    def load_peer_groups(self):

        query = """
        SELECT
            peer_group_name,
            company_id,
            is_benchmark
        FROM peer_groups
        """

        with sqlite3.connect(
            self.db_path
        ) as connection:

            return pd.read_sql_query(
                query,
                connection,
            )

    # ============================================================
    # METRIC COLUMNS
    # ============================================================

    @staticmethod
    def metric_columns():

        return {
            "ROE": "return_on_equity_pct",
            "ROCE": "roce_pct",
            "NPM": "net_profit_margin_pct",
            "D/E": "debt_to_equity",
            "FCF Score": "free_cash_flow_cr",
            "PAT CAGR 5yr": "pat_cagr_5yr",
            "Revenue CAGR 5yr": "revenue_cagr_5yr",
            "Composite Score": "composite_quality_score",
        }

    # ============================================================
    # NORMALISE VALUES
    # ============================================================

    @staticmethod
    def normalize_metric(
        series,
        inverse=False,
    ):

        values = pd.to_numeric(
            series,
            errors="coerce",
        )

        values = values.replace(
            [np.inf, -np.inf],
            np.nan,
        )

        if values.notna().sum() == 0:
            return pd.Series(
                50.0,
                index=series.index,
            )

        p10 = values.quantile(0.10)
        p90 = values.quantile(0.90)

        if pd.isna(p10) or pd.isna(p90):

            result = pd.Series(
                50.0,
                index=series.index,
            )

            return result

        if p90 == p10:

            result = pd.Series(
                50.0,
                index=series.index,
            )

            result[values.isna()] = 50.0

            return result

        clipped = values.clip(
            lower=p10,
            upper=p90,
        )

        result = (
            (clipped - p10)
            /
            (p90 - p10)
            *
            100
        )

        if inverse:

            result = 100 - result

        return result.fillna(50.0)

    # ============================================================
    # BUILD RADAR VALUES
    # ============================================================

    def build_metric_frame(
        self,
        data,
    ):

        metrics = self.metric_columns()

        output = pd.DataFrame(
            index=data.index
        )

        for metric, column in metrics.items():

            inverse = metric == "D/E"

            output[metric] = (
                self.normalize_metric(
                    data[column],
                    inverse=inverse,
                )
            )

        return output

    # ============================================================
    # CREATE SINGLE RADAR
    # ============================================================

    def create_chart(
        self,
        company_id,
        company_values,
        reference_values,
        reference_label,
        peer_group=None,
    ):

        labels = list(
            company_values.index
        )

        company = np.asarray(
            company_values.values,
            dtype=float,
        )

        reference = np.asarray(
            reference_values.values,
            dtype=float,
        )

        number_of_axes = len(labels)

        angles = np.linspace(
            0,
            2 * np.pi,
            number_of_axes,
            endpoint=False,
        ).tolist()

        company = np.concatenate(
            [company, [company[0]]]
        )

        reference = np.concatenate(
            [reference, [reference[0]]]
        )

        angles += [angles[0]]

        fig, ax = plt.subplots(
            figsize=(8, 8),
            subplot_kw={
                "polar": True
            },
        )

        # Company polygon

        ax.plot(
            angles,
            company,
            linewidth=2,
            label=company_id,
        )

        ax.fill(
            angles,
            company,
            alpha=0.20,
        )

        # Reference polygon

        ax.plot(
            angles,
            reference,
            linestyle="--",
            linewidth=2,
            label=reference_label,
        )

        ax.set_xticks(
            angles[:-1]
        )

        ax.set_xticklabels(
            labels,
            fontsize=10,
        )

        ax.set_ylim(
            0,
            100,
        )

        ax.set_yticks(
            [20, 40, 60, 80, 100]
        )

        ax.set_yticklabels(
            ["20", "40", "60", "80", "100"],
            fontsize=8,
        )

        if peer_group:

            title = (
                f"{company_id} - {peer_group}\n"
                f"Company vs Peer Group Average"
            )

        else:

            title = (
                f"{company_id}\n"
                f"Company vs Nifty 100 Average"
            )

        ax.set_title(
            title,
            fontsize=14,
            pad=25,
        )

        ax.legend(
            loc="upper right",
            bbox_to_anchor=(1.25, 1.10),
        )

        fig.tight_layout()

        filename = (
            f"{company_id}_radar.png"
        )

        filepath = (
            OUTPUT_DIR / filename
        )

        fig.savefig(
            filepath,
            dpi=160,
            bbox_inches="tight",
        )

        plt.close(fig)

        return filepath

    # ============================================================
    # GENERATE ALL CHARTS
    # ============================================================

    def generate(self):

        data = self.load_data()

        peer_groups = self.load_peer_groups()

        metric_data = self.build_metric_frame(
            data
        )

        generated = []

        # ============================================================
        # PEER-GROUP COMPANIES
        # ============================================================

        assigned_ids = set(
            peer_groups["company_id"]
        )

        for peer_group in sorted(
            peer_groups[
                "peer_group_name"
            ].unique()
        ):

            assignments = peer_groups[
                peer_groups[
                    "peer_group_name"
                ]
                == peer_group
            ]

            company_ids = list(
                assignments[
                    "company_id"
                ]
            )

            group_rows = data[
                data["company_id"].isin(
                    company_ids
                )
            ]

            group_metric_rows = metric_data.loc[
                group_rows.index
            ]

            if group_metric_rows.empty:
                continue

            peer_average = (
                group_metric_rows.mean(
                    axis=0
                )
            )

            for company_id in company_ids:

                matching = data[
                    data["company_id"]
                    == company_id
                ]

                if matching.empty:
                    continue

                idx = matching.index[0]

                company_values = (
                    metric_data.loc[idx]
                )

                filepath = self.create_chart(
                    company_id=company_id,
                    company_values=company_values,
                    reference_values=peer_average,
                    reference_label="Peer Average",
                    peer_group=peer_group,
                )

                generated.append(
                    filepath
                )

        # ============================================================
        # COMPANIES WITHOUT PEER GROUP
        # ============================================================

        all_metric_average = (
            metric_data.mean(
                axis=0
            )
        )

        unassigned = sorted(
            set(data["company_id"])
            - assigned_ids
        )

        for company_id in unassigned:

            matching = data[
                data["company_id"]
                == company_id
            ]

            if matching.empty:
                continue

            idx = matching.index[0]

            company_values = (
                metric_data.loc[idx]
            )

            filepath = self.create_chart(
                company_id=company_id,
                company_values=company_values,
                reference_values=all_metric_average,
                reference_label="Nifty 100 Average",
                peer_group=None,
            )

            generated.append(
                filepath
            )

        return generated


# ================================================================
# VALIDATION
# ================================================================

def validate_output(
    generated,
    peer_groups,
):

    print("\n" + "=" * 70)
    print("DAY 19 RADAR CHART VALIDATION")
    print("=" * 70)

    print(
        f"Charts generated       : {len(generated)}"
    )

    existing = [
        path
        for path in generated
        if path.exists()
    ]

    print(
        f"PNG files confirmed     : {len(existing)}"
    )

    expected_companies = (
        peer_groups["company_id"]
        .nunique()
    )

    print(
        f"Peer-group companies    : "
        f"{expected_companies}"
    )

    print(
        f"Peer groups             : "
        f"{peer_groups['peer_group_name'].nunique()}"
    )

    print(
        f"Output directory        : "
        f"{OUTPUT_DIR}"
    )

    if len(existing) == 0:

        print(
            "\nDAY 19 VALIDATION: FAIL"
        )

        return

    # Check filename format

    bad_names = [
        path.name
        for path in existing
        if not path.name.endswith(
            "_radar.png"
        )
    ]

    print(
        f"Invalid filenames       : "
        f"{len(bad_names)}"
    )

    # Check file sizes

    empty_files = [
        path.name
        for path in existing
        if path.stat().st_size == 0
    ]

    print(
        f"Empty PNG files         : "
        f"{len(empty_files)}"
    )

    # Final

    if (
        len(existing) > 0
        and len(bad_names) == 0
        and len(empty_files) == 0
    ):

        print(
            "\nDAY 19 VALIDATION: PASS"
        )

    else:

        print(
            "\nDAY 19 VALIDATION: CHECK"
        )

    print("=" * 70)


# ================================================================
# MAIN
# ================================================================

def main():

    print("=" * 70)
    print("SPRINT 3 - DAY 19")
    print("RADAR / POLAR CHART GENERATION")
    print("=" * 70)

    engine = RadarChartEngine()

    print(
        f"\nDatabase: {engine.db_path}"
    )

    peer_groups = (
        engine.load_peer_groups()
    )

    print(
        f"Peer groups: "
        f"{peer_groups['peer_group_name'].nunique()}"
    )

    print(
        f"Peer assignments: "
        f"{len(peer_groups)}"
    )

    generated = engine.generate()

    validate_output(
        generated,
        peer_groups,
    )

    print(
        f"\nRadar charts saved to:"
    )

    print(
        f"  {OUTPUT_DIR}"
    )

    # Show first few files

    print("\nSample files:")

    for path in generated[:10]:

        print(
            f"  {path.name}"
        )


if __name__ == "__main__":
    main()