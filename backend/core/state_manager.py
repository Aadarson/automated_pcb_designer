from typing import Dict, Any, List
import asyncio
import json

class WorkspaceStateManager:
    def __init__(self):
        # Maps project_id -> state dict
        self.workspaces: Dict[str, Dict[str, Any]] = {}
        # Maps project_id -> list of active websocket connections
        self.connections: Dict[str, List[Any]] = {}

    def get_or_create_workspace(self, project_id: str) -> Dict[str, Any]:
        if project_id not in self.workspaces:
            self.workspaces[project_id] = {
                "components": [
                    {"id": "U1", "x": 100, "y": 100, "w": 40, "h": 40, "ref": "MCU", "color": "#1f2937"},
                    {"id": "D1", "x": 200, "y": 150, "w": 20, "h": 10, "ref": "LED", "color": "#1f2937"}
                ],
                "traces": [],
                "schematic_nodes": [],
                "schematic_edges": []
            }
            self.connections[project_id] = []
        return self.workspaces[project_id]

    async def connect(self, websocket: Any, project_id: str):
        await websocket.accept()
        self.get_or_create_workspace(project_id)
        self.connections[project_id].append(websocket)
        # Send initial state
        await websocket.send_json({
            "type": "init",
            "state": self.workspaces[project_id]
        })

    def disconnect(self, websocket: Any, project_id: str):
        if project_id in self.connections:
            if websocket in self.connections[project_id]:
                self.connections[project_id].remove(websocket)

    async def broadcast_update(self, project_id: str, diff: Dict[str, Any]):
        """Apply a diff and broadcast to all connected clients"""
        state = self.workspaces.get(project_id)
        if not state:
            return

        # Simple merge for now
        for k, v in diff.items():
            state[k] = v

        if project_id in self.connections:
            for conn in self.connections[project_id]:
                try:
                    await conn.send_json({
                        "type": "update",
                        "state": state
                    })
                except:
                    # Ignore dead connections
                    pass

manager = WorkspaceStateManager()
