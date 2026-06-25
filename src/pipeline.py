from pathlib import Path
import logging
import sys
import pandas as pd
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"


def load_sources():
    """Load orders, customers and tickets from CSV or XLSX with existence checks.

    Preference order: CSV -> XLSX. Logs row counts and columns for quick validation.
    """
    files = {
        "orders": (DATA_DIR / "orders_source.csv", DATA_DIR / "orders_source.xlsx"),
        "customers": (DATA_DIR / "customers_source.csv", DATA_DIR / "customers_source.xlsx"),
        "tickets": (DATA_DIR / "support_tickets_source.csv", DATA_DIR / "support_tickets_source.xlsx"),
    }

    dfs = {}
    for name, (csv_path, xlsx_path) in files.items():
        if csv_path.exists():
            path = csv_path
            reader = pd.read_csv
        elif xlsx_path.exists():
            path = xlsx_path
            reader = pd.read_excel
        else:
            logging.error("Missing source file for %s. Checked: %s and %s", name, csv_path, xlsx_path)
            raise FileNotFoundError(f"Missing source file for {name}: checked {csv_path} and {xlsx_path}")

        try:
            df = reader(path)
        except Exception as exc:
            logging.error("Failed to read %s (%s): %s", name, path, exc)
            raise

        logging.info("Loaded %s: %d rows, columns: %s", name, len(df), list(df.columns))
        dfs[name] = df

    return dfs["orders"], dfs["customers"], dfs["tickets"]


def generate_data_quality_report(orders: pd.DataFrame, customers: pd.DataFrame, tickets: pd.DataFrame) -> pd.DataFrame:
    """Generate basic data-quality checks for the three datasets."""
    report_rows = []

    # Orders
    total_orders = len(orders)
    dup_orders = int(orders["order_id"].duplicated().sum()) if "order_id" in orders.columns else 0
    missing_cust_orders = int(orders["customer_id"].isna().sum()) if "customer_id" in orders.columns else 0
    order_amounts = pd.to_numeric(orders.get("order_amount", pd.Series()), errors="coerce")
    invalid_order_amounts = int(order_amounts.isna().sum() + (order_amounts < 0).sum()) if not order_amounts.empty else 0

    report_rows.extend([
        {"dataset": "orders", "check": "total_rows", "count": total_orders},
        {"dataset": "orders", "check": "duplicate_order_id", "count": dup_orders},
        {"dataset": "orders", "check": "missing_customer_id", "count": missing_cust_orders},
        {"dataset": "orders", "check": "invalid_order_amounts", "count": invalid_order_amounts},
    ])

    # Customers
    total_customers = len(customers)
    dup_customers = int(customers["customer_id"].duplicated().sum()) if "customer_id" in customers.columns else 0
    missing_cust_customers = int(customers["customer_id"].isna().sum()) if "customer_id" in customers.columns else 0

    report_rows.extend([
        {"dataset": "customers", "check": "total_rows", "count": total_customers},
        {"dataset": "customers", "check": "duplicate_customer_id", "count": dup_customers},
        {"dataset": "customers", "check": "missing_customer_id", "count": missing_cust_customers},
    ])

    # Tickets
    total_tickets = len(tickets)
    missing_resolved = int(tickets["resolved_date"].isna().sum()) if "resolved_date" in tickets.columns else 0
    sat = pd.to_numeric(tickets.get("satisfaction_score", pd.Series()), errors="coerce")
    invalid_satisfaction = int(sat.isna().sum()) if not sat.empty else 0

    report_rows.extend([
        {"dataset": "tickets", "check": "total_rows", "count": total_tickets},
        {"dataset": "tickets", "check": "missing_resolved_date", "count": missing_resolved},
        {"dataset": "tickets", "check": "invalid_satisfaction_score", "count": invalid_satisfaction},
    ])

    return pd.DataFrame(report_rows)


def clean_orders(orders: pd.DataFrame) -> pd.DataFrame:
    """Clean orders: trim strings, coerce numerics/dates, compute net_revenue, drop duplicate order_id."""
    df = orders.copy()
    # Trim string fields
    if "customer_id" in df.columns:
        df["customer_id"] = df["customer_id"].astype(str).str.strip()
    if "customer_name" in df.columns:
        df["customer_name"] = df["customer_name"].astype(str).str.title()

    # Coerce numerics
    df["order_amount"] = pd.to_numeric(df.get("order_amount", pd.Series()), errors="coerce")
    df["discount_pct"] = pd.to_numeric(df.get("discount_pct", pd.Series()), errors="coerce").fillna(0)
    df["quantity"] = pd.to_numeric(df.get("quantity", pd.Series()), errors="coerce")

    # Parse dates
    if "order_date" in df.columns:
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")

    # Compute net revenue
    df["net_revenue"] = df["order_amount"] - (df["order_amount"] * df["discount_pct"] / 100)

    # Drop duplicate order_id (keep first)
    if "order_id" in df.columns:
        dup_count = int(df["order_id"].duplicated().sum())
        if dup_count > 0:
            logging.info("Dropping %d duplicate order_id rows", dup_count)
            df = df[~df["order_id"].duplicated()]

    return df


def clean_customers(customers: pd.DataFrame) -> pd.DataFrame:
    df = customers.copy()
    if "customer_name" in df.columns:
        df["customer_name"] = df["customer_name"].astype(str).str.title()
    if "signup_date" in df.columns:
        df["signup_date"] = pd.to_datetime(df["signup_date"], errors="coerce")
    return df


def clean_tickets(tickets: pd.DataFrame) -> pd.DataFrame:
    df = tickets.copy()
    if "created_date" in df.columns:
        df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    if "resolved_date" in df.columns:
        df["resolved_date"] = pd.to_datetime(df["resolved_date"], errors="coerce")
    if "satisfaction_score" in df.columns:
        df["satisfaction_score"] = pd.to_numeric(df["satisfaction_score"], errors="coerce")

    # resolution days
    if "created_date" in df.columns and "resolved_date" in df.columns:
        df["resolution_days"] = (df["resolved_date"] - df["created_date"]).dt.days

    return df


def main():
    orders, customers, tickets = load_sources()

    # pre-clean data quality report
    try:
        dq = generate_data_quality_report(orders, customers, tickets)
        print("Pre-clean data quality checks:\n", dq.to_string(index=False))
    except Exception as exc:
        logging.warning("Failed to generate pre-clean data quality report: %s", exc)

    # clean datasets
    orders = clean_orders(orders)
    customers = clean_customers(customers)
    tickets = clean_tickets(tickets)

    # print cleaned previews
    # print("\nOrders (cleaned) - first 5 rows:\n")
    # print(orders.head(5).to_string(index=False))
    # print("\nCustomers (cleaned) - first 5 rows:\n")
    # print(customers.head(5).to_string(index=False))
    # print("\nTickets (cleaned) - first 5 rows:\n")
    # print(tickets.head(5).to_string(index=False))

    # write post-clean data quality report
    try:
        OUTPUT_DIR.mkdir(exist_ok=True)
        dq.to_csv(OUTPUT_DIR / "data_quality_report.csv", index=False)
        logging.info("Saved data quality report to %s", OUTPUT_DIR / "data_quality_report.csv")
    except Exception as exc:
        logging.warning("Failed to save data quality report: %s", exc)

    # Deduplicate already handled in clean_orders; build customer 360
    customer_360 = build_customer_360(orders, customers, tickets)

    # Build dashboard outputs
    kpi_summary, region_revenue, category_revenue = build_dashboard_outputs(customer_360, orders)

    # Save outputs
    try:
        save_outputs(customer_360, kpi_summary, region_revenue, category_revenue)
        logging.info("Saved pipeline outputs to %s", OUTPUT_DIR)
    except Exception as exc:
        logging.error("Failed to save outputs: %s", exc)


def build_customer_360(orders: pd.DataFrame, customers: pd.DataFrame, tickets: pd.DataFrame) -> pd.DataFrame:
    """Aggregate orders and tickets to customer-level and enrich with value tier and risk flag."""
    # Ensure numeric fields exist
    orders = orders.copy()
    tickets = tickets.copy()

    order_aggs = {
        "order_count": ("order_id", "count"),
        "total_net_revenue": ("net_revenue", "sum"),
        "average_order_value": ("net_revenue", "mean"),
    }
    if "order_date" in orders.columns:
        order_aggs["last_order_date"] = ("order_date", "max")

    order_summary = orders.groupby("customer_id").agg(**order_aggs).reset_index()

    ticket_summary = (
        tickets.groupby("customer_id")
        .agg(
            ticket_count=("ticket_id", "count"),
            avg_resolution_days=("resolution_days", "mean"),
            avg_satisfaction_score=("satisfaction_score", "mean"),
        )
        .reset_index()
    )

    customer_360 = customers.merge(order_summary, on="customer_id", how="left")
    customer_360 = customer_360.merge(ticket_summary, on="customer_id", how="left")

    # Fill numeric NaNs with 0 where appropriate
    for col in ["order_count", "total_net_revenue", "average_order_value", "ticket_count"]:
        if col in customer_360.columns:
            customer_360[col] = customer_360[col].fillna(0)

    # Value tier
    if "total_net_revenue" in customer_360.columns:
        def tier(val):
            if val >= 10000:
                return "High"
            if val >= 1000:
                return "Medium"
            return "Low"

        customer_360["value_tier"] = customer_360["total_net_revenue"].apply(tier)

    # Risk flag: unhappy customers or slow resolution or inactive
    def risk_flag(row):
        if pd.notna(row.get("avg_satisfaction_score")) and row.get("avg_satisfaction_score") < 3:
            return True
        if pd.notna(row.get("avg_resolution_days")) and row.get("avg_resolution_days") > 7:
            return True
        if "active_flag" in row.index and pd.notna(row.get("active_flag")) and (str(row.get("active_flag")).strip().lower() in ["false", "0", "n", "no"]):
            return True
        return False

    customer_360["risk_flag"] = customer_360.apply(risk_flag, axis=1)

    return customer_360


def build_dashboard_outputs(customer_360: pd.DataFrame, orders: pd.DataFrame):
    # KPIs
    kpi_summary = pd.DataFrame(
        [
            {"metric": "customers", "value": int(customer_360["customer_id"].nunique())},
            {"metric": "total_net_revenue", "value": float(customer_360.get("total_net_revenue", pd.Series()).sum())},
            {"metric": "average_order_value", "value": float(customer_360.get("average_order_value", pd.Series()).mean())},
            {"metric": "average_satisfaction_score", "value": float(customer_360.get("avg_satisfaction_score", pd.Series()).mean())},
        ]
    )

    region_revenue = (
        customer_360.groupby("region")
        .agg(total_net_revenue=("total_net_revenue", "sum"), customers=("customer_id", "count"))
        .reset_index()
    )

    category_revenue = (
        orders.groupby("product_category")
        .agg(total_net_revenue=("net_revenue", "sum"), orders=("order_id", "count"))
        .reset_index()
    )

    return kpi_summary, region_revenue, category_revenue


def save_outputs(customer_360: pd.DataFrame, kpi_summary: pd.DataFrame, region_revenue: pd.DataFrame, category_revenue: pd.DataFrame):
    OUTPUT_DIR.mkdir(exist_ok=True)
    customer_360.to_csv(OUTPUT_DIR / "customer_360.csv", index=False)
    kpi_summary.to_csv(OUTPUT_DIR / "kpi_summary.csv", index=False)
    region_revenue.to_csv(OUTPUT_DIR / "region_revenue.csv", index=False)
    category_revenue.to_csv(OUTPUT_DIR / "category_revenue.csv", index=False)


if __name__ == "__main__":
	main()

