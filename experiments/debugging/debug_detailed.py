#!/usr/bin/env python3
"""Debug the parsing to see why humidity/battery are 0."""

import asyncio
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from bluetooth_manager import BluetoothManager
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

class MockConfig:
    def __init__(self):
        self.connection_timeout = 20  # Shorter test
        self.retry_attempts = 1
        self.scan_timeout = 20
        self._data = {
            "adapter": 0,
            "connection_timeout": 20,
            "retry_attempts": 1
        }
    
    def get(self, key, default=None):
        return self._data.get(key, default)

async def debug_sensor_parsing():
    """Debug why humidity and battery are showing as 0."""
    
    print("Debugging Xiaomi LYWSDCGQ/01ZM parsing with detailed logging")
    print("Looking for humidity ~48% and battery ~55-58%")
    print()
    
    # Initialize Bluetooth manager with debug logging
    config = MockConfig()
    bt_manager = BluetoothManager(config)
    
    # Test just one device for detailed debugging
    mac_address = "4C:65:A8:DC:84:01"
    
    try:
        print(f"Reading from {mac_address} with debug logging...")
        
        sensor_data = await bt_manager.read_device_data(
            mac_address=mac_address,
            device_mode="LYWSDCGQ/01ZM"
        )
        
        if sensor_data:
            print(f"\n✅ FINAL RESULT:")
            print(f"  Temperature: {sensor_data.temperature:.1f}°C")
            print(f"  Humidity: {sensor_data.humidity:.1f}%")
            print(f"  Battery: {sensor_data.battery}%")
            print(f"  RSSI: {sensor_data.rssi} dBm")
        else:
            print(f"\n❌ No sensor data returned")
            
        # Check cache contents
        if hasattr(bt_manager, '_device_cache'):
            cache = bt_manager._device_cache.get(mac_address.upper())
            if cache:
                print(f"\n📋 CACHE CONTENTS:")
                print(f"  Temperature: {cache.get('temperature')}")
                print(f"  Humidity: {cache.get('humidity')}")
                print(f"  Battery: {cache.get('battery')}")
                print(f"  RSSI: {cache.get('rssi')}")
                print(f"  Last Update: {cache.get('last_update')}")
    
    except Exception as e:
        print(f"Error during debugging: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await bt_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(debug_sensor_parsing())