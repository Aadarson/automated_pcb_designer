import os
import glob
from pathlib import Path
import logging
from backend.core.config import settings

logger = logging.getLogger(__name__)

class FootprintResolver:
    def __init__(self):
        self.lib_path = Path(settings.KICAD_FOOTPRINT_LIB_PATH)
        self.index = {}
        self._build_index()

    def _build_index(self):
        # Specific search paths for Windows KiCad 9
        potential_paths = [
            self.lib_path,
            Path("C:/Program Files/KiCad/9.0/share/kicad/footprints"),
            Path("C:/Program Files/KiCad/8.0/share/kicad/footprints"),
            Path(os.environ.get("APPDATA", "")) / "kicad" / "9.0" / "footprints"
        ]
        
        found = False
        for p in potential_paths:
            if p and p.exists():
                self.lib_path = p
                found = True
                break
        
        if not found:
            logger.warning(f"KiCad footprint library not found in standard paths.")
            return
        
        # Look for .pretty directories (KiCad footprint categories)
        for pretty_dir in self.lib_path.glob("*.pretty"):
            category = pretty_dir.stem
            for footprint_file in pretty_dir.glob("*.kicad_mod"):
                package = footprint_file.stem
                self.index[(category, package)] = footprint_file
                # Also index by package name for easier lookup
                self.index[package] = footprint_file
        
        logger.info(f"Built footprint index with {len(self.index)} footprints from {self.lib_path}")

    def resolve(self, footprint_string: str) -> Path:
        """
        Resolve a footprint string to a local path.
        Example of footprint_string: "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"
        Or simple name: "SOIC-8" to fuzzy match
        """
        # Exact match logic
        if ":" in footprint_string:
            category, package_name = footprint_string.split(":", 1)
            if (category, package_name) in self.index:
                return self.index[(category, package_name)]
        
        if footprint_string in self.index:
            return self.index[footprint_string]
        
        # Fuzzy match logic
        query = footprint_string.replace(':', '_').lower()
        for key, path in self.index.items():
            if isinstance(key, str):
                if query in key.lower(): return path
            elif isinstance(key, tuple):
                if query in f"{key[0]}_{key[1]}".lower(): return path

        default_path = self.index.get(("Package_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm"))
        if default_path:
            logger.warning(f"Footprint {footprint_string} not found. using default {default_path}")
            return default_path
        
        # Worst case fallback if index is empty
        logger.error(f"Failed to resolve {footprint_string} and no default available.")
        return Path("/dev/null")

    def get_footprint_size(self, footprint_string: str) -> tuple[float, float, float, float]:
        """Dynamically extract actual width, height, and the anchor offset (cx, cy)."""
        path = self.resolve(footprint_string)
        if not path or not path.exists():
            return 5.0, 5.0, 0.0, 0.0
            
        try:
            from kiutils.footprint import Footprint
            fp = Footprint().from_file(str(path))
            min_x, max_x = 0.0, 0.0
            min_y, max_y = 0.0, 0.0
            has_elements = False
            
            for p in fp.pads:
                has_elements = True
                px, py = p.position.X, p.position.Y
                w, h = p.size.X, p.size.Y
                min_x = min(min_x, px - w/2)
                max_x = max(max_x, px + w/2)
                min_y = min(min_y, py - h/2)
                max_y = max(max_y, py + h/2)
                
            for g in fp.graphicItems:
                if hasattr(g, 'start') and hasattr(g, 'end'):
                    if getattr(g, 'layer', '') == 'F.CrtYd':
                        has_elements = True
                        min_x = min(min_x, g.start.X, g.end.X)
                        max_x = max(max_x, g.start.X, g.end.X)
                        min_y = min(min_y, g.start.Y, g.end.Y)
                        max_y = max(max_y, g.start.Y, g.end.Y)

            if not has_elements:
                return 5.0, 5.0, 0.0, 0.0
                
            width = (max_x - min_x) + 1.0
            height = (max_y - min_y) + 1.0
            cx = (min_x + max_x) / 2.0
            cy = (min_y + max_y) / 2.0
            return max(width, 2.0), max(height, 2.0), cx, cy
        except Exception as e:
            logger.error(f"Error parsing size for {footprint_string}: {e}")
            return 5.0, 5.0, 0.0, 0.0

    def get_pad_offsets(self, footprint_string: str) -> dict:
        """Extracts the exact (X, Y) offset of every pad relative to the footprint's anchor."""
        path = self.resolve(footprint_string)
        offsets = {}
        if not path or not path.exists():
            return offsets
            
        try:
            from kiutils.footprint import Footprint
            fp = Footprint().from_file(str(path))
            npth_idx = 0
            for p in fp.pads:
                pad_id = ""
                if hasattr(p, 'number') and p.number:
                    pad_id = str(p.number)
                else:
                    pad_id = f"NPTH_{npth_idx}"
                    npth_idx += 1
                
                offsets[pad_id] = (float(p.position.X), float(p.position.Y))
        except Exception as e:
            logger.error(f"Error extracting pads for {footprint_string}: {e}")
            
        return offsets

resolver = FootprintResolver()
