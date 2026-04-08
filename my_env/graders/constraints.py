# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Constraints Grader -- penalises violations of hardware connectivity.

Checks that multi-qubit gates (CNOT, SWAP) only act on connected qubit pairs
as defined by the hardware topology graph.

Returns 0.0 on ANY violation (hard failure mode).
"""

import logging
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


class ConstraintsGrader:
    """Evaluate hardware connectivity constraint compliance."""

    @staticmethod
    def grade(
        circuit_gates: List[Dict[str, Any]],
        connectivity: List[Tuple[int, int]],
        num_qubits: int,
    ) -> float:
        """
        Compute constraint compliance score.

        HARD FAILURE: Any single connectivity violation returns 0.0.
        This prevents reward hacking via illegal gate placements.

        Args:
            circuit_gates: List of gate dicts with "gate" and "qubits" keys.
            connectivity: List of (q1, q2) tuples representing connected pairs.
                          Empty list means full connectivity (no constraints).
            num_qubits: Total number of qubits in the circuit.

        Returns:
            Constraint compliance score: 1.0 (all valid) or 0.0 (any violation).
        """
        if not connectivity:
            # Full connectivity -- no constraints to violate
            return 1.0

        # Build adjacency set (bidirectional)
        connected: Set[Tuple[int, int]] = set()
        for a, b in connectivity:
            connected.add((a, b))
            connected.add((b, a))

        for gate_info in circuit_gates:
            qubits = gate_info.get("qubits", [])
            if len(qubits) >= 2:
                q0, q1 = qubits[0], qubits[1]
                if (q0, q1) not in connected:
                    logger.warning(
                        "Connectivity violation: gate=%s qubits=(%d,%d) "
                        "not in allowed pairs %s",
                        gate_info.get("gate"), q0, q1, connectivity,
                    )
                    return 0.0  # Hard failure

        return 1.0
