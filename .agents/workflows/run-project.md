---
description: How to run the Automated PCB Designer project
---

To run this project, you need two terminal windows:

### 1. Start the Backend API
In the root directory (`p:\Text to pcb\automated-pcb-designer`):
// turbo
1. Activate the virtual environment and start the Uvicorn server:
```bash
.\venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```
This serves the API and the PCB design engine on `http://localhost:8000`.

### 2. Start the Frontend
Open a new terminal and navigate to the `frontend` directory:
// turbo
1. Install dependencies (only required the first time):
```bash
cd frontend
npm install
```
2. Start the Vite development server:
```bash
npm run dev
```
The frontend will be accessible at `http://localhost:5173`.

### 3. Verification (Optional)
To verify that the placement and DRC logic is working correctly:
// turbo
```bash
.\venv\Scripts\python.exe run_drc_test.py
```
This runs a sample design end-to-end and checks for violations.
