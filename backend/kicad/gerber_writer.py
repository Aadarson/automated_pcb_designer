import subprocess
import logging
import os
import shutil
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)

def generate_gerber_bundle(pcb_path: str, output_dir: str) -> str:
    """
    Generate Gerbers and Drill files using kicad-cli and bundle them into a ZIP.
    Returns the path to the ZIP file.
    """
    try:
        pcb_path_obj = Path(pcb_path)
        gerber_dir = Path(output_dir) / "gerbers"
        os.makedirs(gerber_dir, exist_ok=True)
        
        # 1. Export Gerbers
        # Layers: F.Cu, B.Cu, F.Paste, B.Paste, F.SilkS, B.SilkS, F.Mask, B.Mask, Edge.Cuts
        layers = "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"
        subprocess.run([
            "kicad-cli", "pcb", "export", "gerber",
            "--output", str(gerber_dir),
            "--layers", layers,
            str(pcb_path_obj)
        ], check=True)
        
        # 2. Export Drill Files
        subprocess.run([
            "kicad-cli", "pcb", "export", "drill",
            "--output", str(gerber_dir),
            str(pcb_path_obj)
        ], check=True)
        
        # 3. Zip everything
        zip_name = f"{pcb_path_obj.stem}_gerbers.zip"
        zip_path = Path(output_dir) / zip_name
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(gerber_dir):
                for file in files:
                    zipf.write(os.path.join(root, file), arcname=file)
                    
        # Cleanup
        shutil.rmtree(gerber_dir)
        
        logger.info(f"Gerber bundle generated at {zip_path}")
        return zip_name
    except Exception as e:
        logger.error(f"Failed to generate gerbers: {e}")
        return None
