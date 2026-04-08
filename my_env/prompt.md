You are an expert systems engineer, RL researcher, and backend architect.

Your task is to build a COMPLETE, PRODUCTION-GRADE OpenEnv environment for:

"Noise-aware, hardware-constrained quantum circuit optimization using reinforcement learning"

This is NOT a toy project. It must fully comply with OpenEnv specification and be deployable.

---

#  HARD REQUIREMENTS (DO NOT VIOLATE)

* Must follow OpenEnv spec EXACTLY:

  * step(action) -> observation, reward, done, info
  * reset()
  * state()
* Use strict Pydantic models
* Include openenv.yaml
* Include 3+ tasks (easy, medium, hard)
* Each task must have deterministic graders (0.0-1.0)
* Include meaningful reward shaping (NOT sparse)
* Include baseline inference.py (OpenAI client)
* Include Dockerfile (must run)
* Must be HF Spaces deployable
* Must pass "openenv validate"

---

#  PROBLEM DEFINITION

We are building an RL environment where an agent learns to:

* Construct and optimize quantum circuits
* Maximize fidelity to a target state/unitary
* Minimize circuit depth and gate count
* Minimize noise impact
* Respect hardware connectivity constraints

Use Qiskit for simulation (statevector + noisy Aer simulator).

---

#  REQUIRED FILE STRUCTURE

envs/my_env/
|---- **init**.py
|---- models.py
|---- client.py
|---- README.md
|---- openenv.yaml
|---- server/
|---- **init**.py
|---- my_environment.py
|---- graders/
|   |---- fidelity.py
|   |---- efficiency.py
|   |---- noise.py
|   |---- constraints.py
|   |---- aggregate.py
|---- tasks/
|   |---- easy.py
|   |---- medium.py
|   |---- hard.py
|---- app.py
|---- Dockerfile

Also include:

* inference.py (root)
* requirements.txt

---

#  MODEL DEFINITIONS (STRICT)

Define:

Action:

* action_type: ADD, REMOVE, SWAP, PARAM, STOP
* gate
* qubits
* parameter (optional)

Observation:

* circuit (structured representation)
* fidelity (float)
* depth (int)
* gate_count (int)
* noise_estimate (float)
* valid_actions

State:

* full circuit object
* step count
* internal simulator state

---

#  ENVIRONMENT LOGIC

Implement:

## reset()

* initialize empty circuit
* load task config (target, noise model, connectivity)
* return initial observation

## step(action)

* validate action
* apply gate using Qiskit
* simulate:

  * ideal (statevector)
  * noisy (Aer)
* compute:

  * fidelity
  * depth
  * noise estimate
* compute reward via modular graders
* return observation, reward, done, info

## state()

* return full internal state

---

#  ACTION SPACE

* ADD gate (H, X, CNOT, RX, RZ)
* REMOVE gate
* SWAP qubits
* PARAM tuning (continuous angle)
* STOP

---

#  REWARD SYSTEM (VERY IMPORTANT)

Implement modular grading:

## fidelity.py

* compute overlap with target state

## efficiency.py

* penalize depth and gate count

## noise.py

* penalize noisy circuits

## constraints.py

* penalize invalid hardware usage

## aggregate.py

* combine scores into final score (0-1)

Final reward:

* shaped reward = current_score - previous_score

---

#  TASKS (MANDATORY)

## EASY

* Bell state (2 qubits)
* no noise

## MEDIUM

* GHZ state (3 qubits)
* noise + connectivity constraints

## HARD

* arbitrary unitary approximation
* strict depth + noisy simulation

Each task must:

* define target
* define constraints
* define grading thresholds

---

#  OPENENV INTEGRATION

Include openenv.yaml:

* name
* description
* tasks
* action/observation schema

Ensure environment passes openenv validate.

---

#  API SERVER

Use FastAPI:

* POST /reset
* POST /step
* GET /state

---

#  DOCKER

Dockerfile must:

* install qiskit, fastapi, uvicorn, openenv
* expose port
* run server

---

#  BASELINE INFERENCE

Create inference.py:

* uses OpenAI client
* reads:

  * API_BASE_URL
  * MODEL_NAME
  * OPENAI_API_KEY
* runs all 3 tasks
* prints logs in EXACT format:

[START]
[STEP]
[END]

This is critical.

---

#  LOGGING FORMAT (STRICT)

Each step must log:

* step number
* action
* reward
* cumulative score

---

#  README REQUIREMENTS

Include:

* problem description
* real-world relevance (quantum compiler optimization)
* action space
* observation space
* reward design
* task descriptions
* setup instructions
* how to run inference
* expected baseline results

---

#  IMPORTANT DESIGN REQUIREMENTS

* Reward must NOT be sparse
* Must include partial progress signals
* Must penalize bad actions
* Must prevent infinite loops
* Must be deterministic (same input -> same score)

---

#  OUTPUT FORMAT

Generate ALL files with FULL CODE.

Do NOT:

* skip files
* leave TODOs
* give partial implementations

Everything must be runnable.

---

#  BONUS (IF POSSIBLE)

* Add circuit visualization utility
* Add simple logging middleware
* Add reproducibility seed

---

#  FINAL GOAL

Produce a COMPLETE, CLEAN, PROFESSIONAL repository that:

* passes OpenEnv validation
* runs locally
* deploys on HF Spaces
* produces meaningful RL signals
* demonstrates real-world quantum optimization

Think like a Meta/Hugging Face engineer reviewing submissions.

Quality > speed.

Now generate the full implementation.
