"""
design_worker.py
Background worker that runs the PCB design pipeline as a FastAPI background task.
Publishes progress events to the in-memory state manager so the WebSocket endpoint
can stream them to the browser canvas.
"""
import asyncio
import traceback
import json

from backend.core.redis_client import redis_client


async def run_design_pipeline(job_id: str, request: dict):
    """
    Entry point called by FastAPI BackgroundTasks.
    Invokes the real design engine pipeline; if anything fails
    it publishes an error event so the frontend is always notified.
    """
    async def publish(event: dict):
        await redis_client.publish_event(job_id, event)

    try:
        await publish({"status": "running", "step": "parsing", "progress": 5})

        # Import lazily so import errors are caught gracefully
        from backend.design_engine.parser import parse_prompt

        prompt  = request.get("prompt", "")
        board_w = request.get("board_width_mm", 100)
        board_h = request.get("board_height_mm", 100)

        # 1. Parse components from natural-language prompt
        await publish({"status": "running", "step": "parsing", "progress": 15})
        parsed = parse_prompt(prompt)
        components = parsed.get("components", [])
        connections = parsed.get("connections", [])

        await publish({"status": "running", "step": "placement", "progress": 40})
        # Placement coordinates already calculated inside parse_prompt.
        # If a future dedicated placement engine is needed, hook it here.
        placements = [
            {
                "ref": c["ref"],
                "x":   c["x"],
                "y":   c["y"],
                "w":   c["w"],
                "h":   c["h"],
                "type": c["type"],
                "color": c["color"],
                "footprint": c["footprint"],
                "value": c["value"],
            }
            for c in components
        ]

        # 3. Build trace list from connections (pixel-level, centre-to-centre)
        await publish({"status": "running", "step": "routing", "progress": 70})
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

        result = {
            "placements":      placements,
            "connections":     connections,
            "traces":          traces,
            "board_width_mm":  board_w,
            "board_height_mm": board_h,
        }
        await publish({"status": "complete", "progress": 100, "result": result})

    except Exception as exc:
        tb = traceback.format_exc()
        await publish({"status": "error", "message": str(exc), "traceback": tb})
