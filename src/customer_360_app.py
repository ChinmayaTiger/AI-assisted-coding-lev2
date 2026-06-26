import streamlit as st
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"


@st.cache_data
def load_output(name: str):
    path = OUTPUT_DIR / name
    if not path.exists():
        return None
    return pd.read_csv(path)


@st.cache_data
def load_orders_source():
    csv_path = ROOT / "data" / "orders_source.csv"
    xlsx_path = ROOT / "data" / "orders_source.xlsx"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    if xlsx_path.exists():
        return pd.read_excel(xlsx_path)
    return None


def main():
    st.set_page_config(page_title="Customer 360 Dashboard", layout="wide")
    st.title("Customer 360 Dashboard")
    st.markdown("A small Customer 360 analytics app built from pipeline outputs.")

    df_cust = load_output("customer_360.csv")
    kpi = load_output("kpi_summary.csv")
    region = load_output("region_revenue.csv")
    category = load_output("category_revenue.csv")
    orders_source = load_orders_source()

    if df_cust is None:
        st.error("Missing outputs/customer_360.csv — run the pipeline first.")
        return

    st.sidebar.header("Filters")
    region_options = sorted(df_cust["region"].dropna().unique()) if "region" in df_cust.columns else []
    tier_options = sorted(df_cust["value_tier"].dropna().unique()) if "value_tier" in df_cust.columns else []

    selected_regions = st.sidebar.multiselect("Region", options=region_options, default=region_options)
    selected_tiers = st.sidebar.multiselect("Value Tier", options=tier_options, default=tier_options)
    risk_only = st.sidebar.checkbox("Show risk customers only", value=False)

    filtered = df_cust.copy()
    if selected_regions and "region" in filtered.columns:
        filtered = filtered[filtered["region"].isin(selected_regions)]
    if selected_tiers and "value_tier" in filtered.columns:
        filtered = filtered[filtered["value_tier"].isin(selected_tiers)]
    if risk_only and "risk_flag" in filtered.columns:
        filtered = filtered[filtered["risk_flag"] == True]

    kpi_display = {
        "Customers": int(filtered["customer_id"].nunique()) if "customer_id" in filtered.columns else 0,
        "Total Net Revenue": float(filtered.get("total_net_revenue", pd.Series(dtype=float)).sum()),
        "Average Order Value": float(filtered.get("average_order_value", pd.Series(dtype=float)).mean()) if "average_order_value" in filtered.columns else 0.0,
        "Average Satisfaction Score": float(filtered.get("avg_satisfaction_score", pd.Series(dtype=float)).mean()) if "avg_satisfaction_score" in filtered.columns else 0.0,
    }

    if kpi_display:
        cols = st.columns(len(kpi_display))
        for idx, (label, value) in enumerate(kpi_display.items()):
            cols[idx].metric(label, round(value, 2) if isinstance(value, float) else value)

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Revenue by Region")
        if "region" in filtered.columns and not filtered.empty:
            region_filtered = filtered.groupby("region").agg(total_net_revenue=("total_net_revenue", "sum")).reset_index()
            st.bar_chart(region_filtered.set_index("region")["total_net_revenue"])
        else:
            st.info("No region revenue data available for current filter selection.")

    with col2:
        st.subheader("Revenue by Product Category")
        if orders_source is not None and not orders_source.empty and "customer_id" in filtered.columns:
            orders_filtered = orders_source.copy()
            customer_ids = filtered["customer_id"].dropna().unique()
            if len(customer_ids) > 0:
                orders_filtered = orders_filtered[orders_filtered["customer_id"].isin(customer_ids)]
            else:
                orders_filtered = orders_filtered.iloc[0:0]

            if not orders_filtered.empty:
                orders_filtered["order_amount"] = pd.to_numeric(orders_filtered.get("order_amount", pd.Series()), errors="coerce")
                orders_filtered["discount_pct"] = pd.to_numeric(orders_filtered.get("discount_pct", pd.Series()), errors="coerce").fillna(0)
                orders_filtered["net_revenue"] = orders_filtered["order_amount"] - (orders_filtered["order_amount"] * orders_filtered["discount_pct"] / 100)
                category_filtered = orders_filtered.groupby("product_category").agg(total_net_revenue=("net_revenue", "sum")).reset_index()
                st.bar_chart(category_filtered.set_index("product_category")["total_net_revenue"])
            else:
                st.info("No category revenue data available for current filter selection.")
        else:
            st.info("No category revenue data available for current filter selection.")

    st.markdown("---")
    st.subheader("Customer 360 Table")
    st.dataframe(filtered)

    st.markdown("---")
    download_csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered customer_360.csv",
        data=download_csv,
        file_name="customer_360_filtered.csv",
        mime="text/csv",
    )

    if "risk_flag" in filtered.columns:
        st.markdown("---")
        st.subheader("Risk Customer Summary")
        risk_count = int(filtered[filtered["risk_flag"] == True].shape[0])
        st.write(f"Total customers flagged as risk: {risk_count}")

if __name__ == "__main__":
    main()
