import requests
import time
import sys

def run_test():
    print("Sending PCB Design Request to local API...")
    url = "http://127.0.0.1:8000/api/v1/design/"
    payload = {
        "project_name": "TestDRC_Local",
        "prompt": "Arduino Uno clone with a ch340g, 4 leds, 2 resistors, and a usb c port.",
        "width_mm": 60,
        "height_mm": 60,
        "layers": 2,
        "power_nets": ["GND", "5V", "3V3"]
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        job_id = data.get("job_id")
        print(f"Job queued: {job_id}")
    except Exception as e:
        print(f"Failed to submit: {e}")
        return

    print("Checking status via websockets or looping...")
    # The API might be fully async. The design returns immediately with job_id.
    # Where does it store project data? Probably in SQLite `design_versions`!
    time.sleep(10)
    print("Finished requesting.")

if __name__ == "__main__":
    run_test()
