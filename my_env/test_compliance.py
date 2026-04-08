#!/usr/bin/env python3
"""
OpenEnv Compliance Test Script
Tests all requirements for HF Space deployment:
1. Reset endpoint availability
2. Step/state endpoints
3. All tasks enumerable
4. All graders produce scores in [0, 1]
5. Reward in valid range
"""

import sys
import json
from server.my_env_environment import QuantumCircuitEnvironment
from models import ActionType, GateType, QuantumAction

def test_reset_endpoint():
    """Test reset endpoint with all tasks."""
    print("=" * 60)
    print("TEST 1: Reset Endpoint")
    print("=" * 60)
    
    env = QuantumCircuitEnvironment(seed=42)
    tasks = ["easy", "medium", "hard", "efficient", "noisy", "budget", "approx"]
    
    for task_id in tasks:
        try:
            obs = env.reset(config={"task_id": task_id})
            assert obs is not None, f"Reset returned None for task {task_id}"
            assert obs.task_id == task_id, f"Task ID mismatch: {obs.task_id} != {task_id}"
            assert 0.0 <= obs.score <= 1.0, f"Score out of range: {obs.score}"
            print(f"  ✓ Task '{task_id}': reset OK, score={obs.score:.4f}")
        except Exception as e:
            print(f"  ✗ Task '{task_id}': FAILED - {e}")
            return False
    
    print("  ✓ All tasks reset successfully\n")
    return True

def test_step_endpoint():
    """Test step endpoint."""
    print("=" * 60)
    print("TEST 2: Step Endpoint")
    print("=" * 60)
    
    env = QuantumCircuitEnvironment(seed=42)
    obs = env.reset(config={"task_id": "easy"})
    
    # Test ADD action
    action = QuantumAction(action_type=ActionType.ADD, gate=GateType.H, qubits=[0])
    obs = env.step(action)
    assert obs is not None, "Step returned None"
    assert hasattr(obs, 'reward'), "Observation missing reward"
    assert hasattr(obs, 'done'), "Observation missing done"
    print(f"  ✓ ADD action: reward={obs.reward:.4f}, done={obs.done}")
    
    # Test REMOVE action
    action = QuantumAction(action_type=ActionType.REMOVE)
    obs = env.step(action)
    print(f"  ✓ REMOVE action: reward={obs.reward:.4f}, done={obs.done}")
    
    # Test STOP action
    action = QuantumAction(action_type=ActionType.STOP)
    obs = env.step(action)
    assert obs.done == True, "STOP should set done=True"
    print(f"  ✓ STOP action: reward={obs.reward:.4f}, done={obs.done}\n")
    
    return True

def test_state_endpoint():
    """Test state property."""
    print("=" * 60)
    print("TEST 3: State Endpoint")
    print("=" * 60)
    
    env = QuantumCircuitEnvironment(seed=42)
    obs = env.reset(config={"task_id": "easy"})
    
    state = env.state
    assert state is not None, "State returned None"
    assert hasattr(state, 'episode_id'), "State missing episode_id"
    assert hasattr(state, 'step_count'), "State missing step_count"
    assert hasattr(state, 'circuit_gates'), "State missing circuit_gates"
    print(f"  ✓ State accessible: episode_id={state.episode_id[:8]}..., steps={state.step_count}")
    print(f"  ✓ State fields: {list(state.__dict__.keys())}\n")
    
    return True

def test_all_tasks_with_graders():
    """Test all tasks and verify grader scores."""
    print("=" * 60)
    print("TEST 4: All Tasks + Graders (3+ tasks)")
    print("=" * 60)
    
    env = QuantumCircuitEnvironment(seed=42)
    tasks = ["easy", "medium", "hard", "efficient", "noisy", "budget", "approx"]
    
    print(f"  Total tasks: {len(tasks)}")
    assert len(tasks) >= 3, f"Need at least 3 tasks, found {len(tasks)}"
    
    for task_id in tasks:
        obs = env.reset(config={"task_id": task_id})
        
        # Check initial scores
        assert 0.0 <= obs.score <= 1.0, f"Score out of range: {obs.score}"
        assert 0.0 <= obs.fidelity <= 1.0, f"Fidelity out of range: {obs.fidelity}"
        
        # Take a step
        action = QuantumAction(action_type=ActionType.ADD, gate=GateType.H, qubits=[0])
        obs = env.step(action)
        
        # Verify all scores in valid range
        assert 0.0 <= obs.score <= 1.0, f"Score out of range after step: {obs.score}"
        assert 0.0 <= obs.fidelity <= 1.0, f"Fidelity out of range: {obs.fidelity}"
        
        # Check metadata scores
        if obs.metadata:
            for key, value in obs.metadata.items():
                if key.endswith('_score') and isinstance(value, (int, float)):
                    assert 0.0 <= value <= 1.0, f"{key} out of range: {value}"
        
        print(f"  ✓ Task '{task_id}': fid={obs.fidelity:.4f}, score={obs.score:.4f}, reward={obs.reward:.4f}")
    
    print(f"  ✓ All {len(tasks)} tasks passed grader validation\n")
    return True

def test_reward_range():
    """Test that rewards are in valid range."""
    print("=" * 60)
    print("TEST 5: Reward Range")
    print("=" * 60)
    
    env = QuantumCircuitEnvironment(seed=42)
    obs = env.reset(config={"task_id": "easy"})
    
    rewards = []
    for i in range(10):
        if obs.done:
            break
        action = QuantumAction(action_type=ActionType.ADD, gate=GateType.H, qubits=[i % 2])
        obs = env.step(action)
        rewards.append(obs.reward)
    
    for i, r in enumerate(rewards):
        # Rewards should be reasonable (typically -1 to 1)
        assert -2.0 <= r <= 2.0, f"Reward {i} out of reasonable range: {r}"
        print(f"  Step {i+1}: reward={r:+.4f}")
    
    print(f"  ✓ All rewards in valid range\n")
    return True

def test_openenv_yaml():
    """Test openenv.yaml compliance."""
    print("=" * 60)
    print("TEST 6: openenv.yaml Compliance")
    print("=" * 60)
    
    import yaml
    with open("openenv.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    required_fields = ["spec_version", "name", "type", "runtime", "app", "port", "tasks"]
    for field in required_fields:
        assert field in config, f"Missing required field: {field}"
        print(f"  ✓ {field}: {config[field]}")
    
    # Check tasks
    assert len(config["tasks"]) >= 3, f"Need at least 3 tasks in openenv.yaml"
    print(f"  ✓ Tasks defined: {len(config['tasks'])}")
    
    # Check schemas
    assert "action_schema" in config, "Missing action_schema"
    assert "observation_schema" in config, "Missing observation_schema"
    print(f"  ✓ Schemas defined\n")
    
    return True

def main():
    """Run all compliance tests."""
    print("\n" + "=" * 60)
    print("OPENENV COMPLIANCE TEST SUITE")
    print("=" * 60 + "\n")
    
    tests = [
        ("Reset Endpoint", test_reset_endpoint),
        ("Step Endpoint", test_step_endpoint),
        ("State Endpoint", test_state_endpoint),
        ("Tasks + Graders", test_all_tasks_with_graders),
        ("Reward Range", test_reward_range),
        ("openenv.yaml", test_openenv_yaml),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"  ✗ {name} FAILED: {e}\n")
            results.append((name, False))
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL COMPLIANCE TESTS PASSED!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
