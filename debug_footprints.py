import logging
import sys
from pathlib import Path

# Setup logging to stdout
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.append(str(Path.cwd()))

try:
    from backend.kicad_bridge.footprint_resolver import resolver
    from backend.models.design import PCBDesignRequest, Component, BoardSpec
    from backend.kicad_bridge.exporter import export_kicad_pcb
    from backend.design_engine.placement import PlacedComponent

    # 1. Test Resolver
    fp_name = "Package_TO_SOT_THT:TO-92_Inline"
    path = resolver.resolve(fp_name)
    logger.info(f"Resolved {fp_name} to: {path}")
    if path and path.exists():
        logger.info("Path exists ✓")
    else:
        logger.error("Path does NOT exist ✗")

    # 2. Test Exporter with one component
    mock_request = PCBDesignRequest(
        prompt="debug",
        project_name="TestProject",
        board=BoardSpec(width_mm=80, height_mm=60),
        components=[Component(ref="Q1", part_id="2N2222", footprint=fp_name, value="2N2222")]
    )
    mock_placements = [PlacedComponent(ref="Q1", x=40, y=30, rotation=0, layer="F.Cu", w=5, h=5)]
    
    out_file = "debug_board.kicad_pcb"
    export_kicad_pcb("debug_job", mock_request, mock_placements, [], out_file)
    
    if Path(out_file).exists():
        content = Path(out_file).read_text()
        if "(module" in content or "(footprint" in content:
            logger.info("Footprint found in output file ✓")
        else:
            logger.error("Footprint MISSING from output file ✗")
            logger.info("File Content Slice:")
            logger.info(content[:1000])
    
except Exception as e:
    logger.exception(f"Diagnostic failed: {e}")
