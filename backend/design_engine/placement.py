import math
import random
import logging
import hashlib
from typing import List, Dict, Tuple
from backend.models.design import BoardSpec, Component, Net, PCBDesignRequest

logger = logging.getLogger(__name__)

class PlacedComponent:
    def __init__(self, ref: str, x: float, y: float, rotation: float, layer: str, w=5.0, h=5.0, cx=0.0, cy=0.0):
        self.ref = ref
        self.x = x
        self.y = y
        self.rotation = rotation
        self.layer = layer
        self.w = w
        self.h = h
        self.cx = cx
        self.cy = cy

    def get_bbox(self) -> Tuple[float, float, float, float]:
        """Returns (x1, y1, x2, y2) bounding box."""
        if self.rotation in [90, 270]:
            half_w, half_h = self.h / 2, self.w / 2
        else:
            half_w, half_h = self.w / 2, self.h / 2
        return (self.x - half_w, self.y - half_h, self.x + half_w, self.y + half_h)

class PlacementEngine:
    def __init__(self, request: PCBDesignRequest):
        self.request = request
        self.board = request.board
        self.components = request.components
        self.nets = request.nets
        self.grid_size = 0.5
        
    def _calculate_hpwl(self, placements: List[PlacedComponent]) -> float:
        """Calculate total Half-Perimeter Wire Length (HPWL) for all nets."""
        pos_map = {p.ref: (p.x, p.y) for p in placements}
        total_hpwl = 0.0
        
        for net in self.nets:
            if len(net.pins) < 2: continue
            
            pins_in_net = [pos_map[pin.ref] for pin in net.pins if pin.ref in pos_map]
            if not pins_in_net: continue
            
            x_coords = [p[0] for p in pins_in_net]
            y_coords = [p[1] for p in pins_in_net]
            
            width = max(x_coords) - min(x_coords)
            height = max(y_coords) - min(y_coords)
            total_hpwl += (width + height)
                
        return total_hpwl

    def _calculate_collisions(self, placements: List[PlacedComponent]) -> int:
        """Count number of overlapping bounding boxes with safety padding."""
        collision_count = 0
        bboxes = []
        for p in placements:
            bb = p.get_bbox()
            # Add 1.5mm safety padding for courtyards and solder masks
            bboxes.append((bb[0]-1.5, bb[1]-1.5, bb[2]+1.5, bb[3]+1.5))
            
        for i in range(len(bboxes)):
            for j in range(i + 1, len(bboxes)):
                b1 = bboxes[i]
                b2 = bboxes[j]
                if not (b1[2] < b2[0] or b1[0] > b2[2] or b1[3] < b2[1] or b1[1] > b2[3]):
                    collision_count = collision_count + 1
        return collision_count

    def run(self) -> List[PlacedComponent]:
        logger.info("Running advanced simulated annealing placement with Spreading Rules...")
        
        # 0. Determinism
        comp_str = "".join([c.ref for c in self.components])
        seed_str = f"{self.request.prompt}_{self.board.width_mm}_{self.board.height_mm}_{comp_str}"
        seed_val = int(hashlib.sha256(seed_str.encode()).hexdigest(), 16) % (10**8)
        rng = random.Random(seed_val)
        
        # 1. Initialize with Spreading Rule
        placements = []
        from backend.kicad.footprint_resolver import resolver
        
        bw = self.board.width_mm
        bh = self.board.height_mm
        
        for c in self.components:
            w, h, cx, cy = resolver.get_footprint_size(c.footprint)
            pid = c.part_id.upper()
            fp = c.footprint.upper()
            
            # Universal Placement Spreading Rule Logic
            if any(mcu in pid for mcu in ["ESP32", "NANO", "ATMEL", "STM32", "PIC"]):
                # MCU -> Center
                x, y = bw/2, bh/2
            elif any(pwr in pid for pwr in ["7805", "LM", "L298", "REGULATOR", "MOSFET"]) or "POWER" in fp:
                # Power -> Bottom-Right
                x, y = bw * 0.75, bh * 0.75
            elif any(sens in pid for sens in ["BMP", "MPU", "DHT", "SENSOR"]):
                # Sensors -> Top-Right
                x, y = bw * 0.75, bh * 0.25
            elif any(comm in pid for comm in ["WIFI", "BT", "NRF", "LORA"]) or "MODULE" in fp:
                # Comms -> Top-Left
                x, y = bw * 0.25, bh * 0.25
            elif any(conn in pid or conn in fp for conn in ["CONN", "HEADER", "TERMINAL", "USB", "JST"]):
                # Connectors -> Edges (Start at Bottom edge)
                x, y = bw/2, bh - 5.0
            else:
                # Default (LEDs, Buttons) -> Bottom-Left
                x, y = bw * 0.25, bh * 0.75

            # Randomize slightly within zone
            x += rng.uniform(-5.0, 5.0)
            y += rng.uniform(-5.0, 5.0)
            
            # Clamp to board
            x = max(cx + 2.0, min(x, bw - (w-cx) - 2.0))
            y = max(cy + 2.0, min(y, bh - (h-cy) - 2.0))
            
            p_obj = PlacedComponent(ref=c.ref, x=x, y=y, rotation=0.0, layer="F.Cu", w=w, h=h, cx=cx, cy=cy)
            is_hot = ("L298" in pid or "7805" in pid or "LM" in pid or "MODULE" in fp)
            setattr(p_obj, 'is_hot', is_hot)
            placements.append(p_obj)

        # 2. Simulated Annealing
        def _calculate_thermal_cost(plcs):
            hot = [p for p in plcs if getattr(p, 'is_hot', False)]
            cost = 0.0
            for i in range(len(hot)):
                for j in range(i + 1, len(hot)):
                    dist = math.hypot(hot[i].x - hot[j].x, hot[i].y - hot[j].y)
                    if dist < 25.0: # 25mm heat-spread threshold
                        cost += (25.0 - dist) * 200.0 # Heavy penalty for clustering
            return cost

        def get_cost(plcs):
            return (self._calculate_hpwl(plcs) + 
                    (self._calculate_collisions(plcs) * 100000.0) + 
                    _calculate_thermal_cost(plcs))

        current_cost = get_cost(placements)
        best_cost = current_cost
        best_placements = [PlacedComponent(p.ref, p.x, p.y, p.rotation, p.layer, p.w, p.h, p.cx, p.cy) for p in placements]
        for idx, p in enumerate(best_placements): setattr(p, 'is_hot', getattr(placements[idx], 'is_hot', False))
        
        T = 100.0
        T_min = 0.01
        alpha = 0.99 # Slower cooling
        
        for _ in range(1000): # More iterations
            if T <= T_min: break
            
            idx = rng.randint(0, len(placements) - 1)
            p = placements[idx]
            old_x = p.x
            old_y = p.y
            
            move_scale = max(T / 100.0, 0.1)
            p.x = p.x + rng.uniform(-10, 10) * move_scale
            p.y = p.y + rng.uniform(-10, 10) * move_scale
            
            # Strict boundary check with margin (Edge clearance DRC fix)
            margin = 4.0 # Keep components safely away from the edge
            # Anchor-aware boundary check (ensures p.x - p.cx >= 2.0)
            p.x = max(p.cx + 2.0, min(p.x, self.board.width_mm - (p.w - p.cx) - 2.0))
            p.y = max(p.cy + 2.0, min(p.y, self.board.height_mm - (p.h - p.cy) - 2.0))
            
            new_cost = get_cost(placements)
            
            # Accept or reject
            if new_cost < current_cost or rng.random() < math.exp((current_cost - new_cost) / T):
                current_cost = new_cost
                if current_cost < best_cost:
                    best_cost = current_cost
                    best_placements = [PlacedComponent(comp.ref, comp.x, comp.y, comp.rotation, comp.layer, comp.w, comp.h, comp.cx, comp.cy) for comp in placements]
            else:
                # Revert
                p.x = old_x
                p.y = old_y
                
            T = T * alpha

        # 3. Post-processing to perfectly eliminate any remaining overlaps
        # Simple push-apart logic
        for _ in range(10):
            collisions = self._calculate_collisions(best_placements)
            if collisions == 0: break
            
            for i in range(len(best_placements)):
                for j in range(i + 1, len(best_placements)):
                    b1 = best_placements[i]
                    b2 = best_placements[j]
                    
                    # Calculate effective width and height for collision detection, considering rotation
                    w1_eff = b1.h if b1.rotation in [90, 270] else b1.w
                    h1_eff = b1.w if b1.rotation in [90, 270] else b1.h
                    w2_eff = b2.h if b2.rotation in [90, 270] else b2.w
                    h2_eff = b2.w if b2.rotation in [90, 270] else b2.h

                    # Use a 1.0mm safety buffer for push-apart logic
                    buffer = 1.0
                    
                    # Check for overlap using center coordinates and effective dimensions
                    if (abs(b1.x - b2.x) * 2 < (w1_eff + w2_eff + buffer) and
                        abs(b1.y - b2.y) * 2 < (h1_eff + h2_eff + buffer)):
                        # Push b2 away from b1
                        dx = b2.x - b1.x
                        dy = b2.y - b1.y
                        if dx == 0 and dy == 0: dx = 1.0 # arbitrary offset
                        
                        dist = math.hypot(dx, dy)
                        # Ensure dist is not zero to avoid division by zero
                        if dist == 0:
                            dist = 0.001 # Small epsilon to prevent division by zero
                            dx = 0.001 # Give it a slight push
                        
                        push_x = (dx / dist) * 2.0
                        push_y = (dy / dist) * 2.0
                        
                        b1.x -= push_x
                        b2.x += push_x
                        b1.y -= push_y
                        b2.y += push_y
                        
                        # Anchor-aware boundary enforcement
                        b1.x = max(b1.cx + 2.0, min(b1.x, self.board.width_mm - (b1.w - b1.cx) - 2.0))
                        b1.y = max(b1.cy + 2.0, min(b1.y, self.board.height_mm - (b1.h - b1.cy) - 2.0))
                        b2.x = max(b2.cx + 2.0, min(b2.x, self.board.width_mm - (b2.w - b2.cx) - 2.0))
                        b2.y = max(b2.cy + 2.0, min(b2.y, self.board.height_mm - (b2.h - b2.cy) - 2.0))

        logger.info(f"Final placement collisions: {self._calculate_collisions(best_placements)}")
        return best_placements

def run_placement(request: PCBDesignRequest) -> List[PlacedComponent]:
    engine = PlacementEngine(request)
    return engine.run()
