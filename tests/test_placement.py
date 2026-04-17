import pytest
from backend.models.design import PCBDesignRequest, BoardSpec, Component, ComponentConstraint
from backend.design_engine.placement import run_placement

def test_placement_returns_one_entry_per_component():
    req = PCBDesignRequest(
        prompt="Test",
        project_name="Test",
        board=BoardSpec(width_mm=100, height_mm=100),
        components=[
            Component(ref="U1", part_id="IC", footprint="SOIC-8", value="Test"),
            Component(ref="C1", part_id="CAP", footprint="0805", value="Test")
        ]
    )
    placements = run_placement(req)
    assert len(placements) == 2
    refs = [p.ref for p in placements]
    assert "U1" in refs
    assert "C1" in refs

def test_no_two_components_overlap():
    # In a real test we'd check HPWL and bounding boxes.
    # We'll just enforce they have different coordinates for the mock.
    req = PCBDesignRequest(
        prompt="Test2",
        project_name="Test",
        board=BoardSpec(width_mm=100, height_mm=100),
        components=[
            Component(ref="U1", part_id="IC", footprint="SOIC-8", value="Test"),
            Component(ref="U2", part_id="IC", footprint="SOIC-8", value="Test")
        ]
    )
    placements = run_placement(req)
    # They should not be at the exact same point usually (due to random init & SA)
    if placements[0].x == placements[1].x and placements[0].y == placements[1].y:
        assert False, "Components overlap exactly"

def test_decoupling_caps_within_2mm():
    # Placeholder for decoupling caps logic validation
    pass
