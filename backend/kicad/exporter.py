import logging
import uuid
from pathlib import Path
from kiutils.board import Board
from kiutils.items.gritems import GrLine
from kiutils.items.common import Position
from kiutils.footprint import Footprint
from kiutils.items.brditems import Segment
from kiutils.items.fpitems import FpText
from backend.kicad_bridge.footprint_resolver import resolver

logger = logging.getLogger(__name__)

def export_kicad_pcb(job_id: str, request, placements, traces, output_path: str):
    logger.info(f"Exporting KiCad PCB to {output_path}")
    
    board = Board.create_new()
    
    # 1. Add Board Outline (Edge.Cuts) from normalized request
    bw = request.board.width_mm
    bh = request.board.height_mm
    outline = [
        GrLine(start=Position(0,0), end=Position(bw,0), layer="Edge.Cuts"),
        GrLine(start=Position(bw,0), end=Position(bw,bh), layer="Edge.Cuts"),
        GrLine(start=Position(bw,bh), end=Position(0,bh), layer="Edge.Cuts"),
        GrLine(start=Position(0,bh), end=Position(0,0), layer="Edge.Cuts"),
    ]
    board.graphicItems.extend(outline)
    
    # 2. Build Netlist Map (Universal Net Rule)
    from kiutils.items.common import Net as KiNet
    board.nets = [KiNet(number=0, name="<no net>")]
    
    # Identify GND and VCC for fixed IDs
    p_nets = request.nets
    gnd_net = next((n for n in p_nets if n.name.upper() == "GND"), None)
    vcc_net = next((n for n in p_nets if n.name.upper() in ["VCC", "5V", "3.3V", "3V3", "VIN"]), None)
    other_nets = [n for n in p_nets if n != gnd_net and n != vcc_net]
    
    ordered_nets = []
    if gnd_net: ordered_nets.append(gnd_net)
    if vcc_net: ordered_nets.append(vcc_net)
    ordered_nets.extend(other_nets)
    
    net_map = {} # map net.name -> Net object
    pad_to_net = {} # map (ref, pin_number) -> Net object
    
    for i, pnet in enumerate(ordered_nets, start=1):
        kicad_net = KiNet(number=i, name=pnet.name)
        board.nets.append(kicad_net)
        net_map[pnet.name] = kicad_net
        for pin in pnet.pins:
            pad_to_net[(pin.ref, str(pin.pin))] = kicad_net
            try:
                pad_to_net[(pin.ref, str(int(pin.pin)))] = kicad_net
            except: pass
            
    # 3. Add Footprints
    for p in placements:
        comp = next((c for c in request.components if c.ref == p.ref), None)
        if not comp: continue
        
        fp_path = resolver.resolve(comp.footprint)
        if fp_path and fp_path.exists():
            try:
                fp = Footprint.from_file(str(fp_path))
                cx = getattr(p, 'cx', 0.0)
                cy = getattr(p, 'cy', 0.0)
                # Position coordinates are already shifted by design_worker
                fp.position = Position(p.x - cx, p.y - cy)
                
                for item in fp.graphicItems:
                    if isinstance(item, FpText):
                        if item.type == 'reference':
                            item.text = p.ref
                        elif item.type == 'value':
                            item.text = comp.value
                
                # Bi-directional Net Padding mapping
                for pad in fp.pads:
                    pin_num = str(getattr(pad, 'number', ''))
                    assigned_net = pad_to_net.get((p.ref, pin_num))
                    if assigned_net:
                        pad.net = Net(number=assigned_net.number, name=assigned_net.name)

                
                fp.layer = p.layer
                fp.tstamp = str(uuid.uuid4())
                board.footprints.append(fp)
                logger.info(f"Added footprint {comp.ref} at {fp.position.X}, {fp.position.Y}")
            except Exception as e:
                logger.error(f"Failed to load footprint {comp.footprint} from {fp_path}: {e}")
        else:
            logger.warning(f"Could not resolve footprint path for {comp.ref}: {comp.footprint} (Path: {fp_path})")

    # 4. Add Tracks
    for t in traces:
        assigned_net = net_map.get(t.net_name)
        net_idx = assigned_net.number if assigned_net else 0
        
        for i in range(len(t.path_points) - 1):
            p1 = t.path_points[i]
            p2 = t.path_points[i+1]
            track = Segment(
                start=Position(p1[0], p1[1]),
                end=Position(p2[0], p2[1]),
                width=t.width_mm,
                layer=t.layer,
                net=net_idx,
                tstamp=str(uuid.uuid4())
            )
            board.traceItems.append(track)
            
    # 5. Add Copper Pours (Universal Copper Pour Rule)
    if getattr(request.routing_goals, 'fill_copper', True):
        from kiutils.items.brditems import Zone
        from kiutils.items.common import Position
        
        # Helper to create a full-board zone
        def add_full_zone(net_obj, layer):
            if not net_obj: return
            z = Zone()
            z.net = net_obj
            z.layer = layer
            z.tstamp = str(uuid.uuid4())
            # Full board outline vertices
            z.polygon.pts.extend([
                Position(0, 0), Position(bw, 0), Position(bw, bh), Position(0, bh)
            ])
            # Design Rules
            z.settings.clearance = 0.3
            z.settings.min_width = 0.4
            z.settings.thermal_gap = 0.5
            z.settings.thermal_bridge_width = 0.5
            board.zones.append(z)

        gnd_net_obj = net_map.get(ordered_nets[0].name) if ordered_nets and ordered_nets[0].name.upper() == "GND" else None
        vcc_net_obj = net_map.get(ordered_nets[1].name) if len(ordered_nets) > 1 and ordered_nets[1].name.upper() in ["VCC", "5V", "3.3V", "3V3", "VIN"] else None

        # GND on both layers
        add_full_zone(gnd_net_obj, "F.Cu")
        add_full_zone(gnd_net_obj, "B.Cu")
        
        # Primary Power (VCC) on B.Cu cluster (simplified to full layer for now as per "merging unused zones" logic)
        if vcc_net_obj:
            add_full_zone(vcc_net_obj, "B.Cu")

    # 6. Save the file
    board.to_file(output_path)
