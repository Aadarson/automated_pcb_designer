import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ─── Color map ────────────────────────────────────────────────────────────────
COMPONENT_COLORS = {
    "MCU":        "#312e81",
    "IC":         "#1c1c3b",
    "Regulator":  "#065f46",  # distinct green — power component
    "LED":        "#065f46",
    "Resistor":   "#7c2d12",
    "Capacitor":  "#1e3a5f",
    "Connector":  "#3b1f6a",
    "Battery":    "#78350f",
    "Switch":     "#1a3a2a",
    "Relay":      "#3b2a1a",
    "Transistor": "#2a1a3b",
    "Diode":      "#1a2a3b",
    "Sensor":     "#1a3b2a",
}

# ─── MCU voltage requirements ─────────────────────────────────────────────────
MCU_VOLTAGE: Dict[str, float] = {
    "esp32":   3.3,
    "esp8266": 3.3,
    "atmega":  5.0,
    "arduino": 5.0,
    "nano":    5.0,
    "uno":     5.0,
    "stm32":   3.3,
    "pic":     3.3,
}

# Voltage regulators: (input_max, output_v, part, footprint, pins)
REGULATORS = [
    (20.0, 3.3, "AMS1117-3.3", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", ["VIN", "VOUT", "GND"]),
    (35.0, 5.0, "LM7805",      "Package_TO_SOT_THT:TO-220-3_Vertical",  ["VIN", "VOUT", "GND"]),
]

# ─── Component detection patterns ────────────────────────────────────────────
COMP_PATTERNS = [
    # (regex, type, footprint, pin_prefix_list)
    (r"(\d+(?:\.\d+)?)[vV]\s+(?:power|supply|logic)?\s*(?:battery|pwr|vcc|bat|cell)",
     "Battery", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", ["BT", "+", "-"]),
    (r"(\d+[kKMm\s]?\d*)\s*(?:ohm|resistor|res)\b",
     "Resistor", "Resistor_SMD:R_0805_2012Metric", ["R", "1", "2"]),
    (r"(?:\d+\s+)?(?:red|green|blue|yellow|white|indicator)?\s*\b(led)\b",
     "LED", "LED_SMD:LED_0805_2012Metric", ["D", "A", "K"]),
    (r"(\d+[uunpmUUNPM]*[fF])\s+(?:bulk|decoupling|bypass|filter)?\s*(?:capacitor|cap)\b",
     "Capacitor", "Capacitor_SMD:C_0805_2012Metric", ["C", "1", "2"]),
    (r"\b(atmega\d+\w*)\b",
     "MCU", "Package_QFP:TQFP-32_7x7mm_P0.8mm", ["U", "VCC", "GND", "GPIO1", "GPIO2"]),
    (r"\b(esp32\w*)\b",
     "MCU", "RF_Module:ESP32-WROOM-32", ["U", "VCC", "GND", "GPIO1", "GPIO2", "GPIO3"]),
    (r"\b(esp8266\w*)\b",
     "MCU", "RF_Module:ESP-12E", ["U", "VCC", "GND", "GPIO1", "GPIO2"]),
    (r"\b(arduino\s+(?:uno|nano|micro)|nano|uno)\b",
     "MCU", "Module:Arduino_Nano_WithMountingHoles", ["U", "VCC", "GND", "D2", "D3", "A0"]),
    (r"\b(stm32\w*)\b",
     "MCU", "Package_QFP:LQFP-48_7x7mm_P0.5mm", ["U", "VCC", "GND", "PA0", "PA1"]),
    (r"\b(NE555|LM358|LM741)\b",
     "IC", "Package_DIP:DIP-8_W7.62mm", ["U", "VCC", "GND", "IN", "OUT"]),
    (r"\b(l298n?|a4988|drv8825)\b",
     "IC", "Package_TO_SOT_THT:TO-220-3_Vertical", ["U", "VCC", "GND", "IN1", "IN2"]),
    (r"\b(dht\d+|pir|ultrasonic)\b",
     "Sensor", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical", ["J", "VCC", "GND", "SIG"]),
    (r"(?:push|tactile)?\s*(?:switch|button|key)\b",
     "Switch", "Button_Switch_SMD:SW_SPST_B3U-1000P", ["SW", "1", "2"]),
    (r"(?:screw|terminal|pin)?\s*(?:connector|header)\b",
     "Connector", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", ["J", "1", "2", "3", "4"]),
    (r"\b(mosfet|transistor|2n\d{4}|bc\d{3})\b",
     "Transistor", "Package_TO_SOT_SMD:SOT-23", ["Q", "G", "D", "S"]),
    (r"\b(diode[s]?|1n\d{4})\b",
     "Diode", "Diode_SMD:D_0805_2012Metric", ["D", "A", "K"]),
    (r"\b(\d+)\s*(?:relay)\b",
     "Relay", "Relay_THT:Relay_SPDT_SANYOU_SRD_Series_Form_C", ["SW", "IN", "COM", "NO", "NC"]),
]

# ─── Canvas geometry ──────────────────────────────────────────────────────────
CANVAS_W, CANVAS_H, MARGIN = 860, 620, 60

PLACEMENT_ZONES = {
    "MCU":        (0.50, 0.40),
    "Regulator":  (0.30, 0.70),
    "Sensor":     (0.75, 0.25),
    "Battery":    (0.10, 0.65),
    "Connector":  (0.50, 0.85),
    "IC":         (0.75, 0.65),
    "Relay":      (0.25, 0.70),
    "LED":        (0.80, 0.70),
    "Resistor":   (0.68, 0.28),
    "Capacitor":  (0.28, 0.25),
    "Switch":     (0.10, 0.35),
    "Transistor": (0.87, 0.45),
    "Diode":      (0.87, 0.22),
}

COMP_SIZES = {
    "MCU":        (70, 50),
    "IC":         (60, 45),
    "Regulator":  (50, 30),
    "LED":        (28, 18),
    "Resistor":   (38, 18),
    "Capacitor":  (28, 18),
    "Battery":    (36, 24),
    "Connector":  (32, 50),
    "Switch":     (30, 20),
    "Relay":      (45, 30),
    "Transistor": (28, 20),
    "Diode":      (28, 18),
    "Sensor":     (40, 28),
}

# ─── Default fallback circuit (always valid) ──────────────────────────────────
DEFAULT_FALLBACK_CIRCUIT = {
    "components": [
        {"id":"U1",  "type":"MCU",       "ref":"U1",  "x":395,"y":270,"w":70,"h":50,"color":"#312e81","pins":["VCC","GND","GPIO1","GPIO2"],"footprint":"RF_Module:ESP32-WROOM-32","value":"ESP32"},
        {"id":"VR1", "type":"Regulator", "ref":"VR1", "x":240,"y":390,"w":50,"h":30,"color":"#065f46","pins":["VIN","VOUT","GND"],         "footprint":"Package_TO_SOT_SMD:SOT-223-3_TabPin2","value":"AMS1117-3.3"},
        {"id":"BT1", "type":"Battery",   "ref":"BT1", "x":100,"y":395,"w":36,"h":24,"color":"#78350f","pins":["+","-"],                    "footprint":"Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical","value":"9V"},
        {"id":"C1",  "type":"Capacitor", "ref":"C1",  "x":340,"y":390,"w":28,"h":18,"color":"#1e3a5f","pins":["1","2"],                    "footprint":"Capacitor_SMD:C_0805_2012Metric","value":"10uF"},
        {"id":"C2",  "type":"Capacitor", "ref":"C2",  "x":400,"y":390,"w":28,"h":18,"color":"#1e3a5f","pins":["1","2"],                    "footprint":"Capacitor_SMD:C_0805_2012Metric","value":"100nF"},
        {"id":"R1",  "type":"Resistor",  "ref":"R1",  "x":570,"y":200,"w":38,"h":18,"color":"#7c2d12","pins":["1","2"],                    "footprint":"Resistor_SMD:R_0805_2012Metric","value":"330R"},
        {"id":"D1",  "type":"LED",       "ref":"D1",  "x":650,"y":330,"w":28,"h":18,"color":"#065f46","pins":["A","K"],                    "footprint":"LED_SMD:LED_0805_2012Metric","value":"LED"},
    ],
    "connections": [
        {"from":"BT1.+",    "to":"VR1.VIN",  "net":"VBAT"},
        {"from":"BT1.-",    "to":"VR1.GND",  "net":"GND"},
        {"from":"VR1.VOUT", "to":"U1.VCC",   "net":"VCC_3V3"},
        {"from":"VR1.GND",  "to":"U1.GND",   "net":"GND"},
        {"from":"C1.1",     "to":"VR1.VOUT", "net":"VCC_3V3"},
        {"from":"C1.2",     "to":"VR1.GND",  "net":"GND"},
        {"from":"C2.1",     "to":"U1.VCC",   "net":"VCC_3V3"},
        {"from":"C2.2",     "to":"U1.GND",   "net":"GND"},
        {"from":"U1.GPIO1", "to":"R1.1",     "net":"NET_LED"},
        {"from":"R1.2",     "to":"D1.A",     "net":"NET_LED"},
        {"from":"D1.K",     "to":"U1.GND",   "net":"GND"},
    ]
}


# ─── Public API ───────────────────────────────────────────────────────────────

class PCBDesignParser:
    def extract_components(self, prompt: str) -> dict:
        return parse_prompt(prompt)


def parse_prompt(prompt: str) -> dict:
    """
    Parse a natural-language prompt into a canvas-ready PCB design.
    Power safety: auto-inserts voltage regulator when battery voltage
    exceeds the MCU's required operating voltage.
    """
    logger.info(f"Parsing prompt: {prompt!r}")

    ref_counters: Dict[str, int] = {}
    found = []

    for pattern, comp_type, footprint, pin_info in COMP_PATTERNS:
        for match in re.finditer(pattern, prompt, re.IGNORECASE):
            val = match.group(1) if match.lastindex else comp_type
            prefix = pin_info[0]
            ref_counters[prefix] = ref_counters.get(prefix, 0) + 1
            rid = f"{prefix}{ref_counters[prefix]}"
            found.append({
                "ref":       rid,
                "type":      comp_type,
                "value":     str(val),
                "footprint": footprint,
                "pins":      pin_info[1:],
                "color":     COMPONENT_COLORS.get(comp_type, "#1f2937"),
            })

    if not found:
        logger.warning("Nothing detected — returning default circuit.")
        return DEFAULT_FALLBACK_CIRCUIT

    # ── Power safety check ────────────────────────────────────────────────────
    found = _enforce_power_safety(found, prompt)

    # ── Placement ─────────────────────────────────────────────────────────────
    type_counts: Dict[str, int] = {}
    placed = []
    for comp in found:
        t = comp["type"]
        type_counts[t] = type_counts.get(t, 0) + 1
        cnt = type_counts[t]
        zx, zy = PLACEMENT_ZONES.get(t, (0.5, 0.5))
        w,  h  = COMP_SIZES.get(t, (40, 25))
        px = int(MARGIN + zx * (CANVAS_W - 2 * MARGIN) + (cnt - 1) * (w + 30))
        py = int(MARGIN + zy * (CANVAS_H - 2 * MARGIN) + (cnt - 1) * (h + 20))
        px = max(MARGIN, min(px, CANVAS_W - w - MARGIN))
        py = max(MARGIN, min(py, CANVAS_H - h - MARGIN))
        placed.append({**comp, "id": comp["ref"], "x": px, "y": py, "w": w, "h": h})

    connections = _generate_connections(placed)
    return {"components": placed, "connections": connections}


# ─── Power Safety Engine ──────────────────────────────────────────────────────

def _parse_voltage(value: str) -> Optional[float]:
    """Extract numeric voltage from a value string like '9V', '3.3V'."""
    m = re.search(r"(\d+(?:\.\d+)?)", str(value))
    return float(m.group(1)) if m else None


def _mcu_required_voltage(prompt: str, mcu_value: str) -> float:
    """Return voltage requirement for the detected MCU."""
    combined = (prompt + " " + mcu_value).lower()
    for keyword, voltage in MCU_VOLTAGE.items():
        if keyword in combined:
            return voltage
    return 3.3  # safe default


def _enforce_power_safety(components: list, prompt: str) -> list:
    """
    Analyse batteries and MCUs.
    If battery_voltage > mcu_required_voltage:
        → insert appropriate voltage regulator
        → add bulk (10 µF) + bypass (100 nF) decoupling caps
    Also ensures a decoupling cap exists on every MCU VCC.
    """
    batteries  = [c for c in components if c["type"] == "Battery"]
    mcus       = [c for c in components if c["type"] == "MCU"]
    regulators = [c for c in components if c["type"] == "Regulator"]

    if not batteries or not mcus:
        return components  # nothing to check

    bat_voltage = _parse_voltage(batteries[0]["value"])
    mcu_voltage  = _mcu_required_voltage(prompt, mcus[0]["value"])

    if bat_voltage is None:
        return components

    needs_regulator = bat_voltage > (mcu_voltage + 0.3)  # 0.3 V tolerance

    if needs_regulator and not regulators:
        logger.warning(
            f"Power safety: {bat_voltage}V battery → {mcu_voltage}V MCU. "
            "Auto-inserting voltage regulator."
        )
        # Pick regulator: lowest that covers input
        chosen = None
        for inp_max, out_v, part, fp, pins in REGULATORS:
            if bat_voltage <= inp_max and abs(out_v - mcu_voltage) < 0.1:
                chosen = (part, fp, pins, out_v)
                break
        if not chosen:
            # Fallback generic LDO
            chosen = ("AMS1117-3.3", "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
                      ["VIN", "VOUT", "GND"], 3.3)

        part, fp, pins, out_v = chosen
        components.append({
            "ref":       "VR1",
            "type":      "Regulator",
            "value":     part,
            "footprint": fp,
            "pins":      pins,
            "color":     COMPONENT_COLORS["Regulator"],
        })

        # Add bulk (10 µF) input cap if not already present
        caps = [c for c in components if c["type"] == "Capacitor"]
        cap_refs = [c["ref"] for c in caps]
        if "C_BULK" not in cap_refs:
            components.append({
                "ref":       "C_BULK",
                "type":      "Capacitor",
                "value":     "10uF",
                "footprint": "Capacitor_SMD:C_0805_2012Metric",
                "pins":      ["1", "2"],
                "color":     COMPONENT_COLORS["Capacitor"],
            })
        # Add bypass (100 nF) output cap
        if "C_BYP" not in cap_refs:
            components.append({
                "ref":       "C_BYP",
                "type":      "Capacitor",
                "value":     "100nF",
                "footprint": "Capacitor_SMD:C_0805_2012Metric",
                "pins":      ["1", "2"],
                "color":     COMPONENT_COLORS["Capacitor"],
            })

        logger.info(f"Regulator {part} inserted; decoupling caps added.")

    return components


# ─── Connection Generator ─────────────────────────────────────────────────────

def _generate_connections(components: list) -> list:
    """
    Build a complete, valid net list.
    Power chain:  Battery → [Regulator] → MCU VCC
    Signal chain: MCU GPIO → Resistor → LED → GND
    """
    connections = []

    by_type: Dict[str, list] = {}
    for c in components:
        by_type.setdefault(c["type"], []).append(c)

    mcu_list   = by_type.get("MCU", [])
    res_list   = by_type.get("Resistor", [])
    led_list   = by_type.get("LED", [])
    cap_list   = by_type.get("Capacitor", [])
    bat_list   = by_type.get("Battery", [])
    reg_list   = by_type.get("Regulator", [])
    ic_list    = by_type.get("IC", [])
    conn_list  = by_type.get("Connector", [])
    sw_list    = by_type.get("Switch", [])
    sens_list  = by_type.get("Sensor", [])

    mcu = (mcu_list + ic_list + [None])[0]
    bat = (bat_list + conn_list[:1] + [None])[0]
    reg = (reg_list + [None])[0]

    # ── Power chain ───────────────────────────────────────────────────────────
    if bat and reg:
        # Battery → Regulator input
        connections += [
            {"from": f"{bat['ref']}.+",   "to": f"{reg['ref']}.VIN", "net": "VBAT"},
            {"from": f"{bat['ref']}.-",   "to": f"{reg['ref']}.GND", "net": "GND"},
        ]
        # Regulator output → MCU
        if mcu:
            connections += [
                {"from": f"{reg['ref']}.VOUT", "to": f"{mcu['ref']}.VCC", "net": "VCC_REG"},
                {"from": f"{reg['ref']}.GND",  "to": f"{mcu['ref']}.GND", "net": "GND"},
            ]
    elif bat and mcu:
        # Direct connection (voltages are compatible)
        connections += [
            {"from": f"{bat['ref']}.+", "to": f"{mcu['ref']}.VCC", "net": "VCC"},
            {"from": f"{bat['ref']}.-", "to": f"{mcu['ref']}.GND", "net": "GND"},
        ]

    # ── Decoupling caps ───────────────────────────────────────────────────────
    vcc_net = "VCC_REG" if reg else "VCC"
    for i, cap in enumerate(cap_list):
        vcc_src = reg["ref"] if (reg and i == 0) else (mcu["ref"] if mcu else None)
        if vcc_src:
            connections += [
                {"from": f"{cap['ref']}.1", "to": f"{vcc_src}.{'VOUT' if reg and i == 0 else 'VCC'}", "net": vcc_net},
                {"from": f"{cap['ref']}.2", "to": f"{vcc_src}.{'GND' if reg  and i == 0 else 'GND'}", "net": "GND"},
            ]

    # ── Signal: MCU → Resistor → LED → GND ───────────────────────────────────
    gpio_pins = [p for p in (mcu["pins"] if mcu else [])
                 if p.startswith(("GPIO", "D", "PA", "A"))]

    for i, (res, led) in enumerate(zip(res_list, led_list)):
        gpio = gpio_pins[i] if i < len(gpio_pins) else f"GPIO{i+1}"
        if mcu:
            connections.append({"from": f"{mcu['ref']}.{gpio}", "to": f"{res['ref']}.1", "net": f"NET{i+1}"})
        connections.append(    {"from": f"{res['ref']}.2",       "to": f"{led['ref']}.A", "net": f"NET{i+1}"})
        if mcu:
            connections.append({"from": f"{led['ref']}.K",       "to": f"{mcu['ref']}.GND", "net": "GND"})

    # Unmatched LEDs → direct GND
    for led in led_list[len(res_list):]:
        if mcu:
            connections.append({"from": f"{led['ref']}.K", "to": f"{mcu['ref']}.GND", "net": "GND"})

    # ── Buttons / Switches ────────────────────────────────────────────────────
    for i, sw in enumerate(sw_list):
        gpio = gpio_pins[len(led_list) + i] if (len(led_list) + i) < len(gpio_pins) else f"GPIO{len(led_list)+i+1}"
        if mcu:
            connections += [
                {"from": f"{mcu['ref']}.{gpio}", "to": f"{sw['ref']}.1", "net": f"SW_NET{i+1}"},
                {"from": f"{sw['ref']}.2",        "to": f"{mcu['ref']}.GND", "net": "GND"},
            ]

    # ── Sensors ───────────────────────────────────────────────────────────────
    for i, sens in enumerate(sens_list):
        gpio = gpio_pins[len(led_list) + len(sw_list) + i] if (len(led_list)+len(sw_list)+i) < len(gpio_pins) else f"GPIO{len(led_list)+len(sw_list)+i+1}"
        if mcu:
            connections += [
                {"from": f"{sens['ref']}.SIG", "to": f"{mcu['ref']}.{gpio}", "net": f"SENS{i+1}"},
                {"from": f"{sens['ref']}.VCC", "to": f"{mcu['ref']}.VCC",    "net": vcc_net},
                {"from": f"{sens['ref']}.GND", "to": f"{mcu['ref']}.GND",    "net": "GND"},
            ]

    return connections
