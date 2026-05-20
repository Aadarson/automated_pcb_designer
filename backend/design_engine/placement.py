import math
import random
import logging
import hashlib
from typing import List, Dict, Tuple
from backend.models.design import PCBDesignRequest

logger = logging.getLogger(__name__)

class PlacedComponent:
    def __init__(self, ref: str, x: float, y: float, rotation: float, layer: str, footprint: str, w=5.0, h=5.0, cx=0.0, cy=0.0):
        self.ref = ref
        self.x = x
        self.y = y
        self.rotation = rotation
        self.layer = layer
        self.footprint = footprint
        self.w = w
        self.h = h
        self.cx = cx
        self.cy = cy

    def get_bbox(self) -> Tuple[float, float, float, float]:
        """Calculates the true bounding box relative to the anchor, considering rotation."""
        hw, hh = self.w / 2, self.h / 2
        off_x, off_y = self.cx, self.cy
        
        if self.rotation in [90, 270]:
            left, right = off_y - hh, off_y + hh
            top, bottom = off_x - hw, off_x + hw
        else:
            left, right = off_x - hw, off_x + hw
            top, bottom = off_y - hh, off_y + hh
            
        return (self.x + left, self.y + top, self.x + right, self.y + bottom)

class PlacementEngine:
    def __init__(self, request: PCBDesignRequest):
        self.request = request
        self.board = request.board
        self.components = request.components
        self.nets = request.nets

    def _calculate_hpwl(self, placements: List[PlacedComponent]) -> float:
        pos_map = {p.ref: (p.x, p.y) for p in placements}
        total_hpwl = 0.0
        for net in self.nets:
            if len(net.pins) < 2: continue
            pins_in_net = [pos_map[pin.ref] for pin in net.pins if pin.ref in pos_map]
            if not pins_in_net: continue
            x_coords = [p[0] for p in pins_in_net]
            y_coords = [p[1] for p in pins_in_net]
            total_hpwl += (max(x_coords) - min(x_coords)) + (max(y_coords) - min(y_coords))
        return total_hpwl

    def _calculate_overlap_depth(self, placements: List[PlacedComponent]) -> float:
        """Returns the sum of overlap depths + proximity penalty (Continuous Repulsion)."""
        total_depth = 0.0
        m = 3.0 # Soft Margin (Proximity)
        bboxes = []
        for p in placements:
            bb = p.get_bbox()
            bboxes.append((bb[0], bb[1], bb[2], bb[3]))
            
        for i in range(len(bboxes)):
            for j in range(i + 1, len(bboxes)):
                b1, b2 = bboxes[i], bboxes[j]
                # Distance between centers
                dx = max(0, abs((b1[0]+b1[2])/2 - (b2[0]+b2[2])/2) - (b1[2]-b1[0] + b2[2]-b2[0])/2)
                dy = max(0, abs((b1[1]+b1[3])/2 - (b2[1]+b2[3])/2) - (b1[3]-b1[1] + b2[3]-b2[1])/2)
                
                dist = math.sqrt(dx**2 + dy**2)
                if dist < m:
                    # Penalty for overlap (dist=0) or proximity (dist < m)
                    total_depth += (m - dist) ** 2 * 100.0
        return total_depth

    def run(self) -> List[PlacedComponent]:
        bw, bh = self.board.width_mm, self.board.height_mm
        best_overall_placements = []
        max_seen_coverage = -1.0

        for attempt in range(1, 4):
            logger.info(f"Placement Attempt {attempt}/3...")
            placements = self._initialize_placements(attempt)
            
            T = 500.0 if attempt > 1 else 300.0
            T_min = 0.01
            alpha = 0.99 # Slightly faster for more attempts
            
            def get_cost(plcs):
                hpwl = self._calculate_hpwl(plcs)
                depth = self._calculate_overlap_depth(plcs)
                
                # Boundary Penalty (Hard Limit)
                boundary_penalty = 0.0
                for p in plcs:
                    bb = p.get_bbox()
                    if bb[0] < 0 or bb[2] > bw or bb[1] < 0 or bb[3] > bh:
                        boundary_penalty += 100000.0
                
                xs, ys = [p.x for p in plcs], [p.y for p in plcs]
                coverage = ((max(xs)-min(xs))*(max(ys)-min(ys))) / (bw * bh)
                # MASSIVE spread bonus to fight Wire Length centralizing force
                spread_bonus = -1.0 * coverage if attempt > 1 else -0.5 * coverage
                return (hpwl * 1.0) + (depth * 10000.0) + (spread_bonus * 1000000.0) + boundary_penalty

            curr_cost = get_cost(placements)
            for _ in range(15000):
                if T <= T_min: break
                p = random.choice(placements)
                ox, oy = p.x, p.y
                
                move_range = 2.0 + (T / 5.0)
                p.x += random.uniform(-move_range, move_range)
                p.y += random.uniform(-move_range, move_range)
                
                # Clip
                bb = p.get_bbox()
                m = 2.0
                if bb[0] < m: p.x += (m - bb[0])
                if bb[2] > bw - m: p.x -= (bb[2] - (bw - m))
                if bb[1] < m: p.y += (m - bb[1])
                if bb[3] > bh - m: p.y -= (nb[3] - (bh - m)) if 'nb' in locals() else (bb[3] - (bh - m)) # Fix local name error if any

                new_cost = get_cost(placements)
                if new_cost <= curr_cost or random.random() < math.exp((curr_cost - new_cost) / T):
                    curr_cost = new_cost
                else:
                    p.x, p.y = ox, oy
                T *= alpha

            xs, ys = [p.x for p in placements], [p.y for p in placements]
            coverage = ((max(xs)-min(xs))*(max(ys)-min(ys))) / (bw * bh)
            if coverage > max_seen_coverage:
                max_seen_coverage = coverage
                best_overall_placements = [PlacedComponent(p.ref, p.x, p.y, p.rotation, p.layer, p.footprint, p.w, p.h, p.cx, p.cy) for p in placements]

            if coverage >= 0.3: # Calibrated for realistic boards
                break
        
        # Greedy Forced Separation Pass (Symmetry Breaking)
        m = 5.0 # Aggressive final clearance
        for _ in range(200): # 2x iterations
            clsn = 0
            for i in range(len(best_overall_placements)):
                for j in range(i + 1, len(best_overall_placements)):
                    p1, p2 = best_overall_placements[i], best_overall_placements[j]
                    b1, b2 = p1.get_bbox(), p2.get_bbox()
                    b1_m = (b1[0]-m/2, b1[1]-m/2, b1[2]+m/2, b1[3]+m/2)
                    b2_m = (b2[0]-m/2, b2[1]-m/2, b2[2]+m/2, b2[3]+m/2)
                    
                    if not (b1_m[2] < b2_m[0] or b1_m[0] > b2_m[2] or b1_m[3] < b2_m[1] or b1_m[1] > b2_m[3]):
                        clsn += 1
                        dx, dy = p2.x - p1.x, p2.y - p1.y
                        if abs(dx) < 0.1 and abs(dy) < 0.1:
                            dx, dy = random.uniform(-1, 1), random.uniform(-1, 1)
                        
                        dist = math.sqrt(dx**2 + dy**2) + 0.001
                        # Forceful nudge
                        p2.x += (dx/dist)*5.0
                        p2.y += (dy/dist)*5.0
                        
                        # Clip
                        nb = p2.get_bbox()
                        if nb[0] < m: p2.x += (m - nb[0])
                        if nb[2] > bw - m: p2.x -= (nb[2] - (bw - m))
                        if nb[1] < m: p2.y += (m - nb[1])
                        if nb[3] > bh - m: p2.y -= (nb[3] - (bh - m))
            if clsn == 0: break
            logger.info(f"Greedy separation pass: Resolving {clsn} collisions...")

        return best_overall_placements

    def _initialize_placements(self, attempt: int) -> List[PlacedComponent]:
        from backend.kicad.footprint_resolver import resolver
        placements = []
        bw, bh = self.board.width_mm, self.board.height_mm
        for c in self.components:
            w, h, cx, cy = resolver.get_footprint_size(c.footprint)
            half_w, half_h = w / 2, h / 2
            # Wider initial scatter
            x = random.uniform(half_w + 5, bw - half_w - 5)
            y = random.uniform(half_h + 5, bh - half_h - 5)
            placements.append(PlacedComponent(c.ref, x, y, 0.0, "F.Cu", c.footprint, w, h, cx, cy))
        return placements

def run_placement(request: PCBDesignRequest) -> List[PlacedComponent]:
    return PlacementEngine(request).run()
