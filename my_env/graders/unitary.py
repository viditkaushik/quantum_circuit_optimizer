# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Unitary Grader -- measures overlap between a target unitary matrix and the
unitary matrix compiled from the current circuit's gate sequence.

Score = |Tr(U_target^dagger U_current)| / 2^N

This evaluates the OPERATOR directly, avoiding issues where
different unitaries may map a single statevector identically.
"""

import numpy as np
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class UnitaryGrader:
    """Compute the normalized trace fidelity of two unitary matrices."""

    @staticmethod
    def construct_unitary(gates: List[Dict[str, Any]], num_qubits: int) -> np.ndarray:
        """
        Construct a dense Unitary matrix (2^N x 2^N) for the given circuit
        by simulating its application to all computational basis states.
        """
        from server.my_env_environment import build_qiskit_circuit
        import qiskit.quantum_info as qi

        qc = build_qiskit_circuit(gates, num_qubits)
        u_matrix = np.asarray(qi.Operator(qc).data, dtype=np.complex128)
        return u_matrix

    @staticmethod
    def grade(
        current_gates: List[Dict[str, Any]],
        target_unitary: np.ndarray,
        num_qubits: int,
    ) -> float:
        """
        Compute unitary overlap: |Tr(U_target^dagger * U_current)| / dim.

        Args:
            current_gates: Circuit gates applied so far.
            target_unitary: Dense target matrix of shape (2^N, 2^N).
            num_qubits: The number of qubits N.

        Returns:
            Fidelity score in [0.0, 1.0].
        """
        if len(current_gates) == 0:
            return 0.2

        dim = 2 ** num_qubits
        if target_unitary.shape != (dim, dim):
            logger.error("Unitary shape mismatch: target=%s, expected=(%d, %d)", target_unitary.shape, dim, dim)
            raise ValueError(f"Unitary shape mismatch: {target_unitary.shape} vs ({dim}, {dim})")

        # Compile current sequence of gates into a unitary matrix
        current_unitary = UnitaryGrader.construct_unitary(current_gates, num_qubits)

        # Compute normalized trace |Tr(U_t^dagger U_c)| / d
        trace_val = np.trace(target_unitary.conj().T @ current_unitary)
        fidelity = abs(trace_val) / dim

        # Shaping for RL friendliness
        fidelity = max(0.1, fidelity)
        fidelity -= 0.01 * len(current_gates)

        # Clip and return
        return float(np.clip(fidelity, 0.0, 1.0))
