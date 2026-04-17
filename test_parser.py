import logging
from backend.design_engine.parser import parse_prompt
from backend.kicad_bridge.footprint_resolver import resolver

prompt = 'Design a 2-layer Arduino Uno motor driver shield with two L298N dual H-bridge motor driver ICs for controlling 4 DC motors, 100nF decoupling capacitors on each L298N power pin, a 7805 5V voltage regulator for logic power, 470uF bulk capacitor on the 12V motor supply rail, flyback diodes on all motor output pins, screw terminal connectors for motor outputs, and a 2x8 pin header for Arduino stacking. Include GND and VCC copper pours.'

req = parse_prompt(prompt)
print(f'Components: {len(req["components"])}')
for c in req["components"]:
    size = resolver.get_footprint_size(c["footprint"])
    print(f'{c["ref"]} - {c["footprint"]} -> {size}')
