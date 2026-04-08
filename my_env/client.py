# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Quantum Circuit Optimization Environment Client."""

from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult

from .models import QuantumAction, QuantumObservation, QuantumState


class QuantumCircuitEnv(
    EnvClient[QuantumAction, QuantumObservation, QuantumState]
):
    """
    Client for the Quantum Circuit Optimization Environment.

    Maintains a persistent WebSocket connection to the environment server
    for efficient multi-step interactions with lower latency.

    Example:
        >>> with QuantumCircuitEnv(base_url="http://localhost:8000") as client:
        ...     result = client.reset()
        ...     print(result.observation.fidelity)
        ...
        ...     from models import ActionType, GateType
        ...     action = QuantumAction(
        ...         action_type=ActionType.ADD,
        ...         gate=GateType.H,
        ...         qubits=[0],
        ...     )
        ...     result = client.step(action)
        ...     print(f"Fidelity: {result.observation.fidelity}")
    """

    def _step_payload(self, action: QuantumAction) -> Dict:
        """
        Convert QuantumAction to JSON payload for step message.

        Args:
            action: QuantumAction instance.

        Returns:
            Dictionary representation suitable for JSON encoding.
        """
        payload = {
            "action_type": action.action_type.value if hasattr(action.action_type, 'value') else action.action_type,
            "qubits": action.qubits,
        }
        if action.gate is not None:
            payload["gate"] = action.gate.value if hasattr(action.gate, 'value') else action.gate
        if action.parameter is not None:
            payload["parameter"] = action.parameter
        return payload

    def _parse_result(self, payload: Dict) -> StepResult[QuantumObservation]:
        """
        Parse server response into StepResult[QuantumObservation].

        Args:
            payload: JSON response data from server.

        Returns:
            StepResult with QuantumObservation.
        """
        obs_data = payload.get("observation", {})

        observation = QuantumObservation(
            circuit_gates=obs_data.get("circuit_gates", []),
            fidelity=obs_data.get("fidelity", 0.0),
            depth=obs_data.get("depth", 0),
            gate_count=obs_data.get("gate_count", 0),
            noise_estimate=obs_data.get("noise_estimate", 0.0),
            valid_actions=obs_data.get("valid_actions", []),
            score=obs_data.get("score", 0.0),
            task_id=obs_data.get("task_id", ""),
            num_qubits=obs_data.get("num_qubits", 0),
            max_steps=obs_data.get("max_steps", 0),
            steps_taken=obs_data.get("steps_taken", 0),
            target_description=obs_data.get("target_description", ""),
            done=payload.get("done", False),
            reward=payload.get("reward"),
            metadata=obs_data.get("metadata", {}),
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> QuantumState:
        """
        Parse server response into QuantumState object.

        Args:
            payload: JSON response from state request.

        Returns:
            QuantumState with full environment state.
        """
        return QuantumState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
            circuit_gates=payload.get("circuit_gates", []),
            target_description=payload.get("target_description", ""),
            task_id=payload.get("task_id", ""),
            max_steps=payload.get("max_steps", 20),
            noise_model_name=payload.get("noise_model_name", "none"),
            current_fidelity=payload.get("current_fidelity", 0.0),
            current_score=payload.get("current_score", 0.0),
        )
