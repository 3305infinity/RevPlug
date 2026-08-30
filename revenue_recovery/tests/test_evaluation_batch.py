import pytest
from app.services.evaluation_service import EvaluationService
from app.domain.failures import FailureCategory

def test_evaluation_reproducibility():
    """Test A/B: Evaluator is 100% reproducible with the same seed."""
    svc1 = EvaluationService()
    res1 = svc1.run_batch_evaluation(count=20, seed=123)
    
    svc2 = EvaluationService()
    res2 = svc2.run_batch_evaluation(count=20, seed=123)
    
    assert res1.recoveros.actual_recovered == res2.recoveros.actual_recovered
    assert res1.baseline.actual_recovered == res2.baseline.actual_recovered
    assert res1.recoveros.stopped_count == res2.recoveros.stopped_count

def test_evaluation_count_bounds():
    """Test bounds on count argument."""
    svc = EvaluationService()
    res_small = svc.run_batch_evaluation(count=-5, seed=1)
    assert res_small.count == 1
    
    res_large = svc.run_batch_evaluation(count=9999, seed=1)
    assert res_large.count == 500

def test_evaluation_mock_agent_safety():
    """Test that RecoverOS (via MockAgent) properly stops on fraud."""
    svc = EvaluationService()
    # Find a dataset with fraud cases
    res = svc.run_batch_evaluation(count=50, seed=42)
    fraud_cases = [c for c in res.per_case if c['original_category'] == 'fraud']
    assert len(fraud_cases) > 0
    
    for case in fraud_cases:
        ros = case['recoveros']
        assert ros['proposed_action'] == 'stop_recovery'
        assert ros['outcome'] == 'stopped'
        assert ros['actual_recovered'] == 0

def test_evaluation_baseline_unnecessary_interventions():
    """Test that the baseline makes unnecessary interventions on fraud cases."""
    svc = EvaluationService()
    res = svc.run_batch_evaluation(count=50, seed=42)
    fraud_cases = [c for c in res.per_case if c['original_category'] == 'fraud']
    assert len(fraud_cases) > 0
    
    for case in fraud_cases:
        bl = case['baseline']
        # Baseline always retries twice
        assert bl['attempts_made'] == 2
        # Since fraud probability is 0.0, outcome is always stopped
        assert bl['outcome'] == 'stopped'
        assert bl['actual_recovered'] == 0
        # It made attempts but recovered nothing -> unnecessary
        assert bl['unnecessary_intervention'] is True
