"""KMeans financial archetype clustering for Nifty100 companies."""

from pathlib import Path
import sqlite3

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


DB_PATH = Path("db/nifty100.db")
OUTPUT_DIR = Path("output")
REPORTS_DIR = Path("reports")

FEATURES = [
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "operating_profit_margin_pct",
]


def load_data():
    """Load clustering features for all 92 companies.

    Primary source is financial_ratios. Missing companies/features are
    supplemented from the underlying financial tables. Remaining missing
    feature values are handled later using sector-median imputation.
    """
    conn = sqlite3.connect(DB_PATH)

    companies = pd.read_sql_query(
        """
        SELECT id AS company_id, company_name
        FROM companies
        """,
        conn,
    )

    ratios = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            operating_profit_margin_pct,
            return_on_equity_pct,
            debt_to_equity,
            revenue_cagr_5yr
        FROM financial_ratios
        """,
        conn,
    )

    sectors = pd.read_sql_query(
        "SELECT * FROM sectors",
        conn,
    )

    pnl = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            sales,
            operating_profit,
            net_profit
        FROM profitandloss
        """,
        conn,
    )

    bs = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            equity_capital,
            reserves,
            borrowings
        FROM balancesheet
        """,
        conn,
    )

    cf = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            operating_activity,
            investing_activity
        FROM cashflow
        """,
        conn,
    )

    conn.close()

    # ------------------------------------------------------------
    # Start with latest financial_ratios record for each company
    # ------------------------------------------------------------
    if not ratios.empty:
        ratios["year"] = pd.to_numeric(ratios["year"], errors="coerce")
        ratios = ratios.sort_values(["company_id", "year"])
        latest = ratios.groupby("company_id", as_index=False).tail(1)
        latest = latest.drop(columns=["year"])
    else:
        latest = pd.DataFrame(columns=[
            "company_id",
            "operating_profit_margin_pct",
            "return_on_equity_pct",
            "debt_to_equity",
            "revenue_cagr_5yr",
        ])

    data = companies.merge(latest, on="company_id", how="left")

    # ------------------------------------------------------------
    # Supplement missing operating margin and ROE from P&L/BS
    # ------------------------------------------------------------
    if not pnl.empty:
        pnl["year"] = pd.to_numeric(pnl["year"], errors="coerce")
        latest_pnl = pnl.sort_values(["company_id", "year"]).groupby(
            "company_id", as_index=False
        ).tail(1)

        pnl_map = latest_pnl.set_index("company_id")

        for idx, row in data.iterrows():
            cid = row["company_id"]

            if cid not in pnl_map.index:
                continue

            p = pnl_map.loc[cid]

            if pd.isna(data.at[idx, "operating_profit_margin_pct"]):
                sales = pd.to_numeric(p.get("sales"), errors="coerce")
                op = pd.to_numeric(p.get("operating_profit"), errors="coerce")

                if pd.notna(sales) and sales != 0 and pd.notna(op):
                    data.at[idx, "operating_profit_margin_pct"] = (
                        op / sales
                    ) * 100

    if not bs.empty and not pnl.empty:
        bs["year"] = pd.to_numeric(bs["year"], errors="coerce")
        latest_bs = bs.sort_values(["company_id", "year"]).groupby(
            "company_id", as_index=False
        ).tail(1)

        bs_map = latest_bs.set_index("company_id")
        pnl_map = latest_pnl.set_index("company_id")

        for idx, row in data.iterrows():
            cid = row["company_id"]

            if cid not in bs_map.index or cid not in pnl_map.index:
                continue

            b = bs_map.loc[cid]
            p = pnl_map.loc[cid]

            equity_capital = pd.to_numeric(
                b.get("equity_capital"), errors="coerce"
            )
            reserves = pd.to_numeric(
                b.get("reserves"), errors="coerce"
            )
            net_profit = pd.to_numeric(
                p.get("net_profit"), errors="coerce"
            )

            equity = equity_capital + reserves

            if (
                pd.isna(data.at[idx, "return_on_equity_pct"])
                and pd.notna(equity)
                and equity != 0
                and pd.notna(net_profit)
            ):
                data.at[idx, "return_on_equity_pct"] = (
                    net_profit / equity
                ) * 100

            if pd.isna(data.at[idx, "debt_to_equity"]):
                borrowings = pd.to_numeric(
                    b.get("borrowings"), errors="coerce"
                )

                if (
                    pd.notna(borrowings)
                    and pd.notna(equity)
                    and equity != 0
                ):
                    data.at[idx, "debt_to_equity"] = (
                        borrowings / equity
                    )

    # ------------------------------------------------------------
    # Calculate FCF CAGR from cash-flow history where available
    # FCF = operating cash flow + investing cash flow
    # ------------------------------------------------------------
    fcf_cagr = {}

    if not cf.empty:
        cf["year"] = pd.to_numeric(cf["year"], errors="coerce")

        for cid, group in cf.groupby("company_id"):
            group = group.sort_values("year").copy()

            group["operating_activity"] = pd.to_numeric(
                group["operating_activity"], errors="coerce"
            )
            group["investing_activity"] = pd.to_numeric(
                group["investing_activity"], errors="coerce"
            )

            group["fcf"] = (
                group["operating_activity"]
                + group["investing_activity"]
            )

            valid = group[
                group["fcf"].notna()
                & (group["fcf"] > 0)
            ]

            if len(valid) >= 2:
                first = valid.iloc[0]
                last = valid.iloc[-1]

                years = last["year"] - first["year"]

                if (
                    pd.notna(years)
                    and years > 0
                    and first["fcf"] > 0
                    and last["fcf"] > 0
                ):
                    fcf_cagr[cid] = (
                        (last["fcf"] / first["fcf"]) ** (1 / years) - 1
                    ) * 100

    data["fcf_cagr_5yr"] = data["company_id"].map(fcf_cagr)

    # ------------------------------------------------------------
    # Normalize sector information
    # ------------------------------------------------------------
    if not sectors.empty:
        sector_cols = sectors.columns.tolist()

        if "company_id" in sector_cols:
            sector_key = "company_id"
        elif "id" in sector_cols:
            sector_key = "id"
            sectors = sectors.rename(columns={"id": "company_id"})
        else:
            sector_key = None

        if sector_key is not None:
            sector_name = None

            for candidate in [
                "broad_sector",
                "sector",
                "sector_name",
                "industry",
            ]:
                if candidate in sectors.columns:
                    sector_name = candidate
                    break

            if sector_name:
                sectors = sectors[
                    ["company_id", sector_name]
                ].rename(columns={sector_name: "broad_sector"})

                data = data.merge(
                    sectors,
                    on="company_id",
                    how="left",
                )

    if "broad_sector" not in data.columns:
        data["broad_sector"] = "Unknown"

    data["broad_sector"] = data["broad_sector"].fillna("Unknown")

    # Ensure all five required features exist.
    for feature in FEATURES:
        if feature not in data.columns:
            data[feature] = np.nan

    return data
    """Load latest financial metrics for all companies."""
    conn = sqlite3.connect(DB_PATH)

    ratios = pd.read_sql_query(
        """
        SELECT
            fr.company_id,
            fr.year,
            fr.return_on_equity_pct,
            fr.debt_to_equity,
            fr.revenue_cagr_5yr,
            fr.operating_profit_margin_pct,
            fr.free_cash_flow_cr
        FROM financial_ratios fr
        ORDER BY fr.company_id, fr.year
        """,
        conn,
    )

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
        SELECT *
        FROM sectors
        """,
        conn,
    )

    conn.close()

    # Calculate 5-year FCF CAGR from the earliest/latest available
    # positive FCF observations within each company's history.
    fcf_records = []

    for company_id, group in ratios.groupby("company_id"):
        group = group.sort_values("year")
        valid = group[group["free_cash_flow_cr"] > 0].copy()

        if len(valid) >= 2:
            first = valid.iloc[0]
            last = valid.iloc[-1]

            try:
                years = int(str(last["year"])[:4]) - int(str(first["year"])[:4])
                if years > 0 and first["free_cash_flow_cr"] > 0:
                    cagr = (
                        (last["free_cash_flow_cr"] / first["free_cash_flow_cr"])
                        ** (1 / years)
                        - 1
                    ) * 100
                else:
                    cagr = np.nan
            except (ValueError, TypeError, ZeroDivisionError):
                cagr = np.nan
        else:
            cagr = np.nan

        fcf_records.append(
            {"company_id": company_id, "fcf_cagr_5yr": cagr}
        )

    fcf_cagr = pd.DataFrame(fcf_records)

    # Latest year per company.
    latest = (
        ratios.sort_values("year")
        .groupby("company_id", as_index=False)
        .tail(1)
        .copy()
    )

    data = latest.merge(fcf_cagr, on="company_id", how="left")
    data = data.merge(companies, on="company_id", how="left")

    # Determine broad sector.
    if "broad_sector" in sectors.columns:
        sector_cols = ["company_id", "broad_sector"]
        sector_data = sectors[sector_cols].drop_duplicates("company_id")
        data = data.merge(sector_data, on="company_id", how="left")
    elif "sector" in sectors.columns:
        sector_data = sectors[
            ["company_id", "sector"]
        ].drop_duplicates("company_id")
        sector_data = sector_data.rename(columns={"sector": "broad_sector"})
        data = data.merge(sector_data, on="company_id", how="left")
    else:
        data["broad_sector"] = "Unknown"

    return data


def sector_median_impute(data: pd.DataFrame) -> pd.DataFrame:
    """Impute missing feature values using sector medians."""
    data = data.copy()

    for feature in FEATURES:
        data[feature] = pd.to_numeric(data[feature], errors="coerce")

        sector_medians = data.groupby("broad_sector")[feature].transform(
            "median"
        )
        data[feature] = data[feature].fillna(sector_medians)

        # Fallback to global median if an entire sector is missing.
        data[feature] = data[feature].fillna(data[feature].median())

    return data


def generate_elbow_plot(X_scaled: np.ndarray) -> None:
    """Generate and save the KMeans elbow plot."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    ks = range(2, 11)
    inertias = []

    for k in ks:
        model = KMeans(
            n_clusters=k,
            random_state=42,
            n_init=20,
        )
        model.fit(X_scaled)
        inertias.append(model.inertia_)

    plt.figure(figsize=(9, 6))
    plt.plot(list(ks), inertias, marker="o")
    plt.xlabel("Number of clusters (k)")
    plt.ylabel("Inertia")
    plt.title("KMeans Elbow Plot")
    plt.xticks(list(ks))
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "elbow_plot.png", dpi=150)
    plt.close()


def name_clusters(data: pd.DataFrame) -> dict[int, str]:
    """Assign descriptive names based on cluster financial profiles."""
    profiles = data.groupby("cluster_id")[FEATURES].mean()

    names = {}

    for cluster_id, row in profiles.iterrows():
        roe = row["return_on_equity_pct"]
        de = row["debt_to_equity"]
        growth = row["revenue_cagr_5yr"]
        fcf = row["fcf_cagr_5yr"]
        opm = row["operating_profit_margin_pct"]

        if roe >= profiles["return_on_equity_pct"].median() and (
            growth >= profiles["revenue_cagr_5yr"].median()
            and opm >= profiles["operating_profit_margin_pct"].median()
        ):
            name = "High-Quality Compounders"
        elif (
            de <= profiles["debt_to_equity"].median()
            and fcf >= profiles["fcf_cagr_5yr"].median()
            and roe >= profiles["return_on_equity_pct"].median()
        ):
            name = "Defensive Dividend Payers"
        elif growth >= profiles["revenue_cagr_5yr"].median():
            name = "Emerging Growth"
        elif de > profiles["debt_to_equity"].median() and roe < 0:
            name = "Distressed or Turnaround"
        else:
            name = "Value Cyclicals"

        names[int(cluster_id)] = name

    # Guarantee five unique labels.
    preferred = [
        "High-Quality Compounders",
        "Defensive Dividend Payers",
        "Value Cyclicals",
        "Distressed or Turnaround",
        "Emerging Growth",
    ]

    used = set()
    for cluster_id in sorted(names):
        if names[cluster_id] in used:
            for candidate in preferred:
                if candidate not in used:
                    names[cluster_id] = candidate
                    break
        used.add(names[cluster_id])

    return names


def run_clustering() -> pd.DataFrame:
    """Run the complete KMeans clustering pipeline."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    data = load_data()

    if len(data) != 92:
        raise ValueError(
            f"Expected 92 companies, but clustering input contains {len(data)}."
        )

    data = sector_median_impute(data)

    X = data[FEATURES].to_numpy(dtype=float)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    generate_elbow_plot(X_scaled)

    model = KMeans(
        n_clusters=5,
        random_state=42,
        n_init=20,
    )

    data["cluster_id"] = model.fit_predict(X_scaled)

    distances = model.transform(X_scaled)
    data["distance_from_centroid"] = distances[
        np.arange(len(data)), data["cluster_id"].to_numpy()
    ]

    names = name_clusters(data)
    data["cluster_name"] = data["cluster_id"].map(names)

    result = data[
        [
            "company_id",
            "cluster_id",
            "cluster_name",
            "distance_from_centroid",
        ]
    ].sort_values("company_id")

    result.to_csv(OUTPUT_DIR / "cluster_labels.csv", index=False)

    print("=" * 60)
    print("SPRINT 6 DAY 36 — KMEANS CLUSTERING")
    print("=" * 60)
    print(f"Companies clustered : {len(result)}")
    print(f"Clusters             : {result['cluster_id'].nunique()}")
    print("\nCluster counts:")
    print(result["cluster_name"].value_counts())
    print("\nOutputs:")
    print(f"  {OUTPUT_DIR / 'cluster_labels.csv'}")
    print(f"  {REPORTS_DIR / 'elbow_plot.png'}")
    print("=" * 60)

    return result


if __name__ == "__main__":
    run_clustering()