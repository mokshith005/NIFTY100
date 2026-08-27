"""
Sprint 3 - Day 17
Screener Composite Score + Excel Export

Implements:
- P10/P90 winsorisation
- 0-100 metric normalisation
- Profitability score
- Cash Quality score
- Growth score
- Leverage score
- 0-100 Composite Quality Score
- Sector-relative scoring
- Six-sheet Excel screener output
- Threshold-based green/red cell formatting
"""

from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter

from src.screener.engine import ScreenerEngine


ROOT_DIR = Path(__file__).resolve().parents[2]

OUTPUT_DIR = ROOT_DIR / "output"
OUTPUT_FILE = OUTPUT_DIR / "screener_output.xlsx"


# =====================================================================
# SCORE ENGINE
# =====================================================================

class CompositeScoreEngine:
    """Calculate Sprint 3 composite quality scores."""

    # ---------------------------------------------------------------
    # Metrics and directions
    # ---------------------------------------------------------------

    METRIC_DIRECTIONS = {
        "roe": "higher",
        "roce": "higher",
        "npm": "higher",
        "fcf_cagr": "higher",
        "cfo_pat_ratio": "higher",
        "fcf_positive": "higher",
        "revenue_cagr": "higher",
        "pat_cagr": "higher",
        "de": "lower",
        "icr": "higher",
    }

    # ---------------------------------------------------------------
    # P10/P90 winsorisation
    # ---------------------------------------------------------------

    @staticmethod
    def winsorise(series):
        """Cap values at P10 and P90."""

        values = pd.to_numeric(
            series,
            errors="coerce",
        )

        valid = values.dropna()

        if valid.empty:
            return values

        p10 = valid.quantile(0.10)
        p90 = valid.quantile(0.90)

        return values.clip(
            lower=p10,
            upper=p90,
        )

    # ---------------------------------------------------------------
    # 0-100 normalisation
    # ---------------------------------------------------------------

    @classmethod
    def normalise(
        cls,
        series,
        higher_is_better=True,
    ):
        """
        P10/P90 winsorisation followed by 0-100 scaling.
        """

        values = cls.winsorise(series)

        valid = values.dropna()

        if valid.empty:
            return pd.Series(
                50.0,
                index=series.index,
            )

        minimum = valid.min()
        maximum = valid.max()

        if maximum == minimum:
            return pd.Series(
                50.0,
                index=series.index,
            )

        if higher_is_better:
            score = (
                (values - minimum)
                /
                (maximum - minimum)
            ) * 100

        else:
            score = (
                (maximum - values)
                /
                (maximum - minimum)
            ) * 100

        return score.clip(
            0,
            100,
        )

    # ---------------------------------------------------------------
    # Sector-relative normalisation
    # ---------------------------------------------------------------

    @classmethod
    def sector_normalise(
        cls,
        df,
        column,
        higher_is_better=True,
    ):
        """Normalise each metric within broad_sector."""

        result = pd.Series(
            index=df.index,
            dtype=float,
        )

        if "broad_sector" not in df.columns:
            return cls.normalise(
                df[column],
                higher_is_better,
            )

        for sector, indexes in df.groupby(
            "broad_sector",
            dropna=False,
        ).groups.items():

            subset = df.loc[
                indexes,
                column,
            ]

            result.loc[indexes] = cls.normalise(
                subset,
                higher_is_better,
            )

        return result

    # =================================================================
    # COMPONENT SCORES
    # =================================================================

    def calculate(self, df):
        """Calculate all Sprint 3 component scores."""

        result = df.copy()

        # =============================================================
        # PROFITABILITY
        # 35%
        #
        # ROE 15%
        # ROCE 10%
        # NPM 10%
        # =============================================================

        result["score_roe"] = self.sector_normalise(
            result,
            "return_on_equity_pct",
            higher_is_better=True,
        )

        result["score_roce"] = self.sector_normalise(
            result,
            "roce_pct",
            higher_is_better=True,
        )

        result["score_npm"] = self.sector_normalise(
            result,
            "net_profit_margin_pct",
            higher_is_better=True,
        )

        result["profitability_score"] = (
            result["score_roe"] * 0.15
            +
            result["score_roce"] * 0.10
            +
            result["score_npm"] * 0.10
        )

        # =============================================================
        # CASH QUALITY
        # 30%
        #
        # FCF CAGR 15%
        # CFO/PAT ratio 10%
        # FCF positive flag 5%
        # =============================================================

        # Existing Sprint 2 data may contain FCF conversion.
        # Use it as the available FCF quality proxy when FCF CAGR
        # has not yet been calculated.

        if "fcf_cagr" not in result.columns:

            if "free_cash_flow_cr" in result.columns:

                result["fcf_cagr"] = (
                    pd.to_numeric(
                        result[
                            "free_cash_flow_cr"
                        ],
                        errors="coerce",
                    )
                )

            else:
                result["fcf_cagr"] = np.nan

        result["score_fcf_cagr"] = self.sector_normalise(
            result,
            "fcf_cagr",
            higher_is_better=True,
        )

        # CFO / PAT
        if (
            "cash_from_operations_cr" in result.columns
            and "pnl_net_profit_cr" in result.columns
        ):

            cfo = pd.to_numeric(
                result[
                    "cash_from_operations_cr"
                ],
                errors="coerce",
            )

            pat = pd.to_numeric(
                result[
                    "pnl_net_profit_cr"
                ],
                errors="coerce",
            )

            result["cfo_pat_ratio"] = np.where(
                pat.abs() > 0,
                cfo / pat,
                np.nan,
            )

        else:
            result["cfo_pat_ratio"] = np.nan

        result["score_cfo_pat_ratio"] = (
            self.sector_normalise(
                result,
                "cfo_pat_ratio",
                higher_is_better=True,
            )
        )

        # FCF positive flag
        if "free_cash_flow_cr" in result.columns:

            fcf = pd.to_numeric(
                result[
                    "free_cash_flow_cr"
                ],
                errors="coerce",
            )

            result["fcf_positive"] = (
                fcf > 0
            ).astype(float)

        else:
            result["fcf_positive"] = 0.0

        result["score_fcf_positive"] = (
            result["fcf_positive"] * 100
        )

        result["cash_quality_score"] = (
            result["score_fcf_cagr"] * 0.15
            +
            result["score_cfo_pat_ratio"] * 0.10
            +
            result["score_fcf_positive"] * 0.05
        )

        # =============================================================
        # GROWTH
        # 20%
        #
        # Revenue CAGR 10%
        # PAT CAGR 10%
        # =============================================================

        result["score_revenue_growth"] = (
            self.sector_normalise(
                result,
                "revenue_cagr_5yr",
                higher_is_better=True,
            )
        )

        result["score_pat_growth"] = (
            self.sector_normalise(
                result,
                "pat_cagr_5yr",
                higher_is_better=True,
            )
        )

        result["growth_score"] = (
            result["score_revenue_growth"] * 0.10
            +
            result["score_pat_growth"] * 0.10
        )

        # =============================================================
        # LEVERAGE
        # 15%
        #
        # D/E 10%
        # ICR 5%
        # =============================================================

        result["score_de"] = self.sector_normalise(
            result,
            "debt_to_equity",
            higher_is_better=False,
        )

        if "effective_interest_coverage" in result.columns:

            result["score_icr"] = self.sector_normalise(
                result,
                "effective_interest_coverage",
                higher_is_better=True,
            )

        else:

            result["score_icr"] = 50.0

        result["leverage_score"] = (
            result["score_de"] * 0.10
            +
            result["score_icr"] * 0.05
        )

        # =============================================================
        # FINAL SCORE
        # =============================================================

        result["composite_quality_score"] = (
            result["profitability_score"]
            +
            result["cash_quality_score"]
            +
            result["growth_score"]
            +
            result["leverage_score"]
        )

        result[
            "composite_quality_score"
        ] = result[
            "composite_quality_score"
        ].clip(
            0,
            100,
        )

        return result


# =====================================================================
# EXPORTER
# =====================================================================

class ScreenerExcelExporter:

    def __init__(self):

        self.engine = ScreenerEngine()

        self.score_engine = (
            CompositeScoreEngine()
        )

        OUTPUT_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

    # =================================================================
    # BUILD DATA
    # =================================================================

    def build_results(self):

        data = self.engine.load_data()

        scored = self.score_engine.calculate(
            data
        )

        results = {}

        for preset_name in self.engine.config[
            "presets"
        ]:

            thresholds = self.engine.config[
                "presets"
            ][preset_name]

            filtered = self.engine.apply_filters(
                scored,
                thresholds,
            )

            filtered = filtered.sort_values(
                "composite_quality_score",
                ascending=False,
            )

            results[preset_name] = (
                filtered.reset_index(
                    drop=True
                )
            )

        return results

    # =================================================================
    # SELECT 20 KPI COLUMNS
    # =================================================================

    @staticmethod
    def select_kpis(df):

        preferred = [
            "company_id",
            "year",
            "broad_sector",
            "return_on_equity_pct",
            "roce_pct",
            "net_profit_margin_pct",
            "debt_to_equity",
            "interest_coverage",
            "effective_interest_coverage",
            "free_cash_flow_cr",
            "cash_from_operations_cr",
            "fcf_cagr",
            "cfo_pat_ratio",
            "revenue_cagr_5yr",
            "pat_cagr_5yr",
            "eps_cagr_5yr",
            "pe_ratio",
            "pb_ratio",
            "dividend_yield_pct",
            "market_cap_crore",
            "composite_quality_score",
        ]

        available = [
            column
            for column in preferred
            if column in df.columns
        ]

        return df[available].copy()

    # =================================================================
    # EXPORT
    # =================================================================

    def export(self):

        results = self.build_results()

        with pd.ExcelWriter(
            OUTPUT_FILE,
            engine="openpyxl",
        ) as writer:

            for preset_name, df in results.items():

                sheet_name = (
                    preset_name
                    .replace("_", " ")
                    .title()
                )[:31]

                output_df = self.select_kpis(
                    df
                )

                output_df.to_excel(
                    writer,
                    sheet_name=sheet_name,
                    index=False,
                )

        self.format_workbook(
            results
        )

        return OUTPUT_FILE

    # =================================================================
    # FORMAT WORKBOOK
    # =================================================================

    def format_workbook(self, results):

        workbook = load_workbook(
            OUTPUT_FILE
        )

        green_fill = PatternFill(
            fill_type="solid",
            fgColor="C6EFCE",
        )

        red_fill = PatternFill(
            fill_type="solid",
            fgColor="FFC7CE",
        )

        header_fill = PatternFill(
            fill_type="solid",
            fgColor="D9EAF7",
        )

        for preset_name, df in results.items():

            sheet_name = (
                preset_name
                .replace("_", " ")
                .title()
            )[:31]

            ws = workbook[
                sheet_name
            ]

            # ---------------------------------------------------------
            # Header
            # ---------------------------------------------------------

            for cell in ws[1]:

                cell.fill = header_fill
                cell.font = Font(
                    bold=True
                )

                cell.alignment = Alignment(
                    horizontal="center"
                )

            # ---------------------------------------------------------
            # Freeze header
            # ---------------------------------------------------------

            ws.freeze_panes = "A2"

            # ---------------------------------------------------------
            # Threshold formatting
            # ---------------------------------------------------------

            thresholds = self.engine.config[
                "presets"
            ][preset_name]

            output_columns = list(
                self.select_kpis(
                    df
                ).columns
            )

            for row_number in range(
                2,
                ws.max_row + 1,
            ):

                for column_number, column_name in enumerate(
                    output_columns,
                    start=1,
                ):

                    if column_name == "company_id":
                        continue

                    # Find filter associated with
                    # this output column.
                    matching_filters = []

                    for filter_name in thresholds:

                        definition = (
                            self.engine.config[
                                "filters"
                            ].get(
                                filter_name
                            )
                        )

                        if not definition:
                            continue

                        if (
                            definition.get(
                                "column"
                            )
                            == column_name
                        ):
                            matching_filters.append(
                                (
                                    filter_name,
                                    definition,
                                    thresholds[
                                        filter_name
                                    ],
                                )
                            )

                    if not matching_filters:
                        continue

                    cell = ws.cell(
                        row=row_number,
                        column=column_number,
                    )

                    try:
                        value = float(
                            cell.value
                        )
                    except (
                        TypeError,
                        ValueError,
                    ):
                        continue

                    passed = True

                    for (
                        filter_name,
                        definition,
                        threshold,
                    ) in matching_filters:

                        symbol = definition[
                            "operator"
                        ]

                        if symbol == ">":
                            passed &= (
                                value > threshold
                            )

                        elif symbol == ">=":
                            passed &= (
                                value >= threshold
                            )

                        elif symbol == "<":
                            passed &= (
                                value < threshold
                            )

                        elif symbol == "<=":
                            passed &= (
                                value <= threshold
                            )

                        elif symbol == "==":
                            passed &= (
                                value == threshold
                            )

                    cell.fill = (
                        green_fill
                        if passed
                        else red_fill
                    )

            # ---------------------------------------------------------
            # Column widths
            # ---------------------------------------------------------

            for column_cells in ws.columns:

                column_letter = (
                    get_column_letter(
                        column_cells[0].column
                    )
                )

                max_length = 0

                for cell in column_cells:

                    if cell.value is not None:

                        max_length = max(
                            max_length,
                            len(
                                str(
                                    cell.value
                                )
                            ),
                        )

                ws.column_dimensions[
                    column_letter
                ].width = min(
                    max_length + 2,
                    28,
                )

        workbook.save(
            OUTPUT_FILE
        )


# =====================================================================
# MAIN
# =====================================================================

def main():

    print("=" * 70)
    print(
        "SPRINT 3 - DAY 17"
    )
    print(
        "COMPOSITE SCORE + EXCEL EXPORT"
    )
    print("=" * 70)

    exporter = (
        ScreenerExcelExporter()
    )

    results = exporter.build_results()

    print("\nCOMPOSITE SCORE CHECK")
    print("-" * 70)

    for name, df in results.items():

        if df.empty:

            print(
                f"{name:30} 0 companies"
            )

            continue

        scores = pd.to_numeric(
            df[
                "composite_quality_score"
            ],
            errors="coerce",
        )

        print(
            f"{name:30} "
            f"{len(df):3} companies | "
            f"min={scores.min():6.2f} | "
            f"max={scores.max():6.2f} | "
            f"mean={scores.mean():6.2f}"
        )

    output = exporter.export()

    print("\n" + "=" * 70)
    print(
        f"Excel generated: {output}"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()