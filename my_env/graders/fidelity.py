# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Fidelity Grader -- measures overlap between current and target quantum states.

Score = |<target|current>|^2  (state fidelity), clamped to [0, 1].
Includes strict dimension validation and normalization.
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)


class FidelityGrader:
    """Compute fidelity between current statevector and target statevector."""

    @staticmethod
    def grade(
        current_statevector: np.ndarray,
        target_statevector: np.ndarray,
    ) -> float:
        """
        Compute the state fidelity with strict validation.

        Args:
            current_statevector: Current circuit's output statevector (complex array).
            target_statevector: Target statevector to match (complex array).

        Returns:
            Fidelity score in [0.0, 1.0].

        Raises:
            ValueError: If statevector dimensions are not powers of 2.
        """
        if current_statevector is None or target_statevector is None:
            return 0.0

        # --- Dimension validation ---
        if current_statevector.shape != target_statevector.shape:
            logger.error("Dimension mismatch: current=%s, target=%s", current_statevector.shape, target_statevector.shape)
            raise ValueError(f"Shape mismatch: {current_statevector.shape} vs {target_statevector.shape}")

        dim = current_statevector.shape[0]
        # Must be a power of 2
        if dim == 0 or (dim & (dim - 1)) != 0:
            logger.error("Statevector dimension %d is not a power of 2", dim)
            raise ValueError(f"Statevector dimension {dim} is not a power of 2")

        # --- Normalization ---
        current_norm = np.linalg.norm(current_statevector)
        target_norm = np.linalg.norm(target_statevector)

        if current_norm < 1e-12 or target_norm < 1e-12:
            return 0.0

        current_normalized = current_statevector / current_norm
        target_normalized = target_statevector / target_norm

        # --- State fidelity = |<target|current>|^2 ---
        overlap = np.abs(np.vdot(target_normalized, current_normalized)) ** 2
        fidelity = float(np.clip(overlap, 0.0, 1.0))

        # Assertion: fidelity must be in [0, 1]
        assert 0.0 <= fidelity <= 1.0 + 1e-9, f"Fidelity out of range: {fidelity}"

        logger.debug("Fidelity: %.6f (dim=%d)", fidelity, dim)
        return fidelity
