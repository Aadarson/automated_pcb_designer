import logging
from backend.design_engine.parser import parse_prompt
from backend.kicad.footprint_resolver import resolver

# Test 1: Original complex prompt
prompt1 = 'Design a 2-layer Arduino Uno motor driver shield with two L298N dual H-bridge motor driver ICs for controlling 4 DC motors, 100nF decoupling capacitors on each L298N power pin, a 7805 5V voltage regulator for logic power, 470uF bulk capacitor on the 12V motor supply rail, flyback diodes on all motor output pins, screw terminal connectors for motor outputs, and a 2x8 pin header for Arduino stacking.'

# Test 2: The fail prompt (Universal Expansion)
prompt2 = 'Raspberry-Pi-IoT-Sensor-Hub'

# Test 3: Mixed prompt
prompt3 = 'ESP32 with DHT11 and a 9V battery'

for i, prompt in enumerate([prompt1, prompt2, prompt3], 1):
    print(f"\n--- Test {i}: {prompt} ---")
    req = parse_prompt(prompt)
    print(f"Components found: {len(req['components'])}")
    for c in req["components"]:
        print(f"  {c['ref']}: {c['part_id']} -> {c['footprint']}")
    print(f"Nets derived: {[n['name'] for n in req['nets']]}")
