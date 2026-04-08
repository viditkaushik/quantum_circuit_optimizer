---
title: Quantum Circuit Optimization Environment
emoji: "⭐"
colorFrom: indigo
colorTo: blue
sdk: docker
pinned: false
app_port: 7860
tags:
  - openenv
  - quantum
  - reinforcement-learning
---

#  Quantum Circuit Optimization Environment

> **🚀 Deployment Status: READY** | All OpenEnv compliance requirements verified ✅
> 
> See [DEPLOYMENT_READY.md](DEPLOYMENT_READY.md) for full checklist

A **noise-aware, hardware-constrained** reinforcement learning environment for quantum circuit design and optimisation, built on the [OpenEnv](https://github.com/meta-pytorch/OpenEnv) framework.

##  Real-World Relevance

Quantum hardware is fragile and expensive. Current NISQ (Noisy Intermediate-Scale Quantum) devices have limited qubit counts, noisy gates, and restricted connectivity. Efficiently compiling and optimising quantum circuits is a **real bottleneck** in quantum computing today. This environment directly maps to:

- **Quantum compiler optimisation** -- replacing heuristic compilers with learned agents
- **Hardware-aware circuit design** -- respecting physical qubit topology
- **NISQ-era algorithm engineering** -- maximising fidelity under noise

##  Problem

The agent must construct quantum circuits step-by-step to:

1. **Maximise fidelity** -- match a target quantum state
2. **Minimise depth** -- shorter circuits run faster
3. **Minimise gate count** -- fewer operations = less noise
4. **Respect connectivity** -- multi-qubit gates only on connected qubits
5. **Resist noise** -- circuits must survive decoherence

##  Action Space

| Action | Description | Parameters |
|--------|-------------|------------|
| `ADD`  | Add a quantum gate | `gate` (H, X, CNOT, RX, RZ), `qubits`, `parameter` |
| `REMOVE` | Remove the last gate | -- |
| `SWAP` | Swap two qubits | `qubits` [q1, q2] |
| `PARAM` | Tune last parametric gate | `parameter` (angle) |
| `STOP` | End the episode | -- |

**Gates available:** Hadamard (H), Pauli-X (X), CNOT, RX(theta), RZ(theta)

##  Observation Space

| Field | Type | Description |
|-------|------|-------------|
| `circuit_gates` | list | Current gates in the circuit |
| `fidelity` | float | Overlap with target state (0-1) |
| `depth` | int | Circuit depth |
| `gate_count` | int | Number of gates |
| `noise_estimate` | float | Estimated fidelity loss from noise |
| `valid_actions` | list | Legal action types |
| `score` | float | Aggregate grader score (0-1) |
| `target_description` | str | What state to build |

##  Reward Design

**Shaped reward** -- NOT sparse. The reward at each step is:

```
reward = current_aggregate_score - previous_aggregate_score
```

The aggregate score is a weighted combination of four modular graders:

| Grader | Weight | Measures |
|--------|--------|----------|
| **Fidelity** | 40-60% | State overlap with target |
| **Efficiency** | 20% | Depth + gate count vs limits |
| **Noise** | 15-25% | Gate-by-gate error probability |
| **Constraints** | 10-15% | Hardware connectivity compliance |

At episode end: **+0.2 bonus** if fidelity >= threshold, **-0.05 penalty** otherwise.

##  Tasks

**7 diverse tasks** covering different quantum circuit optimization challenges:

###  1. Easy -- Bell State
- **Target:** (|00> + |11>) / sqrt(2)
- **Qubits:** 2 | **Noise:** None | **Connectivity:** Full
- **Max depth:** 10 | **Max steps:** 20

###  2. Medium -- GHZ State
- **Target:** (|000> + |111>) / sqrt(2)
- **Qubits:** 3 | **Noise:** Depolarizing | **Connectivity:** Linear (0<->1<->2)
- **Max depth:** 15 | **Max steps:** 30

###  3. Hard -- Unitary Approximation
- **Target:** Ry(pi/3) @ Rz(pi/4) . CNOT
- **Qubits:** 2 | **Noise:** Thermal | **Connectivity:** Restricted (0<->1 only)
- **Max depth:** 20 | **Max steps:** 40

###  4. Efficient -- Imperfect but Efficient
- **Target:** GHZ state with efficiency focus
- **Qubits:** 3 | **Noise:** None | **Grader weights:** 60% fidelity, 40% efficiency

###  5. Noisy -- Noise-Dominant
- **Target:** Bell state with noise focus
- **Qubits:** 2 | **Noise:** Thermal | **Grader weights:** 40% fidelity, 40% noise

###  6. Budget -- Budgeted Optimization
- **Target:** GHZ state with strict gate budget
- **Qubits:** 3 | **Max gates:** 3 | **Hard constraint on gate count**

###  7. Approx -- Approximate Target
- **Target:** 4-qubit GHZ state
- **Qubits:** 4 | **Tolerance:** 0.80 fidelity | **Rewards approximate solutions**

##  Quick Start

### Prerequisites

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

### Run Server Locally

```bash
# Development mode
uvicorn server.app:app --reload --host 0.0.0.0 --port 8000

# Or via uv
uv run --project . server
```

### Test Directly (No Server)

```bash
python server/my_env_environment.py
```

### Build & Run Docker

```bash
docker build -t quantum-circuit-opt:latest .
docker run -p 8000:8000 quantum-circuit-opt:latest
```

### Run Inference

```bash
export HF_TOKEN="your-token"
export IMAGE_NAME="quantum-circuit-opt:latest"
python inference.py
```

### Deploy to HF Spaces

```bash
openenv push
```

##  Expected Baseline Results

With a capable LLM (e.g., Qwen2.5-72B):

| Task | Expected Score | Expected Fidelity |
|------|---------------|-------------------|
| Easy (Bell) | 0.65-0.85 | >= 0.90 |
| Medium (GHZ) | 0.45-0.65 | >= 0.80 |
| Hard (Unitary) | 0.30-0.50 | >= 0.60 |
| Efficient | 0.60-0.80 | >= 0.85 |
| Noisy | 0.40-0.60 | >= 0.75 |
| Budget | 0.50-0.70 | >= 0.80 |
| Approx | 0.55-0.75 | >= 0.70 |

Scores depend heavily on the LLM's ability to reason about quantum operations.

##  Validation & Testing

```bash
# Run compliance tests (verifies all OpenEnv requirements)
python test_compliance.py

# Run pre-deployment validation
python validate_deployment.py

# Run environment smoke tests
python server/my_env_environment.py
```

##  Project Structure

```
my_env/
|---- __init__.py                    # Module exports
|---- models.py                      # Pydantic action/observation/state models
|---- client.py                      # QuantumCircuitEnv client
|---- openenv.yaml                   # OpenEnv manifest
|---- pyproject.toml                 # Project dependencies
|---- inference.py                   # Baseline inference script
|---- Dockerfile                     # Container image
|---- README.md                      # This file
|---- graders/
|   |---- __init__.py
|   |---- fidelity.py                # State fidelity grader
|   |---- efficiency.py              # Depth + gate count grader
|   |---- noise.py                   # Noise resilience grader
|   |---- constraints.py             # Connectivity compliance grader
|   |---- aggregate.py               # Weighted score combiner
|---- server/
    |---- __init__.py
    |---- my_env_environment.py      # Core environment + statevector simulator
    |---- app.py                     # FastAPI application
    |---- tasks/
        |---- __init__.py            # Task registry
        |---- easy.py                # Bell state task
        |---- medium.py              # GHZ state task
        |---- hard.py                # Unitary approximation task
```

##  Technical Design

### Statevector Simulator

Uses a **pure-NumPy statevector simulator** for deterministic, dependency-light quantum simulation:
- No native C++ compilation required (unlike Qiskit Aer)
- Exact simulation for 2-3 qubit circuits
- Supports H, X, CNOT, RX(theta), RZ(theta), SWAP gates
- Fully deterministic -- same inputs always produce same outputs

### Noise Model

Analytical noise estimation rather than density matrix simulation:
- **Depolarizing:** Per-gate error rates (single-qubit: 0.1%, two-qubit: 1%)
- **Thermal:** 2x higher error rates than depolarizing
- Noise score = probability of no error across all gates

### Determinism

All scoring is deterministic: same circuit -> same score. This is critical for reliable RL training and reproducible evaluation.
