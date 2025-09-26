#!/usr/bin/env python3
"""
Bluetooth discovery test using bleak library.
Tests our ability to discover and connect to Xiaomi thermometers.
"""

import asyncio
import sys
from typing import List, Dict

try:
    from bleak import BleakScanner, BleakClient
except ImportError:
    print("❌ bleak not available. Run with: uvx --with bleak python test_bluetooth_discovery.py")
    exit(1)


# Known Xiaomi device patterns
XIAOMI_DEVICE_PATTERNS = [
    "MJ_HT_V1",          # LYWSDCGQ/01ZM
    "LYWSD03MMC",        # LYWSD03MMC  
    "LYWSDCGQ",          # Various LYWSDCGQ
    "MiTemp"             # Generic Mijia
]

# Known Xiaomi MAC prefixes
XIAOMI_MAC_PREFIXES = [
    "A4:C1:38",  # Common Xiaomi prefix
    "58:2D:34",  # Another Xiaomi prefix
    "54:EF:44",  # Xiaomi prefix
    "C4:7C:8D",  # Xiaomi prefix
    "4C:65:A8",  # Your device prefix!
]


async def scan_for_xiaomi_devices(scan_duration: int = 15) -> List[Dict]:
    """Scan for Xiaomi Mijia devices using bleak."""
    print(f"🔍 Scanning for Xiaomi devices for {scan_duration} seconds...")
    print("Make sure your MJ_HT_V1 device is powered on and nearby!")
    print("=" * 60)
    
    discovered_devices = []
    
    def device_detected(device, advertisement_data):
        """Called when a device is discovered."""
        mac = device.address
        name = device.name or "Unknown"
        rssi = advertisement_data.rssi
        
        # Check if it's a Xiaomi device
        if is_xiaomi_device(mac, name):
            device_info = {
                "mac": mac,
                "name": name,
                "rssi": rssi,
                "mode": guess_device_mode(name),
                "advertisment_data": {
                    "local_name": advertisement_data.local_name,
                    "manufacturer_data": dict(advertisement_data.manufacturer_data),
                    "service_data": dict(advertisement_data.service_data),
                    "service_uuids": list(advertisement_data.service_uuids)
                }
            }
            
            # Avoid duplicates
            if not any(d["mac"] == mac for d in discovered_devices):
                discovered_devices.append(device_info)
                print(f"✅ Found Xiaomi device: {name} ({mac}) RSSI: {rssi} dBm")
    
    try:
        # Start scanning
        async with BleakScanner(detection_callback=device_detected) as scanner:
            await asyncio.sleep(scan_duration)
        
        return discovered_devices
        
    except Exception as e:
        print(f"❌ Error during BLE scan: {e}")
        return []


def is_xiaomi_device(mac: str, name: str) -> bool:
    """Check if device is likely a Xiaomi device."""
    # Check MAC prefix
    for prefix in XIAOMI_MAC_PREFIXES:
        if mac.upper().startswith(prefix):
            return True
    
    # Check device name patterns
    name_upper = name.upper()
    for pattern in XIAOMI_DEVICE_PATTERNS:
        if pattern.upper() in name_upper:
            return True
    
    return False


def guess_device_mode(name: str) -> str:
    """Guess the device mode from the name."""
    name_upper = name.upper()
    
    if "MJ_HT_V1" in name_upper:
        return "LYWSDCGQ/01ZM"
    elif "LYWSD03MMC" in name_upper:
        return "LYWSD03MMC"
    elif "LYWSDCGQ" in name_upper:
        return "LYWSDCGQ/01ZM"
    else:
        return "Unknown"


async def test_connection(device_info: Dict) -> bool:
    """Test connecting to a discovered device."""
    mac = device_info["mac"]
    name = device_info["name"]
    
    print(f"\n🔗 Testing connection to {name} ({mac})...")
    
    try:
        async with BleakClient(mac) as client:
            if client.is_connected:
                print(f"✅ Successfully connected to {name}!")
                
                # Get basic device info
                try:
                    services = await client.get_services()
                    print(f"   📋 Found {len(services.services)} services")
                    
                    # Look for characteristics we might use
                    for service in services.services:
                        print(f"   🔧 Service: {service.uuid}")
                        for char in service.characteristics:
                            properties = ", ".join(char.properties)
                            print(f"      📡 Characteristic: {char.uuid} ({properties})")
                            
                            # Check for our expected handles
                            if "0038" in str(char.handle) or "0046" in str(char.handle):
                                print(f"      ⭐ Found expected handle: {char.handle}")
                    
                except Exception as e:
                    print(f"   ⚠️  Could not get services: {e}")
                
                return True
            else:
                print(f"❌ Failed to connect to {name}")
                return False
                
    except Exception as e:
        print(f"❌ Connection error to {name}: {e}")
        return False


async def main():
    """Run Bluetooth discovery tests."""
    print("🧪 Bluetooth Device Discovery Test")
    print("=" * 40)
    
    # Test 1: Device Discovery
    devices = await scan_for_xiaomi_devices(scan_duration=15)
    
    if not devices:
        print("\n❌ No Xiaomi devices found!")
        print("\n💡 Troubleshooting:")
        print("  - Ensure device is powered on (check LCD display)")
        print("  - Device should be within 3-5 meters")
        print("  - Try removing and reinserting battery")
        print("  - Make sure no other apps are connected to device")
        return False
    
    print(f"\n🎉 Found {len(devices)} Xiaomi device(s):")
    print()
    
    for i, device in enumerate(devices, 1):
        print(f"Device {i}:")
        print(f"  📍 MAC: {device['mac']}")
        print(f"  📱 Name: {device['name']}")
        print(f"  🔧 Mode: {device['mode']}")
        print(f"  📶 RSSI: {device['rssi']} dBm")
        print()
    
    # Test 2: Connection Test
    print("🔗 Testing connections...")
    
    success_count = 0
    for device in devices:
        if await test_connection(device):
            success_count += 1
    
    print(f"\n📊 Connection Results: {success_count}/{len(devices)} successful")
    
    # Test 3: Check your configured device
    your_device_mac = "4C:65:A8:DC:84:01"  # From your .env file
    found_your_device = any(d["mac"] == your_device_mac for d in devices)
    
    if found_your_device:
        print(f"✅ Your configured device ({your_device_mac}) was found!")
    else:
        print(f"⚠️  Your configured device ({your_device_mac}) was not found in this scan")
        print("   - It might appear in a longer scan or when closer")
    
    return len(devices) > 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)