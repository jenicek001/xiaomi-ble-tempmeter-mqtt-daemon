#!/usr/bin/env python3
"""
Discover additional Xiaomi sensors and fix advertisement parsing with original logic.
"""

import asyncio
import sys
from pathlib import Path

try:
    from bleak import BleakScanner
    import struct
    import time
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Run with: uvx --with bleak python discover_sensors.py")
    exit(1)


async def discover_xiaomi_sensors():
    """Discover all Xiaomi sensors in range."""
    print("🔍 Scanning for Xiaomi Sensors")
    print("=" * 40)
    
    # Known Xiaomi device patterns
    xiaomi_patterns = ["MJ_HT_V1", "LYWSD03MMC", "LYWSDCGQ"]
    xiaomi_mac_prefixes = ["A4:C1:38", "58:2D:34", "54:EF:44", "C4:7C:8D", "4C:65:A8"]
    
    discovered_sensors = []
    
    def detection_callback(device, advertisement_data):
        """Handle discovered devices."""
        mac = device.address
        name = device.name or "Unknown"
        
        # Check if it's a Xiaomi device
        is_xiaomi = False
        
        # Check by name
        for pattern in xiaomi_patterns:
            if pattern.upper() in name.upper():
                is_xiaomi = True
                break
        
        # Check by MAC prefix
        if not is_xiaomi:
            for prefix in xiaomi_mac_prefixes:
                if mac.upper().startswith(prefix):
                    is_xiaomi = True
                    break
        
        if is_xiaomi:
            device_info = {
                'mac': mac,
                'name': name,
                'rssi': getattr(device, 'rssi', 'N/A'),
                'manufacturer_data': dict(advertisement_data.manufacturer_data),
                'service_data': dict(advertisement_data.service_data)
            }
            
            # Avoid duplicates
            if not any(d['mac'] == mac for d in discovered_sensors):
                discovered_sensors.append(device_info)
                print(f"📱 Found Xiaomi device: {name} ({mac})")
                
                # Check for sensor data in advertisements
                xiaomi_service_uuid = "0000fe95-0000-1000-8000-00805f9b34fb"
                if xiaomi_service_uuid in advertisement_data.service_data:
                    service_data = advertisement_data.service_data[xiaomi_service_uuid]
                    print(f"   📊 Service data: {service_data.hex()}")
                    
                    # Try to decode with original logic
                    result = decode_xiaomi_original(service_data)
                    if result:
                        print(f"   🎉 Decoded: {result['temperature']}°C, {result['humidity']}%")
    
    try:
        print("Scanning for 20 seconds...")
        scanner = BleakScanner(detection_callback=detection_callback)
        await scanner.start()
        await asyncio.sleep(20)
        await scanner.stop()
        
        print(f"\n📋 Summary: Found {len(discovered_sensors)} Xiaomi device(s)")
        
        for i, device in enumerate(discovered_sensors, 1):
            print(f"\nDevice {i}:")
            print(f"  📍 MAC: {device['mac']}")
            print(f"  📱 Name: {device['name']}")
            print(f"  📶 RSSI: {device['rssi']}")
            
            # Determine device type
            if "MJ_HT_V1" in device['name']:
                device_type = "LYWSDCGQ/01ZM"
            elif "LYWSD03MMC" in device['name']:
                device_type = "LYWSD03MMC"
            else:
                device_type = "LYWSDCGQ/01ZM"  # Default for MJ_HT_V1
            
            print(f"  🔧 Type: {device_type}")
        
        return discovered_sensors
        
    except Exception as e:
        print(f"❌ Scanning failed: {e}")
        return []


def decode_xiaomi_original(service_data):
    """
    Decode Xiaomi service data using the original mitemp_bt2 logic.
    
    Based on the original handleNotification code:
    temp = round(int.from_bytes(data[0:2], byteorder="little", signed=True) / 100, 1)
    humidity = int.from_bytes(data[2:3], byteorder="little")
    voltage = int.from_bytes(data[3:5], byteorder="little") / 1000.0
    """
    
    if len(service_data) < 11:  # Need at least header + MAC + some data
        return None
    
    try:
        # Xiaomi service data format:
        # [0-1]: Frame control
        # [2-3]: Product ID  
        # [4]: Frame counter
        # [5-10]: MAC address (reversed)
        # [11+]: Sensor data in TLV format
        
        payload = service_data[11:]  # Skip header
        
        if len(payload) < 3:
            return None
        
        # Look for TLV entries in the payload
        pos = 0
        temp = None
        humidity = None
        battery = None
        
        while pos < len(payload) - 2:
            data_type = payload[pos]
            data_len = payload[pos + 1]
            
            if pos + 2 + data_len > len(payload):
                break
            
            data_value = payload[pos + 2:pos + 2 + data_len]
            
            # Xiaomi data types based on original code
            if data_type == 0x04 and data_len == 2:  # Temperature
                temp = round(
                    int.from_bytes(data_value, byteorder="little", signed=True) / 100, 1
                )
            elif data_type == 0x06 and data_len == 2:  # Humidity  
                humidity = int.from_bytes(data_value, byteorder="little")
            elif data_type == 0x0A and data_len == 1:  # Battery percentage
                battery = data_value[0]
            elif data_type == 0x10 and data_len == 4:  # Combined temp+humidity
                # This is the format we've been seeing
                temp = round(
                    int.from_bytes(data_value[0:2], byteorder="little", signed=True) / 100, 1
                )
                humidity = int.from_bytes(data_value[2:3], byteorder="little")
                # Last byte might be battery or voltage related
                if len(data_value) >= 4:
                    voltage = int.from_bytes(data_value[2:4], byteorder="little") / 1000.0
                    # Original battery calculation: min(int(round((voltage - 2.1), 2) * 100), 100)
                    if voltage > 2.0:  # Reasonable voltage
                        battery = min(int(round((voltage - 2.1) * 100, 0)), 100)
                        battery = max(0, battery)  # Ensure non-negative
            
            pos += 2 + data_len
        
        # Validate results
        if temp is not None and humidity is not None:
            if -40 <= temp <= 80 and 0 <= humidity <= 100:
                result = {'temperature': temp, 'humidity': humidity}
                if battery is not None and 0 <= battery <= 100:
                    result['battery'] = battery
                return result
        
    except Exception as e:
        print(f"   ⚠️  Decode error: {e}")
    
    return None


async def main():
    """Run sensor discovery."""
    sensors = await discover_xiaomi_sensors()
    
    if len(sensors) >= 2:
        print("\n🎉 Found multiple sensors! Ready to configure both.")
        
        print(f"\n📝 Configuration suggestion:")
        print(f"```yaml")
        print(f"# Add to config/config.yaml")
        print(f"devices:")
        print(f"  static_devices:")
        
        for i, sensor in enumerate(sensors):
            device_type = "LYWSDCGQ/01ZM" if "MJ_HT_V1" in sensor['name'] else "LYWSD03MMC"
            room_name = f"room_{i+1}" if i > 0 else "loznice"
            print(f"    - mac: \"{sensor['mac']}\"")
            print(f"      mode: \"{device_type}\"")
            print(f"      name: \"{room_name}\"")
        print(f"```")
        
        print(f"\n📝 Environment variables suggestion:")
        all_macs = ",".join([s['mac'] for s in sensors])
        print(f"```bash")
        print(f"# Add to .env file")
        print(f"STATIC_DEVICES_MACS=\"{all_macs}\"")
        print(f"```")
        
    elif len(sensors) == 1:
        print(f"\n⚠️  Only found 1 sensor. Make sure the second sensor is:")
        print(f"   - Powered on (check LCD display)")
        print(f"   - Within range (< 10 meters)")
        print(f"   - Has fresh batteries")
        
    else:
        print(f"\n❌ No Xiaomi sensors found. Check:")
        print(f"   - Device is powered on")
        print(f"   - Bluetooth is enabled")
        print(f"   - Device is in range")
    
    return len(sensors) > 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)