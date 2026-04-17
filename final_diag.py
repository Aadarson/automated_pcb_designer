import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.append(str(Path.cwd()))

try:
    from backend.kicad_bridge.schematic_writer import write_schematic
    from backend.models.design import PCBDesignRequest, Component, BoardSpec

    mock_request = PCBDesignRequest(
        prompt="debug schematic",
        project_name="FinalTest",
        board=BoardSpec(width_mm=80, height_mm=60),
        components=[
            Component(ref="R1", part_id="10k", footprint="Resistor_SMD:R_0805_2012Metric", value="10k"),
            Component(ref="U1", part_id="ESP32", footprint="RF_Module:ESP32-WROOM-32", value="ESP32")
        ]
    )
    
    out_file = "test_output.kicad_sch"
    success = write_schematic("debug_job", mock_request, out_file)
    
    if success and Path(out_file).exists():
        content = Path(out_file).read_text()
        logger.info(f"Schematic generated successfully ({len(content)} bytes)")
        if "(symbol" in content or "uuid" in content:
            logger.info("Found symbols in schematic ✓")
        else:
            logger.error("Schematic file is empty or missing symbols ✗")
    else:
        logger.error("Failed to generate schematic file ✗")
        
except Exception as e:
    logger.exception(f"Final diagnostic failed: {e}")
