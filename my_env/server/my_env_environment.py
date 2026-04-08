# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Quantum Circuit Optimization Environment Implementation.

A noise-aware, hardware-constrained reinforcement learning environment
for quantum circuit design and optimization.

Physics backend: Qiskit Statevector (stateless — no Aer, no noise models).
RL logic:        Pure Python / NumPy (unchanged from original design).

Design principle:
    Environment = decision + RL logic
    Qiskit      = stateless physics engine
"""

# ---------------------------------------------------------------------------
# sys.path bootstrap -- makes `python server/my_env_environment.py` work
# when run directly from the my_env/ root directory.
# ---------------------------------------------------------------------------
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))   # .../my_env/server/
_ROOT = os.path.dirname(_HERE)                        # .../my_env/
for _p in (_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import logging
import math
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)

import numpy as np

# ---------------------------------------------------------------------------
# STEP 1: Qiskit lightweight imports (statevector only — NO Aer)
# ---------------------------------------------------------------------------
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from openenv.core.env_server.interfaces import Environment

# Try relative imports first (package mode -- same class identity as app.py).
# Fall back to absolute imports (direct execution mode).
try:
    from ..models import ActionType, GateType, QuantumAction, QuantumObservation, QuantumState
    from ..graders import (
        AggregateGrader,
        ConstraintsGrader,
        EfficiencyGrader,
        FidelityGrader,
        NoiseGrader,
        UnitaryGrader,
    )
except ImportError:
    from models import ActionType, GateType, QuantumAction, QuantumObservation, QuantumState
    from graders import (
        AggregateGrader,
        ConstraintsGrader,
        EfficiencyGrader,
        FidelityGrader,
        NoiseGrader,
        UnitaryGrader,
    )

try:
    from .tasks import TASK_REGISTRY
except ImportError:
    from tasks import TASK_REGISTRY


# ---------------------------------------------------------------------------
# STEP 8: Performance constraints (critical)
# ---------------------------------------------------------------------------
MAX_QUBITS: int = 4    # Maximum qubits supported
MAX_STEPS: int  = 15   # Soft cap per spec; per-task configs retain their limits
MAX_DEPTH: int  = 20   # Maximum circuit depth before penalty


# ---------------------------------------------------------------------------
# STEP 2: Circuit converter  (Qiskit — stateless)
# ---------------------------------------------------------------------------

def build_qiskit_circuit(circuit_gates: List[Dict[str, Any]], num_qubits: int) -> QuantumCircuit:
    """
    Convert a list of gate dicts into a Qiskit QuantumCircuit.

    Supports: H, X, CNOT, SWAP, RX, RZ.
    All other gate names are silently skipped.

    Args:
        circuit_gates: List of dicts with keys ``gate``, ``qubits``, ``parameter``.
        num_qubits:    Number of qubits in the circuit.

    Returns:
        A Qiskit :class:`QuantumCircuit` with the gates applied in order.
    """
    qc = QuantumCircuit(num_qubits)

    for g in circuit_gates:
        name = g["gate"]
        q    = g["qubits"]
        p    = g.get("parameter")

        if name == "H":
            qc.h(q[0])
        elif name == "X":
            qc.x(q[0])
        elif name == "CNOT":
            qc.cx(q[0], q[1])
        elif name == "SWAP":
            # STEP 4: Real physics SWAP — used for qubit routing on
            # limited-connectivity hardware (e.g. q0—q1—q2 topology).
            qc.swap(q[0], q[1])
        elif name == "RX":
            qc.rx(float(p) if p is not None else 0.0, q[0])
        elif name == "RZ":
            qc.rz(float(p) if p is not None else 0.0, q[0])
        # Unknown gates are intentionally skipped (graceful degradation)

    return qc


# ---------------------------------------------------------------------------
# STEP 3: Statevector computation (replaces all old NumPy simulator logic)
# ---------------------------------------------------------------------------

def compute_statevector(circuit_gates: List[Dict[str, Any]], num_qubits: int) -> np.ndarray:
    """
    Compute the statevector of a circuit using Qiskit.

    Starts from the |00...0> ground state (Qiskit default).
    Does NOT store any Qiskit objects — returns a plain NumPy complex128 array.

    Args:
        circuit_gates: Gate list as produced by the environment's _gates field.
        num_qubits:    Number of qubits.

    Returns:
        Complex NumPy array of shape (2**num_qubits,).
    """
    if not circuit_gates:
        # Empty circuit → |00...0>
        sv = np.zeros(2 ** num_qubits, dtype=np.complex128)
        sv[0] = 1.0
        return sv

    qc = build_qiskit_circuit(circuit_gates, num_qubits)
    sv = np.asarray(Statevector.from_instruction(qc).data, dtype=np.complex128)

    # Normalize explicitly to handle Qiskit precision quirks
    norm = np.linalg.norm(sv)
    if norm > 0:
        sv = sv / norm

    # STEP 9: Validation
    assert len(sv) == 2 ** num_qubits, (
        f"Statevector length {len(sv)} != 2^{num_qubits}={2**num_qubits}"
    )
    return sv


# ---------------------------------------------------------------------------
# Circuit Depth Calculator (pure Python — no Qiskit dependency)
# ---------------------------------------------------------------------------

def compute_circuit_depth(gates: List[Dict[str, Any]], num_qubits: int) -> int:
    """
    Compute circuit depth (longest path through any qubit).

    Each gate occupies one time-step on each of its qubits.
    Depth = max over all qubits of the number of gate layers touching that qubit.
    """
    if not gates:
        return 0

    qubit_depths = [0] * num_qubits
    for gate_info in gates:
        qubits = gate_info["qubits"]
        if len(qubits) == 1:
            qubit_depths[qubits[0]] += 1
        elif len(qubits) >= 2:
            # Multi-qubit gate: all involved qubits advance to the max + 1
            max_d = max(qubit_depths[q] for q in qubits)
            for q in qubits:
                qubit_depths[q] = max_d + 1

    return max(qubit_depths) if qubit_depths else 0


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

class QuantumCircuitEnvironment(Environment):
    """
    RL environment for noise-aware, hardware-constrained quantum circuit optimization.

    The agent builds a quantum circuit step by step to match a target quantum state
    while minimising depth, gate count, noise impact, and SWAP overhead.

    Physics backend: Qiskit Statevector (stateless — called per step, not stored).
    Supports concurrent WebSocket sessions.
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self, seed: Optional[int] = None):
        """
        Initialise the environment.

        Args:
            seed: Optional RNG seed for reproducibility.
        """
        self._seed = seed or 42
        self._rng = np.random.RandomState(self._seed)

        # Task config -- set on reset()
        self._task_id: str = "easy"
        self._task_config: Dict[str, Any] = {}
        self._target_sv: Optional[np.ndarray] = None
        self._target_unitary: Optional[np.ndarray] = None

        # Circuit state (plain Python dicts — NO Qiskit objects stored)
        self._gates: List[Dict[str, Any]] = []
        self._num_qubits: int = 2

        # Episode tracking
        self._step_count: int = 0
        self._max_steps: int = 20
        self._done: bool = False
        self._prev_score: float = 0.0
        self._prev_fidelity: float = 0.0
        self._prev_depth: int = 0
        self._prev_action: Optional[ActionType] = None
        self._last_reward: float = 0.0
        self._episode_id: str = str(uuid4())
        self._swap_count: int = 0
        self._prev_penalty: float = 0.0

        # Graders
        self._aggregate_grader = AggregateGrader()

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def reset(self, config: Optional[Dict] = None) -> QuantumObservation:
        """
        Reset the environment for a new episode.

        Args:
            config:  Optional configuration dictionary containing task_id.

        Returns:
            Initial QuantumObservation.
        """
        # Resolve task_id from config
        task_id = config.get("task_id", "easy") if config else "easy"

        # Load task
        task_cls = TASK_REGISTRY.get(task_id, TASK_REGISTRY["easy"])
        self._task_config = task_cls.config()
        self._task_id = self._task_config["task_id"]
        self._num_qubits = min(self._task_config["num_qubits"], MAX_QUBITS)
        self._max_steps = self._task_config["max_steps"]

        # Enforce MAX_QUBITS constraint
        if self._task_config["num_qubits"] > MAX_QUBITS:
            logger.warning(
                "Task '%s' requests %d qubits; clamped to MAX_QUBITS=%d.",
                self._task_id, self._task_config["num_qubits"], MAX_QUBITS,
            )

        # Check if task uses statevector or unitary targets
        if hasattr(task_cls, "target_unitary"):
            self._target_unitary = task_cls.target_unitary()
            self._target_sv = None
            logger.info("Loaded task '%s' (%d qubits) with UNITARY target.", self._task_id, self._num_qubits)
        else:
            self._target_sv = task_cls.target_statevector()
            self._target_unitary = None
            logger.info("Loaded task '%s' (%d qubits) with STATEVECTOR target.", self._task_id, self._num_qubits)

        # Set grader weights for this task
        weights = self._task_config.get("grader_weights")
        if weights:
            self._aggregate_grader = AggregateGrader(weights=weights)

        # Reset circuit and episode state
        self._gates = []
        self._step_count = 0
        self._done = False
        self._prev_action = None
        self._last_reward = 0.0
        self._episode_id = str(uuid4())
        self._swap_count = 0

        # Compute initial baseline score so the first step evaluates relatively
        initial_scores = self._compute_all_scores()
        self._prev_score = initial_scores["aggregate"]
        self._prev_fidelity = initial_scores["fidelity"]
        self._prev_depth = initial_scores["depth"]
        self._prev_penalty = (
            0.5 * (1.0 - initial_scores["efficiency"]) +
            0.3 * (1.0 - initial_scores["noise"]) +
            0.2 * (1.0 - initial_scores["constraints"])
        )

        return self._build_observation(reward=0.0)

    def step(self, action: QuantumAction) -> QuantumObservation:  # type: ignore[override]
        """
        Execute one step in the environment.

        STEP 6: Each step:
          1. Applies action to circuit_gates
          2. Computes statevector via Qiskit
          3. Computes reward from state
          4. Returns updated observation

        Args:
            action: QuantumAction specifying the gate operation.

        Returns:
            QuantumObservation with updated metrics and shaped reward.
        """
        if self._done:
            return self._build_observation(reward=0.0)

        self._step_count += 1

        # Handle STOP action
        if action.action_type == ActionType.STOP:
            self._done = True
            reward = self._compute_terminal_reward()

            if self._prev_score > 0.8:
                reward += 0.2
            else:
                reward -= 0.2
            
            # Clamp reward
            reward = max(-1.0, min(1.0, reward))

            logger.info(
                "[STOP] task=%s qubits=%d step=%d reward=%.4f",
                self._task_id, self._num_qubits, self._step_count, reward,
            )
            return self._build_observation(reward=reward)

        # Validate action
        valid, penalty_msg = self._validate_action(action)
        if not valid:
            self._check_done()
            logger.info("[INVALID] task=%s step=%d error=%s", self._task_id, self._step_count, penalty_msg)
            return self._build_observation(reward=-0.1, error=penalty_msg)

        # Capture pre-action state for REMOVE bonus/penalty logic
        pre_action_fidelity = self._prev_fidelity
        pre_action_depth    = self._prev_depth

        # Apply action to circuit_gates
        # STEP 5 (REMOVE): pops last gate; state is recomputed from scratch by Qiskit
        self._apply_action(action)

        # Compute scores (triggers compute_statevector → Qiskit)
        scores = self._compute_all_scores()
        current_score   = scores["aggregate"]
        current_fidelity = scores["fidelity"]
        current_depth   = scores["depth"]

        # ------------------------------------------------------------------
        # STEP 7: Reward function (physically meaningful)
        # ------------------------------------------------------------------

        # --- Penalty computation ---
        current_penalty = (
            0.5 * (1.0 - scores["efficiency"]) +
            0.3 * (1.0 - scores["noise"]) +
            0.2 * (1.0 - scores["constraints"])
        )

        # Redundancy penalty
        if len(self._gates) >= 2:
            prev_gate = self._gates[-2]
            curr_gate = self._gates[-1]
            if prev_gate.get("gate") == curr_gate.get("gate") and prev_gate.get("qubits") == curr_gate.get("qubits"):
                current_penalty += 0.005

        # PARAM penalty
        if action.action_type == ActionType.PARAM:
            current_penalty += 0.003

        # SWAP penalty
        if action.action_type == ActionType.SWAP:
            current_penalty += 0.02

        # --- Reward core ---
        fidelity_delta = current_fidelity - self._prev_fidelity
        penalty_delta = current_penalty - getattr(self, '_prev_penalty', 0.0)

        reward = fidelity_delta * 3.0 - penalty_delta * 0.5

        # --- ADD vs REMOVE balance: reward constructive actions ---
        if action.action_type == ActionType.ADD and fidelity_delta < 0:
            reward += 0.15  # Increased from 0.1 to reduce ADD penalty

        # --- REMOVE logic: NOT profitable ---
        if action.action_type == ActionType.REMOVE:
            # Cap REMOVE reward - it can never profit more than half of last reward
            if self._last_reward != 0:
                reward = min(reward, abs(self._last_reward) * 0.5)
            
            # Small optimization bonus only if depth improved without fidelity loss
            if current_depth < pre_action_depth and abs(current_fidelity - pre_action_fidelity) < 1e-6:
                reward = min(reward + 0.005, 0.01)  # Tiny bonus, capped at 0.01
            elif current_fidelity < pre_action_fidelity:
                reward -= 0.05  # Stronger penalty for fidelity loss

        # --- Penalize ADD→REMOVE loops (direct exploit killer) ---
        if action.action_type == ActionType.REMOVE and self._prev_action == ActionType.ADD:
            reward -= 0.05

        # --- Prevent REMOVE spam loops ---
        if self._prev_action == ActionType.REMOVE:
            reward -= 0.02

        # --- Exploration bias ---
        reward += 0.02

        # --- Overfitting penalty ---
        optimal_depth = self._task_config.get("optimal_depth", 5)
        if current_fidelity > 0.95 and current_depth > optimal_depth:
            reward -= 0.1

        # --- Smooth ---
        reward = np.tanh(reward)

        # Update trackers
        self._prev_action = action.action_type
        self._last_reward = reward

        # Episode limit
        if self._step_count >= self._max_steps:
            self._done = True
            reward -= 0.1
            reward = max(-1.0, min(1.0, reward))

        # Update trackers
        self._prev_score    = current_score
        self._prev_fidelity = current_fidelity
        self._prev_depth    = current_depth
        self._prev_penalty  = current_penalty

        logger.info(
            "[STEP] task=%s qubits=%d step=%d | "
            "fid=%.4f eff=%.4f noise=%.4f cstr=%.4f agg=%.4f | "
            "depth=%d gates=%d swaps=%d reward=%.4f",
            self._task_id, self._num_qubits, self._step_count,
            scores["fidelity"], scores["efficiency"],
            scores["noise"], scores["constraints"], scores["aggregate"],
            current_depth, scores["gate_count"], self._swap_count, reward,
        )

        self._check_done()
        return self._build_observation(reward=reward)

    @property
    def state(self) -> QuantumState:
        """Return the full internal state."""
        scores = self._compute_all_scores()
        return QuantumState(
            episode_id=self._episode_id,
            step_count=self._step_count,
            circuit_gates=list(self._gates),
            target_description=self._task_config.get("description", ""),
            task_id=self._task_id,
            max_steps=self._max_steps,
            noise_model_name=self._task_config.get("noise_model", "none"),
            current_fidelity=scores.get("fidelity", 0.0),
            current_score=scores.get("aggregate", 0.0),
        )

    # ------------------------------------------------------------------
    # Action validation
    # ------------------------------------------------------------------

    def _validate_action(self, action: QuantumAction) -> Tuple[bool, Optional[str]]:
        """Validate that the action is legal."""
        at = action.action_type

        if at == ActionType.ADD:
            if action.gate is None:
                return False, "ADD action requires a gate type"
            if not action.qubits:
                return False, "ADD action requires target qubits"
            for q in action.qubits:
                if q < 0 or q >= self._num_qubits:
                    return False, f"Qubit index {q} out of range [0, {self._num_qubits - 1}]"
            if action.gate == GateType.CNOT and len(action.qubits) != 2:
                return False, "CNOT requires exactly 2 qubits"
            if action.gate in (GateType.H, GateType.X, GateType.RX, GateType.RZ):
                if len(action.qubits) != 1:
                    return False, f"{action.gate.value} requires exactly 1 qubit"
            if action.gate in (GateType.RX, GateType.RZ) and action.parameter is None:
                return False, f"{action.gate.value} requires a parameter (angle)"

        elif at == ActionType.REMOVE:
            if not self._gates:
                return False, "Cannot REMOVE from an empty circuit"

        elif at == ActionType.SWAP:
            if len(action.qubits) != 2:
                return False, "SWAP requires exactly 2 qubits"
            for q in action.qubits:
                if q < 0 or q >= self._num_qubits:
                    return False, f"Qubit index {q} out of range [0, {self._num_qubits - 1}]"
            if action.qubits[0] == action.qubits[1]:
                return False, "SWAP qubit indices must be distinct"

        elif at == ActionType.PARAM:
            if not self._gates:
                return False, "Cannot PARAM-tune with empty circuit"
            if action.parameter is None:
                return False, "PARAM action requires a parameter value"

        return True, None

    # ------------------------------------------------------------------
    # Action application
    # ------------------------------------------------------------------

    def _apply_action(self, action: QuantumAction) -> None:
        """
        Apply a validated action to the circuit gate list.

        IMPORTANT: No Qiskit objects are stored — only plain Python dicts.
        State recomputation happens lazily in _compute_all_scores().
        """
        at = action.action_type

        if at == ActionType.ADD:
            gate_dict: Dict[str, Any] = {
                "gate":   action.gate.value if action.gate else "H",
                "qubits": list(action.qubits),
            }
            if action.parameter is not None:
                gate_dict["parameter"] = action.parameter
            self._gates.append(gate_dict)

        elif at == ActionType.REMOVE:
            # STEP 5: Remove the LAST gate; state recomputed via Qiskit next step
            if self._gates:
                self._gates.pop()

        elif at == ActionType.SWAP:
            # STEP 4: SWAP appended as a gate dict;
            # build_qiskit_circuit translates this to qc.swap(q0, q1)
            self._gates.append({
                "gate":   "SWAP",
                "qubits": list(action.qubits),
            })
            self._swap_count += 1

        elif at == ActionType.PARAM:
            # Tune the parameter of the last parametric gate
            for i in range(len(self._gates) - 1, -1, -1):
                if self._gates[i]["gate"] in ("RX", "RZ"):
                    self._gates[i]["parameter"] = action.parameter
                    break

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _compute_all_scores(self) -> Dict[str, float]:
        """
        Compute all grader scores for the current circuit.

        Calls compute_statevector() → Qiskit for the statevector path.
        UnitaryGrader uses its own matrix math (unchanged).
        """
        # --- Fidelity ---
        if self._target_unitary is not None:
            fidelity_score = UnitaryGrader.grade(self._gates, self._target_unitary, self._num_qubits)
            # Use ground state as placeholder for metadata
            current_sv = np.zeros(2 ** self._num_qubits, dtype=np.complex128)
            current_sv[0] = 1.0
        else:
            # STEP 3: Qiskit statevector computation
            current_sv = compute_statevector(self._gates, self._num_qubits)

            # Dimension assertion (also inside compute_statevector, but belt-and-suspenders)
            expected_dim = 2 ** self._num_qubits
            assert current_sv.shape[0] == expected_dim, (
                f"Statevector dim {current_sv.shape[0]} != 2^{self._num_qubits}={expected_dim}"
            )
            if self._target_sv is not None:
                assert self._target_sv.shape[0] == expected_dim, (
                    f"Target dim {self._target_sv.shape[0]} != 2^{self._num_qubits}={expected_dim}"
                )

            fidelity_score = FidelityGrader.grade(current_sv, self._target_sv)

        # --- Efficiency ---
        depth      = compute_circuit_depth(self._gates, self._num_qubits)
        gate_count = len(self._gates)
        efficiency_score = EfficiencyGrader.grade(
            depth, gate_count,
            self._task_config.get("max_depth", 10),
            self._task_config.get("max_gate_count", 15),
        )

        # --- Noise ---
        noise_model = self._task_config.get("noise_model", "none")
        noise_score, noise_estimate = NoiseGrader.grade(self._gates, noise_model)

        # --- Constraints ---
        connectivity = self._task_config.get("connectivity", [])
        conn_tuples  = [tuple(c) for c in connectivity] if connectivity else []
        constraints_score = ConstraintsGrader.grade(self._gates, conn_tuples, self._num_qubits)

        # --- Aggregate ---
        if self._target_unitary is not None:
            aggregate = 0.7 * fidelity_score + 0.3 * efficiency_score
        else:
            aggregate = self._aggregate_grader.grade(
                fidelity_score, efficiency_score, noise_score, constraints_score
            )

        # Almost-correct zone (smooth transition band 0.7–0.95 fidelity)
        if 0.7 < fidelity_score < 0.95:
            scale = 0.8 + 0.2 * (fidelity_score - 0.7) / 0.25
            aggregate *= scale

        # Approximate task tolerance scaling
        target_tolerance = self._task_config.get("target_tolerance")
        if target_tolerance is not None and fidelity_score > target_tolerance:
            aggregate += 0.2 * (fidelity_score - target_tolerance) / (1.0 - target_tolerance)

        # Noise impact (realism)
        noise_penalty = (1.0 - noise_score) * 2.0
        aggregate -= noise_penalty

        # STEP 7: Depth / time cost
        aggregate -= depth * 0.005

        # STEP 7: SWAP count penalty in aggregate score
        aggregate -= 0.02 * self._swap_count

        # MAX_DEPTH soft penalty
        if depth > MAX_DEPTH:
            aggregate -= 0.1 * (depth - MAX_DEPTH)

        # Budget overflow penalty (smooth)
        strict_budget = self._task_config.get("strict_gate_budget")
        if strict_budget is not None and gate_count > strict_budget:
            overflow = gate_count - strict_budget
            penalty  = overflow / strict_budget
            aggregate *= max(0.3, 1.0 - penalty)

        # Final clamp
        aggregate = max(0.0, min(1.0, aggregate))
        assert 0.0 <= aggregate <= 1.0, f"Aggregate score out of range: {aggregate}"

        return {
            "fidelity":       fidelity_score,
            "efficiency":     efficiency_score,
            "noise":          noise_score,
            "noise_estimate": noise_estimate,
            "constraints":    constraints_score,
            "aggregate":      aggregate,
            "depth":          depth,
            "gate_count":     gate_count,
        }

    def _compute_terminal_reward(self) -> float:
        """Compute bonus/penalty at episode end based on aggregate quality."""
        scores = self._compute_all_scores()
        aggregate = scores["aggregate"]
        return 0.2 if aggregate > 0.8 else -0.2

    # ------------------------------------------------------------------
    # Termination check
    # ------------------------------------------------------------------

    def _check_done(self) -> None:
        """Check if episode should terminate."""
        if self._step_count >= self._max_steps:
            self._done = True

    # ------------------------------------------------------------------
    # Observation builder
    # ------------------------------------------------------------------

    def _build_observation(
        self, reward: float, error: Optional[str] = None
    ) -> QuantumObservation:
        """Build and return a QuantumObservation."""
        scores     = self._compute_all_scores()
        depth      = int(scores.get("depth", 0))
        gate_count = int(scores.get("gate_count", 0))

        # Update trackers from latest scores
        self._prev_fidelity = scores["fidelity"]
        self._prev_depth    = depth

        return QuantumObservation(
            circuit_gates=list(self._gates),
            fidelity=scores["fidelity"],
            depth=depth,
            gate_count=gate_count,
            noise_estimate=scores.get("noise_estimate", 0.0),
            valid_actions=self._get_valid_actions(),
            score=scores["aggregate"],
            task_id=self._task_id,
            num_qubits=self._num_qubits,
            max_steps=self._max_steps,
            steps_taken=self._step_count,
            target_description=self._task_config.get("description", ""),
            done=self._done,
            reward=reward,
            metadata={
                "fidelity_score":     scores["fidelity"],
                "efficiency_score":   scores["efficiency"],
                "noise_score":        scores["noise"],
                "constraints_score":  scores["constraints"],
                "aggregate_score":    scores["aggregate"],
                "error":              error,
            },
        )

    def _get_valid_actions(self) -> List[str]:
        """Return list of valid action type strings."""
        actions = ["ADD", "STOP"]
        if self._gates:
            actions.append("REMOVE")
            has_param_gates = any(g["gate"] in ("RX", "RZ") for g in self._gates)
            if has_param_gates:
                actions.append("PARAM")
        if self._num_qubits >= 2:
            actions.append("SWAP")
        return actions


# ---------------------------------------------------------------------------
# STEP 10: Direct smoke tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")
    print("=== Quantum Circuit Optimization Environment -- Qiskit Smoke Test ===")
    print()

    env = QuantumCircuitEnvironment(seed=42)

    # --- Test 1: Bell State (H + CNOT) → fidelity ≈ 1 ------------------
    print("--- Test 1: Bell State (H + CNOT) ---")
    obs = env.reset(config={"task_id": "easy"})
    print(f"  Initial fidelity: {obs.fidelity:.4f}, score: {obs.score:.4f}")
    obs = env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.H, qubits=[0]))
    print(f"  After H(0):       fid={obs.fidelity:.4f} score={obs.score:.4f} reward={obs.reward:.4f}")
    obs = env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.CNOT, qubits=[0, 1]))
    print(f"  After CNOT(0,1):  fid={obs.fidelity:.4f} score={obs.score:.4f} reward={obs.reward:.4f}")
    obs = env.step(QuantumAction(action_type=ActionType.STOP))
    bell_score = obs.score
    assert bell_score > 0.5, f"FAIL: Bell correct circuit scored {bell_score:.4f}, expected > 0.5"
    print(f"  PASS: Bell score = {bell_score:.4f}")
    print()

    # --- Test 2: GHZ Incomplete -------------------------------------------
    print("--- Test 2: GHZ State (INCOMPLETE: H+CNOT, missing CNOT(1,2)) ---")
    obs = env.reset(config={"task_id": "medium"})
    obs = env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.H, qubits=[0]))
    obs = env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.CNOT, qubits=[0, 1]))
    obs = env.step(QuantumAction(action_type=ActionType.STOP))
    ghz_incomplete = obs.score
    print(f"  STOP: score={ghz_incomplete:.4f} reward={obs.reward:.4f}")
    assert ghz_incomplete < 0.5, f"FAIL: GHZ incomplete scored {ghz_incomplete:.4f}, expected < 0.5"
    print(f"  PASS: GHZ incomplete score = {ghz_incomplete:.4f}")
    print()

    # --- Test 3: GHZ Correct ----------------------------------------------
    print("--- Test 3: GHZ State (CORRECT: H+CNOT(0,1)+CNOT(1,2)) ---")
    obs = env.reset(config={"task_id": "medium"})
    obs = env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.H, qubits=[0]))
    obs = env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.CNOT, qubits=[0, 1]))
    obs = env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.CNOT, qubits=[1, 2]))
    obs = env.step(QuantumAction(action_type=ActionType.STOP))
    ghz_correct = obs.score
    print(f"  STOP: score={ghz_correct:.4f} reward={obs.reward:.4f}")
    assert ghz_correct > 0.5, f"FAIL: GHZ correct scored {ghz_correct:.4f}, expected > 0.5"
    print(f"  PASS: GHZ correct score = {ghz_correct:.4f}")
    print()

    # --- Test 4: SWAP physically swaps qubit states -----------------------
    print("--- Test 4: SWAP — qubit routing effect ---")
    # Qiskit uses LITTLE-ENDIAN qubit ordering:
    #   qubit 0 = LSB, qubit 1 = MSB
    # X on qubit 0 → |10⟩ in big-endian = index 1 (binary ...01 in little-endian)
    # After SWAP(0,1) → qubit states exchange → different basis index
    gates_before_swap = [{"gate": "X", "qubits": [0]}]
    sv_before = compute_statevector(gates_before_swap, 2)
    gates_after_swap  = [{"gate": "X", "qubits": [0]}, {"gate": "SWAP", "qubits": [0, 1]}]
    sv_after  = compute_statevector(gates_after_swap, 2)

    # Find the dominant (non-zero) index for each state
    idx_before = int(np.argmax(np.abs(sv_before)))
    idx_after  = int(np.argmax(np.abs(sv_after)))
    print(f"  Before SWAP: dominant index = {idx_before} (amplitude={abs(sv_before[idx_before]):.4f})")
    print(f"  After  SWAP: dominant index = {idx_after}  (amplitude={abs(sv_after[idx_after]):.4f})")

    # Both must be pure basis states
    assert abs(sv_before[idx_before]) > 0.99, f"Before SWAP not a pure state: {sv_before}"
    assert abs(sv_after[idx_after])  > 0.99, f"After  SWAP not a pure state: {sv_after}"
    # SWAP must have changed which basis state is occupied
    assert idx_before != idx_after, (
        f"SWAP did not change basis state index: before={idx_before}, after={idx_after}"
    )
    print("  PASS: SWAP physically swapped qubit states")
    print()

    # --- Test 5: REMOVE reverts circuit state -----------------------------
    print("--- Test 5: REMOVE — state reverts ---")
    obs = env.reset(config={"task_id": "easy"})
    fid_empty = obs.fidelity
    obs_h = env.step(QuantumAction(action_type=ActionType.ADD, gate=GateType.H, qubits=[0]))
    fid_after_h = obs_h.fidelity
    obs_rm = env.step(QuantumAction(action_type=ActionType.REMOVE))
    fid_after_remove = obs_rm.fidelity
    print(f"  Fidelity (empty): {fid_empty:.6f}")
    print(f"  Fidelity (H(0)):  {fid_after_h:.6f}")
    print(f"  Fidelity (REMOVE→ reverted): {fid_after_remove:.6f}")
    assert abs(fid_after_remove - fid_empty) < 1e-6, (
        f"FAIL: state did not revert after REMOVE "
        f"(empty={fid_empty:.6f}, after_remove={fid_after_remove:.6f})"
    )
    print("  PASS: REMOVE reverted circuit state correctly")
    print()

    # --- Discrimination summary -------------------------------------------
    print("=" * 50)
    print("SCORE DISCRIMINATION SUMMARY:")
    print(f"  Bell correct:     {bell_score:.4f}  (should be > 0.5)")
    print(f"  GHZ incomplete:   {ghz_incomplete:.4f}  (should be < 0.5)")
    print(f"  GHZ correct:      {ghz_correct:.4f}  (should be > 0.5)")
    assert bell_score > ghz_incomplete, "FAIL: Bell should score higher than incomplete GHZ"
    assert ghz_correct > ghz_incomplete, "FAIL: Correct GHZ should score higher than incomplete"
    print("\n  ALL SMOKE TESTS PASSED!")
