from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.api.routes import design, auth, projects, workspace
from backend.core.database import db
from backend.core.config import settings
import os
import mimetypes

# Register KiCad MIME types
mimetypes.add_type('application/x-kicad-pcb', '.kicad_pcb')
mimetypes.add_type('application/x-kicad-netlist', '.net')

app = FastAPI(title="Automated PCB Designer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create storage directory if it doesn't exist
os.makedirs(settings.STORAGE_PATH, exist_ok=True)

# Mount exports directory to serve generated files
app.mount("/exports", StaticFiles(directory=settings.STORAGE_PATH), name="exports")

app.include_router(design.router, prefix="/api/v1/design", tags=["design"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(workspace.router, prefix="/api/v1/workspace", tags=["workspace"])

@app.on_event("startup")
async def startup_db_client():
    await db.connect()

@app.on_event("shutdown")
async def shutdown_db_client():
    await db.disconnect()

@app.get("/")
def read_root():
    return {"status": "ok"}
