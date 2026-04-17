"""
design_worker.py
Stub worker that runs the PCB design pipeline as a FastAPI background task.
Publishes progress events to the in-memory redis client so the WS endpoint
can stream them to the browser.
"""
import asyncio
import traceback
import json

from backend.core.redis_client import redis_client


async def run_design_pipeline(job_id: str, request: dict):
    """
    Entry point called by FastAPI BackgroundTasks.
    Tries to invoke the real design engine pipeline; if anything fails
    it publishes an error event so the frontend is always notified.
    """
    async def publish(event: dict):
        await redis_client.publish_event(job_id, event)

    try:
        await publish({"status": "running", "step": "parsing", "progress": 5})

        # --- Import the real pipeline pieces lazily so import errors are caught ---
        from backend.design_engine.parser    import PCBDesignParser
        from backend.design_engine.placement import ComponentPlacer
        from backend.design_engine.router    import PCBRouter

        prompt     = request.get("prompt", "")
        board_w    = request.get("board_width_mm",  100)
        board_h    = request.get("board_height_mm", 100)

        # 1. Parse components from natural-language prompt
        await publish({"status": "running", "step": "parsing", "progress": 15})
        parser     = PCBDesignParser()
        components = parser.extract_components(prompt)

        # 2. Place components on board
        await publish({"status": "running", "step": "placement", "progress": 40})
        placer     = ComponentPlacer(board_width=board_w, board_height=board_h)
        placements = placer.place(components)

        # 3. Route traces
        await publish({"status": "running", "step": "routing", "progress": 70})
        router     = PCBRouter(board_width=board_w, board_height=board_h)
        traces, unrouted = router.route(placements)

        # 4. Done
        result = {
            "placements": placements,
            "traces":     traces,
            "unrouted":   unrouted,
            "board_width_mm":  board_w,
            "board_height_mm": board_h,
        }
        await publish({"status": "complete", "progress": 100, "result": result})

    except Exception as exc:
        tb = traceback.format_exc()
        await publish({"status": "error", "message": str(exc), "traceback": tb})
