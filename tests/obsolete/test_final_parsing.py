#!/usr/bin/env python3
"""Test the corrected Xiaomi parsing implementation."""

import asyncio
import time
from bleak import BleakScanner
from datetime import datetime

class SensorData:
    def __init__(self, temperature, humidity, battery, voltage, timestamp):
        self.temperature = temperature
        self.humidity = humidity
        self.battery = battery
        self.voltage = voltage
        self.timestamp = timestamp
    
    def __repr__(self):
        return f"SensorData(temp={self.temperature}°C, hum={self.humidity}%, bat={self.battery}%, time={self.timestamp})"

def parse_xiaomi_advertisement(service_data: bytes):
    """Parse Xiaomi advertisement data for LYWSDCGQ/01ZM devices."""
    if len(service_data) < 12:
        return None
    
    try:
        temp = None
        humidity = None
        battery = None
        
        print(f"Raw service data: {service_data.hex()}")
        
        # Look for message patterns in the advertisement data
        for i in range(len(service_data) - 5):
            # Temperature message: 0d1004[temp_byte][xx][xx][xx]
            if (i + 6 < len(service_data) and 
                service_data[i:i+3] == bytes([0x0d, 0x10, 0x04])):
                
                temp_raw = service_data[i + 3]
                temp = temp_raw / 10.0  # LYWSDCGQ/01ZM uses /10 scaling
                print(f"  Temperature: {temp:.1f}°C (from byte {temp_raw})")
            
            # Humidity message: 061002[hum_low][hum_high]
            elif (i + 5 < len(service_data) and 
                  service_data[i:i+3] == bytes([0x06, 0x10, 0x02])):
                
                hum_bytes = service_data[i + 3:i + 5]
                hum_raw = int.from_bytes(hum_bytes, byteorder='little')
                humidity = hum_raw / 10.0  # Little-endian /10 scaling
                print(f"  Humidity: {humidity:.1f}% (from bytes {hum_bytes.hex()} = {hum_raw})")
            
            # Battery message: 0a1001[battery_percent]
            elif (i + 4 < len(service_data) and 
                  service_data[i:i+3] == bytes([0x0a, 0x10, 0x01])):
                
                battery = service_data[i + 3]
                print(f"  Battery: {battery}%")
            
            # Alternative humidity message: 041002[data]
            elif (i + 5 < len(service_data) and 
                  service_data[i:i+3] == bytes([0x04, 0x10, 0x02])):
                
                alt_data = service_data[i + 3:i + 5]
                print(f"  Alt humidity data: {alt_data.hex()}")
                # Try different interpretations
                if len(alt_data) >= 1:
                    byte_val = alt_data[0]
                    if 30 <= byte_val <= 70:  # Reasonable humidity range
                        print(f"    Possible humidity (direct): {byte_val}%")
                if len(alt_data) >= 2:
                    le_val = int.from_bytes(alt_data, byteorder='little')
                    be_val = int.from_bytes(alt_data, byteorder='big')
                    le_hum = le_val / 10.0
                    be_hum = be_val / 10.0
                    print(f"    LE interpretation: {le_hum:.1f}%")
                    print(f"    BE interpretation: {be_hum:.1f}%")
                    if 30 <= le_hum <= 70:
                        humidity = le_hum
                        print(f"    *** Using LE humidity: {humidity:.1f}% ***")
                    elif 30 <= be_hum <= 70:
                        humidity = be_hum
                        print(f"    *** Using BE humidity: {humidity:.1f}% ***")
        
        # Return data if we have at least temperature
        if temp is not None:
            if -40 <= temp <= 80:
                if humidity is None:
                    humidity = 0
                if battery is None:
                    battery = 0
                if humidity > 100:
                    humidity = 0
                
                return SensorData(
                    temperature=temp,
                    humidity=humidity,
                    battery=battery,
                    voltage=0.0,
                    timestamp=datetime.now()
                )
        
    except Exception as e:
        print(f"Error parsing: {e}")
    
    return None

XIAOMI_SERVICE_UUID = "0000fe95-0000-1000-8000-00805f9b34fb"
TARGET_MACS = ["4C:65:A8:DC:84:01", "4C:65:A8:DB:99:44"]

def advertisement_callback(device, advertisement_data):
    """Handle BLE advertisements."""
    if device.address.upper() in [mac.upper() for mac in TARGET_MACS]:
        service_data = advertisement_data.service_data
        
        if XIAOMI_SERVICE_UUID in service_data:
            service_data_bytes = service_data[XIAOMI_SERVICE_UUID]
            
            print(f"\n--- Advertisement from {device.address} ---")
            
            sensor_data = parse_xiaomi_advertisement(service_data_bytes)
            if sensor_data:
                print(f"  ✅ SUCCESS: {sensor_data}")
            else:
                print(f"  ❌ Failed to parse sensor data")

async def test_parsing():
    """Test the corrected parsing implementation."""
    print("Testing corrected Xiaomi LYWSDCGQ/01ZM parsing")
    print(f"Target devices: {TARGET_MACS}")
    print("Expected: Temp ~24.6-24.8°C, Humidity ~48.5%\n")
    
    scanner = BleakScanner(advertisement_callback)
    
    await scanner.start()
    await asyncio.sleep(60)  # Scan for 60 seconds to catch humidity messages
    await scanner.stop()
    
    print("\nTest completed!")

if __name__ == "__main__":
    asyncio.run(test_parsing())