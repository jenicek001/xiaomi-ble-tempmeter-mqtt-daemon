#!/usr/bin/env python3
"""Test the complete system with RSSI information included."""

import asyncio
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from bluetooth_manager import BluetoothManager

class MockConfig:
    def __init__(self):
        self.connection_timeout = 30
        self.retry_attempts = 3
        self.scan_timeout = 15
        self._data = {
            "adapter": 0,
            "connection_timeout": 30,
            "retry_attempts": 3
        }
    
    def get(self, key, default=None):
        return self._data.get(key, default)

async def test_sensor_reading_with_rssi():
    """Test reading from sensors including RSSI information."""
    
    print("Testing Xiaomi LYWSDCGQ/01ZM sensor reading with RSSI information")
    print("Expected values: Temp ~24.6-24.8°C, Humidity ~48.5%, RSSI -80 to -90 dBm")
    print()
    
    # Initialize Bluetooth manager with mock config
    config = MockConfig()
    bt_manager = BluetoothManager(config)
    
    # Test devices
    devices = [
        {"mac": "4C:65:A8:DC:84:01", "name": "Loznice"},
        {"mac": "4C:65:A8:DB:99:44", "name": "Chodba"}
    ]
    
    try:
        for device in devices:
            print(f"Reading from {device['name']} ({device['mac']})...")
            
            sensor_data = await bt_manager.read_device_data(
                mac_address=device['mac'],
                device_mode="LYWSDCGQ/01ZM"
            )
            
            if sensor_data:
                print(f"  ✅ SUCCESS:")
                print(f"    Temperature: {sensor_data.temperature:.1f}°C")
                print(f"    Humidity: {sensor_data.humidity:.1f}%")
                print(f"    Battery: {sensor_data.battery}%")
                
                if sensor_data.rssi is not None:
                    print(f"    RSSI: {sensor_data.rssi} dBm")
                    
                    # Signal quality assessment
                    if sensor_data.rssi >= -30:
                        quality = "Excellent"
                    elif sensor_data.rssi >= -67:
                        quality = "Very Good"
                    elif sensor_data.rssi >= -70:
                        quality = "Good"
                    elif sensor_data.rssi >= -80:
                        quality = "Fair"
                    elif sensor_data.rssi >= -90:
                        quality = "Weak"
                    else:
                        quality = "Very Weak"
                    
                    print(f"    Signal Quality: {quality}")
                else:
                    print(f"    RSSI: Not available")
                
                print(f"    Timestamp: {sensor_data.timestamp}")
                
                # Show MQTT data format
                mqtt_data = sensor_data.to_dict()
                print(f"    MQTT Data: {mqtt_data}")
                
                # Validate against expected values
                temp_ok = 24.0 <= sensor_data.temperature <= 25.5
                hum_ok = sensor_data.humidity == 0 or (40 <= sensor_data.humidity <= 60)
                rssi_ok = sensor_data.rssi is None or (-100 <= sensor_data.rssi <= -30)
                
                print(f"    Validation: Temp {'✅' if temp_ok else '❌'}, Humidity {'✅' if hum_ok else '❌'}, RSSI {'✅' if rssi_ok else '❌'}")
            else:
                print(f"  ❌ FAILED to read sensor data")
            
            print()
    
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await bt_manager.cleanup()
        
    print("Test completed!")

if __name__ == "__main__":
    asyncio.run(test_sensor_reading_with_rssi())