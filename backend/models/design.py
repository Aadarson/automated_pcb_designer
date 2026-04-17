from pydantic import BaseModel, Field
from typing import Literal, Optional
from uuid import UUID

class BoardSpec(BaseModel):
    width_mm: float = Field(..., gt=0, le=500)
    height_mm: float = Field(..., gt=0, le=500)
    layers: Literal[2, 4, 6] = 2
    outline: Literal["rect", "rounded_rect"] = "rect"

class ComponentConstraint(BaseModel):
    fixed_pos: Optional[dict] = None   # {"x": float, "y": float}
    layer: Optional[Literal["F.Cu", "B.Cu"]] = None
    keep_away_mm: Optional[float] = None

class Component(BaseModel):
    ref: str                           # "U1", "C3", "R12"
    part_id: str                       # MPN or internal alias
    footprint: str                     # "Package_SO:SOIC-8_3.9x4.9mm"
    value: str                         # "10uF", "ESP32-WROOM"
    constraints: Optional[ComponentConstraint] = None

class NetPin(BaseModel):
    ref: str
    pin: str

class Net(BaseModel):
    name: str
    net_class: Literal["power", "signal", "differential"] = Field("signal", alias="class")
    pins: list[NetPin]

    class Config:
        populate_by_name = True

class DesignRules(BaseModel):
    min_clearance_mm: float = 0.15
    min_trace_width_mm: float = 0.2
    min_via_drill_mm: float = 0.3
    copper_weight_oz: Literal[1, 2] = 1
    impedance_controlled: bool = False

class RoutingGoals(BaseModel):
    minimize: list[Literal["wire_length", "vias", "crosstalk"]] = ["wire_length"]
    protect_nets: list[str] = []
    fill_copper: bool = True

class PCBDesignRequest(BaseModel):
    prompt: str
    project_name: str
    board: BoardSpec
    components: list[Component] = []
    nets: list[Net] = []
    rules: DesignRules = DesignRules()
    routing_goals: RoutingGoals = RoutingGoals()

class DRCViolation(BaseModel):
    severity: Literal["error", "warning"]
    rule: str
    description: str
    location: Optional[dict] = None

class DRCReport(BaseModel):
    violations: list[DRCViolation] = []
    warnings: list[DRCViolation] = []
    passed: bool

class PCBDesignResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "complete", "error", "partial"]
    result: Optional[dict] = None      # kicad_pcb_url, netlist_url, drc_report, placement_score, routing_completion
    errors: list[str] = []
