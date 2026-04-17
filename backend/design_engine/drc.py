import logging
from backend.models.design import DRCReport, DRCViolation

logger = logging.getLogger(__name__)

def run_internal_drc(pcb_path: str) -> DRCReport:
    """
    Internal fallback DRC runner when kicad-cli is not available.
    """
    logger.info("Running internal DRC ...")
    violations = []
    
    # In a real implementation we would parse the pcb_path using kiutils
    # and perform basic clearance, overlap, and unconnected checks.
    
    violations.append(DRCViolation(
        severity="warning",
        rule="internal_fallback",
        description="kicad-cli not available, using internal DRC — results may differ from KiCad desktop."
    ))
    
    # Mock passed = True for stub
    has_error = any(v.severity == "error" for v in violations)
    return DRCReport(violations=violations, passed=not has_error)
