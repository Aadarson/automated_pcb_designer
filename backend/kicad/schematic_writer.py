import logging
import uuid
from pathlib import Path
from kiutils.schematic import Schematic
from kiutils.items.schitems import SchematicSymbol, Connection
from kiutils.items.common import Position
from backend.models.design import PCBDesignRequest

logger = logging.getLogger(__name__)

def write_schematic(job_id: str, request: PCBDesignRequest, out_path: str):
    """
    Generate a KiCad 6.0+ schematic using direct S-expression templates for reliability.
    """
    try:
        sch_uuid = str(uuid.uuid4())
        lines = [
            f'(kicad_sch (version 20211123) (generator Universal_EDA_Engine)',
            f'  (uuid {sch_uuid})',
            f'  (paper "A4")',
            f'  (lib_symbols)'
        ]
        
        spacing = 50.8
        for i, comp in enumerate(request.components):
            sym_uuid = str(uuid.uuid4())
            col = i % 4
            row = i // 4
            x, y = col * spacing, row * spacing
            
            lib_id = "Device:C" if "C" in comp.ref else "Device:R"
            if "D" in comp.ref: lib_id = "Device:LED"
            elif "U" in comp.ref: lib_id = "Connector:Conn_01x08_Male"
            
            lines.append(f'  (symbol (lib_id "{lib_id}") (at {x} {y} 0) (unit 1)')
            lines.append(f'    (in_bom yes) (on_board yes) (fields_autoplaced)')
            lines.append(f'    (uuid {sym_uuid})')
            lines.append(f'    (property "Reference" "{comp.ref}" (id 0) (at {x} {y-2.54} 0))')
            lines.append(f'    (property "Value" "{comp.value}" (id 1) (at {x} {y+2.54} 0))')
            lines.append(f'    (property "Footprint" "{comp.footprint}" (id 2) (at {x} {y+5.08} 0) (effects (font (size 1.27 1.27)) hide))')
            lines.append(f'  )')
            
        lines.append(')')
        
        with open(out_path, "w") as f:
            f.write("\n".join(lines))
            
        logger.info(f"Schematic saved to {out_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to generate schematic: {e}")
        return False
