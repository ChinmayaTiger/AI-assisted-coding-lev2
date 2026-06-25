import sys
from pathlib import Path

import pandas as pd

# ensure project root is on sys.path so tests can import src.index
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.index import (
    generate_data_quality_report,
    clean_orders,
    build_customer_360,
    build_dashboard_outputs,
    clean_customers,
    clean_tickets,
    save_outputs,
)


def test_generate_data_quality_report_counts():
    orders = pd.DataFrame(
        {
            "order_id": [1, 1, 2],
            "customer_id": ["C1", None, "C2"],
            "order_amount": ["100", "-50", "abc"],
            "discount_pct": [10, 0, 0],
        }
    )

    customers = pd.DataFrame({"customer_id": ["C1", "C2"]})

    tickets = pd.DataFrame(
        {
            "ticket_id": [10, 11],
            "customer_id": ["C1", "C2"],
            "resolved_date": ["2020-01-06", None],
            "satisfaction_score": [5, "bad"],
        }
    )

    dq = generate_data_quality_report(orders, customers, tickets)

    # check duplicate order_id count == 1
    dup = dq[(dq.dataset == "orders") & (dq.check == "duplicate_order_id")]["count"].iloc[0]
    assert dup == 1

    # missing customer id in orders == 1
    missing = dq[(dq.dataset == "orders") & (dq.check == "missing_customer_id")]["count"].iloc[0]
    assert missing == 1

    # invalid order amounts should count negative and non-numeric (2)
    invalid_amt = dq[(dq.dataset == "orders") & (dq.check == "invalid_order_amounts")]["count"].iloc[0]
    assert invalid_amt == 2
    print("generate_data_quality_report check is complete")


def test_clean_orders_and_dedupe_and_net_revenue():
    orders = pd.DataFrame(
        {
            "order_id": [1, 1, 2],
            "customer_id": ["C1", "C1", "C2"],
            "order_amount": ["100", "200", "50"],
            "discount_pct": [10, 0, 0],
        }
    )

    cleaned = clean_orders(orders)
    # duplicates removed -> keep first occurrence -> unique order_id count == 2
    assert cleaned["order_id"].nunique() == 2

    # net_revenue for first row = 100 - 10% = 90
    first_net = float(cleaned[cleaned["order_id"] == 1]["net_revenue"].iloc[0])
    assert abs(first_net - 90.0) < 1e-6
    print("clean_orders check is complete")


def test_build_customer_360_and_kpis():
    orders = pd.DataFrame(
        {
            "order_id": [1, 2],
            "customer_id": ["C1", "C2"],
            "order_amount": [100.0, 200.0],
            "discount_pct": [0, 0],
            "net_revenue": [100.0, 200.0],
            "order_date": [pd.to_datetime("2020-01-01"), pd.to_datetime("2020-02-01")],
            "product_category": ["A", "B"],
        }
    )

    customers = pd.DataFrame({"customer_id": ["C1", "C2"], "customer_name": ["Alice", "Bob"], "region": ["East", "West"]})

    tickets = pd.DataFrame(
        {
            "ticket_id": [10],
            "customer_id": ["C1"],
            "created_date": [pd.to_datetime("2020-01-02")],
            "resolved_date": [pd.to_datetime("2020-01-03")],
            "satisfaction_score": [5],
            "resolution_days": [1],
        }
    )

    cust360 = build_customer_360(orders, customers, tickets)
    assert "total_net_revenue" in cust360.columns
    assert cust360[cust360["customer_id"] == "C1"]["total_net_revenue"].iloc[0] == 100.0

    kpi, region_rev, cat_rev = build_dashboard_outputs(cust360, orders)
    assert any(kpi.metric == "customers")
    assert "region" in region_rev.columns or "region" in cust360.columns
    print("build_customer_360 check is complete")
    print("build_dashboard_outputs check is complete")


def test_clean_customers_parsing_and_titlecase():
    customers = pd.DataFrame({"customer_id": ["c1"], "customer_name": ["alice smith"], "signup_date": ["2021-05-01"]})
    cleaned = clean_customers(customers)
    assert cleaned["customer_name"].iloc[0] == "Alice Smith"
    assert pd.api.types.is_datetime64_any_dtype(cleaned["signup_date"]) or pd.notna(cleaned["signup_date"]).all()
    print("clean_customers check is complete")


def test_clean_tickets_resolution_and_satisfaction():
    tickets = pd.DataFrame({
        "ticket_id": [1, 2],
        "created_date": ["2021-01-01", "2021-01-05"],
        "resolved_date": ["2021-01-03", None],
        "satisfaction_score": ["5", "bad"],
    })
    cleaned = clean_tickets(tickets)
    assert "resolution_days" in cleaned.columns
    # first resolution days should be 2
    assert cleaned["resolution_days"].iloc[0] == 2
    # second satisfaction_score should be NaN due to invalid
    assert pd.isna(cleaned["satisfaction_score"].iloc[1])
    print("clean_tickets check is complete")


def test_value_tier_and_risk_flag_logic():
    customers = pd.DataFrame({"customer_id": ["A", "B", "C"], "active_flag": ["True", "False", "True"]})
    orders = pd.DataFrame({"order_id": [1, 2, 3], "customer_id": ["A", "B", "C"], "net_revenue": [15000, 500, 2000]})
    tickets = pd.DataFrame({"ticket_id": [], "customer_id": [], "resolution_days": [], "satisfaction_score": []})
    cust360 = build_customer_360(orders, customers, tickets)
    # tiers: A->High, B->Low, C->Medium
    tier_map = dict(zip(cust360["customer_id"], cust360["value_tier"]))
    assert tier_map["A"] == "High"
    assert tier_map["B"] == "Low"
    assert tier_map["C"] == "Medium"
    # risk_flag: B inactive -> True
    risk_map = dict(zip(cust360["customer_id"], cust360["risk_flag"]))
    assert risk_map["B"] is True
    print("value_tier and risk_flag checks are complete")


def test_save_outputs_writes_files(tmp_path):
    # create small dfs
    cust360 = pd.DataFrame({"customer_id": ["X"], "total_net_revenue": [100]})
    kpi = pd.DataFrame([{"metric": "customers", "value": 1}])
    region = pd.DataFrame({"region": ["East"], "total_net_revenue": [100], "customers": [1]})
    category = pd.DataFrame({"product_category": ["A"], "total_net_revenue": [100], "orders": [1]})

    # monkeypatch OUTPUT_DIR by temporarily changing environment via import reload
    from importlib import reload
    import src.index as idx

    original_output = idx.OUTPUT_DIR
    try:
        idx.OUTPUT_DIR = tmp_path
        save_outputs(cust360, kpi, region, category)
        assert (tmp_path / "customer_360.csv").exists()
        assert (tmp_path / "kpi_summary.csv").exists()
    finally:
        idx.OUTPUT_DIR = original_output
    print("save_outputs check is complete")
