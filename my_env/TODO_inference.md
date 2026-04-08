# Fix inference.py Crash

## Info Gathered
- Crash at asyncio.run(main()): env = await QuantumCircuitEnv.from_docker_image(None)
- Wrong import: from my_env (missing) → models & server.my_env_environment
- Docker image init fails for local → use HTTP client "http://localhost:7860"
- No error handling

## Plan
1. Fix imports in inference.py
2. Change env init to QuantumCircuitEnv("http://localhost:7860")
3. Add try/except around async calls
4. Align TASKS with server tasks
5. Test: python inference.py

## Pending
- [ ] Edit inference.py
- [ ] Test run
- [ ] Complete

Ready - confirm?
