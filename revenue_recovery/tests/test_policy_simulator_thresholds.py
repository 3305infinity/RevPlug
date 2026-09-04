"""Integration tests for Policy Simulator threshold sensitivity and decision deltas.

Validates that:
1. Changing min_expected_net_ev_minor directly changes decisions (e.g. ₹3,750 Net EV case becomes STOP when threshold raised to ₹4,000).
2. Changing escalation_thresholds_minor changes decisions to ESCALATE for high-value cases.
3. Changing max_contacts_per_24h changes decisions when contact frequency limits are hit.
4. Changing max_intervention_cost_minor blocks high-cost interventions.
5. No live policy configuration is mutated during simulation previews.
6. Expected recovery delta and decision diffs explicitly record policy rule responsible.
"""

import pytest
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.services.policy_simulator import PolicySimulatorService
from app.services.policy_config_service import PolicyConfigStore


def _make_item(
    item_id: str,
    *,
    amount_minor: int = 499900,
    expected_recovery_value: int | None = 375000,
    intervention_cost: int | None = 500,
    proposed_action: str = "send_payment_link",
    recent_contact_count: int = 0,
    attempt_count: int = 1,
    root_cause: str = "payment_timed_out",
) -> RecoveryItem:
    return RecoveryItem(
        id=item_id,
        source_type=SourceType.PAYMENT_FAILURE,
        external_id=f"ext_{item_id}",
        customer_id=f"cust_{item_id}",
        amount_minor=amount_minor,
        currency="INR",
        created_at="2024-01-01T00:00:00Z",
        status=RecoveryStatus.QUEUED,
        root_cause=root_cause,
        expected_recovery_value=expected_recovery_value,
        intervention_cost=intervention_cost,
        metadata={
            "source": "manual_case",
            "is_synthetic": False,
            "proposed_action": proposed_action,
            "attempt_count": attempt_count,
            "recent_contact_count": recent_contact_count,
            "intervention_cost": intervention_cost,
        },
    )


def test_policy_simulator_min_expected_net_ev_delta():
    """Test that Minimum Expected Net EV threshold changes decision for ₹3,750 Net EV case.
    
    - Case has expected recovery ₹3,750 (375000 minor units).
    - Current policy: min_expected_net_ev_minor = 0 -> ALLOWED.
    - Proposed policy: min_expected_net_ev_minor = 400000 (₹4,000) -> STOP.
    - Explicit decision diff: ALLOWED -> STOP.
    """
    store = PolicyConfigStore.get_instance()
    original_config = store.get_config()

    item = _make_item("sim_ev_3750", expected_recovery_value=375000)

    service = PolicySimulatorService()
    service._fetch_opportunities = lambda container, ids: [item]  # type: ignore

    # Preview with min_expected_net_ev_minor = 400000 (₹4,000)
    result = service.preview_policy_change({"min_expected_net_ev_minor": 400000})

    # Verify live policy was NOT mutated
    current_after = store.get_config()
    assert current_after.min_expected_net_ev_minor == original_config.min_expected_net_ev_minor

    # Decision impact checks
    assert result.opportunities_evaluated == 1
    assert result.changed_count == 1
    assert len(result.decision_diffs) == 1

    diff = result.decision_diffs[0]
    assert diff.opportunity_id == "sim_ev_3750"
    assert diff.changed is True
    assert diff.current.decision_type == "ALLOWED"
    assert diff.proposed.decision_type == "STOP"
    assert diff.change_type == "ALLOWED -> STOP"
    assert diff.proposed.reason_code == "ev_below_minimum"
    assert diff.policy_rule_responsible == "min_expected_net_ev_gate"

    # Expected recovery delta: 0 - 375000 = -375000
    assert result.expected_recovery_delta_minor == -375000


def test_policy_simulator_escalation_threshold_delta():
    """Test that lowering escalation threshold changes decision to ESCALATE for high-value case."""
    store = PolicyConfigStore.get_instance()
    original_version = store.get_config().version

    # Case amount ₹15,000 (1500000 minor)
    item = _make_item("sim_esc_15k", amount_minor=1500000)

    service = PolicySimulatorService()
    service._fetch_opportunities = lambda container, ids: [item]  # type: ignore

    # Proposed policy sets escalation threshold to ₹10,000 (1000000 minor)
    result = service.preview_policy_change({"escalation_thresholds_minor": 1000000})

    # Verify live policy version is untouched
    assert store.get_config().version == original_version

    assert result.changed_count == 1
    diff = result.decision_diffs[0]
    assert diff.current.decision_type == "ALLOWED"
    assert diff.proposed.decision_type == "ESCALATE"
    assert diff.change_type == "ALLOWED -> ESCALATE"
    assert diff.proposed.reason_code == "high_value_escalation"
    assert diff.policy_rule_responsible == "escalation_threshold"


def test_policy_simulator_max_contacts_per_24h_delta():
    """Test that lowering max contacts per 24h blocks outbound action."""
    store = PolicyConfigStore.get_instance()

    # Case has 2 recent contacts
    item = _make_item("sim_contacts_2", recent_contact_count=2, proposed_action="send_payment_link")

    service = PolicySimulatorService()
    service._fetch_opportunities = lambda container, ids: [item]  # type: ignore

    # Proposed policy sets max_contacts_per_24h = 2 -> 2 contacts hits threshold (>= 2)
    result = service.preview_policy_change({"max_contacts_per_24h": 2})

    assert result.changed_count == 1
    diff = result.decision_diffs[0]
    assert diff.current.decision_type == "ALLOWED"
    assert diff.proposed.decision_type == "ESCALATE"
    assert diff.proposed.reason_code == "CONTACT_FREQUENCY_LIMIT"


def test_policy_simulator_max_intervention_cost_delta():
    """Test that setting max_intervention_cost_minor below item cost blocks intervention."""
    item = _make_item("sim_cost_600", intervention_cost=600)

    service = PolicySimulatorService()
    service._fetch_opportunities = lambda container, ids: [item]  # type: ignore

    # Proposed policy sets max_intervention_cost_minor = 400 (₹4)
    result = service.preview_policy_change({"max_intervention_cost_minor": 400})

    assert result.changed_count == 1
    diff = result.decision_diffs[0]
    assert diff.current.decision_type == "ALLOWED"
    assert diff.proposed.decision_type == "STOP"
    assert diff.proposed.reason_code == "cost_exceeds_maximum"
    assert diff.policy_rule_responsible == "max_intervention_cost_gate"
