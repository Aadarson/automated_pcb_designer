import json
import zipfile
from pathlib import Path

def generate_kicad_project(project_dir: Path, project_name: str):
    """
    Generates a basic .kicad_pro file and bundles everything into a ZIP.
    """
    pro_path = project_dir / f"{project_name}.kicad_pro"
    
    # Minimal KiCad 6.0+ project JSON
    pro_content = {
        "meta": {"version": 1},
        "project": {
            "view": {
                "last_canvas": 1,
                "zoom_factor": 1.0
            }
        }
    }
    
    with open(pro_path, "w") as f:
        json.dump(pro_content, f, indent=2)
        
    zip_path = project_dir / f"{project_name}_design.zip"
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in project_dir.glob("*"):
            if file.suffix in [".kicad_pcb", ".kicad_pro", ".kicad_sch"]:
                zipf.write(file, arcname=file.name)
                
    return zip_path
