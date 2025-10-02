#!/usr/bin/env python3
"""Test RSSI information from Xiaomi sensor advertisements."""

import asyncio
from bleak import BleakScanner

XIAOMI_SERVICE_UUID = "0000fe95-0000-1000-8000-00805f9b34fb"
TARGET_MACS = ["4C:65:A8:DC:84:01", "4C:65:A8:DB:99:44"]

def advertisement_callback(device, advertisement_data):
    """Handle BLE advertisements and show RSSI information."""
    if device.address.upper() in [mac.upper() for mac in TARGET_MACS]:
        service_data = advertisement_data.service_data
        
        # Get RSSI information
        rssi = advertisement_data.rssi if hasattr(advertisement_data, 'rssi') else "N/A"
        
        print(f"\n--- Advertisement from {device.address} ---")
        print(f"Device Name: {device.name}")
        print(f"RSSI: {rssi} dBm")
        
        # Show signal strength interpretation
        if isinstance(rssi, int):
            if rssi >= -30:
                strength = "Excellent"
            elif rssi >= -67:
                strength = "Very Good"  
            elif rssi >= -70:
                strength = "Good"
            elif rssi >= -80:
                strength = "Fair"
            elif rssi >= -90:
                strength = "Weak"
            else:
                strength = "Very Weak"
            
            print(f"Signal Strength: {strength}")
            
            # Estimate distance (very rough approximation)
            if rssi >= -50:
                distance = "Very Close (< 1m)"
            elif rssi >= -60:
                distance = "Close (1-3m)"
            elif rssi >= -70:
                distance = "Medium (3-10m)"
            elif rssi >= -80:
                distance = "Far (10-30m)"
            else:
                distance = "Very Far (> 30m)"
            
            print(f"Estimated Distance: {distance}")
        
        # Check if we have Xiaomi service data
        if XIAOMI_SERVICE_UUID in service_data:
            service_data_bytes = service_data[XIAOMI_SERVICE_UUID]
            print(f"Service Data: {service_data_bytes.hex()}")
            
            # Quick parsing for sensor type
            data = service_data_bytes
            if len(data) >= 12:
                for i in range(len(data) - 5):
                    if (i + 6 < len(data) and 
                        data[i:i+3] == bytes([0x0d, 0x10, 0x04])):
                        temp_raw = data[i + 3]
                        temp = temp_raw / 10.0
                        print(f"Temperature: {temp:.1f}°C")
                    elif (i + 5 < len(data) and 
                          data[i:i+3] == bytes([0x06, 0x10, 0x02])):
                        hum_bytes = data[i + 3:i + 5]
                        hum_raw = int.from_bytes(hum_bytes, byteorder='little')
                        humidity = hum_raw / 10.0
                        print(f"Humidity: {humidity:.1f}%")
                    elif (i + 4 < len(data) and 
                          data[i:i+3] == bytes([0x0a, 0x10, 0x01])):
                        battery = data[i + 3]
                        print(f"Battery: {battery}%")

async def scan_with_rssi():
    """Scan for advertisements and show RSSI information."""
    print("Scanning for Xiaomi sensors with RSSI information...")
    print(f"Target devices: {TARGET_MACS}")
    print("\nRSSI Scale:")
    print("  > -30 dBm: Excellent")
    print("  -30 to -67 dBm: Very Good")
    print("  -67 to -70 dBm: Good") 
    print("  -70 to -80 dBm: Fair")
    print("  -80 to -90 dBm: Weak")
    print("  < -90 dBm: Very Weak")
    print()
    
    scanner = BleakScanner(advertisement_callback)
    
    await scanner.start()
    await asyncio.sleep(30)  # Scan for 30 seconds
    await scanner.stop()
    
    print("\nScan completed!")

if __name__ == "__main__":
    asyncio.run(scan_with_rssi())