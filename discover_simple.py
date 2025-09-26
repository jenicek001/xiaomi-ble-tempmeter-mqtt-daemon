#!/usr/bin/env python3
"""
Simple BLE scanner for Xiaomi devices using basic system tools.
No external Python dependencies required.
"""

import subprocess
import json
import re
import time


def scan_for_xiaomi_devices():
    """Use bluetoothctl to scan for Xiaomi devices."""
    print("🔍 Scanning for Xiaomi devices using bluetoothctl...")
    print("Make sure your LYWSDCGQ/01ZM device is nearby and powered on!")
    print("=" * 60)
    
    try:
        # Start scan
        print("Starting 20-second Bluetooth scan...")
        subprocess.run(["bluetoothctl", "scan", "on"], 
                      timeout=20, capture_output=True)
        
        # Get list of discovered devices
        result = subprocess.run(["bluetoothctl", "devices"], 
                               capture_output=True, text=True)
        
        if result.returncode == 0:
            devices = result.stdout.strip().split('\n')
            xiaomi_devices = []
            
            print(f"Found {len(devices)} total devices, filtering for Xiaomi...")
            print()
            
            for device_line in devices:
                if device_line.strip():
                    # Parse device line: "Device MAC_ADDRESS Device_Name"
                    parts = device_line.split(' ', 2)
                    if len(parts) >= 2:
                        mac = parts[1]
                        name = parts[2] if len(parts) > 2 else "Unknown"
                        
                        # Check if it's a Xiaomi device
                        if is_xiaomi_device(mac, name):
                            xiaomi_devices.append({
                                'mac': mac,
                                'name': name
                            })
                            
            if xiaomi_devices:
                print("✅ Found Xiaomi device(s):")
                print()
                for i, device in enumerate(xiaomi_devices, 1):
                    print(f"Device {i}:")
                    print(f"  📍 MAC Address: {device['mac']}")
                    print(f"  📱 Name: {device['name']}")
                    print(f"  🔧 Likely Type: {guess_device_type(device['name'])}")
                    print()
                    
                print("💡 To use this device, add to your .env file:")
                print(f"   STATIC_DEVICES_MACS=\"{xiaomi_devices[0]['mac']}\"")
                print()
            else:
                print_troubleshooting()
                
        else:
            print(f"❌ Error running bluetoothctl: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("Scan completed (20 seconds)")
        subprocess.run(["bluetoothctl", "scan", "off"], capture_output=True)
    except Exception as e:
        print(f"❌ Error during scan: {e}")


def is_xiaomi_device(mac, name):
    """Check if device is likely a Xiaomi device."""
    # Xiaomi MAC prefixes (first 3 octets)
    xiaomi_prefixes = [
        "A4:C1:38",  # Common Xiaomi prefix
        "58:2D:34",  # Another Xiaomi prefix
        "54:EF:44",  # Xiaomi prefix
        "C4:7C:8D",  # Xiaomi prefix
    ]
    
    # Check MAC prefix
    mac_prefix = mac[:8].upper()
    if any(mac.upper().startswith(prefix) for prefix in xiaomi_prefixes):
        return True
        
    # Check device name
    xiaomi_names = [
        "LYWSD03MMC", "LYWSDCGQ", "MJ_HT_V1", "LYWSD02",
        "Xiaomi", "Mi Temp", "Mijia"
    ]
    
    name_upper = name.upper()
    if any(xiaomi_name.upper() in name_upper for xiaomi_name in xiaomi_names):
        return True
        
    return False


def guess_device_type(name):
    """Guess the device type from the name."""
    name_upper = name.upper()
    
    if "LYWSD03MMC" in name_upper:
        return "LYWSD03MMC (Mijia BLE Hygrothermograph)"
    elif "LYWSDCGQ" in name_upper:
        return "LYWSDCGQ/01ZM (Original Mijia)"
    elif "MJ_HT_V1" in name_upper:
        return "MJ_HT_V1 (Mijia Gen1)"
    else:
        return "Unknown Xiaomi device"


def print_troubleshooting():
    """Print troubleshooting tips."""
    print("❌ No Xiaomi devices found!")
    print()
    print("💡 Troubleshooting tips:")
    print("  1. Make sure the device is powered on (check LCD display)")
    print("  2. Ensure device is within 3-5 meters of this computer")
    print("  3. Try removing and reinserting the battery")
    print("  4. Make sure no other apps are connected to the device")
    print("  5. Wait a few seconds and try scanning again")
    print()
    print("🔧 Manual steps to find your device:")
    print("  1. Run: bluetoothctl")
    print("  2. Type: scan on")
    print("  3. Wait 10-15 seconds")
    print("  4. Look for devices with MAC starting with A4:C1:38")
    print("  5. Type: scan off")
    print("  6. Type: exit")


if __name__ == "__main__":
    scan_for_xiaomi_devices()