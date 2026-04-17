import subprocess
import json
import tempfile
import logging
from pathlib import Path
from backend.models.design import DRCReport, DRCViolation

logger = logging.getLogger(__name__)

def run_drc(pcb_path: str) -> DRCReport:
    try:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_output:
            out_file = tmp_output.name

        result = subprocess.run(
            ["kicad-cli", "pcb", "drc", "--format", "json", "--output", out_file, pcb_path],
            timeout=45,
            capture_output=True,
            text=True
        )

        if Path(out_file).stat().st_size == 0:
            logger.error("KiCad DRC output file is empty.")
            return DRCReport(violations=[DRCViolation(
                severity="error", rule="cli_error", description="KiCad DRC failed to produce a report."
            )], passed=False)

        with open(out_file, "r") as f:
            drc_data = json.load(f)

        Path(out_file).unlink(missing_ok=True)
        
        violations = []
        for v in drc_data.get("violations", []):
            # KiCad 9.0 JSON schema uses 'items' array with 'pos' instead of root 'location'
            loc = v.get("location")
            if not loc and "items" in v and len(v["items"]) > 0:
                first_item = v["items"][0]
                if "pos" in first_item:
                    loc = first_item["pos"]
                    
            violations.append(DRCViolation(
                severity=v.get("severity", "warning"),
                rule=v.get("type", "unknown"),
                description=v.get("description", ""),
                location=loc
            ))
            
        has_error = any(v.severity == "error" for v in violations)
        return DRCReport(violations=violations, passed=not has_error)

    except FileNotFoundError:
        logger.warning("kicad-cli not available, using internal DRC — results may differ from KiCad desktop.")
        # Fallback to internal DRC
        from backend.design_engine.drc import run_internal_drc
        return run_internal_drc(pcb_path)
    except subprocess.TimeoutExpired:
        logger.error("KiCad CLI DRC timed out.")
        return DRCReport(violations=[DRCViolation(
            severity="error", rule="timeout", description="DRC checking timed out"
        )], passed=False)
    except Exception as e:
        logger.error(f"DRC check failed: {str(e)}")
        return DRCReport(violations=[DRCViolation(
            severity="error", rule="exception", description=str(e)
        )], passed=False)
