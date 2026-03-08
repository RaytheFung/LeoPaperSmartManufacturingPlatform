"""
Test that ML predictions are now dynamic and respond to input changes
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from core.ml_predictor import MLPredictor
import numpy as np

def test_dynamic_predictions():
    """Test that predictions change with different inputs"""
    
    print("Testing Dynamic ML Predictions")
    print("=" * 80)
    
    predictor = MLPredictor()
    
    # Test 1: Different maintenance hours should give different results
    print("\n1. Testing different maintenance hours:")
    print("-" * 40)
    
    test_cases = [
        ("Very Recent", 50),
        ("Recent", 300),
        ("Normal", 800),
        ("Overdue", 1500),
        ("Very Overdue", 2500)
    ]
    
    results = []
    for label, hours in test_cases:
        eff, conf = predictor.predict_efficiency(
            machine_id="024-001",
            team_leader="Test Leader",
            material_code="MAT001",
            hours_since_maintenance=hours,
            task_difficulty="中"
        )
        results.append((label, hours, eff, conf))
        print(f"{label:15s} ({hours:4d}h): Efficiency={eff:.2f}, Confidence={conf:.0%}")
    
    # Check that we get different values
    efficiencies = [r[2] for r in results]
    unique_eff = len(set([round(e, 1) for e in efficiencies]))
    
    if unique_eff > 1:
        print("✅ Maintenance hours affect predictions!")
    else:
        print("⚠️  All maintenance hours gave same efficiency")
    
    # Test 2: Different task difficulties
    print("\n2. Testing different task difficulties:")
    print("-" * 40)
    
    difficulties = ["易", "中", "難"]
    diff_results = []
    
    for diff in difficulties:
        eff, conf = predictor.predict_efficiency(
            machine_id="024-001",
            team_leader="Test Leader",
            material_code="MAT001",
            hours_since_maintenance=500,
            task_difficulty=diff
        )
        diff_results.append((diff, eff, conf))
        print(f"Difficulty {diff}: Efficiency={eff:.2f}, Confidence={conf:.0%}")
    
    diff_efficiencies = [r[1] for r in diff_results]
    if len(set([round(e, 1) for e in diff_efficiencies])) > 1:
        print("✅ Task difficulty affects predictions!")
    else:
        print("⚠️  All difficulties gave same efficiency")
    
    # Test 3: Different machines
    print("\n3. Testing different machines:")
    print("-" * 40)
    
    machines = ["024-001", "024-010", "035-002", "166-001"]
    machine_results = []
    
    for machine in machines:
        eff, conf = predictor.predict_efficiency(
            machine_id=machine,
            team_leader="Test Leader",
            material_code="MAT001",
            hours_since_maintenance=500,
            task_difficulty="中"
        )
        machine_results.append((machine, eff, conf))
        print(f"Machine {machine:10s}: Efficiency={eff:.2f}, Confidence={conf:.0%}")
    
    machine_efficiencies = [r[1] for r in machine_results]
    if len(set([round(e, 1) for e in machine_efficiencies])) > 1:
        print("✅ Machine ID affects predictions!")
    else:
        print("⚠️  All machines gave same efficiency")
    
    # Test 4: Different team leaders
    print("\n4. Testing different team leaders:")
    print("-" * 40)
    
    leaders = ["張三", "李四", "王五", "趙六"]
    leader_results = []
    
    for leader in leaders:
        eff, conf = predictor.predict_efficiency(
            machine_id="024-001",
            team_leader=leader,
            material_code="MAT001",
            hours_since_maintenance=500,
            task_difficulty="中"
        )
        leader_results.append((leader, eff, conf))
        print(f"Leader {leader:10s}: Efficiency={eff:.2f}, Confidence={conf:.0%}")
    
    leader_efficiencies = [r[1] for r in leader_results]
    if len(set([round(e, 2) for e in leader_efficiencies])) > 1:
        print("✅ Team leader affects predictions!")
    else:
        print("⚠️  All leaders gave same efficiency")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    # Check overall dynamism
    all_efficiencies = efficiencies + diff_efficiencies + machine_efficiencies + leader_efficiencies
    unique_values = len(set([round(e, 2) for e in all_efficiencies]))
    
    if unique_values >= 5:
        print(f"✅ SUCCESS! Predictions are dynamic ({unique_values} unique values found)")
        print("✅ The ML module now responds to different input parameters!")
    else:
        print(f"⚠️  Limited variation ({unique_values} unique values)")
        print("   The model may need more training data for better predictions")
    
    # Show range of predictions
    print(f"\nPrediction range: {min(all_efficiencies):.2f} - {max(all_efficiencies):.2f} kWh/unit")
    print(f"Average: {np.mean(all_efficiencies):.2f} kWh/unit")
    print(f"Std Dev: {np.std(all_efficiencies):.2f}")

if __name__ == "__main__":
    test_dynamic_predictions()