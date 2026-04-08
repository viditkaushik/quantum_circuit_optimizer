# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Data models for the Quantum Circuit Optimization Environment.

Defines strict Pydantic models for actions, observations, and state
used in the noise-aware, hardware-constrained quantum circuit optimization
reinforcement learning environment.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from openenv.core.env_server.types import Action, Observation, State
from pydantic import Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ActionType(str, Enum):
    """Types of actions the agent can take."""
    ADD = "ADD"
    REMOVE = "REMOVE"
    SWAP = "SWAP"
    PARAM = "PARAM"
    STOP = "STOP"


class GateType(str, Enum):
    """Available quantum gates."""
    H = "H"
    X = "X"
    CNOT = "CNOT"
    RX = "RX"
    RZ = "RZ"


# ---------------------------------------------------------------------------
# Gate representation
# ---------------------------------------------------------------------------

class GateInfo(dict):
    """Serializable gate information stored as a dict for JSON compatibility."""
    pass


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------

class QuantumAction(Action):
    """
    Action for the Quantum Circuit Optimization environment.

    The agent selects an action type and, depending on the type,
    specifies the gate, target qubits, and optional continuous parameter.
    """

    action_type: ActionType = Field(
        ..., description="Type of action: ADD, REMOVE, SWAP, PARAM, or STOP"
    )
    gate: Optional[GateType] = Field(
        default=None,
        description="Gate to apply (required for ADD, optional for PARAM)",
    )
    qubits: List[int] = Field(
        default_factory=list,
        description="Target qubit indices for the gate",
    )
    parameter: Optional[float] = Field(
        default=None,
        description="Continuous angle parameter for parametric gates (RX, RZ)",
    )


# ---------------------------------------------------------------------------
# Observation
# ---------------------------------------------------------------------------

class QuantumObservation(Observation):
    """
    Observation returned by the Quantum Circuit Optimization environment.

    Provides the agent with the current circuit state, performance metrics,
    and valid actions for the next step.
    """

    circuit_gates: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Structured list of gates currently in the circuit",
    )
    fidelity: float = Field(
        default=0.0,
        description="Overlap with the target quantum state (0.0-1.0)",
    )
    depth: int = Field(
        default=0,
        description="Current circuit depth",
    )
    gate_count: int = Field(
        default=0,
        description="Total number of gates in the circuit",
    )
    noise_estimate: float = Field(
        default=0.0,
        description="Estimated fidelity loss due to noise (0.0-1.0)",
    )
    valid_actions: List[str] = Field(
        default_factory=list,
        description="List of valid action types in the current state",
    )
    score: float = Field(
        default=0.0,
        description="Aggregate grader score (0.0-1.0)",
    )
    task_id: str = Field(
        default="",
        description="Current task identifier",
    )
    num_qubits: int = Field(
        default=0,
        description="Number of qubits in the circuit",
    )
    max_steps: int = Field(
        default=0,
        description="Maximum steps allowed for this episode",
    )
    steps_taken: int = Field(
        default=0,
        description="Number of steps taken so far",
    )
    target_description: str = Field(
        default="",
        description="Human-readable description of the target state",
    )


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class QuantumState(State):
    """
    Full internal state of the Quantum Circuit Optimization environment.

    Extends the base OpenEnv State with circuit-specific information
    for checkpointing and debugging.
    """

    circuit_gates: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Full circuit gate list",
    )
    target_description: str = Field(
        default="",
        description="Description of the target quantum state",
    )
    task_id: str = Field(
        default="",
        description="Active task identifier",
    )
    max_steps: int = Field(
        default=20,
        description="Maximum steps for this episode",
    )
    noise_model_name: str = Field(
        default="none",
        description="Name of the active noise model",
    )
    current_fidelity: float = Field(
        default=0.0,
        description="Current fidelity score",
    )
    current_score: float = Field(
        default=0.0,
        description="Current aggregate score",
    )
