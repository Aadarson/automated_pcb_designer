import logging
import re
import difflib
from typing import Dict, List

logger = logging.getLogger(__name__)

# Component color map for canvas rendering
COMPONENT_COLORS = {
    "MCU": "#312e81",
    "LED": "#065f46",
    "Resistor": "#7c2d12",
    "Capacitor": "#1e3a5f",
    "Connector": "#3b1f6a",
    "Battery": "#78350f",
    "Switch": "#1a3a2a",
    "IC": "#1c1c3b",
    "Relay": "#3b2a1a",
    "Transistor": "#2a1a3b",
    "Diode": "#1a2a3b",
    "Sensor": "#1a3b2a",
}

# Footprint definitions keyed by component type
COMP_PATTERNS = [
    (r"(\d+[vV])\s+(?:power|supply|logic)?\s*(battery|pwr|vcc)", "Battery", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", ["BT", "+", "-"]),
    (r"(\d+[kM\s]?\d*)\s*(?:pull-up|pull-down|series)?\s*(ohm|resistor|res)", "Resistor", "Resistor_SMD:R_0805_2012Metric", ["R", "1", "2"]),
    (r"(?:\d+\s+)?(?:red|green|blue|yellow|indicator)?\s*(led)", "LED", "LED_SMD:LED_0805_2012Metric", ["D", "A", "K"]),
    (r"(\d+[uunpmUUNPM]*[fF])\s+(?:bulk|decoupling|bypass|filter)?\s*(capacitor|cap)", "Capacitor", "Capacitor_SMD:C_0805_2012Metric", ["C", "1", "2"]),
    (r"(atmega\d+\w*)", "MCU", "Package_QFP:TQFP-32_7x7mm_P0.8mm", ["U", "VCC", "GND", "GPIO1", "GPIO2"]),
    (r"(esp32\w*)", "MCU", "RF_Module:ESP32-WROOM-32", ["U", "VCC", "GND", "GPIO1", "GPIO2", "GPIO3"]),
    (r"(arduino\s+(uno|nano|micro)|nano|uno)", "MCU", "Module:Arduino_Nano_WithMountingHoles", ["U", "VCC", "GND", "D2", "D3", "A0"]),
    (r"\b(NE555|LM358|LM741|LM317|LM7805)\b", "IC", "Package_DIP:DIP-8_W7.62mm", ["U", "VCC", "GND", "IN", "OUT"]),
    (r"(\d+)\s*(relay[s]?)\b", "Relay", "Relay_THT:Relay_SPDT_SANYOU_SRD_Series_Form_C", ["SW", "IN", "COM", "NO", "NC"]),
    (r"\b(l298n?|a4988|drv8825)\b", "IC", "Package_TO_SOT_THT:TO-220-3_Vertical", ["U", "VCC", "GND", "IN1", "IN2"]),
    (r"\b(dht\d+|pir|ultrasonic)\b", "Sensor", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical", ["J", "VCC", "GND", "SIG"]),
    (r"(?:push|tactile)?\s*(switch|button|key)\b", "Switch", "Button_Switch_SMD:SW_SPST_B3U-1000P", ["SW", "1", "2"]),
    (r"(?:screw|terminal|pin)?\s*(connector|header)\b", "Connector", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", ["J", "1", "2", "3", "4"]),
    (r"\b(mosfet|transistor|2n\d{4}|bc\d{3})\b", "Transistor", "Package_TO_SOT_SMD:SOT-23", ["Q", "G", "D", "S"]),
    (r"\b(diode[s]?|1n\d{4})\b", "Diode", "Diode_SMD:D_0805_2012Metric", ["D", "A", "K"]),
]

# Canvas size (pixels) for coordinate mapping
CANVAS_W = 860
CANVAS_H = 620
MARGIN = 60

# Placement zones by component type (normalized 0-1 grid)
PLACEMENT_ZONES = {
    "MCU":        (0.50, 0.40),
    "Sensor":     (0.75, 0.25),
    "Battery":    (0.15, 0.70),
    "Connector":  (0.50, 0.85),
    "IC":         (0.75, 0.65),
    "Relay":      (0.25, 0.70),
    "LED":        (0.75, 0.75),
    "Resistor":   (0.60, 0.25),
    "Capacitor":  (0.30, 0.25),
    "Switch":     (0.15, 0.40),
    "Transistor": (0.85, 0.45),
    "Diode":      (0.85, 0.20),
}

# Component canvas sizes (w, h) in pixels
COMP_SIZES = {
    "MCU":        (70, 50),
    "IC":         (60, 45),
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

DEFAULT_FALLBACK_CIRCUIT = {
    "components": [
        {"id": "U1", "type": "MCU",      "ref": "U1",  "x": 395, "y": 270, "w": 70, "h": 50, "color": "#312e81", "pins": ["VCC","GND","GPIO1","GPIO2"], "footprint": "RF_Module:ESP32-WROOM-32", "value": "MCU"},
        {"id": "R1", "type": "Resistor", "ref": "R1",  "x": 560, "y": 210, "w": 38, "h": 18, "color": "#7c2d12", "pins": ["1","2"],                    "footprint": "Resistor_SMD:R_0805_2012Metric", "value": "10k"},
        {"id": "D1", "type": "LED",      "ref": "D1",  "x": 640, "y": 335, "w": 28, "h": 18, "color": "#065f46", "pins": ["A","K"],                    "footprint": "LED_SMD:LED_0805_2012Metric", "value": "LED"},
        {"id": "BT1","type": "Battery",  "ref": "BT1", "x": 140, "y": 335, "w": 36, "h": 24, "color": "#78350f", "pins": ["+","-"],                    "footprint": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", "value": "9V"},
    ],
    "connections": [
        {"from": "BT1.+",   "to": "U1.VCC",  "net": "VCC"},
        {"from": "BT1.-",   "to": "U1.GND",  "net": "GND"},
        {"from": "U1.GPIO1","to": "R1.1",    "net": "NET1"},
        {"from": "R1.2",    "to": "D1.A",    "net": "NET1"},
        {"from": "D1.K",    "to": "U1.GND",  "net": "GND"},
    ]
}


class PCBDesignParser:
    """
    Parses a natural language circuit description into a structured canvas-ready
    component and connection list, fully compatible with the frontend canvas format.
    """

    def extract_components(self, prompt: str) -> dict:
        return parse_prompt(prompt)


def parse_prompt(prompt: str) -> dict:
    """
    Parse a natural-language prompt into canvas-ready PCB design data.
    Returns: { components, connections }
    """
    logger.info(f"Parsing prompt: {prompt!r}")

    ref_counters = {"BT": 0, "R": 0, "D": 0, "C": 0, "U": 0, "J": 0, "SW": 0, "Q": 0}
    found = []

    for pattern, comp_type, footprint, pin_info in COMP_PATTERNS:
        for match in re.finditer(pattern, prompt, re.IGNORECASE):
            val = match.group(1) if match.lastindex else comp_type
            ref_prefix = pin_info[0]
            ref_counters[ref_prefix] = ref_counters.get(ref_prefix, 0) + 1
            ref = f"{ref_prefix}{ref_counters[ref_prefix]}"
            found.append({
                "ref": ref,
                "type": comp_type,
                "value": val,
                "footprint": footprint,
                "pins": pin_info[1:],
                "color": COMPONENT_COLORS.get(comp_type, "#1f2937"),
            })

    # If nothing was found, return a default valid circuit
    if not found:
        logger.warning("No components detected — returning default fallback circuit.")
        return DEFAULT_FALLBACK_CIRCUIT

    # --- Place components ---
    type_counts: Dict[str, int] = {}
    placed = []
    for comp in found:
        t = comp["type"]
        type_counts[t] = type_counts.get(t, 0) + 1
        count = type_counts[t]

        zone_x, zone_y = PLACEMENT_ZONES.get(t, (0.5, 0.5))
        w, h = COMP_SIZES.get(t, (40, 25))

        # Spread multiple components of the same type
        offset_x = (count - 1) * (w + 30)
        offset_y = (count - 1) * (h + 20)

        px = int(MARGIN + zone_x * (CANVAS_W - 2 * MARGIN) + offset_x)
        py = int(MARGIN + zone_y * (CANVAS_H - 2 * MARGIN) + offset_y)

        # Clamp to canvas bounds
        px = max(MARGIN, min(px, CANVAS_W - w - MARGIN))
        py = max(MARGIN, min(py, CANVAS_H - h - MARGIN))

        placed.append({
            "id": comp["ref"],
            "ref": comp["ref"],
            "type": comp["type"],
            "value": comp["value"],
            "x": px,
            "y": py,
            "w": w,
            "h": h,
            "color": comp["color"],
            "footprint": comp["footprint"],
            "pins": comp["pins"],
        })

    # --- Generate connections ---
    connections = _generate_connections(placed)

    return {"components": placed, "connections": connections}


def _generate_connections(components: list) -> list:
    """
    Generate logical net connections based on standard circuit rules:
    - Power source → MCU/IC VCC
    - MCU GPIO → Resistor pin 1
    - Resistor pin 2 → LED anode
    - LED cathode → GND
    - All GND pins share one net
    """
    connections = []
    by_type: Dict[str, list] = {}
    for c in components:
        by_type.setdefault(c["type"], []).append(c)

    mcu_list    = by_type.get("MCU", [])
    res_list    = by_type.get("Resistor", [])
    led_list    = by_type.get("LED", [])
    cap_list    = by_type.get("Capacitor", [])
    bat_list    = by_type.get("Battery", [])
    ic_list     = by_type.get("IC", [])
    conn_list   = by_type.get("Connector", [])
    sw_list     = by_type.get("Switch", [])
    sensor_list = by_type.get("Sensor", [])

    main_driver = (mcu_list + ic_list + [None])[0]  # First MCU or IC, or None

    gpio_idx = 0

    # Power: Battery/Connector → MCU VCC
    for src in bat_list + conn_list[:1]:
        if main_driver and "VCC" in main_driver["pins"]:
            connections.append({"from": f"{src['id']}.+", "to": f"{main_driver['id']}.VCC", "net": "VCC"})
            connections.append({"from": f"{src['id']}.-", "to": f"{main_driver['id']}.GND", "net": "GND"})

    # MCU → Resistor → LED chains
    gpio_pins = [p for p in (main_driver["pins"] if main_driver else []) if p.startswith("GPIO") or p.startswith("D")]
    for i, (res, led) in enumerate(zip(res_list, led_list)):
        gpio_pin = gpio_pins[i] if i < len(gpio_pins) else f"GPIO{i+1}"
        if main_driver:
            connections.append({"from": f"{main_driver['id']}.{gpio_pin}", "to": f"{res['id']}.1", "net": f"NET_{i+1}"})
        connections.append({"from": f"{res['id']}.2", "to": f"{led['id']}.A", "net": f"NET_{i+1}"})
        if main_driver:
            connections.append({"from": f"{led['id']}.K", "to": f"{main_driver['id']}.GND", "net": "GND"})

    # Unmatched LEDs → GND (no resistor pair)
    for led in led_list[len(res_list):]:
        if main_driver:
            connections.append({"from": f"{led['id']}.K", "to": f"{main_driver['id']}.GND", "net": "GND"})

    # Capacitors → decoupling on VCC/GND
    for cap in cap_list:
        if main_driver and "VCC" in main_driver["pins"]:
            connections.append({"from": f"{cap['id']}.1", "to": f"{main_driver['id']}.VCC", "net": "VCC"})
            connections.append({"from": f"{cap['id']}.2", "to": f"{main_driver['id']}.GND", "net": "GND"})

    # Switches → MCU GPIO
    for sw in sw_list:
        gpio_pin = gpio_pins[gpio_idx] if gpio_idx < len(gpio_pins) else f"GPIO{gpio_idx+1}"
        if main_driver:
            connections.append({"from": f"{main_driver['id']}.{gpio_pin}", "to": f"{sw['id']}.1", "net": f"NET_SW{gpio_idx+1}"})
            connections.append({"from": f"{sw['id']}.2", "to": f"{main_driver['id']}.GND", "net": "GND"})
        gpio_idx += 1

    # Sensors → MCU GPIO (signal) + power
    for sensor in sensor_list:
        gpio_pin = gpio_pins[gpio_idx] if gpio_idx < len(gpio_pins) else f"GPIO{gpio_idx+1}"
        if main_driver:
            connections.append({"from": f"{sensor['id']}.SIG", "to": f"{main_driver['id']}.{gpio_pin}", "net": f"NET_SENS{gpio_idx+1}"})
            connections.append({"from": f"{sensor['id']}.VCC", "to": f"{main_driver['id']}.VCC", "net": "VCC"})
            connections.append({"from": f"{sensor['id']}.GND", "to": f"{main_driver['id']}.GND", "net": "GND"})
        gpio_idx += 1

    return connections
