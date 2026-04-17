import logging
import sys
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

sys.path.append(str(Path.cwd()))

from backend.models.design import PCBDesignRequest, BoardSpec, Component
from backend.design_engine.parser import parse_prompt
from backend.design_engine.placement import run_placement
from backend.design_engine.router import run_router
from backend.kicad_bridge.exporter import export_kicad_pcb
from backend.kicad_bridge.drc_runner import run_drc

def run_test():
    try:
        prompt = "Connect 3 ESP32s, 5 1k resistors, and 5 LEDs on a 100x100mm board."
        
        request = PCBDesignRequest(
            prompt=prompt,
            project_name="drc_self_test",
            board=BoardSpec(width_mm=100, height_mm=100),
            layers=2
        )
        
        # 1. Parse
        parsed = parse_prompt(prompt)
        # Override to ensure we have a dense board for testing DRC overlaps
        request.components = [
            Component(ref="U1", part_id="ESP32", footprint="RF_Module:ESP32-WROOM-32", value="ESP32"),
            Component(ref="U2", part_id="ESP32", footprint="RF_Module:ESP32-WROOM-32", value="ESP32"),
            Component(ref="R1", part_id="1K", footprint="Resistor_SMD:R_0805_2012Metric", value="1K"),
            Component(ref="R2", part_id="1K", footprint="Resistor_SMD:R_0805_2012Metric", value="1K"),
            Component(ref="D1", part_id="LED", footprint="LED_SMD:LED_0805_2012Metric", value="LED Green"),
            Component(ref="D2", part_id="LED", footprint="LED_SMD:LED_0805_2012Metric", value="LED Red"),
        ]
        
        # 2. Place
        logger.info("Running placement...")
        placements = run_placement(request)
        for p in placements:
            logger.info(f"Placed {p.ref} at ({p.x:.2f}, {p.y:.2f})")
            
        # 3. Route
        logger.info("Running router...")
        traces, unrouted = run_router(request, placements)
        
        # 4. Export
        out_pcb = "drc_self_test.kicad_pcb"
        logger.info(f"Exporting to {out_pcb}...")
        export_kicad_pcb("test_job", request, placements, traces, out_pcb)
        
        # 5. Run DRC
        logger.info("Running KiCad CLI DRC...")
        drc_report = run_drc(out_pcb)
        
        violations = drc_report.violations if hasattr(drc_report, 'violations') else []
        unconnected = drc_report.unconnected_items if hasattr(drc_report, 'unconnected_items') else []
        
        print("\n--- TEST RESULTS ---")
        print(f"Total Violations: {len(violations)}")
        print(f"Total Unconnected: {len(unconnected)}")
        
        for v in violations:
            print(f"- {getattr(v, 'error_type', 'Unknown')}: {getattr(v, 'description', '')}")
            
    except Exception as e:
        logger.exception("Test failed")

if __name__ == "__main__":
    run_test()
