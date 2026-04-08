# Quick Deployment Guide

## Prerequisites
- Docker installed
- HuggingFace account with token
- OpenEnv CLI installed (`pip install openenv-core`)

## Step 1: Build Docker Image

```bash
docker build -t quantum-circuit-opt:latest .
```

## Step 2: Test Locally

```bash
# Run container
docker run -p 7860:7860 quantum-circuit-opt:latest

# In another terminal, test endpoints
curl http://localhost:7860/health
curl http://localhost:7860/tasks

# Open browser to http://localhost:7860/ui
```

## Step 3: Test Reset Endpoint

```bash
# Using Python
python -c "
from server.my_env_environment import QuantumCircuitEnvironment
env = QuantumCircuitEnvironment(seed=42)
obs = env.reset(config={'task_id': 'easy'})
print(f'Reset successful: fidelity={obs.fidelity:.4f}, score={obs.score:.4f}')
"
```

## Step 4: Run Compliance Tests

```bash
python test_compliance.py
```

Expected output:
```
🎉 ALL COMPLIANCE TESTS PASSED!
Total: 6/6 tests passed
```

## Step 5: Test Inference (Optional)

```bash
export HF_TOKEN="your-hf-token"
export IMAGE_NAME="quantum-circuit-opt:latest"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"

python inference.py
```

## Step 6: Deploy to HuggingFace Spaces

### Option A: Using OpenEnv CLI (Recommended)

```bash
# Login to HuggingFace
huggingface-cli login

# Push to HF Spaces
openenv push
```

### Option B: Manual Deployment

1. Create a new Space on HuggingFace:
   - Go to https://huggingface.co/spaces
   - Click "Create new Space"
   - Name: `quantum-circuit-optimizer`
   - SDK: Docker
   - Hardware: CPU Basic (or better)

2. Clone the Space repository:
```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/quantum-circuit-optimizer
cd quantum-circuit-optimizer
```

3. Copy all files from your environment:
```bash
cp -r /path/to/my_env/* .
```

4. Commit and push:
```bash
git add .
git commit -m "Initial deployment"
git push
```

5. Wait for Space to build (5-10 minutes)

6. Verify deployment:
   - Visit your Space URL
   - Check that UI loads
   - Test reset by clicking "Reset Environment"

## Step 7: Verify Deployment

Once deployed, test the Space:

```bash
# Replace with your Space URL
SPACE_URL="https://YOUR_USERNAME-quantum-circuit-optimizer.hf.space"

# Test health endpoint
curl $SPACE_URL/health

# Test tasks endpoint
curl $SPACE_URL/tasks

# Test reset via API (requires session)
# Or use the Gradio UI at $SPACE_URL/ui
```

## Troubleshooting

### Build fails
- Check Dockerfile syntax
- Verify all dependencies in pyproject.toml
- Ensure uv.lock is up to date: `uv lock`

### Reset endpoint not available
- Verify `reset(config: Dict)` signature in environment
- Check that `create_app` is called correctly in app.py
- Ensure environment is properly registered

### Scores out of range
- All grader scores must be in [0.0, 1.0]
- Check aggregate grader weights sum correctly
- Verify reward clamping in step function

### Inference fails
- Verify HF_TOKEN is set
- Check MODEL_NAME is accessible
- Ensure IMAGE_NAME matches built image
- Review inference.py stdout format

## Success Criteria

✅ Space builds without errors
✅ Health endpoint returns 200
✅ Reset endpoint responds with valid observation
✅ All 7 tasks are accessible
✅ Graders produce scores in [0.0, 1.0]
✅ Inference script completes without error
✅ UI is accessible and functional

## Next Steps

After successful deployment:
1. Test with different LLM models
2. Monitor Space logs for errors
3. Iterate on reward function based on agent performance
4. Add more tasks for diversity
5. Optimize Docker image size if needed

## Support

- OpenEnv Documentation: https://github.com/meta-pytorch/OpenEnv
- HuggingFace Spaces: https://huggingface.co/docs/hub/spaces
- Issues: Report in your repository's issue tracker
