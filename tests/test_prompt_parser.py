import pytest
from backend.design_engine.parser import parse_prompt

def test_stm32_bus_derivation():
    prompt = "STM32 with I2C sensor and CAN transceiver"
    result = parse_prompt(prompt)
    nets = result["nets"]
    net_names = [n["name"] for n in nets]
    
    # Assert specific bus signals are present
    assert "SDA" in net_names
    assert "SCL" in net_names
    assert "CAN_H" in net_names
    assert "CAN_L" in net_names
    
    # Assert net count (GND, VCC, SDA, SCL, CAN_H, CAN_L)
    assert len(nets) >= 6
    
    # Assert unique IDs
    net_ids = [n["id"] for n in nets]
    assert len(net_ids) == len(set(net_ids))
    assert all(isinstance(nid, int) for nid in net_ids)

def test_esp32_spi_usb_derivation():
    prompt = "ESP32 with SPI flash and USB-C"
    result = parse_prompt(prompt)
    net_names = [n["name"] for n in result["nets"]]
    
    assert "MOSI" in net_names
    assert "MISO" in net_names
    assert "SCK" in net_names
    assert "CS" in net_names
    assert "USB_DP" in net_names
    assert "USB_DN" in net_names

def test_simple_blink_derivation():
    prompt = "LED blinker with resistor"
    result = parse_prompt(prompt)
    nets = result["nets"]
    net_names = [n["name"] for n in nets]
    
    # Minimal nets: GND=1, VCC=2
    assert "GND" in net_names
    assert "VCC" in net_names
    assert len(nets) == 2
    
    # Verify exact IDs for GND/VCC
    gnd = next(n for n in nets if n["name"] == "GND")
    vcc = next(n for n in nets if n["name"] == "VCC")
    assert gnd["id"] == 1
    assert vcc["id"] == 2
