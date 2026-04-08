# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Aggregate Grader -- combines all sub-grader scores into a single 0-1 score.

CRITICAL DESIGN: Fidelity acts as a GATE, not just a weighted component.
The aggregate score is the weighted sum MULTIPLIED by fidelity, ensuring
that low-fidelity circuits cannot score highly regardless of efficiency/noise.

Formula:
    weighted_sum = w_f * fidelity + w_e * efficiency + w_n * noise + w_c * constraints
    aggregate = weighted_sum * fidelity

This means:
    - fidelity=1.0: aggregate == weighted_sum (normal behaviour)
    - fidelity=0.5: aggregate drops by 50% (strong penalty)
    - fidelity=0.0: aggregate == 0.0 (total failure)

This prevents trivially short, incorrect circuits from scoring highly
via inflated efficiency/noise scores.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# Default weight configuration
DEFAULT_WEIGHTS: Dict[str, float] = {
    "fidelity": 0.50,
    "efficiency": 0.20,
    "noise": 0.15,
    "constraints": 0.15,
}


class AggregateGrader:
    """Combine individual grader scores into a single aggregate score."""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize with optional custom weights.

        Args:
            weights: Dict mapping grader name to weight.
                     Must sum to ~1.0. Defaults to DEFAULT_WEIGHTS.
        """
        self.weights = weights or DEFAULT_WEIGHTS.copy()

    def grade(
        self,
        fidelity_score: float,
        efficiency_score: float,
        noise_score: float,
        constraints_score: float,
    ) -> float:
        """
        Compute weighted aggregate score with fidelity gating.

        The final score is:
            weighted_sum * fidelity_score

        This ensures fidelity dominates: a circuit with fidelity=0.25
        can score at most 0.25, regardless of other components.

        If constraints_score == 0.0, the entire score is zeroed out
        (hard constraint failure).

        Args:
            fidelity_score: Score from FidelityGrader [0, 1].
            efficiency_score: Score from EfficiencyGrader [0, 1].
            noise_score: Score from NoiseGrader [0, 1].
            constraints_score: Score from ConstraintsGrader [0, 1].

        Returns:
            Aggregate score in [0.0, 1.0].
        """

        # Hard constraint failure: zero everything
        if constraints_score < 1e-6:
            logger.debug(
                "Aggregate: CONSTRAINT FAILURE -> 0.0 "
                "(fid=%.4f eff=%.4f noise=%.4f cstr=%.4f)",
                fidelity_score, efficiency_score, noise_score, constraints_score,
            )
            return 0.0

        # Weighted sum
        weighted_sum = (
            self.weights.get("fidelity", 0.5) * fidelity_score
            + self.weights.get("efficiency", 0.2) * efficiency_score
            + self.weights.get("noise", 0.15) * noise_score
            + self.weights.get("constraints", 0.15) * constraints_score
        )

        # FIDELITY GATE: multiply by fidelity so low-fidelity circuits
        # cannot score highly from efficiency/noise alone.
        aggregate = weighted_sum * fidelity_score

        aggregate = float(max(0.0, min(1.0, aggregate)))

        logger.debug(
            "Aggregate: %.4f (fid=%.4f eff=%.4f noise=%.4f cstr=%.4f, "
            "weighted_sum=%.4f, fid_gated=%.4f)",
            aggregate, fidelity_score, efficiency_score,
            noise_score, constraints_score, weighted_sum, aggregate,
        )

        return aggregate
