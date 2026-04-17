import sys
from pathlib import Path
sys.path.append(str(Path.cwd()))

from backend.kicad_bridge.footprint_resolver import resolver
from backend.models.design import PCBDesignRequest, Component, Net, NetPin, BoardSpec
from backend.design_engine.router import run_router
from backend.design_engine.placement import PlacedComponent

def test():
    # Simulate a small Arduino request
    request = PCBDesignRequest(
        prompt="Arduino Nano with LED",
        project_name="Test",
        components=[
            Component(ref="U1", part_id="Nano", footprint="Arduino_Nano", value="Nano"),
            Component(ref="D1", part_id="LED", footprint="LED_0805", value="Red")
        ],
        nets=[
            Net(name="N1", pins=[NetPin(ref="U1", pin="1"), NetPin(ref="D1", pin="1")]),
            Net(name="GND", pins=[NetPin(ref="U1", pin="4"), NetPin(ref="D1", pin="2")])
        ],
        board=BoardSpec(width_mm=50, height_mm=50, layers=2)
    )
    
    placements = [
        PlacedComponent(ref="U1", x=25, y=25, rotation=0, layer="F.Cu", w=43, h=18, cx=0, cy=0),
        PlacedComponent(ref="D1", x=10, y=10, rotation=0, layer="F.Cu", w=3, h=2, cx=0, cy=0)
    ]
    
    print("Running router with diagnostic logging...")
    traces, unrouted = run_router(request, placements)
    print(f"Generated {len(traces)} traces.")
    print(f"Unrouted: {unrouted}")
    
    # Check if Pad 2 of U1 (not in N1) was an obstacle for N1
    # We'd need to add logging inside router.py to see this.

if __name__ == "__main__":
    test()
