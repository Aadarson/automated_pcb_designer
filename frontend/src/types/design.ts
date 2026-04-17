export interface BoardSpec {
    width_mm: number;
    height_mm: number;
    layers: 2 | 4 | 6;
    outline: "rect" | "rounded_rect";
}

export interface ComponentConstraint {
    fixed_pos?: { x: number; y: number };
    layer?: "F.Cu" | "B.Cu";
    keep_away_mm?: number;
}

export interface Component {
    ref: string;
    part_id: string;
    footprint: string;
    value: string;
    constraints?: ComponentConstraint;
}

export interface NetPin {
    ref: string;
    pin: string;
}

export interface Net {
    name: string;
    net_class: "power" | "signal" | "differential";
    pins: NetPin[];
}

export interface DesignRules {
    min_clearance_mm: number;
    min_trace_width_mm: number;
    min_via_drill_mm: number;
    copper_weight_oz: 1 | 2;
    impedance_controlled: boolean;
}

export interface RoutingGoals {
    minimize: ("wire_length" | "vias" | "crosstalk")[];
    protect_nets: string[];
    fill_copper: boolean;
}

export interface PCBDesignRequest {
    prompt: string;
    project_name: string;
    board: BoardSpec;
    components?: Component[];
    nets?: Net[];
    rules?: DesignRules;
    routing_goals?: RoutingGoals;
}

export interface DRCViolation {
    severity: "error" | "warning";
    rule: string;
    description: string;
    location?: { x: number; y: number };
}

export interface DRCReport {
    violations: DRCViolation[];
    passed: boolean;
}

export interface PCBDesignResponse {
    job_id: string;
    status: "queued" | "running" | "complete" | "error";
    result?: {
        kicad_pcb_url: string;
        netlist_url: string;
        drc_report: DRCReport;
        placement_score?: number;
        routing_completion?: number;
        placements?: any[];
        traces?: any[];
    };
    errors?: string[];
}
