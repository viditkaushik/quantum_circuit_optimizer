#  Skills: Quantum Circuit Optimization via Reinforcement Learning

## Overview

This environment trains agents to design and optimize quantum circuits under real-world constraints such as noise, hardware topology, and gate costs.

Unlike toy quantum problems, this simulates **actual challenges faced in NISQ (Noisy Intermediate-Scale Quantum) systems**:
- Noise-aware optimization
- Hardware-constrained compilation
- Multi-objective tradeoffs

---

##  Core Skill

Learn to construct and optimize quantum circuits that:

- Maximize fidelity to a target quantum state/unitary
- Minimize circuit depth and gate count
- Reduce noise-induced degradation
- Respect hardware connectivity constraints

---

##  Sub-skills

### 1. Sequential Decision Making
- Selecting optimal gates step-by-step
- Planning long-horizon circuit construction

### 2. Trade-off Optimization
- Balancing fidelity vs depth vs noise
- Avoiding overfitting to ideal simulation

### 3. Hardware Awareness
- Learning valid qubit connectivity
- Using SWAP operations intelligently

### 4. Noise Robustness
- Designing circuits resilient to decoherence
- Avoiding unnecessary gate operations

### 5. Circuit Editing
- Modifying existing circuits (not just building from scratch)
- Removing redundant or harmful gates

---

##  Observations

Agent receives:

- Current circuit representation (graph or sequence encoding)
- Current fidelity score
- Circuit depth and gate count
- Hardware constraints (connectivity graph)
- Noise model parameters

---

##  Actions

Agent can:

- Add gate (H, X, CNOT, RX, RZ, etc.)
- Remove gate
- Swap qubits
- Tune gate parameters (continuous)
- STOP (terminate episode)

---

##  Rewards

Multi-objective reward signal:

Reward = 
    + Fidelity improvement
    - Depth penalty
    - Noise penalty
    - Invalid action penalty

---

##  Tasks

###  Easy
- Generate Bell state (2 qubits)
- Minimal constraints

###  Medium
- Generate GHZ state (3 qubits)
- Includes noise + connectivity constraints

###  Hard
- Approximate target unitary under:
    - Noise
    - Limited gate set
    - Depth constraint

---

##  Success Criteria

- Fidelity >= threshold
- Circuit depth <= limit
- Noise robustness maintained

Score range: 0.0 - 1.0

---

##  Real-World Relevance

This environment directly maps to:

- Quantum compiler optimization
- Hardware-aware circuit design
- NISQ-era quantum algorithm engineering

---

##  Why This Matters

Quantum hardware is fragile and expensive.  
Optimizing circuits efficiently is a **real bottleneck in quantum computing today**.

This environment enables training agents that can:
- outperform heuristic compilers
- adapt to hardware-specific constraints
- generalize across quantum tasks