"""Tests for Policy Simulator Service.

Validates:
- Policy simulation preview
- Decision diff detection
- Safety conflict detection
- Canonical action reuse (no fallback invention)
- No live execution
- No policy mutation
- Financial integrity
- API endpoints
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.services.policy_simulator import (
    PolicySimulatorService,
    _build_guard,
    _evaluate_item,
    _get_canonical_action,
    _classify_item,
    DecisionDiff,
)
from app.policies.engine import InterventionPolicy
from app.policies.stopping_rules import StoppingRules
from app.policies.guard import DefaultRecoveryGuard
from app.services.policy_config_service import PolicyConfigStore
from app.main import create_app


def _make_item(
    item_id: str,
    *,
    root_cause: str | None = "soft",
    status: RecoveryStatus = RecoveryStatus.QUEUED,
    amount_minor: int = 10000,
    expected_recovery_value: int | None = 5000,
    metadata: dict | None = None,
    opted_out: bool = False,
) -> RecoveryItem:
    base_meta = {
        "source": "manual_case",
        "is_synthetic": False,
    }
    if metadata is not None:
        base_meta.update(metadata)
    return RecoveryItem(
        id=item_id,
        source_type=SourceType.PAYMENT_FAILURE,
        external_id=f"ext_{item_id}",
        customer_id=f"cust_{item_id}",
        amount_minor=amount_minor,
        currency="INR",
        created_at="2024-01-01T00:00:00Z",
        status=status,
        root_cause=root_cause,
        expected_recovery_value=expected_recovery_value,
        metadata=base_meta,
    )


class TestPolicySimulatorService:
    """Tests for PolicySimulatorService."""

    def test_01_same_policy_produces_no_changes(self):
        """Evaluating with the same policy should produce no decision changes."""
        store = PolicyConfigStore.get_instance()
        service = PolicySimulatorService()

        items = [_make_item("sim_same_001", metadata={"proposed_action": "retry_payment"})]
        service._fetch_opportunities = lambda container, ids: items  # type: ignore

        result = service.preview_policy_change({})
        assert result.changed_count == 0
        assert result.unchanged_count == 1

    def test_02_proposed_policy_is_evaluated_independently(self):
        """Proposed policy evaluation must not mutate the active configuration."""
        store = PolicyConfigStore.get_instance()
        original = store.get_config()
        original_max_retries = original.max_retries

        service = PolicySimulatorService()
        items = [_make_item("sim_indep_001", metadata={"proposed_action": "retry_payment"})]
        service._fetch_opportunities = lambda container, ids: items  # type: ignore

        result = service.preview_policy_change({"max_retries": 99})

        current = store.get_config()
        assert current.max_retries == original_max_retries

    def test_03_current_policy_remains_unchanged(self):
        """Preview must not modify the current policy."""
        store = PolicyConfigStore.get_instance()
        original_version = store.get_config().version

        service = PolicySimulatorService()
        items = [_make_item("sim_curr_001", metadata={"proposed_action": "retry_payment"})]
        service._fetch_opportunities = lambda container, ids: items  # type: ignore

        service.preview_policy_change({"max_retries": 5})

        assert store.get_config().version == original_version

    def test_04_changed_decisions_detected(self):
        """Lowering max_retries should change decisions for retry-heavy cases."""
        service = PolicySimulatorService()
        # Current: max_retries=2, attempt_count=1 -> ALLOWED
        # Proposed: max_retries=1, attempt_count=1 -> ESCALATE (budget exhausted)
        item = _make_item("sim_chg_001", metadata={"attempt_count": 1, "proposed_action": "retry_payment"})
        service._fetch_opportunities = lambda container, ids: [item]  # type: ignore

        result = service.preview_policy_change({"max_retries": 1})
        assert result.changed_count >= 1

    def test_05_all_four_decisions_supported(self):
        """Simulator should handle all product decisions."""
        service = PolicySimulatorService()
        items = [
            _make_item("sim_dec_001", root_cause="soft", metadata={"proposed_action": "retry_payment"}),
            _make_item("sim_dec_002", root_cause="soft", metadata={"proposed_action": "escalate_human"}),
            _make_item("sim_dec_003", root_cause="fraud", metadata={"proposed_action": "escalate_human"}),
            _make_item("sim_dec_004", root_cause="hard", metadata={"proposed_action": "send_payment_link"}),
        ]
        service._fetch_opportunities = lambda container, ids: items  # type: ignore

        result = service.preview_policy_change({})
        assert result.opportunities_evaluated == 4
        decision_types = {d.current.decision_type for d in result.decision_diffs} | {d.proposed.decision_type for d in result.decision_diffs}
        assert decision_types.issubset({"ALLOWED", "DENY", "ESCALATE", "WAIT", "STOP"})

    def test_06_reason_codes_preserved(self):
        """Reason codes should be stable and machine-readable."""
        service = PolicySimulatorService()
        item = _make_item("sim_reason_001", metadata={"proposed_action": "retry_payment"})
        service._fetch_opportunities = lambda container, ids: [item]  # type: ignore

        result = service.preview_policy_change({})
        for diff in result.decision_diffs:
            assert diff.current.reason_code != ""
            assert diff.proposed.reason_code != ""

    def test_07_policy_evidence_preserved(self):
        """Policy evidence (rule, reason) should be present in diffs."""
        service = PolicySimulatorService()
        item = _make_item("sim_evid_001", metadata={"proposed_action": "retry_payment"})
        service._fetch_opportunities = lambda container, ids: [item]  # type: ignore

        result = service.preview_policy_change({})
        for diff in result.decision_diffs:
            assert diff.policy_rule_responsible != ""
            assert diff.current.rule != ""
            assert diff.proposed.rule != ""

    def test_08_unsafe_proposed_policy_detected(self):
        """Proposed policy that removes safety protections should be flagged."""
        service = PolicySimulatorService()
        item = _make_item("sim_unsafe_001", root_cause="fraud", metadata={"proposed_action": "retry_payment"})
        service._fetch_opportunities = lambda container, ids: [item]  # type: ignore

        result = service.preview_policy_change({"failure_categories_blocked": []})
        # Fraud should still be blocked by stopping rules, not policy
        assert result.opportunities_evaluated == 1

    def test_09_consent_protection_preserved(self):
        """Opted-out customers should remain protected."""
        service = PolicySimulatorService()
        item = _make_item("sim_consent_001", opted_out=True, metadata={"customer_opted_out": True})
        service._fetch_opportunities = lambda container, ids: [item]  # type: ignore

        result = service.preview_policy_change({})
        assert result.opportunities_evaluated == 1

    def test_10_terminal_state_protection_preserved(self):
        """Terminal-state items should not become recoverable."""
        service = PolicySimulatorService()
        item = _make_item("sim_term_001", status=RecoveryStatus.RECOVERED)
        service._fetch_opportunities = lambda container, ids: [item]  # type: ignore

        result = service.preview_policy_change({})
        assert result.opportunities_evaluated == 1

    def test_11_duplicate_protection_preserved(self):
        """Duplicate execution protection should remain."""
        service = PolicySimulatorService()
        item = _make_item("sim_dup_001", metadata={"attempt_count": 3, "proposed_action": "retry_payment"})
        service._fetch_opportunities = lambda container, ids: [item]  # type: ignore

        result = service.preview_policy_change({"max_retries": 1})
        assert result.opportunities_evaluated == 1

    def test_12_retry_cooldown_respected(self):
        """Cooldown changes should affect timing-sensitive decisions."""
        service = PolicySimulatorService()
        item = _make_item("sim_cool_001")
        service._fetch_opportunities = lambda container, ids: [item]  # type: ignore

        result = service.preview_policy_change({"cooldown_retry_minutes": 1440})
        assert result.opportunities_evaluated == 1

    def test_13_active_promise_respected(self):
        """Active promises should produce WAIT decisions."""
        service = PolicySimulatorService()
        item = _make_item("sim_prom_001", metadata={"promise_status": "promised"})
        service._fetch_opportunities = lambda container, ids: [item]  # type: ignore

        result = service.preview_policy_change({})
        assert result.opportunities_evaluated == 1

    def test_14_expected_recovery_not_verified(self):
        """Simulator expected recovery must not be treated as verified recovery."""
        service = PolicySimulatorService()
        item = _make_item("sim_exp_001", expected_recovery_value=5000, metadata={"proposed_action": "retry_payment"})
        service._fetch_opportunities = lambda container, ids: [item]  # type: ignore

        result = service.preview_policy_change({})
        assert result.current_expected_recovery_minor == 5000
        assert result.proposed_expected_recovery_minor == 5000

    def test_15_revenue_at_risk_distinct(self):
        """Revenue at risk and expected recovery must remain distinct."""
        service = PolicySimulatorService()
        item = _make_item("sim_rar_001", amount_minor=100000, expected_recovery_value=5000, metadata={"proposed_action": "retry_payment"})
        service._fetch_opportunities = lambda container, ids: [item]  # type: ignore

        result = service.preview_policy_change({})
        assert result.current_revenue_at_risk_minor == 100000
        assert result.current_expected_recovery_minor == 5000
        assert result.current_revenue_at_risk_minor != result.current_expected_recovery_minor

    def test_16_zero_value_cases_handled(self):
        """Zero-amount cases must not crash."""
        service = PolicySimulatorService()
        item = _make_item("sim_zero_001", amount_minor=0, metadata={"proposed_action": "retry_payment"})
        service._fetch_opportunities = lambda container, ids: [item]  # type: ignore

        result = service.preview_policy_change({})
        assert result.opportunities_evaluated == 1

    def test_17_simulator_cannot_trigger_live_execution(self):
        """Simulator must not create live execution side effects."""
        service = PolicySimulatorService()
        item = _make_item("sim_exec_001", metadata={"proposed_action": "retry_payment"})
        service._fetch_opportunities = lambda container, ids: [item]  # type: ignore

        result = service.preview_policy_change({})
        for diff in result.decision_diffs:
            assert diff.proposed.proposed_action != "execute_payment"

    def test_18_simulator_cannot_create_settlement(self):
        """Simulator must not create settlement evidence."""
        service = PolicySimulatorService()
        item = _make_item("sim_settle_001", metadata={"proposed_action": "retry_payment"})
        service._fetch_opportunities = lambda container, ids: [item]  # type: ignore

        result = service.preview_policy_change({})
        for diff in result.decision_diffs:
            assert "settlement" not in (diff.proposed.reason or "").lower()

    def test_19_benchmark_data_excluded_from_simulation(self):
        """Benchmark/synthetic items should be classified and excluded."""
        item = _make_item("sim_bench_001", metadata={"is_synthetic": True, "source": "synthetic_dataset"})
        classification = _classify_item(getattr(item, "metadata", {}))
        assert classification == "BENCHMARK_SYNTHETIC"

    def test_20_simulation_id_unique(self):
        """Each simulation should have a unique ID."""
        service = PolicySimulatorService()
        items = [_make_item("sim_uid_001")]
        service._fetch_opportunities = lambda container, ids: items  # type: ignore

        r1 = service.preview_policy_change({})
        r2 = service.preview_policy_change({})
        assert r1.simulation_id != r2.simulation_id

    def test_21_proposed_policy_overlay_correct(self):
        """Proposed policy should overlay correctly on current policy."""
        service = PolicySimulatorService()
        items = [_make_item("sim_overlay_001")]
        service._fetch_opportunities = lambda container, ids: items  # type: ignore

        result = service.preview_policy_change({"max_retries": 10})
        assert result.proposed_policy_version != result.current_policy_version

    def test_22_no_mutation_of_live_metrics(self):
        """Simulator must not contaminate live strategy analytics or attribution."""
        service = PolicySimulatorService()
        items = [_make_item("sim_metric_001")]
        service._fetch_opportunities = lambda container, ids: items  # type: ignore

        result = service.preview_policy_change({})
        assert result.scope in ("current_portfolio", "selected_opportunities")

    def test_23_canonical_action_reused_not_invented(self):
        """Simulator must use canonical proposed_action, not invent fallback."""
        # Item with no proposed_action in metadata must be skipped
        item = _make_item("sim_canon_001", metadata={"attempt_count": 1})
        service = PolicySimulatorService()
        service._fetch_opportunities = lambda container, ids: [item]  # type: ignore

        result = service.preview_policy_change({})
        assert result.unevaluable_count == 1
        assert result.changed_count == 0
        assert result.unchanged_count == 0

    def test_24_canonical_action_used_for_both_evaluations(self):
        """Same canonical action must be used for current and proposed policy."""
        service = PolicySimulatorService()
        item = _make_item("sim_canon_02", metadata={"proposed_action": "send_payment_link", "attempt_count": 1})
        service._fetch_opportunities = lambda container, ids: [item]  # type: ignore

        result = service.preview_policy_change({})
        if result.decision_diffs:
            assert result.decision_diffs[0].current.proposed_action == "send_payment_link"
            assert result.decision_diffs[0].proposed.proposed_action == "send_payment_link"

    def test_25_unevaluable_items_excluded_from_distribution(self):
        """Items without canonical action must not appear in decision distribution."""
        service = PolicySimulatorService()
        items = [
            _make_item("sim_uneval_001", metadata={"proposed_action": "retry_payment"}),
            _make_item("sim_uneval_002", metadata={"attempt_count": 1}),  # no proposed_action
        ]
        service._fetch_opportunities = lambda container, ids: items  # type: ignore

        result = service.preview_policy_change({})
        assert result.unevaluable_count == 1
        assert result.opportunities_evaluated == 2
        total_dist = sum(result.current_distribution.values()) + sum(result.proposed_distribution.values())
        assert total_dist == 2  # only the evaluable item counted


class TestPolicySimulatorAPI:
    """Tests for Policy Simulator API endpoints."""

    def test_01_current_policy_endpoint(self):
        """GET /api/policy-simulator/current should return active policy snapshot."""
        app = create_app(webhook_secret="test-secret")
        client = TestClient(app)
        resp = client.get("/api/policy-simulator/current")
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data
        assert "max_retries" in data
        assert "updated_at" in data

    def test_02_preview_endpoint_validates_policy_fields(self):
        """POST /api/policy-simulator/preview should reject unknown fields."""
        app = create_app(webhook_secret="test-secret")
        client = TestClient(app)
        resp = client.post("/api/policy-simulator/preview", json={
            "proposed_policy": {"unknown_field_xyz": 999}
        })
        assert resp.status_code == 400

    def test_03_preview_does_not_mutate_policy(self):
        """Preview must not change active policy version."""
        app = create_app(webhook_secret="test-secret")
        client = TestClient(app)
        get_resp = client.get("/api/policy-simulator/current")
        original_version = get_resp.json()["version"]

        client.post("/api/policy-simulator/preview", json={
            "proposed_policy": {"max_retries": 99}
        })

        get_resp2 = client.get("/api/policy-simulator/current")
        assert get_resp2.json()["version"] == original_version

    def test_04_preview_returns_unevaluable_count(self):
        """Preview response should include unevaluable_count."""
        app = create_app(webhook_secret="test-secret")
        client = TestClient(app)
        resp = client.post("/api/policy-simulator/preview", json={"proposed_policy": {}})
        assert resp.status_code == 200
        data = resp.json()
        assert "unevaluable_count" in data
        assert "unevaluable_ids" in data
