from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
        logger.info(f"Client joined collaboration room: {room_id}")

    def disconnect(self, room_id: str, websocket: WebSocket):
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def broadcast(self, room_id: str, message: bytes, sender: WebSocket):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                if connection != sender:
                    await connection.send_bytes(message)

manager = ConnectionManager()

@router.websocket("/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(room_id, websocket)
    try:
        while True:
            # Yjs binary updates are received as bytes
            data = await websocket.receive_bytes()
            await manager.broadcast(room_id, data, websocket)
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
        logger.info(f"Client left collaboration room: {room_id}")
