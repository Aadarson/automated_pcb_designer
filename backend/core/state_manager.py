"""
state_manager.py
In-memory workspace state and WebSocket connection manager.
"""
from typing import Dict, Any, List


# Color palette for each component type — used when initialising workspaces
COMPONENT_COLORS = {
    "MCU":        "#312e81",
    "IC":         "#1c1c3b",
    "LED":        "#065f46",
    "Resistor":   "#7c2d12",
    "Capacitor":  "#1e3a5f",
    "Battery":    "#78350f",
    "Connector":  "#3b1f6a",
    "Switch":     "#1a3a2a",
    "Relay":      "#3b2a1a",
    "Transistor": "#2a1a3b",
    "Diode":      "#1a2a3b",
    "Sensor":     "#1a3b2a",
}

# Default workspace shown until first copilot prompt
DEFAULT_COMPONENTS = [
    {"id": "U1",  "type": "MCU",      "ref": "U1",  "x": 395, "y": 270, "w": 70, "h": 50, "color": "#312e81", "pins": ["VCC","GND","GPIO1","GPIO2"], "footprint": "RF_Module:ESP32-WROOM-32",               "value": "ESP32"},
    {"id": "R1",  "type": "Resistor", "ref": "R1",  "x": 570, "y": 210, "w": 38, "h": 18, "color": "#7c2d12", "pins": ["1","2"],                    "footprint": "Resistor_SMD:R_0805_2012Metric",           "value": "10k"},
    {"id": "D1",  "type": "LED",      "ref": "D1",  "x": 660, "y": 340, "w": 28, "h": 18, "color": "#065f46", "pins": ["A","K"],                    "footprint": "LED_SMD:LED_0805_2012Metric",               "value": "LED"},
    {"id": "BT1", "type": "Battery",  "ref": "BT1", "x": 140, "y": 340, "w": 36, "h": 24, "color": "#78350f", "pins": ["+","-"],                    "footprint": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", "value": "9V"},
]

DEFAULT_CONNECTIONS = [
    {"from": "BT1.+",    "to": "U1.VCC",   "net": "VCC"},
    {"from": "BT1.-",    "to": "U1.GND",   "net": "GND"},
    {"from": "U1.GPIO1", "to": "R1.1",     "net": "NET1"},
    {"from": "R1.2",     "to": "D1.A",     "net": "NET1"},
    {"from": "D1.K",     "to": "U1.GND",   "net": "GND"},
]


def _build_traces(components: list, connections: list) -> list:
    pos_map = {c["id"]: c for c in components}
    traces = []
    for conn in connections:
        src_ref = conn["from"].split(".")[0]
        dst_ref = conn["to"].split(".")[0]
        src = pos_map.get(src_ref)
        dst = pos_map.get(dst_ref)
        if src and dst:
            traces.append({
                "x1": src["x"] + src["w"] // 2,
                "y1": src["y"] + src["h"] // 2,
                "x2": dst["x"] + dst["w"] // 2,
                "y2": dst["y"] + dst["h"] // 2,
                "net": conn.get("net", ""),
            })
    return traces


class WorkspaceStateManager:
    def __init__(self):
        # Maps project_id → state dict
        self.workspaces: Dict[str, Dict[str, Any]] = {}
        # Maps project_id → list of active WebSocket connections
        self.connections: Dict[str, List[Any]] = {}

    def get_or_create_workspace(self, project_id: str) -> Dict[str, Any]:
        if project_id not in self.workspaces:
            traces = _build_traces(DEFAULT_COMPONENTS, DEFAULT_CONNECTIONS)
            self.workspaces[project_id] = {
                "components":  list(DEFAULT_COMPONENTS),
                "connections": list(DEFAULT_CONNECTIONS),
                "traces":      traces,
            }
            self.connections[project_id] = []
        return self.workspaces[project_id]

    async def connect(self, websocket: Any, project_id: str):
        await websocket.accept()
        state = self.get_or_create_workspace(project_id)
        self.connections[project_id].append(websocket)
        # Send full initial state to newly connected client
        await websocket.send_json({"type": "init", "state": state})

    def disconnect(self, websocket: Any, project_id: str):
        if project_id in self.connections:
            try:
                self.connections[project_id].remove(websocket)
            except ValueError:
                pass

    async def broadcast_update(self, project_id: str, diff: Dict[str, Any]):
        """Apply a diff to workspace state and broadcast to all clients."""
        state = self.workspaces.get(project_id)
        if not state:
            return

        for k, v in diff.items():
            state[k] = v

        dead = []
        for conn in self.connections.get(project_id, []):
            try:
                await conn.send_json({"type": "update", "state": state})
            except Exception:
                dead.append(conn)

        # Clean up dead connections
        for conn in dead:
            try:
                self.connections[project_id].remove(conn)
            except ValueError:
                pass


manager = WorkspaceStateManager()
