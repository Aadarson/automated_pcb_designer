import logging
import sys
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

from backend.models.design import PCBDesignRequest, BoardSpec
from backend.design_engine.parser import parse_prompt
from backend.design_engine.placement import run_placement
from backend.design_engine.router import run_router
from backend.kicad_bridge.exporter import export_kicad_pcb
from backend.kicad_bridge.drc_runner import run_drc
from backend.ml_engine.rl_agent import rl_router_agent

def run_rl_validation():
    try:
        prompt = "Design a 2-layer Arduino Uno motor driver shield with two L298N dual H-bridge motor driver ICs for controlling 4 DC motors, 100nF decoupling capacitors on each L298N power pin, a 7805 5V voltage regulator for logic power, 470uF bulk capacitor on the 12V motor supply rail, flyback diodes on all motor output pins, screw terminal connectors for motor outputs, and a 2x8 pin header for Arduino stacking. Include GND and VCC copper pours."
        
        parsed = parse_prompt(prompt)
        
        request = PCBDesignRequest(
            prompt=prompt,
            project_name="rl_validation_test",
            board=BoardSpec(width_mm=80, height_mm=80),
            layers=2,
            components=parsed["components"],
            nets=parsed["nets"]
        )
        
        logger.info(f"Loaded {len(request.components)} components natively from parser.")
        out_pcb = "rl_validation.kicad_pcb"
        
        max_epochs = 3
        rl_router_agent.reset_episode()
        
        for epoch in range(1, max_epochs + 1):
            logger.info(f"\n--- EPOCH {epoch} ---")
            
            placements = run_placement(request)
            traces, unrouted = run_router(request, placements)
            export_kicad_pcb("test_job", request, placements, traces, out_pcb)
            
            logger.info("Running KiCad CLI DRC check...")
            drc_report = run_drc(out_pcb)
            
            violations = getattr(drc_report, 'violations', [])
            errors = [v for v in violations if getattr(v, 'severity', '') == 'error']
            
            if len(violations) == 0:
                logger.info(f"SUCCESS: 0 DRC Violations (Errors + Warnings) found on Epoch {epoch}!")
                break
            else:
                logger.warning(f"Validation found {len(errors)} Errors and {len(violations)-len(errors)} Warnings.")
                # We will print the raw json to see where the coordinates are hidden
                import subprocess
                subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--output", "raw_drc.json", "rl_validation.kicad_pcb"])
                logger.info(open("raw_drc.json").read())
                break

    except Exception as e:
        logger.exception("Validation failed")

if __name__ == "__main__":
    run_rl_validation()
