---
title: Quantum Circuit Optimizer
emoji: "⚛️"
colorFrom: indigo
colorTo: blue
sdk: docker
pinned: false
app_port: 7860
tags:
  - quantum
  - reinforcement-learning
  - circuit-optimization
  - gradio
  - qiskit
---

# ⚛️ Quantum Circuit Optimizer

A web-based reinforcement learning environment for optimizing quantum circuits. Build and optimize quantum circuits step-by-step to maximize fidelity with target quantum states while respecting hardware constraints and noise.

## 🌟 Features

- **Interactive Web UI**: Built with Gradio for easy circuit construction
- **Reinforcement Learning Ready**: Compatible with RL algorithms for automated optimization
- **Hardware-Aware**: Respects qubit connectivity and gate constraints
- **Noise Simulation**: Includes noise models for realistic NISQ-era circuits
- **Multiple Tasks**: From simple Bell states to complex unitary approximations

## 🎯 Problem Statement

The agent must construct quantum circuits to:

1. **Maximize Fidelity** - Match target quantum states
2. **Minimize Depth** - Shorter circuits run faster
3. **Minimize Gate Count** - Fewer operations reduce noise
4. **Respect Connectivity** - Multi-qubit gates only on connected qubits
5. **Resist Noise** - Circuits must survive decoherence

## 🚀 Action Space

| Action | Description | Parameters |
|--------|-------------|------------|
| `ADD`  | Add a quantum gate | `gate` (H, X, CNOT, RX, RZ), `qubits`, `parameter` |
| `REMOVE` | Remove last gate | -- |
| `SWAP` | Swap two qubits | `qubits` [q1, q2] |
| `PARAM` | Tune parametric gate | `parameter` (angle in radians) |
| `STOP` | End episode | -- |

**Available Gates:**
- **H** - Hadamard (single qubit)
- **X** - Pauli-X / NOT (single qubit)
- **CNOT** - Controlled-NOT (two qubits)
- **RX(θ)** - Rotation around X-axis (parameterized)
- **RZ(θ)** - Rotation around Z-axis (parameterized)

## 🏗️ Architecture

- **Backend**: Qiskit for quantum state simulation
- **Frontend**: Gradio web interface
- **Server**: FastAPI with WebSocket support
- **Environment**: Custom Gym-compatible RL environment

## 🚀 Quick Start

### Local Development

1. **Clone and setup:**
   ```bash
   git clone https://github.com/viditkaushik/quantum_circuit_optimizer.git
   cd quantum_circuit_optimizer
   pip install -r requirements.txt
   ```

2. **Run locally:**
   ```bash
   python server/app.py
   # Or with uvicorn:
   uvicorn server.app:app --host 0.0.0.0 --port 7860
   ```

3. **Open browser:** http://localhost:7860

### Docker Deployment

```bash
# Build image
docker build -t quantum-circuit-optimizer .

# Run container
docker run -p 7860:7860 quantum-circuit-optimizer
```

## 📊 Tasks

- **Easy**: Bell State (2 qubits, no noise)
- **Medium**: GHZ State (3 qubits, depolarizing noise)
- **Hard**: Unitary Approximation (2 qubits, thermal noise)
- **Efficient**: Imperfect but Efficient (budget constraints)
- **Noisy**: Noise-Dominant (high decoherence)
- **Budget**: Budgeted Optimization (resource limits)
- **Approx**: Approximate Target (tolerance-based)

## 🔧 API Endpoints

- `POST /reset` - Reset environment with task
- `POST /step` - Execute action
- `GET /state` - Get current state
- `GET /health` - Health check

## 📈 Metrics

- **Fidelity**: How close circuit output is to target state
- **Efficiency**: Circuit depth and gate count
- **Noise Score**: Resilience to decoherence
- **Constraints Score**: Hardware constraint satisfaction
- **Aggregate Score**: Weighted combination of above

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Add tests
5. Submit pull request

## 📄 License

This project is licensed under the BSD-style license.

## 🙏 Acknowledgments

Built using Qiskit, Gradio, FastAPI, and OpenEnv framework.
- **H** - Hadamard (single qubit)
- **X** - Pauli-X / NOT (single qubit)
- **CNOT** - Controlled-NOT (two qubits)
- **RX(θ)** - Rotation around X-axis (parameterized)
- **RZ(θ)** - Rotation around Z-axis (parameterized)

## 🏗️ Architecture

- **Backend**: Qiskit for quantum state simulation
- **Frontend**: Gradio web interface
- **Server**: FastAPI with WebSocket support
- **Environment**: Custom Gym-compatible RL environment

## 🚀 Quick Start

### Local Development

1. **Clone and setup:**
   ```bash
   git clone https://github.com/viditkaushik/quantum_circuit_optimizer.git
   cd quantum_circuit_optimizer
   pip install -r requirements.txt
   ```

2. **Run locally:**
   ```bash
   python server/app.py
   # Or with uvicorn:
   uvicorn server.app:app --host 0.0.0.0 --port 7860
   ```

3. **Open browser:** http://localhost:7860

### Docker Deployment

```bash
# Build image
docker build -t quantum-circuit-optimizer .

# Run container
docker run -p 7860:7860 quantum-circuit-optimizer
```

## 📊 Tasks

- **Easy**: Bell State (2 qubits, no noise)
- **Medium**: GHZ State (3 qubits, depolarizing noise)
- **Hard**: Unitary Approximation (2 qubits, thermal noise)
- **Efficient**: Imperfect but Efficient (budget constraints)
- **Noisy**: Noise-Dominant (high decoherence)
- **Budget**: Budgeted Optimization (resource limits)
- **Approx**: Approximate Target (tolerance-based)

## 🔧 API Endpoints

- `POST /reset` - Reset environment with task
- `POST /step` - Execute action
- `GET /state` - Get current state
- `GET /health` - Health check

## 📈 Metrics

- **Fidelity**: How close circuit output is to target state
- **Efficiency**: Circuit depth and gate count
- **Noise Score**: Resilience to decoherence
- **Constraints Score**: Hardware constraint satisfaction
- **Aggregate Score**: Weighted combination of above

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Add tests
5. Submit pull request

## 📄 License

This project is licensed under the BSD-style license.

## 🙏 Acknowledgments

Built using Qiskit, Gradio, FastAPI, and OpenEnv framework.

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
