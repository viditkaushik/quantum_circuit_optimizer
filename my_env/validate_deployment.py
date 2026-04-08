#!/usr/bin/env python3
"""
Pre-Deployment Validation Script
Run this before deploying to HuggingFace Spaces to ensure everything is ready.
"""

import os
import sys
import yaml
import json
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a required file exists."""
    if Path(filepath).exists():
        print(f"  ✓ {description}: {filepath}")
        return True
    else:
        print(f"  ✗ {description} MISSING: {filepath}")
        return False

def validate_openenv_yaml():
    """Validate openenv.yaml structure."""
    print("\n" + "="*60)
    print("Validating openenv.yaml")
    print("="*60)
    
    if not Path("openenv.yaml").exists():
        print("  ✗ openenv.yaml not found!")
        return False
    
    with open("openenv.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    required = ["spec_version", "name", "type", "runtime", "app", "port", "tasks", "action_schema", "observation_schema"]
    all_ok = True
    
    for field in required:
        if field in config:
            print(f"  ✓ {field}: present")
        else:
            print(f"  ✗ {field}: MISSING")
            all_ok = False
    
    # Check tasks
    if "tasks" in config:
        task_count = len(config["tasks"])
        if task_count >= 3:
            print(f"  ✓ Tasks: {task_count} defined (>= 3 required)")
        else:
            print(f"  ✗ Tasks: only {task_count} defined (need >= 3)")
            all_ok = False
    
    return all_ok

def validate_dockerfile():
    """Validate Dockerfile."""
    print("\n" + "="*60)
    print("Validating Dockerfile")
    print("="*60)
    
    if not Path("Dockerfile").exists():
        print("  ✗ Dockerfile not found!")
        return False
    
    with open("Dockerfile", "r") as f:
        content = f.read()
    
    checks = [
        ("EXPOSE 7860", "Port 7860 exposed"),
        ("HEALTHCHECK", "Health check configured"),
        ("CMD", "CMD instruction present"),
        ("uvicorn", "Uvicorn server command"),
    ]
    
    all_ok = True
    for pattern, description in checks:
        if pattern in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} MISSING")
            all_ok = False
    
    return all_ok

def validate_project_structure():
    """Validate project structure."""
    print("\n" + "="*60)
    print("Validating Project Structure")
    print("="*60)
    
    required_files = [
        ("pyproject.toml", "Project configuration"),
        ("README.md", "Documentation"),
        ("inference.py", "Inference script"),
        ("models.py", "Data models"),
        ("client.py", "Client implementation"),
        ("server/app.py", "FastAPI application"),
        ("server/my_env_environment.py", "Environment implementation"),
        ("server/tasks.py", "Task definitions"),
        ("graders/__init__.py", "Graders module"),
    ]
    
    all_ok = True
    for filepath, description in required_files:
        if not check_file_exists(filepath, description):
            all_ok = False
    
    return all_ok

def validate_environment_interface():
    """Validate environment implements required interface."""
    print("\n" + "="*60)
    print("Validating Environment Interface")
    print("="*60)
    
    try:
        from server.my_env_environment import QuantumCircuitEnvironment
        from models import QuantumAction, QuantumObservation, ActionType, GateType
        
        env = QuantumCircuitEnvironment(seed=42)
        
        # Test reset
        obs = env.reset(config={"task_id": "easy"})
        assert isinstance(obs, QuantumObservation), "reset() must return QuantumObservation"
        print("  ✓ reset(config) returns QuantumObservation")
        
        # Test step
        action = QuantumAction(action_type=ActionType.ADD, gate=GateType.H, qubits=[0])
        obs = env.step(action)
        assert isinstance(obs, QuantumObservation), "step() must return QuantumObservation"
        assert hasattr(obs, 'reward'), "Observation must have reward"
        assert hasattr(obs, 'done'), "Observation must have done"
        print("  ✓ step(action) returns QuantumObservation with reward and done")
        
        # Test state
        state = env.state
        assert state is not None, "state property must return State"
        print("  ✓ state property returns State")
        
        # Test score range
        assert 0.0 <= obs.score <= 1.0, f"Score out of range: {obs.score}"
        print(f"  ✓ Score in valid range: {obs.score:.4f}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Environment validation failed: {e}")
        return False

def validate_tasks():
    """Validate all tasks are accessible."""
    print("\n" + "="*60)
    print("Validating Tasks")
    print("="*60)
    
    try:
        from server.my_env_environment import QuantumCircuitEnvironment
        
        env = QuantumCircuitEnvironment(seed=42)
        tasks = ["easy", "medium", "hard", "efficient", "noisy", "budget", "approx"]
        
        for task_id in tasks:
            obs = env.reset(config={"task_id": task_id})
            assert obs.task_id == task_id, f"Task ID mismatch: {obs.task_id} != {task_id}"
            print(f"  ✓ Task '{task_id}': accessible")
        
        print(f"  ✓ All {len(tasks)} tasks validated")
        return True
        
    except Exception as e:
        print(f"  ✗ Task validation failed: {e}")
        return False

def validate_inference_script():
    """Validate inference script structure."""
    print("\n" + "="*60)
    print("Validating Inference Script")
    print("="*60)
    
    if not Path("inference.py").exists():
        print("  ✗ inference.py not found!")
        return False
    
    with open("inference.py", "r") as f:
        content = f.read()
    
    checks = [
        ("from openai import OpenAI", "OpenAI client import"),
        ("API_BASE_URL", "API_BASE_URL variable"),
        ("MODEL_NAME", "MODEL_NAME variable"),
        ("HF_TOKEN", "HF_TOKEN variable"),
        ("[START]", "START log format"),
        ("[STEP]", "STEP log format"),
        ("[END]", "END log format"),
        ("async def main", "Async main function"),
    ]
    
    all_ok = True
    for pattern, description in checks:
        if pattern in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} MISSING")
            all_ok = False
    
    return all_ok

def main():
    """Run all validation checks."""
    print("\n" + "="*60)
    print("PRE-DEPLOYMENT VALIDATION")
    print("="*60)
    
    checks = [
        ("Project Structure", validate_project_structure),
        ("openenv.yaml", validate_openenv_yaml),
        ("Dockerfile", validate_dockerfile),
        ("Environment Interface", validate_environment_interface),
        ("Tasks", validate_tasks),
        ("Inference Script", validate_inference_script),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n  ✗ {name} validation failed with exception: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n" + "="*60)
        print("🎉 READY FOR DEPLOYMENT!")
        print("="*60)
        print("\nNext steps:")
        print("  1. Build Docker image: docker build -t quantum-circuit-opt:latest .")
        print("  2. Test locally: docker run -p 7860:7860 quantum-circuit-opt:latest")
        print("  3. Deploy to HF Spaces: openenv push")
        print("\nSee QUICK_DEPLOY.md for detailed instructions.")
        return 0
    else:
        print("\n" + "="*60)
        print(f"❌ {total - passed} check(s) failed")
        print("="*60)
        print("\nPlease fix the issues above before deploying.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
