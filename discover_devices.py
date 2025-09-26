#!/usr/bin/env python3
"""
Device discovery script for Xiaomi Mijia thermometers.
Scans for and displays information about discoverable devices.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from bluetooth_manager import BluetoothManager


async def discover_xiaomi_devices():
    """Discover and display Xiaomi thermometer devices."""
    print("🔍 Scanning for Xiaomi Mijia thermometers...")
    print("Make sure your device is nearby and not connected to other apps!")
    print("=" * 60)
    
    # Create bluetooth manager with basic config
    config = {
        "adapter": 0,
        "scan_duration": 15,  # Longer scan for better detection
        "connection_timeout": 10,
        "retry_attempts": 3,
        "retry_delay": 5
    }
    
    bluetooth_manager = BluetoothManager(config)
    
    try:
        # Discover devices
        devices = await bluetooth_manager.discover_devices()
        
        if devices:
            print(f"✅ Found {len(devices)} Xiaomi device(s):")
            print()
            
            for i, device in enumerate(devices, 1):
                print(f"Device {i}:")
                print(f"  📍 MAC Address: {device['mac']}")
                print(f"  📱 Name: {device['name']}")
                print(f"  🔧 Mode: {device['mode']}")
                print(f"  📶 RSSI: {device.get('rssi', 'N/A')} dBm")
                print()
                
            print("💡 Copy the MAC address to your .env file:")
            print("   STATIC_DEVICES_MACS=\"<MAC_ADDRESS>\"")
            
        else:
            print("❌ No Xiaomi devices found!")
            print()
            print("💡 Troubleshooting tips:")
            print("  - Make sure the device is nearby (within 3-5 meters)")
            print("  - Ensure no other apps are connected to the device")
            print("  - Try removing and reinserting the battery")
            print("  - Check if Bluetooth is enabled on this system")
            
    except Exception as e:
        print(f"❌ Error during discovery: {e}")
        
    finally:
        await bluetooth_manager.cleanup()


if __name__ == "__main__":
    asyncio.run(discover_xiaomi_devices())