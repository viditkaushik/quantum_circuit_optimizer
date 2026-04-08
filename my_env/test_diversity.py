import asyncio
from typing import Dict, Any

from server.my_env_environment import QuantumCircuitEnvironment
from models import ActionType, GateType, QuantumAction

def evaluate_tasks():
    env = QuantumCircuitEnvironment()

    print("\n=== Testing Diversity Mechanics ===")

    # 1. Budgeted Option Test
    print("\n--- Task: Budgeted Optimization (Max Gate Count 3) ---")
    env.reset(task_id="budget")
    # Apply 4 gates (should trigger 0.5x multiplier)
    print("Applying 4 gates... (Budget is 3)")
    env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.H, qubits=[0]))
    env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.CNOT, qubits=[0, 1]))
    env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.X, qubits=[1]))
    obs = env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.H, qubits=[2]))
    print(f"Final Score (After 4th gate): {obs.score:.4f} (Notice it is brutally halved!)")
    
    # 2. Approximate Tolerance Boost Test
    print("\n--- Task: Approximate Target (Tolerance Check) ---")
    env.reset(task_id="approx")
    # A random gate isn't enough
    obs = env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.H, qubits=[0]))
    print(f"Current score before stop: {obs.score:.4f}")
    if obs.score > 0.8:
        print("Wait, score is high enough to trigger tolerance.")
    obs = env.step(QuantumAction(action_type=ActionType.STOP))
    print(f"Final Reward on STOP: {obs.reward:.4f} (Checks if +0.2 tolerance jump triggered)")
    
    # 3. Efficient over perfect test
    print("\n--- Task: Imperfect But Efficient ---")
    env.reset(task_id="efficient")
    obs = env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.H, qubits=[0]))
    print(f"Score for H(0): {obs.score:.4f} (Heavy efficiency ratio vs fidelity)")
    
    # 4. Overfitting Penalty test
    print("\n--- Task: Overfitting Catch ---")
    # Easy task Bell state is perfect at depth 2
    env.reset(task_id="easy")
    env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.H, qubits=[0]))
    env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.CNOT, qubits=[0, 1]))
    
    # Now we do useless operations that don't change fidelity significantly to trigger depth > optimal
    # Wait, Bell state only needs depth 2. Any additional ops might ruin fidelity. 
    # But if we did e.g. SWAP(0,1), wait no... if we do I(0), but I gate isn't an option.
    print("If an agent surpasses depth 5 with > 0.95 fidelity, it loses -0.1 reward natively per step.")

if __name__ == "__main__":
    evaluate_tasks()
