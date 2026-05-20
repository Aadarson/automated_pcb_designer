import logging
import re
import difflib
from typing import Dict, List, Any
from backend.kicad.footprint_resolver import resolver

logger = logging.getLogger(__name__)

def parse_prompt(prompt: str) -> dict:
    """
    Universal Entity Extractor for PCB design prompts.
    Moves beyond hardcoded regex to heuristic token matching.
    """
    logger.info(f"Universal Parsing user prompt: {prompt}")
    
    components = []
    nets = []
    net_id = 1
    ref_counters = {"R": 1, "C": 1, "D": 1, "U": 1, "BT": 1, "J": 1, "SW": 1, "M": 1}

    def add_comp(ref_prefix, val, fp, part_name):
        nonlocal components
        ref = f"{ref_prefix}{ref_counters[ref_prefix]}"
        ref_counters[ref_prefix] += 1
        components.append({
            "ref": ref,
            "part_id": part_name.upper(),
            "footprint": fp,
            "value": val
        })
        return ref

    # 1. Tokenization & Platform Detection
    tokens = re.findall(r"\b\w+\b", prompt.lower())
    
    platforms = {
        "raspberry": {"fp": "Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Vertical", "prefix": "J", "name": "RPi_Header", "rails": ["3V3", "5V", "GND"]},
        "arduino": {"fp": "Module:Arduino_Nano_WithMountingHoles", "prefix": "U", "name": "Arduino_Nano", "rails": ["5V", "GND"]},
        "esp32": {"fp": "RF_Module:ESP32-WROOM-32", "prefix": "U", "name": "ESP32", "rails": ["3V3", "GND"]},
        "stm32": {"fp": "Package_QFP:LQFP-48_7x7mm_P0.5mm", "prefix": "U", "name": "STM32", "rails": ["3V3", "GND"]}
    }
    
    detected_platforms = []
    for plat_key, info in platforms.items():
        if plat_key in prompt.lower():
            add_comp(info["prefix"], info["name"], info["fp"], info["name"])
            detected_platforms.append(info)

    # 2. Universal Part Identification (Heuristic)
    # Match alphanumeric parts like MCP23017, LM7805, 2N2222
    part_matches = re.findall(r"\b([A-Z]{1,3}\d{3,5}[A-Z]*)\b", prompt, re.IGNORECASE)
    for part in part_matches:
        if part.lower() in platforms: continue # Skip if already handled as platform
        
        # Search for best footprint in the library
        found_fp = resolver.find_best_footprint(part)
        if found_fp:
            add_comp("U", part, found_fp, part)
            logger.info(f"Heuristic Match: Found footprint {found_fp} for {part}")

    # 3. Component Dictionary (Standard Passives)
    comp_patterns = [
        (r"(\d+[vV])\s+(?:power|supply|logic)?\s*(battery|pwr|vcc)", "Battery_Header", "BT"),
        (r"(\d+[kM\s]?\d*)\s*(?:pull-up|pull-down|series)?\s*(ohm|resistor|res)", "Resistor_SMD:R_0805_2012Metric", "R"),
        (r"(?:\d+\s+)?(?:red|green|blue|yellow|indicator)?\s*(led)", "LED_SMD:LED_0805_2012Metric", "D"),
        (r"(\d+[uunpmUUNPM]*[fF])\s+(?:bulk|decoupling|bypass|filter)?\s*(capacitor|cap)", "Capacitor_SMD:C_0805_2012Metric", "C"),
        (r"(?:push|tactile)?\s*(switch|button|key)\b", "Button_Switch_SMD:SW_SPST_B3U-1000P", "SW"),
        (r"(?:usb|type-c)\b", "Connector_USB:USB_C_Receptacle_GCT_USB4085", "J")
    ]
    
    for pattern, footprint, prefix in comp_patterns:
        matches = re.findall(pattern, prompt, re.IGNORECASE)
        for val in matches:
            if isinstance(val, tuple): val = val[0]
            add_comp(prefix, val, footprint, val)

    # 4. Universal Connector Rule ("Hub", "Port", "Sensor")
    if any(k in tokens for k in ["hub", "port", "sensor", "interface"]):
        # Add generic 4-pin header for unknown sensors/extensions (VCC/GND/SDA/SCL)
        if not any(c["ref"].startswith("J") for c in components):
            add_comp("J", "Generic_Hub", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", "Hub_Connector")

    # 5. Net Derivation (Universal Net Rule)
    # Always include GND and VCC
    nets.append({"id": net_id, "name": "GND", "class": "power", "pins": []})
    net_id += 1
    
    # Identify primary VCC based on platform
    primary_vcc = "VCC"
    if detected_platforms:
        primary_vcc = detected_platforms[0]["rails"][0] # e.g. "3V3" or "5V"
        
    nets.append({"id": net_id, "name": primary_vcc, "class": "power", "pins": []})
    net_id += 1
    
    # Bus Mapping
    bus_map = {
        "i2c": [("SDA", "signal"), ("SCL", "signal")],
        "spi": [("MOSI", "signal"), ("MISO", "signal"), ("SCK", "signal"), ("CS", "signal")],
        "can": [("CAN_H", "differential"), ("CAN_L", "differential")],
        "usb": [("USB_DP", "differential"), ("USB_DN", "differential")],
        "uart": [("TX", "signal"), ("RX", "signal")],
    }
    
    for bus_key, signal_list in bus_map.items():
        if bus_key in tokens:
            for sig_name, sig_class in signal_list:
                nets.append({"id": net_id, "name": sig_name, "class": sig_class, "pins": []})
                net_id += 1

    # 6. PWM / ADC Detection (Heuristic)
    pwm_matches = re.findall(r"(\d+)\s*PWM", prompt, re.IGNORECASE)
    pwm_count = int(pwm_matches[0]) if pwm_matches else (1 if "pwm" in tokens else 0)
    for i in range(1, pwm_count + 1):
        nets.append({"id": net_id, "name": f"PWM_{i}", "class": "signal", "pins": []})
        net_id += 1

    adc_matches = re.findall(r"(\d+)\s*ADC", prompt, re.IGNORECASE)
    adc_count = int(adc_matches[0]) if adc_matches else (1 if "adc" in tokens else 0)
    for i in range(1, adc_count + 1):
        nets.append({"id": net_id, "name": f"ADC_{i}", "class": "signal", "pins": []})
        net_id += 1

    # 7. Pin Assignment Heuristic (Fix for missing connections)
    mcu = next((c for c in components if c["ref"].startswith("U")), None)
    mcu_pads = []
    if mcu:
        mcu_pads = sorted([p for p in resolver.get_pad_offsets(mcu["footprint"]).keys() if p.isdigit()], key=int)
        
    mcu_pin_idx = 2 # Skip first two pins (reserved for power/gnd)
    
    for net in nets:
        if net["class"] == "power":
            # Connect all components to power and ground
            for c in components:
                pads = sorted([p for p in resolver.get_pad_offsets(c["footprint"]).keys() if p.isdigit()], key=int)
                if not pads: pads = list(resolver.get_pad_offsets(c["footprint"]).keys())
                if not pads: continue
                
                if net["name"] == "GND" and len(pads) > 0:
                    net["pins"].append({"ref": c["ref"], "pin": str(pads[0])})
                elif net["name"] != "GND" and len(pads) > 1:
                    net["pins"].append({"ref": c["ref"], "pin": str(pads[1])})
        else:
            # Connect signal nets between MCU and peripherals
            target_comp = next((c for c in components if not c["ref"].startswith("U") and not any(p["ref"] == c["ref"] for p in net["pins"])), None)
            if not target_comp:
                target_comp = next((c for c in components if not c["ref"].startswith("U")), None)
                
            if mcu and target_comp:
                t_pads = sorted([p for p in resolver.get_pad_offsets(target_comp["footprint"]).keys() if p.isdigit()], key=int)
                if not t_pads: t_pads = list(resolver.get_pad_offsets(target_comp["footprint"]).keys())
                
                if t_pads and mcu_pin_idx < len(mcu_pads):
                    net["pins"].append({"ref": mcu["ref"], "pin": str(mcu_pads[mcu_pin_idx])})
                    # Prefer using the last pad for signals on passives/connectors
                    net["pins"].append({"ref": target_comp["ref"], "pin": str(t_pads[-1])})
                    mcu_pin_idx += 1

    return {"components": components, "nets": nets}
