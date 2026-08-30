from app.services.evaluation_service import EvaluationService
import json

def run_live_eval():
    print("==========================================")
    print("STEP 1 - REAL BATCH EVALUATION + BASELINE")
    print("==========================================")
    print("Starting evaluation of 50 synthetic recovery cases...")
    
    service = EvaluationService()
    result = service.run_batch_evaluation(count=50, seed=31337)
    
    print("\n--- RESULTS ---")
    print(f"Total Cases: {result.dataset_info['count']}")
    print(f"Total Amount at Risk: Rs. {result.revplug.total_amount_at_risk/100:,.2f}\n")
    
    print("[ BASELINE (Dumb Fixed-Strategy) ]")
    print(f"Recovery Rate: {result.baseline.recovery_rate * 100:.2f}%")
    print(f"Actual Recovered: Rs. {result.baseline.actual_recovered/100:,.2f}")
    print(f"Intervention Cost: Rs. {result.baseline.intervention_cost/100:,.2f}\n")
    
    print("[ REVPLUG (Intelligent Orchestrator) ]")
    print(f"Recovery Rate: {result.revplug.recovery_rate * 100:.2f}%")
    print(f"Actual Recovered: Rs. {result.revplug.actual_recovered/100:,.2f}")
    print(f"Intervention Cost: Rs. {result.revplug.intervention_cost/100:,.2f}")
    print(f"Unnecessary Interventions: {result.revplug.unnecessary_interventions}\n")
    
    print("[ COMPARISON ]")
    print(result.comparison.honest_summary.replace("₹", "Rs. "))
    if result.comparison.relative_improvement:
        print(f"Relative Improvement: +{result.comparison.relative_improvement * 100:.2f}%")
    
    print("\n==========================================")
    print("EVALUATION COMPLETE")
    print("==========================================")

if __name__ == "__main__":
    run_live_eval()
