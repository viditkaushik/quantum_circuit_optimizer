# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Noise Grader -- penalises circuits that degrade under noise.

Uses an analytical noise model: each gate introduces a small fidelity loss.
The noise estimate is the probability that *no* gate experienced an error.
"""

import math
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class NoiseGrader:
    """Estimate noise resilience of the circuit."""

    # Per-gate error rates for the depolarizing model
    DEFAULT_ERROR_RATES: Dict[str, float] = {
        "H": 0.001,
        "X": 0.001,
        "RX": 0.002,
        "RZ": 0.002,
        "CNOT": 0.01,
        "SWAP": 0.015,
    }

    @staticmethod
    def grade(
        circuit_gates: List[Dict[str, Any]],
        noise_model: str = "none",
        error_rates: Optional[Dict[str, float]] = None,
    ) -> Tuple[float, float]:
        """
        Compute noise resilience score and raw noise estimate.

        The noise estimate is the cumulative probability of error:
            P(no_error) = product(1 - err_rate_i) for each gate
            noise_estimate = 1 - P(no_error)

        Score = P(no_error), i.e., how likely the circuit survives without error.

        Args:
            circuit_gates: List of gate dicts with at least a "gate" key.
            noise_model: Name of noise model ("none", "depolarizing", "thermal").
            error_rates: Optional custom per-gate error rates.

        Returns:
            Tuple of (score, noise_estimate) where score is in [0, 1]
            and noise_estimate is the estimated fidelity loss.
        """
        if noise_model == "none" or not circuit_gates:
            return 1.0, 0.0

        rates = error_rates or NoiseGrader.DEFAULT_ERROR_RATES.copy()

        # Thermal noise has higher error rates
        if noise_model == "thermal":
            rates = {k: v * 2.0 for k, v in rates.items()}

        # Compute survival probability
        log_survival = 0.0
        for gate_info in circuit_gates:
            gate_name = gate_info.get("gate", "H")
            rate = rates.get(gate_name, 0.005)
            log_survival += math.log(max(1.0 - rate, 1e-15))

        survival_prob = math.exp(log_survival)
        noise_estimate = 1.0 - survival_prob

        score = float(max(0.0, min(1.0, survival_prob)))

        logger.debug(
            "Noise: model=%s, gates=%d, survival=%.6f, estimate=%.6f",
            noise_model, len(circuit_gates), score, noise_estimate,
        )

        return score, float(noise_estimate)
