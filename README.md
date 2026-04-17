# Automated PCB Designer

End-to-end automated PCB (Printed Circuit Board) design system.

## Prerequisites
- Python 3.10+
- Node.js 20+

*Note: This modified version runs entirely locally using FastAPI BackgroundTasks and in-memory event queues, removing the need for Docker, PostgreSQL, and Redis.*

## Environment Setup
If not already set up, ensure you have the virtual environment activated and dependencies installed:
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

In the `frontend` directory:
```bash
cd frontend
npm install
```

## Running the Application

You only need two terminal windows now.

### 1. Start the Backend API
In a new terminal window at the project root (`automated-pcb-designer`):
```bash
.\venv\Scripts\activate
uvicorn backend.main:app --reload --port 8000
```
This serves the API logic and the background design worker on `http://localhost:8000`.

### 2. Start the Frontend
In a new terminal window:
```bash
cd frontend
npm run dev
```
The frontend UI will be accessible at http://localhost:5173.

## Usage
Simply navigate to the frontend URL, enter your circuit requirements, and the backend will process the placement and routing locally without any external queues!
