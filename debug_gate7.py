from backend.design_engine.placement import PlacementEngine, PlacedComponent
from backend.models.design import PCBDesignRequest, BoardSpec, Component, Net

request = PCBDesignRequest(
    project_name="Debug",
    prompt="ESP32",
    board=BoardSpec(width_mm=50, height_mm=40, layers=2),
    components=[Component(ref="U1", part_id="ESP32", footprint="ESP32-WROOM-32", value="ESP32")],
    nets=[Net(id=1, name="GND", **{"class": "power"}, pins=[]), Net(id=2, name="VCC", **{"class": "power"}, pins=[])]
)

engine = PlacementEngine(request)
placements = engine.run()

for p in placements:
    bb = p.get_bbox()
    print(f"Component {p.ref}: pos=({p.x}, {p.y}), size=({p.w}, {p.h}), cx={p.cx}, cy={p.cy}")
    print(f"  BBox: {bb}")
    margin = 0.5
    t1 = bb[0] < -margin
    t2 = bb[1] < -margin
    t3 = bb[2] > request.board.width_mm + margin
    t4 = bb[3] > request.board.height_mm + margin
    print(f"  Terms: {t1}, {t2}, {t3}, {t4} (Board: {request.board.width_mm}x{request.board.height_mm})")
    outside = t1 or t2 or t3 or t4
    print(f"  Outside Board: {outside}")
