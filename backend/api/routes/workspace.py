"""
workspace.py
WebSocket route for the live PCB editor workspace.
Handles copilot prompts, component moves, and canvas clear events.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.core.state_manager import manager
from backend.design_engine.parser import parse_prompt
import json
import asyncio

router = APIRouter()


def _build_canvas_state(parsed: dict) -> dict:
    """Convert parser output to a full canvas-ready state dict."""
    components = parsed.get("components", [])
    connections = parsed.get("connections", [])

    # Build pixel-level traces from connections using component center coords
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

    return {
        "components": components,
        "connections": connections,
        "traces": traces,
    }


@router.websocket("/{project_id}/ws")
async def workspace_ws(websocket: WebSocket, project_id: str):
    await manager.connect(websocket, project_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            # ── Copilot: User typed a circuit prompt ─────────────────────────
            if msg_type == "copilot_prompt":
                prompt = message.get("prompt", "").strip()
                if not prompt:
                    await websocket.send_json({
                        "type": "copilot_response",
                        "text": "Please describe a circuit to generate."
                    })
                    continue

                # Acknowledge immediately
                await websocket.send_json({
                    "type": "copilot_response",
                    "text": f"⚡ Generating layout for: \"{prompt}\"…"
                })

                # Run parser (CPU-bound but fast enough for background)
                try:
                    parsed = await asyncio.get_event_loop().run_in_executor(
                        None, parse_prompt, prompt
                    )
                    canvas_state = _build_canvas_state(parsed)
                    component_count = len(canvas_state["components"])
                    connection_count = len(canvas_state["connections"])

                    # Persist state
                    manager.workspaces[project_id].update(canvas_state)

                    # Broadcast real design to canvas
                    await manager.broadcast_update(project_id, canvas_state)

                    # Send confirmation message
                    comp_names = ", ".join(
                        f"{c['ref']} ({c['type']})"
                        for c in canvas_state["components"]
                    )
                    await websocket.send_json({
                        "type": "copilot_response",
                        "text": (
                            f"✅ Placed {component_count} components with "
                            f"{connection_count} connections.\n"
                            f"Components: {comp_names}\n"
                            f"You can drag components to rearrange them."
                        )
                    })

                except Exception as exc:
                    await websocket.send_json({
                        "type": "copilot_response",
                        "text": f"⚠️ Generation failed: {exc}. Showing default circuit."
                    })
                    from backend.design_engine.parser import DEFAULT_FALLBACK_CIRCUIT
                    fallback_state = _build_canvas_state(DEFAULT_FALLBACK_CIRCUIT)
                    manager.workspaces[project_id].update(fallback_state)
                    await manager.broadcast_update(project_id, fallback_state)

            # ── Component dragged on the canvas ───────────────────────────────
            elif msg_type == "component_move":
                comp_id = message.get("component_id")
                new_x = message.get("x", 0)
                new_y = message.get("y", 0)

                workspace = manager.workspaces.get(project_id, {})
                components = workspace.get("components", [])
                connections = workspace.get("connections", [])

                # Update position
                for c in components:
                    if c["id"] == comp_id:
                        c["x"] = new_x
                        c["y"] = new_y
                        break

                # Recompute traces after move
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

                updated = {"components": components, "connections": connections, "traces": traces}
                manager.workspaces[project_id].update(updated)
                await manager.broadcast_update(project_id, updated)

            # ── Clear canvas ──────────────────────────────────────────────────
            elif msg_type == "clear_canvas":
                cleared = {"components": [], "connections": [], "traces": []}
                manager.workspaces[project_id].update(cleared)
                await manager.broadcast_update(project_id, cleared)
                await websocket.send_json({
                    "type": "copilot_response",
                    "text": "Canvas cleared. Describe a new circuit to start."
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)
