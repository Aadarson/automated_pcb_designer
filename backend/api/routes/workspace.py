from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.core.state_manager import manager
import json
import asyncio

router = APIRouter()

@router.websocket("/{project_id}/ws")
async def workspace_ws(websocket: WebSocket, project_id: str):
    await manager.connect(websocket, project_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle incoming edits or copilot messages
            if message.get("type") == "copilot_prompt":
                prompt = message.get("prompt", "")
                
                # Mock AI generating a response and updating the board
                # In reality, this would call ml_engine and stream updates
                await websocket.send_json({
                    "type": "copilot_response",
                    "text": f"Got it! Generating circuit for: {prompt}..."
                })
                
                await asyncio.sleep(1.5)
                
                new_state_diff = {
                    "components": manager.workspaces[project_id]["components"] + [
                        {"id": f"NEW_{len(manager.workspaces[project_id]['components'])}", "x": 300, "y": 200, "w": 30, "h": 30, "ref": "New_IC", "color": "#1f2937"}
                    ]
                }
                
                await websocket.send_json({
                    "type": "copilot_response",
                    "text": "Component placed on canvas!"
                })
                await manager.broadcast_update(project_id, new_state_diff)
            
            elif message.get("type") == "component_move":
                # Handle drag/drop update
                # Diff would be just the component moving
                components = manager.workspaces[project_id]["components"]
                updated_comps = []
                for c in components:
                    if c["id"] == message["component_id"]:
                        c["x"] = message["x"]
                        c["y"] = message["y"]
                    updated_comps.append(c)
                
                await manager.broadcast_update(project_id, {"components": updated_comps})
            
            elif message.get("type") == "clear_canvas":
                # Clear all components and traces
                await manager.broadcast_update(project_id, {
                    "components": [],
                    "traces": []
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)
