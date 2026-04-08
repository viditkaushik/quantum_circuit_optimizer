# -*- coding: utf-8 -*-
"""
Minimal FastAPI + Gradio server for the Quantum Circuit Optimization Environment.

Deployment spec:
  - Root endpoint:  GET /          → health check JSON
  - Gradio UI:      mounted at     /ui
  - Port:           7860  (managed externally by Docker / HF Spaces)
  - No uvicorn.run() in this file

Run locally:
  uvicorn server.app:app --host 0.0.0.0 --port 7860
"""

import json
import logging
import os
import sys

# sys.path bootstrap so this file can be run directly
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI, Body
from fastapi.responses import RedirectResponse
import gradio as gr
from pydantic import BaseModel

from openenv.core.env_server import create_fastapi_app

from models import ActionType, GateType, QuantumAction, QuantumObservation
from .my_env_environment import QuantumCircuitEnvironment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI base app - Includes OpenEnv WebSocket endpoints
# ---------------------------------------------------------------------------
fastapi_app = create_fastapi_app(
    lambda: QuantumCircuitEnvironment(seed=42),
    QuantumAction,
    QuantumObservation
)

@fastapi_app.get("/web")
def web_redirect():
    """Redirect /web to root Gradio UI."""
    return RedirectResponse(url="/")

@fastapi_app.get("/health")
def health():
    return {"status": "ok", "message": "Quantum Circuit Optimizer is running"}

@fastapi_app.get("/api/info")
def info():
    return {
        "name": "Quantum Circuit Optimization Environment",
        "version": "1.0.0",
        "gradio_ui": "Available at root path /"
    }

class ResetRequest(BaseModel):
    task_id: str = "easy"

# Root-level endpoints for OpenEnv validation
@fastapi_app.post("/reset")
def reset_endpoint(body: dict = Body(default={})):
    """OpenEnv-compliant reset endpoint."""
    task_id = body.get("task_id", "easy")
    temp_env = QuantumCircuitEnvironment(seed=42)
    obs = temp_env.reset(config={"task_id": task_id})
    obs_dict = obs.model_dump() if hasattr(obs, "model_dump") else obs.dict()
    return JSONResponse(content={"observation": obs_dict})

@fastapi_app.post("/step")
def step_endpoint(action: QuantumAction):
    """OpenEnv-compliant step endpoint."""
    temp_env = QuantumCircuitEnvironment(seed=42)
    temp_env.reset(config={"task_id": "easy"})
    obs = temp_env.step(action)
    obs_dict = obs.model_dump() if hasattr(obs, "model_dump") else obs.dict()
    return JSONResponse(content={"observation": obs_dict})

@fastapi_app.get("/state")
def state_endpoint():
    """OpenEnv-compliant state endpoint."""
    temp_env = QuantumCircuitEnvironment(seed=42)
    temp_env.reset(config={"task_id": "easy"})
    state = temp_env.state
    state_dict = state.model_dump() if hasattr(state, "model_dump") else state.dict()
    return JSONResponse(content={"state": state_dict})

# API endpoints (for programmatic access with global env)
@fastapi_app.post("/api/reset")
def api_reset(req: ResetRequest):
    """Programmatic endpoint to reset the environment."""
    global current_obs, step_history
    current_obs = env.reset(config={"task_id": req.task_id})
    step_history = []
    return current_obs

@fastapi_app.post("/api/step")
def api_step(action: QuantumAction):
    """Programmatic endpoint to step the environment."""
    global current_obs
    current_obs = env.step(action)
    return current_obs

@fastapi_app.get("/api/state")
def api_state():
    """Programmatic endpoint to fetch the full internal state."""
    return env.state

# ---------------------------------------------------------------------------
# Global environment instance (for Gradio UI)
# ---------------------------------------------------------------------------
env = QuantumCircuitEnvironment(seed=42)

# Gradio State
current_obs = None
step_history: list = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_circuit(obs) -> str:
    """ASCII circuit summary."""
    if not obs or not obs.circuit_gates:
        return "(empty circuit)"
    lines = []
    for i, g in enumerate(obs.circuit_gates):
        gate   = g.get("gate", "?")
        qubits = g.get("qubits", [])
        param  = g.get("parameter")
        q_str  = ",".join(str(q) for q in qubits)
        if param is not None:
            lines.append(f"  {i+1:>2}. {gate}({q_str}, θ={param:.4f})")
        else:
            lines.append(f"  {i+1:>2}. {gate}({q_str})")
    return "\n".join(lines)


def _format_scores(obs) -> str:
    """Plain-text score summary."""
    if not obs:
        return ""
    meta = obs.metadata or {}
    fid  = round(meta.get("fidelity_score",    obs.fidelity), 4)
    eff  = round(meta.get("efficiency_score",   0),            4)
    noi  = round(meta.get("noise_score",        0),            4)
    con  = round(meta.get("constraints_score",  0),            4)
    agg  = round(meta.get("aggregate_score",    obs.score),    4)
    return (
        f"Fidelity:    {fid}\n"
        f"Efficiency:  {eff}\n"
        f"Noise:       {noi}\n"
        f"Constraints: {con}\n"
        f"AGGREGATE:   {agg}"
    )


def _status(obs, extra: str = "") -> str:
    if not obs:
        return "No environment loaded — click Reset."
    s = (
        f"Task: {obs.task_id} | Qubits: {obs.num_qubits} | "
        f"Step: {obs.steps_taken}/{obs.max_steps}\n"
        f"Fidelity: {obs.fidelity:.4f} | Score: {obs.score:.4f} | "
        f"Reward: {obs.reward:+.4f}"
    )
    if obs.done:
        s += f"\n>>> EPISODE COMPLETE — final score: {obs.score:.4f} <<<"
    if extra:
        s += f"\n{extra}"
    return s


# ---------------------------------------------------------------------------
# Gradio callbacks
# ---------------------------------------------------------------------------

TASK_MAP = {
    "Bell State (Easy)":         "easy",
    "GHZ State (Medium)":        "medium",
    "Unitary Approx (Hard)":     "hard",
    "Imperfect but Efficient":   "efficient",
    "Noise-Dominant":            "noisy",
    "Budgeted Optimization":     "budget",
    "Approximate Target":        "approx",
}


def do_reset(task_name):
    global current_obs, step_history
    task_id = TASK_MAP.get(task_name, "easy")
    current_obs  = env.reset(config={"task_id": task_id})
    step_history = []
    return (
        _status(current_obs, f"Reset to: {task_name}"),
        _format_circuit(current_obs),
        _format_scores(current_obs),
        "",
    )


def do_step(action_type, gate_type, qubit_0, qubit_1, parameter):
    global current_obs, step_history

    if current_obs is None:
        return "ERROR: Reset the environment first!", "(no circuit)", "", ""
    if current_obs.done:
        return _status(current_obs), _format_circuit(current_obs), _format_scores(current_obs), "\n".join(step_history)

    try:
        at     = ActionType(action_type)
        gate   = None
        qubits = []
        param  = None

        if at == ActionType.ADD:
            gate = GateType(gate_type) if gate_type else None
            if gate in (GateType.CNOT,):
                qubits = [int(qubit_0), int(qubit_1)]
            elif gate is not None and gate.value == "SWAP":
                qubits = [int(qubit_0), int(qubit_1)]
            else:
                qubits = [int(qubit_0)]
            if gate in (GateType.RX, GateType.RZ) and parameter is not None:
                param = float(parameter)

        elif at == ActionType.SWAP:
            qubits = [int(qubit_0), int(qubit_1)]

        elif at == ActionType.PARAM:
            if parameter is not None:
                param = float(parameter)

        action      = QuantumAction(action_type=at, gate=gate, qubits=qubits, parameter=param)
        current_obs = env.step(action)

    except Exception as exc:
        logger.exception("Step error: %s", exc)
        return (
            f"ACTION ERROR: {exc}",
            _format_circuit(current_obs) if current_obs else "(no circuit)",
            _format_scores(current_obs) if current_obs else "",
            "\n".join(step_history),
        )

    gate_label = ""
    if gate:
        gate_label = f" {gate_type}({','.join(str(q) for q in qubits)})"
    entry = (
        f"Step {current_obs.steps_taken}: {action_type}{gate_label}"
        f" → fid={current_obs.fidelity:.4f}"
        f" score={current_obs.score:.4f}"
        f" reward={current_obs.reward:+.4f}"
        + (" [DONE]" if current_obs.done else "")
    )
    step_history.append(entry)

    return (
        _status(current_obs),
        _format_circuit(current_obs),
        _format_scores(current_obs),
        "\n".join(step_history),
    )


# ---------------------------------------------------------------------------
# Gradio UI — Elegant and User-Friendly
# ---------------------------------------------------------------------------

TASK_DESCRIPTIONS = {
    "Bell State (Easy)": {
        "description": "Create the famous Bell state: (|00⟩ + |11⟩)/√2",
        "difficulty": "Easy",
        "qubits": 2,
        "noise": "None",
        "connectivity": "Full",
        "goal": "Learn basic 2-qubit entanglement with H + CNOT"
    },
    "GHZ State (Medium)": {
        "description": "Build a 3-qubit GHZ state: (|000⟩ + |111⟩)/√2",
        "difficulty": "Medium",
        "qubits": 3,
        "noise": "Depolarizing",
        "connectivity": "Linear (0↔1↔2)",
        "goal": "Handle noise and limited connectivity"
    },
    "Unitary Approx (Hard)": {
        "description": "Approximate a complex unitary: Ry(π/3) ⊗ Rz(π/4) · CNOT",
        "difficulty": "Hard",
        "qubits": 2,
        "noise": "Thermal",
        "connectivity": "Restricted",
        "goal": "Precise parametric gate tuning under noise"
    },
    "Imperfect but Efficient": {
        "description": "GHZ state with emphasis on circuit efficiency",
        "difficulty": "Medium",
        "qubits": 3,
        "noise": "None",
        "connectivity": "Full",
        "goal": "Balance fidelity (60%) vs efficiency (40%)"
    },
    "Noise-Dominant": {
        "description": "Bell state optimized for noise resilience",
        "difficulty": "Medium",
        "qubits": 2,
        "noise": "Thermal (High)",
        "connectivity": "Full",
        "goal": "Minimize gate count to survive noise (40% weight)"
    },
    "Budgeted Optimization": {
        "description": "GHZ state with strict 3-gate budget",
        "difficulty": "Medium",
        "qubits": 3,
        "noise": "None",
        "connectivity": "Full",
        "goal": "Achieve high fidelity with minimal gates"
    },
    "Approximate Target": {
        "description": "4-qubit GHZ with relaxed fidelity threshold (0.80)",
        "difficulty": "Medium",
        "qubits": 4,
        "noise": "None",
        "connectivity": "Full",
        "goal": "Scale to larger circuits with approximate solutions"
    },
}

GATE_DESCRIPTIONS = {
    "H": "Hadamard — Creates superposition: |0⟩ → (|0⟩+|1⟩)/√2",
    "X": "Pauli-X — Bit flip: |0⟩ ↔ |1⟩",
    "CNOT": "Controlled-NOT — Entangles 2 qubits (requires qubit 0 & 1)",
    "RX": "X-Rotation — Rotate around X-axis by angle θ (needs parameter)",
    "RZ": "Z-Rotation — Rotate around Z-axis by angle θ (needs parameter)",
}

ACTION_DESCRIPTIONS = {
    "ADD": "Add a quantum gate to the circuit",
    "REMOVE": "Remove the last gate from the circuit",
    "SWAP": "Swap two qubits (requires qubit 0 & 1)",
    "PARAM": "Tune the parameter of the last parametric gate (RX/RZ)",
    "STOP": "End the episode and finalize the circuit",
}

def create_gradio_app() -> gr.Blocks:
    with gr.Blocks(title="Quantum Circuit Optimizer", theme=gr.themes.Soft()) as demo:

        # Header
        gr.Markdown(
            """
            # Quantum Circuit Optimizer
            ### Build quantum circuits step-by-step to maximize fidelity with target states
            
            **Goal:** Design circuits that are accurate, efficient, noise-resistant, and hardware-compliant.
            """
        )

        # Task Selection Section
        with gr.Accordion("Available Tasks & Challenges", open=False):
            gr.Markdown(
                """
                Choose a task below to start optimizing. Each task has different constraints:
                
                | Task | Difficulty | Qubits | Noise | Connectivity | Focus |
                |------|------------|--------|-------|--------------|-------|
                | **Bell State** | Easy | 2 | None | Full | Basic entanglement |
                | **GHZ State** | Medium | 3 | Depolarizing | Linear | Noise + topology |
                | **Unitary Approx** | Hard | 2 | Thermal | Restricted | Parametric tuning |
                | **Efficient** | Medium | 3 | None | Full | Minimize depth/gates |
                | **Noise-Dominant** | Medium | 2 | High thermal | Full | Noise resilience |
                | **Budgeted** | Medium | 3 | None | Full | 3-gate limit |
                | **Approximate** | Medium | 4 | None | Full | Scale to 4 qubits |
                """
            )

        with gr.Accordion("Quick Start Guide", open=False):
            gr.Markdown(
                """
                ### How to Use:
                1. **Select a Task** — Choose from 7 quantum optimization challenges
                2. **Reset Environment** — Initialize the task and clear the circuit
                3. **Build Your Circuit** — Add gates step-by-step:
                   - Use **H** and **CNOT** for entanglement
                   - Use **RX/RZ** for parametric rotations (set angle in radians)
                   - Use **SWAP** to rearrange qubits for connectivity
                4. **Monitor Scores** — Watch fidelity, efficiency, noise, and constraints
                5. **Stop** — End the episode when satisfied
                
                ### Scoring:
                - **Fidelity** (40-60%): How close to the target state
                - **Efficiency** (20%): Circuit depth and gate count
                - **Noise** (15-25%): Resilience to quantum errors
                - **Constraints** (10-15%): Hardware connectivity compliance
                """
            )

        gr.Markdown("---")

        # Step 1: Task Selection
        gr.Markdown("### Step 1: Select Task")
        with gr.Row():
            with gr.Column(scale=3):
                task_dd = gr.Dropdown(
                    choices=list(TASK_MAP.keys()),
                    value="Bell State (Easy)",
                    label="Choose a Quantum Task",
                    info="Select the optimization challenge you want to solve"
                )
            with gr.Column(scale=1):
                reset_btn = gr.Button("Reset Environment", variant="primary", size="lg")

        # Task info display
        task_info = gr.Markdown("")
        
        def update_task_info(task_name):
            info = TASK_DESCRIPTIONS.get(task_name, {})
            return f"""
            **{info.get('difficulty', '')}** | {info.get('qubits', 0)} qubits | Noise: {info.get('noise', 'N/A')} | Connectivity: {info.get('connectivity', 'N/A')}
            
            {info.get('description', '')}
            
            **Goal:** {info.get('goal', '')}
            """
        
        task_dd.change(fn=update_task_info, inputs=[task_dd], outputs=[task_info])

        gr.Markdown("---")

        # Step 2: Circuit Building
        gr.Markdown("### Step 2: Build Your Circuit")
        
        with gr.Row():
            with gr.Column():
                action_dd = gr.Dropdown(
                    choices=["ADD", "REMOVE", "SWAP", "PARAM", "STOP"],
                    value="ADD",
                    label="Action Type",
                    info="What operation do you want to perform?"
                )
                action_help = gr.Markdown(ACTION_DESCRIPTIONS["ADD"])
                action_dd.change(fn=lambda x: ACTION_DESCRIPTIONS.get(x, ""), inputs=[action_dd], outputs=[action_help])
            
            with gr.Column():
                gate_dd = gr.Dropdown(
                    choices=["H", "X", "CNOT", "RX", "RZ"],
                    value="H",
                    label="Gate Type (for ADD action)",
                    info="Which quantum gate to add?"
                )
                gate_help = gr.Markdown(GATE_DESCRIPTIONS["H"])
                gate_dd.change(fn=lambda x: GATE_DESCRIPTIONS.get(x, ""), inputs=[gate_dd], outputs=[gate_help])

        with gr.Row():
            qubit_0 = gr.Number(
                value=0,
                label="Qubit 0",
                info="Target qubit (or first qubit for 2-qubit gates)",
                precision=0
            )
            qubit_1 = gr.Number(
                value=1,
                label="Qubit 1",
                info="Second qubit (for CNOT/SWAP only)",
                precision=0
            )
            parameter = gr.Slider(
                minimum=-3.14159,
                maximum=3.14159,
                value=0,
                step=0.01,
                label="Parameter (θ in radians)",
                info="Rotation angle for RX/RZ gates"
            )

        with gr.Row():
            step_btn = gr.Button("Execute Step", variant="primary", size="lg", scale=2)
            state_btn = gr.Button("Get Full State", variant="secondary", scale=1)

        gr.Markdown("---")

        # Step 3: Monitor Progress
        gr.Markdown("### Step 3: Monitor Your Progress")
        
        with gr.Row():
            with gr.Column():
                status_out = gr.Textbox(
                    label="Current Status",
                    lines=4,
                    interactive=False,
                    placeholder="Click 'Reset Environment' to start..."
                )
                scores_out = gr.Textbox(
                    label="Score Breakdown",
                    lines=6,
                    interactive=False
                )
            
            with gr.Column():
                circuit_out = gr.Textbox(
                    label="Current Circuit",
                    lines=10,
                    interactive=False,
                    placeholder="Your circuit will appear here..."
                )

        history_out = gr.Textbox(
            label="Step History",
            lines=8,
            interactive=False,
            placeholder="Action history will be logged here..."
        )

        # Advanced: Full State
        with gr.Accordion("Advanced: Full Environment State", open=False):
            state_out = gr.JSON(label="Complete State Dump")

        # Footer
        gr.Markdown(
            """
            ---
            **Tips:**
            - Start simple: H on qubit 0, then CNOT(0,1) creates a Bell state
            - Watch the fidelity score — aim for >0.90 on easy tasks
            - Fewer gates = better efficiency and noise scores
            - Use REMOVE to undo mistakes
            - Use PARAM to fine-tune RX/RZ angles
            """
        )

        # Event Handlers
        OUTS = [status_out, circuit_out, scores_out, history_out]

        reset_btn.click(fn=do_reset, inputs=[task_dd], outputs=OUTS)
        step_btn.click(fn=do_step, inputs=[action_dd, gate_dd, qubit_0, qubit_1, parameter], outputs=OUTS)
        
        def fetch_state():
            s = env.state
            return s.dict() if hasattr(s, "dict") else s
        
        state_btn.click(fn=fetch_state, inputs=[], outputs=[state_out])

        # Initialize task info on load
        demo.load(fn=update_task_info, inputs=[task_dd], outputs=[task_info])

    return demo


# ---------------------------------------------------------------------------
# Create Gradio app and mount to FastAPI
# ---------------------------------------------------------------------------
demo = create_gradio_app()

# Mount Gradio at root
app = gr.mount_gradio_app(fastapi_app, demo, path="/")

# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
def main():
    """Entry point for 'uv run server' command."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
