import uuid
from typing import Optional
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, BackgroundTasks
from backend.models.design import PCBDesignRequest, PCBDesignResponse
from backend.models.user import User
from backend.auth.jwt_handler import get_current_user, get_current_user_optional
from backend.jobs.design_worker import run_design_pipeline
from backend.core.database import db
from backend.core.redis_client import redis_client

router = APIRouter()

JOBS = {}

@router.post("/", response_model=PCBDesignResponse)
async def create_design(request: PCBDesignRequest, background_tasks: BackgroundTasks, current_user: Optional[User] = Depends(get_current_user_optional)):
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "queued", "progress": 0}
    
    background_tasks.add_task(run_design_pipeline, job_id, request.dict())
    return PCBDesignResponse(job_id=job_id, status="queued")

@router.get("/{job_id}", response_model=PCBDesignResponse)
async def get_design_status(job_id: str, current_user: Optional[User] = Depends(get_current_user_optional)):
    job = redis_client.latest_status.get(job_id, {"status": "running", "progress": 0})
    return PCBDesignResponse(job_id=job_id, **job)

@router.websocket("/{job_id}/ws")
async def design_websocket(websocket: WebSocket, job_id: str):
    await websocket.accept()
    channel = f"job:{job_id}:events"
    pubsub = await redis_client.get_subscriber(channel)
    
    try:
        async for message in pubsub.listen():
            if message['type'] == 'message':
                data = message['data']
                await websocket.send_text(data)
                
                # Close string match (because data is a string literal containing json)
                if '"complete"' in data or '"error"' in data:
                    break
    except WebSocketDisconnect:
        pass
