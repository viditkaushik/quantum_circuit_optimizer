"""
Inference Script -- Quantum Circuit Optimization
===================================
MANDATORY
- Before submitting, ensure the following variables are defined in your environment configuration:
    API_BASE_URL   The API endpoint for the LLM.
    MODEL_NAME     The model identifier to use for inference.
    HF_TOKEN       Your Hugging Face / API key.
    IMAGE_NAME     The name of the local image to use for the environment if you are using
                   from_docker_image() method.

- Defaults are set only for API_BASE_URL and MODEL_NAME
    (and should reflect your active inference setup):
    API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
    MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")

- The inference script must be named `inference.py` and placed in the root directory of the project
- Participants must use OpenAI Client for all LLM calls using above variables

STDOUT FORMAT
- The script must emit exactly three line types to stdout, in this order:

    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>

  Rules:
    - One [START] line at episode begin.
    - One [STEP] line per step, immediately after env.step() returns.
    - One [END] line after env.close(), always emitted (even on exception).
    - reward and rewards are formatted to 2 decimal places.
    - done and success are lowercase booleans: true or false.
    - error is the raw last_action_error string, or null if none.
    - All fields on a single line with no newlines within a line.
    - Each tasks should return score in [0, 1]
"""

import asyncio
import json
import os
import textwrap
from typing import Any, Dict, List, Optional

from openai import OpenAI

from my_env import QuantumAction, QuantumCircuitEnv

# Naive .env loader
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                os.environ[key] = val

IMAGE_NAME = os.getenv("IMAGE_NAME")  # If you are using docker image
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")

API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
BENCHMARK = "quantum_circuit_opt"
TEMPERATURE = 0.7
MAX_TOKENS = 300
SUCCESS_FIDELITY = 0.80  # minimum fidelity for "success"

# Task configurations
TASKS = [
    {"id": "easy", "name": "bell_state", "max_steps": 15},
    {"id": "medium", "name": "ghz_state", "max_steps": 15},
    {"id": "hard", "name": "unitary_approx", "max_steps": 15},
    {"id": "efficient", "name": "imperfect_efficient", "max_steps": 15},
    {"id": "noisy", "name": "noise_dominant", "max_steps": 15},
    {"id": "budget", "name": "budget_optimization", "max_steps": 15},
    {"id": "approx", "name": "approximate_target", "max_steps": 15},
]


# ---------------------------------------------------------------------------
# Logging helpers (strict format)
# ---------------------------------------------------------------------------

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# ---------------------------------------------------------------------------
# System prompt for the LLM
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = textwrap.dedent("""\
    You are an expert quantum circuit designer. You are interacting with an RL environment
    that lets you build quantum circuits step by step.

    AVAILABLE ACTIONS (respond with valid JSON only):
    1. ADD a gate:
       {"action_type": "ADD", "gate": "<H|X|CNOT|RX|RZ>", "qubits": [<int>, ...], "parameter": <float or null>}
       - H, X: single-qubit gates, qubits = [q]
       - CNOT: two-qubit gate, qubits = [control, target]
       - RX, RZ: parametric single-qubit gates, qubits = [q], parameter = angle in radians

    2. REMOVE the last gate:
       {"action_type": "REMOVE", "qubits": []}
       Note: Yields +0.05 bonus if depth decreases with no fidelity loss. Yields -0.05 penalty if fidelity drops.

    3. SWAP two qubits:
       {"action_type": "SWAP", "qubits": [q1, q2]}
       Note: Yields -0.02 penalty per SWAP since it represents real hardware routing overhead.

    4. PARAM -- tune the last parametric gate:
       {"action_type": "PARAM", "qubits": [], "parameter": <float>}

    5. STOP -- end the episode:
       {"action_type": "STOP", "qubits": []}

    RULES:
    - Respond with ONLY the JSON object, nothing else.
    - Maximize fidelity to the target state while minimizing circuit depth.
    - Consider REMOVE to revert a bad step to avoid depth penalties, or SWAP to map qubits.
    - Respect any hardware connectivity constraints described in the observation.
    - All episodes end at 15 steps max.
""")


# ---------------------------------------------------------------------------
# LLM interaction
# ---------------------------------------------------------------------------

def build_user_prompt(obs_data: Dict[str, Any], step: int, history: List[str]) -> str:
    """Build a user prompt from the current observation."""
    history_block = "\n".join(history[-5:]) if history else "None"
    return textwrap.dedent(f"""\
        Step: {step}
        Task: {obs_data.get('target_description', 'unknown')}
        Qubits: {obs_data.get('num_qubits', 2)}
        Current fidelity: {obs_data.get('fidelity', 0.0):.4f}
        Current depth: {obs_data.get('depth', 0)}
        Gate count: {obs_data.get('gate_count', 0)}
        Noise estimate: {obs_data.get('noise_estimate', 0.0):.4f}
        Score: {obs_data.get('score', 0.0):.4f}
        Valid actions: {obs_data.get('valid_actions', [])}
        Steps remaining: {obs_data.get('max_steps', 20) - obs_data.get('steps_taken', 0)}

        Current circuit gates: {json.dumps(obs_data.get('circuit_gates', []))}

        Recent history:
        {history_block}

        Choose your next action (JSON only):
    """)


def get_model_action(
    client: OpenAI,
    obs_data: Dict[str, Any],
    step: int,
    history: List[str],
) -> Dict[str, Any]:
    """Query the LLM for the next action."""
    user_prompt = build_user_prompt(obs_data, step, history)
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()

        # Try to extract JSON from the response
        # Handle markdown code blocks
        if "```" in text:
            lines = text.split("```")
            for block in lines[1:]:
                block = block.strip()
                if block.startswith("json"):
                    block = block[4:].strip()
                if block.startswith("{"):
                    text = block.split("```")[0].strip()
                    break

        action_dict = json.loads(text)
        return action_dict
    except Exception as exc:
        print(f"[DEBUG] Model request/parse failed: {exc}", flush=True)
        # Fallback: try a simple H gate on qubit 0
        return {"action_type": "ADD", "gate": "H", "qubits": [0]}


def dict_to_action(action_dict: Dict[str, Any]) -> QuantumAction:
    """Convert a dict to a QuantumAction."""
    return QuantumAction(
        action_type=action_dict.get("action_type", "STOP"),
        gate=action_dict.get("gate"),
        qubits=action_dict.get("qubits", []),
        parameter=action_dict.get("parameter"),
    )


# ---------------------------------------------------------------------------
# Main inference loop
# ---------------------------------------------------------------------------

async def run_task(
    client: OpenAI,
    env: QuantumCircuitEnv,
    task_config: Dict[str, Any],
) -> float:
    """Run a single task and return the final score."""
    task_id = task_config["id"]
    task_name = task_config["name"]
    max_steps = task_config["max_steps"]

    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = await env.reset(config={"task_id": task_id})
        obs = result.observation
        obs_data = {
            "fidelity": obs.fidelity,
            "depth": obs.depth,
            "gate_count": obs.gate_count,
            "noise_estimate": obs.noise_estimate,
            "valid_actions": obs.valid_actions,
            "score": obs.score,
            "circuit_gates": obs.circuit_gates,
            "target_description": obs.target_description,
            "num_qubits": obs.num_qubits,
            "max_steps": obs.max_steps,
            "steps_taken": obs.steps_taken,
        }

        for step in range(1, max_steps + 1):
            if result.done:
                break

            # Get action from LLM
            action_dict = get_model_action(client, obs_data, step, history)
            action_str = json.dumps(action_dict, separators=(",", ":"))

            # Convert to QuantumAction and step
            action = dict_to_action(action_dict)
            result = await env.step(action)
            obs = result.observation

            reward = result.reward or 0.0
            done = result.done
            error = obs.metadata.get("error") if obs.metadata else None

            rewards.append(reward)
            steps_taken = step

            log_step(step=step, action=action_str, reward=reward, done=done, error=error)

            # Update obs_data for next prompt
            obs_data = {
                "fidelity": obs.fidelity,
                "depth": obs.depth,
                "gate_count": obs.gate_count,
                "noise_estimate": obs.noise_estimate,
                "valid_actions": obs.valid_actions,
                "score": obs.score,
                "circuit_gates": obs.circuit_gates,
                "target_description": obs.target_description,
                "num_qubits": obs.num_qubits,
                "max_steps": obs.max_steps,
                "steps_taken": obs.steps_taken,
            }

            history.append(
                f"Step {step}: {action_str} -> reward={reward:+.2f} fidelity={obs.fidelity:.4f}"
            )

            if done:
                break

        # Final score = aggregate score from the environment
        score = obs_data.get("score", 0.0)
        score = min(max(score, 0.0), 1.0)
        success = obs_data.get("fidelity", 0.0) >= SUCCESS_FIDELITY

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score


async def main() -> None:
    """Run inference across all tasks."""
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    env = await QuantumCircuitEnv.from_docker_image(IMAGE_NAME)

    try:
        total_score = 0.0
        for task_config in TASKS:
            score = await run_task(client, env, task_config)
            total_score += score
            print(f"\n[SUMMARY] Task {task_config['name']}: score={score:.3f}\n", flush=True)

        avg_score = total_score / len(TASKS)
        print(f"\n[FINAL] Average score across {len(TASKS)} tasks: {avg_score:.3f}", flush=True)

    finally:
        try:
            await env.close()
        except Exception as e:
            print(f"[DEBUG] env.close() error (container cleanup): {e}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())