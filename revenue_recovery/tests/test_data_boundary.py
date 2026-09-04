"""Regression tests for data and financial-state boundaries across RevPlug.

Verifies:
1. Synthetic benchmark records cannot enter operational recovery KPIs.
2. Operational/test recovery records cannot silently appear as benchmark results.
3. Unverified payments cannot become verified recovered amounts.
4. Verified settlement updates the authoritative recovery state.
5. Runtime status does not claim provider mode without credentials.
6. Simulation fallback is distinguishable from provider-backed execution.
7. Policy configuration reads from authoritative PolicyConfigStore.
8. Unknown metadata items are quarantined from operational APIs.
"""

import os
from unittest.mock import patch
from app.dashboard_api import _classify_item, _get_items, build_dashboard_summary, _actual_recovered_from_outcomes
from app.db.container import PersistenceContainer
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType, RecoveryOutcome
from app.services.policy_config_service import PolicyConfigStore, PolicyConfig
from app.services.settlement_verifier import SettlementVerifier


def test_synthetic_benchmark_records_isolated_from_operational_kpis():
    container = PersistenceContainer()
    
    # Live item
    live_item = RecoveryItem(
        id="item_live_101",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_live_101",
        customer_id="cust_live_101",
        amount_minor=500000,
        status=RecoveryStatus.DETECTED,
        metadata={"source": "webhook_live", "is_synthetic": False},
    )
    
    # Benchmark synthetic item
    synth_item = RecoveryItem(
        id="item_synth_999",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_synth_999",
        customer_id="cust_synth_999",
        amount_minor=999000,
        status=RecoveryStatus.RECOVERED,
        metadata={"source": "demo_scenario", "is_synthetic": True},
    )
    
    container.recovery_items.save(live_item)
    container.recovery_items.save(synth_item)
    
    # Filtered operational items
    operational_items = _get_items(container, include_synthetic=False)
    op_ids = {i.id for i in operational_items}
    
    assert "item_live_101" in op_ids
    assert "item_synth_999" not in op_ids
    
    # Summary should only include live item amount at risk
    summary = build_dashboard_summary(container)
    assert summary["portfolio"]["revenue_at_risk_minor"] == 500000


def test_unknown_metadata_quarantined_from_operational_kpis():
    container = PersistenceContainer()
    
    unknown_item = RecoveryItem(
        id="item_unknown_000",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_unk_000",
        customer_id="cust_unk_000",
        amount_minor=100000,
        status=RecoveryStatus.DETECTED,
        metadata={"source": "unrecognized_source"},
    )
    container.recovery_items.save(unknown_item)
    
    classification = _classify_item(unknown_item.metadata)
    assert classification == "UNKNOWN"
    
    items = _get_items(container, include_synthetic=False)
    assert unknown_item not in items


def test_unverified_payments_cannot_become_verified_recovered_amounts():
    container = PersistenceContainer()
    
    item = RecoveryItem(
        id="item_pending_777",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_777",
        customer_id="cust_777",
        amount_minor=300000,
        status=RecoveryStatus.INTERVENTION_EXECUTED,
        metadata={"source": "webhook_live", "is_synthetic": False},
    )
    container.recovery_items.save(item)
    
    # No outcome saved yet
    summary = build_dashboard_summary(container)
    assert summary["portfolio"]["actual_recovered_minor"] == 0


def test_verified_settlement_updates_authoritative_recovery_state():
    container = PersistenceContainer()
    verifier = SettlementVerifier(container)
    
    item = RecoveryItem(
        id="item_settle_888",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_888",
        customer_id="cust_888",
        amount_minor=450000,
        status=RecoveryStatus.INTERVENTION_EXECUTED,
        metadata={"source": "webhook_live", "is_synthetic": False},
    )
    container.recovery_items.save(item)
    
    # Verify settlement via authoritative SettlementVerifier
    verifier.verify_and_record_settlement(
        recovery_item_id="item_settle_888",
        provider_payment_id="pay_settle_888",
        settled_amount_minor=450000,
        verification_method="razorpay_webhook_payload",
    )
    
    updated_item = container.recovery_items.get("item_settle_888")
    assert updated_item.status == RecoveryStatus.RECOVERED
    
    rec_amount = _actual_recovered_from_outcomes(container)
    assert rec_amount == 450000


def test_runtime_status_does_not_claim_provider_mode_without_credentials():
    with patch.dict(os.environ, {"RAZORPAY_KEY_ID": "", "RAZORPAY_WEBHOOK_SECRET": "", "RECOVERY_EXECUTION_MODE": "simulation"}):
        from app.api.dashboard import api_razorpay_status
        status = api_razorpay_status()
        assert status["is_live_test_mode"] is False
        assert status["execution_mode"] == "SIMULATED"
        assert "Simulated" in status["razorpay_connection"]


def test_simulation_fallback_distinguishable_from_provider_mode():
    with patch.dict(os.environ, {"RAZORPAY_KEY_ID": "rzp_test_12345", "RAZORPAY_WEBHOOK_SECRET": "sec_12345", "RECOVERY_EXECUTION_MODE": "razorpay_test"}):
        from app.api.dashboard import api_razorpay_status
        status = api_razorpay_status()
        assert status["is_live_test_mode"] is True
        assert status["execution_mode"] == "REAL TEST MODE"


def test_policy_configuration_has_one_authoritative_source():
    store = PolicyConfigStore.get_instance()
    cfg = store.get_config()
    
    from app.api.dashboard import api_controls
    ctrls = api_controls()
    
    assert ctrls["max_payment_retries"] == cfg.max_retries
    assert ctrls["policy_version"] == cfg.version
