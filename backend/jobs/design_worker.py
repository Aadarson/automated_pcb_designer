import os
import asyncio
import logging
from pathlib import Path
from backend.core.database import db
from backend.core.redis_client import redis_client
from backend.core.config import settings
from backend.kicad.project_generator import generate_kicad_project
from backend.models.design import PCBDesignRequest

logger = logging.getLogger(__name__)

from backend.design_engine.parser import parse_prompt
from backend.kicad.footprint_resolver import resolver
from backend.design_engine.placement import run_placement
from backend.design_engine.router import run_router
from backend.kicad.exporter import export_kicad_pcb
from backend.kicad.schematic_writer import write_schematic
from backend.kicad.netlist_writer import write_netlist
from backend.kicad.drc_runner import run_drc
from backend.kicad.gerber_writer import generate_gerber_bundle
from backend.ml_engine.smart_judge import judge

async def run_design_pipeline(job_id: str, request_dict: dict):
    try:
        await redis_client.publish_event(job_id, {"step": "parsing", "progress": 10})
        
        # 1. Universal Prompt Parser Rule
        prompt = request_dict.get("prompt", "")
        parsed_data = parse_prompt(prompt)
        
        if not request_dict.get("components"):
            request_dict["components"] = parsed_data["components"]
        if not request_dict.get("nets"):
            request_dict["nets"] = parsed_data["nets"]
            
        request = PCBDesignRequest(**request_dict)

        # SAFETY GATES (INITIAL)
        if len(request.nets) < 2:
            raise ValueError("Net count gate failure — at least 2 nets required.")
        
        for comp in request.components:
            if not resolver.resolve(comp.footprint):
                raise ValueError(f"Footprint validation failure: {comp.footprint}")

        async def execute_task():
            os.makedirs(settings.STORAGE_PATH, exist_ok=True)
            project_dir = Path(settings.STORAGE_PATH) / job_id
            project_dir.mkdir(parents=True, exist_ok=True)
            pcb_path = project_dir / f"{request.project_name}.kicad_pcb"
            
            max_epochs = 3
            placements, traces, unrouted, drc_report = [], [], [], None
            
            from backend.ml_engine.rl_agent import rl_router_agent
            rl_router_agent.reset_episode()

            for epoch in range(1, max_epochs + 1):
                await redis_client.publish_event(job_id, {"step": "placement", "status": f"epoch {epoch}", "progress": 30 + epoch*10})
                placements = run_placement(request)
                
                # Placement Spread Check
                xs = [p.x for p in placements]
                ys = [p.y for p in placements]
                coverage = ((max(xs)-min(xs))*(max(ys)-min(ys))) / (request.board.width_mm * request.board.height_mm)
                if coverage < 0.2: logger.warning("Spread check failure - clustering detected.")

                traces, unrouted = run_router(request, placements)
                export_kicad_pcb(job_id, request, placements, traces, str(pcb_path))
                
                drc_report = run_drc(pcb_path)
                violations = getattr(drc_report, 'violations', [])
                if not violations: break
                rl_router_agent.learn_from_drc(violations)

            # Final Gates
            if request.routing_goals.fill_copper:
                with open(pcb_path, 'r') as f:
                    if "(zone" not in f.read():
                        logger.error("Copper pour gate failure - no zones found.")

            zip_path = generate_kicad_project(project_dir, request.project_name)
            gerber_zip = generate_gerber_bundle(str(pcb_path), str(project_dir))
            
            result = {
                "pcb_file": f"/exports/{job_id}/{request.project_name}.kicad_pcb",
                "zip_file": f"/exports/{job_id}/{zip_path.name}",
                "gerber_file": f"/exports/{job_id}/{gerber_zip}" if gerber_zip else None,
                "drc_report": {"passed": not violations, "violations": [v.dict() for v in violations]},
                "unrouted": unrouted,
                "placement_score": 0.85, # placeholder
                "routing_completion": (len(request.nets)-len(unrouted))/len(request.nets) if request.nets else 0
            }
            return result

        # 10. Timeout Handling (90s)
        try:
            final_result = await asyncio.wait_for(execute_task(), timeout=90.0)
            await redis_client.publish_event(job_id, {"step": "done", "progress": 100, "status": "complete", "result": final_result})
        except asyncio.TimeoutError:
            await redis_client.publish_event(job_id, {"step": "partial", "progress": 90, "status": "partial", "error": "Job timed out (90s)"})

    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        await redis_client.publish_event(job_id, {"step": "error", "progress": 100, "status": "error", "error": str(e)})
