import asyncio
from backend.models.design import PCBDesignRequest
from backend.design_engine.placement import run_placement
from backend.ml_engine.trainer import get_rl_placement
from backend.design_engine.router import run_router
from backend.kicad.drc_runner import run_drc
from backend.kicad.exporter import export_kicad_pcb
import os
import shutil

async def compare_sa_and_rl():
    request_dict = {
        "project_name": "AntigravityTest",
        "prompt": "Arduino Uno clone with a ch340g, 4 leds, 2 resistors, and a usb c port.",
        "board": {"width_mm": 60, "height_mm": 60, "layers": 2, "outline": "rect"},
        "components": [
            {"ref": "U1", "value": "CH340G", "part_id": "CH340", "footprint": "Package_SO:SOIC-16_3.9x9.9mm_P1.27mm"},
            {"ref": "D1", "value": "LED", "part_id": "LED", "footprint": "LED_SMD:LED_0805_2012Metric"},
            {"ref": "D2", "value": "LED", "part_id": "LED", "footprint": "LED_SMD:LED_0805_2012Metric"}
        ],
        "nets": [
            {"name": "GND", "class": "power", "pins": [{"ref": "U1", "pin": "1"}, {"ref": "D1", "pin": "1"}]}
        ],
        "rules": {}, "routing_goals": {}
    }
    request = PCBDesignRequest(**request_dict)
    
    print("--- Running Simulated Annealing ---")
    sa_plcs = run_placement(request)
    
    # Check SA violations
    os.makedirs("test_sa", exist_ok=True)
    export_kicad_pcb("sa_job", request, sa_plcs, [], "test_sa/test.kicad_pcb")
    drc_sa = run_drc("test_sa/test.kicad_pcb")
    print(f"SA Violations: {len(drc_sa.violations)}")
    
    print("--- Running RL Engine (initialized with SA) ---")
    rl_plcs = get_rl_placement(request, sa_plcs)
    
    os.makedirs("test_rl", exist_ok=True)
    export_kicad_pcb("rl_job", request, rl_plcs, [], "test_rl/test.kicad_pcb")
    drc_rl = run_drc("test_rl/test.kicad_pcb")
    print(f"RL Violations: {len(drc_rl.violations)}")

if __name__ == "__main__":
    asyncio.run(compare_sa_and_rl())
