# 🚀 Deployment Guide - Hugging Face Spaces

## Step-by-Step Instructions

### 1. **Clean Build** (Remove old Docker images)
```bash
# Remove old Docker images
docker rmi quantum-circuit-opt:latest -f
docker system prune -f
```

### 2. **Build New Docker Image**
```bash
cd d:\2026\Meta_Pytorch\OpenEnv\my_env

# Build the image
docker build -t quantum-circuit-opt:latest .
```

### 3. **Test Locally**
```bash  
# Run the container
docker run -p 7860:7860 quantum-circuit-opt:latest

# Open browser to: http://localhost:7860
# You should see the Gradio UI
```

### 4. **Deploy to Hugging Face Spaces**
```bash
# Make sure you're in the my_env directory
cd d:\2026\Meta_Pytorch\OpenEnv\my_env

# Push to HF Spaces
openenv push
```

### 5. **Verify Deployment**
- Go to your HF Space: https://huggingface.co/spaces/YOUR_USERNAME/quantum_circuit_optimizer
- Wait for build to complete (check logs)
- The Gradio UI should load automatically

---

## 🔧 Troubleshooting

### Issue: `{"detail":"Not Found"}`
**Cause**: FastAPI routing conflict or wrong entry point

**Fix**: 
- Ensure `server/app.py` exposes `app = demo` (Gradio Blocks object)
- Dockerfile CMD should run: `python -m server.app`

### Issue: Container builds but UI doesn't load
**Cause**: Port mismatch or wrong server configuration

**Fix**:
- Check README.md has `app_port: 7860`
- Verify Dockerfile exposes port 7860
- Ensure Gradio launches with `server_name="0.0.0.0"`

### Issue: Import errors in container
**Cause**: Missing dependencies or wrong Python path

**Fix**:
- Check `pyproject.toml` has all dependencies
- Verify `PYTHONPATH` is set in Dockerfile
- Run `uv sync` to update lock file

---

## 📋 Validation Checklist

After deployment, run the validation script:

```bash
cd d:\2026\Meta_Pytorch\OpenEnv\my_env
bash validate-submission.sh
```

This will check:
- ✅ Environment can be imported
- ✅ Reset works correctly
- ✅ Step actions execute
- ✅ Rewards are calculated
- ✅ All tasks are accessible

---

## 🎯 Expected Behavior

### Successful Deployment:
1. Space shows "Running" status
2. Gradio UI loads with:
   - Task dropdown (Easy/Medium/Hard)
   - Action controls (ADD/REMOVE/SWAP/PARAM/STOP)
   - Gate selection (H/X/CNOT/RX/RZ)
   - Circuit display
   - Score visualization
3. Can interact with UI:
   - Reset environment
   - Execute steps
   - See rewards update

### What You Should See:
```
Task: easy | Qubits: 2 | Step: 0/20
Fidelity: 0.0000 | Score: 0.0000 | Reward: +0.0000
```

After clicking "Reset Environment" and executing steps.

---

## 📁 Key Files

- `server/app.py` - Main Gradio application
- `Dockerfile` - Container configuration
- `README.md` - HF Spaces metadata
- `pyproject.toml` - Dependencies
- `openenv.yaml` - Environment manifest

---

## 🔄 Quick Redeploy

If you need to redeploy after changes:

```bash
# 1. Rebuild Docker image
docker build -t quantum-circuit-opt:latest .

# 2. Test locally
docker run -p 8000:8000 quantum-circuit-opt:latest

# 3. Push to HF Spaces
openenv push
```

---

## ✅ Success Indicators

- ✅ Docker build completes without errors
- ✅ Local test shows Gradio UI at http://localhost:8000
- ✅ HF Space shows "Running" status
- ✅ UI loads and is interactive
- ✅ Can reset environment and execute actions
- ✅ Rewards update correctly
