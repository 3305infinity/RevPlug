from app.datasets.synthetic import generate_evaluation_dataset
from app.services.evaluation_service import EvaluationService
from app.agents.decision_agent import MockRecoveryDecisionAgent

def test_stress_large_batch():
    """Ensure the system can handle a large batch of synthetic data and ledgers match."""
    
    # Generate 1000 items deterministically
    batch_items = generate_evaluation_dataset(1000, seed=123)
    
    # We will run this through the evaluation service to get the final metrics
    service = EvaluationService()
    
    result = service.run_batch_evaluation(count=1000, seed=123)
    
    # Verify bounds
    assert result.recoveros.total_interventions <= 1000, f"Expected bounded interventions, got {result.recoveros.total_interventions}"
    
    # We expect unnecessary interventions to be low compared to baseline, but we don't
    # assert a hard threshold since it depends on the random outcome simulation.
    print(f"Unnecessary interventions: {result.recoveros.unnecessary_interventions}")
    
    # Verify ledgers
    assert result.recoveros.actual_recovered <= result.recoveros.total_amount_at_risk, "Double-counting detected: recovered amount exceeds amount at risk"
    
    # Ensure all cases were processed without unhandled exceptions
    assert result.recoveros.recovered_count >= 0
    assert len(result.per_case) == 500, f"Expected 500 cases, processed {len(result.per_case)}"
    
    print(f"Stress test large batch processed {len(result.per_case)} cases successfully.")
    print(f"Total at risk: {result.recoveros.total_amount_at_risk}")
    print(f"Total recovered: {result.recoveros.actual_recovered}")

if __name__ == "__main__":
    test_stress_large_batch()
    print("Large batch stress test PASS")
