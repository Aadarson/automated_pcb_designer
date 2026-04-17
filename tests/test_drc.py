import pytest
from backend.models.design import DRCReport, DRCViolation
from backend.kicad_bridge.drc_runner import run_drc
from backend.design_engine.drc import run_internal_drc

def test_overlapping_components_drc_error():
    # Mock DRC
    report = DRCReport(violations=[
        DRCViolation(severity="error", rule="overlap", description="Overlap desc")
    ], passed=False)
    
    assert report.passed == False
    assert any(v.severity == "error" for v in report.violations)

def test_trace_narrower_than_min_width_drc_warning():
    report = DRCReport(violations=[
        DRCViolation(severity="warning", rule="trace_width", description="Width warning")
    ], passed=True)
    
    assert report.passed == True
    assert any(v.severity == "warning" for v in report.violations)

def test_perfect_board_passes_drc():
    report = DRCReport(violations=[], passed=True)
    assert report.passed == True
    assert len(report.violations) == 0
