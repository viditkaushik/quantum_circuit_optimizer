# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Efficiency Grader -- penalises excessive AND insufficient circuit complexity.

Scores circuits based on how well their depth and gate count match
the expected complexity for the given task. Too-short circuits are penalized
because they likely haven't solved the task.
"""

import logging

logger = logging.getLogger(__name__)


class EfficiencyGrader:
    """Evaluate circuit efficiency relative to task constraints."""

    @staticmethod
    def grade(
        depth: int,
        gate_count: int,
        max_depth: int,
        max_gate_count: int,
        min_expected_gates: int = 0,
    ) -> float:
        """
        Compute efficiency score.

        Penalizes both over-complexity (exceeding limits) and under-complexity
        (circuits with fewer gates than the minimum expected for this task).

        Args:
            depth: Current circuit depth.
            gate_count: Current total gate count.
            max_depth: Maximum allowed depth from task config.
            max_gate_count: Maximum allowed gate count from task config.
            min_expected_gates: Minimum number of gates expected for a correct
                                solution. Circuits below this are penalized.

        Returns:
            Efficiency score in [0.0, 1.0].
        """
        if max_depth <= 0:
            max_depth = 1
        if max_gate_count <= 0:
            max_gate_count = 1

        # --- Depth sub-score ---
        depth_ratio = depth / max_depth
        if depth_ratio <= 1.0:
            depth_score = 1.0 - depth_ratio * 0.5  # 1.0 at 0, 0.5 at limit
        else:
            depth_score = max(0.0, 1.0 - depth_ratio)  # drops past limit

        # --- Gate count sub-score ---
        gate_ratio = gate_count / max_gate_count
        if gate_ratio <= 1.0:
            gate_score = 1.0 - gate_ratio * 0.5
        else:
            gate_score = max(0.0, 1.0 - gate_ratio)

        score = (depth_score + gate_score) / 2.0

        logger.debug(
            "Efficiency: depth=%d/%d (%.2f), gates=%d/%d (%.2f), "
            "min_expected=%d, score=%.4f",
            depth, max_depth, depth_score,
            gate_count, max_gate_count, gate_score,
            min_expected_gates, score,
        )

        return float(max(0.0, min(1.0, score)))
