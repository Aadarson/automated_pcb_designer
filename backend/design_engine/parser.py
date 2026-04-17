import logging
import re
import difflib
from typing import Dict, List
from backend.kicad_bridge.footprint_resolver import resolver

logger = logging.getLogger(__name__)

def parse_prompt(prompt: str) -> dict:
    """
    Advanced regex-based parser for identifying components and nets.
    Example prompt: "A 9V battery connected to a 1k resistor and a Red LED"
    """
    logger.info(f"Parsing user prompt: {prompt}")
    
    components = []
    nets = []
    
    # 1. Extract Components (Resistance, Capacitance, ICs, LEDs, Batteries)
    # Pattern: [Value] [Type] (e.g., "9V battery", "1k resistor", "Red LED")
    comp_patterns = [
        (r"(\d+[vV])\s+(?:power|supply|logic)?\s*(battery|pwr|vcc)", "Battery_Header"),
        (r"(\d+[kM\s]?\d*)\s*(?:pull-up|pull-down|series)?\s*(ohm|resistor|res)", "Resistor_SMD:R_0805_2012Metric"),
        (r"(?:\d+\s+)?(?:red|green|blue|yellow|indicator)?\s*(led)", "LED_SMD:LED_0805_2012Metric"),
        (r"(\d+[uunpmUUNPM]*[fF])\s+(?:bulk|decoupling|bypass|filter)?\s*(capacitor|cap)", "Capacitor_SMD:C_0805_2012Metric"),
        (r"(atmega\d+\w*)", "Package_QFP:TQFP-32_7x7mm_P0.8mm"),
        (r"(esp32\w*)", "RF_Module:ESP32-WROOM-32"),
        (r"(arduino\s+(uno|nano|micro)|nano|uno)", "Module:Arduino_Nano_WithMountingHoles"),
        (r"\b([A-Z]{2,3}\d{3,4}[A-Z]*)\b", "Package_DIP:DIP-8_W7.62mm"), # ICs like LM358, NE555
        (r"(\d+)\s*(relay[s]?)\b", "Relay_THT:Relay_SPDT_SANYOU_SRD_Series_Form_C"), 
        (r"\b(l298n?|a4988|drv8825)\b", "Package_TO_SOT_THT:TO-220-15_P1.27x2.54mm_StaggerOdd_Lead4.58mm_Vertical"),
        (r"\b(dht\d+|pir|ultrasonic)\b", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical"),
        (r"(?:push|tactile)?\s*(switch|button|key)\b", "Button_Switch_SMD:SW_SPST_B3U-1000P"),
        (r"(?:screw|terminal|pin)?\s*(connector|header)\b", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical"),
        (r"\b(mosfet|transistor|2n\d{4}|bc\d{3})\b", "Package_TO_SOT_SMD:SOT-23"),
        (r"\b(diode[s]?|1n\d{4})\b", "Diode_SMD:D_0805_2012Metric"),
    ]
    
    ref_counters = {"R": 1, "C": 1, "D": 1, "U": 1, "BT": 1, "J": 1, "SW": 1, "M": 1}
    
    for pattern, footprint in comp_patterns:
        matches = re.findall(pattern, prompt, re.IGNORECASE)
        for val in matches:
            if isinstance(val, tuple): val = val[0]
            
            ref_prefix = "U"
            if "resistor" in footprint.lower() or "R_" in footprint: ref_prefix = "R"
            elif "capacitor" in footprint.lower() or "C_" in footprint: ref_prefix = "C"
            elif "led" in footprint.lower() or "diode" in footprint.lower(): ref_prefix = "D"
            elif "battery" in footprint.lower(): ref_prefix = "BT"
            elif "connector" in footprint.lower() or "header" in footprint.lower(): ref_prefix = "J"
            elif "relay" in footprint.lower() or "switch" in footprint.lower() or "button" in footprint.lower(): ref_prefix = "SW"
            
            ref = f"{ref_prefix}{ref_counters[ref_prefix]}"
            ref_counters[ref_prefix] += 1
            
            # Fuzzy match footprint
            actual_fp = footprint.split(":")[-1] if ":" in footprint else footprint
            
            if actual_fp not in resolver.index:
                choices = [str(k) for k in resolver.index.keys() if isinstance(k, str)]
                matches = difflib.get_close_matches(actual_fp, choices, n=1, cutoff=0.5)
                if matches:
                    actual_fp = matches[0]
                    logger.info(f"Fuzzy matched '{footprint}' to '{actual_fp}'")

            components.append({
                "ref": ref,
                "part_id": val.upper(),
                "footprint": actual_fp,
                "value": val
            })
            
    # 2. Extract Connectivity (Semantic)
    # Very basic: if "connected to" or "and" exists, assume a single net for all components
    # In a real V3 system, this would be much more complex.
    if components:
        net_pins = []
        for c in components:
            # Assume pin 1 and 2 for passives, pin 1 for ICs as a first pass
            net_pins.append({"ref": c["ref"], "pin": "1"})
        
        nets.append({
            "name": "N1",
            "net_class": "signal",
            "pins": net_pins
        })

    return {"components": components, "nets": nets}
