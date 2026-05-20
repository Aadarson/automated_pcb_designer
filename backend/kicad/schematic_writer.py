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
    Generate a KiCad 6.0+ schematic with improved layout and pin labeling.
    """
    try:
        sch_uuid = str(uuid.uuid4())
        lines = [
            f'(kicad_sch (version 20211123) (generator Universal_EDA_Engine)',
            f'  (uuid {sch_uuid})',
            f'  (paper "A4")',
            f'  (lib_symbols)'
        ]
        
        # Determine library IDs based on ref
        def get_lib_id(ref):
            if ref.startswith("C"): return "Device:C"
            if ref.startswith("R"): return "Device:R"
            if ref.startswith("D"): return "Device:LED"
            if ref.startswith("U"): return "MCU_Module:Arduino_Nano_Every" if "ARDUINO" in ref.upper() else "Package_QFP:TQFP-32_7x7mm_P0.8mm"
            if ref.startswith("J"): return "Connector:Conn_01x08_Male"
            return "Device:Component"

        # Organize symbols in a grid
        spacing_x = 50.8
        spacing_y = 50.8
        for i, comp in enumerate(request.components):
            sym_uuid = str(uuid.uuid4())
            col = i % 4
            row = i // 4
            # Keep symbols within standard A4 bounds
            x, y = 50 + (col * spacing_x), 50 + (row * spacing_y)
            
            lib_id = get_lib_id(comp.ref)
            
            lines.append(f'  (symbol (lib_id "{lib_id}") (at {x} {y} 0) (unit 1)')
            lines.append(f'    (in_bom yes) (on_board yes) (fields_autoplaced)')
            lines.append(f'    (uuid {sym_uuid})')
            lines.append(f'    (property "Reference" "{comp.ref}" (id 0) (at {x} {y-2.54} 0))')
            lines.append(f'    (property "Value" "{comp.value}" (id 1) (at {x} {y+2.54} 0))')
            lines.append(f'    (property "Footprint" "{comp.footprint}" (id 2) (at {x} {y+5.08} 0) (effects (font (size 1.27 1.27)) hide))')
            
            # Add net labels to symbols (Electrical IQ)
            for net in request.nets:
                for pin in net.pins:
                    if pin.ref == comp.ref:
                        # Add a global label for visibility
                        label_uuid = str(uuid.uuid4())
                        lines.append(f'    (label "{net.name}" (at {x+5.08} {y+(int(pin.pin)*1.27)} 0) (fields_autoplaced)')
                        lines.append(f'      (effects (font (size 1.27 1.27)) (justify left))')
                        lines.append(f'      (uuid {label_uuid})')
                        lines.append(f'    )')

            lines.append(f'  )')
            
        lines.append(')')
        
        with open(out_path, "w") as f:
            f.write("\n".join(lines))
            
        logger.info(f"Schematic saved to {out_path} with {len(request.components)} symbols.")
        return True
    except Exception as e:
        logger.error(f"Failed to generate schematic: {e}")
        return False
