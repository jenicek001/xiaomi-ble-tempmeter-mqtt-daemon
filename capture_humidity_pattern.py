#!/usr/bin/env python3
"""Capture multiple advertisement samples to find humidity pattern."""

import asyncio
import time
from bleak import BleakScanner

XIAOMI_SERVICE_UUID = "0000fe95-0000-1000-8000-00805f9b34fb"
TARGET_MACS = ["4C:65:A8:DC:84:01", "4C:65:A8:DB:99:44"]

def parse_xiaomi_service_data(service_data_hex: str, mac: str) -> dict:
    """Parse Xiaomi service data with corrected temperature scaling."""
    try:
        data = bytes.fromhex(service_data_hex)
        
        if len(data) >= 7 and data[2] == 0x04:
            sensor_data = data[3:]  # Skip header: 0d 10 04
            
            # Temperature: first byte / 10 (0xf8 = 248 / 10 = 24.8°C - CORRECT!)
            temp = sensor_data[0] / 10.0
            
            # Now we need to find humidity. Known value is ~48.5%
            # Let's check all remaining bytes
            print(f"MAC {mac}: Temp={temp:.1f}°C, Raw bytes: {sensor_data.hex()}")
            for i, byte_val in enumerate(sensor_data[1:], 1):
                print(f"  Byte {i}: {byte_val} (0x{byte_val:02x})")
                if 40 <= byte_val <= 60:  # Reasonable humidity range
                    print(f"    *** Potential humidity: {byte_val}% ***")
            
            return {
                "temperature": temp,
                "raw_data": sensor_data.hex(),
                "bytes": [sensor_data[i] for i in range(len(sensor_data))]
            }
            
    except Exception as e:
        print(f"Error parsing service data for {mac}: {e}")
    
    return {}

def advertisement_callback(device, advertisement_data):
    """Handle BLE advertisements."""
    if device.address.upper() in [mac.upper() for mac in TARGET_MACS]:
        service_data = advertisement_data.service_data
        
        if XIAOMI_SERVICE_UUID in service_data:
            service_data_bytes = service_data[XIAOMI_SERVICE_UUID]
            service_data_hex = service_data_bytes.hex()
            
            print(f"\n--- Advertisement from {device.address} ---")
            print(f"Service data: {service_data_hex}")
            
            parsed = parse_xiaomi_service_data(service_data_hex, device.address)
            if parsed:
                print(f"Parsed: {parsed}")

async def scan_advertisements():
    """Scan for Xiaomi sensor advertisements."""
    print(f"Scanning for advertisements from: {TARGET_MACS}")
    print("Looking for humidity pattern in multiple samples...")
    print("Known values: Temp 24.6-24.8°C, Humidity ~48.5%")
    print()
    
    scanner = BleakScanner(advertisement_callback)
    
    # Scan for 30 seconds to get multiple samples
    await scanner.start()
    await asyncio.sleep(30)
    await scanner.stop()

if __name__ == "__main__":
    asyncio.run(scan_advertisements())