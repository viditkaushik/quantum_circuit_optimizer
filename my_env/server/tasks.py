# -*- coding: utf-8 -*-
"""
Task definitions for the Quantum Circuit Optimization environment.

All three tasks (easy, medium, hard) are defined in this single module
to avoid import chain complexity with sub-packages.
"""

import numpy as np
from typing import Any, Dict, List, Tuple


# ---------------------------------------------------------------------------
# Easy Task -- Bell State (2 qubits, no noise)
# ---------------------------------------------------------------------------

class EasyTask:
    """Bell state preparation task -- 2 qubits, no noise."""

    TASK_ID = "easy"
    DESCRIPTION = "Bell State (|00>+|11>)/sqrt2 -- 2 qubits, no noise, full connectivity"
    NUM_QUBITS = 2
    MAX_DEPTH = 10
    MAX_GATE_COUNT = 15
    MAX_STEPS = 20
    NOISE_MODEL = "none"
    CONNECTIVITY: List[Tuple[int, int]] = []
    FIDELITY_THRESHOLD = 0.90
    GRADER_WEIGHTS = {"fidelity": 0.60, "efficiency": 0.25, "noise": 0.05, "constraints": 0.10}

    @staticmethod
    def target_statevector() -> np.ndarray:
        """(|00> + |11>) / sqrt2"""
        sv = np.zeros(4, dtype=np.complex128)
        sv[0] = 1.0 / np.sqrt(2.0)
        sv[3] = 1.0 / np.sqrt(2.0)
        return sv

    @staticmethod
    def config() -> Dict[str, Any]:
        return {
            "task_id": EasyTask.TASK_ID,
            "description": EasyTask.DESCRIPTION,
            "num_qubits": EasyTask.NUM_QUBITS,
            "max_depth": EasyTask.MAX_DEPTH,
            "max_gate_count": EasyTask.MAX_GATE_COUNT,
            "max_steps": EasyTask.MAX_STEPS,
            "noise_model": EasyTask.NOISE_MODEL,
            "connectivity": EasyTask.CONNECTIVITY,
            "fidelity_threshold": EasyTask.FIDELITY_THRESHOLD,
            "grader_weights": EasyTask.GRADER_WEIGHTS,
        }


# ---------------------------------------------------------------------------
# Medium Task -- GHZ State (3 qubits, depolarizing noise)
# ---------------------------------------------------------------------------

class MediumTask:
    """GHZ state preparation -- 3 qubits, depolarizing noise, linear connectivity."""

    TASK_ID = "medium"
    DESCRIPTION = "GHZ State (|000>+|111>)/sqrt2 -- 3 qubits, depolarizing noise, linear connectivity"
    NUM_QUBITS = 3
    MAX_DEPTH = 15
    MAX_GATE_COUNT = 25
    MAX_STEPS = 30
    NOISE_MODEL = "depolarizing"
    CONNECTIVITY: List[Tuple[int, int]] = [(0, 1), (1, 2)]
    FIDELITY_THRESHOLD = 0.85
    GRADER_WEIGHTS = {"fidelity": 0.45, "efficiency": 0.20, "noise": 0.20, "constraints": 0.15}

    @staticmethod
    def target_statevector() -> np.ndarray:
        """(|000> + |111>) / sqrt2"""
        sv = np.zeros(8, dtype=np.complex128)
        sv[0] = 1.0 / np.sqrt(2.0)
        sv[7] = 1.0 / np.sqrt(2.0)
        return sv

    @staticmethod
    def config() -> Dict[str, Any]:
        return {
            "task_id": MediumTask.TASK_ID,
            "description": MediumTask.DESCRIPTION,
            "num_qubits": MediumTask.NUM_QUBITS,
            "max_depth": MediumTask.MAX_DEPTH,
            "max_gate_count": MediumTask.MAX_GATE_COUNT,
            "max_steps": MediumTask.MAX_STEPS,
            "noise_model": MediumTask.NOISE_MODEL,
            "connectivity": MediumTask.CONNECTIVITY,
            "fidelity_threshold": MediumTask.FIDELITY_THRESHOLD,
            "grader_weights": MediumTask.GRADER_WEIGHTS,
        }


# ---------------------------------------------------------------------------
# Hard Task -- Unitary Approximation (2 qubits, thermal noise)
# ---------------------------------------------------------------------------

def _build_hard_target_unitary() -> np.ndarray:
    """Ry(pi/3) x Rz(pi/4) followed by CNOT(0,1). Returns dense 4x4 matrix."""
    theta = np.pi / 3.0
    ry = np.array([
        [np.cos(theta / 2), -np.sin(theta / 2)],
        [np.sin(theta / 2),  np.cos(theta / 2)],
    ], dtype=np.complex128)

    phi = np.pi / 4.0
    rz = np.array([
        [np.exp(-1j * phi / 2), 0],
        [0, np.exp(1j * phi / 2)],
    ], dtype=np.complex128)

    # Tensor product of Ry(theta) and Rz(phi)
    u_init = np.kron(ry, rz)

    cnot = np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 0, 1],
        [0, 0, 1, 0],
    ], dtype=np.complex128)
    
    # Final unitary U = CNOT @ (Ry x Rz)
    u_target = cnot @ u_init
    return u_target


class HardTask:
    """Arbitrary unitary approximation -- 2 qubits, thermal noise, restricted connectivity."""

    TASK_ID = "hard"
    DESCRIPTION = (
        "Approximate Ry(pi/3)@Rz(pi/4).CNOT - "
        "2 qubits, thermal noise, restricted connectivity, depth <= 20"
    )
    NUM_QUBITS = 2
    MAX_DEPTH = 20
    MAX_GATE_COUNT = 30
    MAX_STEPS = 40
    NOISE_MODEL = "thermal"
    CONNECTIVITY: List[Tuple[int, int]] = [(0, 1)]
    FIDELITY_THRESHOLD = 0.80
    GRADER_WEIGHTS = {"fidelity": 0.40, "efficiency": 0.20, "noise": 0.25, "constraints": 0.15}

    @staticmethod
    def target_unitary() -> np.ndarray:
        return _build_hard_target_unitary()

    @staticmethod
    def config() -> Dict[str, Any]:
        return {
            "task_id": HardTask.TASK_ID,
            "description": HardTask.DESCRIPTION,
            "num_qubits": HardTask.NUM_QUBITS,
            "max_depth": HardTask.MAX_DEPTH,
            "max_gate_count": HardTask.MAX_GATE_COUNT,
            "max_steps": HardTask.MAX_STEPS,
            "noise_model": HardTask.NOISE_MODEL,
            "connectivity": HardTask.CONNECTIVITY,
            "fidelity_threshold": HardTask.FIDELITY_THRESHOLD,
            "grader_weights": HardTask.GRADER_WEIGHTS,
        }


# ---------------------------------------------------------------------------
# New Diversity Tasks
# ---------------------------------------------------------------------------

def _build_approx_target() -> np.ndarray:
    """4-qubit GHZ state."""
    state = np.zeros(16, dtype=np.complex128)
    state[0] = 1.0 / np.sqrt(2)
    state[-1] = 1.0 / np.sqrt(2)
    return state

class EfficientTask:
    TASK_ID = "efficient"
    DESCRIPTION = "Imperfect but Efficient - GHZ target, prefers short circuits"
    NUM_QUBITS = 3
    MAX_DEPTH = 10
    MAX_GATE_COUNT = 15
    MAX_STEPS = 20
    NOISE_MODEL = "none"
    CONNECTIVITY: List[Tuple[int, int]] = []
    FIDELITY_THRESHOLD = 0.90
    GRADER_WEIGHTS = {"fidelity": 0.60, "efficiency": 0.40, "noise": 0.0, "constraints": 0.0}

    @staticmethod
    def target_statevector() -> np.ndarray:
        return MediumTask.target_statevector()

    @staticmethod
    def config() -> Dict[str, Any]:
        return {
            "task_id": EfficientTask.TASK_ID,
            "description": EfficientTask.DESCRIPTION,
            "num_qubits": EfficientTask.NUM_QUBITS,
            "max_depth": EfficientTask.MAX_DEPTH,
            "max_gate_count": EfficientTask.MAX_GATE_COUNT,
            "max_steps": EfficientTask.MAX_STEPS,
            "noise_model": EfficientTask.NOISE_MODEL,
            "connectivity": EfficientTask.CONNECTIVITY,
            "fidelity_threshold": EfficientTask.FIDELITY_THRESHOLD,
            "grader_weights": EfficientTask.GRADER_WEIGHTS,
        }

class NoisyTask:
    TASK_ID = "noisy"
    DESCRIPTION = "Noise-Dominant - Bell target, thermal noise heavily weighted"
    NUM_QUBITS = 2
    MAX_DEPTH = 10
    MAX_GATE_COUNT = 15
    MAX_STEPS = 20
    NOISE_MODEL = "thermal"
    CONNECTIVITY: List[Tuple[int, int]] = []
    FIDELITY_THRESHOLD = 0.90
    GRADER_WEIGHTS = {"fidelity": 0.40, "noise": 0.40, "efficiency": 0.20, "constraints": 0.0}

    @staticmethod
    def target_statevector() -> np.ndarray:
        return EasyTask.target_statevector()

    @staticmethod
    def config() -> Dict[str, Any]:
        return {
            "task_id": NoisyTask.TASK_ID,
            "description": NoisyTask.DESCRIPTION,
            "num_qubits": NoisyTask.NUM_QUBITS,
            "max_depth": NoisyTask.MAX_DEPTH,
            "max_gate_count": NoisyTask.MAX_GATE_COUNT,
            "max_steps": NoisyTask.MAX_STEPS,
            "noise_model": NoisyTask.NOISE_MODEL,
            "connectivity": NoisyTask.CONNECTIVITY,
            "fidelity_threshold": NoisyTask.FIDELITY_THRESHOLD,
            "grader_weights": NoisyTask.GRADER_WEIGHTS,
        }

class BudgetedTask:
    TASK_ID = "budget"
    DESCRIPTION = "Budgeted Optimization - GHZ target, hard limit on gates"
    NUM_QUBITS = 3
    MAX_DEPTH = 10
    MAX_GATE_COUNT = 3  # Will be intercepted dynamically by strictly budgeted logic
    MAX_STEPS = 20
    NOISE_MODEL = "none"
    CONNECTIVITY: List[Tuple[int, int]] = []
    FIDELITY_THRESHOLD = 0.90
    GRADER_WEIGHTS = {"fidelity": 0.80, "efficiency": 0.20, "noise": 0.0, "constraints": 0.0}

    @staticmethod
    def target_statevector() -> np.ndarray:
        return MediumTask.target_statevector()

    @staticmethod
    def config() -> Dict[str, Any]:
        return {
            "task_id": BudgetedTask.TASK_ID,
            "description": BudgetedTask.DESCRIPTION,
            "num_qubits": BudgetedTask.NUM_QUBITS,
            "max_depth": BudgetedTask.MAX_DEPTH,
            "max_gate_count": BudgetedTask.MAX_GATE_COUNT,
            "max_steps": BudgetedTask.MAX_STEPS,
            "noise_model": BudgetedTask.NOISE_MODEL,
            "connectivity": BudgetedTask.CONNECTIVITY,
            "fidelity_threshold": BudgetedTask.FIDELITY_THRESHOLD,
            "grader_weights": BudgetedTask.GRADER_WEIGHTS,
            "strict_gate_budget": BudgetedTask.MAX_GATE_COUNT,
        }

class ApproximateTask:
    TASK_ID = "approx"
    DESCRIPTION = "Approximate Target - 4-qubit target, reward tolerance"
    NUM_QUBITS = 4
    MAX_DEPTH = 15
    MAX_GATE_COUNT = 20
    MAX_STEPS = 30
    NOISE_MODEL = "none"
    CONNECTIVITY: List[Tuple[int, int]] = []
    FIDELITY_THRESHOLD = 0.80  # Much lower requirement
    GRADER_WEIGHTS = {"fidelity": 0.80, "efficiency": 0.20, "noise": 0.0, "constraints": 0.0}

    @staticmethod
    def target_statevector() -> np.ndarray:
        return _build_approx_target()

    @staticmethod
    def config() -> Dict[str, Any]:
        return {
            "task_id": ApproximateTask.TASK_ID,
            "description": ApproximateTask.DESCRIPTION,
            "num_qubits": ApproximateTask.NUM_QUBITS,
            "max_depth": ApproximateTask.MAX_DEPTH,
            "max_gate_count": ApproximateTask.MAX_GATE_COUNT,
            "max_steps": ApproximateTask.MAX_STEPS,
            "noise_model": ApproximateTask.NOISE_MODEL,
            "connectivity": ApproximateTask.CONNECTIVITY,
            "fidelity_threshold": ApproximateTask.FIDELITY_THRESHOLD,
            "grader_weights": ApproximateTask.GRADER_WEIGHTS,
            "target_tolerance": ApproximateTask.FIDELITY_THRESHOLD,
        }

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

TASK_REGISTRY = {
    "easy": EasyTask,
    "medium": MediumTask,
    "hard": HardTask,
    "efficient": EfficientTask,
    "noisy": NoisyTask,
    "budget": BudgetedTask,
    "approx": ApproximateTask,
}
