import math
import heapq
import logging
from typing import List, Tuple, Set, Dict
from backend.models.design import PCBDesignRequest

logger = logging.getLogger(__name__)

class Trace:
    def __init__(self, net_name: str, layer: str, path_points: List[Tuple[float, float]], width_mm: float):
        self.net_name = net_name
        self.layer = layer
        self.path_points = path_points
        self.width_mm = width_mm

def heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def a_star(start: Tuple[int, int], goal: Tuple[int, int], obstacles: Set[Tuple[int, int]], bounds: Tuple[int, int], thermal_keepouts: Set[Tuple[int, int]] = set()) -> List[Tuple[int, int]]:
    close_set = set()
    came_from = {}
    gscore = {start: 0}
    fscore = {start: heuristic(start, goal)}
    oheap = []

    heapq.heappush(oheap, (fscore[start], start))
    
    while oheap:
        current = heapq.heappop(oheap)[1]

        if current == goal:
            data = []
            while current in came_from:
                data.append(current)
                current = came_from[current]
            data.append(start)
            return data[::-1]

        close_set.add(current)
        for i, j in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            neighbor = (current[0] + i, current[1] + j)
            
            # Boundary check
            if not (0 <= neighbor[0] < bounds[0] and 0 <= neighbor[1] < bounds[1]):
                continue

            # Obstacle check: Allow goal node to be reached even if it's an "obstacle"
            if neighbor in obstacles and neighbor != goal:
                continue

            if neighbor in close_set:
                continue
                
            # Congestion-aware cost: Penalize nodes with many adjacent obstacles
            congestion_penalty = 0.0
            for ni, nj in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                if (neighbor[0] + ni, neighbor[1] + nj) in obstacles:
                    congestion_penalty += 0.5
                    
            from backend.ml_engine.rl_agent import rl_router_agent
            rl_penalty = rl_router_agent.get_penalty(neighbor[0], neighbor[1])
            
            thermal_penalty = 50.0 if neighbor in thermal_keepouts else 0.0
            
            tentative_g_score = gscore[current] + 1 + congestion_penalty + rl_penalty + thermal_penalty

            
            if neighbor not in gscore or tentative_g_score < gscore[neighbor]:
                came_from[neighbor] = current
                gscore[neighbor] = tentative_g_score
                fscore[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                heapq.heappush(oheap, (fscore[neighbor], neighbor))
                
    return []

def run_router(request: PCBDesignRequest, placements: List[any]) -> Tuple[List[Trace], List[str]]:
    logger.info("Running Advanced A* Router")
    traces = []
    unrouted_nets = []
    
    # Grid Setup (0.5mm)
    # 1. Prepare Grid
    grid_scale = 10.0 # 0.1mm grid for precision
    w_grid = int(request.board.width_mm * grid_scale)
    h_grid = int(request.board.height_mm * grid_scale)
    
    pos_map = {} # (ref, pin) -> (gx, gy)
    from backend.kicad_bridge.footprint_resolver import resolver
    comp_dict = {c.ref: c.footprint for c in request.components}
    
    thermal_keepouts = set()
    for p in placements:
        # Get exact physical pads relative to physical anchor
        fp_str = comp_dict.get(p.ref)
        pad_offsets = resolver.get_pad_offsets(fp_str) if fp_str else {}
        
        anchor_x = p.x - getattr(p, 'cx', 0.0)
        anchor_y = p.y - getattr(p, 'cy', 0.0)
        
        # If component is "Hot", mark its entire body as a high-cost zone for heat distribution
        if getattr(p, 'is_hot', False):
            gx_min, gx_max = int(anchor_x * grid_scale), int((anchor_x + p.w) * grid_scale)
            gy_min, gy_max = int(anchor_y * grid_scale), int((anchor_y + p.h) * grid_scale)
            for gx in range(gx_min - 5, gx_max + 6):
                for gy in range(gy_min - 5, gy_max + 6):
                    thermal_keepouts.add((gx, gy))

        for pin_num, (ox, oy) in pad_offsets.items():
            abs_x = anchor_x + ox
            abs_y = anchor_y + oy
            gx, gy = int(abs_x * grid_scale), int(abs_y * grid_scale)
            pos_map[(p.ref, pin_num)] = (gx, gy)
            
        pos_map[p.ref] = (int(p.x * grid_scale), int(p.y * grid_scale))
    
    logger.info(f"Built pos_map with {len(pos_map)} entries including pads.")

    # 2. Route each net
    global_trace_grid = {} # (gx, gy) -> net_name
    for net in request.nets:
        if net.net_class == 'power': continue
        
        if len(net.pins) < 2:
            unrouted_nets.append(net.name)
            continue
            
        # 3. Build obstacles explicitly for this net (excluding the specific target pads)
        net_obstacles = set()
        connected_pad_keys = {(pin.ref, str(pin.pin)) for pin in net.pins}
        
        # Add all other traces as obstacles (unless they belong to this net)
        for coord, mapped_net in global_trace_grid.items():
            if mapped_net != net.name:
                net_obstacles.add(coord)
        
        # Add all OTHER pads as obstacles
        for key, coord in pos_map.items():
            if isinstance(key, tuple):
                ref, pin_num = key
                if (ref, pin_num) not in connected_pad_keys:
                    gx_pad, gy_pad = coord
                    # Hard block pad center and significant margin (1.5mm radius)
                    for dx in range(-15, 16):
                        for dy in range(-15, 16):
                            net_obstacles.add((gx_pad + dx, gy_pad + dy))

        # 4. Route pin-to-pin sequentially
        p1 = net.pins[0]
        start_node = pos_map.get((p1.ref, p1.pin), pos_map.get(p1.ref))
        if not start_node: 
            unrouted_nets.append(f"{net.name}:{p1.ref}")
            continue
        
        for i in range(1, len(net.pins)):
            p2 = net.pins[i]
            end_node = pos_map.get((p2.ref, p2.pin), pos_map.get(p2.ref))
            if not end_node: 
                unrouted_nets.append(f"{net.name}:{p2.ref}")
                continue
            
            # CRITICAL: UNBLOCK EXTREMELY TIGHT AREA ONLY (1 cell) to permit connection
            unblocked_for_this_seg = []
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    for node_to_free in [start_node, end_node]:
                        n = (node_to_free[0]+dx, node_to_free[1]+dy)
                        if n in net_obstacles:
                            net_obstacles.remove(n)
                            unblocked_for_this_seg.append(n)

            path = a_star(start_node, end_node, net_obstacles, (w_grid, h_grid), thermal_keepouts)
            
            # Put them back
            for node in unblocked_for_this_seg:
                net_obstacles.add(node)

            if path:
                # 1. Path Simplification: Merge collinear segments to reduce file size and segment count
                simplified_path = []
                if len(path) > 0:
                    simplified_path.append(path[0])
                    for i in range(1, len(path) - 1):
                        p_prev = path[i-1]
                        p_curr = path[i]
                        p_next = path[i+1]
                        
                        # Calculate directions
                        dx1, dy1 = p_curr[0] - p_prev[0], p_curr[1] - p_prev[1]
                        dx2, dy2 = p_next[0] - p_curr[0], p_next[1] - p_curr[1]
                        
                        # If direction changes, keep the current point
                        if (dx1, dy1) != (dx2, dy2):
                            simplified_path.append(p_curr)
                    if len(path) > 1:
                        simplified_path.append(path[-1])
                
                # 2. Convert to mm with 0.1mm grid scale
                mm_path = [(px / grid_scale, py / grid_scale) for px, py in simplified_path]
                
                # 3. Use wider traces for power nets (VCC, GND, 12V, 5V, VIN)
                power_names = ["VCC", "GND", "5V", "12V", "VIN"]
                width = 0.6 if any(p in net.name.upper() for p in power_names) else 0.2
                
                traces.append(Trace(net.name, "F.Cu", mm_path, width))
                
                # Register trace in global grid (0.3mm buffer) for other nets' avoidance
                for i in range(len(path)):
                    node = path[i]
                    for dx in range(-3, 4):
                        for dy in range(-3, 4):
                            global_trace_grid[(node[0]+dx, node[1]+dy)] = net.name
                
                start_node = end_node
            else:
                unrouted_nets.append(f"{net.name}:{p2.ref}")
                
    return traces, unrouted_nets
