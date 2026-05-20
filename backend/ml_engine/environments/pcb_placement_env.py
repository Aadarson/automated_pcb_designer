import gymnasium as gym
from gymnasium import spaces
import numpy as np
import logging
from typing import List, Dict
from backend.models.design import PCBDesignRequest, Component, Net

logger = logging.getLogger(__name__)

class PCBPlacementEnv(gym.Env):
    """
    Universal Gymnasium environment for PCB component placement optimization.
    Fixed observation and action spaces (up to MAX_COMPONENTS) allow a single
    universal RL model to train on and generalize across ANY board size/complexity.
    """
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 30}

    def __init__(self, request: PCBDesignRequest = None, initial_placements: List[any] = None):
        super(PCBPlacementEnv, self).__init__()
        
        self.max_comps = 100 # Universal Padding Limit
        
        self.request = request
        self.initial_placements = initial_placements or []
        if request:
            self.bw = request.board.width_mm
            self.bh = request.board.height_mm
            self.num_components = min(len(request.components), self.max_comps)
        else:
            self.bw, self.bh = 100.0, 100.0
            self.num_components = 10

        # Action Space: [comp_idx, dx, dy, d_rotate]
        self.action_space = spaces.Box(
            low=np.array([0, -50.0, -50.0, -1.0]), 
            high=np.array([self.max_comps - 1, 50.0, 50.0, 1.0]), 
            dtype=np.float32
        )

        # Observation Space: [x, y, w, h] * max_comps
        self.observation_space = spaces.Box(
            low=-1000.0, 
            high=1000.0, 
            shape=(self.max_comps * 4,), 
            dtype=np.float32
        )

        self.state = None
        self.comp_data = [] # Stores [ref, w, h, cx, cy] for ACTIVE components
        self.adjacency = None 

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # Initialize fully zeroed arrays
        self.state = np.zeros((self.max_comps * 4,), dtype=np.float32)
        self.adjacency = np.zeros((self.max_comps, self.max_comps))
        self.comp_data = []
        
        if not self.request:
            return self.state, {}

        # Populate Active Components
        from backend.kicad.footprint_resolver import resolver
        
        ref_to_idx = {}
        for i in range(self.num_components):
            c = self.request.components[i]
            ref_to_idx[c.ref] = i
            w, h, cx, cy = resolver.get_footprint_size(c.footprint)
            self.comp_data.append({"ref": c.ref, "w": w, "h": h, "cx": cx, "cy": cy})
            
            # Extract initial position from SA engine if available
            x, y = self.bw / 2, self.bh / 2
            if i < len(self.initial_placements):
                x = self.initial_placements[i].x
                y = self.initial_placements[i].y
            
            base_idx = i * 4
            self.state[base_idx] = x
            self.state[base_idx + 1] = y
            self.state[base_idx + 2] = w
            self.state[base_idx + 3] = h
        
        # Build adjacency matrix
        for net in self.request.nets:
             pins = [p.ref for p in net.pins if p.ref in ref_to_idx]
             for i in range(len(pins)):
                 for j in range(i + 1, len(pins)):
                     idx1, idx2 = ref_to_idx[pins[i]], ref_to_idx[pins[j]]
                     self.adjacency[idx1, idx2] += 1
                     self.adjacency[idx2, idx1] += 1

        return self.state, {}

    def step(self, action):
        comp_idx = int(np.clip(action[0], 0, self.max_comps - 1))
        dx, dy = action[1], action[2]
        
        # Only allow moving ACTIVE components
        if comp_idx < self.num_components:
            base_idx = comp_idx * 4
            w, h = self.state[base_idx + 2], self.state[base_idx + 3]
            self.state[base_idx] = np.clip(self.state[base_idx] + dx, w/2, self.bw - w/2)
            self.state[base_idx + 1] = np.clip(self.state[base_idx + 1] + dy, h/2, self.bh - h/2)

        # Calculate Reward
        hpwl = self._calculate_hpwl()
        clearance_penalty = self._calculate_clearance_penalty()
        overlaps = self._calculate_overlaps_count()
        coverage = self._calculate_coverage()
        
        reward = -(hpwl * 0.1) - (clearance_penalty * 50.0) + (coverage * 50.0)
        
        return self.state, reward, False, False, {"hpwl": hpwl, "overlaps": overlaps, "clearance": -clearance_penalty}

    def _calculate_hpwl(self) -> float:
        total_hpwl = 0.0
        coords = self.state.reshape(-1, 4)[:, :2]
        for i in range(self.num_components):
            for j in range(i + 1, self.num_components):
                if self.adjacency[i, j] > 0:
                    dist = np.sum(np.abs(coords[i] - coords[j]))
                    total_hpwl += dist * self.adjacency[i, j]
        return total_hpwl

    def _calculate_clearance_penalty(self) -> float:
        penalty = 0.0
        target_clearance = 3.0
        boxes = self.state.reshape(-1, 4)
        for i in range(self.num_components):
            for j in range(i + 1, self.num_components):
                b1, b2 = boxes[i], boxes[j]
                
                dx = max(0, abs(b1[0] - b2[0]) - (b1[2] + b2[2]) / 2)
                dy = max(0, abs(b1[1] - b2[1]) - (b1[3] + b2[3]) / 2)
                
                dist = np.sqrt(dx**2 + dy**2)
                if dx == 0 and dy == 0:
                    overlap_depth = (b1[2] + b2[2]) / 2 - abs(b1[0]-b2[0]) + (b1[3] + b2[3]) / 2 - abs(b1[1]-b2[1])
                    penalty += 1000.0 + overlap_depth * 100.0
                elif dist < target_clearance:
                    penalty += (target_clearance - dist) ** 2
        return penalty

    def _calculate_overlaps_count(self) -> int:
        overlaps = 0
        boxes = self.state.reshape(-1, 4)
        for i in range(self.num_components):
            for j in range(i + 1, self.num_components):
                b1, b2 = boxes[i], boxes[j]
                x1_min, x1_max = b1[0] - b1[2]/2, b1[0] + b1[2]/2
                y1_min, y1_max = b1[1] - b1[3]/2, b1[1] + b1[3]/2
                x2_min, x2_max = b2[0] - b2[2]/2, b2[0] + b2[2]/2
                y2_min, y2_max = b2[1] - b2[3]/2, b2[1] + b2[3]/2
                if not (x1_max < x2_min or x1_min > x2_max or y1_max < y2_min or y1_min > y2_max):
                    overlaps += 1
        return overlaps

    def _calculate_coverage(self) -> float:
        if self.num_components < 2: return 0.0
        coords = self.state.reshape(-1, 4)[:self.num_components, :2]
        x_min, x_max = np.min(coords[:, 0]), np.max(coords[:, 0])
        y_min, y_max = np.min(coords[:, 1]), np.max(coords[:, 1])
        return ((x_max - x_min) * (y_max - y_min)) / (self.bw * self.bh)

    def render(self): pass
