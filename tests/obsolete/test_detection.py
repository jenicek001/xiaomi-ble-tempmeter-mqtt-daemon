#!/usr/bin/env python3
"""
Test device detection method
"""
import asyncio
import logging
from src.bluetooth_manager import BluetoothManager

logging.basicConfig(level=logging.DEBUG)

async def test_device_detection():
    config = {'retry_attempts': 1}
    bt_manager = BluetoothManager(config)
    
    mac_address = "4C:65:A8:DC:84:01"
    
    print(f"Testing device detection for {mac_address}...")
    device_type = await bt_manager._detect_device_type(mac_address)
    print(f"Detected device type: '{device_type}'")
    
    # Also try direct advertisement reading
    print(f"\nTrying direct advertisement reading...")  
    result = await bt_manager.read_sensor_data_advertisement(mac_address, scan_timeout=15)
    if result:
        print(f"SUCCESS: {result}")
    else:
        print("FAILED: No data from advertisements")

if __name__ == "__main__":
    asyncio.run(test_device_detection())