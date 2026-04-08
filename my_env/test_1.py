import asyncio
from my_env import QuantumCircuitEnv, QuantumAction, ActionType, GateType

async def test():
    # Connect to your running server
    async with QuantumCircuitEnv(base_url="http://localhost:8000") as env:
        # 1. Reset to Easy task (Bell State)
        result = await env.reset()
        print(f"Target: {result.observation.target_description}")
        print(f"Initial Fidelity: {result.observation.fidelity:.4f}")

        # 2. Add a Hadamard gate
        action = QuantumAction(action_type=ActionType.ADD, gate=GateType.H, qubits=[0])
        result = await env.step(action)
        print(f"Step 1 (H): Fidelity={result.observation.fidelity:.4f}, Reward={result.reward:.4f}")

        # 3. Add a CNOT gate
        action = QuantumAction(action_type=ActionType.ADD, gate=GateType.CNOT, qubits=[0, 1])
        result = await env.step(action)
        print(f"Step 2 (CNOT): Fidelity={result.observation.fidelity:.4f}, Reward={result.reward:.4f}")

        # 4. Stop
        result = await env.step(QuantumAction(action_type=ActionType.STOP))
        print(f"Final Score: {result.observation.score:.4f}")

if __name__ == "__main__":
    asyncio.run(test())
