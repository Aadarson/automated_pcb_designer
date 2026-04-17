import logging
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)

class RoutingRLAgent:
    def __init__(self, memory_file="rl_routing_memory.pkl"):
        self.memory_file = Path(memory_file)
        self.q_table = {} # Simple coordinate penalty map: (x, y) -> penalty factor
        self._load_memory()

    def _load_memory(self):
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "rb") as f:
                    self.q_table = pickle.load(f)
                logger.info(f"RL Agent loaded structural memory with {len(self.q_table)} spatial experiences.")
            except Exception as e:
                logger.error(f"Failed to load RL memory: {e}")

    def _save_memory(self):
        try:
            with open(self.memory_file, "wb") as f:
                pickle.dump(self.q_table, f)
        except Exception as e:
            logger.error(f"Failed to saving RL memory: {e}")

    def learn_from_drc(self, drc_violations):
        """
        Parses DRC reports. Assigns massive penalties to the specific 
        (X, Y) layout coordinates where the physical violation occurred.
        """
        learned_count = 0
        for violation in drc_violations:
            if hasattr(violation, 'location') and violation.location:
                # e.g., "(12.5000 mm, 34.2000 mm)"
                # Extract coordinates
                try:
                    # KiCad CLI json often provides specific numeric coords, or a string
                    if isinstance(violation.location, dict) and 'x' in violation.location:
                        x = float(violation.location['x'])
                        y = float(violation.location['y'])
                    elif isinstance(violation.location, list) and len(violation.location) == 2:
                        x = float(violation.location[0])
                        y = float(violation.location[1])
                    else:
                        continue # Couldn't parse natively, skipping

                    # Quantize coordinate to 0.1mm grid scale (matching the high-res router)
                    grid_scale = 10.0
                    gx = int(x * grid_scale)
                    gy = int(y * grid_scale)

                    # Mark a 1.0mm penalty radius (10 cells at 0.1mm) around the exact DRC failure spot
                    for dx in range(-10, 11):
                        for dy in range(-10, 11):
                            coord = (gx + dx, gy + dy)
                            self.q_table[coord] = self.q_table.get(coord, 0.0) + 50000.0 # Mathematically exclude the area
                            learned_count += 1
                except Exception as e:
                    logger.debug(f"RL agent skipping unparseable coordinate: {e}")
                    
        if learned_count > 0:
            logger.info(f"RL Agent updated policy matrix: Punished {learned_count} pathfinding states.")
            self._save_memory()

    def get_penalty(self, gx: int, gy: int) -> float:
        """Returns the learned Q-table topological penalty for a given router grid node."""
        return self.q_table.get((gx, gy), 0.0)

    def reset_episode(self):
        """Empties volatile short-term spatial memory for a totally new design."""
        self.q_table = {}

rl_router_agent = RoutingRLAgent()
