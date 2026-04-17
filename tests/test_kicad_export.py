import os
import pytest
from backend.models.design import PCBDesignRequest, BoardSpec, Component, Net
from backend.kicad_bridge.exporter import export_kicad_pcb

def test_kicad_export():
    req = PCBDesignRequest(
        prompt="Test",
        project_name="Test",
        board=BoardSpec(width_mm=80, height_mm=60)
    )
    output_path = "test_output.kicad_pcb"
    export_kicad_pcb("test_job", req, [], [], output_path)
    
    assert os.path.exists(output_path)
    
    with open(output_path, "r") as f:
        content = f.read()
        assert "kicad_pcb" in content
        
    os.remove(output_path)
