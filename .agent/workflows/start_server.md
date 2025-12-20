---
description: Start the SIPI API Backend server
---

# Start SIPI API

This workflow starts the Uvicorn GraphQL server (FastAPI/Starlette).

1. Ensure you are in the `sipi-api` directory.
2. Activate the virtual environment:
   ```powershell
   .\venv\Scripts\activate
   ```
3. Install dependencies if needed:
   ```powershell
   pip install -r requirements.txt
   ```
4. Start the server (with reload enabled):
   // turbo
   ```powershell
   uvicorn app.graphql.app:application --host 0.0.0.0 --port 8040 --reload
   ```
5. GraphQL Playground will be at `http://localhost:8040/graphql`.
