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


def main():
    st.set_page_config(page_title="Customer 360 Dashboard", layout="wide")
    st.title("Customer 360 Dashboard")
    st.markdown("A small Customer 360 analytics app built from pipeline outputs.")

    df_cust = load_output("customer_360.csv")
    kpi = load_output("kpi_summary.csv")
    region = load_output("region_revenue.csv")
    category = load_output("category_revenue.csv")

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

    if kpi is not None and not kpi.empty:
        cols = st.columns(len(kpi))
        for idx, row in kpi.iterrows():
            cols[idx].metric(row["metric"].replace("_", " ").title(), row["value"])

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Revenue by Region")
        if region is not None and not region.empty:
            st.bar_chart(region.set_index("region")["total_net_revenue"])
        else:
            st.info("No region revenue data available.")

    with col2:
        st.subheader("Revenue by Product Category")
        if category is not None and not category.empty:
            st.bar_chart(category.set_index("product_category")["total_net_revenue"])
        else:
            st.info("No category revenue data available.")

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
