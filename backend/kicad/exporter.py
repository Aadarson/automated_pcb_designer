import logging
import uuid
from pathlib import Path
from kiutils.board import Board
from kiutils.items.gritems import GrLine
from kiutils.items.common import Position, Net as KiNet
from kiutils.footprint import Footprint
from kiutils.items.brditems import Segment
from kiutils.items.fpitems import FpText
from kiutils.items.zones import Zone, ZonePolygon, FillSettings
from backend.kicad.footprint_resolver import resolver

logger = logging.getLogger(__name__)

def export_kicad_pcb(job_id: str, request, placements, traces, output_path: str):
    """
    Exports the generated pcb layout and traces into a standard KiCad 6.0+ .kicad_pcb file.
    Uses 'traceItems' for KiCad 9 compatibility.
    """
    logger.info(f"Exporting KiCad PCB to {output_path}")
    bw, bh = request.board.width_mm, request.board.height_mm
    
    board = Board.create_new()
    # Edge Cuts
    board.graphicItems.extend([
        GrLine(start=Position(0,0), end=Position(bw,0), layer="Edge.Cuts"),
        GrLine(start=Position(bw,0), end=Position(bw,bh), layer="Edge.Cuts"),
        GrLine(start=Position(bw,bh), end=Position(0,bh), layer="Edge.Cuts"),
        GrLine(start=Position(0,bh), end=Position(0,0), layer="Edge.Cuts"),
    ])

    # 1. Nets (KiCad 6+ Format)
    board.nets = [KiNet(number=0, name="<no net>")]
    net_map = {}
    for i, pnet in enumerate(request.nets, start=1):
        knet = KiNet(number=i, name=pnet.name)
        board.nets.append(knet)
        net_map[pnet.name] = knet

    # 2. Footprints
    for plc in placements:
        fp_path = resolver.resolve(plc.footprint)
        if not fp_path or not fp_path.exists():
            continue
            
        try:
            fp = Footprint().from_file(str(fp_path))
            fp.position = Position(plc.x, plc.y)
            fp.angle = plc.rotation
            fp.layer = plc.layer
            
            # Reference Designator
            for item in fp.graphicItems:
                if isinstance(item, FpText) and item.type == "reference":
                    item.text = plc.ref
                    item.position = Position(0, -2.0) 

            # Assign Nets to Pads (Electrical Connectivity Fix)
            ref_pin_to_net = {}
            for net in request.nets:
                for pin in net.pins:
                    if pin.ref == plc.ref:
                        ref_pin_to_net[str(pin.pin)] = net.name
            
            for pad in fp.pads:
                net_name = ref_pin_to_net.get(str(pad.number))
                if net_name:
                    knet = net_map.get(net_name)
                    if knet:
                        # Assign the entire Net object to the pad, not just the ID
                        pad.net = knet
                        logger.info(f"Assigned {plc.ref}.{pad.number} to net {knet.name}")

            board.footprints.append(fp)
        except Exception as e:
            logger.error(f"Error loading footprint {plc.footprint}: {e}")

    # 3. Tracks (Attribute Fix: using traceItems instead of 'tracks')
    trace_count = 0
    for trace in traces:
        knet = net_map.get(trace.net_name)
        if not knet: continue
        
        for i in range(len(trace.path) - 1):
            p1 = trace.path[i]
            p2 = trace.path[i+1]
            
            seg = Segment()
            seg.start = Position(p1[0], p1[1])
            seg.end = Position(p2[0], p2[1])
            seg.width = trace.width_mm
            seg.layer = trace.layer
            seg.net = knet.number
            seg.tstamp = str(uuid.uuid4())
            # For KiCad 6+, board.traceItems is the correct storage for segments
            if hasattr(board, 'traceItems'):
                board.traceItems.append(seg)
                trace_count += 1
            elif hasattr(board, 'tracks'):
                board.tracks.append(seg)
                trace_count += 1
    
    logger.info(f"Exported {trace_count} track segments to PCB.")

    # 4. Copper Pours
    def add_zone(net_name, layer, pts):
        net_obj = net_map.get(net_name)
        if not net_obj or not pts: return
        z = Zone()
        z.net = int(net_obj.number)
        z.netName = str(net_obj.name)
        z.layers = [layer]
        z.tstamp = str(uuid.uuid4())
        
        zp = ZonePolygon()
        zp.coordinates.extend([Position(p[0], p[1]) for p in pts])
        z.polygons.append(zp)
        
        z.fillSettings = FillSettings(yes=True)
        z.fillSettings.thermalGap, z.fillSettings.thermalBridgeWidth = 0.5, 0.5
        z.clearance, z.minThickness = 0.3, 0.4
        board.zones.append(z)

    if getattr(request.routing_goals, 'fill_copper', True):
        full_pts = [(0,0), (bw,0), (bw,bh), (0,bh)]
        add_zone("GND", "F.Cu", full_pts)
        add_zone("GND", "B.Cu", full_pts)

    # 5. Finalize
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)
    board.to_file(output_path)
    logger.info(f"Successfully saved PCB to {output_path} with {len(board.nets)} nets.")
