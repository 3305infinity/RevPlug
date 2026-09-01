"""Regression test for demo scenario / opportunity detector idempotency.

Asserts that firing the same demo scenario twice in a row increases
the recovery queue count by exactly 1, not 2.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_demo_scenario_idempotency_does_not_create_duplicate_rows():
    """Fire scenario twice in a row and assert recovery inbox count increases by exactly 1."""
    # Reset demo data to start clean
    client.post("/api/demo/reset")

    resp1 = client.get("/api/opportunity-inbox")
    assert resp1.status_code == 200
    initial_count = len(resp1.json())

    scenario_payload = {
        "amount_minor": 499900,
        "currency": "INR",
        "error_reason": "authentication_required",
        "method": "card",
        "customer_id": "cust_demo_pivot_101",
        "customer_name": "Swiggy Enterprise Logistics",
        "metadata": {"failure_category": "authentication_required"},
    }

    # Fire 1st time
    r1 = client.post("/api/demo/payment-failure", json=scenario_payload)
    assert r1.status_code == 200

    resp_after_first = client.get("/api/opportunity-inbox")
    assert resp_after_first.status_code == 200
    count_after_first = len(resp_after_first.json())
    assert count_after_first == initial_count + 1, f"Expected count to increase by 1, got {count_after_first}"

    # Fire 2nd time (duplicate replay)
    r2 = client.post("/api/demo/payment-failure", json=scenario_payload)
    assert r2.status_code == 200

    resp_after_second = client.get("/api/opportunity-inbox")
    assert resp_after_second.status_code == 200
    count_after_second = len(resp_after_second.json())

    # Assert no duplicate case was created!
    assert count_after_second == count_after_first, f"Duplicate scenario execution created extra row! Expected {count_after_first}, got {count_after_second}"
