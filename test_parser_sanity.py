from backend.design_engine.parser import parse_prompt
import json

prompt = "Design a 2-layer PCB with an ESP32, USB-C for power, and an I2C sensor. Include 3.3V and GND copper pours."
result = parse_prompt(prompt)
print(json.dumps(result, indent=2))
