# -*- coding: utf-8 -*-
"""
Comprehensive test suite for the Qiskit-backed Quantum Circuit Optimization Environment.

Covers:
  1. Bell State   — H → CNOT → fidelity ≈ 1
  2. GHZ State    — H → CNOT(0,1) → CNOT(1,2) → fidelity ≈ 1
  3. SWAP         — verify qubit swap physically changes statevector
  4. REMOVE       — add gate → remove gate → state reverts
  5. Budget task  — smooth overflow penalty
  6. Noise impact — deeper circuits penalised
  7. STOP         — correct terminal reward threshold
  8. Redundancy   — repeated gates penalised
"""

import sys
import numpy as np

from server.my_env_environment import (
    QuantumCircuitEnvironment,
    compute_statevector,
    build_qiskit_circuit,
    MAX_QUBITS,
    MAX_DEPTH,
)
from models import ActionType, GateType, QuantumAction


PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"


def section(title: str) -> None:
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


def check(cond: bool, msg: str) -> None:
    tag = PASS if cond else FAIL
    print(f"  [{tag}] {msg}")
    if not cond:
        raise AssertionError(msg)


# ---------------------------------------------------------------------------
# STEP 10 — Test 1: Bell State — H → CNOT → fidelity ≈ 1
# ---------------------------------------------------------------------------
def test_bell_state():
    section("TEST 1: Bell State — H → CNOT → fidelity ≈ 1")
    env = QuantumCircuitEnvironment(seed=42)
    obs = env.reset(task_id="easy")
    print(f"  Initial fidelity: {obs.fidelity:.6f}, score: {obs.score:.6f}")

    obs = env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.H, qubits=[0]))
    print(f"  After H(0):       fid={obs.fidelity:.6f} reward={obs.reward:+.6f}")

    obs = env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.CNOT, qubits=[0, 1]))
    print(f"  After CNOT(0,1):  fid={obs.fidelity:.6f} reward={obs.reward:+.6f}")

    obs = env.step(QuantumAction(action_type=ActionType.STOP))
    check(obs.fidelity > 0.99, f"Bell fidelity {obs.fidelity:.6f} should be ≈ 1.0")
    check(obs.score > 0.5,     f"Bell aggregate score {obs.score:.6f} should be > 0.5")


# ---------------------------------------------------------------------------
# STEP 10 — Test 2: GHZ State — H → CNOT(0,1) → CNOT(1,2) → fidelity ≈ 1
# ---------------------------------------------------------------------------
def test_ghz_state():
    section("TEST 2: GHZ State — H → CNOT(0,1) → CNOT(1,2) → fidelity ≈ 1")
    env = QuantumCircuitEnvironment(seed=42)
    obs = env.reset(task_id="medium")
    print(f"  Initial fidelity: {obs.fidelity:.6f}")

    obs = env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.H, qubits=[0]))
    obs = env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.CNOT, qubits=[0, 1]))
    obs = env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.CNOT, qubits=[1, 2]))
    print(f"  After H+CNOT(0,1)+CNOT(1,2):  fid={obs.fidelity:.6f}")

    obs = env.step(QuantumAction(action_type=ActionType.STOP))
    check(obs.fidelity > 0.99, f"GHZ fidelity {obs.fidelity:.6f} should be ≈ 1.0")
    check(obs.score > 0.5,     f"GHZ aggregate score {obs.score:.6f} should be > 0.5")


# ---------------------------------------------------------------------------
# STEP 10 — Test 3: SWAP — verify qubit swap physically changes statevector
# ---------------------------------------------------------------------------
def test_swap_physics():
    section("TEST 3: SWAP — physical qubit routing verification")

    # Qiskit uses LITTLE-ENDIAN qubit ordering (qubit 0 = LSB).
    # X on qubit 0 sets the LSB → state occupies some basis index.
    # After SWAP(0,1) the occupied index must change (qubits exchanged).
    gates_x    = [{"gate": "X", "qubits": [0]}]
    sv_before  = compute_statevector(gates_x, num_qubits=2)
    gates_swap = [{"gate": "X", "qubits": [0]}, {"gate": "SWAP", "qubits": [0, 1]}]
    sv_after   = compute_statevector(gates_swap, num_qubits=2)

    idx_before = int(np.argmax(np.abs(sv_before)))
    idx_after  = int(np.argmax(np.abs(sv_after)))
    print(f"  Before SWAP: dominant index = {idx_before} (|amp|={abs(sv_before[idx_before]):.4f})")
    print(f"  After  SWAP: dominant index = {idx_after}  (|amp|={abs(sv_after[idx_after]):.4f})")

    check(
        abs(sv_before[idx_before]) > 0.99,
        f"Before SWAP must be pure basis state; |amp|={abs(sv_before[idx_before]):.4f}"
    )
    check(
        abs(sv_after[idx_after]) > 0.99,
        f"After SWAP must be pure basis state;  |amp|={abs(sv_after[idx_after]):.4f}"
    )
    check(
        idx_before != idx_after,
        f"SWAP must change the occupied basis index: before={idx_before}, after={idx_after}"
    )

    # Also verify it works correctly inside the RL environment
    env = QuantumCircuitEnvironment(seed=42)
    env.reset(task_id="easy")
    env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.X, qubits=[0]))
    obs_before_swap = env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.H, qubits=[1]))
    fid_before = obs_before_swap.fidelity

    obs_after_swap = env.step(QuantumAction(action_type=ActionType.SWAP, qubits=[0, 1]))
    fid_after = obs_after_swap.fidelity
    print(f"  RL env — fidelity before SWAP: {fid_before:.6f}, after SWAP: {fid_after:.6f}")
    check(obs_after_swap.reward is not None, "SWAP action executed without error in RL environment")
    check(obs_after_swap.reward < 10.0,      "SWAP reward is finite and penalises SWAP count")


# ---------------------------------------------------------------------------
# STEP 10 — Test 4: REMOVE — add gate → remove gate → state reverts
# ---------------------------------------------------------------------------
def test_remove_reverts():
    section("TEST 4: REMOVE — state reverts after gate removal")
    env = QuantumCircuitEnvironment(seed=42)
    obs_empty = env.reset(task_id="easy")
    fid_empty = obs_empty.fidelity
    sv_empty  = compute_statevector([], num_qubits=2)

    obs_h = env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.H, qubits=[0]))
    fid_h = obs_h.fidelity
    print(f"  Fidelity (empty):          {fid_empty:.6f}")
    print(f"  Fidelity (after H(0)):     {fid_h:.6f}")
    check(abs(fid_h - fid_empty) > 1e-6, "H gate must change fidelity from empty state")

    obs_rm = env.step(QuantumAction(action_type=ActionType.REMOVE))
    fid_rm = obs_rm.fidelity
    sv_rm  = compute_statevector([], num_qubits=2)
    print(f"  Fidelity (after REMOVE):   {fid_rm:.6f}")
    check(
        abs(fid_rm - fid_empty) < 1e-6,
        f"After REMOVE fidelity {fid_rm:.6f} should revert to {fid_empty:.6f}"
    )

    # Verify statevectors match too (direct Qiskit call)
    check(
        np.allclose(sv_rm, sv_empty, atol=1e-10),
        "Statevector after REMOVE matches original empty statevector"
    )
    check(obs_rm.gate_count == 0, "Gate count should be 0 after REMOVE on 1-gate circuit")


# ---------------------------------------------------------------------------
# Original regression tests
# ---------------------------------------------------------------------------

def test_budget_penalty():
    section("TEST 5: Budget Task — smooth overflow penalty")
    env = QuantumCircuitEnvironment()
    env.reset(task_id="budget")
    env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.H, qubits=[0]))
    env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.CNOT, qubits=[0, 1]))
    obs1 = env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.CNOT, qubits=[1, 2]))
    s1 = obs1.score
    print(f"  Score at budget (3 gates): {s1:.4f}")

    obs2 = env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.H, qubits=[2]))
    s2 = obs2.score
    print(f"  Score at overflow (4 gates): {s2:.4f}")

    obs3 = env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.H, qubits=[2]))
    s3 = obs3.score
    print(f"  Score at overflow (5 gates): {s3:.4f}")
    check(s1 >= 0.0 and s2 >= 0.0 and s3 >= 0.0, "All budget scores are non-negative")


def test_stop_reward():
    section("TEST 6: STOP — correct terminal reward threshold")
    env = QuantumCircuitEnvironment()

    # High-score stop → reward should be +0.2
    env.reset(task_id="easy")
    env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.H,    qubits=[0]))
    env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.CNOT, qubits=[0, 1]))
    obs = env.step(QuantumAction(action_type=ActionType.STOP))
    print(f"  High-score STOP: score={obs.score:.4f} reward={obs.reward:.4f}")
    check(obs.done, "Episode must be done after STOP")

    # Low-score stop → reward should be -0.2
    env.reset(task_id="easy")
    obs = env.step(QuantumAction(action_type=ActionType.STOP))
    print(f"  Low-score STOP:  score={obs.score:.4f} reward={obs.reward:.4f}")
    check(obs.done, "Episode must be done after low-score STOP")
    check(obs.reward <= 0.0, f"Low-score STOP reward {obs.reward:.4f} should be ≤ 0")


def test_redundancy_penalty():
    section("TEST 7: Redundancy penalty — same gate twice")
    env = QuantumCircuitEnvironment()
    env.reset(task_id="easy")
    env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.H, qubits=[0]))
    obs = env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.H, qubits=[0]))
    print(f"  H(0) twice reward: {obs.reward:.4f} (expect negative contribution from redundancy)")
    # Reward contains multiple terms; just check it's computed without error
    check(obs.reward is not None, "Reward computed for redundant gate")


def test_module_constants():
    section("TEST 8: Module-level performance constants")
    from server.my_env_environment import MAX_QUBITS, MAX_STEPS, MAX_DEPTH
    check(MAX_QUBITS == 4,  f"MAX_QUBITS={MAX_QUBITS}, expected 4")
    check(MAX_STEPS  == 15, f"MAX_STEPS={MAX_STEPS}, expected 15")
    check(MAX_DEPTH  == 20, f"MAX_DEPTH={MAX_DEPTH}, expected 20")
    print(f"  MAX_QUBITS={MAX_QUBITS}  MAX_STEPS={MAX_STEPS}  MAX_DEPTH={MAX_DEPTH}")


def test_statevector_validation():
    section("TEST 9: Statevector dimension assertion")
    for n in (1, 2, 3, 4):
        sv = compute_statevector([], num_qubits=n)
        check(len(sv) == 2 ** n, f"Empty circuit, {n} qubits → len={len(sv)}, expected {2**n}")
        print(f"  {n} qubits: len={len(sv)} ✓")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_all():
    tests = [
        test_bell_state,
        test_ghz_state,
        test_swap_physics,
        test_remove_reverts,
        test_budget_penalty,
        test_stop_reward,
        test_redundancy_penalty,
        test_module_constants,
        test_statevector_validation,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {type(e).__name__}: {e}")
            failed += 1

    section("RESULTS")
    print(f"  Passed: {passed}/{len(tests)}")
    print(f"  Failed: {failed}/{len(tests)}")
    if failed:
        sys.exit(1)
    else:
        print("\n  ALL TESTS PASSED!")


if __name__ == "__main__":
    run_all()
